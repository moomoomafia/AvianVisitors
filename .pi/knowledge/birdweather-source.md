# BirdWeather / eBird source (`frame/birdweather.py`)

Used when `species_source = "birdweather"` — a frame with **no microphone**. Stdlib
only, no key required for the main path. Library + CLI (`python3 birdweather.py 94107`).

This path is **independent of BirdNET-Pi**: no `birds.db`, no `action=recent`. It
produces the same `[{"sci","com","n"}]` shape so `frame/shoot.py` renders it unchanged.

## External services

| Service | Constant | Auth |
|---|---|---|
| BirdWeather GraphQL | `BIRDWEATHER = "https://app.birdweather.com/graphql"` (`:24`) | none (public) |
| zippopotam.us geocoder | `GEOCODER = "https://api.zippopotam.us"` (`:25`) | none |
| eBird recent geo observations | `EBIRD = "https://api.ebird.org/v2/data/obs/geo/recent"` (`:26`) | `X-eBirdApiToken` |

All responses capped (`r.read(2_000_001)` then reject >2 MiB for GraphQL) and shape-
validated; `_graphql(..., strict=False)` **degrades to `{}`** on any error so the
radius-growth loop can fall through, while `strict=True` raises `BirdWeatherError`.

## Two modes, two different failure philosophies

### ZIP mode — `species_for_zip(zip, country, target=10, days=7, radii=(15,30,50))` `:402`

1. `geocode()` — cached forever in `~/.birdframe/geocode.json` (a ZIP's coordinates
   never move; atomic tmp+`os.replace`, shape-guarded on read).
2. `top_species(lat, lon, miles, days, limit=60)` via `topSpecies(period, ne, sw, limit)`,
   filtered to drawable slugs; **grow the radius only until `target` drawable species
   are found** — stays as local as the data allows.
3. Still short → `triangulate()`: `nearest_stations()` grows search boxes
   `(50,150,400)` miles until ≥n stations, then inverse-distance-weighted
   `topSpecies` from the 3 nearest (`weight = 1/max(miles,1)`).
4. Still short → `ebird_nearby(lat, lon, days*2)` (`dist=50`, `back≤30`), keyless
   installs return `[]` and skip.
5. Sort by `-n`, return top `target`.

### Station mode — `species_for_station(value, target=10, days=7)` `:437`

`top_species_for_station()` (`:170`) is deliberately **strict and fallback-free**: one
GraphQL query that asks for `station(id)` *and* `topSpecies(stationIds:[id])`
together, verifies the returned station id equals the requested id
("BirdWeather returned a different station"), validates every row's types, and raises
`BirdWeatherError` otherwise. **A station-tethered frame must never substitute another
station's birds** (`:172-174`). Only ZIP mode may fall back geographically or via eBird.

`station_id()` (`:63`) canonicalises to a numeric string, rejects bools/leading
zeros/non-numeric, and enforces the same 32-bit upper bound (2147483647) as the
website. `birdnet_locator()` in `frame/display.py:109` refuses configs that set both
`bw_station_id` and `zip`.

`station_location()` (`:80`) exists for bundle selection — the frame needs the
station's own coordinates to pick a regional bundle.

## The drawable filter — `drawable_slugs()` `:341`

Species are filtered to those the repo can actually draw:

* Preferred source: `avian/frontend/dims.json` keys.
* Fallback: inline `var DIMS = {...}` parsed out of `avian/frontend/apt.js` (older
  bundles).
* `-2` suffix stripped, so perched/flight variants collapse to the base slug
  (`re.sub(r"-2$", "", k)`).
* Memoised in `_drawable`.
* **If neither source yields keys it raises** rather than filtering every bird into an
  empty nest — "refusing to filter every bird into an empty nest". Note this is the
  *only* empty-list protection in the whole source chain; downstream, an empty list
  renders the empty-nest collage happily.
* `frame/display.py` can pass `drawable=bundle.drawable_slugs` to override this with the
  active illustration bundle instead of the repo's set
  (`fetch_species(cfg, auth, drawable=…)`).

## Coverage reports for the installer

`coverage_for_zip(sample=15)` `:456` / `coverage_for_station()` `:477` run the same
gather but **unfiltered**, cap at top `sample`, then split into `(have, missing)`.
`frame/install.sh` uses `--missing` to offer generating absent cutouts; `sample` (15) sits
above render `target` (10) so BirdWeather count drift doesn't cause generating birds
that never reach the collage. The CLI prints `Sci|Com` lines for `pregen.py --stdin`
and a summary on stderr, and **exits 0 on lookup failure** so it can never break the
installer.

## eBird credential handling (`_private_ebird_key()` `:276`)

Order: explicit `key` → `EBIRD_API_KEY` env → `~/.birdframe/ebird-api-key`.
The file read is symlink-hardened: `O_DIRECTORY|O_NOFOLLOW` on the dir then
`O_NOFOLLOW|O_NONBLOCK` on the file via `dir_fd`, dir must be uid-owned and not
group/other-writable, file must be a regular single-link 0600 file of 1…4096 bytes
matching `[A-Za-z0-9]{1,4095}\n?`. `FileNotFoundError` ⇒ `None` (keyless install);
any other `OSError` ⇒ `BirdWeatherError`. The launcher resets the environment
(`--reset-env`), which is why the file exists at all — see
`frame/test_ebird_credentials.py`, `frame/test_install_security.py`.

## Signature interaction

`birdweather_signature_scope()` (`frame/display.py:125`) folds
`kind/id-or-country+zip/days` into the signature, so changing `bw_days` or the locator
redraws even if the species list is unchanged. Local mode passes no scope, preserving
hash compatibility with existing frames.
