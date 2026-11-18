# Station JSON API — `avian/api/birdnet-api.php`

Read-only JSON facade over BirdNET-Pi's `birds.db` (SQLite). Served at
`/avian/api/birdnet-api.php` on the station. The frame is one of its two
consumers; `avian/frontend/apt.js` is the other.

Header comment `avian/api/birdnet-api.php:3-14` lists the actions.

## Actions

| `?action=` | Params | Purpose | Line |
|---|---|---|---|
| `stats` | `date?` | totals / today / last_hour / week / started | `:313` |
| `lifelist` | — | every species ever, with `first_seen`, `last_seen`, `n`, `best_conf` | `:340` |
| **`recent`** | `hours?` (default 24, clamped 1…1 000 000), `date?` | species-collapsed view of the window — **what the frame and the collage use** | `:352` |
| `species` | `sci` (required), `limit`≤1000, `offset` | per-species detection list | `:402` |
| `timeseries` | `days?` | daily counts per species | `:428` |
| `firstseen` | `limit?` | newest lifelist additions | `:461` |
| `calendar` | — | detection totals by date | `:481` |
| `rhythm` | `hours?` | minute-by-minute rhythm vs prior period | `:502` |
| `hourly` | `date?` | species-by-hour ledger for one calendar day | `:571` |
| `scope-probe` | `edu` only | educator-scope existence probe; rejects any extra query key | `:139-158` |

`hours >= 1000000` (~114 y) is the frontend's **"ALL"** button — it removes the
lower bound rather than adding a code path (`:353-356`).

## `action=recent` response

```jsonc
{
  "hours": 24,
  "date": "2026-09-02",           // the date context in play (requested or today)
  "station_date": "2026-09-02",   // the station's actual today
  "is_today": true,
  "anchor": "2026-09-02 15:30:00",// upper bound of the window, station local clock
  "reset_at_midnight": false,      // did the station's display preference apply? (after the
                                   // R1 change: station flag OR ?reset_at_midnight=1, not scoped)
  "midnight_clamped": false,       // was this window actually clamped to start of day?
  "window_start": "2026-09-01 15:30:00",  // null when unbounded
  "species": [ {
      "sci": "Corvus brachyrhynchos", "com": "American Crow",
      "n": 20,                      // COUNT(*) in the window
      "best_conf": 0.87,
      "last_seen": "2026-09-02 14:02:11",
      "top_file": "...",            // file of the highest-confidence detection IN WINDOW
      "detection_id": 1234,
      "top_at": "2026-09-02 14:02:11"
  } ],
  "site_name": "Avian Visitors",
  "as_of": "2026-09-02T15:30:05+00:00",
  "educator_scope": null,
  "frame_capture_id": 1             // injected by frame/shoot.py only, never by the station
}
```

SQL shape (`:369-375`): one row per `Sci_Name` in the window, `GROUP BY Sci_Name
ORDER BY last_seen DESC`, `n = COUNT(*)`. Then an N+1 loop (`:376-388`) fetches each
species' top-confidence detection inside the same window for `top_file`.

## Time windows: two different builders

* `windowClause(hours)` — `:300`. Plain rolling window, `> DATETIME(:anchor,'-N hours')`.
  Used by `stats` (`last_hour`, `week`). **Never clamped.**
* `recentWindow(db, hours, dateContext, resetAtMidnight, scoped)` — `:82`. Used by
  `recent`. Returns `{where, bind, reset_at_midnight, midnight_clamped, window_start}`.

### `recentWindow` semantics (memorise this table)

`$enabled = $resetAtMidnight && !$scoped`
`$clamped = $enabled && $is_today && $rolling <= $midnight`
start = `$clamped ? 'start of day' : $rolling`, and the lower operator is **`>=` when
clamped, `>` when rolling** (so a detection exactly at midnight is included after a
reset, and the boundary detection is excluded in rolling mode).

| inputs | result |
|---|---|
| `hours=24`, today, reset=1, unscoped | clamped to station midnight |
| `hours=12`, today, reset=1, unscoped | **not** clamped (rolling start is already inside today) |
| `hours=24`, today, reset=0 | rolling, crosses midnight |
| any `hours`, historical `?date=`, reset=1 | not clamped (`is_today` false) |
| educator scope present (`$scoped`) | `reset_at_midnight: false`, output **byte-identical** to reset=0 |
| `hours >= 1000000` | no lower bound, never clamped |

Contract test: `tests/test_midnight_reset.php` (run via
`tests/test_midnight_reset.py`, skipped without `php`) asserts every row above,
including the SQL boundary case (a detection at `00:00:00` is included, `23:59:59`
of the prior day is excluded).

Key gap for frame work: **there is no request-level way to ask for a clamped
window.** Clamping today requires the station-wide `RESET_AT_MIDNIGHT=1` in
`birdnet.conf`, read once per request via
`publicConfigFlag($CONF_PATH, 'RESET_AT_MIDNIGHT')` (`:129`, defined `:68`). The plan
forbids changing that global setting, so a new opt-in param (e.g.
`&reset_at_midnight=1`) would have to be threaded into `recentWindow`'s
`$resetAtMidnight` argument — while keeping the "saved scope ignores the station
display preference" invariant and leaving `stats`/`hourly`/`rhythm` untouched.

