# Plan review — reset-after-midnight v0.2 (draft)

Review of [`.pi/reset-after-midnight Plan v0.2.md`](../reset-after-midnight%20Plan%20v0.2.md)
against the code. **Not an implementation.** Goal: make the plan executable, and pin
down what the parent orchestrator must decide before dispatching workers.
Code facts cited here live in [feature-midnight-reset.md](feature-midnight-reset.md)
and [station-clock-and-data.md](station-clock-and-data.md).

## Verdict

The requirement set is now close to implementable; the *orchestration* half is the
weaker half. Four things will bite if left as written:

1. Requirements 9/10 are stated as refresh-gate problems, but there are **draw paths
   that bypass the gate entirely** — including one that runs automatically.
2. The plan treats an API change as optional, while its own constraints make one
   effectively **necessary**; a Worker handed "if necessary" will pick the cheapest
   thing that fails a requirement.
3. It never says the feature is **mode-specific** — `local` only, or also
   `birdweather`/`image`?
4. Phase 5's test list omits the specific existing tests that will break, and the
   machine it will be run on cannot run most of them.

## v0.1 → v0.2 delta (what changed and why it matters)

| Added in v0.2 | Where it lands in code | Note |
|---|---|---|
| Req 11 "preserve the displayed image across process restarts whenever possible" | `load_state()` swallows **any** exception → `{"signature": None, "last_refresh": 0}` (`frame/display.py:329`) | On e-ink the image already survives power loss physically; the real requirement is *"do not draw on restart"*, which is exactly the corrupt-state-file path. Needs an explicit rule. |
| Req 9 "never overwrite the retained collage with a blank/no-birds screen" | `signature([])` is a real hash; empty window == change | Correct, but see Gap 1 — the gate is not the only draw path. |
| Req 10 heal logic must not clear the collage | `heal_due` (`display.py:444`) | Right; has a hardware side-effect (Gap 6). |
| Req 1 "station's local calendar date … starting at 00:00" | `station_date`/`anchor` in the `recent` response; `Date` column + index | Good — and better spellings exist than the one v0.1 implied (Improvement 1). |
| "Do not approximate … rounding elapsed time to whole hours" | `hours` is an int; `recentWindow` uses `'-N hours'` | Kills the obvious client-side approach; forces a server-side window (Gap 2). |
| Test 9 timezone differences, Test 11 other API clients | see Gap 7 for concrete scenarios | Both currently un-falsifiable as written. |
| Isolation: API change "optional, request-scoped, backward compatible" | `recentWindow(..., $resetAtMidnight, $scoped)` already takes the flag per-request | The shape already anticipates request scoping — good instinct. |
| One-child-at-a-time orchestration, task ledger, 6 phases | [`.pi/knowledge/orchestration.md`](orchestration.md) | Role mapping fixed there; `Tester` does not exist. |

## Gaps and risks in the plan

### Gap 1 — the draw paths the gate does not cover (highest severity)

`frame/display.py:446` gates only when **neither** `--force` **nor** `--preview`, and
`changed` is unconditionally True with `--no-signature` (`display.py:445`). So all of
these reach `obtain_image()` and can render an empty today collage:

| Path | Command | Risk |
|---|---|---|
| **Render after `avian-bundle use`** (only when the selection actually changed) or **`avian-bundle rollback`** (renders unconditionally) | `bundle_runtime._render_callback()` → `display.py --force --no-signature --wait-lock` (`frame/bundle_runtime.py:2083-2113`; `changed` gate at `:1953-1955`, `:1962-1963`; rollback at `:1993-1997`) | User-initiated, but the user asked for **artwork**, not a wipe — a bundle switch during an empty today window blanks the wall. |
| `birdframe-names on\|off` | `display.py … --force` (`frame/birdframe-names:63-68`) | A deliberate user action, but the user asked for names, not a wipe. |
| Manual `--force` | documented in `frame/README.md` as the standard update step | The README literally tells users to run `--force` after every `git pull`. |
| `--no-signature` | documented dev path | Same. |

⇒ The guard cannot live only in the refresh gate. It must decide *before capture*
whenever a today-window render is requested, and the plan should say so in Task B with
a named test for the bundle/rollback path. There is a hidden escape hatch
(`--no-render`, suppressed from help, `bundle_runtime.py:2121,2124`) but it is not a
substitute for the guard.

