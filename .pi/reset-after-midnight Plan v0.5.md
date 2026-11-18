# BirdFrame midnight reset — Plan v0.5

Repository: `AvianVisitors` (fork `moomoomafia/AvianVisitors`; parent `Twarner491/AvianVisitors`,
push to parent disabled). Branch: `feature/birdframe-midnight-reset`, pushed to `origin` at
`5f90208c` (operator-authorised, 2026-11-17). Product base: `5950f807` (= the parent's tip).
Shipped so far: W1 (`428f3104`, +3/−2 in `avian/api/birdnet-api.php`).

Supersedes [Plan v0.4](reset-after-midnight%20Plan%20v0.4.md) (kept for history, like v0.1–v0.3).
The knowledge base is the source of truth for evidence and rulings:
[`.pi/knowledge/_index.md`](knowledge/_index.md), [decision register](knowledge/open-decisions.md),
[minimal-footprint](knowledge/minimal-footprint.md), [verification log](knowledge/verification-log.md).
Read [AGENTS.md](../AGENTS.md) first.

> **Status (2026-11-17): G0 lifted for W1–W3.** W1 built and reviewed; the K1 Linux test container
> is built and green on HEAD. **Next: P2 (regenerate the handoff from this plan), then W2.**
> V, H, §8 and any further push/PR need separate permission.
>
> **What v0.5 changes, and why.** An **execution-state revision**: §1–§5 (objective, principle,
> requirements, design, tests) are carried over from v0.4 **unchanged**, so the design is identical
> to v0.3. `frame/` and `tests/` are still byte-identical to base, so every `file:line` anchor in
> §4 still holds. v0.4's in-place amendments are folded in cleanly:
>
> 1. **Verification gate (§6):** virtualization works, so the D4 container is the local gate again
>    ([D24](knowledge/open-decisions.md#d24--re-confirm-d4-container-as-the-local-gate-once-virtualization-works)).
>    **K1** (`bash .pi/k1/run.sh [ref]`) runs the parent's suites on Linux; Windows runs are quick
>    pre-checks only. **K2** (fake station + fake panel) follows W2
>    ([D26](knowledge/open-decisions.md#d26--container-scope-phasing-and-build-authorisation)).
> 2. **Execution (§7):** D23 done (`94663e4b`); K1 done; W2's "done when" is a K1 re-run; K2
>    inserted after W2. Container steps are named K1/K2 so they never clash with §5's
>    characterization cases C1–C8.
> 3. **The educator backend suite** is gated as an A/B against the base on Linux: it fails there on
>    the parent's own base because of a parent bug (`avian/api/educator-store.php:263,321`), written
>    up in [bug-d28-educator-store-lost-lock.md](knowledge/bug-d28-educator-store-lost-lock.md)
>    ([D28](knowledge/open-decisions.md#d28--report-the-educator-store-lost-lock-bug-upstream)).
> 4. **Open items (§9)** refreshed: D21, D22, D27, D28 open; D23, D24, D26 answered.
> 5. The branch is **pushed** to `origin` (11 earlier local commits included). Untracked worker
>    files are invisible to K1 (it archives tracked + staged files): W2 must commit its work.
>
> Reviews behind this plan: [Plan v0.3 Oracle review](knowledge/verification-log.md#plan-v03-oracle-review),
> [post-W1 review](knowledge/verification-log.md#post-w1-review-implementation-and-test-coverage),
> [pre-container Oracle review](knowledge/verification-log.md#pre-container-oracle-review),
> [K1 build and baseline](knowledge/verification-log.md#k1-build-and-baseline).

---

## 1. Objective

*(unchanged from v0.3)* Add an optional, per-frame `reset_at_midnight` setting (default off) to
the BirdFrame in `local` mode. When on, the frame shows only birds the **station** heard since the
**station's** midnight. The e-ink panel is never redrawn or blanked because the day rolled over:
yesterday's collage stays until the first bird the frame can actually draw is heard today, which
replaces it with today's birds only. Everything else — and the whole setting off — behaves exactly
as the parent does today.

## 2. Guiding principle (D20)

Align with and default to what the parent repo does; change the smallest amount of code; reuse
upstream mechanisms before adding any; research/A-B when options are close; keep our tooling in
`.pi/`. Target: **5 parent files, ~45–60 changed lines plus tests in the parent's existing test
files** (upstream's own station midnight reset was +112 shipped / +108 test lines).
**Spent so far:** 1 file, +3/−2 (W1).

## 3. Requirements → rulings (all decided; no open design blockers)

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
**D3** additive request param + config toggle `reset_at_midnight`, default `false`; **D4** local gate =
the `.pi/` container (re-confirmed by D24), CI = the parent's existing jobs, no new workflow, hardware
pass mandatory; **D11c** `.pi/` + `AGENTS.md`
are on this branch and must be stripped before any PR to the parent, **and so must the root
`.pi-tasks/`** (D11 amendment, 2026-11-17); **D14** outdated station ⇒ hold + exit 1; **D15**
Educators scope ⇒ hold via the D14 path, **exit 1** (the register's original "exit 0" text is
superseded by its D20 amendment; no dedicated code); **D16** station unreachable ⇒ timer skips
(exit 0), forced run exits 1; **D20** minimal footprint.
Open, non-design: **D21** (CI via a PR inside the fork, stage V), **D22** (commit a parent test for
W1), **D27** (K2's midnight clock), **D28** (report a parent bug; outside the feature). See §9.

## 4. Design

### 4.1 Station — `avian/api/birdnet-api.php` (R1 variant B′) — DONE

**Built 2026-11-17 by W1, local commit `428f3104`** (+3/−2, matches v0.3 verbatim):

```php
// avian/api/birdnet-api.php:136, right after $action (:135)
$resetAtMidnight = $RESET_AT_MIDNIGHT || (($_GET['reset_at_midnight'] ?? null) === '1');
// :170   (($educatorCacheDisabled || $resetAtMidnight) ? 'no-store' : 'public, max-age=30')
// :363   recentWindow($db, $hours, $ctx, $resetAtMidnight, $educatorScope !== null)
```

Facts this relies on (executed, R3): only exact `1` enables it; arrays, `0`, case variants are
ignored; PHP key mangling and last-wins duplicates behave as for every upstream param; a request
can never switch a station-wide ON off; educator scopes still win (`:90`). Requests without the
param are byte-identical to today. The response field `reset_at_midnight` now means "station flag
OR param, not scoped"; the lowercase key was not found in `avian/frontend/apt.js` or `frame/`.

**Evidence (post-W1 review):** `.pi/research/w1/recent_param_probe.php` drives the real `recent`
and `stats` endpoints. It passes 11/11 on HEAD, while exactly the 3 param-dependent checks fail on
base. `tests/test_midnight_reset.php` passes 20 and `tests/test_site_name_api.php` passes 6.
**Not verified:** `Cache-Control: no-store` with the param (CLI exposes no headers). It moves to
the H checklist (§6).

### 4.2 Frame — `frame/display.py` (W2; unchanged from v0.3)

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
   an outdated station can never hide behind an exit-0 decline. Step (c) is also the **only**
   Educators handling (D15): no `educator_scope` branch.
5. `obtain_image` (`:366`) passes `window_hours=24 if active else cfg["hours"]` and
   `reset_at_midnight=active` to `shoot()` (`:395-400`). The birdweather and image branches are
   untouched.

### 4.3 Frame — `frame/shoot.py` (W2; unchanged from v0.3)

`_make_api_handler(..., reset_at_midnight=False)` (`:243`): in the station branch after the existing
`hours` substitution (`:258`), append `reset_at_midnight=1` when asked and not already present.
`shoot(..., reset_at_midnight=False)` (`:412`) threads it to the route at `:448`. This is the
**single** injection point for every page `recent` request (verified, pre-v0.3 item 5); every other
query parameter is preserved verbatim (characterization C8). Upstream's re-sign from the captured
response (`frame/display.py:457-463`) keeps state truthful if the window changes between the fetch
and the capture.

### 4.4 "Drawable" (D12 + R5 amendment; W2; unchanged from v0.3)

* **Frame bundle active** (the operator's setup, D12b): a species is drawable iff the bundle has a
  base pose for it — `"perched"` or `"variant-1"` in `bundle.index["assets"].get(slugify(sci), {})`.
  Equivalent to "its unsuffixed slug is a masks key" (install invariant,
  `frame/bundle_runtime.py:1883-1889`), i.e. exactly the collage's drop test
  (`avian/frontend/apt.js:3164-3186`). **Do not change `ActiveBundle.drawable_slugs`** (species-level;
  upstream BirdWeather filtering depends on it).
* **No frame bundle:** per the **D12 amendment of 2026-11-16** the frame does **not** fetch the
  station's mask table (`avian/frontend/masks.json` is ~800 KB, too heavy every 15 min on a
  Zero 2 W), so only an **empty** today-window declines. The residual risk (a station-default
  flight-only species) is fail-static: panel kept, capture times out, exit 1.

### 4.5 Config and docs (W3)

* `frame/config.example.toml`: add after `hours = 24` (`:26`):
  `# reset_at_midnight = false  # local mode only: show birds since the station's midnight; keeps the`
  `#                             # last collage until today's first drawable bird; needs an updated station`
* `frame/README.md`: one short paragraph **after the bird-names section** — i.e. after the
  `--image-url` labels paragraph (`frame/README.md:89`) and before "When updating a paired mic and
  frame" (`:91`). *(v0.4 correction: v0.3 said `:87`, which is the `shoot_title` line inside that
  section.)* Content: what it does, local mode only, `hours` is ignored while on, update the
  station first, `--force` will not repaint an empty day, set back to `false` to restore today's
  behaviour (no state reset needed). End-user voice, no internals. Also say: with an outdated
  station the frame keeps its collage and reports a failure every 15 minutes (including during
  quiet hours) until the station is updated (D14).

### 4.6 Not changed

`install.sh`, `config_contract.py`, `birdframe-names`, systemd units, `apt.js`, the station's global
setting, any workflow file, `ActiveBundle.drawable_slugs`, signature hashing (D6 dropped),
`state.json` format (D9). **Plus (v0.4):** `avian/api/birdnet-api.php` beyond W1's three lines,
unless the operator picks D22 (a), which touches a *test* file only.

## 5. Tests (in the parent's existing files, in their style)

Frame rows (W2) are **unchanged from v0.3**:

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

PHP row (**replaced in v0.4**; governed by
[D22](knowledge/open-decisions.md#d22--commit-a-parent-test-for-w1s-request-param), open, not
blocking W2):

| Option | What | Trace |
|---|---|---|
| (a) recommended | one clock-independent case in an existing parent PHP test: two `edu_endpoint` calls (`tests/test_educator_backend.php:64-104`) on `recent`, `hours=24`, with and without `reset_at_midnight=1`, asserting only `midnight_clamped` and `window_start` ending `00:00:00` (true at any time of day for today, `avian/api/birdnet-api.php:109-113`). Store provisioned (`educator_store_open(true)`, `:178`), no capture running. | test lines only |
| (b) | record the gap; rely on the `.pi/` probe + R1's argument | none |
| (c) | the full probe as a parent test (time-relative rows need a midnight guard → flake risk) | more test lines |

If (a) is chosen it is a separate small step (**T1**, §7), not part of W2, and must not touch
`avian/api/birdnet-api.php`.

Our own scaffolding stays in `.pi/`: the characterization suite
(`.pi/research/pre-v03/test_characterize_today.py`, 13/13 today) is re-run after W2 to show the
intended flips with the flag on and no change with it off; the R3 scripts and
`.pi/research/w1/recent_param_probe.php` re-verify the PHP.

## 6. Verification

| Where | What | Expected / notes |
|---|---|---|
| **K1: local gate** (Linux container, D24/D26) | `bash .pi/k1/run.sh` (worktree: tracked + staged files) or `bash .pi/k1/run.sh <ref>`. Image: `.pi/k1/Dockerfile` on the parent's pinned `debian:bookworm-slim` (PHP 8.2, Python 3.11, Playwright 1.62.0 + Chromium), non-root user. Tree: `git -c core.autocrlf=false archive` piped into the container, never the bind-mounted CRLF worktree. ~4 min | exit 0 = every named suite passed and none skipped. Suites: PHP syntax, `tests/test_midnight_reset.php` (20), `tests/test_site_name_api.php` (6), `tests/test_educator_backend.php` (A/B: exactly the 18 base lines in `.pi/k1/educator-backend.baseline`), pytest `tests/test_midnight_reset.py`, `tests/test_frame_capture.py` (77 on HEAD before W2), `tests/test_frame_birdweather.py` (18), `tests/test_frame_capture_browser.py` (38), `tests/test_educator_security.py` (7), `frame/test_bundle_runtime.py` (42), the `.pi/` W1 probe, R3 clamp and characterization suites, flake8 fatal set |
| **K2** (after W2; needs D27) | fake station (`php -S`, copied tree, provisioned Educators lock, synthetic `birds.db`) + headless fake `inky` + midnight scenarios | push/no-push asserted on the fake panel; still not the real glass |
| Windows pre-check | `PYTHONPATH=.pi/research/pre-v03/stubs python -m pytest tests/test_frame_capture.py tests/test_frame_birdweather.py`; scoop PHP for the PHP suites (stale shell: export `PHP_INI_SCAN_DIR`, recipe in [testing-and-ci.md](knowledge/testing-and-ci.md)) | fast feedback only; 7 POSIX-permission failures and 14/199 educator failures are Windows-only artefacts; **not evidence** |
| Local | flake8 with the repo `.flake8` on changed files | complexity is advisory upstream (`run()` is 18 on base) |
| CI (parent's existing `python-app.yml` on the fork) | `pytest` + `frame-capture` browser job | runs only on `main`/`test_me`/`avian-visitors` pushes or PRs; **the feature-branch push triggers nothing**. Real CI needs an operator-authorised PR *inside the fork* (D21) |
| Hardware (`birdpic`) | mandatory before any upstream PR: flag on over a midnight with silence; a first drawable bird; a flight-only bird alone (if the bundle has one); power-cycle before the first bird; flag off regression; `curl -sI '<station>/avian/api/birdnet-api.php?action=recent&hours=24&reset_at_midnight=1'` shows `Cache-Control: no-store` (without the param: `public, max-age=30`, unless Educators is enabled); record the station's PHP version (D28) | burn-in, real timing, real SAPI headers and panel behaviour are hardware-only |

Every report names the environment and lists what was not executed.

## 7. Execution (one child at a time; no recursive delegation)

Available agents: `scout`, `oracle`, `worker`, `reviewer` (no `tester`). Commits are **local**;
pushing needs the operator's say-so each time. **`defaultReads` is rejected by this install's
`subagent` tool**; pin the full `.pi/handoff/...` paths in the task text. Workers stage explicit
`frame/` and `tests/` paths only (never `-a`, `-A`, `-u`) and **commit** their work (K1 cannot see
untracked files).

| Step | Agent | Task | Status / done when |
|---|---|---|---|
| G0 | operator | authorise building | **done 2026-11-17** (W1–W3) |
| W1 | worker | §4.1 station change | **done**, `428f3104`; verified by the parent (post-W1 review) and K1 |
| K1 | parent | `.pi/` Linux test container | **done**; base and HEAD baselines recorded ([K1 log](knowledge/verification-log.md#k1-build-and-baseline)) |
| P2 | parent | regenerate `.pi/handoff/plan.md` + `context.md` from **this v0.5**, header rule "where verbatim ruling text conflicts with §4, §4 wins"; update the ledger | handoff names v0.5; working tree has no stray tracked changes |
| W2 | worker | §4.2–4.4 frame change + §5 frame tests, one local commit | parent re-runs K1: new tests pass, nothing else changes against the K1 HEAD baseline; characterization flips as expected with the flag on and nothing changes with it off |
| K2 | parent | fake station + fake panel + scenarios | needs D27; the midnight scenarios assert push/no-push |
| W3 | worker | §4.5 docs | README paragraph at `frame/README.md:89`/`:91` + config line, end-user voice |
| T1 | worker | only if D22 = (a): one PHP case per §5 | case passes on HEAD, fails on base `5950f807` (K1 A/B) |
| R | reviewer | review the full diff vs this plan, D20 and every ruling | no unresolved High findings |
| V | parent | §6 runs; CI only if the operator authorises it on the fork (D21) | results recorded in the verification log |
| O | oracle | drift/ruling audit of the result | verdict recorded |
| H | operator + parent | hardware pass on `birdpic` (§6) | checklist recorded |

G0 covers W1–W3 only. Whether T1 falls under it is part of the D22 ruling. The parent records
each step in `.pi/knowledge/verification-log.md`, keeps the register and `.pi/handoff/ledger.md`
current, and runs `python .pi/scripts/check_kb.py --index` (exit 0) at the end of each session.

## 8. Deployment (after merge to the operator's fork, when authorised)

*(unchanged from v0.3)*

1. **Station first:** web UI → Tools → Pull latest (otherwise a flag-on frame holds and exits 1, D14).
2. **Frame:** `cd ~/AvianVisitors/frame && git pull --ff-only`.
3. Add `reset_at_midnight = true` to `~/.birdframe/config.toml`. No restart: the timer runs the
   oneshot every 15 min. A manual `display.py --force` will **not** repaint if no drawable bird has
   been heard since midnight — that is intended.
4. Off switch: set it to `false` (or remove it); the next run behaves exactly as before.

## 9. Gates and open items

* **G0 lifted 2026-11-17** (W1–W3; V and H separately gated).
* **Answered 2026-11-17:** D23 (`.pi/` committed before W2, `94663e4b`), D24 (Docker container is the
  local gate), D26 (K1 now, K2 after W2).
* **Open:**
  * **D22** (not blocking W2): commit a parent test for W1 (§5 PHP row, step T1).
  * **D27** (blocks K2 only): how K2 makes "just after midnight" happen. Recommended: a per-run
    POSIX `TZ` offset (verified for SQLite, PHP's SQLite and Python; **Chromium ignores it**).
  * **D21** (stage V only): CI via a PR inside the fork into its `avian-visitors`.
  * **D28** (outside the feature): file the parent-bug issue; draft ready in
    [bug-d28-educator-store-lost-lock.md](knowledge/bug-d28-educator-store-lost-lock.md).
* **Upstream PR:** strip `.pi/`, `AGENTS.md` **and the root `.pi-tasks/`** first (D11c + its
  2026-11-17 amendment); whether to go upstream at all is undecided (D11a). The PR would carry
  only §4 and §5.
* **Not researched (operator deselected):** parent CI health; station-default masks scan; a
  throwaway spike.
* **Recorded deviations:** D12 amended for the no-bundle path (§4.4); §4.2 item 2 departs from the
  superseded D17 "flag-only helper" bullet; §4.5 README anchor corrected (v0.4).
* **Line endings:** `core.autocrlf=true` comes from the system gitconfig; keep files LF and let git
  normalise. Linux runs use K1's archive, never the worktree.
* **Known residuals:** station-default flight-only species with no frame bundle (§4.4); a tile with a
  mask left unplaced by the packer (pre-existing, Audit 2) — both fail-static, never blank;
  Cache-Control with the param unverified until H.
