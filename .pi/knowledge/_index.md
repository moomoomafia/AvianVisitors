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
`C:/apps/birdNet/AvianVisitors`. Feature brief: `.pi/reset-after-midnight Plan
v0.2.md` (draft; v0.1 kept for the delta). Plan critique + open questions:
[plan-review-midnight-reset.md](plan-review-midnight-reset.md).

---

**Status (2026-11-16): design-ready, building NOT authorised.** All blocking decisions are
ruled ([D12](open-decisions.md#d12--what-does-nothing-to-draw-mean-for-the-d1-decline)–[D16](open-decisions.md#d16--no-validated-list-fetch-failed-or---no-signature-with-the-flag-on) answered via small guiding questions; see
[open-decisions.md](open-decisions.md)). Next step: write Plan v0.3. Current shape:
[feature-midnight-reset.md](feature-midnight-reset.md#decided-design-d1d4-ruled-2026-11-16-amended-by-audit-2).

## Open threads (last updated 2026-11-16, after the pre-v0.3 probes)

Written for a reader with zero memory of the conversation. Update this list at the end of
every session; delete items when they close.

1. **[D12](open-decisions.md#d12--what-does-nothing-to-draw-mean-for-the-d1-decline)–[D16](open-decisions.md#d16--no-validated-list-fetch-failed-or---no-signature-with-the-flag-on) ruled (2026-11-16)** via small guiding questions: decline only when
   today has **no drawable** bird (frame uses its own bundle); reset ignores `hours`
   (everything since midnight); outdated station ⇒ hold + **exit 1**; station unreachable
   on a manual run ⇒ report failure (bundle switch reverts); Educators not used (D15
   parent-decided: hold, exit 0). **Next: write Plan v0.3** from the register + "Decided
   design".
2. **[D18](open-decisions.md#d18--knowledge-base-reference-conventions-linking) done (2026-11-16):** hybrid linking applied; `python .pi/tools/check_kb.py --index`
   now validates the whole base and regenerates [_references.md](_references.md). It must
   exit 0 at the end of every session (see [AGENTS.md](../../AGENTS.md)).
3. **[D11](open-decisions.md#d11--commit-ignore-or-leave-untracked-pi-and-root-agentsmd) settled (D11c, 2026-11-16):** `.pi/` and [AGENTS.md](../../AGENTS.md) are committed on this
   branch and pushed to the operator's fork (`origin`). **Strip them before any PR to the
   parent repo** — whether this goes upstream at all (D11a) is still undecided. Never commit
   `.pi/ask-log/`.
4. **[D19](open-decisions.md#d19--make-the-documentation-duty-fire-automatically-skill-vs-extension) built, awaiting trust:** the `kb-document` skill + extension exist and pass
   20/20 tests plus a headless real-Pi load, but they load in normal sessions **only after
   you approve the project-trust prompt** on next start. Then do one live check: plant a
   broken link in a scratch KB doc, say "document this", and confirm the injected procedure
   and the end-of-run fix-up continuation. Until trusted, `/kb-check` is absent.
5. **Building the feature is not authorised.** Separate from the design status; only the
   operator can lift it.
6. **R5 answered (2026-11-16): yes, reachable today** — a live community bundle has 22
   flight-only species; D12's "drawable" now means "unsuffixed slug is a masks key" ([R5 brief](../outputs/r5-drawable-base-pose.md)).
   No open research questions remain.
   **Still unverified, but no longer blocking:** how often a day's first detection lacks art
   (urgency of D12 only); Playwright 1.62.0 on Debian 12 (only matters for the blocked D4
   container). **Moot under [D20](open-decisions.md#d20--guiding-principle-minimal-footprint-aligned-with-the-parent-repo)** (the design no longer depends on them): `getenv()`
   visibility of `AVIAN_STATION_TIMEZONE` under FPM, and index use through the unscoped
   `TEMP VIEW` (the `Date =` optimisation was dropped). *(Closed
   since: GitHub runners have PHP + SQLite3 — R2; the clamp and param-shape claims — R3.)*
7. **PHP now runs locally** (scoop, PHP 8.5; [R3](verification-log.md#r3-execute-the-clamp-and-param-shape-claims-with-php)): the parent's PHP suites and the R3
   checks execute for real. Still not executed: anything needing Linux (`frame/display.py`
   tests, the fake station + fake panel) or hardware. The [D4](open-decisions.md#d4--what-environment-is-the-acceptance-gate) container
   does not exist; Docker Desktop's daemon is off on this machine, and **WSL2 cannot start**
   (Wsl/Service/CreateInstance/CreateVm/HCS/HCS_E_HYPERV_NOT_INSTALLED — Virtual Machine Platform / virtualization not enabled;
   found 2026-11-16 when attempting R3), so Docker almost certainly can't run either. The
   D4 container needs virtualization enabled first (admin + reboot).
8. **[D20](open-decisions.md#d20--guiding-principle-minimal-footprint-aligned-with-the-parent-repo) principle adopted (2026-11-16):** align with the parent repo, change the least
   code. [minimal-footprint.md](minimal-footprint.md) shrank the design. Re-asked rulings:
   D17 → **use the parent repo's flow** (superseded); D4's CI clause → **no new workflow**
   (after R2: parent CI already runs PHP + SQLite3 on `ubuntu-latest`). **R1 done**
   (variant B′, [brief](../outputs/r1-station-param-variant.md)); R3 remains (execute the
   `hours=24` clamp proof and the param-shape claims in the `.pi/` container with `php`).
9. **Next natural step:** write Plan v0.3 from the register +
   [minimal-footprint.md](minimal-footprint.md) (which overrides the older
   "Decided design" where they differ); then, when authorised, the harness in `.pi/` before
   any feature code.

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
| [open-decisions.md](open-decisions.md) | **Decision register.** [D1](open-decisions.md#d1--may-a-forced-render-draw-an-empty-today-window-collage)–[D4](open-decisions.md#d4--what-environment-is-the-acceptance-gate) ruled by the operator (some amended); [D12](open-decisions.md#d12--what-does-nothing-to-draw-mean-for-the-d1-decline)–[D16](open-decisions.md#d16--no-validated-list-fetch-failed-or---no-signature-with-the-flag-on) answered 2026-11-16 (no blocking items open); [D6](open-decisions.md#non-blocking--decided-by-the-parent-from-house-style-to-be-proposed-in-the-pr)–[D10](open-decisions.md#non-blocking--decided-by-the-parent-from-house-style-to-be-proposed-in-the-pr), [D17](open-decisions.md#d17--the-local-mode-served-list-variant) parent-decided; [D5](open-decisions.md#non-blocking--decided-by-the-parent-from-house-style-to-be-proposed-in-the-pr) superseded by [D14](open-decisions.md#d14--how-is-an-un-updated-station-detected-and-with-what-exit-code-supersedes-d5); [D11](open-decisions.md#d11--commit-ignore-or-leave-untracked-pi-and-root-agentsmd) housekeeping. Record rulings inline here. |
| [_references.md](_references.md) | **Generated** reverse index: every doc, source file and decision → the docs that cite it. Look here before amending anything. Regenerate with `python .pi/tools/check_kb.py --index`; never hand-edit. |
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
    found` — environment, not product. WSL2/Docker can't start (`HCS_E_HYPERV_NOT_INSTALLED`).
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
