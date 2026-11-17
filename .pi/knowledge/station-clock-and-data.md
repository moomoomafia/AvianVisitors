# Station data, clocks, and deployment surface

Everything about how a detection gets its timestamp, what "today" means on a
station, and how the PHP actually runs. Read this before designing anything
time-related. Most of it was scouted for the midnight-reset feature
([feature-midnight-reset.md](feature-midnight-reset.md)).

## How a detection gets its `Date` / `Time`

```
recording filename  YYYY-MM-DD-HH:MM:SS....wav
   └─ ParseFileName (scripts/utils/classes.py:45-52)  regex + strptime → NAIVE datetime
        └─ Detection (scripts/utils/classes.py:23-42)
             self.datetime = file_date + timedelta(seconds=start_offset)
             self.date = "%Y-%m-%d"      self.time = "%H:%M:%S"
             self.iso8601 = astimezone(get_localzone()).isoformat()   # tz only here
        └─ write_to_db (scripts/utils/reporting.py:134) INSERT INTO detections VALUES (?,×12)
```

Consequences:

* `Date`/`Time` are **wall-clock strings in the station's local filesystem time**,
  taken from the *recording filename* plus the detection's offset into the file. They
  are not stored as instants and carry no offset.
* A detection that crosses midnight inside a recording lands on the correct day,
  because the offset is added to the file's start time before formatting.
* **DST:** a naive local timestamp is ambiguous during a fall-back hour and
  nonexistent during a spring-forward gap. Lexicographic comparison on
  `Date`/`Time` sidesteps arithmetic but cannot resolve the ambiguity — ordering
  inside the repeated hour is insertion order, not true time.
* If an operator changes the station timezone or clock, **historical rows keep the
  old local date**. "Since midnight today" is always relative to the *current*
  station clock.
* `Week` in the DB is an ISO week, while the range model needs BirdNET's 48-week
  partitioning (`birdnet_week`, `scripts/utils/classes.py:7-20`) — a documented trap,
  unrelated to this feature, but it shows the house habit of recording clock
  conventions in comments.

## Schema and index reality (`scripts/createdb.sh`)

```sql
CREATE TABLE detections (Date DATE, Time TIME, Sci_Name, Com_Name, Confidence,
  Lat, Lon, Cutoff, Week INT, Sens, Overlap, File_Name);        -- + detection_id added by migration
CREATE INDEX detections_Com_Name   ON detections (Com_Name);
CREATE INDEX detections_Sci_Name   ON detections (Sci_Name);
CREATE INDEX detections_Date_Time  ON detections (Date DESC, Time DESC);
```

**`Date = 'YYYY-MM-DD'` can use `detections_Date_Time`;
`DATETIME(Date||' '||Time) >= …` cannot** (the expression defeats the index). The
existing `recent` `where` is the expression form, so it full-scans. `hourly` and
`stats`' `today` queries use `Date = :d`. Any new "today only" window has a cheaper,
more exact spelling available: predicate on `Date`, not on a computed datetime.

## What "today" already means in the API

`dateContext()` (`avian/api/birdnet-api.php:279`) —
`$today = SELECT DATE('now','localtime')`, `?date=` must be valid and ≤ today
(else `400 bad date`), `$anchor = DATETIME('now','localtime')` for today else
`"$date 23:59:59"`. Returned by `recent` as `date`, `station_date`, `is_today`,
`anchor`.

**`station_date` is a free, authoritative "the station's calendar day" signal to any
client** — including the frame. No timezone name, no clock agreement, no math. This
is the cleanest available way for a client to notice a day rolled over.

Precedent for a **calendar-day** window already exists: `case 'hourly'`
(`avian/api/birdnet-api.php:571-595`) filters `WHERE d.Date = :d` and carries this
comment —

> "Today" comes from SQLite's localtime, the same clock the rows were written
> against… PHP's `date()` follows `date.timezone`, which on a stock Pi is **UTC**:
> taking today from there puts a US station a day ahead every evening and the ledger
> reads empty.

