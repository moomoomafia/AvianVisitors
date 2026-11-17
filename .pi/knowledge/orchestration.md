# Orchestration in this environment

Ground truth for executing
[.pi/reset-after-midnight Plan v0.2.md](../reset-after-midnight%20Plan%20v0.2.md)
as a parent orchestrator. Verified on this machine, not assumed.

## Available child agents

Source: `~/.pi/agent/npm/node_modules/pi-subagents/agents/*.md`. The plan's named
roles map onto real agents except **Tester**, which does not exist.

| Plan role | Actual agent | Tools | Notes that change how you use it |
|---|---|---|---|
| Scout | `scout` | read, grep, find, ls, bash, **write**, contact_supervisor | `output: context.md`, `thinking: low`, `systemPromptMode: replace`, `inheritProjectContext: true`, `inheritSkills: false`. Writes `context.md` into **its cwd** and returns a short summary — it is a *writer*, so never run it in a tree a worker is editing. Mandated output shape: Files Retrieved / Key Code / Architecture / Start Here, with exact `file:lines`. |
| Oracle | `oracle` (alias `advisor`) | read, grep, find, ls, bash (read-only, `acceptanceRole: read-only`) | `thinking: high`, **`defaultContext: fork`** — inherits a fork of *your* conversation as its authoritative contract, so it is the anti-drift check and needs almost no briefing. Output shape: Inherited decisions / Diagnosis / Drift check / Recommendation / Risks / Need from main agent / Suggested execution prompt. Will `contact_supervisor` for a decision when blocked. Default stance: prefer narrow corrections over plan rewrites; does **not** assume a worker handoff follows. |
| Worker | `worker` (aliases developer/coder/implementer) | read, grep, find, ls, bash, edit, write, contact_supervisor | `acceptanceRole: writer`, `thinking: high`, **`defaultContext: fresh`**, **`defaultReads: context.md, plan.md`** → it starts blank and reads those two files, so *that is the handoff protocol*: write `plan.md`, have scout write `context.md`. |
| Reviewer | `reviewer` | read, grep, find, ls, **watchdog_diff**, contact_supervisor | `acceptanceRole: read-only`, `thinking: high`. Has a diff tool — hand it the diff, not a re-scout. |
| Tester | **none** | — | Use `worker` to author+run tests, `reviewer` (read-only) to judge. There is also `evidence-auditor` (web-claim checking, not test running). |
| — | `researcher` | read, write, web_search, fetch_content, get_search_content, source_check | `output: research.md`. Only if upstream BirdNET-Pi behaviour needs external sourcing. |
| — | `delegate` | read, grep, find, ls, bash, edit, write, contact_supervisor | Parent model, `systemPromptMode: append`, no default reads. Closest thing to a general hand. |
| — | `claude-code`, `codex-exec`, `cursor-agent` (+`-writer` variants) | external CLIs | **Avoid**: the plan requires one child at a time and no recursive delegation; these spawn their own agent loops. |

Related skills that exist here: `pi-subagents` (orchestration patterns),
`council-mode` (supervisor-mediated advisor council). Both are loaded in the parent.

## Enforcing "maximum one active child"

Use the **one-child form** of the `subagent` tool, one call at a time:

```
subagent({ agent: "scout", task: "…" })
```

* Do **not** pass `workflow: "parallel"`, `args.tasks`, an array of `{agent,task}`, or
  `Promise.all` — the plan bans batch dispatch, and one-writer-per-cwd is also a
  correctness rule here.
* Async is allowed by the plan (`async: true`), but only one run may be in flight:
  a child must be completed, failed, cancelled, or confirmed terminated before the
  next launch. Native async completion wakes this session, so return control and wait
  rather than polling with `bg_wait`.
* Delegation depth 1: instruct every child explicitly — *"do not spawn subagents;
  you have no subagent tool"* — since `worker`/`scout` can `bash`, a motivated child
  could otherwise shell out to `pi -ne`. If a child reports it delegated, treat it as
  a failed run.
* `model` overrides are supported per child (`:minimal/:low/:high` suffixes); the
  agent defaults (`scout` low, `oracle`/`worker`/`reviewer` high) are sensible.

## Single-writer hazard specific to this repo

Every child runs in **this worktree** (`AvianVisitors-birdframe-midnight-reset`)
unless you pass `cwd`/`worktree`. Two consequences:

