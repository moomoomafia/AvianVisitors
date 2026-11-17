# Repo map

AvianVisitors = **a layer on top of BirdNET-Pi**, not a fork rewrite. Two trees
are shipped into a station; everything at root is upstream BirdNET-Pi unless a
release note says otherwise (`README.md:165-173`).

```
avian/          everything AvianVisitors adds to BirdNET-Pi (deployed to the station)
├── frontend/   static collage: apt.js (739 KB), stamps*.js, styles.css, dims.json,
│               masks.json, fonts/, assets/  (index.html 26 KB)
├── api/        PHP served by BirdNET-Pi's PHP-FPM at /avian/api/*.php
├── assets/     illustrations (bundled cutout PNGs) + photo-cutout fallbacks
├── bundles/    bundle build/publish inputs
├── scripts/    Python bundle pipeline (canonical, moderate, validate, publish,
│               masks, pregen, cutout generation) + its own tests
└── forwarding/ optional MQTT / Caddy-auth / Cloudflare tunnel configs
frame/          the e-ink wall frame client (its own venv, installer, systemd units)
homepage/       legacy PHP homepage (index.php, views.php)
model/          BirdNET 6K tflite models + labels (+ model/l18n translations)
ops/            cloudflare access configs
docs/           release notes, bundle publication/review docs, educators, translations
scripts/        inherited BirdNET-Pi runtime (analysis, installers, admin, reports)
templates/      inherited config templates (cron, gotty, bashrc, bootstrap)
extras/archive/ archived material
tests/          the real test suite (pytest + php + node smoke scripts)
.github/workflows/
```

## frame/ inventory (this is where frame work happens)

| File | LOC | Role |
|---|---|---|
| `frame/display.py` | 540 | **The timer entry point.** Fetch species → signature → refresh decision → get image → mat/centre → push Inky → save state. |
| `frame/shoot.py` | 751 | Headless-Chromium capture of the live site, or offline render of a species list (`shoot_birdweather`). Library + CLI. |
| `frame/bundle_runtime.py` | 2175 | Illustration-bundle download/verify/select; `avian-bundle` CLI; `active_bundle()` used by `display.py`. |
| `frame/birdweather.py` | 500 | BirdWeather GraphQL / geocoder / eBird client + drawable-species filter. Library + CLI. |
| `frame/capture_art.py` | 142 | Pixel budget + PNG/WebP validation + final composition of capture strips. |
| `frame/config_contract.py` | 141 | Installer pre-flight: does an existing `config.toml` still mean the requested mode? |
| `frame/install.sh` | 841 | The whole Pi setup: apt deps, SPI/I2C, venv, Playwright, config write, systemd units, symlinks. |
| `frame/birdframe-names` | 68 | `on\|off\|status` CLI: edits `bird_names` in config, then `display.py --force`. |
| `frame/avian-bundle`, `frame/avian-bundle-installed`, `frame/vendor/avian-bundle-control` | 62/106/15 | Hardened launchers (setpriv, `--reset-env`, symlink-safe path resolution). |
| `frame/generate_illustrations.py` | 140 | Generate missing cutouts off-device (rembg + paid Gemini key). |
| `frame/shoot.py` CLI / `frame/capture_art.py` | — | Desktop capture path; `display.py` is the on-device path. |
| `frame/systemd/birdframe.{service,timer}` | 16/15 | Reference units; **`install.sh:579-606` generates the installed copies** with your user/paths. |
| `frame/config.example.toml` | 68 | Full reference config (gitignored real one is `~/.birdframe/config.toml`). |
| `frame/requirements-frame.txt` | 7 | Device: `Pillow`, `inky`, `tomli` (<3.11). |
| `frame/requirements-shoot.txt` | 4 | Capture host: `playwright==1.62.0`, `Pillow`. |
| `frame/requirements-bundle-species.txt` | — | Extra deps for species-bundle work. |
| `frame/test_bundle_runtime.py` (979), `frame/test_bundle_render_integration.py` (885), `frame/test_install_security.py` (1183), `frame/test_ebird_credentials.py` (107) | | Frame-local tests (Linux-only: `fcntl`, `os.geteuid`, `O_NOFOLLOW`). |
| `frame/hardware/` | | STEP/F3D/3MF enclosure + mic-mount CAD. |
| `frame/Dockerfile.install-security`, `frame/check_install_security.sh` | | Containerised installer-security gate. |

## avian/api/ inventory (the station side)

