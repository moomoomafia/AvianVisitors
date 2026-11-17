# Testing & CI

## Commands

```bash
# CI-equivalent full gate (Linux)
pytest
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics

# frame-relevant subsets
pytest tests/test_frame_capture.py -q            # shoot.py + display.py logic (no browser)
pytest tests/test_frame_capture_browser.py -q    # real Chromium (CI job frame-capture)
pytest tests/test_frame_birdweather.py -q        # birdweather.py + display signature
pytest tests/test_midnight_reset.py -q           # runs tests/test_midnight_reset.php
pytest frame/ -q                                 # bundle runtime, render, installer security
php tests/test_midnight_reset.php                # direct PHP contract
```

`.flake8`: `max-line-length = 160`, `max-complexity = 15`. CI runs a second,
exit-zero complexity pass (`--max-complexity=10`) for information.
Python matrix in `.github/workflows/python-ci.yml`: **3.9 / 3.11 / 3.13** → keep frame Python
3.9-compatible (`from __future__ import annotations`, no runtime `X | Y`, no
`match`). `tomllib` needs the `tomli` backport on 3.9 (already in
`frame/requirements-frame.txt`).

## Verified state on this Windows workstation (2026-11-16)

Environment: Python 3.14.0, pytest 9.1.1, Pillow present, playwright importable,
**`php` not installed**, `fcntl`/`os.geteuid`/`O_NOFOLLOW` absent (POSIX-only).

| Command | Result |
|---|---|
| `pytest tests/test_frame_capture.py` | **58 passed, 1 skipped, 19 errors** |
| `pytest tests/test_frame_birdweather.py` | **14 passed + 34 subtests, 4 errors** |
| `pytest tests/test_midnight_reset.py` | passes (skips the PHP check — no `php`) |
| `pytest tests/` | **collection aborted: 15 errors** |
| `pytest frame/` | **collection aborted: 4 errors** |

Error causes, confirmed:

* `ModuleNotFoundError: No module named 'fcntl'` — anything that imports
  `frame/display.py` (19 tests in `tests/test_frame_capture.py`, all of
  `frame/test_bundle_runtime.py`) because
  `tests/test_frame_capture.py:154` does `load("capture_display", "frame/display.py")`.
* `AttributeError: module 'os' has no attribute 'geteuid'` / `O_NOFOLLOW` —
  `frame/test_ebird_credentials.py`, `frame/test_install_security.py`,
  `tests/test_bundle_species_runtime.py`, `tests/test_shifted_directory_migration.py`.
* `ModuleNotFoundError: No module named 'librosa'` — `tests/test_analysis.py`
  (and friends needing `requirements.txt`: tensorflow, pandas, plotly, apprise,
  pyarrow, matplotlib, soundfile, streamlit…).
* Missing `php` degrades PHP contract tests to skips, not failures.

**Implication:** this box cannot be the verification gate for frame work. Plan on
WSL/Docker/CI for the authoritative run, and locally verify only the pure-Python
subset (signature/gate logic) — or use the stub below.

### Running display.py tests on Windows

`fcntl` is imported at module import time (`frame/display.py:14`), so stub it before
loading the module. Verified working:

```python
import sys, types
m = types.ModuleType("fcntl")
m.LOCK_EX, m.LOCK_NB, m.LOCK_UN = 2, 4, 8
m.flock = lambda *a, **k: None
sys.modules["fcntl"] = m
# only needed if the test also imports bundle_runtime / birdweather paths that
# touch os.geteuid or os.O_NOFOLLOW at import time
import importlib.util
spec = importlib.util.spec_from_file_location("display", "frame/display.py")
display = importlib.util.module_from_spec(spec); spec.loader.exec_module(display)
```

As a pytest one-liner, drop the stub in a `conftest.py` at repo root (do **not**
commit a root `conftest.py` that changes behaviour for CI without saying so — CI runs
on Linux where the real module is used).

Quick logic checks that need no hardware and no `fcntl`-free trick once stubbed:

