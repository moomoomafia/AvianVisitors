# Verification log

Durable record of **independent verification runs** over the findings in this knowledge
base, so future agents know which claims were checked, how, and by whom — and which are
still assumptions. The subagent artifact this was distilled from is session-scoped and
will be cleaned; this file is the record.

---

## Audit 1 — Oracle run on the midnight-reset findings

* **Date:** 2026-11-16 · **Branch:** `feature/birdframe-midnight-reset` (no source changes)
* **Executor:** one `oracle` child agent (`6a6f60a5-36fe-4bb4-8823-2a32808b626d`),
  read-only, `defaultContext: fork`. One child at a time, per the draft plan's
  concurrency rule; the child was instructed not to delegate and did not.
* **Method:** independent re-derivation from source. No test-suite runs (no `php`, no
  `fcntl` on this box), so every verdict is code-reading plus two local proofs noted
  below.
* **Scope audited:** [`.pi/knowledge/plan-review-midnight-reset.md`](plan-review-midnight-reset.md),
  [`feature-midnight-reset.md`](feature-midnight-reset.md), [`station-clock-and-data.md`](station-clock-and-data.md), plus supporting claims in
  [`frame-refresh-decision.md`](frame-refresh-decision.md), [`_index.md`](_index.md), [`testing-and-ci.md`](testing-and-ci.md), [`repo-map.md`](repo-map.md),
  [`orchestration.md`](orchestration.md), against
  [`.pi/reset-after-midnight Plan v0.2.md`](../reset-after-midnight%20Plan%20v0.2.md).

### Verdicts (post-audit, after the parent re-verified each counter-claim)

| # | Claim | Verdict | Evidence | Falsified by |
|---|---|---|---|---|
| 1 | `--force` / `--no-signature` bypass the refresh gate | **AGREE**; `--preview` inclusion **OVERSTATED** | `frame/display.py:445` `changed = (not use_signature) or …`; `:446` `if not force and not preview:`; `--preview` returns at `:468-473` **before** `push_panel` (`:476`) and never calls `save_state` | preview reaching `push_panel` — it does not |
| 2 | `avian-bundle` renders with `--force --no-signature --wait-lock`; non-zero exit is bad | **AGREE on flags/exit**; **MISSTATED consequence** | `frame/bundle_runtime.py:2098-2106` flags; `:2108-2110` raise; `:1953-1955` render only when `changed`; `:1962-1972` on failure **restores prior state, re-renders, then raises**; `rollback` renders unconditionally `:1993-1997`; hidden `--no-render` `:2121,2124` | a non-zero exit that only logged (it does not) |
| 3 | `signature([])` is a real distinct hash; `load_state` failure ⇒ "changed" | **AGREE** | `display.py:103-107` (sorted `[]` hashed); independently reproduced `sha256("[]")[:16] = 4f53cda18c2baa0c`; `:329-335` any exception ⇒ `signature: None`; `:445` | an existing emptiness guard — none exists |
| 4 | A page-URL param cannot reach the API; inject in both places | **AGREE** | `frame/shoot.py:249-250` intercepts only `action=recent`; `:259` is a **substitution** of `hours=\d+`, not an append; `apt.js:378-387 birdApiUrl` builds from passed params + `edu`; `location.search` is read **only** for `edu` (`avian/frontend/apt.js:317`), `labels` (`:1809`), `atlasLifers` (`:4657`) | any generic param pass-through in `apt.js` — there is none |
| 5 | Client-side `last_seen` filter cannot satisfy "never mix days" | **AGREE** | `avian/api/birdnet-api.php:369-375`: `COUNT(*) AS n … WHERE $where` — `n` is window-scoped; `last_seen` is only `MAX(...)` | `n` being per-day — it is not |
| 6 | Midnight clamp exists but only via the station-wide flag; scoped requests ignore it | **AGREE** | `:82-89` signature + `$enabled = $resetAtMidnight && !$scoped`; `:110-116` clamp + `>=` vs `>`; `:129` flag; `:358-363` call site; response `:392-397` | a request-level param already existing — it does not |
| 7 | `Date = :d` is sargable, `DATETIME(Date||' '||Time) >= …` is not | **AGREE — and UNDERSTATED** | `EXPLAIN QUERY PLAN` against the real `scripts/createdb.sh:5-20` schema: `Date = '2026-09-02'` → `SEARCH detections USING INDEX detections_Date_Time (Date=?)`; the current rolling predicate → `SCAN detections`. So **today's `recent` already full-scans on every poll**. Precedent `case 'hourly'` `:571-595` | the planner choosing the index for the expression form |
| 8 | `Date`/`Time` come from the recording filename; `as_of` is UTC | **AGREE with caveat** | `scripts/utils/classes.py:27-29` `file_date + timedelta(seconds=start)`, `:45-51` naive `strptime`; `as_of = date('c')` at `birdnet-api.php:397`; `:577-581` notes `date.timezone` is UTC on a stock Pi. **Caveat:** nothing in `avian/api/` pins the zone and sibling scripts call `date_default_timezone_set()` (`scripts/common.php:22`, `scripts/config.php:113`) | an API-side `date_default_timezone_set()` — absent |
| 9 | `AVIAN_STATION_TIMEZONE` reaches PHP | **Delivery AGREE; last hop UNPROVEN** | `env AVIAN_STATION_TIMEZONE $AVIAN_STATION_TIMEZONE` in **six** blocks (`scripts/update_caddyfile.sh:967,976,985,993,1003,1013`); fpm `clear_env = yes` (`scripts/security_refresh.sh:118`). But `tests/smoke_caddy_generated_routes.sh:129` asserts `$_SERVER[...]` while `educator_station_timezone()` reads **`getenv()`** (`avian/api/educator-store.php:408`); PHP tests inject with `putenv` (`tests/test_educator_backend.php:133,519,539`) — CLI only | an HTTP-level test showing `getenv()` returns empty under FPM; or the reverse, confirming it |
| 10 | `tests/smoke_collage_readiness.mjs` couples to `shoot.py` and pins site blanking | **AGREE** | `:87` `shooter.match(/FRAME_READY = """([\s\S]*?)"""/)`; `:25` `assert.equal(draws.length, 1, 'a successful zero-detection result clears old birds')`; `:19`, `:22` guard loading/malformed cases | the regex no longer matching (i.e. reshaping the literal) |
| 11 | Unscoped `signature()` hash is a frozen contract; use the `scope` slot | **AGREE** | `tests/test_frame_birdweather.py:191-196` re-derives `sha256(json.dumps([(slug, bucket)]))[:16]`; `tests/test_frame_capture.py:218` pins captured-data signatures; `display.py:103-107` `material = [scope, items] if scope else items` | a compat test being removed |
| 12 | Local verification is largely impossible here | **AGREE** | `php: command not found`; `importlib.util.find_spec('fcntl') → None`; PHP checks are `@unittest.skipUnless(shutil.which("php"))` (`tests/test_midnight_reset.py:7`) ⇒ **pass vacuously** | installing PHP / running under WSL |

### Corrections the audit forced (all applied, all re-verified by the parent)

1. `--preview` removed from the "can blank the panel" set — it returns before
   `push_panel`. Was in [`feature-midnight-reset.md`](feature-midnight-reset.md); [`_index.md`](_index.md) fact 9 reworded.
2. Bundle-render failure consequence rewritten: non-zero exit **reverts the selection
   and re-renders**, so a non-zero decline silently undoes the user's bundle switch —
   a stronger reason for exit-0 than "reports failure after activation".
   [`feature-midnight-reset.md`](feature-midnight-reset.md), [`plan-review-midnight-reset.md`](plan-review-midnight-reset.md), [`_index.md`](_index.md) fact 9.
3. "Automatic" bundle render reworded to *on selection change*; `rollback` added as an
   unconditional renderer; hidden `--no-render` noted.
