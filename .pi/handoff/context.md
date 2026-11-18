# Worker context — BirdFrame midnight reset, step W2

Prepared by the parent on 2026-11-17 (Plan v0.5 step P2) from the knowledge base; no fresh scout
(the base holds the scout phase). Authoritative design: `.pi/handoff/plan.md` (verbatim Plan v0.5
§3–§9 + rulings). Ledger: `.pi/handoff/ledger.md`. Background, if needed:
`.pi/knowledge/frame-refresh-decision.md`, `.pi/knowledge/frame-render-capture.md`,
`.pi/knowledge/testing-and-ci.md`.

## Files retrieved (anchors re-checked 2026-11-17: `frame/` and `tests/` are byte-identical to base `5950f807`)

* `frame/display.py:42-70` — `DEFAULTS` (add `"reset_at_midnight": False`).
* `frame/display.py:91-101` — `fetch_recent` (extract into `fetch_recent_payload`, keep the wrapper).
* `frame/display.py:366`, `:395-400` — `obtain_image` → `shoot(...)` call.
* `frame/display.py:418-445` — `run()` signature/refresh block; `:429-443` the `if use_signature:` block,
  `:438-441` the bundle salt, `:445` `--no-signature` ⇒ `changed = True`.
* `frame/display.py:457-463` — upstream re-sign from what the browser was served (keep).
* `frame/display.py:520-528` — `main()` takes the render lock before `run()`.
* `frame/shoot.py:243-259` — `_make_api_handler`, `hours=\d+` substitution at `:258-259`.
* `frame/shoot.py:412`, `:448` — `shoot(...)` signature and the route.
* `frame/bundle_runtime.py:1883-1889` — install invariant (base pose ⇔ masks key).
* `avian/frontend/apt.js:3164-3186` — collage drop test (read-only reference; do not edit).
* `tests/test_frame_capture.py` — where every §5 frame row goes, in its existing style (it stubs
  Playwright; see `:149-152`).
* `.pi/research/pre-v03/test_characterize_today.py` — characterization C1–C8 of today's behaviour
  (13/13 on HEAD). Read-only for you; the parent re-runs it.

## How to test (Windows host, your shell)

* Fast pre-check:
  `bash -lc 'cd C:/apps/birdNet/AvianVisitors-birdframe-midnight-reset && PYTHONPATH=.pi/research/pre-v03/stubs python -m pytest tests/test_frame_capture.py tests/test_frame_birdweather.py -q'`
  Baseline on Windows: the 7 POSIX-permission failures in `tests/test_frame_capture.py`
  (chmod/`os.geteuid` tests) exist **before** your change; they must stay exactly 7 and nothing new
  may fail. `fcntl` is stubbed by `.pi/research/pre-v03/stubs/fcntl.py`.
* `python -m flake8 --select=E9,F63,F7,F82 frame tests` must be clean; respect `.flake8` (160 cols).
* **The real gate is the Linux container K1** (`bash .pi/k1/run.sh`), which the parent runs after
  you return. You may run it yourself (~4 min) but it only sees **committed or staged** files.
* The bash tool may run under cmd.exe: wrap multi-step shell in `bash -lc '...'`. Python printing
  non-ASCII crashes the console unless `PYTHONIOENCODING=utf-8`.
* `core.autocrlf=true`: write files with LF; git normalises.

## Rules for every child

* You have **no subagent tool**; do not spawn agents or shell out to `pi`.
* Do not touch, commit, or clean untracked or unrelated files (`.pi/`, `.pi-tasks/`,
  `.pi/ask-log/`, `AGENTS.md`); never `git add -A`/`-u`, `git commit -a`, `git clean`, `git stash`.
  No push, no PR.
* §4.6 "Not changed" is a hard boundary. Python 3.9-compatible code. Match upstream style
  (comment voice, fail-closed validation); don't refactor `run()` to meet complexity.
* Frame target is Python 3.9; CI tests on 3.11.

## Report back

Diff stat, the commit hash, the test commands you ran with their exact pass/fail counts, any
deviation from §4/§5 (with the reason), and anything you could not verify.

## Start here

`plan.md` "Precedence rule", then §4.2 → §4.3 → §4.4, then §5 frame rows, then the W2 row in §7.
