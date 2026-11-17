# Minimal footprint: align with the parent repo

**Operator principle (2026-11-16, decision [D20](open-decisions.md#d20--guiding-principle-minimal-footprint-aligned-with-the-parent-repo)):** "At all points whenever possible, we want
to stick to aligning and defaulting to what the parent repo does. We only change the
smallest amount of code to implement our desired change. If that requires additional
research, A/B testing, then plan it out, research it, document it. We walk lightly,
quietly, and leave as little trace as possible at the expense of us working harder."

This outranks every *parent-decided* design detail. Operator rulings that conflict with
it are re-asked, never silently overridden.

## How to apply it (checklist for every design choice)

1. **Is there already an upstream mechanism that does this?** Use it, even if a new one
   would be "cleaner". Evidence first: read the code path, cite `file:line`.
2. **Count the trace.** Changed lines in shipped files, new files, new workflows, new
   config keys, new response fields, new state. Prefer zero of each beyond the minimum.
3. **Match the parent's idiom**, not ours: parameter parsing, test placement, docs voice.
4. **Shipped tree vs our tree.** Research tooling, harnesses, notes and checkers live in
   `.pi/` (locally git-excluded, [D11](open-decisions.md#d11--commit-ignore-or-leave-untracked-pi-and-root-agentsmd)), never in the parent's tree.
5. **When two options are close, run an A/B**: prototype both outside the shipped tree,
   measure the diff and the tests, record the result here, then choose.

## Parent-repo evidence (how upstream itself makes changes like ours)

| Upstream change | Commit | Footprint | What it tells us |
|---|---|---|---|
| Station "reset at midnight" | `f1cb3add` | 7 files, +112 / −13 (incl. UI, config, release notes) | The clamp machinery we need already exists and was built to be reused per request: `recentWindow(..., $resetAtMidnight, $scoped)` (`avian/api/birdnet-api.php:82-121`). |
| Its tests | `1092b969` | `tests/test_midnight_reset.php` (+85), `tests/test_midnight_reset.py` (+23), smoke updates | Tests for this area go in **that** file, in that style. |
| Frame bird names | `402342ff` | 5 files, +161 / −31 | Frame features touch `frame/display.py`, `frame/shoot.py`, `frame/config.example.toml`; the URL param pattern is `frame_url()` (`frame/display.py:355-363`). |
| Frame exact BirdWeather station | `80f2a9fe` | 10 files, +1113 / −77 (603 of it tests) | Upstream ships tests with frame behaviour, in `tests/test_frame_*.py`. |

Upstream query-param idiom (`avian/api/birdnet-api.php:135,281,356,403-406,434,465,508`):
`$_GET['x'] ?? default` with a cast or strict compare — **no** alias-folding machinery.

## Footprint audit of the settled design

Every item was re-checked against source on 2026-11-16.

| Design item (source) | Before | Minimal, upstream-aligned | Evidence | Status |
|---|---|---|---|---|
| Station window for "today" ([D13](open-decisions.md#d13--does-the-today-window-respect-the-hours-setting) impl.) | New SQL branch `Date = :station_date AND … <= :anchor` + echo fields | **Reuse upstream `recentWindow`**: the frame sends `hours=24` + the param. With `hours=24` and today's anchor, `anchor − 24h` is always before `start of day`, so the clamp **always** applies — exactly "everything since midnight", which is D13's ruling. Upstream already pins this: *"24 hour window clamps after midnight"* (`tests/test_midnight_reset.php`). | `avian/api/birdnet-api.php:104-116` | parent-decided (UX ruling unchanged) |
| Station param plumbing ([D3](open-decisions.md#d3--station-api-additive-request-param-name-and-shape) mechanics) | strict parse + PHP alias guard + `no-store` re-send in `case 'recent'` | **Superseded by R1 (2026-11-16): variant B′, +1 / 2 modified** — a new local `$resetAtMidnight = $RESET_AT_MIDNIGHT || (($_GET['reset_at_midnight'] ?? null) === '1');` in the request-derived block (`:131-136`), swapped in at `:169` and `:362` (see [R1 brief](../outputs/r1-station-param-variant.md)). *Original text:* **One line** at `avian/api/birdnet-api.php:129`: OR the request param into `$RESET_AT_MIDNIGHT`. That variable is used in exactly two places — the cache header (`:169`) and the `recentWindow` call (`:362`) — so `no-store` and the clamp follow automatically, and `$scoped` still wins. Idiom `($_GET['reset_at_midnight'] ?? null) === '1'`; an array value (`x[]=1`) is not `'1'`, so alias folding is a non-issue. *(Corrected by R1: arrays are rejected, but PHP key mangling (`reset.at.midnight=1`) and last-wins duplicates are honoured, exactly as for every upstream param — harmless for a read-only display window; D3 amended.)* | `:129,169,362`; idiom above | parent-decided; see A/B R1 |
| Degraded-station detection ([D14](open-decisions.md#d14--how-is-an-un-updated-station-detected-and-with-what-exit-code-supersedes-d5)) | new echo field | **No new field.** Detect on the existing `midnight_clamped`. Audit 2's objections to that signal disappear once the frame always sends `hours=24`: an old station with the global flag ON returns `midnight_clamped: true` *and the correct rows*, so the frame is right anyway; small-`hours` false negatives can't happen. Exit 1 (operator ruling) unchanged. | `:110-116,392-397` | parent-decided |
| Educators scope ([D15](open-decisions.md#d15--educators-capture-active-while-reset_at_midnight-is-on)) | dedicated branch | **No code.** A scoped response reports `midnight_clamped: false` (`$enabled = … && !$scoped`, `:90`), so it falls into the D14 hold path. Only the log text widens: "station did not apply the midnight window (outdated station, or an Educators capture is active)". Operator doesn't use Educators. | `:90` | parent-decided |
| Render path ([D17](open-decisions.md#d17--the-local-mode-served-list-variant), from D3 ruling) — **operator chose the parent repo's flow, 2026-11-16** | flag-gated variant of `_make_api_handler` that serves the frame's own response; page request no longer reaches the station | **Upstream flow unchanged**: the page still fetches the station; `frame/shoot.py` already rewrites `hours=` in that request (`frame/shoot.py:258`) — add the param there. D17's reason (signature and pixels from one response) is **already solved upstream**: `frame/display.py` re-signs from exactly what the browser was served (`frame/display.py:457-463`; captured from the page's response at `frame/shoot.py:272-275`). | cited | **decided: upstream flow** (D17 superseded) |
| Drawable decline ([D12](open-decisions.md#d12--what-does-nothing-to-draw-mean-for-the-d1-decline)) | — | Small: filter by the frame bundle's existing `drawable_slugs` (`frame/bundle_runtime.py:2023-2025`), already passed to `fetch_species` but ignored in local mode (`frame/display.py:150`). | cited | unchanged |
| Day-identity salt ([D6](open-decisions.md#non-blocking--decided-by-the-parent-from-house-style-to-be-proposed-in-the-pr)) | optional `scope` salt | **Drop.** Near-cosmetic (Audit 2) and adds hash material. | — | parent-decided |
| `Date =` index optimisation | recommended as "a general win" | **Drop.** Out of scope; changes an upstream query for a benefit nobody asked for. | — | parent-decided |
| Test harness ([D4](open-decisions.md#d4--what-environment-is-the-acceptance-gate) elaboration) | fake `inky` in `tests/`; container; new CI job | Fake panel + fake station + container live in **`.pi/`** (our tree). Feature tests go only where upstream puts them (`tests/test_midnight_reset.php`, `tests/test_frame_capture.py`), using their existing patterns. **No new workflow**: upstream CI already runs `pytest` on Linux (`.github/workflows/python-app.yml`). | cited | **decided: no new workflow** (operator, after R2, 2026-11-16) |
| `frame/install.sh`, `frame/config_contract.py`, companion CLI | — | No change (already ruled out). | — | unchanged |

### Estimated shipped diff after the audit

Parent-repo files only; tests counted separately. Estimates, to be replaced by measured
numbers in A/B R4.

| File | Change | Lines (est.) |
|---|---|---|
| `avian/api/birdnet-api.php` | new `$resetAtMidnight` local (station flag OR request) + one-token swaps at `:169`, `:362` (R1 variant B′) | 3 (+1 added, 2 modified) |
| `frame/display.py` | `DEFAULTS` key; param + `hours=24` in `fetch_recent`; pre-capture decline (no drawable today / not clamped); fetch on forced runs when the flag is on | ~25–35 |
| `frame/shoot.py` | thread one flag through `shoot()` to the existing `hours=` rewrite and append the param | ~4–6 |
| `frame/config.example.toml` | one commented key | ~3 |
| `frame/README.md` | one short paragraph | ~6–10 |
| tests (`tests/test_midnight_reset.php`, `tests/test_frame_capture.py`) | extend existing files in their style | ~60–90 |

For scale: upstream's own station midnight reset was +112 shipped lines plus +108 test lines.

## Research and A/B plan

### R2 result (2026-11-16)

* Parent CI jobs run on `ubuntu-latest` (`.github/workflows/python-app.yml:17,32`); no parent
  workflow installs PHP itself.
* `ubuntu-latest` = Ubuntu 24.04, image `20261111.370.1`: **PHP 8.3.6** (runner-images
  `Ubuntu2404-Readme.md`, "PHP Tools"). GitHub's notice: "`ubuntu-latest` label will use
  Ubuntu 26.04 in November 2026" (runner-images issue #14748); the 26.04 image
  (`20261111.196.1`) ships **PHP 8.5.4**.
* The SQLite3 extension the PHP contract test needs (`new SQLite3(':memory:')`) is installed on
  both: `images/ubuntu/scripts/build/install-php.sh` loops over the toolset's PHP versions and
  apt-installs a hard-coded module list that includes `php$version-sqlite3`
  (`toolsets/toolset-2404.json` lists only `"versions": ["8.3"]`).
* ⇒ The parent's existing `build` job (`pytest`) already runs `tests/test_midnight_reset.py`
  → `shutil.which("php")` → the PHP contract **for real**, and the `frame/display.py`-dependent
  tests too (Linux has `fcntl`). Feature tests added to those existing files run in parent
  CI with **no workflow change**. Only the fake-station + fake-panel end-to-end harness needs
  the `.pi/` container.
* **Caveat:** derived from the image README and build script, not from an observed parent
  CI run log. Also assumes the parent's `build` job is green today (not checked).

None of these require building the feature; R4 requires the operator's go-ahead because it
writes prototype code (in a scratch worktree, never this one).

| ID | Question | Method | Decides |
|---|---|---|---|
| R1 ✅ | **Answered 2026-11-16: variant B′** (+1 / 2 modified, `$resetAtMidnight`) — [R1 brief](../outputs/r1-station-param-variant.md), reviewer-verified. Ranking B′ > B > A > C; A and B′ are runtime-identical; C drops D3's `no-store` and would need an operator amendment. *Original question:* PHP variant **A** (1 line: `$RESET_AT_MIDNIGHT = publicConfigFlag(…) \|\| (($_GET['reset_at_midnight'] ?? null) === '1');`) vs **B** (3 lines: separate `$resetAtMidnight` used at `:169` and `:362`, leaving the config variable meaning "config") | Compare against upstream naming in `f1cb3add`; ask "which would an upstream reviewer accept without comment?" | variant |
| R2 ✅ | Does GitHub's `ubuntu-latest` runner ship `php` + `sqlite3`? **Answered — see below.** If yes, the PHP contract test is already non-vacuous in upstream CI and no workflow change is ever needed. | Read the runner-images software list | whether CI needs touching at all |
| R3 | Prove the `hours=24` clamp claim by execution, not argument | Add assertions to `tests/test_midnight_reset.php` and run them in the `.pi/` container (needs `php`) | confirms the D13 reuse |
| R4 ✖ | *Not needed — operator chose the upstream flow without an A/B.* Empirical A/B of the render path: **A** param in the page request (upstream flow) vs **B** served list (D17) | Two scratch worktrees; measure `git diff --stat`, run both suites + the fake panel; record numbers here | D17 (with operator) |