| Endpoint | LOC | Notes |
|---|---|---|
| `avian/api/birdnet-api.php` | 28.6 KB | **The JSON facade over `birds.db` (read-only).** Actions: `stats`, `lifelist`, `recent`, `species`, `timeseries`, `firstseen`, `calendar`, `rhythm`, `hourly`, `scope-probe`. |
| `avian/api/config.php` | 19 KB | Settings contract; `RESET_AT_MIDNIGHT` declared as `['type' => 'bool']` (`avian/api/config.php:40`). |
| `avian/api/educator-scope.php` / `avian/api/educator-store.php` | 36/88 KB | "Saved view" privacy scopes; resolves the DB path (`educator_birds_db_path()`); `educator_station_timezone()` (`:407`) resolves the IANA zone from `AVIAN_STATION_TIMEZONE`, which Caddy passes to PHP (`scripts/update_caddyfile.sh:967,976,985`). |
| `avian/api/cutout.php` | 13.7 KB | Serves a bird illustration: `?sci=&pose=&bundle=&content=`. |
| `avian/api/bundle-assets.php`, `avian/api/bundle-species.php`, `avian/api/bundle-preview.php`, `avian/api/bundles.php`, `avian/api/bundle-runtime.php` | | Bundle catalogue/asset metadata. |
| `avian/api/birdweather.php` | 23.6 KB | Station-side BirdWeather reporting (separate from the frame's own client). |
| `avian/api/birdnet-status.php`, `avian/api/spectrogram.php`, `avian/api/recording.php`, `avian/api/export.php`, `avian/api/generate.php`, `avian/api/admin-auth.php`, `avian/api/admin-state.php`, `avian/api/archive.php`, `avian/api/menu.php`, `avian/api/wiki.php`, `educators*.php`, `avian/api/maintenance.php`, `educator-audio*.php` | | The rest of the station admin/UI surface. |

### How the PHP finds the station

`avian/api/birdnet-api.php:29-37`: the file is symlinked into the BirdNET-Pi Caddy
site root; PHP resolves `__DIR__` through the symlink, so `dirname(__DIR__, 2)` is
the BirdNET-Pi install root and `birdnet.conf` sits next to it. `getenv('HOME')` is
unusable (PHP-FPM runs as `caddy`). DB path comes from
`educator_birds_db_path()`. Consequence: **frame code must never assume paths from
the checkout** — it talks HTTP.

## Entry points, by intent

| I want to… | Start at |
|---|---|
| Change when/whether the panel refreshes | `frame/display.py:418 run()` + `frame/display.py:103 signature()` |
| Change what species the frame shows | `frame/display.py:132 fetch_species()` |
| Change the picture | `frame/shoot.py:412 shoot()` (capture) and `frame/display.py:233 mat_and_center()` (layout) |
| Change the API window | `avian/api/birdnet-api.php:82 recentWindow()` (and `:279 dateContext`) |
| Change the collage layout/labels | `avian/frontend/apt.js` (`renderCollage` ~`:3121`, labels ~`:1636`, `birdApiUrl` ~`:378`) |
| Change installer behaviour | `frame/install.sh` (config write at `:705-752`, units at `:576-612`) |
| Change bundles | `frame/bundle_runtime.py` |

## Other files that matter for data / time / deploy work

| File | Why it matters |
|---|---|
| `scripts/utils/classes.py` | `ParseFileName` + `Detection`: a detection's `Date`/`Time` come from the **recording filename** (naive station-local), offset by the detection's start seconds. |
| `scripts/utils/reporting.py` | `write_to_db()` (`:134`) — the 12-column `INSERT INTO detections`. |
| `scripts/createdb.sh` | `detections` schema + indexes, incl. `detections_Date_Time (Date DESC, Time DESC)` — the reason `Date = :d` beats a computed datetime filter. |
| `scripts/update_caddyfile.sh` | Generates the station's Caddy config; validates `/etc/timezone` against `/etc/localtime` + zoneinfo + PHP (`:145-170`); injects Caddy's `AVIAN_DIRECT_LOCAL` FastCGI marker used for the LAN-admin decision. |
| `avian/api/admin-auth.php` | `avian_is_direct_local_request()` (`:143`), `avian_require_admin()` (`:817`) — LAN-direct requests skip admin unless `LAN_ADMIN_AUTH` is on. |
| `avian/api/birdnet-status.php` | Admin-gated station diagnostics; `?action=version` → `{ok, release}` (reaches the frame only on a direct LAN request). |
| `scripts/educators_control.sh` | Also sets `AVIAN_STATION_TIMEZONE` for **CLI** store ops (`runuser -u caddy -- env -i …`); the web path gets it from Caddy instead. |
| `extras/archive/tests/` | **Archived** superseded test scripts — do not "fix" them. |

### Grep traps in this repo

* `avian/frontend/assets/bundle-catalog/catalog-snapshot.js` is a ~1 MB single-line
  JSON blob — exclude it (`--exclude-dir=assets`) or it floods the result.
* `scripts/gotty*` are vendored binaries (matched as binary by grep) — scope to real
  source dirs.
* `avian/frontend/apt.js` is 739 KB / ~15 k lines; grep for a symbol then read a
  narrow range, never the file.

## Tests & CI

* `pytest` at repo root is the CI command (`.github/workflows/python-app.yml`,
  job `build`). CI installs `requirements.txt`, runs flake8 twice (fatal only for
  `E9,F63,F7,F82`), then `pytest`.
* Separate job `frame-capture` installs `frame/requirements-shoot.txt` +
  `playwright install --with-deps chromium` and runs
  `tests/test_frame_capture_browser.py` only.
* `.github/workflows/python-ci.yml` lints with `flake8` (root `.flake8`: `max-line-length=160`,
  `max-complexity=15`) on Python **3.9 / 3.11 / 3.13** *(on PRs to `main` only — the parent's default
  branch is `avian-visitors`, so this job does not gate parent PRs; measured 2026-11-16)* — so frame Python must stay
  3.9-compatible (`from __future__ import annotations`, no `X | Y` at runtime).
* `tests/` naming: `test_*.py` (pytest), `test_*.php` (PHP scripts, run via a thin
  Python subprocess wrapper, skipped when `php` is absent), `smoke_*.mjs` /
  `*.test.js` (browser/node), `smoke_*.sh` (shell).
* Also `.github/workflows/publish-bundle.yml`, `.github/workflows/validate-bundle.yml`, `.github/workflows/frame-installer-security.yml`.

See [testing-and-ci.md](testing-and-ci.md) for what actually runs on this machine.
