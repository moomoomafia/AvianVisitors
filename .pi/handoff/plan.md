# Worker handoff plan — BirdFrame midnight reset (Plan v0.5, step W2R)

Regenerated 2026-11-17 by the parent with `.pi/scripts/build_handoff.py` from
`.pi/reset-after-midnight Plan v0.5.md` (§3–§9 verbatim, including the §4.7 review-R amendments) and
`.pi/knowledge/open-decisions.md` (rulings verbatim). Never use the edit-surface table in
`.pi/knowledge/feature-midnight-reset.md` (superseded).

## Precedence rule (read first)

**Where a verbatim ruling body below conflicts with Plan §4, §4 wins**, and **§4.7 wins over the
earlier §4.2/§4.3/§4.5 text it amends.** Example: D15 holds via the D14 path with **exit 1**. If §4
itself proves unimplementable, stop and report — do not deviate or redesign.

## Authorisation and your task

G0 (operator, 2026-11-17) authorises W1–W3; W2R fixes review findings in W2/W3 and is within it.
Done: W1 (`428f3104`), W2 (`dece12cf`), W3 (`ec5cdc7d`). **Your task is W2R only: implement §4.7
items 1–5** (code, tests, docs) with the smallest diff. Not T1, not K2. Stages V and H, §8
deployment, any push or PR are **not** authorised. The review behind §4.7 is in
`.pi/knowledge/verification-log.md`, section "Review R: full product diff".

## Commit rules

* Stage **explicit paths only**: `git add frame/display.py tests/test_frame_capture.py frame/README.md frame/config.example.toml`
  (and `frame/shoot.py` only if genuinely needed — say why). Never `git add -A`, `-a`, `-u`,
  `git commit -a`, `git clean`, `git stash`.
* Make **one local commit** (style: `fix(frame): …`). No push.
* Do not touch `.pi/`, `AGENTS.md`, `.pi-tasks/`, `avian/`, or anything in §4.6.

## Open questions you must NOT decide

D21, D22, D27, D28 (see §9). None blocks W2R. If you hit a new design question, stop and report it.

## Plan §3–§7 (verbatim)

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

### §4. Design

#### 4.1 Station — `avian/api/birdnet-api.php` (R1 variant B′) — DONE

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

#### 4.2 Frame — `frame/display.py` (W2; unchanged from v0.3)

> **Amended 2026-11-17 by review R** (see §4.7): step (b) for preview, step (e)'s shape, the
> "ignored" line, and a new step (f) after the capture. The original text below is kept.

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

#### 4.3 Frame — `frame/shoot.py` (W2; unchanged from v0.3)

`_make_api_handler(..., reset_at_midnight=False)` (`:243`): in the station branch after the existing
`hours` substitution (`:258`), append `reset_at_midnight=1` when asked and not already present.
`shoot(..., reset_at_midnight=False)` (`:412`) threads it to the route at `:448`. This is the
**single** injection point for every page `recent` request (verified, pre-v0.3 item 5); every other
query parameter is preserved verbatim (characterization C8). Upstream's re-sign from the captured
response (`frame/display.py:457-463`) keeps state truthful if the window changes between the fetch
and the capture. *Amended 2026-11-17 (review R, F1): truthful state is not enough. If the station
passes midnight between the fetch and the page's request, the capture is an empty nest and would be
pushed; §4.7 step (f) declines it.*

#### 4.4 "Drawable" (D12 + R5 amendment; W2; unchanged from v0.3)

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

#### 4.5 Config and docs (W3)

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

#### 4.7 Review-R amendments (2026-11-17, step W2R)