1. `scout` writes `context.md` and `worker` reads `context.md`/`plan.md` — pin the
   path in the task text (e.g. `.pi/handoff/context.md`) and pass the same
   `defaultReads` path, or children will scatter `context.md` across the repo root.
   Those handoff files are **untracked artifacts**: decide whether they belong in git
   (see [station-clock-and-data.md](station-clock-and-data.md) on `.pi/` being
   untracked and un-ignored).
2. `worker` may `git status`/`git diff` and see `.pi/` noise; tell it explicitly not
   to touch, commit, or clean untracked files.

## Environment constraints children must be told

* **`php` is not installed here** → every PHP contract test skips. A worker that
  "verifies" a PHP change by running `pytest tests/test_midnight_reset.py` has
  verified nothing (it passes vacuously). Either install PHP, run in WSL/Docker, or
  state plainly in the report that the PHP contract was not executed.
* **`fcntl`, `os.geteuid`, `os.O_NOFOLLOW` are absent** → `frame/display.py`-dependent
  tests error locally; use the stub recipe in
  [testing-and-ci.md](testing-and-ci.md#running-displaypy-tests-on-windows) and label
  it a local-only check.
* No e-ink hardware on this machine: requirement checks must assert *"would a refresh
  have been triggered"*, via the patched-collaborator pattern in
  `tests/test_frame_capture.py`.
* Full-suite runs abort at collection here (15 errors in `tests/`, 4 in `frame/`).
  Run named files, not bare `pytest`.
* No commits/pushes/PRs without explicit authorization (plan §4) — and the parent
  should verify children obey, since `worker` has `bash`.

## Gate before dispatching any Worker

**All blocking decisions are ruled** ([D1](open-decisions.md#d1--may-a-forced-render-draw-an-empty-today-window-collage)–[D4](open-decisions.md#d4--what-environment-is-the-acceptance-gate), 2026-11-16 — see
[open-decisions.md](open-decisions.md)), so Phase 3 is design-ready. **It is not yet
authorised**: the operator has not approved building the feature, and their instruction
stands until they say otherwise. When they do, copy the rulings verbatim into
`plan.md` for the Worker handoff — do not re-ask a decided question, and if a ruling
proves unimplementable, amend it in the register with evidence rather than deviating.
**D4** fixes Phase 5's environment: a Debian dev container (php-cli, php-sqlite3, Python
3.11 venv, Playwright Chromium) with a fake station and a headless fake panel, mirrored in
CI, plus a mandatory `birdpic` hardware pass before merge — see
[test-environment.md](test-environment.md). Phase 5 never runs on Windows.
Everything from [D5](open-decisions.md#non-blocking--decided-by-the-parent-from-house-style-to-be-proposed-in-the-pr) on is already answered in the register; paste those rulings into the
Worker's brief rather than re-asking.

## Task ledger template (plan §4 asks for one)

Keep it as a table in `.pi/handoff/ledger.md` and update it after each child:

| ID | Phase | Agent | Status | Deps | Key findings / artifacts | Remaining |
|---|---|---|---|---|---|---|
| P1-S1 | Discovery | scout | queued | — | → `.pi/handoff/context.md` | |
| P2-A1 | Architecture | oracle | queued | P1-S1 | master plan → `.pi/handoff/plan.md` | |
| P3-W1 | Impl: window logic | worker | queued | P2-A1 | | |
| P3-W2 | Impl: retention/refresh | worker | queued | P3-W1 | | |
| P3-W3 | Impl: config + docs | worker | queued | P3-W1,W2 | | |
| P4-R1 | Review | reviewer | queued | P3-* | findings by severity | |
| P5-T1 | Tests | worker | queued | P4-R1 | | |
| P6-O1 | Final audit | oracle | queued | P5-T1 | PR-readiness verdict | |

Seed each child with: the plan file, the ledger, `.pi/handoff/context.md`, and the
relevant [knowledge base](_index.md) docs — the plan says avoid repeated repo
exploration, and the knowledge base already contains the Scout phase for this
feature ([feature-midnight-reset.md](feature-midnight-reset.md),
[station-clock-and-data.md](station-clock-and-data.md)). Consider starting Phase 1
from that material and asking Scout to *verify and extend* rather than re-scout from
zero — cheaper, and it catches knowledge drift.
