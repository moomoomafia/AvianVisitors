# AvianVisitors — Agent Knowledge Base

Second brain for this repo. Read `_index.md` first, then open only the doc that
matches the task. Every doc cites `file:line` so you can jump straight to source
instead of re-scouting.

**Entry point for a new session: [`../../AGENTS.md`](../../AGENTS.md)** (repo root) —
Pi's auto-loaded priming contract: prime order, the documentation duty, which register
gets what, and the environment's verification limits. This index is the map; that file is
the rules for keeping the map true.

**Repo:** AvianVisitors — an "Avian Visitors" layer on top of
[BirdNET-Pi](https://github.com/environmentalessay/BirdNET-Pi): a bird-collage
web frontend (`avian/`) plus an optional e-ink wall frame (`frame/`).
**This checkout:** git **worktree** `AvianVisitors-birdframe-midnight-reset`,
branch `feature/birdframe-midnight-reset`, main worktree
`C:/apps/birdNet/AvianVisitors`. Current plan: [`.pi/reset-after-midnight Plan v0.5.md`](../reset-after-midnight%20Plan%20v0.5.md) (2026-11-17; design unchanged since v0.3; [v0.4](../reset-after-midnight%20Plan%20v0.4.md), [v0.3](../reset-after-midnight%20Plan%20v0.3.md), v0.1 and v0.2 kept for history). Plan critique + open questions:
[plan-review-midnight-reset.md](plan-review-midnight-reset.md).

---

**Status (2026-11-17): G0 lifted — building authorised for W1–W3 only** (V, H still closed; ~~2026-11-16: design-ready, building NOT authorised~~ superseded 2026-11-17). All blocking decisions are
ruled ([D12](open-decisions.md#d12--what-does-nothing-to-draw-mean-for-the-d1-decline)–[D16](open-decisions.md#d16--no-validated-list-fetch-failed-or---no-signature-with-the-flag-on) answered via small guiding questions; see
[open-decisions.md](open-decisions.md)). ~~Next step: write Plan v0.3.~~ *(Superseded 2026-11-17: Plan v0.3
is written and W1 is built and reviewed; next is W2 after
[D23](open-decisions.md#d23--commit-the-pending-pi-changes-before-the-w2-worker-runs) — see open thread 0.)* Current shape:
[feature-midnight-reset.md](feature-midnight-reset.md#decided-design-d1d4-ruled-2026-11-16-amended-by-audit-2).

## Open threads (last updated 2026-11-17, Plan v0.5 written)

Written for a reader with zero memory of the conversation. Update this list at the end of
every session; delete items when they close (their history lives in the register and the log).

> **Pending commitments live in [next-actions.md](next-actions.md)** (D25). Read it if the
> extension did not inject it.

0. **Where the build stands.** **[Plan v0.5](../reset-after-midnight%20Plan%20v0.5.md) is current**
   (execution-state revision; design unchanged since v0.3). Built: **W1** (`428f3104`, station +3/−2,
   [post-W1 review](verification-log.md#post-w1-review-implementation-and-test-coverage)) and the
   **K1** Linux test container (`bash .pi/k1/run.sh [ref]`, green on HEAD,
   [K1 log](verification-log.md#k1-build-and-baseline)). **Also built, local commits not pushed:**
   W2 frame code + 14 tests (`dece12cf`, [log](verification-log.md#w2-frame-change-and-tests)),
   W3 docs (`ec5cdc7d`), review R ([log](verification-log.md#review-r-full-product-diff): F1 High,
   a capture straddling the station's midnight could push the empty nest) and its fixes W2R
   (`0046db23`, [log](verification-log.md#w2r-review-r-fixes), Plan v0.5 §4.7). K1 green on
   `0046db23`. `origin` is at `5f90208c`. **Waiting on the operator:** D22 (T1), D27 (K2), a push,
   then D21 for stage V. Handoffs are built with `.pi/scripts/build_handoff.py`.
1. **Open decisions** ([register](open-decisions.md)):
   [D22](open-decisions.md#d22--commit-a-parent-test-for-w1s-request-param) (a committed parent test
   for W1; recommended: one clock-independent `edu_endpoint` case),
   [D27](open-decisions.md#d27--how-the-container-makes-just-after-midnight-happen) (K2's midnight
   clock; recommended: per-run `TZ` offset; Chromium ignores it),
   [D21](open-decisions.md#d21--may-the-parent-open-a-pr-inside-the-fork-so-the-parents-ci-runs) (CI
   via a PR inside the fork; stage V),
   [D28](open-decisions.md#d28--report-the-educator-store-lost-lock-bug-upstream) (file the parent
   bug; draft in [bug-d28-educator-store-lost-lock.md](bug-d28-educator-store-lost-lock.md)).
2. **Before any PR to the parent** (D11c + amendment): strip `.pi/`, [AGENTS.md](../../AGENTS.md)
   and the root `.pi-tasks/`. Whether to go upstream at all (D11a) is undecided. Never commit
   `.pi/ask-log/`.
3. **Still unverified:** `Cache-Control: no-store` with the param (hardware `curl`, plan §6 H); the
   station's PHP version (assumed 8.2); whether the collage's JS uses the page's local `Date` (K2
   only); field frequency of the D28 bug.
4. **Environment:** Docker Desktop + WSL2 work (BIOS virtualization enabled after a CPU swap,
   [post-reboot check](verification-log.md#post-reboot-virtualization-check-2026-11-17)). Windows
   runs (stub `fcntl`, scoop PHP) are pre-checks only. The KB checker
   (`python .pi/scripts/check_kb.py --index`) must exit 0 at the end of every session; the
   `kb-document` extension is active (project trust granted).


## Docs

| Doc | Read it when the task touches… |
|---|---|
| [repo-map.md](repo-map.md) | Orientation: what lives where, entry points, sizes, CI, how the PHP is deployed onto a station. |
| [frame-pipeline.md](frame-pipeline.md) | The frame end to end: systemd timer → data fetch → refresh decision → image → Inky panel. |
| [frame-refresh-decision.md](frame-refresh-decision.md) | Change detection, `signature()`, `state.json`, quiet hours, daily heal, render lock, failure-preserves-panel rules. **Required reading before touching `frame/display.py`.** |
| [birdnet-api.md](birdnet-api.md) | The station JSON API (`avian/api/birdnet-api.php`): actions, params, `recent` response shape, time windows, midnight clamping, caching, educator scope. |
| [frame-render-capture.md](frame-render-capture.md) | How the picture is made: `frame/shoot.py` headless-Chromium capture contract, `avian/frontend/apt.js` handshake (frame token/revision, `__avianFrameCapture`, `?labels=`), `display.py` mat/centre math, Inky push. |
| [birdweather-source.md](birdweather-source.md) | `frame/birdweather.py`: BirdWeather GraphQL, ZIP geocoding, radius growth, triangulation, eBird fallback, drawable-species filter. |
| [illustration-bundles.md](illustration-bundles.md) | Illustration bundles: `frame/bundle_runtime.py` verification/install/select, `avian-bundle` CLI, cutout/dims/masks routing, catalog + manifest integrity. |
| [config-reference.md](config-reference.md) | Every knob: `~/.birdframe/config.toml` keys + defaults, what `frame/install.sh` writes, env file, `state.json`, station-side `birdnet.conf` flags incl. `RESET_AT_MIDNIGHT`. |
| [testing-and-ci.md](testing-and-ci.md) | What to run, what passes on Windows vs Linux, the `fcntl` stub recipe, test-mocking conventions, GitHub workflows. |
| [code-conventions.md](code-conventions.md) | House style: fail-closed validation, atomic writes, symlink-safe IO, minimal deps, comment voice, lint limits. |
| [station-clock-and-data.md](station-clock-and-data.md) | Where `Date`/`Time` come from, what "today" means on a station, indexes, timezone plumbing that does/doesn't exist, LAN admin bypass, caching, deploy + update paths, repo grep traps. |
| [orchestration.md](orchestration.md) | Running the multi-agent plan: verified subagent inventory (`scout`/`oracle`/`worker`/`reviewer`; **no `tester`**), one-child-at-a-time mechanics, `context.md`/`plan.md` handoff contract, ledger template, env constraints children must be told. |
| [feature-midnight-reset.md](feature-midnight-reset.md) | The in-flight feature: verified code facts, draw paths that bypass the gate, window options ranked, edit surface, requirement→code map. |
| [plan-review-midnight-reset.md](plan-review-midnight-reset.md) | Review of the draft plan: gaps, risks, improvements for v0.3, and the question backlog that fed the decision register. |
| [bug-d28-educator-store-lost-lock.md](bug-d28-educator-store-lost-lock.md) | A **parent-repo bug** found by K1 (Educators store drops SQLite locks on Linux): plain-language summary, code path, evidence, reproduction, and a ready-to-file draft issue ([D28](open-decisions.md#d28--report-the-educator-store-lost-lock-bug-upstream)). |
| [next-actions.md](next-actions.md) | **Pending commitments** (trigger → action → log). Injected automatically into the first prompt of every session by the `kb-document` extension ([D25](open-decisions.md#d25--harden-kb-document-so-commitments-and-operator-statements-are-recorded-automatically)). Add an item instead of promising anything in chat. |
| [open-decisions.md](open-decisions.md) | **Decision register.** [D1](open-decisions.md#d1--may-a-forced-render-draw-an-empty-today-window-collage)–[D4](open-decisions.md#d4--what-environment-is-the-acceptance-gate) ruled by the operator (some amended); [D12](open-decisions.md#d12--what-does-nothing-to-draw-mean-for-the-d1-decline)–[D16](open-decisions.md#d16--no-validated-list-fetch-failed-or---no-signature-with-the-flag-on) answered 2026-11-16 (no blocking items open); [D6](open-decisions.md#non-blocking--decided-by-the-parent-from-house-style-to-be-proposed-in-the-pr)–[D10](open-decisions.md#non-blocking--decided-by-the-parent-from-house-style-to-be-proposed-in-the-pr), [D17](open-decisions.md#d17--the-local-mode-served-list-variant) parent-decided; [D5](open-decisions.md#non-blocking--decided-by-the-parent-from-house-style-to-be-proposed-in-the-pr) superseded by [D14](open-decisions.md#d14--how-is-an-un-updated-station-detected-and-with-what-exit-code-supersedes-d5); [D11](open-decisions.md#d11--commit-ignore-or-leave-untracked-pi-and-root-agentsmd) housekeeping. Record rulings inline here. |
| [_references.md](_references.md) | **Generated** reverse index: every doc, source file and decision → the docs that cite it. Look here before amending anything. Regenerate with `python .pi/scripts/check_kb.py --index`; never hand-edit. |
| [verification-log.md](verification-log.md) | Which findings were independently verified, by whom, with what evidence — and which are still assumptions. Read before trusting any claim here. |
| [minimal-footprint.md](minimal-footprint.md) | **The D20 principle in practice**: upstream-change evidence, footprint audit of every design item (before → minimal), estimated shipped diff, research/A-B plan R1–R4. Overrides older design text where they differ. |
| [test-environment.md](test-environment.md) | How to test without the e-ink panel: what's installed here, the fake-station + fake-panel design, why upstream `inky.mock` can't drive a 13.3" panel, and what stays hardware-only. |

---

## 60-second mental model

```
                    ┌────────────────────── STATION (BirdNET-Pi + avian/) ─────────────────────┐
 birdnet_recording  │  birds.db (SQLite)  ←  analysis                                            │
                    │        │                                                                  │
                    │        ▼                                                                  │
                    │  avian/api/birdnet-api.php  ← ?action=recent&hours=24                     │
                    │        │                                                                  │
                    │        ▼                                                                  │
                    │  avian/frontend (apt.js)  →  #collage  (tiles + labels + empty nest)      │
                    └────────┼─────────────────────────────────────────────────────────────┬────┘
                             │ HTTP JSON (intercepted+re-written by shoot.py)              │ screenshots
                    ┌────────▼───────────────── FRAME PI (frame/) ─────────────────────────▼────┐
   systemd timer    │ display.py: fetch species → signature → refresh? → obtain_image →          │
   every 15 min ───▶│   shoot.py (headless chromium, route rewrites) → mat_and_center →          │
                    │   push_panel(inky) ; state.json holds last drawn signature                 │
                    └─────────────────────────────────────────────────────────────────────────────┘
```

Three frame data sources, one renderer:
`local` (screenshot the station site) · `birdweather` (ZIP/station → species list
→ render locally) · `image` (fetch a pre-rendered PNG from someone else).

## Hard-won facts (do not relearn these the expensive way)

1. **`frame/display.py` imports `fcntl`** → it cannot be imported on Windows.
   Tests that load it error with `ModuleNotFoundError: No module named 'fcntl'`.
   Stub it (see [testing-and-ci.md](testing-and-ci.md#running-displaypy-tests-on-windows)).
2. **`signature([])` is a valid, distinct hash.** An empty species list is *not*
   treated as "no data" anywhere in the refresh path — an empty window therefore
   *does* trigger a refresh to the empty-nest collage. This is the single biggest
   hazard for midnight-reset work.
3. **A failed fetch is treated as "no change"**, and a failed image fetch or panel
   push leaves `state.json` untouched so the next cycle retries
   ([frame-refresh-decision.md](frame-refresh-decision.md#failure-rules-the-frame-is-fail-static-not-fail-open)).
4. **The frame never asks the station for a date window** — only `hours=N`. Any
   "today only" semantics must come from a new request param or from response
   fields the frame reads; the station's global `RESET_AT_MIDNIGHT` must stay
   untouched by frame work.
5. **Midnight is computed in the *station's* clock** (`DATETIME(:anchor,'start of
   day')` on SQLite `localtime`), while quiet hours and heal use the **frame Pi's**
   clock. Two clocks, never assume they agree.
6. **`frame/shoot.py` rewrites the page's own network traffic** — `action=recent`,
   `avian/frontend/apt.js`, `avian/api/cutout.php`, `avian/frontend/dims.json`, `avian/frontend/masks.json`, `avian/api/bundle-assets.php`. Today
   `recent` is re-fetched with `hours=\d+` *substituted* (`frame/shoot.py:259`). Under the
   decided design ([D17](open-decisions.md#d17--the-local-mode-served-list-variant)) the flag-on path instead **fulfils** `recent` with the frame's own
   full response, so the page's request never reaches the station; flag-off is unchanged.
7. **Capture is integrity-gated.** Any artwork/API/bundle mismatch aborts the
   refresh and keeps the previous panel image; there are 3 bounded retries and one
   shared deadline. Do not add sleeps or extend the deadline to "fix" flakiness.
8. **One render at a time** via `~/.birdframe/.render.lock` — a concurrent push on
   the 13.3" panel can wedge a half-panel controller until a power cycle.
9. **The refresh gate is not the only way to draw.** `--force` skips it and
   `--no-signature` forces `changed`; `avian-bundle use` (selection changed) and
   `avian-bundle rollback` (always) render with `--force --no-signature --wait-lock`.
   Declining to draw must exit 0, because a non-zero exit makes `use`/`rollback`
   **revert the bundle selection and re-render**
   (`frame/bundle_runtime.py:1962-1972`, `:1993-2000`) — not merely log a failure.
   (`--preview` is exempt: it returns before `push_panel` and cannot touch the glass.)
10. **The website deliberately blanks on an empty window**
    (`tests/smoke_collage_readiness.mjs:25` — "a successful zero-detection result
    clears old birds"), so frame-side retention must never be pushed into `apt.js`.
    That same test regex-extracts `FRAME_READY` out of `frame/shoot.py` and runs it.
11. **`recent` already tells you the station's calendar day** (`station_date`) and
    whether a clamp happened (`midnight_clamped`, `window_start`) — the cheapest
    correct signals available. An IANA zone exists **server-side** but a client never
    needs it, and `as_of` carries its own (non-contractual) zone — never derive a day
    from it.
12. **`Date = :date` can use the `detections_Date_Time` index; `DATETIME(Date||' '||
    Time) >= …` cannot** (`scripts/createdb.sh:20`). `case 'hourly'` is the in-repo
    precedent for a calendar-day window. (Proven on the base table; the API queries a
    `TEMP VIEW` over it, `avian/api/educator-scope.php:486` — flattening is assumed, not proven.)
13. **"Non-empty" ≠ "drawable".** In `local` mode the frame does not filter species by
    available art (`display.py:150`); `apt.js` silently drops maskless tiles
    (`apt.js:3179,3186`) and only signals ready when something was placed (`:3359`). An
    all-undrawable list therefore **hangs capture to the deadline and exits 1**, it does
    not draw an empty nest (that needs an empty list, `:3124`). Exit 1 under
    `avian-bundle use`/`rollback` reverts the bundle.
14. **`php -S` is SAPI `cli-server`, not `cli`.** Every `AV_EDUCATOR_*` test override is
    `cli`-only and is ignored by the built-in server, and every API request first takes a
    root-owned Educators lock (`educator-scope.php:148-157`) — a naive fake station 503s.
15. **Educators mode can silently scope the frame.** During an active classroom capture,
    *unscoped* requests are scoped automatically (`educator-scope.php:182-191`), and
    scoped requests ignore display preferences — including any midnight clamp.
16. **Walk lightly ([D20](open-decisions.md#d20--guiding-principle-minimal-footprint-aligned-with-the-parent-repo)).** Reuse upstream before adding. Two upstream mechanisms make most
    of our planned new code unnecessary: `recentWindow` with `hours=24` *always* clamps a
    today window to midnight (`avian/api/birdnet-api.php:104-116`), and `frame/display.py`
    already re-signs from exactly what the browser was served
    (`frame/display.py:457-463`). The whole station change is three lines (R1 variant B′:
    one new `$resetAtMidnight` local + two one-token swaps in `avian/api/birdnet-api.php`).
    See [minimal-footprint.md](minimal-footprint.md).
17. **PHP runs here now — in a *new* shell.** Scoop's PHP loads SQLite3 via the user env
    var `PHP_INI_SCAN_DIR` + `~/scoop/persist/php/cli/conf.d/zz-avian-sqlite3.ini`. A shell
    older than the install fails `tests/test_midnight_reset.py` with `Class "SQLite3" not
    found` — environment, not product. ~~WSL2/Docker can't start (`HCS_E_HYPERV_NOT_INSTALLED`).~~
    *2026-11-17: WSL2 and Docker work now (BIOS virtualization enabled after a CPU swap).*
18. **"Drawable" has two meanings upstream.** `ActiveBundle.drawable_slugs` /
    `birdweather.drawable_slugs` are species-level (any pose); the collage draws only the base
    pose or `-2` (15% roll) and drops the rest (`avian/frontend/apt.js:3164-3186`). A live
    community bundle has 22 flight-only species. For "will it render?" test the unsuffixed slug
    against the masks table, never `drawable_slugs` (R5).
19. **Local frame-test loop (2026-11-16):** `PYTHONPATH=.pi/research/pre-v03/stubs` (a no-op
    `fcntl` stand-in) runs the parent's frame suites unmodified on Windows — birdweather 18/18,
    capture 76 passed + 7 POSIX-permission failures that never touch `run()`. The today-baseline
    for v0.3 is `.pi/research/pre-v03/test_characterize_today.py` (13/13). The parent is still at
    our base `5950f807` (no drift), and its `.flake8` complexity limit is not enforced
    (upstream `run()` = 18).
20. **Never create `.pi/tools/` (or `.pi/hooks/`) in this repo.** Pi 1.5.2 treats any project
    `.pi/tools/` entry other than fd/rg as deprecated "custom tools". It prints a migration
    warning and **blocks startup on "Press any key"**
    (`checkDeprecatedExtensionDirs` in pi's `dist/migrations.js:220`). Helper scripts go in
    `.pi/scripts/`; the KB checker lives at `.pi/scripts/check_kb.py` (moved 2026-11-17).
21. **`tests/test_educator_backend.php` fails 14/199 on this Windows host on base *and* HEAD**
    (identical set; tar/permission paths). It is the only parent suite that runs
    `avian/api/birdnet-api.php` end to end — don't attribute those 14 to our change; A/B with
    `git archive 5950f807 avian tests scripts | tar -x -C <tmp>` (on Windows; for a Linux extract
    add `-c core.autocrlf=false`, else the files carry CRs: fact 23). Driving the real endpoint in
    CLI needs `educator_store_open(true)` first, else 503 "educator data store is missing or
    unsafe" ([post-W1 review](verification-log.md#post-w1-review-implementation-and-test-coverage)).
    **On Linux (K1, 2026-11-17) it is a different set:** 17 FAIL + a fatal abort, identical on base
    and HEAD, caused by the parent's store code dropping SQLite's POSIX locks
    (`avian/api/educator-store.php:263,321`) and PHP 8.2 `proc_open`. K1 gates it as an A/B against
    `.pi/k1/educator-backend.baseline` ([K1 log](verification-log.md#k1-build-and-baseline)).
22. **You will not remember anything across sessions; promises in chat are lies by default**
    ([D25](open-decisions.md#d25--harden-kb-document-so-commitments-and-operator-statements-are-recorded-automatically)).
    A promise ("when you say X I'll do Y") goes in [next-actions.md](next-actions.md) first. The
    extension injects that file into every new session and sends you back once if a run
    promises, recommends, asks, or hears an operator preference without touching the KB.
    Changes to the extension apply only after `/reload` or a new session.
23. **Never run Linux tests from a bind-mounted worktree.** `core.autocrlf=true`; the working tree
    is CRLF (`frame/install.sh`, `frame/display.py`, `scripts/createdb.sh`, checked with `file`,
    2026-11-17), so `bash\r` breaks scripts in a container. autocrlf comes from the **system**
    gitconfig, and a plain `git archive` applies it too (23 CRs in `scripts/createdb.sh`). Use
    `git -c core.autocrlf=false archive ${ref:-$(git stash create)} | docker run -i … tar -x`
    (0 CRs; tracked files only). The worktree's `.git` is a Windows `gitdir:` path a container
    cannot resolve ([D26](open-decisions.md#d26--container-scope-phasing-and-build-authorisation)).
24. **K1 is the local gate: `bash .pi/k1/run.sh [ref]`** (2026-11-17). No ref = tracked + staged
    worktree state; `5950f807` = base. ~4 min per run (most of it the 38 Chromium tests); exit 0 =
    every named suite passed, none skipped. New files are invisible until `git add`-ed. Rebuild is
    automatic (`docker build` each run; cached).
