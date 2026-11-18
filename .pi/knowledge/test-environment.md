# Test environment: how far without the e-ink panel

Answers three questions with evidence, for decision **[D4](open-decisions.md#d4--what-environment-is-the-acceptance-gate)** in
[open-decisions.md](open-decisions.md): can a VM/venv with PHP cover the reset feature,
can the panel be emulated, and where hardware becomes unavoidable.

**Short answers:** Yes on the virtual environment — and it beats real hardware for
*this* feature, because the hard cases are time-travel cases you cannot stage on a wall.
Yes on panel emulation, but **not with the official one** — upstream `inky.mock` cannot
drive a 13.3" panel, so a small headless fake is the right tool. Hardware stays
necessary only for physics: refresh artifacts, burn-in, the controller-wedge hazard,
timing, and colour fidelity.

## What this machine has (probed 2026-11-16)

| Tool | Status |
|---|---|
| `php` | **Installed 2026-11-16 per-user via scoop: PHP 8.5.12** (CLI, ZTS, x64). SQLite3 enabled by `~/scoop/persist/php/cli/conf.d/zz-avian-sqlite3.ini`; loaded in shells that have scoop's user `PHP_INI_SCAN_DIR`. Runs the parent's PHP tests natively ([R3](verification-log.md#r3-execute-the-clamp-and-param-shape-claims-with-php)). *Earlier: absent.* |
| `docker` | **Inferred unavailable too (not verified):** Docker Desktop on Windows needs the WSL2 or Hyper-V backend, and Hyper-V is reported as not installed. CLI at `C:\Program Files\Docker\...\docker.exe`; **daemon not running** (`//./pipe/dockerDesktopLinuxEngine` not found) — needs Docker Desktop started |
| `wsl` | *2026-11-17: **works** after BIOS virtualization was enabled (Ubuntu boots, Docker Desktop 4.91.0 runs; [post-reboot check](verification-log.md#post-reboot-virtualization-check-2026-11-17)); the K1 container is built ([K1 log](verification-log.md#k1-build-and-baseline)).* ~~**WSL2 registered but cannot start**~~ (checked 2026-11-16 when attempting R3): `wsl -d Ubuntu` fails with `Wsl/Service/CreateInstance/CreateVm/HCS/HCS_E_HYPERV_NOT_INSTALLED` — "WSL2 is not supported with your current machine configuration. Please enable the 'Virtual Machine Platform' optional component and ensure virtualization is enabled in the BIOS." Fix needs admin: `wsl.exe --install --no-distribution` (+ reboot, possibly BIOS). *Earlier text: "WSL2 present, `Ubuntu` (Stopped) + `docker-desktop` distro" — the distros are registered, but none can run.* |
| `node` / `npm` | present |
| Python | 3.14 (default) + 3.13; **no 3.11**; `venv`/`ensurepip` OK; Pillow, pytest, playwright importable |
| `sqlite3` | present (miniconda) |
| `choco` / `scoop` / `winget` | all present |
| POSIX modules | `fcntl`, `os.geteuid`, `os.O_NOFOLLOW` **absent** → `frame/display.py` cannot import here |

Consequence: **Linux is required regardless of the panel question** — `display.py` will
not even import on Windows. So "venv on Windows with PHP" covers the PHP contract only,
not the frame. WSL2 Ubuntu or a container is the minimum viable environment, and both are
already installed here.

There is also in-repo precedent for the container route: `frame/Dockerfile.install-security`
is digest-pinned `debian:bookworm-slim` + `apt-get install` (≈ Raspberry Pi OS base),
driven by `.github/workflows/frame-installer-security.yml`, and
`tests/publication-runtime.Dockerfile` exists for the bundle pipeline. A test container
would follow an established pattern, not invent one.

## Layer 1 — no new infrastructure (already available today)

* Patched-collaborator unit tests in `tests/test_frame_capture.py`
  (`load_state`/`fetch_species`/`obtain_image`/`push_panel`/`save_state` all mocked):
  these answer *"was a refresh attempted?"* — which is 90% of the brief's acceptance
  list — with no panel, no browser, no PHP.
* `display.py --preview out.png [--mat-box]` renders the real layout + a 6-ink dither to
  a PNG and **never touches the panel or state** (`frame/display.py:469-474`).
* Limits: cannot run here (`fcntl`), cannot prove PHP window math, cannot prove anything
  about real pixels.

## Layer 2 — the station simulator (the real prize)

> **Amended 2026-11-16 (Audit 2, F-H6) — read before building.** The fake station below
> is harder than first written. Parent re-verified each point:
>
> * `php -S` runs as SAPI **`cli-server`**; every API test override is gated on
>   `PHP_SAPI === 'cli'` (`avian/api/educator-store.php:39,46,52,101,421,492`;
>   `avian/api/educator-state.php:23,30`) — so `AV_EDUCATOR_BIRDS_DB`, `AV_EDUCATOR_NOW` etc. are
>   **ignored** under `php -S`.
> * Every request takes `educator_store_lock(false)` **before** checking whether Educators
>   is enabled (`avian/api/educator-scope.php:148-157`); the lock is
>   `/var/lib/avian-visitors/educators.lock` (root:caddy 0660, real `caddy` group, posix
>   functions). Unprovisioned ⇒ **every** call returns 503. Provision it in the image, or
>   drive endpoints through the `php -r` harness (`tests/test_educator_security.py:216-236`)
>   where the `cli` overrides do work.
> * Paths are fixed relative to the served file (`avian/api/birdnet-api.php:35-36`):
>   `<tree>/../../scripts/birds.db`, `birdnet.conf` at `dirname(__DIR__,2)`. Serve a
>   **copied** tree.
> * **No clock seam for `recent`**: today and the anchor are SQLite
>   `'now','localtime'` (`birdnet-api.php:280,294-296`). The `AV_EDUCATOR_NOW` reference
>   below does not apply. Use rows seeded relative to *real* now, a `TZ` offset, or
>   `libfaketime` — choose explicitly.
> * `scripts/createdb.sh` is not a fixture (sources `/etc/birdnet/birdnet.conf`, writes
>   `$HOME/BirdNET-Pi/…`, `DROP TABLE`, `chown`) — copy its DDL.
> * Don't install `requirements.txt` (station ML stack) or `frame/requirements-frame.txt`
>   (real `inky` → `spidev` needs a compiler and defeats the fake panel). Pillow +
>   `frame/requirements-shoot.txt` + pytest.
> * DST cases drop out if [D13](open-decisions.md#d13--does-the-today-window-respect-the-hours-setting) picks the calendar-day (`Date =`) form.
> * CI already runs `pytest` on Linux (`.github/workflows/python-app.yml` `build`) and has a Python 3.11 +
>   Playwright job (`frame-capture`); extend it rather than adding a parallel job.

Debian container or WSL2 Ubuntu with `php-cli`, `php-sqlite3`, `sqlite3`, Python venv
(Pillow, pytest, Playwright Chromium). What that unlocks:

1. **Real PHP contract tests**: `php tests/test_midnight_reset.php` stops skipping and
   stops passing vacuously; `php -l` on changed API files; the existing
   `php -r` endpoint harness with a fabricated `$_SERVER`/`$_GET`
   (`tests/test_educator_security.py:216-236`) and the
   `AVIAN_BIRDNET_API_LIBRARY_ONLY` library-load trick.
2. **A fake station**: serve the real `avian/api/` with `php -S` against a synthetic
   `birds.db` built from `scripts/createdb.sh` (including its indexes), then run the real
   `frame/display.py` in `local` mode against it. This makes every time scenario in the brief
   *deterministic and repeatable*:
   * yesterday full / today empty (the blank-the-wall case) — seed rows dated
     `now - 20 h`, run at `now + 5 h` conceptually, or simply seed relative to a chosen
     anchor;
   * first detection at 00:04 on the day boundary;
   * three consecutive silent days (heal interaction);
   * 23-hour and 25-hour DST transition days;
   * station clock ahead of / behind the frame's clock;
   * **an old station that ignores the new param** (drop the param handling and assert the
     degrade path);
   * boundary rows at `00:00:00` vs `23:59:59` — the exact case
     `tests/test_midnight_reset.php` pins.
   Prefer seeding the database relative to a chosen anchor over changing the container
   clock; the repo already has a clock-override precedent for CLI logic
   (`AV_EDUCATOR_NOW`, `avian/api/educator-store.php:420-427`).
3. **`fcntl` works** → the 19 currently-erroring `display.py` tests and all of
   `frame/` collect and run; `os.geteuid`/`O_NOFOLLOW` return the installer/credential
   tests.
4. **A fake panel** (see next section) → end-to-end "seed detections → assert exactly one
   update with today-only pixels, and zero updates across midnight".

This is strictly stronger than a physical frame for the above: on hardware you cannot
un-hear a bird, you cannot make midnight arrive, and you cannot re-run the same
boundary case twice.

## Layer 3 — panel emulation: what's actually possible

**Upstream `inky.mock` cannot emulate this panel.** Verified from `pimoroni/inky@master`:

* `inky/inky.py`: `_RESOLUTION` = `(800,480)`, `(600,448)`, `(400,300)`, `(212,104)`,
  `(250,122)`.
* `InkyMock.__init__` raises `ValueError("Resolution …x… not supported!")` for anything
  outside that set — the frame's panel is **1600×1200** (`inky_el133uf1`,
  `frame/display.py:308-327`), so the stock mock refuses it.
* `inky/__init__.py` exports only `InkyMockPHAT` and `InkyMockWHAT`; there is no
  Impression/13.3" mock class in the package namespace.
* `InkyMock.__init__` calls `tkinter.Tk()` unconditionally → needs a display server
  (X11 or `xvfb-run`), so it is an *interactive preview*, not a CI-friendly fake.
* `pip install inky` itself fails on Windows: `dependencies = numpy, pillow, smbus2,
  spidev, gpiodevice` and `spidev` is Linux-only. Upstream issue
  [pimoroni/inky#78](https://github.com/pimoroni/inky/issues/78) is exactly this
  regression ("Mock version of inky doesn't work on windows anymore"); issue
  [#168](https://github.com/pimoroni/inky/issues/168) is the resolution-override limitation.

So: **do not build on `inky.mock`** for the 13.3". Two better options:

1. **Headless recording fake (recommended).** `push_panel` lazy-imports `inky`
   (`display.py:313-318` — deliberately, "so this module still loads on a machine without
   the Inky library"), so a stub `inky` package on `PYTHONPATH` intercepts it with **zero
   production changes**:
   * `inky.auto.auto()` and `inky.inky_el133uf1.Inky(resolution=(1600,1200))` return an
     object with `width/height = 1600/1200`, `set_image(buf, saturation=...)`, `show()`.
   * It appends each update to a list and writes `update-NNN.png`, and asserts the
     branch actually taken (`panel = "el133uf1"` vs `auto()`), the rotate value, and the
     `saturation` kwarg path (`display.py:322-326` inspects the signature — a fake whose
     `set_image` lacks `saturation` exercises the other branch).
   * Then "no refresh at midnight" is a literal assertion: **update count == 0**, and
     "first detection replaces the collage" is **update count == 1 with today's species
     rendered**. That is exactly what the brief asks to prove.
2. **Visual preview without hardware** — already exists as `--preview`. Note its own
   comment: the six `SPECTRA6` inks are *"approximate… On hardware the Inky library maps
   to the panel's real palette"*, so preview is a layout tool, not a colour proof.

If a live window is genuinely wanted for demo/review, run the real driver API shape under
WSL2 with a Tk window (or `xvfb-run` + screenshot) using a patched `_RESOLUTION`; that is
a nice-to-have, and it is a *fork of upstream behaviour*, so it must not be mistaken for
testing the real library.

## What only the physical panel can prove

| Not emulatable | Why |
|---|---|
| Partial-refresh artifacts, ghosting, burn-in, and therefore the **heal policy** | depends on the real waveform; and [D7](open-decisions.md#non-blocking--decided-by-the-parent-from-house-style-to-be-proposed-in-the-pr) (suppress heal during an empty window) is precisely a burn-in question |
| The **split-image / controller-wedge hazard** under concurrent pushes | documented in `frame/display.py:516-528`: two half-panel controllers, wedged only a full power cycle recovers. A fake lock proves nothing about it. |
| Real capture timing on a Zero 2 W (70–120 s) vs `timeout = 180` and `TimeoutStartSec=300` | hardware CPU/memory bound; `frame/README.md` says desktop/container tests do not replace a capture check on the frame Pi |
| Colour fidelity / saturation on Spectra-6 ink | emulation uses an approximate palette |
| SPI/I2C enablement, reboot-on-install, power behaviour | kernel/firmware |
| Physical A5 opening geometry, mat shadow, legibility at viewing distance | optical |
| Retention over a multi-day silent stretch in a real room (sunlight, temperature) | environment |

## Recommended shape of D4

Three tiers, cheap first:

1. **Now (zero install):** keep using the patched-collaborator tests as the design
   harness on any machine; treat local PHP/display results as *not run*.
2. **Build once, use forever (recommended):** a Debian-based dev container
   (`php-cli`, `php-sqlite3`, `sqlite3`, Python 3.11 venv, Playwright Chromium,
   optionally `xvfb`) containing (a) the real API files + synthetic `birds.db` station
   fixture, (b) the headless `inky` fake, (c) a scenario runner covering the brief's 11
   cases plus the audit's extras (bundle/`--force` paths, corrupt `state.json`,
   boot-after-outage timer run, DST day). Mirror it as a CI job so "tests pass" means
   something reproducible; the repo already runs a Debian container gate this way.
   > **D20 (2026-11-16):** the container, fake station, fake `inky` and scenario runner live
   > in **`.pi/`** (our locally-excluded tree), not in the parent's `tests/`. Feature tests go
   > only into upstream's existing files (`tests/test_midnight_reset.php`,
   > `tests/test_frame_capture.py`) in their style, which upstream CI already runs. The "new CI
   > job" clause was ruled **"No new workflow"** after research R2 (2026-11-16); DST cases drop out under the
   > `recentWindow` reuse. See [minimal-footprint.md](minimal-footprint.md).
3. **Before merge, one hardware pass on `birdpic`:** the residual table above, with a
   written checklist and the result recorded in
   [verification-log.md](verification-log.md).

Do not let tier 2 become a reason to skip tier 3 — `frame/README.md` is explicit that
capture must be checked on the frame Pi. And do not let tier 1 reports say "tests pass"
when the environment skipped them (see
[verification-log.md](verification-log.md) claim 12).

## Cost and caveats

* Container build is a one-off (Playwright Chromium is the bulk: ~~~150 MB~~ **656 MB** for Chromium 151 with `--with-deps`, measured by the Oracle 2026-11-17) and needs
  Docker Desktop started, or use WSL2 Ubuntu directly (already installed, `wsl -l -v`
  shows it Stopped — it starts on demand).
* Windows-side `php` via `choco`/`scoop`/`winget` is possible and would make the PHP
  contract runnable natively, but it is a partial environment: `frame/display.py` still cannot
  import, so it splits the verification story for no gain over WSL2.
* Keep any fake-panel shim in `tests/` (e.g. a fixture package on `PYTHONPATH`), never as
  an env-var branch inside `display.py` — the house style is lazy import + test-side
  patching, and a production hook for tests invites the fake to drift from the real
  driver.
* A container is not the panel: it cannot falsify "the wall looks wrong". Reports must
  name which tier proved what.