Related hard constraint, **stronger than it first looks**: `_render_callback` raises on
any non-zero exit (`:2108-2110`), and the caller then **restores the previous bundle
state and re-renders** before raising
(`:1962-1972`: `_save_state(storage, before)` → `render()` → `BundleError("frame render
failed; the previous bundle was restored")`). So a decline-to-draw that exits non-zero
would silently **undo the user's bundle switch**, not just log a failure. Declining must
return success (exit 0, like the existing "no change; skip" path).

Scope note: this gap maps to brief requirements **9 and 10 only** — requirement 12
("disabled ⇒ unchanged") is untouched by it. Don't let a Worker conflate them.

### Gap 2 — "if an API change is necessary" (Phase 2) is a decision, not a question

Requirements "station's local calendar date, starting 00:00", "no whole-hour
approximation", "never mix yesterday and today", and correct `n` for tile sizing
cannot be met from the client: `recent` exposes only an hours-based window, and
per-species `last_seen` + `n` from a rolling window would mix counts and keep
yesterday's birds inflating `_bucket()` brackets. The no-change alternative —
`hours=1000000` ("ALL") + client-side filter — fails "never mix" and is slower.
**Recommendation: Phase 2 should record "request-scoped additive param on
`action=recent`" as a decision with the rejected alternatives written down**, so
Workers don't relitigate it and Oracle has something concrete to check drift against.
Backward compatibility is cheap: absent param ⇒ existing SQL and headers unchanged.

### Gap 3 — the feature is never scoped by frame mode

| Mode | Can "today only" even be defined? |
|---|---|
| `local` (screenshot the station) | Yes — this is what the whole brief describes. |
| `birdweather` (ZIP/station via BirdWeather, `bw_days = 7`) | Different data source entirely. "Midnight reset" means something like `bw_days` → current-day-only, which the BirdWeather `topSpecies(period:)` API may not answer locally. Probably **out of scope**; needs saying. |
| `image_url` / `image` | The frame draws someone else's pixels; it can append `labels=` but cannot change their window. Should be documented as **not supported** (mirrors the existing bundle caveat, `frame/display.py:402-405`). |

If Task A is written mode-blind, a Worker may "make it work" in birdweather mode by
mutating BirdWeather parameters — an unrequested behaviour change with its own
fallback chain (`triangulate`, eBird).

### Gap 4 — station/frame version coupling is unspecified

