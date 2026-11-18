# Configuration reference

## Frame config: `~/.birdframe/config.toml`

Loaded by `display.py:486 load_config()` as `dict(DEFAULTS)` updated with the TOML —
**unknown keys are silently accepted**, missing keys fall back to `DEFAULTS`
(`frame/display.py:42-70`). Real file is gitignored; `frame/config.example.toml` is
the full reference. Line 1 of an installed file is a mode marker
(`# birdframe-mode: local|image|birdweather`).

### Source selection

| Key | Default | Meaning |
|---|---|---|
| `base_url` | `http://birdnet.local` | Station origin. Used for `action=recent` **and** as the capture target; in `image` mode the installer sets it to the image URL's origin. |
| `species_source` | `""` | `""` = BirdNET recent API; `"birdweather"` = BirdWeather. |
| `zip` | `""` | BirdWeather postal code. Mutually exclusive with `bw_station_id`. |
| `bw_station_id` | `""` | Public numeric BirdWeather station id (the number at the end of the station-page URL, **not** the upload token). |
| `bw_days` | `7` | BirdWeather lookback; part of the signature scope. |
| `bw_country` | `us` | Geocoder country for the ZIP; part of the signature scope. |
| `hours` | `24` | Rolling window for both the signature fetch and the capture (`window_hours`). |
| `image` | `""` | Local PNG dropped by a sibling process. |
| `image_url` | `""` | Pre-rendered frame PNG (frame gets `?labels=1|0` appended). |
| `shoot` | `false` | `true` = render/capture here (needs Chromium). `frame/install.sh` writes `true` for local and birdweather modes, `false` for image mode. |

### Look (only when this Pi renders)

| Key | Default | Notes |
|---|---|---|
| `shoot_title` | `None` | `.static-head .pre` (eyebrow). `""` hides the title only. |
| `shoot_subtitle` | `None` | `.static-head h1` (headline). |
| `shoot_headline_px` | `42` | 39 in birdweather mode. |
| `shoot_eyebrow_px` | `18` | 17 in birdweather mode. |
| `shoot_lowercase` | `false` | clears `text-transform` on the headline. |
| `shoot_mat` | `0.04` | padding inside the capture viewport. |
| `shoot_small_floor` | `0.04` | floors the rarest counts so tiny birds pack larger. |
| `shoot_count_exp` | `0.65` | tile size vs count; `1.0` in birdweather mode. |
| `bird_names` | `false` | toggled by `birdframe-names on|off` (which then runs `--force`). |

### Panel & geometry

| Key | Default | Notes |
|---|---|---|
| `rotate` | `90` | `90` or `270`; anything else warns and uses 90. |
| `saturation` | `0.6` | passed to `Inky.set_image` when supported. |
| `mat` | `0.0` | extra shrink inside the opening. |
| `opening` | `0.7071` | opening height as a panel fraction (1:√2 rect). `0.7071` = A5 default; `0.84` ≈ B5; up to ≈`0.98` for a bare panel. One knob, not width/height independently. |
| `panel` | `""` | `"el133uf1"` forces the 13.3" driver when `inky.auto()` fails. |

### Refresh policy

| Key | Default | Notes |
|---|---|---|
| `quiet_start` / `quiet_end` | `0` / `0` | whole hours on the **frame Pi's** clock; equal ⇒ never quiet (default: nocturnal detections still show). |
| `heal_hours` | `24` | forced refresh floor. |
| `state` | `~/.birdframe/state.json` | `{"signature","last_refresh"}`. |
| `cache` | `~/.birdframe` | holds `shot.png`, `frame.png`, `geocode.json`, `.render.lock`. |
| `bundle_root` | `~/.birdframe/bundles` | verified bundles. |
| `timeout` | `180` | seconds; shared capture deadline. Zero 2 W needs ~70–120 s. Must stay under the unit's `TimeoutStartSec=300`. |

### Auth

`basic_user` / `basic_pass` (both default `None`) — only if the **whole** station is
behind basic auth; applied to the API fetch, the image fetch, and Playwright.

### `reset_at_midnight` (added on this branch, 2026-11-17)

~~`reset_at_midnight` does **not** exist in `DEFAULTS`, `frame/config.example.toml`, or
`frame/install.sh` yet — it is the thing being added.~~ *(true until W2.)* Now: `DEFAULTS["reset_at_midnight"] =
False` (`frame/display.py:50`); documented commented-out in `frame/config.example.toml:27-28` and in
`frame/README.md:91`; **not** written by `frame/install.sh` (by design, plan §4.6).