```python
display.signature([])                 # '4f53cda18c2baa0c'  ← empty is a REAL signature
display.signature([{"sci":"Corvus brachyrhynchos","com":"American Crow","n":20}])
display._bucket(n)                    # 0,0,1,2,3,4,5,6,7,8 for n=0,1,2,5,15,40,100,300,1000,5000
display.in_quiet_hours({"quiet_start":22,"quiet_end":6}, 23)   # True
display.frame_url("https://x/frame.png?k=1", True)             # ...?k=1&labels=1
```

## Test-mocking conventions

* **Module loading by path**, no package install: `tests/test_frame_capture.py:23-27`
  `load(name, path)` uses `importlib.util.spec_from_file_location`. Frame modules are
  therefore importable without `frame/` being on `sys.path` — and
  `frame/display.py`'s `from shoot import …` / `from bundle_runtime import …` still resolve
  because the frame dir is the script dir when run on the Pi; tests patch
  `sys.modules` where needed.
* **Playwright is stubbed** for non-browser tests
  (`tests/test_frame_capture.py:149-152`): a fake `playwright.sync_api` module with
  `TimeoutError` and `sync_playwright = lambda: None` is installed via
  `mock.patch.dict(sys.modules, …)` *around* the import of `frame/shoot.py`.
  Real-browser tests live in `tests/test_frame_capture_browser.py` and are the only
  CI job that needs `playwright install --with-deps chromium`.
* **`bundle_runtime.active_bundle` is patched to `None`** in `setUp`
  (`tests/test_frame_capture.py:157-163`) so bundle code is opt-in per test; bundle
  tests build a `types.SimpleNamespace(drawable_slugs=…, reference=…)` stand-in.
* **`display.run()` is tested by patching its own collaborators** — `load_state`,
  `fetch_species`, `obtain_image`, `fit_panel`, `mat_and_center`, `push_panel`,
  `save_state` — with `contextlib.redirect_stdout/stderr(io.StringIO())`. Copy that
  shape for new refresh-gate tests; it needs no network, no browser, no panel.
* Fakes for HTTP: `Response` (`read(limit)` returns truncated JSON, `.json()`, `.ok`,
  `.status`) and `Route` (records `fulfill`/`continue_`/`fetch` args) at
  `tests/test_frame_capture.py:29-45` and onward.
* `SPECIES = [{"sci": "Corvus brachyrhynchos", "com": "American Crow", "n": 20}]` is
  the shared fixture.
* PHP contracts are plain scripts that `exit(1)` on the first failed `check*()` and
  print `"<thing> tests passed (N checks)"`; a Python wrapper asserts the marker
  string appears. `tests/test_midnight_reset.php` defines
  `AVIAN_BIRDNET_API_LIBRARY_ONLY` before requiring `avian/api/birdnet-api.php` — that constant
  makes the API file load **functions only** (the `if (defined(...)) return;` at
  `avian/api/birdnet-api.php:127`), which is how pure window math gets unit-tested
  without a web server or a DB.
* Frame-local tests (`frame/test_*.py`) run from `frame/` and use `import bundle_runtime`
  directly (implicit cwd on `sys.path`).

## CI workflows

| Workflow | Trigger | What it does |
|---|---|---|
| `.github/workflows/python-app.yml` `build` | push/PR to `main`, `test_me`, `avian-visitors` | `pip install -r requirements.txt`, flake8 (fatal only `E9,F63,F7,F82`), `pytest`. |
| `.github/workflows/python-app.yml` `frame-capture` | same | `pip install pytest Pillow -r frame/requirements-shoot.txt`, `playwright install --with-deps chromium`, `pytest tests/test_frame_capture_browser.py -v`. |
| `.github/workflows/python-ci.yml` | PR to `main` touching `**.py` | flake8 on 3.9/3.11/3.13. |
| `.github/workflows/frame-installer-security.yml` | frame installer changes | container gate via `frame/Dockerfile.install-security` + `frame/check_install_security.sh`. |
| `.github/workflows/validate-bundle.yml`, `.github/workflows/publish-bundle.yml` | bundle submissions/publication | `avian/scripts/` bundle pipeline. |