New frame + un-updated station (the README's standing warning is *"update both"*).
Options: (a) silently fall back to rolling — violates "never mix" but keeps a live
frame; (b) keep the previous collage and log — consistent with the fail-static
house style; (c) hard-fail. There is a LAN-only capability probe available
(`birdnet-status.php?action=version`, no auth needed for direct LAN requests —
`avian/api/admin-auth.php:817-825`), but it 401s through a tunnel, so it cannot be the primary
mechanism. **Better: read the response's own `reset_at_midnight` /
`midnight_clamped` / `window_start` fields** — those already exist, and their absence
or falsity is a definitive "this station did not clamp" signal. Recommend (b) +
explicit log line; needs a decision recorded.

### Gap 5 — one real-time edge: cached clamped responses across midnight

`recent` is `public, max-age=30` unless the **global** flag is on
(`avian/api/birdnet-api.php:169-171`). A request-scoped clamp leaves caching public under its own
URL, so seconds after midnight a shared cache can serve a pre-midnight clamped
response for up to 30 s. Harmless given the skip-when-nothing-to-draw rule ([D12](open-decisions.md#d12--what-does-nothing-to-draw-mean-for-the-d1-decline); originally
written as "skip-on-empty") and the 15-min cadence,
but the plan should state whether the clamped variant should be `no-store` for
determinism. It should also state the new param must not flip caching for requests
that don't send it.

### Gap 6 — suppressing heal forever has a hardware cost

`heal_hours = 24` exists to force a periodic full refresh (burn-in hygiene / missed
refreshes while offline). Requirement 10 makes a heal during an empty today window a
no-op — correct for the data, but it means a frame with no detections for a week gets
no heal for a week. Worth an explicit sentence in the README/docs, plus a decision on
whether heal is suppressed for the empty window only (recommended) or capped
(e.g. allow a heal that redraws *the same retained image* — **impossible**: once the
window clamps to today, the frame can no longer obtain yesterday's collage at all, so
"redraw the retained image" is not implementable. This is a consequence of the design
that nobody has written down yet: *retention means "don't touch the panel", not
"can re-render it"*. If the panel is corrupted mid-stretch (power glitch during a
partial update), recovery requires a detection.)

### Gap 7 — Phase 5's list is not falsifiable as written

"Station and BirdFrame timezone differences" and "API requests from other clients"
need concrete assertions. Minimum concrete scenarios missing from the plan:

1. **Bundle switch during an empty today window** → no panel write (Gap 1).
2. `birdframe-names on` during an empty today window → no panel write.
3. `--preview` during an empty window → **still renders** (dev tool; must not be gated).
4. `state.json` missing / corrupt / from an older version (no new fields) + empty
   window → no write; `state.json` valid + non-empty window → normal.
5. Station clock steps **backwards** across midnight (NTP correction): a window that
   just clamped may un-clamp; assert no thrash (no repeated refresh).
6. DST day (23 h and 25 h) — assert the day boundary is calendar-based, not 24 h.
7. `?date=<historical>` + clamp param → no clamp (PHP test already pins
   "historical date stays rolling"; keep it green).
8. `edu=` educator-scope request + clamp param → scope still wins/ignores display
   preference (PHP test pins this for the global flag; the param must not bypass it).
9. `hours >= 1000000` ("ALL") + clamp param → defined behaviour (probably ALL wins).
10. First detection lands inside quiet hours (e.g. 03:00 with `quiet_start=22`,
    `quiet_end=6`) → panel stays on yesterday until quiet ends; assert that is the
    intended UX.
11. Species present in the window but **not drawable** → must be treated as "nothing to
    draw": no capture, no write. *(Corrected in Audit 2: this item originally claimed
    `fetch_species(drawable=…)` already filters them. It does not in `local` mode
    (`frame/display.py:150`); un-illustrated species reach the page, are dropped by `avian/frontend/apt.js`, and
    an all-undrawable list hangs capture. Now decision [D12](open-decisions.md#d12--what-does-nothing-to-draw-mean-for-the-d1-decline).)*
12. Param absent from an `apt.js` request → byte-identical SQL/headers to today
    (Test 11's real assertion).

Also missing from Phase 5: the tests that will **break** if shoot.py's capture
handshake changes — `tests/smoke_collage_readiness.mjs` regex-extracts `FRAME_READY`
from `frame/shoot.py` and runs it in a Node VM (`:86-88`), and it asserts
`"a successful zero-detection result clears old birds"` for the **website** (`:25`),
i.e. the site must keep blanking on an empty window while the frame must not. That
asymmetry is a design statement the plan should record so nobody "fixes" it centrally.

### Gap 8 — process details that will stall a child

* `worker` has **`defaultReads: context.md, plan.md`** and `defaultContext: fresh`:
  the plan never tells the parent to write `plan.md`. If it isn't created, every
  worker starts blind. See [orchestration.md](orchestration.md).
* No `Tester` agent exists; Phase 5 must say `worker` + `reviewer`.
* Phase 4 Reviewer and Phase 6 Oracle both check "drift"; give them non-overlapping
  briefs (Reviewer = diff/code/tests/regressions via `watchdog_diff`;
  Oracle = requirement/decision drift against forked context).
* "Run the queue autonomously without asking for permission" conflicts with the
  oracle's built-in `contact_supervisor` behaviour on material unknowns. Pre-resolve
  the questions below so no child blocks on them.
* Completion criteria say "Tests pass" without naming the platform. On this Windows
  box, `php` is absent *(true at the time; installed 2026-11-16, [R3](verification-log.md#r3-execute-the-clamp-and-param-shape-claims-with-php))* (PHP contract tests **pass vacuously**) and `fcntl` is absent
  (`frame/display.py` tests error). Require the final report to name the environment and
  list not-executed checks.

## Improvements worth folding into v0.3

1. **Express "today" as `Date = :station_date` — but keep the anchor ceiling.** The
   form is exact to the second, DST-proof, and the only one that can use
   `detections_Date_Time (Date DESC, Time DESC)` (`scripts/createdb.sh:20`);
   `DATETIME(Date||' '||Time) >= midnight` cannot. Verified with `EXPLAIN QUERY PLAN`
   against that schema: `Date = '2026-09-02'` → `SEARCH … USING INDEX
detections_Date_Time`, the current rolling predicate → `SCAN detections` — i.e. the
   **existing** `recent` query already full-scans on every poll, so this is a general
   win. Precedent: `case 'hourly'` (`WHERE d.Date = :d`).
   **Caveat:** `recentWindow` always applies an upper bound
   `DATETIME(Date||' '||Time) <= DATETIME(:anchor)` (`avian/api/birdnet-api.php:89`). A bare
   `Date = :d` silently drops that ceiling and changes semantics for skewed or
   future-stamped rows. Use `Date = :d AND DATETIME(Date||' '||Time) <= :anchor`.
2. **Reuse `signature(species, scope)` for day identity instead of new state.** The
   `scope` slot already exists to make two different windows with the same species set
   hash differently (`birdweather_signature_scope`), with a frozen compatibility test
   (`tests/test_frame_birdweather.py:191`) proving unscoped hashes stay stable.
   Putting e.g. the effective window identity there (station date when clamped) means
   a day change *with an identical species set* still refreshes — which closes the
   "first detection of the day produced no visible change" edge without inventing a
   parallel mechanism. Unscoped frames are untouched.
3. **Use the station date, not a computed midnight.** `recent` already returns
   `station_date`, so the frame needs no clock agreement and no client-side tz resolution.
   *(Amended by Audit 2: this originally said to **store** it in `state.json`; [D9](open-decisions.md#non-blocking--decided-by-the-parent-from-house-style-to-be-proposed-in-the-pr) now adds
   no state keys — the station's window already starts at its own midnight, so the frame
   has nothing to remember.)* (Server-side there *is* an
   authoritative zone: Caddy passes `AVIAN_STATION_TIMEZONE` to PHP
   (`scripts/update_caddyfile.sh:967,976,985`), so a request-scoped clamp can be tz-exact in
   PHP — the point is only that the **frame** shouldn't compute midnight itself.)
4. **Guard placement: decide in `run()` *before* capture, from the fetched species
   list + a "clamp actually happened" check**, not inside the gate block. Covers
   `--force`/`--no-signature`/bundle path in one place, and avoids burning a
   70–120 s Chromium capture on a frame we've already decided not to draw.
5. **Write the rejected approaches into the plan** (client-side `last_seen` filter,
   `hours=1000000`+filter, changing the global flag, doing it in `avian/frontend/apt.js`) with one-line
   reasons. Cheap insurance against a Worker re-deriving a bad idea.
6. **Add a kill-switch sentence** to docs/deployment: `reset_at_midnight = false`
   restores exact prior behaviour, and state/signature compatibility means flipping it
   back needs no reset of `state.json`.
7. **Make the PHP work testable the existing way:** the repo already injects a
   synthetic clock (`AV_EDUCATOR_NOW`, CLI-only, `avian/api/educator-store.php:420-427`) and runs
   endpoints without a web server via `php -r` with a fabricated `$_SERVER`/`$_GET`
   (`tests/test_educator_security.py:216-236`). Use that, plus the
   `AVIAN_BIRDNET_API_LIBRARY_ONLY` load trick, instead of inventing a harness.

## Clarifying questions (blocking for Phase 2)

> **Superseded for triage purposes by
> [open-decisions.md](open-decisions.md)**, which maps these to decision IDs [D1](open-decisions.md#d1--may-a-forced-render-draw-an-empty-today-window-collage)–[D11](open-decisions.md#d11--commit-ignore-or-leave-untracked-pi-and-root-agentsmd) and
> records which are pre-answered. Kept here because the recommendation column carries
> the reasoning. Mapping: Q1→D1, Q4→[D2](open-decisions.md#d2--which-frame-modes-does-the-feature-apply-to), Q8→[D3](open-decisions.md#d3--station-api-additive-request-param-name-and-shape), Q9→[D4](open-decisions.md#d4--what-environment-is-the-acceptance-gate), Q2→[D5](open-decisions.md#non-blocking--decided-by-the-parent-from-house-style-to-be-proposed-in-the-pr), Q3→[D6](open-decisions.md#non-blocking--decided-by-the-parent-from-house-style-to-be-proposed-in-the-pr), Q5→[D7](open-decisions.md#non-blocking--decided-by-the-parent-from-house-style-to-be-proposed-in-the-pr), Q6→[D8](open-decisions.md#non-blocking--decided-by-the-parent-from-house-style-to-be-proposed-in-the-pr),
> Q7→[D9](open-decisions.md#non-blocking--decided-by-the-parent-from-house-style-to-be-proposed-in-the-pr), Q10→D11.

| # | Question | My recommendation |
|---|---|---|
| Q1 | May `--force` / the automatic post-bundle render draw an empty today collage? | No: decline (exit 0). Only `--preview` draws an empty window. |
| Q2 | Un-updated station ignores the param: fall back to rolling (mixes days), or keep the previous collage + log? | Keep previous + log a one-line update hint, matching the existing "update both the mic and frame" behaviour. |
| Q3 | If the first detection of the day yields a signature identical to the retained one, is "no refresh" acceptable? | No — salt the signature with the effective window identity via the existing `scope` arg (Improvement 2). |
| Q4 | Does the feature apply in `birdweather` and `image_url` modes, or `local` only? | `local` only; document the other two as unsupported, mirroring the existing bundle caveat. |
| Q5 | Suppress the 24 h heal indefinitely while today is empty? | Yes (data correctness first), and document the burn-in consequence. |
| Q6 | Is a first detection inside quiet hours allowed to leave yesterday's collage up until quiet ends? | Yes (requirements say preserve quiet hours), but state it. |
| Q7 | New `state.json` fields OK, and must files written by older frames keep working? | Yes and yes: additive keys, tolerate missing. |
| Q8 | Param name/shape, and does it need to survive upstream PR review (i.e. should it reuse the existing `RESET_AT_MIDNIGHT` vocabulary)? | `reset_at_midnight=1`, strict scalar parse, ignore folded aliases; matches existing vocabulary and response field. |
| Q9 | Which environment is the acceptance gate — CI only, WSL/Docker, or real `birdpic` hardware? | CI + a Linux devbox for PHP/pytest; hardware pass required before merge, and the report must list which checks were not run. |
| Q10 | Commit, ignore, or leave untracked: `.pi/` (this knowledge base, plan drafts, child handoff files)? | Ask the operator; today it is untracked and **not** gitignored, so a careless `git add -A` would commit it. |

## Post-audit triage (Oracle, same day)

An independent `oracle` run verified the findings against source. Confirmed: the
central hazard (empty window is valid and drawable end to end), "retain ≠ can
redraw", Gap 2, Gap 3. Corrected: the `--preview` inclusion, the bundle-failure
consequence, and the timezone line list — all folded into this doc above.

**Blocking questions** (each changes code, not prose):

* **Q1** forced-render semantics — Gap 1 is unimplementable without it.
* **Q4** mode scoping — changes which code paths exist at all.
* **Q8** param name/shape incl. strict scalar parse and PHP `key[]`/NUL folding.
* **Q9** acceptance environment — nothing load-bearing is verifiable on this box.

**Answerable without the operator** (adopt + document, don't ask):

* **Q2** — ~~the fail-static house style already answers it: keep the previous collage,
  log a hint, detect via absent `midnight_clamped`/`window_start`.~~ **Re-opened by Audit 2
  as [D14](open-decisions.md#d14--how-is-an-un-updated-station-detected-and-with-what-exit-code-supersedes-d5)**: those fields are always present, so absence detects nothing; detection needs a
  distinct echo field, and the exit code (0 vs the README precedent's 1) needs a ruling.
* **Q3** — adopt the `scope`-salt recommendation; it is compatible with the frozen test.
* **Q5/Q6** — both follow from "preserve heal and quiet hours".
* **Q7** — `load_state()` already tolerates anything by resetting; pin a test instead.
* **Q10** — housekeeping, but settle **before** any worker runs `git add`.

### Requirements still unmapped to code

Brief §3 items that the feature doc's requirement→code table did not cover (now added
there, listed here so Reviewer/Phase-6 has something to check):

1. **"Do not modify or delete historical detections"** — trivially true of a read-only
   API, but it must be *asserted*, not assumed.
2. **"Preserve e-ink rendering, layout, change detection, quiet hours"** — quiet hours
   previously appeared only as a test scenario, not a mapped requirement.
3. **Requirement 11's *scheduled* restart vector** — `frame/systemd/birdframe.timer` has
   `OnBootSec=2min` (`frame/systemd/birdframe.timer:10`; `Persistent=true` is inert without `OnCalendar=`), so a
   boot after a multi-day outage fires a render within two minutes: exactly the
   "restart before the first detection" case, and it arrives on a timer, not a manual
   restart.
4. **"Do not enable or modify the global `RESET_AT_MIDNIGHT`"** — currently unowned.
   The PHP contract tests the flag's *behaviour*; nobody checks that frame code never
   writes config. Cheap Reviewer assertion: `frame/*.py` must not POST to
   `avian/api/config.php`.

## What the plan gets right

Explicit "don't touch the global `RESET_AT_MIDNIGHT`" and "don't touch history";
"preserve existing e-ink/layout/quiet-hours except where required"; the isolation list;
mocked-display verification with hardware gaps called out; "small, focused changes
over broad refactoring"; "don't discard unrelated local changes"; "no commit/push/PR
without authorization"; and the final-Oracle drift audit. Those map one-to-one onto
the house style in [code-conventions.md](code-conventions.md).