* Active only when the value is exactly `true` **and** local mode (`species_source != "birdweather"`,
  `shoot = true`) (`frame/display.py:116-119`); otherwise one log line "applies only to local mode;
  ignored" (`:454-455`) and behaviour is unchanged.
* While active, `hours` is ignored: the frame asks the mic for `hours=24&reset_at_midnight=1` and the
  capture uses the same window (`:460`, `:416-424`).
* Needs an updated mic (W1). With an old mic, or during an Educators capture, the frame holds the
  collage and exits 1 every run (`:464-468`).
* Off switch: set it to `false` or remove it; no state reset needed (no new state keys, D9).

Design: [Plan v0.5](../reset-after-midnight%20Plan%20v0.5.md) §4; background:
[feature-midnight-reset.md](feature-midnight-reset.md).

## What the installer writes per mode (`frame/install.sh:705-752`)

* `local` → `base_url`, `shoot = true`, titles, `bird_names = false`, `rotate`,
  `saturation`, `timeout = 180`, commented-out basic-auth block.
* `image` → `base_url` (origin), `image_url`, `shoot = false`, `rotate`, `saturation`.
  Written with `printf`, never a heredoc, so the URL is literal, not shell-expanded.
* `birdweather` → `species_source`, `bw_station_id` **or** `zip`+`bw_country`,
  `bw_days = 7`, `shoot = true`, titles, `bird_names`, `rotate`, `saturation`.

Rerunning the installer **never overwrites an existing config**; it first runs
`verify_existing_config` → `frame/config_contract.py verify(path, mode, station,
zip, image_url)` (`install.sh:319`), which asserts the existing file still means the
requested mode (and rejects ambiguous/malformed combos, e.g. both locators, or an
image URL alongside `shoot = true`).

`--hours` and a midnight flag are **not** installer CLI options today; `hours` simply
comes from `DEFAULTS`.

## Process environment

`frame/systemd/birdframe.service` sets `Environment=PYTHONUNBUFFERED=1` and
`EnvironmentFile=-/etc/avian-birdframe/environment` (root-owned `0600`, written by the
installer for `EBIRD_API_KEY`; optional `-` prefix, `frame/install.sh:592`). Legacy
`Environment=EBIRD_API_KEY=` lines in an old unit are migrated
(`install.sh:492-494`). The `avian-bundle` launchers use `setpriv --reset-env`, so
bundle-time code must read files, not env vars.

## Station-side config: `birdnet.conf`

Read by the PHP through `dirname(__DIR__, 2)/birdnet.conf` (never `$HOME`, which is
`/var/lib/caddy` under PHP-FPM). Only specific keys are ever exposed:

* `SITE_NAME` — via `publicSiteName()` (`avian/api/birdnet-api.php:42`), ≤60 chars,
  charset-filtered, last assignment wins; used as `site_name` in API responses.
* `RESET_AT_MIDNIGHT` — via `publicConfigFlag()` (`:68`): truthy is
  `1|true|yes|on` (case-insensitive, quotes stripped, **last assignment wins**).
  Declared in the settings contract as `['type' => 'bool']`
  (`avian/api/config.php:40`); validated `0|1` by `scripts/admin_control.sh:191`;
  default `RESET_AT_MIDNIGHT=0` from `scripts/install_config.sh:190`; UI toggle
  "Reset at midnight — keep time windows inside the current day"
  (`avian/frontend/apt.js:12934`).
  Effects: clamps `recent` windows to station midnight
  (`avian/api/birdnet-api.php:82-121`) and forces `Cache-Control: no-store` (`:169`).
  It is a **station-wide display preference**; the educator (saved-view) scope
  explicitly ignores it.
* Everything else in `birdnet.conf` may contain credentials — never read or echo the
  whole file.

## Related state files

| Path | Content |
|---|---|
| `~/.birdframe/state.json` | last drawn signature + last successful refresh epoch |
| `~/.birdframe/geocode.json` | `{ "<country>/<zip>": [lat, lon] }`, permanent |
| `~/.birdframe/ebird-api-key` | 0600, single link, `[A-Za-z0-9]{1,4095}` |
| `~/.birdframe/bundles/state` | active bundle reference (`bundle_runtime`) |
| `~/.birdframe/.render.lock` | flock target, no content that matters |