> **Built 2026-11-17 (W1, `428f3104`):** `$resetAtMidnight = $RESET_AT_MIDNIGHT ||
> (($_GET['reset_at_midnight'] ?? null) === '1')` (`avian/api/birdnet-api.php:136`), used for
> `Cache-Control: no-store` (`:170`) and passed to `recentWindow` (`:363`). Only the exact value `1`
> enables it; a request can never switch a station-wide ON off; scoped requests still ignore it.
> Guarded by `tests/test_midnight_reset.py` (T1) and the `.pi/` probe. **Visible side effect:** the
> collage's window caption reads "since midnight" whenever `midnight_clamped` is true
> (`avian/frontend/apt.js:3609`, upstream code), so a frame with the flag on shows that caption.

## Date context & clocks — `dateContext()` `:279`

```php
$today = DATE('now','localtime')          // station clock
$asked = $_GET['date']                     // must be valid Y-m-d and <= today, else 400
$anchor = $is_today ? DATETIME('now','localtime') : "$date 23:59:59"
// with an educator scope and no ?date=, the anchor is the scope's latest detection instead
```

"A stats date is always interpreted in the station's SQLite local clock"
(`:276-278`). Everything downstream anchors on that. So: **midnight is the
station's midnight**, while the frame's quiet hours use the frame Pi's clock.

## Response headers / caching — `:165-171`

```php
header('Cache-Control: ' . (($educatorCacheDisabled || $RESET_AT_MIDNIGHT)
    ? 'no-store' : 'public, max-age=30'));
```

Plus `Content-Type: application/json`, `Referrer-Policy: no-referrer`,
`X-Content-Type-Options: nosniff`, `Cross-Origin-Resource-Policy: same-origin`.
Meaning: with the midnight preference **off**, `recent` may be served from a 30-second
public cache. Any frame param must therefore be part of the URL (a distinct cache
key), and a frame that polls faster than 30 s can legitimately see a stale window.

## Errors & transaction discipline

* DB opens read-only inside an explicit `BEGIN`, with `busyTimeout(2000)`
  (`:186-188`); `birdnetRespond()` (`:215`) rechecks the educator generation,
  appends `educator_scope`, then rolls back. Failures `ROLLBACK` + `close()`.
* Missing `birds.db` → `503 {"error":"birds.db not found"}` (`:173-182`) — note this
  is a *successful HTTP* response shape the frame treats as a signature-fetch
  failure, i.e. "no change".
* Educator scope errors are mapped to public, non-leaking messages
  (`educator_public_scope_error`) and `Cache-Control: no-store`.
* `site_name` is read out of `birdnet.conf` key-by-key (`publicSiteName`, `:42`) so
  the rest of that file (which can hold credentials) is never exposed; ≤60 chars,
  `[A-Za-z0-9 _.,'-]`, last assignment wins.

## How the frame consumes it

* Direct: `display.py:91 fetch_recent()` — `urllib`, UA `AvianVisitors-frame/1.0`,
  optional basic auth, `read(2_000_000)`, and it **rejects anything that is not a
  dict with a `species` list** (`raise ValueError("recent API has no species list")`).
  Verified by `test_signature_fetch_rejects_missing_species_not_as_empty`.
* Indirect: `shoot.py:243 _make_api_handler` intercepts every page request matching
  `**/birdnet-api.php**`:
  * `action=recent` → re-fetched with `re.sub(r"hours=\d+", f"hours={window_hours}", url)`
    (auth header injected if configured), validated, counts floored for the rarest
    birds, `frame_capture_id` stamped in, then `route.fulfill`ed.
  * non-`recent` requests → passed through (`route.continue_()`) **except** in
    birdweather mode, where they are fulfilled with `{}` (no backend in that mode).
  * any failure → `502 {"error":"frame recent API failed"}` and the capture aborts.
  * Species rows are required to be dicts with a non-blank string `sci`
    (`frame/shoot.py:266-268`), else it fails closed.

So a new API param must survive that URL rewrite (`hours=\d+` substitution preserves
everything else in the URL) and must be sent by *both* `fetch_recent` (signature) and
the page's own `recent` request (render), or the signature and the drawn collage can
describe different windows.

## Frontend request path (for parity checks)

`apt.js:378 birdApiUrl(action, params)` builds `?action=…&k=v…` (skips
`undefined|null|''`) then appends `&edu=<scope>` when a saved view is active.
`recent` is fetched with `{ hours: forHours }` where
`forHours = educatorScopeId() ? 1000000 : currentHours` and
`currentHours = +readLS('bird:window','24') || 24` (`avian/frontend/apt.js:1035`, picker writes the
same key at `:1043`). A scoped (educator) view is therefore *always* "ALL time".