4. `AVIAN_STATION_TIMEZONE` line list corrected 3 → 6 blocks, and the `getenv()` hop
   marked assumed. [`station-clock-and-data.md`](station-clock-and-data.md), [`repo-map.md`](repo-map.md), [`testing-and-ci.md`](testing-and-ci.md).
   (This was the **second** timezone error in the same claim within one session — the
   first, "not exposed to PHP at all", was caught by the parent before the audit.)
5. `Date = :d` recommendation narrowed: must retain the `<= DATETIME(:anchor)` ceiling
   (`avian/api/birdnet-api.php:89`) or the clamp silently changes semantics for skewed /
   future-stamped rows.
6. Gap 1 severity scoped to requirements **9 and 10**; requirement 12
   ("disabled ⇒ unchanged") is untouched by it.

### Confirmed and strengthened by the audit

* The central hazard — an empty window is a **valid, drawable state end to end**, so
  retention must live in the frame and the gate alone is insufficient — survived
  verification intact. The audit called it the most valuable finding.
* "Retain means *don't touch the panel*, not *can redraw*" confirmed: a clamped window
  structurally cannot return yesterday's rows.
* Gap 2 (the API change is a decision, not a question) held under an explicit attempt to
  falsify it: the only frame-only alternative is hour-rounded (barred by the brief) and
  still cannot fix `n`.
* Gap 3 (mode scoping) confirmed with sharper evidence: in `image` mode `run()` still
  calls `fetch_species`→`fetch_recent(base_url)` for the signature (`frame/display.py:430-443`)
  while the pixels come from someone else's render (`:406-415`), so sending a clamp
  param there is incoherent.
* Claim 7 is a broader win than recorded: the current `recent` predicate scans on every
  poll, so the `Date =` form is a general performance improvement, not just a
  new-path detail.

### New findings the audit produced