So: **`as_of` (`date('c')`) follows PHP's `date.timezone` — UTC on a stock Pi, but not
contractual** (nothing in `avian/api/` pins it; sibling scripts call
`date_default_timezone_set()`, `scripts/common.php:22`, `scripts/config.php:113`) and it
carries its own offset — while `anchor`/`date` are station-local strings. Never mix them,
and never use `as_of` to decide a day.

## Timezone plumbing that exists (and what doesn't)

| Thing | Status |
|---|---|
| `/etc/timezone` | validated at install: size 2–129, regex `[A-Za-z0-9._+-]+(/…)*`, must resolve under `/usr/share/zoneinfo/` and `cmp` equal `/etc/localtime`, and `new DateTimeZone()` must accept it (`scripts/update_caddyfile.sh:145-170`) |
| `AVIAN_STATION_TIMEZONE` | **Yes — passed to PHP by the generated Caddy config,** as a FastCGI param: `env AVIAN_STATION_TIMEZONE $AVIAN_STATION_TIMEZONE` in all six site blocks (`scripts/update_caddyfile.sh:967,976,985,993,1003,1013`), alongside `AVIAN_DIRECT_LOCAL`, `AVIAN_FORCE_AUTH`, `AVIAN_EXTRACTED_ROOT`, `AVIAN_BUNDLE_EXPORT_POOL`. The php-fpm pool runs `clear_env = yes` (`scripts/security_refresh.sh:118`), so **only** gateway-passed vars survive — which is why they are enumerated. Also set explicitly for CLI store ops (`scripts/educators_control.sh:713,867,878` via `runuser -u caddy -- env -i …`) |
| ↑ provenance caveat | Delivery into the request is **proven**; the last hop is **not**. `tests/smoke_caddy_generated_routes.sh:129` asserts `$_SERVER['AVIAN_STATION_TIMEZONE']`, but `educator_station_timezone()` reads **`getenv()`** (`avian/api/educator-store.php:408`), and the PHP tests inject it with `putenv` (`tests/test_educator_backend.php:133,519,539`), which is CLI. Whether `variables_order`/FPM exposes the FCGI param to `getenv()` is **assumed, not tested here** — only an HTTP-level check settles it. |
| `educator_station_timezone()` (`avian/api/educator-store.php:407`) | reads that var via `getenv()` and returns a real `DateTimeZone`; throws `503 station timezone is unavailable` when absent (see the caveat above — outside the generated Caddy config, a hand-rolled `php -r`/`php -S` harness must set it). Treat "an authoritative IANA zone is available to PHP" as strong-but-unverified for the web path. |
| `AV_EDUCATOR_NOW` (CLI-only clock override, `educator-store.php:420-427`) | the existing pattern for making time-dependent PHP logic **testable**; reuse the idea for window tests |

Practical consequence: the server can compute an exact tz-aware day boundary, but a
**client** still has no reason to resolve zone names — `recent` already returns
`station_date`/`anchor` in the station's own calendar terms.

## How the PHP is served, and who is "admin"

* Files live in `~/BirdNET-Pi/avian/api/`, symlinked into the Caddy site root as
  `/avian/api/*`. `__DIR__` resolves through the symlink →
  `dirname(__DIR__, 2)` is the install root, `birdnet.conf` sits there
  (`avian/api/birdnet-api.php:29-37`). `getenv('HOME')` is `/var/lib/caddy` under
  PHP-FPM and is never used.
* `avian_require_admin()` (`avian/api/admin-auth.php:817-825`) **returns early for a
  direct LAN request** unless `LAN_ADMIN_AUTH` is enabled (`AVIAN_FORCE_AUTH`, set per
  site block by Caddy at `scripts/update_caddyfile.sh:965,974,983`).
  `avian_is_direct_local_request()` (`:143-165`) trusts Caddy's FastCGI marker
  `AVIAN_DIRECT_LOCAL=1` (`update_caddyfile.sh:964,982`; explicitly `0` on the
  forwarded blocks at `:973,990`) **plus** private-IP source, local `Host`, and
  matching `X-Forwarded-For/Host/Proto`; any unexpected forwarding-family field
  voids it.