Related tests worth running with any API change: `tests/test_site_name_api.php`,
`tests/test_birdweather_api.php`, `tests/test_bundle_php_endpoints.py`,
`tests/smoke_collage_readiness.mjs`, `tests/test_birdweather_architecture.py`,
`tests/test_birdweather_reporting.py`.

## PHP harness recipes (no web server needed)

Three patterns already exist — reuse them rather than inventing one:

1. **Load the API as a library.** `define('AVIAN_BIRDNET_API_LIBRARY_ONLY', true)`
   before `require`ing `avian/api/birdnet-api.php`: the `if (defined(...)) return;`
   guard at `avian/api/birdnet-api.php:127` makes the file expose **functions only**,
   so pure logic (e.g. `recentWindow`, `publicConfigFlag`, `publicSiteName`) is
   unit-testable with an `:memory:` SQLite handle and a temp `birdnet.conf`. See
   `tests/test_midnight_reset.php`, `tests/test_site_name_api.php`.
2. **Invoke an endpoint with a fabricated request.** `php -r` with base64-injected
   `$_SERVER` (+ `$_GET`) runs a real endpoint script without Caddy/PHP-FPM —
   `tests/test_educator_security.py:216-236` (`run_endpoint`) is the template, e.g.
   for testing a new `recent` query param against a temp DB.
3. **Lint PHP without executing it:** `php -l <file>` for every API file, gated on
   `shutil.which("php")` (`tests/test_educator_security.py:197-210`).

Time-dependent logic gets a clock override precedent from the educators code:
`AV_EDUCATOR_NOW` (CLI-only, `avian/api/educator-store.php:420-427`). The related env
var `AVIAN_STATION_TIMEZONE` reaches the request because the **generated Caddy config**
passes it as a FastCGI param (all six site blocks: `update_caddyfile.sh:967,976,985,
993,1003,1013`) while the fpm pool runs `clear_env = yes`
(`scripts/security_refresh.sh:118`). Note `tests/smoke_caddy_generated_routes.sh:129`
asserts it on `$_SERVER`, whereas `educator_station_timezone()` reads `getenv()` — so
any `php -r` / `php -S` harness must set it explicitly, and `getenv()` visibility under
real FPM is assumed rather than covered by a test here.

**`php -S` is not `php -r`:** the built-in server runs as SAPI `cli-server`, and every
`AV_EDUCATOR_*` override (`AV_EDUCATOR_BIRDS_DB`, `AV_EDUCATOR_NOW`, lock/state-file
overrides) is gated on `PHP_SAPI === 'cli'`, so they are silently ignored under `php -S`.
Every API request also takes the root-owned Educators lock first
(`avian/api/educator-scope.php:148-157`). See [test-environment.md](test-environment.md).

## Coupling that surprises people

* **`tests/smoke_collage_readiness.mjs` reads frame source.** It does
  `fs.readFileSync('../frame/shoot.py')` and
  `shooter.match(/FRAME_READY = """([\s\S]*?)"""/)` (`:86-88`), then executes that
  predicate in a `node:vm` against a mocked DOM. Reshaping or renaming that literal —
  or moving it into a template/f-string — breaks a Node test from the Python side.
  It also pins site behaviour: `assert.equal(draws.length, 1, 'a successful
  zero-detection result clears old birds')` (`:25`), i.e. the **website** must blank on
  a real empty window.
* **Frozen hash contract:** `tests/test_frame_birdweather.py:191` asserts
  `signature(species)` equals `sha256(json.dumps([(slug, bucket)…]))[:16]` exactly.
  Any new material folded into a signature must go through the `scope` argument or
  that test fails and every existing frame mass-redraws.
* **Browser tests are a separate CI job** with their own install
  (`playwright install --with-deps chromium`); the default `pytest` run must not
  require a browser (`tests/test_frame_capture.py` stubs `playwright.sync_api`).
* **Node smoke tests** (`tests/*.mjs`, `tests/*.test.js`) need node and run outside
  pytest — check which workflow runs them before assuming a change is covered.