1. **A cheaper, house-consistent option for the signature/image split.** `birdweather`
   mode already proves it: `_make_api_handler(..., species=species)`
   (`frame/shoot.py:243-257`) serves the frame's own fetched list to the browser, so the
   page's request stops mattering. Doing the same in `local` mode makes signature/image
   agreement **structural with one upstream request** instead of injecting a param in
   two places and hoping they stay in sync. Supporting evidence: `top_file` has **0
   occurrences in `avian/frontend/apt.js`**, and the detail modal is hidden during capture. Cost: the
   payload must carry `sci/com/n`, and the live site is no longer the source of truth
   for the capture. Added to
   [feature-midnight-reset.md](feature-midnight-reset.md#window-options-ranked).
2. **Four brief requirements were unmapped to code** (now added to the requirement→code
   table in [`feature-midnight-reset.md`](feature-midnight-reset.md) and listed in
   [plan-review-midnight-reset.md](plan-review-midnight-reset.md#requirements-still-unmapped-to-code)):
   "do not modify/delete historical detections"; "preserve quiet hours / layout /
   e-ink"; requirement 11's **scheduled** restart vector (`frame/systemd/birdframe.timer`
   `OnBootSec=2min` fires a render ~2 min after a boot following a multi-day outage --
   *Audit 2 correction:* originally also attributed to `Persistent=true`, which is inert
   without `OnCalendar=`); and an owner for "never write the global `RESET_AT_MIDNIGHT`" —
   assertable as *`frame/*.py` must not POST to `avian/api/config.php`*.

### Still unverified (carry these forward as assumptions)

* `getenv('AVIAN_STATION_TIMEZONE')` visibility under real PHP-FPM (claim 9). Needs an
  HTTP-level check on a station or a container with the generated Caddy config.
  *(2026-11-16: moot — under D20 the design uses no station timezone.)*
* Everything the environment blocked: the PHP window contract
  (`tests/test_midnight_reset.php`) *(executed 2026-11-16: 20/20, [R3](verification-log.md#r3-execute-the-clamp-and-param-shape-claims-with-php))*, the
  `frame/display.py`-dependent pytest set (`fcntl`), and any e-ink behaviour. None of these were executed in this session — they are
  **not** verified, and any report claiming otherwise should be challenged.
* Hardware-only questions: heal suppression vs burn-in over a long empty stretch, and
  panel state after a power glitch mid-update.

### Method note (worth reusing)

Two of the strongest corrections came from **re-deriving, not re-reading**: computing the
empty-list hash independently, and running `EXPLAIN QUERY PLAN` against the real schema.
Both are cheap on this box, both produce evidence independent of the prose, and both
caught things a second read of the same file did not.

---

## Audit 2: Reviewer pass over the settled design

* **Date:** 2026-11-16 · **Status:** complete · **Trigger:** operator switched to a
  stronger model and asked for a full soundness/viability review before Plan v0.3.
* **Executor:** one `reviewer` child (`f8005d27-854f-4170-9cee-35a671b5e7af`), read-only,
  no bash, no delegation. Seeded with parent hypotheses H1–H7 plus a general sweep.
* **Method:** source-reading only — no PHP, pytest, Node, container, Playwright or
  hardware was run. The parent then **re-verified each load-bearing counter-claim against
  source** before accepting it (table below).
* **Headline:** no Critical findings — nothing in the settled design blanks a wall *if* the
  guard is keyed on the data. Six High findings changed the contract; **Plan v0.3 is not
  ready** until [D12](open-decisions.md#d12--what-does-nothing-to-draw-mean-for-the-d1-decline)–[D16](open-decisions.md#d16--no-validated-list-fetch-failed-or---no-signature-with-the-flag-on) are ruled ([open-decisions.md](open-decisions.md)).

### Hypothesis verdicts

| # | Hypothesis | Verdict | Key evidence | Design consequence |
|---|---|---|---|---|
| H1 | Non-empty but undrawable today-window hangs capture | **CONFIRMED** | `frame/display.py:132-150` (local ignores `drawable`); `avian/frontend/apt.js:3181-3190` (maskless tiles dropped; *drop is precisely `:3179,3186` — corrected by R5*), `:1611-1614` (`loadMask` null); `:3359` (`finishFrameRender` needs `placed.length`); `:3124` (empty nest only when `!items.length`); `frame/shoot.py:517-521` timeout; `display.py:464-466`; `frame/bundle_runtime.py:1962-1972,1993-2000` revert | [D1](open-decisions.md#d1--may-a-forced-render-draw-an-empty-today-window-collage) must key on **drawable**, not empty → **[D12](open-decisions.md#d12--what-does-nothing-to-draw-mean-for-the-d1-decline)**. Pre-existing for rolling windows; today-only makes it common. Mixed lists are fine. Second, pre-existing hang not worsened here: a tile still unplaced after 10 shrink passes (`x=-99999`) breaks `collagePlaced.length === placed.length` the same way. |
| H2 | `Date =` form vs `recentWindow` are two contracts | **CONFIRMED** | `avian/api/birdnet-api.php:91-99,104-116`; `tests/test_midnight_reset.php:38-40` pins "short window inside the day stays rolling"; `display.py:51` `hours` user-settable | Pick one → **[D13](open-decisions.md#d13--does-the-today-window-respect-the-hours-setting)**. Req 1 ("starting at 00:00") literally fits only the `Date =` form. |
| H3 | Birdweather served-list pattern is drop-in for local | **PARTIAL** | `shoot.py:250-256` answers `recent` with `{hours, species, as_of}` only and everything else with `{}`; `apt.js:6065` `applySiteName` needs `site_name`; `tests/test_frame_capture.py:177-185` pins `educator_scope` pass-through | Needs a local variant: full response, other actions continued, flag-gated → **[D17](open-decisions.md#d17--the-local-mode-served-list-variant)**. Handshake (`frame_capture_id`, `shoot.py:272-275`) and `small_floor` unaffected; captured-signature invariant (`display.py:458-463`) becomes trivially true. |
| H4 | [D5](open-decisions.md#non-blocking--decided-by-the-parent-from-house-style-to-be-proposed-in-the-pr)'s degraded-station signal is definitive | **REFUTED** | response `reset_at_midnight` = `global && !scoped` (`birdnet-api.php:90,95,118`); `midnight_clamped`/`window_start` always present (`:392-397`) | Distinct echo field + exit-code choice → **[D14](open-decisions.md#d14--how-is-an-un-updated-station-detected-and-with-what-exit-code-supersedes-d5)** (supersedes D5). |
| H5 | [D6](open-decisions.md#non-blocking--decided-by-the-parent-from-house-style-to-be-proposed-in-the-pr) salt + state are safe | **PARTIAL (safe)** | frozen test only checks the unscoped hash (`tests/test_frame_birdweather.py:193-197`); bundle re-hash after `signature()` (`display.py:438-441,459-463`); `fetch_recent` returns only `data["species"]` (`display.py:100`); `save_state` only after `push_panel` (`:477-481`) | D6 optional; [D7](open-decisions.md#non-blocking--decided-by-the-parent-from-house-style-to-be-proposed-in-the-pr)/[D9](open-decisions.md#non-blocking--decided-by-the-parent-from-house-style-to-be-proposed-in-the-pr) need no mechanism; **never `save_state` on a decline**; metadata needs a flag-only fetch helper. Toggle on/off costs one refresh; no `state.json` reset needed. |
| H6 | [D4](open-decisions.md#d4--what-environment-is-the-acceptance-gate) fake station is straightforward | **REFUTED (as documented)** | `php -S` = SAPI `cli-server`, all overrides gated on `cli` (`avian/api/educator-store.php:39,46,52,101,421,492`; `avian/api/educator-state.php:23,30`); lock before profile check (`avian/api/educator-scope.php:148-157`); paths (`birdnet-api.php:35-36`); clock from SQLite `localtime` (`:280,294-296`); `scripts/createdb.sh:2-3,22-23` not runnable as a fixture; `frame/requirements-frame.txt:5` pulls `inky`→`spidev` | D4 *ruling* stands; its elaboration amended (D4 note). DST cases drop out under the `Date =` form. |
| H7 | Every brief requirement maps to the design | **PARTIAL** | reviewer's requirement table | Holes: undrawable-only (req 3–6 → D12), capture without a list (req 8 → **[D16](open-decisions.md#d16--no-validated-list-fetch-failed-or---no-signature-with-the-flag-on)**), Educators automatic scope (req 8 → **[D15](open-decisions.md#d15--educators-capture-active-while-reset_at_midnight-is-on)**), served-list gating (req 12 → D17). `case 'recent'` must re-send `Cache-Control` (sent at `:169-171` before the `switch`). |

### Findings by severity

**High** — F-H1 guard keys on empty, not drawable (→ [D12](open-decisions.md#d12--what-does-nothing-to-draw-mean-for-the-d1-decline)) · F-H2 two window contracts
(→ [D13](open-decisions.md#d13--does-the-today-window-respect-the-hours-setting)) · F-H3 capturing without a list lets the page fetch the rolling window and mixes
days (→ [D16](open-decisions.md#d16--no-validated-list-fetch-failed-or---no-signature-with-the-flag-on)) · F-H4 Educators automatic scope overrides the frame
(`avian/api/educator-scope.php:182-191`, `avian/api/educator-store.php:1108-1112`; → [D15](open-decisions.md#d15--educators-capture-active-while-reset_at_midnight-is-on)) · F-H5 [D5](open-decisions.md#non-blocking--decided-by-the-parent-from-house-style-to-be-proposed-in-the-pr) signal
wrong (→ [D14](open-decisions.md#d14--how-is-an-un-updated-station-detected-and-with-what-exit-code-supersedes-d5)) · F-H6 [D4](open-decisions.md#d4--what-environment-is-the-acceptance-gate) fake station not viable as written (D4 amended).

**Medium** — F-M1 [D2](open-decisions.md#d2--which-frame-modes-does-the-feature-apply-to) activation test also matches `image` mode (D2 amended) · F-M2
served list not stated as flag-gated (→ [D17](open-decisions.md#d17--the-local-mode-served-list-variant)) · F-M3 degraded-station exit code
unspecified (→ D14) · F-M4 docs still said "inject in both places" (fixed) · F-M5
`plan-review` Gap 7 #11 false for local mode (fixed) · F-M6 tri-state param invites `=0`
overriding the global flag ([D3](open-decisions.md#d3--station-api-additive-request-param-name-and-shape) amended: only `1` counts).

**Low** — [`frame-refresh-decision.md`](frame-refresh-decision.md) "empty nest when zero *drawable*" was wrong (fixed) ·
`Persistent=true` misattributed in 5 places; inert without `OnCalendar=` (fixed) ·
[`station-clock-and-data.md`](station-clock-and-data.md) still said `as_of` "is UTC" (fixed) · line drift: preview
return `frame/display.py:469-474`, `push_panel` `:477`, Cache-Control `avian/api/birdnet-api.php:169-171`
(fixed) · a 3.11-only container doesn't exercise Python 3.9 · `run()` complexity vs flake8 *(2026-11-16: moot — upstream `run()` is already 18 and the gate is not enforced for the parent's branch)*
15 · date typo 2025→2026 in [`testing-and-ci.md`](testing-and-ci.md) (fixed).

**Simpler-path notes** — [D7](open-decisions.md#non-blocking--decided-by-the-parent-from-house-style-to-be-proposed-in-the-pr)/[D9](open-decisions.md#non-blocking--decided-by-the-parent-from-house-style-to-be-proposed-in-the-pr) need no mechanism (no new `state.json` keys); [D6](open-decisions.md#non-blocking--decided-by-the-parent-from-house-style-to-be-proposed-in-the-pr) optional;
extend the existing `frame-capture` CI job instead of adding one; `action=hourly`
already aggregates by station day but caps at 30 species (`birdnet-api.php:584`) and has
no anchor ceiling, so it is not a drop-in.

### Parent re-verification of the counter-claims

| Counter-claim | Parent check | Result |
|---|---|---|
| Lock taken before the Educators-enabled check | read `avian/api/educator-scope.php:148-157` | **holds** — the comment says it guards crash-mid-restore |
| Test overrides are `cli`-only | grep `PHP_SAPI` in `avian/api/educator-store.php`, `avian/api/educator-state.php` | **holds** — 8 sites, all `=== 'cli'` |
| Automatic scope during an active capture | read `educator-scope.php:180-193` | **holds** — `$automatic = true` from `educator_current_capture_row` |
| `--no-signature` never fetches in local mode | read `frame/display.py:377-384,418-432` | **holds** — only birdweather re-fetches when `species is None` |
| Page re-fetches `recent` itself when no list is served | read `frame/shoot.py:254-262` | **holds** |
| `avian/frontend/apt.js` "since midnight" label keys on `midnight_clamped` | read `apt.js:3605-3612` | **holds** |
| `Persistent=true` inert here | `frame/systemd/birdframe.timer:9-13` has no `OnCalendar=`; systemd applies `Persistent=` to calendar timers only | **holds** |
| [D2](open-decisions.md#d2--which-frame-modes-does-the-feature-apply-to) precedent at `frame/bundle_runtime.py:479` | that line is `_safe_dir` | **citation wrong, substance right** — real precedent `bundle_runtime.py:433,474`, `frame/config_contract.py:75` |

### Corrections applied from this audit

Register: [D2](open-decisions.md#d2--which-frame-modes-does-the-feature-apply-to), [D3](open-decisions.md#d3--station-api-additive-request-param-name-and-shape), [D4](open-decisions.md#d4--what-environment-is-the-acceptance-gate) amended; [D5](open-decisions.md#non-blocking--decided-by-the-parent-from-house-style-to-be-proposed-in-the-pr) superseded; [D6](open-decisions.md#non-blocking--decided-by-the-parent-from-house-style-to-be-proposed-in-the-pr)/[D7](open-decisions.md#non-blocking--decided-by-the-parent-from-house-style-to-be-proposed-in-the-pr)/[D9](open-decisions.md#non-blocking--decided-by-the-parent-from-house-style-to-be-proposed-in-the-pr) annotated; [D12](open-decisions.md#d12--what-does-nothing-to-draw-mean-for-the-d1-decline)–[D16](open-decisions.md#d16--no-validated-list-fetch-failed-or---no-signature-with-the-flag-on) opened; [D17](open-decisions.md#d17--the-local-mode-served-list-variant)
parent-decided. Docs: [`_index.md`](_index.md), [`feature-midnight-reset.md`](feature-midnight-reset.md), [`frame-refresh-decision.md`](frame-refresh-decision.md),
[`plan-review-midnight-reset.md`](plan-review-midnight-reset.md), [`station-clock-and-data.md`](station-clock-and-data.md), [`test-environment.md`](test-environment.md),
[`testing-and-ci.md`](testing-and-ci.md), [`frame-pipeline.md`](frame-pipeline.md), [`birdnet-api.md`](birdnet-api.md), this log, and [`AGENTS.md`](../../AGENTS.md).

### Still unverified after Audit 2

* Playwright 1.62.0 on Debian 12; whether the GitHub runner image ships `php` + sqlite3
  *(runner part answered by [R2](verification-log.md#r2-does-the-parents-ci-already-run-the-php-contract))*.
* That SQLite flattens the unscoped `CREATE TEMP VIEW detections AS SELECT d.rowid AS
  detection_id, d.* FROM main.detections d` (`educator-scope.php:486`) and still uses
  `detections_Date_Time`. The Audit 1 `EXPLAIN QUERY PLAN` evidence was taken against the
  base table, not the view the API actually queries. Very likely; not proven.
  *(2026-11-16: moot — the `Date =` optimisation was dropped under D20.)*
* How often a day's first detection lacks illustration art (drives [D12](open-decisions.md#d12--what-does-nothing-to-draw-mean-for-the-d1-decline)'s urgency).
* Everything in Audit 1's "still unverified" list remains open.

---

## D18 migration: reference refactor and checker

* **Date:** 2026-11-16 · **Executor:** parent (no child agent) · **Ruling:**
  [D18](open-decisions.md#d18--knowledge-base-reference-conventions-linking) (hybrid).
* **Tool:** `.pi/tools/check_kb.py` — validates doc links + GitHub-rule anchors, flags bare
  doc mentions, resolves every backtick source ref (full path, unique basename, ambiguous,
  missing, or runtime file), checks cited line numbers are within the file, and with
  `--index` regenerates [_references.md](_references.md). Standard library only;
  flake8-clean against the repo's own `.flake8` (it would otherwise have failed the
  `.github/workflows/python-ci.yml` complexity gate had `.pi/` been committed — the first draft's `check()`
  scored 35 against a limit of 15).
* **Method:** baseline run → 5 hand fixes for judgement calls → one-off migration script
  (rewrote only code spans and prose; skipped headings, fenced blocks, existing links;
  deleted after use) → re-run → **integrity proof**: after undoing the three intended
  transforms, all 19 files were byte-identical to the pre-migration backup and every table
  kept its row count.

| Measure | Before | After |
|---|---|---|
| errors | 5 | 0 |
| warnings | 289 | 0 |
| doc→doc links added | — | 54 |
| source refs normalised to full path (first use per section) | — | 225 |
| decision IDs linked (first use per section) | — | 118 |

### Real defects the checker found (not style)

1. **Wrong path since session 1:** [birdweather-source.md](birdweather-source.md) cited
   *tests/test_ebird_credentials.py* (quoted in italics because it does not exist); the file
   is `frame/test_ebird_credentials.py`. No human
   review pass (including Audits 1 and 2) caught it.
2. **Two genuinely ambiguous refs** in [repo-map.md](repo-map.md): *config.php* and *spectrogram.php*
   each exist in `scripts/` and `avian/api/`. Now `avian/api/config.php`,
   `avian/api/spectrogram.php`.

### Defects in the parent's own work, found and fixed during the migration

1. `lstrip("./")` strips *characters*, not a prefix — it silently turned `.github/...` into
   `github/...`. Fixed with an explicit prefix loop.
2. **Status in decision headings made every decision link brittle**: the status is part of
   the anchor, so ruling on D12 (`OPEN` → `ANSWERED`) would have broken every inbound link.
   All 12 decision headings now carry status on a `**Status:**` line instead; inbound
   anchors rewritten in 9 docs. Rule recorded at the top of the register.
3. **The reverse index undercounted**: decision IDs were counted only outside links, so the
   migration's own 118 decision links vanished from the index (D3 appeared cited by one doc).
   The checker now counts link text.
4. The heading-rewrite regex ended in `\s*$` under `re.M` and **swallowed the blank line**
   after all 12 headings, merging each `**Status:**` line into the following paragraph.
   Restored.

### Conventions now enforced (also in [AGENTS.md](../../AGENTS.md))

Doc→doc references are markdown links; source refs stay backtick `path:line` with the full
repo path on first use per section; headings stay plain text; decision status never in a
heading; `python .pi/tools/check_kb.py --index` must exit 0 at the end of every session.

---

## D19 build: kb-document skill and extension

* **Date:** 2026-11-16 · **Executor:** parent · **Ruling:**
  [D19](open-decisions.md#d19--make-the-documentation-duty-fire-automatically-skill-vs-extension)
  (extension + skill; operator-chosen trigger words; trust to be approved on next start).
* **Research basis (installed Pi 1.5.2 docs):** skills are listed by name + description and
  loaded at the model\x27s discretion (`skills.md`: "A model might fail to load a relevant
  skill"); extensions get deterministic hooks — `input` / `before_agent_start` see the raw
  prompt and can inject a message, `agent_before_settle` can append entries and request one
  continuation (`extensions.md`). Project `.pi/extensions|skills|prompts` load only after
  project trust (`configuration.md`, `security.md`); AGENTS.md loads regardless. This repo had
  **no saved trust decision** and `defaultProjectTrust` unset (⇒ ask).
* **Built:** [SKILL.md](../skills/kb-document/SKILL.md) (single source of the procedure;
  AGENTS.md now defers to it), `.pi/extensions/kb-document/index.ts` + pure `src/core.ts`,
  `/kb-check` command, and `check_kb.py --verify-index` (no-write staleness check — needed
  because the settle hook must not silently rewrite files).

### Evidence

| Check | Result |
|---|---|
| `node --test "test/*.test.ts"` (Node v25.1.0) | **20/20 pass** — 11 pure-logic (trigger words incl. negatives such as `document.querySelector`, *recordings*, URLs, fenced code; audit phrases; frontmatter strip; snapshot diff; bounded verdicts; root search never climbs past a `.git`), 9 wiring tests driving the real `index.ts` through a fake `pi` (injection, exit-0 decline semantics, retry cap = 2 then gives up, missing Python never blocks, inert outside the repo) |
| Real Pi load: `node .pi/extensions/kb-document/test/verify-in-pi.mjs` | **PASS** — `pi --mode rpc --no-session -ne -e … -ns --skill …` + `get_commands` lists `extension:kb-check` and `skill:kb-document`, no load error; no model request made |
| `check_kb.py --verify-index` | exit 0 on a fresh index; exit 1 naming `_references.md` after tampering; restored |
| flake8 on `check_kb.py` with the repo `.flake8` | clean |

### Defects found along the way

1. First wiring test of `findRepoRoot` failed on Windows: expected `/r`, got `\r` — a
   POSIX-only test expectation, not a logic bug; fixed with `path.join`.
2. Mid-test, the shell ran under **cmd.exe**, so `T=…` never assigned; a tamper line was
   appended to `_references.md` but the backup/restore failed. Recovered exactly by
   regenerating the (generated) index, then re-run under `bash -lc`. Recorded as a shell trap
   in AGENTS.md.

### Not yet verified

* Live behaviour in a trusted interactive session: that the injected message reaches the
  model, that `ctx.ui.notify` appears, and that an `agent_before_settle` continuation fires
  on a real failing check. Requires the operator to grant project trust (D19 ruling) and one
  deliberate test: say "document this" with a broken link planted in a scratch KB doc.
* Keyword false positives in real use (e.g. "record" as a noun) — tune `TRIGGERS` in
  `src/core.ts` if it fires too often.

---

## D20 research: how the parent repo makes changes like ours

* **Date:** 2026-11-16 · **Executor:** parent · **Trigger:** operator principle
  [D20](open-decisions.md#d20--guiding-principle-minimal-footprint-aligned-with-the-parent-repo)
  (align with upstream, smallest change). Output: [minimal-footprint.md](minimal-footprint.md).
* **Method:** `git log -S` / `git show --stat` over upstream history, then direct reads of the
  code paths each shrink relies on. No PHP available here, so PHP behaviour is argued from
  the code and the language semantics and **flagged for execution** (R3).

| Claim | Evidence | Status |
|---|---|---|
| Upstream's station midnight reset was `f1cb3add` (7 files, +112/−13) with tests in `1092b969` (`tests/test_midnight_reset.php` +85, `tests/test_midnight_reset.py` +23) | `git show --stat` | verified |
| `$RESET_AT_MIDNIGHT` is used in exactly 2 places: the cache header and the `recentWindow` call | grep: `avian/api/birdnet-api.php:129` (set), `:169`, `:362` | verified ⇒ the station change can be 1 line |
| Upstream's param idiom is `$_GET['x'] ?? default` with a cast or strict compare | `avian/api/birdnet-api.php:135,281,356,403-406,434,465,508` | verified |
| An array param (`reset_at_midnight[]=1`) cannot satisfy `=== '1'` | PHP semantics: an array is never identical to a string | argued; not executed (no `php`) |
| `recentWindow` with `hours=24` always clamps a today window to midnight | `avian/api/birdnet-api.php:104-116`: clamped iff `DATETIME(anchor,'-24 hours') <= DATETIME(anchor,'start of day')`; the anchor is within today, so always true; upstream test "24 hour window clamps after midnight" | argued + upstream-pinned; execute in R3 |
| Upstream already re-signs from exactly what the page drew, in both capture paths | `frame/display.py:457-463`; `frame/shoot.py:272-275` sets `capture["species"]` from the response the page received | verified ⇒ D17's premise is already handled upstream |
| The frame's default `hours` is 24 and is threaded to both the fetch and the capture | `frame/display.py:49,150,399` | verified |

### Consequences recorded

Parent-decided shrinks: D13 implementation (reuse `recentWindow`), D3 mechanics (1-line OR,
upstream idiom), D14 detection (existing `midnight_clamped`), D15 (no code); D6 and the
`Date =` optimisation dropped. Re-opened for the operator: D17 and D4's new-CI-job clause.

### Defects in the parent's own work during this step

1. The first attempt to append this section used a heredoc inside `bash -lc '...'`; the
   apostrophe in "Upstream's" closed the quoting and bash aborted before running — nothing
   was written. AGENTS.md already says to put large content in a file with the write tool;
   this is the second time that rule would have prevented a failure.
2. `check_kb.py`'s decision pattern was `D(1[0-9]|[1-9])`, capped at D19, so D20 was invisible
   to the reverse index ("19 decision IDs cited" with 20 in the register). Widened to any one- or two-digit ID, and the checker now indexes only IDs that exist in the
   register (an unknown ID is a warning) — which is how this very sentence, in its first
   form, was caught creating a phantom decision ("D-99", hyphenated here so it is not
   counted again).

---

## R2: does the parent's CI already run the PHP contract?

* **Date:** 2026-11-16 · **Executor:** parent (web research, no child agent) · **Trigger:**
  operator answer to the re-opened D4 CI clause: *"Decide after research R2."*
* **Sources:** `actions/runner-images` — `images/ubuntu/Ubuntu2404-Readme.md` (image
  `20261111.370.1`), `images/ubuntu/Ubuntu2604-Readme.md` (image `20261111.196.1`),
  `images/ubuntu/scripts/build/install-php.sh`, `images/ubuntu/toolsets/toolset-2404.json`,
  and issue #14748 (the `ubuntu-latest` → 26.04 notice). Local:
  `.github/workflows/python-app.yml:17,32`, `tests/test_midnight_reset.py`.

| Claim | Evidence | Status |
|---|---|---|
| Parent CI jobs run on `ubuntu-latest`; no parent workflow installs PHP | `.github/workflows/python-app.yml:17,32`; no `php` in `.github/workflows/` | verified locally |
| `ubuntu-latest` (24.04) ships PHP 8.3.6 | Ubuntu2404 README "PHP Tools" | documented |
| `ubuntu-latest` is moving to 26.04 in November 2026; 26.04 ships PHP 8.5.4 | runner-images announcement / issue #14748; Ubuntu2604 README | documented |
| PHP's SQLite3 extension is installed on both | `install-php.sh` apt-installs a hard-coded module list including `php$version-sqlite3` for every toolset version; toolset 2404 lists `"versions": ["8.3"]` | documented (build script) |
| ⇒ the parent's `build` job already executes `tests/test_midnight_reset.php` for real | `tests/test_midnight_reset.py` is `skipUnless(shutil.which("php"))`, and php is on PATH | **inferred** — not observed in a real parent CI run log; also assumes `build` is green today |

**Consequence:** feature tests added to the parent's *existing* test files run in parent CI
with no workflow change. Only the fake-station + fake-panel end-to-end harness needs the
`.pi/` container. Final D4 CI-clause answer recorded in the register.

---

## R1: station parameter variant (deep-research brief + reviewer)

* **Date:** 2026-11-16 · **Workflow:** `deep-research` skill, adapted (output in `.pi/outputs/`
  per D20; no `verifier` agent exists, so one `reviewer` child verified). **Brief:**
  [../outputs/r1-station-param-variant.md](../outputs/r1-station-param-variant.md) (revision 2) ·
  **provenance:** [../outputs/r1-station-param-variant.provenance.md](../outputs/r1-station-param-variant.provenance.md).
* **Answer:** variant **B′** — one new local
  `$resetAtMidnight = $RESET_AT_MIDNIGHT || (($_GET['reset_at_midnight'] ?? null) === '1')` in
  the request-derived block of `avian/api/birdnet-api.php` (`:131-136`), swapped in at `:169`
  (cache header) and `:362` (`recentWindow`). +1 line added, 2 modified. Ranking B′ > B > A > C.
* **Evidence method:** parent gathered locally (scan of all top-level variables in
  `avian/api/*.php`; `git show` of `116471c1` and `f1cb3add`; `git log -L` churn on lines
  129/169/362; reads of the frame fetch and capture paths and of the Caddy and forwarding configs).
* **Reviewer:** run `199f88cc-69de-4453-bf68-b7dac284e421`, read-only, no git, no `php`. Verdict
  **OK with notes.**

| Claim | Reviewer | Parent re-check | Effect on the brief |
|---|---|---|---|
| E1 UPPER_CASE = config only | PARTIAL — 18 names / 30 sites, not 15 / 24; missed `$EXTRACTED` (request-gated, server-env value) | held: `avian/api/export.php:450-459` | counts corrected; claim narrowed to "no client data" |
| E2 camelCase request locals at `:131-136` | CONFIRMED | — | none |
| E3/E4 cache-header idiom; reset ⇒ `no-store` | CONFIRMED in source; commit attribution unverifiable without git | parent's `git show` stands | none |
| E5 no cache layer for the frame | CONFIRMED and strengthened (`route.fetch`, `avian/frontend/apt.js` `cache: 'no-store'`, no caching in forwarding configs) | — | strengthened |
| E6 two consumers of `$RESET_AT_MIDNIGHT` | CONFIRMED in source; churn unverifiable without git | parent's `git log -L` stands | none |
| E7 param read not testable like upstream | PARTIAL — **wrong**: upstream's `edu_endpoint` harness reaches the full endpoint | held: `tests/test_educator_backend.php:64-76,664-668` | corrected; test placement left to Plan v0.3 |
| E8 `=== '1'` shape | CONFIRMED, but **omitted** PHP key mangling and last-wins duplicates, contradicting D3's amendment | held: [open-decisions.md](open-decisions.md) D3 amendment bullet 1 | acknowledged; D3 amended by D20/R1 |
| Ranking | **P1:** C is not a fallback — it drops D3's `no-store` requirement; rank B′/B > A > C | agreed | re-ranked |
| Missed variant | B′ (`$resetAtMidnight`), which is what the R1 row originally specified | held: [minimal-footprint.md](minimal-footprint.md) R1 row | B′ adopted; client-specific name `$frameResetRequested` dropped |

### Findings recorded elsewhere

* Every variant changes the meaning of the `reset_at_midnight` response field to "station flag
  OR param, not scoped" — no reader in the repo; noted in [birdnet-api.md](birdnet-api.md).
* A, B and B′ send `no-store` on **every** action carrying the param (header set before the
  `switch`) — parity with the global flag; requests without the param are unchanged (D3 rule).

### Propagation

The parent's earlier claim "the whole station change can be one line" (D20 research section
above) was superseded. It was updated in [_index.md](_index.md) (fact 16 and open threads),
[minimal-footprint.md](minimal-footprint.md) (D3 mechanics row, R1 row, estimated diff),
[feature-midnight-reset.md](feature-midnight-reset.md) item 3, and the register (D3 amendment). The D20 section above is kept as written, as history.

### Still unverified

~~E8's mangling/duplicate behaviour and the `hours=24` clamp are argued, not executed.~~
Executed by [R3](verification-log.md#r3-execute-the-clamp-and-param-shape-claims-with-php) — all held.

---

## R3: execute the clamp and param-shape claims with PHP

* **Date:** 2026-11-16 · **Executor:** parent · **Operator choices:** run R3 in WSL Ubuntu →
  WSL2 could not start → *"scoop install php"*.
* **Environment found:** `wsl -d Ubuntu` fails with
  `Wsl/Service/CreateInstance/CreateVm/HCS/HCS_E_HYPERV_NOT_INSTALLED` (Virtual Machine Platform /
  virtualization not enabled). Docker Desktop needs the same, so the D4 container is blocked here
  (inferred, not started). Recorded in [test-environment.md](test-environment.md) and the D4 entry.
* **Environment set up:** `scoop install php` → PHP **8.5.12** (CLI, ZTS, x64), per-user, no admin.
  Scoop sets the user env var `PHP_INI_SCAN_DIR`, but its `php.ini` leaves `sqlite3` commented and
  uses a relative `extension_dir`. Added one drop-in,
  `~/scoop/persist/php/cli/conf.d/zz-avian-sqlite3.ini` (absolute `extension_dir` +
  `extension=sqlite3`), to match GitHub's runner, which loads SQLite3 (R2). Nothing in the repo
  changed. Undo: delete that file; `scoop uninstall php`.
* **Scripts (kept for reproducibility, our tree only):** `.pi/research/r3/clamp_check.php`,
  `.pi/research/r3/param_check.php`, `.pi/research/r3/www/echo.php`.

| Check | Result | Notes |
|---|---|---|
| Parent suite `tests/test_midnight_reset.php`, unmodified | **20/20 pass** | first-ever execution of this contract in this project |
| Parent suite `tests/test_site_name_api.php`, unmodified | **6/6 pass** | same library-mode include |
| Parent pytest wrapper `tests/test_midnight_reset.py` | **1 passed** (was a vacuous skip) | in a new-shell environment; see the side effect below |
| (a) Clamp: `recentWindow(hours=24, reset on, today)` | **30/30** | clamps to that day's `00:00:00` at 8 anchors (00:00:00, 00:00:01, 06:30, 12:00, 23:59:59, US DST date 2026-03-08, fall-back hour 2026-11-01 01:30, leap day 2028-02-29); contrast cases `hours=12`, ALL, reset off and educator scope do **not** clamp; rows: yesterday 23:59:59 excluded, `00:00:00` included, anchor included, anchor+1s excluded; reset off keeps yesterday's row (the bug the feature fixes) |
| (b) Param shape: `$RESET_AT_MIDNIGHT \|\| (($_GET['reset_at_midnight'] ?? null) === '1')` | **38/38**, identical in `parse_str` and a **real HTTP request via `php -S`** | only exact `1` (incl. `%31`) is true; absent, `0`, empty, key-only, `true`, `01`, trailing space, `RESET_AT_MIDNIGHT=1` (case-sensitive key), `x[]=1`, `x[k]=1` are false; `reset.at.midnight=1` and `reset at midnight=1` are **mangled to `reset_at_midnight` and true**; duplicates: **last wins**; station flag ON can never be switched off by the request |

### Claims this converts from "argued" to "executed"

* R1 brief E7 (the clamp the design relies on) and E8 (param shape, incl. mangling and last-wins)
  — [../outputs/r1-station-param-variant.md](../outputs/r1-station-param-variant.md).
* D13's implementation via `recentWindow` reuse and `hours=24` (minimal-footprint, D20 audit).
* The D3 amendment by D20/R1 (mangled aliases honoured, harmless).

### Side effect found and fixed

Installing PHP flipped `tests/test_midnight_reset.py` from **skip** to **fail** in this shell:
`Class "SQLite3" not found`, because the shell predated scoop's `PHP_INI_SCAN_DIR` and the
`php.ini` didn't load SQLite3 anyway. Fixed by the drop-in `.ini`; verified `1 passed` with the
new-shell environment. Documented in AGENTS.md (verification honesty) and as hard-won fact 17,
so a future agent doesn't read an environment failure as a product failure.

### Defect in the parent's own work

The first clamp run reported 1 failure: the test's *expected* row count for the reset-off
contrast case was wrong (it guessed 2; the rolling window correctly returns 3, including
yesterday's 23:59:59 bird). The product behaved correctly; the expectation was fixed.

### Still unverified

The station change itself (R1 variant B′) is not implemented — ~~building is not authorised~~ (superseded 2026-11-17: G0 lifted; W1 implements it, see [G0 lift](#g0-lift-and-w1-dispatch)) — so
the full endpoint with the real param (e.g. via upstream's `edu_endpoint` harness) is untested.
Everything needing Linux (`fcntl`) or the D4 container is still blocked by the WSL2 finding.

---

## R5: drawable vs base pose (deep-research brief + reviewer + live-feed scan)

* **Date:** 2026-11-16 · **Workflow:** `deep-research` skill, adapted (output in `.pi/outputs/`;
  no `verifier` agent, so one `reviewer` child). **Brief:**
  [../outputs/r5-drawable-base-pose.md](../outputs/r5-drawable-base-pose.md) (revision 2) ·
  **provenance:** [../outputs/r5-drawable-base-pose.provenance.md](../outputs/r5-drawable-base-pose.provenance.md) ·
  **scan:** `.pi/research/r5/manifest_scan.py`.
* **Question:** can a species pass D12's "drawable" check (frame bundle `drawable_slugs`) yet be
  dropped by the collage, recreating the 180-second capture hang?
* **Answer:** **yes, and it is reachable today.** D12's predicate was refined (dated amendment in the
  register): drawable ⇔ some species' unsuffixed slug is a key in the masks table the collage
  loads.

### Revision history: how the answer flipped

| Step | Claim | Status |
|---|---|---|
| Revision 1 | "In principle yes; in practice no" — scan of the vendored catalog + station UI snapshot found 0 species without a base pose | **overstated** |
| Reviewer (`b53c28e4-782b-48a4-bb3e-cd81d20e82c6`, read-only) | **OK with notes.** E1, E1b, E2, E5 confirmed. **P1:** the frame also installs from the **live community feed** (`refresh_catalog`, `frame/bundle_runtime.py:1949-1950,1152-1155`), which was not scanned. **P1:** the parent's exporter can emit flight-only species (`avian/scripts/bundle_export.py:400-401,847`). P2s: upstream's species-level precedent, the `avian/api/bundle-assets.php` route, the station predicate, line refs, scan robustness | — |
| Parent re-check of the P1s | both held (read `frame/bundle_runtime.py:1945-1952,1152-1170,826-839`; `avian/scripts/bundle_export.py:398-409,845-848`) | confirmed |
| Revision 2 scan (vendored + **live feed** + snapshot reference; https, host-pinned, SHA-256 verified, `species` list and `species_count` checked) | **12 unique manifests, 0 problems; `community-peterdeboer-nl-cacd91aeb7749fec` (329 species) has 22 flight-only species**; every other bundle has a base pose for every species | **reverses revision 1** |

### Verified mechanics

* Collage draws only the base slug or `-2`: `avian/frontend/apt.js:3164-3186` (`hasFlight` `:3166`,
  roll `:3172` with `FLY_PROB = 0.15` `:1557`, fallback 2 → base only `:3178`, drop `:3179`,
  `.filter(Boolean)` `:3186`); `loadMask` null when `MASKS[slug]` is absent (`:1611-1614`); numbered
  variants appear only in the postcard picker (`:9439-9445`). Fresh browser per capture
  (`frame/shoot.py:425,434`) ⇒ an independent 15% roll each run.
* No validator or tool requires a base pose (frame install, authoring contract, station installer,
  station PHP, station frontend), and the exporter can produce one — table in the brief, E2.
* With a frame bundle, "has `perched`/`variant-1`" ⇔ "unsuffixed slug is a masks key"
  (`frame/bundle_runtime.py:1455-1458,1883-1889`); `frame/shoot.py:470-482` routes the collage's *dims.json*,
  *masks.json* and `avian/api/bundle-assets.php` requests to the bundle.

### Decision recorded

[D12](open-decisions.md#d12--what-does-nothing-to-draw-mean-for-the-d1-decline) amended
(`PARENT-DECIDED`, refines "drawable" without changing D12a's ruling): option A, the collage's own
drop test. Rejected: A′ ("drawn sometimes" — hangs ~85% of runs) and B (species-level
`drawable_slugs` — unsafe for the Netherlands bundle). `ActiveBundle.drawable_slugs` stays
species-level because upstream uses it for BirdWeather filtering.

### Propagation

Updated: the register (D12 amendment; two inline corrections),
[feature-midnight-reset.md](feature-midnight-reset.md) (retention-guard predicate),
[minimal-footprint.md](minimal-footprint.md) (drawable-decline row; R5 row),
[_index.md](_index.md) (open thread 6; hard-won fact 18; line ref),
[frame-refresh-decision.md](frame-refresh-decision.md) (line ref),
[illustration-bundles.md](illustration-bundles.md) (`drawable_slugs` meaning). The stale citation
*apt.js lines 3181-3190* for the drop was corrected to `avian/frontend/apt.js:3179,3186` wherever it
was asserted (historical rows annotated, not rewritten).

### Defects in the parent's own work

1. Revision 1 scanned the station UI snapshot instead of the frame's real install sources — the
   same "searched the wrong place, then generalised" pattern as the earlier empty-grep timezone
   error. The reviewer caught it; the follow-up scan turned "unverified" into a positive finding.
2. The scan's first form reported a malformed manifest as "0 species" instead of failing; fixed
   (now fails on a missing `species` list, a SHA mismatch, a fetch error, or a count mismatch).

### Still unverified

* The live feed is a 2026-11-16 snapshot; option A is safe regardless of future bundles.
* The station-default path's own masks table was not scanned.
* Not implemented; nothing observed on a live station.

---

## Pre-v0.3 probes: drift, local test loop, capture path, characterization

* **Date:** 2026-11-16 · **Executor:** parent · **Operator-selected:** items 1, 3, 5, 6 of the
  pre-v0.3 list (2, 4, 7, 8 not selected). Artifacts (our tree only, D20):
  `.pi/research/pre-v03/stubs/fcntl.py`, `.pi/research/pre-v03/test_characterize_today.py`.
* **Unprompted findings from the scoping probe:** (a) the `.flake8` complexity limit is **not
  enforced** for the parent's branch — upstream `run()` is already 18, `_make_api_handler` 16,
  `shoot()` 46; `.github/workflows/python-ci.yml` runs only on PRs to `main` (the parent's default
  branch is `avian-visitors`) and `.github/workflows/python-app.yml` gates only `E9,F63,F7,F82` —
  so the inherited "extract a helper to stay under 15" premise was false and has been corrected in
  six places; (b) `windowLabel` ("since midnight" when clamped) is used only in tooltips and the
  Atlas (`avian/frontend/apt.js:3298,3521,5783`), never in the captured collage — the feature does
  not change the frame's picture text.

### Item 1 — upstream drift: none

`git fetch upstream avian-visitors` (2026-11-16): the parent's tip is still `5950f807`
(2026-10-22) — our base. Zero commits we lack. **Every line reference in the knowledge base is
current against the parent.**

### Item 3 — a local frame-test loop works with an `fcntl` stand-in

`PYTHONPATH=.pi/research/pre-v03/stubs` (a no-op `fcntl.flock`, never in the parent's tree):

| Suite | Without the stand-in | With it |
|---|---|---|
| `tests/test_frame_birdweather.py` | 14 passed, 4 errors | **18 passed** |
| `tests/test_frame_capture.py` | 58 passed, 19 errors | **76 passed, 7 failed** |

All 7 failures are POSIX file-mode or symlink assertions (`438` = `0o666`, Windows ignores umask
and chmod bits): `test_new_capture_respects_process_umask` (3 subtests),
`test_replacing_capture_preserves_existing_file_permissions` (3),
`test_capture_does_not_follow_an_output_symlink` (asserts `0o600`). **None touch `run()`**; every
refresh-decision test v0.3 will extend passes (`test_capture_failure_preserves_panel_state…`,
`test_saved_signature_describes_captured_data…`, `test_captured_signature_keeps_the_exact_bundle_selection`,
`test_signature_fetch_rejects_missing_species_not_as_empty`, `test_recent_errors_are_not_rewritten_as_success`,
`test_valid_empty_response_and_scope_metadata_survive`, `test_unscoped_signature_stays_compatible…`,
`test_station_identity_is_part_of_change_signature`). Caveat: the stand-in makes the render lock a
no-op, so lock semantics are not tested locally; CI (Linux) stays authoritative.

### Item 5 — the capture has exactly one injection point for the station param

* The page fetches `recent` in three places, all through `scopedFetchJson` → `birdApiUrl`, which
  always emits `hours=<number>` (`avian/frontend/apt.js:378-387`): `refreshStatsContext`
  (`:5984`, with `date` only when `currentHours >= 1000000` and a stats date is chosen — never in a
  fresh capture context, where `bird:window` defaults to 24, `:1035`), `refreshRecent` (`:6009`),
  `refreshAll` (`:6028`).
* `frame/shoot.py` routes `**/birdnet-api.php**` to `_make_api_handler` (`:448`), which intercepts
  every URL containing `action=recent` (`:250`) and substitutes `hours=\d+` (`:258`). So **one
  edit in that branch covers every `recent` request the page can make**; the substitution
  preserves every other query parameter verbatim (characterization C8).

### Item 6 — characterization of today's behaviour (13/13 pass on unmodified parent code)

`.pi/research/pre-v03/test_characterize_today.py`, written in the parent's own test style
(modules loaded by path, Playwright stubbed, `frame/display.py` collaborators patched):

| ID | Today's behaviour (base `5950f807`) | Decision it bears on |
|---|---|---|
| C1 | **Empty window with yesterday's collage on the glass → capture renders `[]`, panel pushed, state saved with `signature([])`** — the core bug | D1/D12 |
| C2 | `--force` redraws an unchanged window | D1 |
| C3 | `--no-signature` never fetches in local mode; capture gets `species=None` | D16 |
| C4 | `heal_hours` elapsed → redraw of an unchanged empty window | D7 |
| C5 | unreadable state (`signature: None`) + empty window → redraw | D9 / restart |
| C6 | local mode ignores `drawable` (`fetch_species`) | D12 / R5 |
| C7 | `fetch_recent` returns only `species`; `midnight_clamped` etc. are discarded; URL is `…?action=recent&hours=24` | D14 |
| C8 | capture rewrite substitutes `hours` and keeps other params (incl. a would-be `reset_at_midnight=1`) | D3 / D17 |
| — | preserved behaviours: unchanged window skips without touching state; quiet hours skip a real change; a failed push never saves state; non-`recent` actions pass through; no `window_hours` ⇒ no rewrite | D8, D9 |

These tests assert **today's** outcomes; v0.3's tests should show C1–C5 flip under
`reset_at_midnight = true` and stay identical with it `false` (req 12).

### Still unverified

Items 2 (parent CI health), 4 (upstream `edu_endpoint` harness on Windows PHP), 7 (station-default
masks scan) and 8 (throwaway spike) were not selected.

---

## Plan v0.3 Oracle review

* **Date:** 2026-11-16 · **Executor:** one `oracle` child (`45c675ca-9a4c-4139-9511-26faed72037e`),
  forked context, read-only, no tests run. **Plan:**
  [`.pi/reset-after-midnight Plan v0.3.md`](../reset-after-midnight%20Plan%20v0.3.md).
* **Verdict:** **READY WITH EDITS.** The architecture matches every ruling: §4.1 is exactly R1
  variant B′; §4.3 uses the single rewrite point (`frame/shoot.py:258`); §4.4's lookup is right
  (`frame/display.py:80-81` `slugify` and `frame/bundle_runtime.py:1233-1234` `_slug` are the same
  regex). Confirmed: step (d) returns True before the gate on every path, so a bundle `use`
  (`--force --no-signature`) on an empty day keeps the bundle (`frame/bundle_runtime.py:2108-2110`);
  steps (b)/(c) return False on forced paths and revert the bundle (`:1962-1972`), as D14/D16 record;
  (c) before (d) is correct; D13 is met; the 45–60-line footprint is plausible.

| # | Finding | Severity | Parent re-check | Resolution |
|---|---|---|---|---|
| 1 | Step (e) "continue into the unchanged gate" leaves the existing `if use_signature:` block (`frame/display.py:429-443`) calling `fetch_species` **without** the param ⇒ a second, rolling fetch; `changed` (`:445`) decided on the rolling list while the capture draws the clamped one; can delay req 6 just after midnight | **High** | held — read `:429-443` | §4.2 (e) rewritten: the block is skipped when active; `sig` from `payload["species"]` + the bundle salt; exactly one fetch; new tests |
| 2 | No-bundle "only empty declines" silently departs from D12's text ("else the station's mask table") and R5's `slug in MASKS` | Medium | held — [open-decisions.md](open-decisions.md) D12 combined ruling | D12 amended (parent-decided; basis D20 — `avian/frontend/masks.json` ~800 KB — and D12b); §4.4 cites it |
| 3 | §6 claimed the parent's CI runs "on the fork"; pushing the branch triggers nothing | Medium | held — `.github/workflows/python-app.yml` triggers; 0 `workflow_dispatch` | §6 states the real trigger; new **D21** (open, stage V) |
| 4 | Step (e) listed "lock" as part of the gate; the lock is taken in `main()` (`:520-528`) | Low | held | removed; note added |
| 5 | §4.2 item 2 departs from the superseded D17 "flag-only helper" bullet without saying so | Low | held | deviation stated in §4.2 and §9 |
| 6 | Missing tests: D8 (first bird in quiet hours), D1 (preview of an empty day) | Low | — | added to §5 |
| 7 | Brief scenario 9 (timezones) had no named test | Low | — | clock-independence test added |
| 8 | Brief scenario 11 (other clients unchanged) has no parent-CI coverage | Low | — | W1 must record the gap if no `edu_endpoint` test is added |

Also added from the review's risks: §4.5 README must say an outdated station reports failure every
15 minutes, including in quiet hours (D14); §9 notes `core.autocrlf=true` (keep files LF).

**Operator question raised:** D21 (CI via a PR inside the fork) — open, not blocking until stage V.

---

## G0 lift and W1 dispatch

* **Date:** 2026-11-17 · **Who:** parent session (Claude, Pi) · **Environment:** Windows host,
  scoop PHP 8.5, Python with the `.pi/research/pre-v03/stubs` `fcntl` stand-in; no WSL2/Docker,
  no panel, no CI.

### G0: operator go-ahead (quoted)

*"Execute Gate G0 of [Plan v0.3](../reset-after-midnight%20Plan%20v0.3.md) §7 end-to-end on this host … then
(5) dispatch W1 only (§4.1, the three-line station-API change) as a single fresh `worker` child in
this session."* and *"G0 lifts only on the operator's explicit go-ahead, and per the answer this
request is that go-ahead."* **Scope:** W1–W3; stages V and H, §8 deployment, pushes and PRs
remain closed. **D21 deferred** (still `OPEN`, re-ask at V): nothing blocks W1–W3 because §6's
local runs cover this host and a feature-branch push triggers no CI. Recorded as a gate
amendment in [open-decisions.md](open-decisions.md) (no new decision ID).

### Flip of every building-gate location

Grep-verified set flipped with the old text struck through and dated: [AGENTS.md](../../AGENTS.md) feature-freeze
paragraph; [_index.md](_index.md) status line, open threads 5 and 9; [open-decisions.md](open-decisions.md)
gate paragraph + status table; [orchestration.md](orchestration.md) gate section;
[feature-midnight-reset.md](feature-midnight-reset.md) "Decided design"; this log's R3 "Still
unverified"; Plan v0.3 status banner and §9.

### Handoff

`.pi/handoff/plan.md` is generated by section extraction (not restated) from Plan v0.3 §3–§5,
§7, §9 deviations and the register's D1–D4, D12–D17, D20, D21 and non-blocking table (D9), plus
open question Q1 (§5 `edu_endpoint` row — unanswered, owned by W1). `.pi/handoff/ledger.md` uses
the orchestration column set with one row per §7 step. `.pi/handoff/context.md` lists the reads
this session did (`avian/api/birdnet-api.php:135`, `:169-171`, `:358-364`;
`tests/test_educator_backend.php:64-76`). All three committed with `git add -f`.

### W1 result

(pending — filled in when the worker returns)

### Not executed

Docker / D4 container; POSIX file-mode tests (7 known local failures); anything on `birdpic`;
CI (D21 deferred); W2, W3, R, V, O, H.
