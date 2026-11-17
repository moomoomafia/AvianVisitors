# Agent instructions — AvianVisitors (BirdFrame worktree)

**Memory is volatile. Files are not.** You may be a fresh instance with no recollection
of this repo. Everything a competent agent needs here is on disk. Treat these files as
the authoritative memory, and treat your own recollection as untrusted.

## Prime yourself before doing anything

In this order:

1. **[`.pi/knowledge/_index.md`](.pi/knowledge/_index.md)** — table of contents for the second brain, plus the
   "Hard-won facts" list. Do not skip it; it exists so you do not re-derive an hour of
   scouting.
2. **[`.pi/knowledge/open-decisions.md`](.pi/knowledge/open-decisions.md)** — the decision register. Read the **status
   table at the top**; it is the only place decision status is recorded (this file
   deliberately does not repeat it, so it cannot go stale). Treat an `OPEN` decision that
   governs your task as a hard stop. If a ruling turns out to be unimplementable, amend it
   there with evidence rather than quietly deviating.
   Then read the **Open threads** section of [`_index.md`](.pi/knowledge/_index.md): what the last session left
   unfinished.
3. **[`.pi/knowledge/verification-log.md`](.pi/knowledge/verification-log.md)** — which claims were independently verified and
   which are assumptions. Do not present an assumption as a fact.
4. The topic doc for your task (the index table says which one). Only then open source.

Pi loads this file automatically from the working directory and its parents. Context
files from `<agent-dir>` still apply too; `AGENTS.override.md` would override only this
directory's copy.

## Guiding principle: walk lightly (decision D20)

The operator's words: *"At all points whenever possible, we want to stick to aligning and
defaulting to what the parent repo does. We only change the smallest amount of code to
implement our desired change. If that requires additional research, AB testing, then plan it
out, research it, document it. We walk lightly, quietly, and leave as little trace as possible
the expense of us working harder."*

In practice ([`.pi/knowledge/minimal-footprint.md`](.pi/knowledge/minimal-footprint.md)):

* **Reuse an existing upstream mechanism before adding one** — and prove it exists with a
  `file:line` read. Check how the parent repo made similar changes (`git log -S`, `git show
  --stat`) and match its idiom, file placement and test style.
* **Count the trace** of every option: shipped lines, new files, workflows, config keys,
  response fields, state. Pick the smallest that meets the requirement; when options are
  close, A/B them in a scratch worktree and record the measured result.
* **Our tooling stays in our tree** (`.pi/`, locally git-excluded): harnesses, fakes,
  checkers, notes. Never add them to the parent's `tests/`, workflows, or docs.
* This principle **outranks parent-decided design details**. If it conflicts with an
  operator ruling, re-ask the operator — never override silently.

## Non-negotiable documentation duty

You are maintaining a second brain, not just completing a task.