From [review R](../knowledge/verification-log.md#review-r-full-product-diff); each finding was
re-checked against source by the parent. They implement existing rulings (D1, D14, D20); no new
design choice.

1. **Step (f), post-capture decline (F1, High).** After `obtain_image` succeeds and before
   `mat_and_center`/preview/push: if `active and not preview and "species" in capture and not
   has_drawable_bird(capture["species"], bundle)`, print the step (d) line and **return True** (no
   push, no `save_state`). Evidence: `frame/shoot.py:66-75` accepts an empty collage;
   `frame/display.py:506-520` re-signs and pushes; `frame/systemd/birdframe.timer:11` is phase-free.
   Test: the flag-on stub captures a list that differs from the decided one (`[]`) ⇒ `run()` True,
   no push, no save.
2. **Step (b) and preview (F2).** `return not (force or preview) and use_signature`: a preview whose
   fetch failed reports failure (as the flag-off path does) instead of exiting 0 with no file.
3. **Step (e) shape (F4, D20; also fixes F3).** Remove the duplicated signature/salt lines from the
   `if active:` block and restore the upstream `if use_signature:` (not `elif`); change only its
   first statement to `species = species if active else fetch_species(...)`. Flag off: identical
   (`active` is False). Flag on: still one fetch, `fetch_species` not called, and a malformed entry
   is caught by the upstream `try` as "signature fetch failed".
4. **"Ignored" line (F7).** Print it only when `cfg.get("reset_at_midnight") is True and not active`.
5. **Docs (F5, F6).** README: add that with an outdated mic (or an active Educators capture) bundle
   switches are undone until the mic is updated (D14's required sentence).
   `frame/config.example.toml`: say "mic", not "station" (that file's "station" is BirdWeather).

#### 4.6 Not changed

`install.sh`, `config_contract.py`, `birdframe-names`, systemd units, `apt.js`, the station's global
setting, any workflow file, `ActiveBundle.drawable_slugs`, signature hashing (D6 dropped),
`state.json` format (D9). **Plus (v0.4):** `avian/api/birdnet-api.php` beyond W1's three lines,
unless the operator picks D22 (a), which touches a *test* file only.

### §5. Tests (in the parent's existing files, in their style)

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
[D22](../knowledge/open-decisions.md#d22--commit-a-parent-test-for-w1s-request-param), open, not
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

### §6. Verification

| Where | What | Expected / notes |
|---|---|---|
| **K1: local gate** (Linux container, D24/D26) | `bash .pi/k1/run.sh` (worktree: tracked + staged files) or `bash .pi/k1/run.sh <ref>`. Image: `.pi/k1/Dockerfile` on the parent's pinned `debian:bookworm-slim` (PHP 8.2, Python 3.11, Playwright 1.62.0 + Chromium), non-root user. Tree: `git -c core.autocrlf=false archive` piped into the container, never the bind-mounted CRLF worktree. ~4 min | exit 0 = every named suite passed and none skipped. Suites: PHP syntax, `tests/test_midnight_reset.php` (20), `tests/test_site_name_api.php` (6), `tests/test_educator_backend.php` (A/B: exactly the 18 base lines in `.pi/k1/educator-backend.baseline`), pytest `tests/test_midnight_reset.py`, `tests/test_frame_capture.py` (77 on HEAD before W2), `tests/test_frame_birdweather.py` (18), `tests/test_frame_capture_browser.py` (38), `tests/test_educator_security.py` (7), `frame/test_bundle_runtime.py` (42), the `.pi/` W1 probe, R3 clamp and characterization suites, flake8 fatal set |
| **K2** (after W2; needs D27) | fake station (`php -S`, copied tree, provisioned Educators lock, synthetic `birds.db`) + headless fake `inky` + midnight scenarios | push/no-push asserted on the fake panel; still not the real glass |
| Windows pre-check | `PYTHONPATH=.pi/research/pre-v03/stubs python -m pytest tests/test_frame_capture.py tests/test_frame_birdweather.py`; scoop PHP for the PHP suites (stale shell: export `PHP_INI_SCAN_DIR`, recipe in [testing-and-ci.md](../knowledge/testing-and-ci.md)) | fast feedback only; 7 POSIX-permission failures and 14/199 educator failures are Windows-only artefacts; **not evidence** |
| Local | flake8 with the repo `.flake8` on changed files | complexity is advisory upstream (`run()` is 18 on base) |
| CI (parent's existing `python-app.yml` on the fork) | `pytest` + `frame-capture` browser job | runs only on `main`/`test_me`/`avian-visitors` pushes or PRs; **the feature-branch push triggers nothing**. Real CI needs an operator-authorised PR *inside the fork* (D21) |
| Hardware (`birdpic`) | mandatory before any upstream PR: flag on over a midnight with silence; a first drawable bird; a flight-only bird alone (if the bundle has one); power-cycle before the first bird; flag off regression; `curl -sI '<station>/avian/api/birdnet-api.php?action=recent&hours=24&reset_at_midnight=1'` shows `Cache-Control: no-store` (without the param: `public, max-age=30`, unless Educators is enabled); record the station's PHP version (D28) | burn-in, real timing, real SAPI headers and panel behaviour are hardware-only |

Every report names the environment and lists what was not executed.

### §7. Execution (one child at a time; no recursive delegation)

Available agents: `scout`, `oracle`, `worker`, `reviewer` (no `tester`). Commits are **local**;
pushing needs the operator's say-so each time. **`defaultReads` is rejected by this install's
`subagent` tool**; pin the full `.pi/handoff/...` paths in the task text. Workers stage explicit
`frame/` and `tests/` paths only (never `-a`, `-A`, `-u`) and **commit** their work (K1 cannot see
untracked files).

| Step | Agent | Task | Status / done when |
|---|---|---|---|
| G0 | operator | authorise building | **done 2026-11-17** (W1–W3) |
| W1 | worker | §4.1 station change | **done**, `428f3104`; verified by the parent (post-W1 review) and K1 |
| K1 | parent | `.pi/` Linux test container | **done**; base and HEAD baselines recorded ([K1 log](../knowledge/verification-log.md#k1-build-and-baseline)) |
| P2 | parent | regenerate `.pi/handoff/plan.md` + `context.md` from **this v0.5**, header rule "where verbatim ruling text conflicts with §4, §4 wins"; update the ledger | handoff names v0.5; working tree has no stray tracked changes |
| W2 | worker | §4.2–4.4 frame change + §5 frame tests, one local commit | parent re-runs K1: new tests pass, nothing else changes against the K1 HEAD baseline; characterization flips as expected with the flag on and nothing changes with it off |
| K2 | parent | fake station + fake panel + scenarios | needs D27; the midnight scenarios assert push/no-push |
| W3 | worker | §4.5 docs | README paragraph at `frame/README.md:89`/`:91` + config line, end-user voice |
| W2R | worker | §4.7 review-R fixes (F1, F2, F4, F7 code + tests; F5, F6 docs), one local commit (added 2026-11-17) | parent re-runs K1; the F1 test fails on `ec5cdc7d` and passes after; flag-off behaviour unchanged |
| T1 | worker | only if D22 = (a): one PHP case per §5 | case passes on HEAD, fails on base `5950f807` (K1 A/B) |
| R | reviewer | review the full diff vs this plan, D20 and every ruling | no unresolved High findings |
| V | parent | §6 runs; CI only if the operator authorises it on the fork (D21) | results recorded in the verification log |
| O | oracle | drift/ruling audit of the result | verdict recorded |
| H | operator + parent | hardware pass on `birdpic` (§6) | checklist recorded |

G0 covers W1–W3 only. Whether T1 falls under it is part of the D22 ruling. The parent records
each step in `.pi/knowledge/verification-log.md`, keeps the register and `.pi/handoff/ledger.md`
current, and runs `python .pi/scripts/check_kb.py --index` (exit 0) at the end of each session.

## Plan §9 (verbatim)

### §9. Gates and open items

* **G0 lifted 2026-11-17** (W1–W3; V and H separately gated).
* **Answered 2026-11-17:** D23 (`.pi/` committed before W2, `94663e4b`), D24 (Docker container is the
  local gate), D26 (K1 now, K2 after W2).
* **Open:**
  * **D22** (not blocking W2): commit a parent test for W1 (§5 PHP row, step T1).
  * **D27** (blocks K2 only): how K2 makes "just after midnight" happen. Recommended: a per-run
    POSIX `TZ` offset (verified for SQLite, PHP's SQLite and Python; **Chromium ignores it**).
  * **D21** (stage V only): CI via a PR inside the fork into its `avian-visitors`.
  * **D28** (outside the feature): file the parent-bug issue; draft ready in
    [bug-d28-educator-store-lost-lock.md](../knowledge/bug-d28-educator-store-lost-lock.md).
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

## Rulings (verbatim from `.pi/knowledge/open-decisions.md`)

### D1 — May a forced render draw an empty today-window collage?

**Status:** `ANSWERED 2026-11-16`

> **Ruling:** **Decline on all forced paths.** Retention is a property of the *data*, not
> of the trigger. Every forced path declines, **exits 0**, and logs a line. `--preview`
> still renders for inspection.

Consequences the implementation must honour:

* The guard runs **before** capture, so a doomed refresh never burns a 70–120 s Chromium
  render on a Zero 2 W.
* Covers `--force`, `--no-signature`, `avian-bundle use` (when the selection changed),
  `avian-bundle rollback` (unconditional), and `birdframe-names on|off`.
* Exit **0** is not cosmetic: a non-zero exit makes `use`/`rollback` revert the bundle
  selection and re-render (`frame/bundle_runtime.py:1962-1972`).
* Logs must be greppable and calm — one line, not a stack trace, because this fires on
  every poll during a silent stretch.
* Requirement 12 (disabled ⇒ unchanged) is separate: with `reset_at_midnight = false` this
  guard must not exist at all, not merely be false.

Original options retained below for the record.

The brief says never overwrite the retained collage with a blank screen (req 9) and
that heal must not clear it (req 10). It does not say what an *explicit* render should
do, and there are four forced paths plus a fifth that nobody asked for:

| Path | Source |
|---|---|
| `display.py --force` (documented in `frame/README.md` as the standard post-`git pull` step) | `frame/display.py:446` |
| `--no-signature` (forces `changed = True`) | `display.py:445` |
| `avian-bundle use` when the selection changed | `bundle_runtime.py:1953-1955,1962-1963` |
| `avian-bundle rollback` — renders unconditionally | `bundle_runtime.py:1993-1997` |
| `birdframe-names on\|off` | `frame/birdframe-names:63-68` |

Options:
1. **Decline on every forced path** (recommended): the retention rule is a property of
   the *data*, not of the trigger. Exit **0** — a non-zero exit makes `use`/`rollback`
   revert the bundle selection and re-render (`bundle_runtime.py:1962-1972`), silently
   undoing the user's request.
2. Honour `--force` literally: an explicit `--force` draws whatever the window holds,
   including the empty nest; the automatic paths (bundle, names) still decline.
3. Only the gate declines; all forced paths draw (this is the naive reading of the
   brief and it wipes walls).

Consequence if unanswered: a Worker implements the gate only, which satisfies the letter
of req 9 for timer runs and blanks the panel on every `git pull` + `--force` update.
`--preview` is deliberately outside this decision — it cannot touch the panel
(`display.py:469-474`) and must keep rendering for inspection.

### D2 — Which frame modes does the feature apply to?

**Status:** `ANSWERED 2026-11-16`

> **Ruling:** **`local` mode only.** `birdweather` and `image` modes are documented as
> unsupported, mirroring the existing bundle caveat at `frame/display.py:402-405`.

What that means concretely:

* The clamp param and the retention guard activate **only** when
  `species_source` is empty (station-backed `local` mode).

  > **Amended 2026-11-16 (Audit 2, F-M1):** the test above is wrong — `image`/`image_url`
  > frames *also* have an empty `species_source` (`display.py:44,406-416`). The correct
  > activation test is **`cfg.get("species_source") != "birdweather" and cfg.get("shoot") is True`**,
  > the same predicate the codebase already uses to mean "this Pi renders the station"
  > (`frame/bundle_runtime.py:433,474`; `frame/config_contract.py:75`). The ruling itself (local only)
  > is unchanged.
* `birdweather` mode keeps `bw_days` semantics untouched — no BirdWeather parameter is
  changed, and its radius/triangulate/eBird fallback chain is out of scope.
* `image` / `image_url` modes keep fetching `recent` for the signature exactly as today;
  they do **not** send the param. Document that such a frame shows whatever its source
  rendered — same wording pattern the README already uses for bundles and for `labels=`.
* Worth a test: `reset_at_midnight = true` with `species_source = "birdweather"` must be a
  no-op (or a startup warning), not a silent partial effect. Decide which in the PR;
  a logged warning fits the house style better than silence.

Original options retained below for the record.

The brief is written entirely in terms of the BirdNET station window, but the frame has
three sources.

| Mode | Today-only meaningful? | Note |
|---|---|---|
| `local` | Yes | the whole brief |
| `birdweather` (`zip` / `bw_station_id`, `bw_days = 7`) | Different data source | "midnight" would have to be redefined against BirdWeather; its radius-growth / triangulate / eBird fallback chain would need to change too |
| `image_url` / `image` | No | pixels come from someone else's render; the frame still calls `fetch_recent(base_url)` for the signature (`display.py:430-443`) but cannot control what produced the image |

Options: **(A) `local` only**, other modes documented as unsupported — mirrors the
existing precedent at `display.py:402-405` ("an active illustration bundle requires
local or BirdWeather render mode"). (B) `local` + `birdweather` with a redefined window.
(C) All modes.

Recommendation: **(A)**. Consequence if unanswered: a mode-blind Task A can "make it
work" by mutating BirdWeather parameters — an unrequested behaviour change in a service
the brief never mentions.

### D3 — Station API: additive request param, name and shape?

**Status:** `ANSWERED 2026-11-16`

> **Ruling:** **Additive param + the frame serves its own list to the browser.**
> Operator condition attached, quoted: *"As long as in the config.toml file the user is
> able to define if this feature is turned on or off. As not all users will want this
> behavior."*

That condition is a hard requirement, not a preference — record it in every handoff:

* **`reset_at_midnight` lives in `~/.birdframe/config.toml`, defaults to `false`.** The
  station's own `RESET_AT_MIDNIGHT` stays untouched, so the feature is per-frame: two
  frames on one station can disagree, which is exactly what the request-scoped design
  allows (`recentWindow` already takes the flag per call).
* Default off ⇒ existing installs are bit-identical after an update: no new param on the
  wire, no new hash material, no new guard. This is requirement 12 satisfied by default.
* Must be documented in `frame/config.example.toml` next to `hours = 24` and in
  `frame/README.md` in end-user prose — including that it needs an updated station, and
  that flipping it back to `false` needs no `state.json` reset.
* Consider whether it deserves a companion CLI like `birdframe-names` (edit config →
  `display.py --force`). **Rejected here**: under D1 a forced render during an empty
  today-window declines, so such a command would silently not repaint. Document the
  config edit instead, and note this interaction so nobody "fixes" it later.

Mechanics (unchanged from the recommendation):

* Strict scalar param; absent ≠ false ≠ true; ignore PHP-folded aliases
  (`educator_scope_raw_parameter_count`, `avian/api/educator-scope.php:28-48`).
* `case 'recent'` only; `$scoped` still ignores display preferences; `hours >= 1000000`
  and historical `?date=` preserved; clamped response `no-store`; requests without the
  param keep today's `public, max-age=30`.
* Window form: `Date = :station_date AND DATETIME(Date||' '||Time) <= :anchor`.
* The frame serves its own fetched list to the browser (the `birdweather`-proven pattern,
  `frame/shoot.py:243-257`), which makes signature/pixel agreement structural rather than a
  two-place param injection. Note this removes no user control: the frame already rewrites
  `hours=` in the intercepted request (`shoot.py:259`), so the site's window picker has
  never driven the collage.

> **Amended 2026-11-16 (Audit 2).** The ruling stands; four mechanics bullets above were
> wrong or underspecified:
>
> 1. **Param values (F-M6):** not tri-state. Only the exact scalar `1` has an effect;
>    anything else (absent, `0`, arrays, folded aliases) is treated as absent.
>    *Amended by D20/R1 (2026-11-16):* "folded aliases … treated as absent" is **dropped**.
>    Upstream's idiom `($_GET['x'] ?? null) === '1'` rejects absent, `0`, other strings and
>    arrays, but honours PHP key mangling (`reset.at.midnight=1`) and last-wins duplicates,
>    exactly like every other upstream param. Harmless: the param only selects a read-only
>    display window and any client can send the canonical name. See the R1 brief, E8. A `=0` must
>    never be able to override the station's global flag — no requirement asks for that.
> 2. **Caching:** "requests without the param keep `public, max-age=30`" is wrong — the
>    global flag and Educators mode already force `no-store` (`avian/api/birdnet-api.php:165-171`).
>    Correct wording: *requests without the param get exactly today's headers*. Note
>    `Cache-Control` is sent at `:169-171`, **before** the `switch`, so `case 'recent'` must
>    re-send `no-store` when it honours the param.
> 3. **Window form:** contradicts "reuse `recentWindow`" elsewhere in the docs, and the two
>    differ whenever `hours < 24` or `hours = 1000000`. **Moved to D13 (OPEN).**
> 4. **Served list:** the `birdweather` pattern is *not* drop-in for `local` mode. It
>    answers `recent` with only `{hours, species, as_of}` (dropping `site_name`,
>    `educator_scope`) and answers every other action with `{}` (`shoot.py:250-256`).
>    The local-mode variant is specified in **D17**.

Original options retained below for the record.

The brief calls an API change optional; the constraints make one effectively necessary
([verification-log.md](../knowledge/verification-log.md) claims 5 and 7). If accepted:

* **Name:** `reset_at_midnight=1` (matches the existing config vocabulary and the
  `reset_at_midnight` response field) vs a more neutral `window=today`. Upstream PR
  review may prefer the former; a station operator reading logs will too.
* **Shape:** strict scalar; absent ≠ false ≠ true; must ignore PHP-folded aliases
  (`key[]`, `key\0`) — precedent `educator_scope_raw_parameter_count`
  (`avian/api/educator-scope.php:28-48`).
* **Scope:** `case 'recent'` only; `stats`/`hourly`/`rhythm`/`windowClause` untouched;
  educator `$scoped` must keep ignoring display preferences; `hours >= 1000000` and
  historical `?date=` behaviour preserved.
* **Window form:** `Date = :station_date AND DATETIME(Date||' '||Time) <= :anchor`
  (keep the ceiling at `birdnet-api.php:89`).
* **Caching:** clamped response `no-store` or at minimum its own cache key; requests
  without the param must keep today's `public, max-age=30`.

The alternative that avoids touching PHP entirely — serving the frame's own fetched list
to the browser in `local` mode, the pattern `birdweather` already uses
(`shoot.py:243-257`) — is **also a decision under D3**, because it changes where the
truth comes from. Recommendation: additive param, and evaluate the list-serving variant
as the mechanism that keeps signature and image structurally in sync.

Consequence if unanswered: two Workers can implement two different contracts (API param
vs frame-only), and the Phase 4 review has nothing to check against.

### D12 — What does "nothing to draw" mean for the D1 decline?

**Status:** `ANSWERED 2026-11-16` (via sub-rulings D12a–c below)

Asked in small guiding steps (operator preference, 2026-11-16):

* **D12a — UX, `ANSWERED 2026-11-16`.** Q: "After midnight, the first bird heard today has
  no picture. What should the wall show?" Ruling: **"Keep yesterday's collage"** — treat
  *only undrawable birds* exactly like *no birds yet*; the wall changes on the first
  *drawable* bird. (Rejected: showing a 'listening' card, which would blank the wall.)
* **D12b — operator's setup, `ANSWERED 2026-11-16`.** Q: "Have you run
  `sudo avian-bundle use <BUNDLE_ID>` on the frame?" Answer: **"Yes, the frame has its own
  bundle."** ⇒ the primary path is exact: filter today's species by the active frame bundle's
  `drawable_slugs` (`frame/bundle_runtime.py:2023-2025`). The no-frame-bundle path (station
  mask table via `avian/api/bundle-assets.php`) is still supported, but tested second.
* **D12c — fallback, `ANSWERED 2026-11-16`.** Q: "If the frame can't tell which birds are
  drawable, what should it do?" Ruling: **"Behave like today"** — attempt the draw; worst
  case is today's fail-static behaviour (wall unchanged, retry later). Never blanks the wall.

**Combined ruling:** with `reset_at_midnight` on, decline (exit 0, no capture, no
`save_state`) when today's window contains **no drawable species**; drawable = frame-bundle
`drawable_slugs` when a frame bundle is active, else the station's mask table; if the
drawable set can't be determined, proceed as today.

> **Amended 2026-11-16 by R5 (`PARENT-DECIDED`, refines "drawable"; [R5 brief](../outputs/r5-drawable-base-pose.md), [R5](../knowledge/verification-log.md#r5-drawable-vs-base-pose-deep-research-brief--reviewer--live-feed-scan)).**
> "Drawable" now means what the collage actually draws on every capture: **some species in
> today's window has its unsuffixed slug as a key in the masks table the collage will load**
> (frame bundle: a `perched` or `variant-1` pose; station default: `slug in MASKS`, no suffix
> stripping, masks not dims). *Basis:* the collage draws only the base pose or `-2` and drops the
> tile otherwise (`avian/frontend/apt.js:3164-3186`; pose 2 only on a 15% roll); no validator
> requires a base pose; and an installable bundle in the live community feed
> (`community-peterdeboer-nl-cacd91aeb7749fec`) has **22 flight-only species**, which the
> species-level `drawable_slugs` would call drawable while the capture hangs on ~85% of runs.
> This implements D12a's ruling ("keep yesterday's collage" until the wall can show today's
> bird) more faithfully; it does not change it. Computed locally — **`ActiveBundle.drawable_slugs`
> stays species-level** (upstream uses it for BirdWeather filtering).

> **Amended 2026-11-16 after the [Plan v0.3 Oracle review](../knowledge/verification-log.md#plan-v03-oracle-review) (`PARENT-DECIDED`, no-bundle path only).**
> With **no frame bundle**, the frame does **not** fetch the station's mask table: only an
> **empty** today-window declines; every listed species counts as drawable. *Basis:* D20 (the
> station table `avian/frontend/masks.json` is ~800 KB — too heavy to fetch every 15 minutes on
> a Zero 2 W) and D12b (the operator's frame has its own bundle, where the exact base-pose test
> applies). The "else the station's mask table" clause above and the R5 "station default:
> `slug in MASKS`" clause are **superseded for the frame**. Residual risk (a station-default
> flight-only species, no frame bundle) is fail-static: panel kept, capture times out, exit 1.

**Why it blocks:** D1 as written declines on an *empty* list. But a non-empty list can be
undrawable: in `local` mode `fetch_species` ignores `drawable` (`frame/display.py:132-150`),
`renderCollage` drops tiles with no mask (`avian/frontend/apt.js:3179,3186`; cited as `:3181-3190`
before R5), and with zero placed tiles
`finishFrameRender` is never called (`apt.js:3359`) — so `FRAME_READY` never fires, capture
runs the full 180 s deadline, and the run **exits 1**: every timer cycle, and under
`avian-bundle use`/`rollback` exit 1 **reverts the bundle**. Pre-existing for rolling
windows; today-only makes it common because a day's first detection is often a single
(nocturnal) species. Mixed lists are fine (only drawn tiles are counted).

**Where a local frame can learn the drawable set:**

* Frame bundle active: exact — `bundle.drawable_slugs` (`frame/bundle_runtime.py:2023-2025`).
  *(Corrected by R5: species-level, so not exact — use the base-pose / masks-key test above.)*
* No frame bundle: the station's tables — `avian/frontend/masks.json` (`apt.js:1294`) or, if the station
  selected a bundle, `avian/api/bundle-assets.php`'s active `masks` table
  (`avian/api/bundle-assets.php:41,106`). The frame clone's own `avian/frontend/dims.json` is the **wrong**
  source (different checkout, possibly different version).

**Options:**

1. **Decline when no species in today's window is drawable** (recommended). Frame bundle ⇒
   filter by `drawable_slugs`; no bundle ⇒ read mask keys from the station's
   `bundle-assets.php` only when a capture is about to run; if that read fails, fall back
   to today's behaviour. Flag-gated only.
2. Keep "empty list only", and document the exit-1 storm + bundle-revert risk.

**Consequence if unanswered:** the first un-illustrated bird after midnight produces a
3-minute failed render every 15 minutes until a drawable bird arrives (req 6 delayed),
and any bundle switch in that window is silently undone.

### D13 — Does the today-window respect the `hours` setting?

**Status:** `ANSWERED 2026-11-16`

> **Amended by [D20](../knowledge/open-decisions.md#d20--guiding-principle-minimal-footprint-aligned-with-the-parent-repo) (2026-11-16) — implementation only; the UX ruling stands.** Instead of a new
> SQL branch, reuse upstream `recentWindow`: the frame sends `hours=24` plus the param, and with a
> 24-hour window on today's anchor the clamp always applies (`anchor − 24h` < `start of day`), which
> is exactly "everything since midnight". Upstream already pins it ("24 hour window clamps after
> midnight", `tests/test_midnight_reset.php`). No new SQL, no echo fields. See [minimal-footprint.md](../knowledge/minimal-footprint.md).

> **Ruling:** **"Everything since midnight."** Asked as: *"With midnight reset turned on,
> which birds should the wall show during the day?"* — with reset on, the frame **ignores
> `hours`** and shows the whole station calendar day up to the anchor. Implementation
> consequence (from the recommendation): a separate branch
> `Date = :station_date AND DATETIME(Date||' '||Time) <= :anchor`, leaving `recentWindow` and
> its pinned test untouched; echo `window_start = "<date> 00:00:00"` and
> `midnight_clamped: true`. README must say `hours` is ignored while reset is on. The DST
> test cases drop out (no time arithmetic).

Original analysis retained below.

**Why it blocks:** the docs specify two contracts. `recentWindow` gives *intersection(last
`hours`, today)* and only clamps when `rolling <= midnight` (`avian/api/birdnet-api.php:104-116`;
pinned by "short window inside the day stays rolling", `tests/test_midnight_reset.php:38-40`).
The `Date = :station_date AND … <= :anchor` form ignores `hours`. They agree for
`hours >= 24`, differ for smaller values late in the day and for `hours = 1000000`.
`hours` is user-settable (`frame/display.py:51`).

**Options:**

1. **Ignore `hours` when the flag is on** (recommended): window = the station's calendar
   day up to the anchor. Only this satisfies req 1 ("starting at 00:00") literally. Implement
   as a **separate branch**, leaving `recentWindow` and its pinned test untouched; echo
   `window_start = "<date> 00:00:00"` and `midnight_clamped: true` so `avian/frontend/apt.js`'s
   "since midnight" label (`apt.js:3609`) stays coherent. Say so in the README.
2. Reuse `recentWindow` with the param as `$resetAtMidnight` — smallest diff; `hours < 24`
   means "last N hours, but not before midnight".

**Consequence if unanswered:** Workers implement one contract while tests and docs assume
the other; with option 2 and the old D5 signal, a correct new station returns
`midnight_clamped: false` for small `hours` and gets mistaken for a degraded one.

### D14 — How is an un-updated station detected, and with what exit code? (supersedes D5)

**Status:** `ANSWERED 2026-11-16`

> **Amended by [D20](../knowledge/open-decisions.md#d20--guiding-principle-minimal-footprint-aligned-with-the-parent-repo) (2026-11-16) — detection only; exit 1 ruling stands.** No new echo field:
> detect on the existing `midnight_clamped`. Audit 2's objections vanish once the frame always sends
> `hours=24` (an old station with the global flag ON already returns correct, clamped rows). See [minimal-footprint.md](../knowledge/minimal-footprint.md).

> **Ruling (exit code):** **"Loud — mark it failed."** Asked as: *"Frame updated, station
> not; the frame keeps its last collage. How loud should it be?"* ⇒ hold the previous collage
> and **exit 1** with the existing "update both the mic and frame" wording, matching today's
> outdated-station behaviour (`frame/README.md:91`). Never blank, never mix.
>
> **Detection (parent-decided, technical):** a **distinct echo field** emitted only by the new
> station code and only when the param was honoured (e.g. `"window": "station_day"`); detect
> on that alone, never on `reset_at_midnight` / `midnight_clamped`. D1's exit 0 remains for
> the steady-state "nothing to draw today" case only.
>
> Known consequence, to state in the README: under `avian-bundle use` an outdated station
> makes the render exit 1, which reverts the bundle switch — the same as today's old-mic case.

Original analysis retained below.

**Why it blocks:** D5's signal is not definitive (see the D5 row). Separately, D5 said
"log one line" but never chose an exit code — and the README precedent for an old mic
("keeps its previous image and logs an update reminder", `frame/README.md:91`) currently
**exits 1** via capture failure (`frame/shoot.py:520`), so systemd shows the unit failed.

**Recommendation:**

* A **distinct echo field** emitted only by the new code, only when the param was honoured
  (e.g. `"window": "station_day"`); detect on that alone. Never infer from
  `reset_at_midnight` / `midnight_clamped`.
* Hold the previous collage and **exit 1** with the existing "update both the mic and frame"
  wording — a frame that will never update again should be loud, as it is today.
* D1's exit 0 remains for the *steady-state* empty window only.
* Note exit 1 under `avian-bundle use` reverts the bundle — consistent with today's old-mic
  behaviour, but worth a README sentence.

### D15 — Educators capture active while `reset_at_midnight` is on?

**Status:** `PARENT-DECIDED 2026-11-16`

> **Amended by [D20](../knowledge/open-decisions.md#d20--guiding-principle-minimal-footprint-aligned-with-the-parent-repo) (2026-11-16):** no dedicated code. A scoped response reports
> `midnight_clamped: false` (`avian/api/birdnet-api.php:90`), so it takes the D14 hold path; only
> the log text widens to name both causes (outdated station, or an Educators capture). See [minimal-footprint.md](../knowledge/minimal-footprint.md).

> **Operator context:** asked *"Do you use the station's Educators (classroom) feature?"* —
> answer: **"No, I don't use it."** So this path is not reachable on the operator's setup and
> was not escalated further.
>
> **Decision (house style, fail-static):** option (a) — if the response shows an Educators
> scope (`educator_scope` present) while the flag is on, **hold the previous collage, log
> "educator capture active", ~~exit 0~~**. *(Amended 2026-11-16 by the D20 note above: no
> dedicated branch — the hold goes through the D14 path and **exits 1**, as Plan v0.3 §3/§4.2(c)
> say. Marker added 2026-11-17 in the
> [post-W1 review](../knowledge/verification-log.md#post-w1-review-implementation-and-test-coverage) because a
> verbatim copy in the W2 handoff could mislead a blank worker.)* Scope semantics win; the param never overrides a scope
> (that invariant is pinned by `tests/test_midnight_reset.php`). Revisit if the operator ever
> starts using Educators. Needs one test, no hardware.

Original analysis retained below.

**Why it blocks:** while Educators is enabled and a capture is `running`/`paused`, every
*unscoped* request is scoped automatically (`avian/api/educator-scope.php:182-191`;
`avian/api/educator-store.php:1108-1112`). Scoped requests ignore display preferences
(`avian/api/birdnet-api.php:90`) and anchor on the latest scoped detection (`:286-296`). So during a
classroom capture the frame either holds for its whole duration (with D14) or, naively,
mixes days.

**Options:** (a) **hold and log "educator capture active", exit 0** (recommended — scope
semantics win, frame stays fail-static); (b) show the scoped collage as today does;
(c) let the param override the scope (weakens an invariant the PHP tests pin).

### D16 — No validated list (fetch failed, or `--no-signature`) with the flag on?

**Status:** `ANSWERED 2026-11-16`

> **Ruling:** **"Report a failure, like today."** Asked as: *"You run a manual refresh (or
> switch bundles) while the station is unreachable. With midnight reset on, what should
> happen?"* ⇒ with the flag on in local mode the frame **never captures without a validated,
> honoured list**, so forced paths gain the fetch. **Timer run** + fetch failure ⇒ skip,
> exit 0, retry in 15 min (as today). **Forced run** (`--force`, `--no-signature`,
> `avian-bundle use`/`rollback`, `birdframe-names`) + fetch failure ⇒ **exit 1**, which
> makes a bundle switch revert so it can be retried — matching today's station-down
> behaviour. The wall is never touched either way.

Original analysis retained below.

**Why it blocks:** today a heal after a failed fetch captures with `species=None`
(`frame/display.py:444-453`), and `--no-signature` — used by both bundle paths — never fetches in
local mode (`display.py:429`; only the birdweather branch re-fetches, `:377-384`). With the
list-serving design, such a capture would let the page fetch `recent` *without* the param
(`frame/shoot.py:258`) and **mix days**.

**Recommendation:** with the flag on in local mode, **never capture without a validated,
honoured list**. Forced paths therefore gain the fetch. Timer run + fetch failure ⇒ skip,
exit 0 (as today); forced run + fetch failure ⇒ exit 1 (matches today's
station-unreachable behaviour).

### D17 — The local-mode served-list variant

**Status:** `SUPERSEDED 2026-11-16` — operator chose the parent repo's flow

> **Operator ruling (re-asked under D20):** asked *"How should the frame get today's birds onto
> the page it photographs?"* — **"Use the parent repo's way."** The page keeps fetching
> `recent` from the station exactly as upstream does; the frame adds the midnight param (and
> `hours=24`) to the request `frame/shoot.py` already rewrites (`frame/shoot.py:258`). No
> served-list code path. This also **replaces the "frame serves its own list" half of the D3
> ruling**; D3's other half (additive request param, config toggle default off) stands.
> Signature/pixel agreement is provided by upstream's existing re-sign from the captured
> response (`frame/display.py:457-463`). A/B R4 is no longer needed.

> **Re-opened by [D20](../knowledge/open-decisions.md#d20--guiding-principle-minimal-footprint-aligned-with-the-parent-repo) (2026-11-16) — needs operator re-confirmation.** Its premise (signature and
> pixels must come from one response) is already handled upstream: `frame/display.py:457-463`
> re-signs from what the browser was served (`frame/shoot.py:272-275`). The upstream-aligned
> alternative keeps the page's own station request and adds the param to the existing `hours=`
> rewrite (`frame/shoot.py:258`). See [minimal-footprint.md](../knowledge/minimal-footprint.md) and A/B R4.

Amends D3's mechanics; does not change the ruling.

* Fulfil `recent` with the frame's **full** fetched response — every field (`site_name`,
  `educator_scope`, window metadata, `species`) — plus `frame_capture_id`. `small_floor`
  applies after the capture snapshot exactly as today (`frame/shoot.py:270-280`).
* **`continue_()` all other actions to the station**, as local mode does today
  (`shoot.py:253`). Do not adopt birdweather's `{}`.
* **Flag-gated.** With `reset_at_midnight = false`, `_make_api_handler` behaves exactly as
  today, so req 12 stays bit-identical (`site_name` and `educator_scope` pass-through is
  pinned by `tests/test_frame_capture.py:177-185`).
* The fetch helper returns the **whole response**, not `data["species"]` (needed by D14
  and D6). Add a flag-only helper rather than changing `fetch_recent` / `fetch_species`, so
  existing mocks and req 12 are untouched.
* ~~`run()` gains several branches; plan a helper to stay under flake8 `max-complexity = 15`.~~
  *Corrected 2026-11-16:* measured 2026-11-16 with the repo's `.flake8`: upstream `frame/display.py` `run()` = 18, `frame/shoot.py` `_make_api_handler` = 16, `shoot()` = 46 — the 15 limit is **not enforced**: `.github/workflows/python-ci.yml` (plain `flake8`) runs only on PRs to `main`, the parent's default branch is `avian-visitors`, and `.github/workflows/python-app.yml` gates only `E9,F63,F7,F82` (complexity is `--exit-zero`). Under D20, add the feature's branch(es) in upstream's style;
  do not restructure `run()`.

Basis: house style (additive, flag-gated, minimal blast radius) and the pinned tests above.

---

### D20 — Guiding principle: minimal footprint, aligned with the parent repo

**Status:** `ANSWERED 2026-11-16`

> **Ruling (operator's words):** "At all points whenever possible, we want to stick to
> aligning and defaulting to what the parent repo does. We only change the smallest amount of
> code to implement our desired change. If that requires additional research, AB testing,
> then plan it out, research it, document it. We walk lightly, quietly, and leave as little
> trace as possible the expense of us working harder."

**Precedence:** outranks every `PARENT-DECIDED` detail; operator rulings that conflict with it
are **re-asked**, not overridden. Applied in
[minimal-footprint.md](../knowledge/minimal-footprint.md) the same day: parent-decided details shrunk
(D13 implementation, D3 mechanics, D14 detection, D15, D6 dropped, `Date =` optimisation
dropped); two operator rulings flagged for re-confirmation (D3's "frame serves its own list"
half → [D17](../knowledge/open-decisions.md#d17--the-local-mode-served-list-variant), and D4's "mirror it as a CI job").
**Outcomes:** D17 — operator chose the parent repo's flow (superseded). D4 CI clause — operator:
"Decide after research R2"; R2 done (parent CI already runs PHP + SQLite3); then **"No new
workflow."**

## Non-blocking — decided by the parent from house style, to be proposed in the PR

Recorded so no child re-opens them, and so Reviewer can check the implementation matches.

| ID | Question | Adopted answer | Basis |
|---|---|---|---|
| D5 | ~~Un-updated station ignores the param: fall back to rolling, or hold?~~ **SUPERSEDED by D14 (Audit 2).** | ~~Hold; detect via absent `midnight_clamped` / `window_start`~~ — those fields are **always present** on any station with the global-flag code (`avian/api/birdnet-api.php:392-397`), and an old station with the global flag ON already returns `midnight_clamped: true`, so they cannot prove the param was honoured | see D14 |
| D6 | First detection of the day hashes identically to yesterday — refresh? | **Dropped by [D20](../knowledge/open-decisions.md#d20--guiding-principle-minimal-footprint-aligned-with-the-parent-repo) (2026-11-16): not implemented — near-cosmetic, adds hash material.** Force a refresh by putting the effective window identity in the existing `scope` argument of `signature()`. **Audit 2: optional / near-cosmetic** — if today's signature equals the saved one, the glass already shows that species+bucket set. The salt must come from the *same* response in both hashing sites (`frame/display.py:438-441,459-463`) | precedent `birdweather_signature_scope` (`display.py:125`); keeps the frozen unscoped hash contract (`tests/test_frame_birdweather.py:193-197`) |
| D7 | Suppress the 24 h heal while today's window is empty? | Yes, suppress; document the burn-in consequence. A heal cannot "redraw the retained image" — a clamped window structurally cannot return yesterday's rows. **Audit 2: needs no mechanism** — a data-keyed pre-capture guard already suppresses it | req 10 explicitly outranks heal; [`frame-refresh-decision.md`](../knowledge/frame-refresh-decision.md) |
| D8 | First detection inside quiet hours leaves yesterday up until quiet ends? | Yes — the brief says preserve quiet hours; state it in docs and cover with a test | `in_quiet_hours` (`display.py:348`) |
| D9 | Additive `state.json` keys; must older files still work? | **Amended (Audit 2): add no keys.** A data-keyed pre-capture guard is already immune to a corrupt/missing `state.json`, so the state format stays unchanged. Hard rule: **a decline must never call `save_state`** (it would stamp `last_refresh` without a push); today `save_state` is only reached after `push_panel` (`display.py:477-481`) — keep it that way. Covers the `OnBootSec=2min` boot-after-outage run | `display.py:329-335,477-481`; `frame/systemd/birdframe.timer:10` |
| D10 | Should any of this be pushed into `avian/frontend/apt.js` or the global flag? | No. The site must keep clearing on a genuinely empty window, and the global `RESET_AT_MIDNIGHT` is off-limits | `tests/smoke_collage_readiness.mjs:25`; brief isolation list |

---
