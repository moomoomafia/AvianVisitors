# Feature: BirdFrame reset-after-midnight — code ground truth

Feature branch `feature/birdframe-midnight-reset` (this worktree), no source changes
committed yet (`git status` clean apart from untracked `.pi/`).

* Draft brief: [`.pi/reset-after-midnight Plan v0.2.md`](../reset-after-midnight%20Plan%20v0.2.md)
  (v0.1 kept alongside for delta).
* Plan critique, gaps, improvements, open questions:
  [plan-review-midnight-reset.md](plan-review-midnight-reset.md).
* How to run the orchestrated queue here: [orchestration.md](orchestration.md).
* Clock/data provenance: [station-clock-and-data.md](station-clock-and-data.md).

This doc holds only **verified code facts** about the change surface, so it stays
valid across plan revisions.

## Decided design (D1–D4 ruled 2026-11-16; amended by Audit 2)

> **Read [minimal-footprint.md](minimal-footprint.md) first ([D20](open-decisions.md#d20--guiding-principle-minimal-footprint-aligned-with-the-parent-repo), 2026-11-16).** The operator's
> principle — align with the parent repo, change the least code — shrank several items below.
> Where this section and that doc disagree, **that doc wins**; the items are annotated in place.

Rulings live in [open-decisions.md](open-decisions.md); this is the shape they imply.
Building is **still not authorised**. Items marked ⚑ below were opened by Audit 2 and
are now **ruled** ([D12](open-decisions.md#d12--what-does-nothing-to-draw-mean-for-the-d1-decline)–[D16](open-decisions.md#d16--no-validated-list-fetch-failed-or---no-signature-with-the-flag-on), 2026-11-16) — read each ⚑ against its register entry. Audit evidence:
[verification-log.md](verification-log.md#audit-2-reviewer-pass-over-the-settled-design).

1. **Config:** `reset_at_midnight = false` in `~/.birdframe/config.toml`, per-frame,
   default off (operator condition: the user must be able to switch it on/off in config).
   Station-wide `RESET_AT_MIDNIGHT` is never touched.
2. **Scope:** `local` mode only, activated by
   `species_source != "birdweather" and shoot is True` ([D2](open-decisions.md#d2--which-frame-modes-does-the-feature-apply-to) amended — an empty
   `species_source` alone also matches `image` mode). `birdweather` and `image`/`image_url`
   are unsupported and documented; the flag there is a logged no-op.
3. **API** — *R1 form (variant B′, 2026-11-16): a new local
   `$resetAtMidnight = $RESET_AT_MIDNIGHT || (($_GET['reset_at_midnight'] ?? null) === '1')` in
   the request-derived block of `avian/api/birdnet-api.php` (`:131-136`), swapped in at the
   cache header (`:169`) and the `recentWindow` call (`:362`) — 3 lines, runtime-identical to
   the earlier 1-line fold into `$RESET_AT_MIDNIGHT` but keeping that name config-only; the frame sends `hours=24`;
   no new SQL branch, no echo field, detection on the existing `midnight_clamped`. The text
   below is the pre-D20 design, kept for the record:* additive, request-scoped param on `action=recent`; only the exact value `1`
   has an effect (anything else = absent); absent ⇒ identical SQL and headers; educator
   `$scoped` still ignores display preferences; honoured response re-sends `no-store`
   (Cache-Control is emitted before the `switch`, `avian/api/birdnet-api.php:169-171`) and carries a
   **distinct echo field** proving the param was honoured (⚑ [D14](open-decisions.md#d14--how-is-an-un-updated-station-detected-and-with-what-exit-code-supersedes-d5)). Window contract:
   ⚑ **[D13](open-decisions.md#d13--does-the-today-window-respect-the-hours-setting)** (ruled: "everything since midnight") — the station calendar day up
   to the anchor, **ignoring `hours`**, as a separate branch:
   `Date = :station_date AND DATETIME(Date||' '||Time) <= :anchor`; `recentWindow` and its
   pinned test stay untouched; echo `window_start = "<date> 00:00:00"` and
   `midnight_clamped: true`. *(Rejected: `recentWindow` reuse, which respects `hours`.)*
4. **Render path ([D17](open-decisions.md#d17--the-local-mode-served-list-variant)):** when the flag is on, the frame fulfils the page's `recent`
   request with its **full** fetched response (incl. `site_name`, `educator_scope`) plus
   `frame_capture_id`, and still `continue_()`s every other action to the station. With
   the flag off, `_make_api_handler` is unchanged. Signature and drawn collage therefore
   come from one response. This supersedes injecting the param in two places.
   > **Superseded (operator, 2026-11-16): use the parent repo's flow — D17.** Re-opened by D20 because
   > upstream already re-signs from what the page was served
   > (`frame/display.py:457-463`), so the upstream-aligned alternative — keep the page's own
   > station request and add the param to the existing `hours=` rewrite
   > (`frame/shoot.py:258`) — is a candidate. Awaiting operator re-confirmation / A/B R4.
5. **Retention guard:** decided **before capture**, applies to *every* forced path
   (`--force`, `--no-signature`, `avian-bundle use`/`rollback`, `birdframe-names`), and
   **exits 0** for the steady-state "nothing to draw today" case — a non-zero exit would
   make `use`/`rollback` revert the bundle selection and re-render
   (`frame/bundle_runtime.py:1962-1972`). Predicate (⚑ **D12**, ruled): *no drawable species*,
   not merely an empty list (a non-empty undrawable list hangs capture and exits 1).
   Drawable = the active **frame bundle's** `drawable_slugs` (the operator's setup) else the
   station's mask table; if that can't be determined, proceed as today. With the flag on,
   never capture without a validated, honoured list (⚑ **D16**, ruled: timer run skips with
   exit 0, forced run exits 1). Outdated station (⚑ **D14**, ruled): hold and **exit 1**.
   During an Educators automatic scope (⚑ **[D15](open-decisions.md#d15--educators-capture-active-while-reset_at_midnight-is-on)**) hold rather than mix days. A decline **never**
   calls `save_state`. `--preview` is exempt: it returns before `push_panel`
   (`frame/display.py:469-474`).
6. **State:** no new `state.json` keys ([D9](open-decisions.md#non-blocking--decided-by-the-parent-from-house-style-to-be-proposed-in-the-pr) amended); the data-keyed guard already covers
   heal ([D7](open-decisions.md#non-blocking--decided-by-the-parent-from-house-style-to-be-proposed-in-the-pr)) and corrupt/missing state. [D6](open-decisions.md#non-blocking--decided-by-the-parent-from-house-style-to-be-proposed-in-the-pr)'s `scope` salt is optional.
7. **Verification** (D20: container, fakes and harness live in `.pi/`; feature tests only
   in upstream's existing test files; a *new* CI job is re-opened)**:** [D4](open-decisions.md#d4--what-environment-is-the-acceptance-gate) container + CI with a fake station + headless fake `inky`, plus a
   mandatory hardware pass — *as amended*: no `requirements.txt` / real `inky`; `php -S`
   is SAPI `cli-server` so `cli`-gated overrides don't apply; the Educators lock file must be
   provisioned; there is no clock seam for `recent`. See
   [test-environment.md](test-environment.md).

Interactions nobody should rediscover:

* Under item 5 a `birdframe-names`-style "toggle then `--force`" command will legitimately
  **not** repaint during an empty today-window.
* A corrupt/missing `state.json` must not turn an empty window into a change
  (`display.py:329-335`), including on the `OnBootSec=2min` boot-after-outage run.
* An undrawable first detection of the day means the panel keeps yesterday's collage until
  a *drawable* bird arrives — req 6 is satisfied by the first drawable detection, not the
  first detection.
* A frame updated before its station holds forever (⚑ D14 proposes exit 1 so it is loud).

## Current behaviour that the feature must work with

| Fact | Where |
|---|---|
| The frame asks for a window only as `hours=N` (int, 1…1 000 000); there is no date/midnight param. | `frame/display.py:91 fetch_recent()`; `avian/api/birdnet-api.php:356` |
| Midnight clamping **already exists**, driven by the station-wide flag. | `birdnet-api.php:82 recentWindow(db, hours, dateContext, $resetAtMidnight, $scoped)`, flag read at `:129`, passed at `:358-363` |
| Clamped windows use `>=` at start-of-day; rolling windows use `>`. A `00:00:00` detection is included when clamped. | `recentWindow` + `tests/test_midnight_reset.php` |
| Response already carries `reset_at_midnight`, `midnight_clamped`, `window_start`, `anchor`, `is_today`, `date`, `station_date`. | `birdnet-api.php` `case 'recent'` |
| `signature([])` is a real distinct hash → **an empty window currently counts as a change** and would draw the empty-nest collage. | verified by running it (`4f53cda18c2baa0c`) |
| The refresh gate is skipped by `--force` and `--preview`, and `--no-signature` forces `changed = True`. | `frame/display.py:445-452` |
| `heal_hours = 24` forces a refresh even when unchanged; `last_refresh` is only stamped on a successful push. | `display.py:444`, `:481` |
| `load_state()` turns **any** error into `{"signature": None, "last_refresh": 0}` → next valid signature counts as a change. | `display.py:329-335` |
| The collage is drawn by `avian/frontend/apt.js` in headless Chromium; the frame only rewrites the page's `recent` response. A page-URL param does **not** reach the API (`apt.js` builds its own URL; only `?labels=` is read off `location.search`). | `frame/shoot.py:243 _make_api_handler`; `apt.js:378`, `:6028`, `:1809` |
| The saved signature is recomputed from what the browser was actually served. | `display.py:457-463`; `tests/test_frame_capture.py::test_saved_signature_describes_captured_data_not_earlier_fetch` |
| Unscoped `signature(species)` hash is a frozen compat contract. | `tests/test_frame_birdweather.py:191` |
| The **website** must keep clearing the collage on a real zero-detection window. | `tests/smoke_collage_readiness.mjs:25` |
| `FRAME_READY` is regex-extracted from `frame/shoot.py` and executed by a Node test — the literal must stay matchable. | `tests/smoke_collage_readiness.mjs:86-88` |
| An empty window is a perfectly valid *renderable* frame (empty-nest card), so nothing downstream protects the panel. | `apt.js:3121-3144`; `shoot.py` `FRAME_READY` accepts count 0 |
| Only the source chain filters: `drawable_slugs()` raises rather than filter everything away; downstream empty lists are accepted. | `frame/birdweather.py:341` |

## Draw paths that bypass the refresh gate

Only the first four can put pixels on the glass.

| Path | Invocation | Notes |
|---|---|---|
| Render after `avian-bundle use` (only if the selection changed) | `frame/bundle_runtime.py:1953-1955,1962-1963` → `display.py --force --no-signature --wait-lock` | User asked for **artwork**, not a wipe. |
| `avian-bundle rollback` | `bundle_runtime.py:1993-1997` — renders **unconditionally**, no `changed` gate | Same forced, signature-free render. |
| Hidden escape hatch | `--no-render` on `use` and `rollback` (`:2121,2124`, `argparse.SUPPRESS`) | Exists, but is not a substitute for a real guard. |
| `birdframe-names on\|off` | `frame/birdframe-names:63-68` → `display.py … --force` | User asked for names, not a wipe. |
| Documented manual update | `frame/README.md` → `display.py … --force` after `git pull` | |
| `--no-signature` | documented dev path | `changed` forced True. |
| `--preview` | `frame/display.py:469-474` | **Cannot touch the panel**: returns before `push_panel` (`:477`) and never writes state. Keep it ungated — it is how you inspect an empty window. |

**Why declining must exit 0** (stronger than "reports a failure"):
`_render_callback` raises on any non-zero exit (`bundle_runtime.py:2108-2110`), and
`use`/`rollback` then **restore the previous bundle state and re-render** before raising
`BundleError("frame render failed; the previous bundle was restored")`
(`:1962-1972`, `:1993-2000`). A non-zero decline would silently **undo the user's bundle
switch**.

⇒ A gate-only guard is insufficient. Decide "draw or decline" from the fetched species
list before capture, covering forced runs, and return success when declining.
This maps to brief requirements **9 and 10**; requirement 12 (disabled ⇒ unchanged) is a
separate concern.

## Window options, ranked

> **D20 note:** the recommended row below is now implemented in its smallest form — OR the
> param into the existing `$RESET_AT_MIDNIGHT` and send `hours=24` — rather than via a new
> branch. See [minimal-footprint.md](minimal-footprint.md).

| Option | Verdict |
|---|---|
| **Additive request-scoped param on `action=recent`** (e.g. `reset_at_midnight=1`) → `recentWindow`'s `$resetAtMidnight` | Recommended. Exact boundary, correct `n`, absent ⇒ identical SQL/headers. Must keep `$scoped` suppression, `hours>=1000000` behaviour, and historical `?date=` rolling. |
| Client-side filter on per-species `last_seen` | **Rejected**: `n` is `COUNT(*)` over the rolling window, so yesterday's calls keep inflating tile size and `_bucket()` → mixes days. |
| **Serve the frame's own fetched list to the browser in `local` mode** — the pattern `birdweather` mode already uses (`frame/shoot.py:243-257` `species=` ⇒ fulfils `recent` locally, so the page's own request stops mattering) | Worth serious consideration: makes signature/image agreement **structural** with one upstream request instead of injecting a param in two places and hoping they stay in sync. Costs: the payload must carry `sci/com/n`, and it abandons the live site as the source of truth for the capture. (`top_file` is genuinely unused by the frontend — 0 occurrences in `avian/frontend/apt.js`.) |
| `hours=1000000` ("ALL") + client-side filter | **Rejected**: same mixing flaw, plus a full-table aggregate per poll. |
| Frame computes `hours = hours-since-midnight` | **Rejected** by the brief (no whole-hour approximation) and it uses the *frame's* clock for the station's day. |
| Flip the station's global `RESET_AT_MIDNIGHT` | **Forbidden** by the brief; it is a station-wide display preference and forces `no-store` on every response (`avian/api/birdnet-api.php:167-170`). |
| Change `apt.js` | **Rejected**: changes station-wide behaviour and breaks `tests/smoke_collage_readiness.mjs`. |

Implementation notes for the recommended option:

* Prefer `Date = :station_date` over `DATETIME(Date||' '||Time) >= midnight`:
  exact to the second, DST-proof, and the only form that can use
  `detections_Date_Time (Date DESC, Time DESC)` (`scripts/createdb.sh:20` — confirmed
  by `EXPLAIN QUERY PLAN`: `Date = …` → index search, the rolling expression →
  `SCAN detections`, so today's `recent` already full-scans). Precedent:
  `case 'hourly'` (`birdnet-api.php:571-595`).
  **Keep the anchor ceiling**: `recentWindow` always adds
  `DATETIME(Date||' '||Time) <= DATETIME(:anchor)` (`:89`), so use
  `Date = :d AND DATETIME(Date||' '||Time) <= :anchor` or the clamp quietly changes
  semantics for skewed/future-stamped rows.
* Read the param strictly: scalar only; `null` (absent) ≠ false ≠ true; ignore
  PHP-folded aliases (`key[]`, `key\0`) — see
  `educator_scope_raw_parameter_count` (`avian/api/educator-scope.php:28-48`).
* Unknown params are otherwise free-form on every action except `scope-probe`
  (`birdnet-api.php:139-158`), which rejects extras.
* Cache: an honoured request should be `no-store`; requests without the param get
  exactly today's headers (which are already `no-store` when the global flag or Educators
  mode is on, `birdnet-api.php:165-171`). `Cache-Control` is emitted **before** the
  `switch`, so `case 'recent'` must re-send it.
* ~~Frame side must inject the param in both `fetch_recent()` and
  `shoot._make_api_handler`~~ — **superseded by [D17](open-decisions.md#d17--the-local-mode-served-list-variant)**: the frame sends the param once
  (its own fetch) and serves that full response to the page. The page's own request never
  reaches the station while the flag is on. (Historical note: the rewrite at `shoot.py:259`
  is a substitution of `hours=\d+`, so two-place injection would also have needed an
  append.)
* The param must not be sent in `birdweather` mode (no station involved) nor in
  `image` mode (someone else's render).

## Day identity without clock agreement

* The station's day is already returned as `station_date` (SQLite `localtime`), so the
  frame never needs a client-side tz database or clock agreement to know which day it is.
  *(Superseded detail: this used to recommend persisting `station_date` in `state.json`.
  Audit 2 amended [D9](open-decisions.md#non-blocking--decided-by-the-parent-from-house-style-to-be-proposed-in-the-pr) to **add no state keys** — the data-keyed pre-capture guard needs no
  remembered day, because the station's own window already starts at its midnight.)* (An
  authoritative IANA zone **does** exist server-side: Caddy passes
  `AVIAN_STATION_TIMEZONE` into PHP (`scripts/update_caddyfile.sh:967,976,985`), so
  `educator_station_timezone()` (`avian/api/educator-store.php:407`) resolves a real
  `DateTimeZone` in the web path and a request-scoped clamp can be tz-exact — but the
  frame has no need to resolve zone names itself.)
* `as_of` is `date('c')`, so its zone follows PHP's `date.timezone` (UTC on a stock
  Pi) and is **not contractual** — nothing in `avian/api/` pins it, and sibling
  scripts do call `date_default_timezone_set()` (`scripts/common.php:22`,
  `scripts/config.php:113`). It carries its own offset, so never derive a day from it;
  `anchor`/`date` are station-local strings. The `hourly` comment at
  `avian/api/birdnet-api.php:577-581` records exactly this bug class.
* Detection timestamps originate from the **recording filename**, naive local time
  (`scripts/utils/classes.py:23-52`) — see
  [station-clock-and-data.md](station-clock-and-data.md).
* For the "first detection of the day hashes the same as yesterday" case, the existing
  `signature(species, scope)` second argument is the designed hook for window identity
  (precedent: `birdweather_signature_scope`, `frame/display.py:125`); unscoped hashes stay
  byte-compatible (`tests/test_frame_birdweather.py:191`).

## Degraded-station signal

> **Refuted by Audit 2 — now ⚑ [D14](open-decisions.md#d14--how-is-an-un-updated-station-detected-and-with-what-exit-code-supersedes-d5).** The text below claimed that absent/false
> `reset_at_midnight` / `midnight_clamped` / `window_start` is a *definitive* "this station
> did not clamp" test. It is not: `midnight_clamped`/`window_start` are **always present**
> on any station with the global-flag code (`avian/api/birdnet-api.php:392-397`), `reset_at_midnight`
> echoes the *global* flag (`:90,95,118`), and an old station with that flag ON returns
> `midnight_clamped: true`. Recommended replacement: a **distinct echo field** emitted only
> by the new code when the param was honoured. Original text kept for the record:

~~Absence/falsity of `reset_at_midnight` / `midnight_clamped` / `window_start` in the
response is the definitive "this station did not clamp" test — no version guessing.~~
A LAN-only capability probe also exists (`birdnet-status.php?action=version`,
unauthenticated for direct LAN requests via `avian_require_admin()`'s early return,
`avian/api/admin-auth.php:817-825`) but 401s through a tunnel, so it cannot be primary.

## Edit surface (worker-sized tasks)

> **Superseded in size by D20.** The estimated minimal diff (per file, with line counts) is in
> [minimal-footprint.md](minimal-footprint.md#estimated-shipped-diff-after-the-audit). The table
> below is the pre-D20 surface and over-states the PHP and `frame/shoot.py` changes.

| File | Change |
|---|---|
| `avian/api/birdnet-api.php` | `case 'recent'` only: strict `=1` param; window per ⚑ [D13](open-decisions.md#d13--does-the-today-window-respect-the-hours-setting) (separate branch, or `recentWindow` reuse); distinct echo field (⚑ [D14](open-decisions.md#d14--how-is-an-un-updated-station-detected-and-with-what-exit-code-supersedes-d5)); re-send `no-store` when honoured; keep `$scoped`, `hours>=1000000` and historical-date behaviour; no change to other actions. |
| `frame/display.py` | `DEFAULTS["reset_at_midnight"] = False`; activation predicate ([D2](open-decisions.md#d2--which-frame-modes-does-the-feature-apply-to) amended); a **flag-only** fetch helper returning the whole response (leave `fetch_recent`/`fetch_species` untouched); pre-capture decline on *no drawable species* (⚑ [D12](open-decisions.md#d12--what-does-nothing-to-draw-mean-for-the-d1-decline)) covering every forced path, exit 0, no `save_state`; forced paths gain the fetch (⚑ [D16](open-decisions.md#d16--no-validated-list-fetch-failed-or---no-signature-with-the-flag-on)); Educators-scope hold (⚑ [D15](open-decisions.md#d15--educators-capture-active-while-reset_at_midnight-is-on)); degraded-station hold + exit code (⚑ D14); pass the response into `shoot()`. Extract a helper to stay under flake8 complexity 15. **No new `state.json` keys.** |
| `frame/shoot.py` | `_make_api_handler` flag-gated local variant ([D17](open-decisions.md#d17--the-local-mode-served-list-variant)): fulfil `recent` with the full served response + `frame_capture_id`, `continue_()` everything else. Flag off ⇒ unchanged. Keep `FRAME_READY` extractable (Node smoke test regexes it). |
| `frame/config.example.toml`, `frame/README.md` | Document the knob, per-mode support, kill switch, heal/burn-in consequence, station-update requirement. |
| `tests/test_midnight_reset.php` | Param on/off, scoped, historical, ALL-time, boundary rows. |
| `tests/test_frame_capture.py` | Gate + forced-path retention tests via the existing patch-collaborators pattern (assert *no push attempted*). |
| possibly `tests/smoke_collage_readiness.mjs` | Only if the capture handshake literals move. |
| not expected | `frame/config_contract.py` (orthogonal to mode), `frame/install.sh` (no config rewrite on rerun; there is no `--hours` flag either). |

## Requirement → deciding code

| Brief requirement | Decided by |
|---|---|
| 1 today = station's calendar day from 00:00 | `Date = :station_date` (or `start of day`) server-side |
| 2 show only today's species once active | clamped window drives both signature and served list |
| 3 reset at midnight without clearing/refreshing | decline-to-draw on empty today window |
| 4/5 keep previous collage while today is empty | same guard; must also cover heal + restart + forced/bundle paths |
| 6 first detection replaces collage | clamp changes set/counts → `changed`; salt day identity via `scope` if needed |
| 7 keep refreshing on real changes | unchanged `signature`/`_bucket` behaviour |
| 8 never mix days | server-side clamp (not client filter — see rejected options) |
| 9 never a blank screen from an empty window | guard **before** capture, all draw paths |
| 10 heal must not clear | guard ordered with/before `heal_due`; suppress heal only while the window is empty |
| 11 survive restarts | `load_state()` failure must not make an empty window "changed"; e-ink holds the image unpowered |
| 12 disabled ⇒ unchanged | param absent, no scope salt, identical hash inputs |
| isolation: station display unchanged | request-scoped param; educator `$scoped` still ignores display preference |
| isolation: optional/backward-compatible API | additive param, absent ⇒ identical SQL + headers |
| other API clients unaffected | same, plus no change to `stats`/`hourly`/`rhythm`/`windowClause` |
| isolation: do not modify/delete historical detections | read-only handle (`SQLITE3_OPEN_READONLY`, `:186`); assert no write/DDL in the diff |
| isolation: preserve quiet hours, layout, e-ink handling | untouched paths: `in_quiet_hours` (`frame/display.py:348`), `mat_and_center` (`:233`), `push_panel` (`:308`) |
| isolation: never touch the global `RESET_AT_MIDNIGHT` | frame code must never POST to `avian/api/config.php` — currently an **unowned** Reviewer check; the PHP tests cover the flag's behaviour, not frame restraint |
| 11 restart vector, scheduled | `frame/systemd/birdframe.timer` `OnBootSec=2min` (`frame/systemd/birdframe.timer:10`; `Persistent=true` is inert without `OnCalendar=`) fires a render ~2 min after a boot that follows a multi-day outage — the retention rule must hold for timer-driven runs, not just manual restarts |

## Verification

Authoritative runs need Linux + `php` (absent here — PHP contract tests skip, and
`frame/display.py` tests error on `fcntl`): see
[testing-and-ci.md](testing-and-ci.md#running-displaypy-tests-on-windows).
Requirement checks on a machine without e-ink must assert that **no push was
attempted** (`push_panel` not called, `save_state` not called), following
`tests/test_frame_capture.py::test_capture_failure_preserves_panel_state_and_next_cycle_retries`.
Desktop/container tests do not replace a capture check on the frame Pi
(`frame/README.md`).