* Therefore a LAN frame can read **`birdnet-status.php?action=version`** →
  `{ok:true, release:"…"}` (`avian/api/birdnet-status.php:294-306`, which shells to
  `admin_control.sh release`) with no credentials. A frame behind a Cloudflare
  tunnel/forwarding is *not* direct-local → `401`. Treat this as an opportunistic
  capability probe, never a hard dependency.
* Query-param hardening precedent: `educator_scope_raw_parameter_count()`
  (`avian/api/educator-scope.php:28-48`) counts raw `&`/`;`-separated keys and
  returns `-1` for PHP-folded aliases (`key[]`, `key\0suffix`), because
  "`PHP folds bracket and NUL-suffixed keys into the same top-level name`". The
  `scope-probe` action additionally **rejects any unexpected query key**
  (`birdnet-api.php:139-158`). A new boolean param should be read strictly:
  scalar only, `null` ≠ false ≠ true, and it must ignore folded aliases rather than
  inherit them.
* Response headers: `recent` is `public, max-age=30` unless educator caching is
  disabled or the station's `RESET_AT_MIDNIGHT` is on, which forces `no-store`
  (`birdnet-api.php:169-171`). Error paths always `no-store` (`:162`). A
  request-scoped param must therefore be part of the URL (distinct cache key), and a
  clamped response can lag reality by up to 30 s.
* `publicConfigFlag()` (`:68-81`) scans the **whole** `birdnet.conf`, last assignment
  wins, truthy = `1|true|yes|on` after stripping quotes/space. The admin UI writes
  the file; `RESET_AT_MIDNIGHT` is declared `['type' => 'bool']` in
  `avian/api/config.php:40` **with no `restart` flag** (unlike `LATITUDE`,
  `'restart' => true`) → the global toggle is hot, and the frontend reacts by calling
  `refreshAll()` right after saving it (`avian/frontend/apt.js:8745-8766`).

## Deployment / update paths

| Action | How |
|---|---|
| Update the **station (mic)** | web UI **Tools → Pull latest** (`avian/api/maintenance.php`, `scripts/update_birdnet.sh`, `scripts/pre_update.sh`) |
| Update the **frame** | `cd ~/AvianVisitors/frame && git pull --ff-only && .venv/bin/python display.py --config ~/.birdframe/config.toml --force` (`frame/README.md`) |
| Re-run frame setup | `./install.sh …` — **never overwrites** an existing `~/.birdframe/config.toml`; it verifies the existing config still means the requested mode (`frame/config_contract.py`) and re-enables the timer |
| Renderer after a bundle change | `bundle_runtime._render_callback()` (`frame/bundle_runtime.py:2083-2113`) runs `display.py --config <cfg> --force --no-signature --wait-lock` in a scrubbed env (`PYTHONPATH`/`PYTHONHOME`/… removed, `PYTHONNOUSERSITE=1`, `PYTHONDONTWRITEBYTECODE=1`) and raises `BundleError("frame renderer returned an error")` on any non-zero exit (`:2108-2110`); the calling `use`/`rollback` then **restores the previous bundle and re-renders** before re-raising (`:1962-1972`, `:1993-2000`). `use` renders only when the selection changed; `rollback` always renders |
| Toggle bird names | `birdframe-names on\|off` → edits config → `display.py --force` |

Both sides must be updated together for capture changes: an older mic frontend
cannot confirm collage readiness, so the frame keeps its previous image and logs an
update reminder (`frame/README.md`).

## Repo housekeeping

* `.pi/` (this knowledge base and the plan drafts) is **not** in `.gitignore` and
  shows as untracked (`?? .pi/`) — the orchestrator plan forbids unauthorized
  commits, so decide explicitly whether `.pi/` should be ignored or committed.
* `extras/archive/tests/` holds superseded test scripts (e.g. `extras/archive/tests/smoke_worker.sh`) —
  don't "fix" them; they are archives.
* `scripts/` contains vendored binaries (`gotty`, `gotty-aarch64`, `gotty-x86_64`)
  and `avian/frontend/assets/bundle-catalog/catalog-snapshot.js` is a ~1 MB single-line
  JSON blob: **exclude both when grepping**
  (`--exclude-dir=assets`, or scope to real source dirs) or you will flood context.
