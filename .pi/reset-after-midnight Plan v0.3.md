# BirdFrame midnight reset — Plan v0.3

Repository: `AvianVisitors` (fork `moomoomafia/AvianVisitors`; parent `Twarner491/AvianVisitors`,
push to parent disabled). Branch: `feature/birdframe-midnight-reset`. Product base: `5950f807`
(= the parent's current tip, verified 2026-11-16).

Supersedes Plan v0.2. Everything here is grounded in the knowledge base, which is the source of
truth for evidence and rulings: [`.pi/knowledge/_index.md`](knowledge/_index.md),
[decision register](knowledge/open-decisions.md), [minimal-footprint](knowledge/minimal-footprint.md),
[verification log](knowledge/verification-log.md). Read [AGENTS.md](../AGENTS.md) first.

> **Status: plan only. Building is NOT authorised** until the operator says so (§9, gate G0).
>
> *Revision 2 (2026-11-16) after an Oracle review (verdict "ready with edits"): §4.2 now replaces
> the signature fetch when the flag is on (exactly one station fetch per run); the no-bundle
> drawable rule is a recorded D12 amendment; §5 gains six tests; §6 states how CI actually
> triggers. See [verification-log.md → Plan v0.3 Oracle review](knowledge/verification-log.md#plan-v03-oracle-review).*

---

## 1. Objective

Add an optional, per-frame `reset_at_midnight` setting (default off) to the BirdFrame in `local`
mode. When on, the frame shows only birds the **station** heard since the **station's** midnight.
The e-ink panel is never redrawn or blanked because the day rolled over: yesterday's collage stays
until the first bird the frame can actually draw is heard today, which replaces it with today's
birds only. Everything else — and the whole setting off — behaves exactly as the parent does today.

## 2. Guiding principle (D20)

Align with and default to what the parent repo does; change the smallest amount of code; reuse
upstream mechanisms before adding any; research/A-B when options are close; keep our tooling in
`.pi/`. This plan's shipped change is **5 parent files, ~45–60 changed lines plus tests in the
parent's existing test files** (upstream's own station midnight reset was +112 shipped / +108 test
lines).

## 3. Requirements → rulings (all decided; no open blockers)

| # | Requirement (v0.2 brief) | How it is met | Ruling |
|---|---|---|---|
| 1 | Today = station's calendar day from 00:00 | station clamps `recentWindow` with `hours=24` → `[midnight, now]` | D13, R3 (executed 30/30) |
| 2 | Show only today's species | the window above drives both the signature and the capture | D3, D17→superseded |
| 3 | Midnight resets logically, no redraw | decline when today has no **drawable** bird (exit 0, no capture, no `save_state`) | D1, D12 (+R5 amendment) |
| 4–5 | Keep the previous collage while today is empty, for any number of days | same decline; data-keyed, independent of `last_refresh` | D1, D7, D9 |
| 6 | First drawable detection replaces the collage | clamped species list → signature changes → normal refresh | D12a |
| 7 | Continue refreshing normally | unchanged signature/bucket logic | — |
| 8 | Never mix days | station-side clamp only; never capture without an honoured list | D16, R1 |
| 9 | Never overwrite with a blank screen because the window is empty | decline on **every** path: timer, heal, `--force`, `--no-signature`, `avian-bundle use/rollback`, `birdframe-names` | D1 |
| 10 | Heal cannot clear the collage | the decline runs before the gate | D7 |
| 11 | Survive restarts | decline is data-keyed; corrupt/missing state can't trigger a redraw | D9 |
| 12 | Off ⇒ unchanged | every new branch is behind the flag; no new param/hash/state otherwise | D3 condition |
| Iso | Station display, global `RESET_AT_MIDNIGHT`, history untouched | request-scoped param; frame never writes station config; read-only DB | D3, D10 |

Supporting rulings: **D2** local mode only (`species_source != "birdweather" and shoot is True`);
**D3** additive request param + config toggle `reset_at_midnight`, default `false`; **D4** CI = the
parent's existing jobs, no new workflow, hardware pass mandatory; **D11c** `.pi/` + `AGENTS.md`
are on this branch and must be stripped before any PR to the parent; **D14** outdated station ⇒
hold + exit 1; **D15** Educators scope ⇒ hold (falls into the D14 path); **D16** station
unreachable ⇒ timer skips (exit 0), forced run exits 1; **D20** minimal footprint.

## 4. Design

### 4.1 Station — `avian/api/birdnet-api.php` (R1 variant B′, +1 / 2 modified)

```php
// new line in the request-derived block, after $action (:135)
$resetAtMidnight = $RESET_AT_MIDNIGHT || (($_GET['reset_at_midnight'] ?? null) === '1');
// :169   (($educatorCacheDisabled || $resetAtMidnight) ? 'no-store' : 'public, max-age=30')
// :362   recentWindow($db, $hours, $ctx, $resetAtMidnight, $educatorScope !== null)
```

Facts this relies on (executed, R3): only exact `1` enables it; arrays, `0`, case variants are
ignored; PHP key mangling (`reset.at.midnight`) and last-wins duplicates behave as for every
upstream param; a request can never switch a station-wide ON off; educator scopes still win
(`:90`). Requests without the param are byte-identical to today. With the param, `no-store` applies
to whatever action carries it (parity with the global flag); the response field
`reset_at_midnight` then means "station flag OR param, not scoped" (no in-repo reader).

### 4.2 Frame — `frame/display.py`

1. `DEFAULTS["reset_at_midnight"] = False` (`:42-70`).
2. **One shared fetch.** Extract the body of `fetch_recent` (`:91-101`) into
   `fetch_recent_payload(base, hours, timeout, auth=None, reset_at_midnight=False)` returning the
   validated dict (same URL, same `read(2_000_000)`, same "no species list" `ValueError`), appending
   `&reset_at_midnight=1` only when asked. `fetch_recent` becomes a one-line wrapper returning
   `payload["species"]` — **identical behaviour**, pinned by the parent's
   `test_signature_fetch_rejects_missing_species_not_as_empty` and characterization C7. (Chosen over
   a duplicate helper to avoid copying upstream's URL/validation logic; D20. This deliberately
   departs from the superseded D17 bullet "add a flag-only helper rather than changing
   `fetch_recent`" — the parent's tests pin the wrapper's behaviour, copying the validation would
   be worse.)
3. **Activation** — `active = cfg.get("reset_at_midnight") is True and
   cfg.get("species_source") != "birdweather" and cfg.get("shoot") is True` (D2 amended). If the
   flag is set but not `active`, print one line ("reset_at_midnight applies only to local mode;
   ignored") and continue exactly as today.
4. **In `run()` (`:418`), when `active`, before the existing signature block:**

   | Step | Condition | Action | Exit |
   |---|---|---|---|
   | a | always (timer, heal, `--force`, `--no-signature`, preview) | `payload = fetch_recent_payload(base_url, 24, timeout, auth, reset_at_midnight=True)` | — |
   | b | fetch raised | timer run (`not force and use_signature`): print, **return True**; forced: print, **return False** | 0 / 1 |
   | c | `payload.get("midnight_clamped") is not True` | print "station did not apply the midnight window — update the station (Tools → Pull latest), or an Educators capture is active"; **return False** (preview: warn, continue) | 1 |
   | d | no species in `payload["species"]` is drawable (§4.4); with `bundle is None`, every species counts as drawable, so only an **empty** list declines | print "no drawable bird since midnight; keeping the current collage"; **return True** — no capture, no `push_panel`, no `save_state` (preview: continue and render) | 0 |
   | e | otherwise | `species = payload["species"]`. **The existing `if use_signature:` block (`frame/display.py:429-443`) is skipped**: if `use_signature`, set `sig = signature(species, "")` and apply the bundle salt exactly as at `:438-441`; `fetch_species` is **not** called — **exactly one station fetch per run**, and `changed` is decided on the clamped list. `--no-signature` keeps `changed = True` (`:445`). Then the **unchanged** gate: heal, quiet hours, capture, push, save. | as today |

   The steps sit in one `if active:` block; no restructuring of `run()` (it is already complexity 18
   upstream and the limit is not enforced on the parent's branch). The render lock is already held:
   `main()` takes it before calling `run()` (`frame/display.py:520-528`). Step (c) runs before (d) so
   an outdated station can never hide behind an exit-0 decline.
5. `obtain_image` (`:366`) passes `window_hours=24 if active else cfg["hours"]` and
   `reset_at_midnight=active` to `shoot()` (`:395-400`). The birdweather and image branches are
   untouched.

### 4.3 Frame — `frame/shoot.py`

`_make_api_handler(..., reset_at_midnight=False)` (`:243`): in the station branch after the existing
`hours` substitution (`:258`), append `reset_at_midnight=1` when asked and not already present.
`shoot(..., reset_at_midnight=False)` (`:412`) threads it to the route at `:448`. This is the
**single** injection point for every page `recent` request (verified, pre-v0.3 item 5); every other
query parameter is preserved verbatim (characterization C8). Upstream's re-sign from the captured
response (`frame/display.py:457-463`) keeps state truthful if the window changes between the fetch
and the capture.

### 4.4 "Drawable" (D12 + R5 amendment)

* **Frame bundle active** (the operator's setup, D12b): a species is drawable iff the bundle has a
  base pose for it — `"perched"` or `"variant-1"` in `bundle.index["assets"].get(slugify(sci), {})`.
  Equivalent to "its unsuffixed slug is a masks key" (install invariant,
  `frame/bundle_runtime.py:1883-1889`), i.e. exactly the collage's drop test
  (`avian/frontend/apt.js:3164-3186`). **Do not change `ActiveBundle.drawable_slugs`** (species-level;
  upstream BirdWeather filtering depends on it).
* **No frame bundle:** per the **D12 amendment of 2026-11-16** (parent-decided after the Oracle
  review; basis D20 and D12b) the frame does **not** fetch the station's mask table —
  `avian/frontend/masks.json` is ~800 KB, too heavy every 15 min on a Zero 2 W, and the operator's
  frame has its own bundle — so only an **empty** today-window declines. The residual risk (a
  station-default flight-only species) is fail-static: panel kept, capture times out, exit 1.

### 4.5 Config and docs

* `frame/config.example.toml`: add after `hours = 24` (`:26`):
  `# reset_at_midnight = false  # local mode only: show birds since the station's midnight; keeps the`
  `#                             # last collage until today's first drawable bird; needs an updated station`
* `frame/README.md`: one short paragraph after the bird-names section (`:87`): what it does, local
  mode only, `hours` is ignored while on, update the station first, `--force` will not repaint an
  empty day, set back to `false` to restore today's behaviour (no state reset needed). End-user
  voice, no internals. Also say: with an outdated station the frame keeps its collage and reports a
  failure every 15 minutes (including during quiet hours) until the station is updated (D14).

### 4.6 Not changed

`install.sh`, `config_contract.py`, `birdframe-names`, systemd units, `apt.js`, the station's global
setting, any workflow file, `ActiveBundle.drawable_slugs`, signature hashing (D6 dropped),
`state.json` format (D9).

## 5. Tests (in the parent's existing files, in their style)

| File | Add | Proves |
|---|---|---|
| `tests/test_frame_capture.py` | flag-on twins of characterization C1–C5: empty window ⇒ no capture/push/save, `run()` True; `--force` and `--no-signature` empty ⇒ same; heal-due empty ⇒ same; unreadable state + empty ⇒ same | req 3, 4, 5, 9, 10, 11 |
| ″ | flight-only-only today (bundle stand-in with `{"ardea-herodias": {"flight": …}}`) ⇒ decline; mixed list ⇒ draws | req 3, R5 |
| ″ | unclamped payload ⇒ `run()` False, no push (D14); fetch error ⇒ timer True / forced False, no push (D16) | D14, D16 |
| ″ | flag on, first drawable bird ⇒ capture receives the clamped list; signature from it; push + save | req 6, 7 |
| ″ | flag **off**: every C1–C8 case behaves exactly as characterized | req 12 |
| ″ | flag on in birdweather / image mode ⇒ one log line, behaviour identical to off | D2 |
| ″ | `_make_api_handler(..., reset_at_midnight=True)` appends the param once, sets `hours=24`, keeps other params | D3, C8 |
| ″ | `fetch_recent` unchanged; `fetch_recent_payload(..., reset_at_midnight=True)` URL ends `&reset_at_midnight=1` | C7 |
| ″ | flag on: **exactly one** `fetch_recent_payload` call per run and `fetch_species` **not** called | Oracle High |
| ″ | divergence fixture: clamped list differs from the rolling list ⇒ `changed` and the capture both use the clamped list | req 2, 6, 8 |
| ″ | first drawable bird during quiet hours ⇒ skip, no push; the next run outside quiet hours draws | D8 |
| ″ | `--preview` of an empty day ⇒ renders the preview file, never `push_panel`/`save_state` | D1 |
| ″ | flag on, `force=True, use_signature=False` (bundle `use`/`rollback`) with an empty day ⇒ `run()` returns True (bundle kept) | D1 |
| ″ | the flag-on URL and decision do not depend on the frame's clock (patch `time.time`/`datetime` far from the station's day) | brief scenario 9 |

Worker note: flag-on tests must patch `fetch_recent_payload`, not `fetch_species`.
| `tests/test_midnight_reset.php` | none required: the param read is after the library-only guard and the clamp it relies on is already pinned (`:33-36`). If the worker shows upstream's `edu_endpoint` pattern (`tests/test_educator_backend.php:64-76`) runs the full `recent` endpoint with the param cheaply, add one case there; **otherwise W1 must record the gap** (brief scenario 11 — other API clients unchanged — then rests on R1's argument and the `.pi/` R3 scripts). | req 1, 8, brief 11 |

Our own scaffolding stays in `.pi/`: the characterization suite
(`.pi/research/pre-v03/test_characterize_today.py`, 13/13 today) is re-run after the change to show
the intended flips with the flag on and no change with it off; the R3 scripts re-verify the PHP.

## 6. Verification

| Where | What | Notes |
|---|---|---|
| Local (Windows) | `PYTHONPATH=.pi/research/pre-v03/stubs python -m pytest tests/test_frame_capture.py tests/test_frame_birdweather.py` | expected: all new tests pass; the 7 known POSIX-permission failures unchanged |
| Local | `php tests/test_midnight_reset.php`, `php tests/test_site_name_api.php`, R3 scripts | PHP 8.5 via scoop; use a shell opened after the install |
| Local | flake8 with the repo `.flake8` on changed files (fatal set `E9,F63,F7,F82` as CI) | complexity is advisory upstream |
| CI (parent's existing `python-app.yml` on the fork) | `pytest` + `frame-capture` browser job | Linux: real `fcntl`, PHP 8.3/8.5 + SQLite3. **Pushing the feature branch alone triggers nothing** — the workflow runs only on pushes to `main`/`test_me`/`avian-visitors` or PRs into `main`/`avian-visitors`, with no `workflow_dispatch`. Real CI needs an operator-authorised PR *inside the fork* into its `avian-visitors` branch, with Actions enabled on the fork (D21). |
| Hardware (`birdpic`) | mandatory before any upstream PR: flag on over a midnight with silence; a first drawable bird; a flight-only bird alone (if the bundle has one); power-cycle before the first bird; flag off regression | burn-in, real timing and panel behaviour are hardware-only |

Report must name the environment and list what was not executed.

## 7. Execution (one child at a time; no recursive delegation)

Available agents: `scout`, `oracle`, `worker`, `reviewer` (no `tester`). Each `worker` starts
blank: hand it this plan, the relevant knowledge docs and an exact task. Commits are **local**;
nothing is pushed without the operator's say-so.

| Step | Agent | Task | Done when |
|---|---|---|---|
| G0 | operator | authorise building | explicit go-ahead |
| W1 | worker | §4.1 station change | diff = 3 lines in `avian/api/birdnet-api.php`; parent PHP tests + R3 scripts pass |
| W2 | worker | §4.2–4.4 frame change + §5 frame tests | §5 tests pass locally (stub loop); characterization flips as expected |
| W3 | worker | §4.5 docs | README paragraph + config line, end-user voice |
| R | reviewer | review the full diff vs this plan, D20 and every ruling | no unresolved High findings |
| V | parent | §6 local runs; push only if the operator authorises CI on the fork | results recorded in the verification log |
| O | oracle | drift/ruling audit of the result | verdict recorded |
| H | operator + parent | hardware pass on `birdpic` | checklist recorded |

The parent records each step in `.pi/knowledge/verification-log.md`, keeps the register current, and
runs `python .pi/tools/check_kb.py --index` (exit 0) at the end of each session.

## 8. Deployment (after merge to the operator's fork, when authorised)

1. **Station first:** web UI → Tools → Pull latest (otherwise a flag-on frame holds and exits 1, D14).
2. **Frame:** `cd ~/AvianVisitors/frame && git pull --ff-only`.
3. Add `reset_at_midnight = true` to `~/.birdframe/config.toml`. No restart: the timer runs the
   oneshot every 15 min. A manual `display.py --force` will **not** repaint if no drawable bird has
   been heard since midnight — that is intended.
4. Off switch: set it to `false` (or remove it); the next run behaves exactly as before.

## 9. Gates and open items

* **G0 — building not authorised** until the operator says so.
* **Upstream PR:** strip `.pi/` and `AGENTS.md` first (D11c); whether to go upstream at all is
  undecided (D11a). The PR would carry only §4 and §5.
* **Project trust:** approve the prompt so the `kb-document` extension loads (D19).
* **Not researched (operator deselected):** parent CI health; `edu_endpoint` on Windows PHP;
  station-default masks scan; a throwaway spike.
* **CI access (D21, open, needed only at stage V):** may the parent open a PR within the fork into
  its `avian-visitors` branch purely so the parent's existing CI runs?
* **Recorded deviations:** D12 amended for the no-bundle path (§4.4); §4.2 item 2 departs from the
  superseded D17 "flag-only helper" bullet.
* **Line endings:** the repo uses `core.autocrlf=true`; keep files LF and let git normalise.
* **Known residuals:** station-default flight-only species with no frame bundle (§4.4); a tile with a
  mask left unplaced by the packer (pre-existing, Audit 2) — both fail-static, never blank.
