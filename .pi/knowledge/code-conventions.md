# Code conventions (what "fits here" means)

Derived from `frame/display.py`, `frame/shoot.py`, `frame/birdweather.py`,
`frame/bundle_runtime.py`, `frame/install.sh`, `avian/api/birdnet-api.php`, and the
test suite. Follow these when writing the midnight-reset change.

## First principle: walk lightly ([D20](open-decisions.md#d20--guiding-principle-minimal-footprint-aligned-with-the-parent-repo))

Everything below describes the *parent repo's* style so our changes are indistinguishable
from it. Before writing any code: reuse an existing upstream mechanism if one exists, match
how upstream made comparable changes (`git log -S`, `git show --stat`), and choose the option
with the smallest trace in shipped files. Our tooling stays in `.pi/`. Applied in
[minimal-footprint.md](minimal-footprint.md). Example of the idiom to copy: upstream reads
query params as `$_GET['x'] ?? default` with a cast or strict compare
(`avian/api/birdnet-api.php:356,403-406`) — not with bespoke parsing helpers.

## Python

* `#!/usr/bin/env python3` + `from __future__ import annotations` first, then a module
  docstring that explains **why the module exists and where it runs** (device vs
  workstation), not just what it does. Match that voice: terse, concrete,
  hardware-aware ("a Zero 2 W needs ~70-120s to shoot the collage").
* Stdlib first, tiny dependency surface. `frame/requirements-frame.txt` is 3 lines.
  Do **not** add a dependency to make frame code easier — Pillow/Playwright/inky/tomli
  are the whole budget on-device.
* Comments explain constraints and consequences, e.g. *why* the lock exists
  ("shows a split image and can wedge one controller until a full power cycle"),
  *why* 60 px band (`a 60px band clears the ~30px eyebrow/headline gap so the title
  stays whole`). A new comment should read like that, not restate the code.
* Python 3.9-compatible (CI matrix 3.9/3.11/3.13). `dict.get` defaults over
  dataclasses for config; `try: import tomllib except ModuleNotFoundError: import tomli`.
* flake8: 160 cols, complexity 15 (CI nags above 10).

## Defensive input handling — the house pattern

Apply every one of these to any new config key, URL, or remote payload:

1. **Reject bools where numbers/strings are expected**
   (`if isinstance(opening, bool): raise`, `birdweather.station_id`, `_bounded_int`).
   `True` is a valid int in Python and that is treated as a bug class here.
2. **Bound every read**: `r.read(2_000_000)`, `read(20_000_000)`, then reject oversize
   (`if len(raw) > 2_000_000: raise`).
3. **Shape-check before use** and raise a domain error: `if not isinstance(data, dict)
   or not isinstance(data.get("species"), list): raise ValueError("recent API has no
   species list")`. A malformed response must **not** degrade to "empty list".
4. **Distinct error types per domain**: `BirdWeatherError(RuntimeError)`,
   `BundleError(RuntimeError)`, `_CaptureChanged(RuntimeError)`.
5. **Strict vs lenient is a deliberate choice, expressed per call**: `_graphql(...,
   strict=True)` for exact-station mode (never substitute another station),
   `strict=False` for radius growth (a transient upstream failure degrades to the next
   fallback). Say which one you chose, in a comment, when it isn't obvious.
6. **Never print or persist a secret**; credentials are read through
   `O_NOFOLLOW`+`dir_fd` with uid/mode/link-count/size/content-regex checks.
7. **Fail static**: a bad fetch must leave the previous state and previous image
   alone. `--missing` exits 0 on lookup failure "so it can never break the installer".

## Filesystem

* Atomic writes only: write `path + ".tmp"`, `flush()`, `os.fsync()`, `os.replace()`
  (`save_state`, `geocode`, `_atomic`). Comment says why: *"atomic: a power cut can't
  leave a half-written file."*
* Capture output is written `open(pending, "xb")` inside a tempdir next to the target,
  then `os.replace`, **preserving the previous file's uid/gid/mode**, and refuses a
  non-regular target (`follow_symlinks=False`, `stat.S_ISREG`).
* Directories created with `0700`, files `0600`; `umask 077` in shell tools;
  `_safe_dir`/`_safe_file` reject symlinks and unexpected owners.
* Config edits preserve everything else in the file — `birdframe-names` rewrites one
  key with `awk` and re-adds it if absent, then `chmod 0600` + `mv`.

## Bash

`set -eu`/`set -euo pipefail`, `umask 077`, absolute binaries
(`/usr/bin/sudo`, `/usr/bin/mktemp`), `PATH=/usr/bin:/bin` + `setpriv --no-new-privs
--reset-env` for launched commands, bounded symlink resolution with fail-closed
errors, `trap 'rm -f "$tmp"' EXIT`, unit files written to a temp then
`install -T -o root -g root -m 0644`, and elevation requested only for the specific
system files it manages.

## PHP

`declare(strict_types=1)`; JSON always via `json_encode`; prepared statements with
bound params (the interpolated values are ints clamped by `max/min` first); read-only
DB handle inside `BEGIN`…`ROLLBACK` with `busyTimeout`; allow-lists for config keys
that may be exposed; `header('Cache-Control: no-store')` on any error path; error
messages public-safe and stable. Guard `defined('AVIAN_BIRDNET_API_LIBRARY_ONLY')`
keeps `recentWindow`/`publicConfigFlag` unit-testable without a web server — keep that
contract intact when extending the API.

## API/behaviour discipline

* **Additive params only.** Existing clients (the site's `avian/frontend/apt.js`, other frames,
  MQTT/export consumers) must behave identically when the new param is absent.
* A new request param must not silently widen a privileged path — educator
  (`edu=`) scopes deliberately ignore display preferences.
* Preserve byte-level compatibility where persisted state is involved
  (`signature(species)` with no scope must hash exactly what older frames hashed, so a
  fleet doesn't mass-redraw after an upgrade).
* Update `frame/config.example.toml` **and** `frame/README.md` for any user-visible
  knob; the README is written as end-user setup prose, not an API dump.

## Docs & commit voice

Short, declarative, lowercase-ish subject lines in the log
(`fix(settings): preserve the minimum range-filter value`,
`Preserve detections when rerunning setup`). Docs favour "do X; Y keeps Z" over
marketing. Prefer the terminology already in use: *collage*, *frame*, *mic*,
*station*, *bundle*, *heal*, *quiet hours*, *drawable*, *selection*, *anchor*.

## Review habits to copy

Every non-obvious rule above has a matching test — e.g.
`test_capture_failure_preserves_panel_state_and_next_cycle_retries`,
`test_saved_signature_describes_captured_data_not_earlier_fetch`,
`test_unscoped_signature_stays_compatible_with_existing_frames`,
`tests/test_midnight_reset.php` ("saved scope ignores the station display
preference"). If you add a behaviour rule, add a test whose **name states the rule**.