**The full procedure lives in one place: [`.pi/skills/kb-document/SKILL.md`](.pi/skills/kb-document/SKILL.md).** Read
it before documenting; it is the single source, and the rules below summarise it. In this
repo it is also enforced by a project extension
([`.pi/extensions/kb-document/`](.pi/extensions/kb-document/index.ts), decision
[D19](.pi/knowledge/open-decisions.md#d19--make-the-documentation-duty-fire-automatically-skill-vs-extension)): when the user's prompt contains *document, record, write down, note this,
register, decision, ruling* or asks *"was everything recorded?"*, the extension injects that
skill into the turn; and when a run changes [`.pi/knowledge/`](.pi/knowledge/_index.md) or this file, it runs
`check_kb.py --verify-index` and sends you back (at most twice) if the check fails. That
extension and skill load **only after project trust is granted** — if you see no
`/kb-check` command, they are not active and this file is all you have.

* **Every finding goes in the knowledge base in the same session you made it** — before
  you write your summary to the user. A finding that exists only in chat is lost.
* **Update the register it belongs to** (see next section). Registers are append/inline
  edit; do not create a new file per question.
* **Cite `file:line`** for every claim, from a read you actually did. Line refs drift;
  a ref you did not verify is a liability, not a citation.
* **Re-derive cheap facts instead of reasoning about them.** Two of the sharpest
  corrections in this repo came from running things rather than re-reading prose:
  computing the empty-window hash (`signature([])` → `4f53cda18c2baa0c`) and running
  `EXPLAIN QUERY PLAN` against the real schema. Both cost seconds.
* **Label assumptions explicitly** (e.g. "delivery proven; last hop assumed"). If you
  cannot verify something in this environment, say so in the doc *and* in your report.
* **Never state a negative as fact from a search that came up empty.** "X is not exposed /
  not used / does not exist" needs positive evidence (the code path that excludes it), or
  it must be written as "not found in <where you looked>". The worst error in this base
  so far ("no HTTP-exposed station timezone") was an empty grep written as a fact; it was
  wrong (`scripts/update_caddyfile.sh:967`) and had spread to five docs.
* **Child-agent results are not recorded until you record them.** Subagent outputs live in
  session-scoped artifacts that get cleaned up. Distil every audit/review into
  [`verification-log.md`](.pi/knowledge/verification-log.md) (agent, run id, method, per-claim verdicts, evidence) before
  acting on it.
* **Re-verify a child's counter-claims against source before accepting them**, and log
  the check. Independent reviewers are not infallible: the Oracle cited a wrong line once,
  and catching it required a second read.
* **Amending a claim or decision:** look it up in [`_references.md`](.pi/knowledge/_references.md) first; keep the
  original text (strike through `~~…~~` or mark *Superseded/Refuted/Amended* with a date and
  reason); fix every dependent doc it lists; then grep for the **old claim's wording**, not
  just the new one — dependents restate a premise in their own words.
* **When you find an error, fix everywhere it propagated, then log the correction.**
  One wrong claim here had spread to five files before it was caught. Corrections go in
  [`verification-log.md`](.pi/knowledge/verification-log.md) with the evidence that overturned them.
* **Update [`_index.md`](.pi/knowledge/_index.md)** whenever you add a doc. An orphaned doc is an unread doc.
* **Reference conventions (D18):** doc→doc references are relative markdown links, never
  bare backtick names. Source references stay backtick `path:line` (**not** links — line
  anchors drift and stale links look authoritative), with the **full repo-relative path**
  the first time a file appears in each section. Decision IDs link to
  [the register](.pi/knowledge/open-decisions.md) on first use per section. Headings stay
  plain text: editing a heading changes its anchor. A decision's status lives on a
  `**Status:**` line, never in its heading.
* **Before amending any claim or decision, look it up in
  [`_references.md`](.pi/knowledge/_references.md)** — the generated reverse index of who
  cites which doc, source file and decision. That is how "fix everywhere it propagated"
  is done; grepping for the corrected phrase misses dependents.
* Verify internal links and anchors after edits; broken links read as trusted content
  that vanished. Use **GitHub slug rules** (lowercase, strip punctuation except `-`/`_`,
  spaces → `-`, **no hyphen collapsing**): an em dash in a heading yields a double hyphen
  (`Audit 1 — Oracle` → `audit-1--oracle`), so prefer `:` in headings you intend to link.

## Registers

| Register | File | Rule |
|---|---|---|
| Decisions & open questions | [`.pi/knowledge/open-decisions.md`](.pi/knowledge/open-decisions.md) | Heading `### Dn — question` (never a status in the heading — it is the link anchor), then a `**Status:**` line: `OPEN`, `ANSWERED <date>` (quote the operator's words) or `PARENT-DECIDED <date>` (answered from house style; give the basis). Body: why it blocks, options, recommendation, consequence if unanswered. Keep the status table at the top in sync. Never resolve a decision silently in code; amendments keep the original text plus a dated note. |
| Verification & audits | [`.pi/knowledge/verification-log.md`](.pi/knowledge/verification-log.md) | One dated section per audit: who ran it (agent + run id), method, per-claim verdicts with evidence and *what would falsify it*, corrections forced, what is still unverified. If an audit overturns a claim, the log records both the old and new wording. |
| Orchestration task ledger | `.pi/handoff/ledger.md` | Only when running the multi-agent plan: task id, phase, agent, status, dependencies, findings, remaining. Update after every child returns. |
| Hard-won facts | [`.pi/knowledge/_index.md`](.pi/knowledge/_index.md) | Short, load-bearing, non-obvious rules. Add when a discovery would cost the next agent real time or a wrong decision. |

Question-handling discipline: **collect before asking.** Batch genuine blockers into one
numbered set with recommendations rather than drip-asking; anything answerable from the
repo's existing conventions is answered there and recorded as a decision with its basis,
not escalated.

## Verification honesty

This workstation cannot verify most of what matters here, and that must never leak into
a report as a green check:

* `php` is absent → PHP contract tests are `skipUnless` and **pass vacuously**.
* `fcntl` is absent → every `frame/display.py`-dependent test errors on import.
* `os.geteuid` / `os.O_NOFOLLOW` absent → installer and credential tests fail to collect.
* No e-ink panel → requirement checks must assert *"no push was attempted"*, not
  *"the display looks right"*.
* `pytest tests/` and `pytest frame/` abort at collection. Run named files.

The agreed fix is **[D4](.pi/knowledge/open-decisions.md#d4--what-environment-is-the-acceptance-gate)**: a Debian dev container (php-cli, php-sqlite3, Python 3.11 venv,
Playwright Chromium) with a fake station and a headless fake panel, mirrored as a CI job —
see [`.pi/knowledge/test-environment.md`](.pi/knowledge/test-environment.md) (read its Audit-2 amendment: `php -S` is SAPI
`cli-server`, the Educators lock must be provisioned, and there is no clock seam for
`recent`). Until that container exists, do not claim coverage from anything run on this
Windows box. Note the existing Linux CI (`.github/workflows/python-app.yml`) already runs
`pytest` where `fcntl` works — a CI result is real evidence; a local skip is not.

Any report must name the environment and list what was **not** executed.

## Feature freeze (current branch)

Branch `feature/birdframe-midnight-reset`. The draft brief is
[`.pi/reset-after-midnight Plan v0.2.md`](.pi/reset-after-midnight%20Plan%20v0.2.md); it is a **rough draft and building the feature is
NOT authorised** — that is an operator permission, and only the operator can lift it.
Whether the *design* is settled is a separate question answered solely by the register's
status table (open items are also marked ⚑ in
[`.pi/knowledge/feature-midnight-reset.md`](.pi/knowledge/feature-midnight-reset.md) "Decided design"). Scout, document, review, question.
Read [`.pi/knowledge/plan-review-midnight-reset.md`](.pi/knowledge/plan-review-midnight-reset.md) first if you intend to revise the plan:
the draft's Phase 3 as written would blank physical displays.

Standing safety rails for this product: never overwrite a working e-ink collage with a
blank screen to be "correct"; never touch the station-wide `RESET_AT_MIDNIGHT` setting or
historical detections from frame code; do not commit, push, or open PRs without explicit
authorisation; do not discard unrelated local changes.

## Practical repo traps

* **Grep traps:** `avian/frontend/assets/bundle-catalog/catalog-snapshot.js` is a ~1 MB
  single-line JSON blob; `scripts/gotty*` are binaries; `avian/frontend/apt.js` is
  ~15k lines. Scope greps or you will drown your own context.
* `frame/display.py` is POSIX-only (`fcntl`); the frame targets Python **3.9** (CI
  matrix 3.9/3.11/3.13), flake8 160 cols / complexity 15.
* `extras/archive/tests/` are archived — do not "fix" them.
* `tests/smoke_collage_readiness.mjs` reads `frame/shoot.py` as text and executes the
  extracted `FRAME_READY`; site behaviour that "looks like a bug" may be a pinned
  contract. Read the test before "cleaning up" behaviour.
* **The bash tool sometimes runs under cmd.exe**: `VAR=x cmd`, `$(...)` and heredocs then
  fail or misbehave silently (a variable never set, a backup never written). Wrap
  multi-step shell in `bash -lc '...'`.
* **Never write `\uXXXX` escapes into file content** via the write/edit tools: they are stored
  literally and render as "\u2014" in markdown. Type the real character.
* **Python printing non-ASCII to this console crashes** (cp1252 `UnicodeEncodeError`) — set
  `PYTHONIOENCODING=utf-8`. A crash *after* a write leaves a half-finished batch, and an
  `&&` chain then skips your cleanup: re-check state, don't assume.
* **Shell on this Windows box:** native Python resolves `/tmp` to `C:\tmp`, not the bash
  temp dir — pass `$(cygpath -m /tmp)` paths into Python. Very long heredocs can be cut
  off mid-command (the write silently doesn't happen): put large content in a file with
  the write tool, then process it. Don't leave scratch files or `__pycache__` in `.pi/`.
* `.pi/` **and this `AGENTS.md`** are **committed on this branch** (D11c, pushed to the operator's
  fork `origin`). They **must be removed before any PR to the parent repo** (`upstream`, push
  disabled). `.pi/ask-log/` must never be committed. *History:* they were previously hidden from git **locally** via `.git/info/exclude`
  ([D11](.pi/knowledge/open-decisions.md#d11--commit-ignore-or-leave-untracked-pi-and-root-agentsmd)) — shared by every worktree; no git history, so only as safe as this disk.
  **Never run `git clean -x` or `-X` here: they delete ignored files** (the whole knowledge
  base). Committing them later needs `git add -f`, and only after the operator decides.
* Subagents: `scout`/`oracle`/`worker`/`reviewer` exist; **there is no `tester`**. One
  child at a time on this machine; `worker` starts blank and reads `context.md` +
  `plan.md`, so write them. Details in [`.pi/knowledge/orchestration.md`](.pi/knowledge/orchestration.md).

## End of session (and whenever the operator asks "was everything recorded?")

Run the 7-step **Procedure** in [`.pi/skills/kb-document/SKILL.md`](.pi/skills/kb-document/SKILL.md) (findings sweep,
registers, propagation sweep, index, checker, open threads, tidy) — not a summary of it
from memory. The checker proves links and paths are valid; it **cannot** prove your
findings were written down. That is your job, and the operator does check — answer from
the audit. If any step fails, say so in your report: "recorded, except X" beats a false
"all done".
