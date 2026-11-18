---
name: kb-document
description: Record findings, decisions and audits into this repo's agent knowledge base (.pi/knowledge) so a memory-less session can be re-primed. Use when the user says document, documented, documentation, record, recorded, write down, note this, register, decision, ruling, "was everything recorded" or "did you document"; after any audit, subagent review, or correction; and before ending a session in this repo.
---

# Document into the knowledge base

Memory is volatile; `.pi/knowledge/` is the memory. This skill is the **single source** of the
documentation procedure for this repo. [AGENTS.md](../../../AGENTS.md) points here; the
`kb-document` project extension injects this file automatically when a trigger word appears.

## When this applies

* The user used a trigger word (document, record, write down, note this, register, decision,
  ruling) or asked whether everything was recorded.
* You learned, decided, or corrected anything about the repo this session.
* A subagent (oracle, reviewer, scout, worker) returned results.
* You are about to end the session or write a summary.

## Rules (each one exists because it was broken once)

1. **Record before you summarise.** A finding that exists only in chat is lost.
2. **Cite `file:line` from a read you actually did.** Full repo-relative path on the first use
   in each section; later uses may shorten. Source refs stay backtick text, never links.
3. **Never state a negative as fact from an empty search.** Write "not found in <where>"
   unless you have the code path that excludes it.
4. **Label assumptions** ("delivery proven; last hop assumed") in the doc *and* the report.
5. **Subagent output is not recorded until you record it.** Distil it into
   `.pi/knowledge/verification-log.md` (agent, run id, method, per-claim verdicts, evidence)
   before acting on it. Re-verify its counter-claims against source and log that check.
6. **Questions and decisions go in the register**, `.pi/knowledge/open-decisions.md`:
   heading `### Dn — question` (no status in the heading — it is the link anchor), then a
   `**Status:**` line: `OPEN`, `ANSWERED <date>` with the operator's words quoted, or
   `PARENT-DECIDED <date>` with the basis. Include why it blocks, options, recommendation,
   consequence if unanswered. Keep the status table at the top in sync. Batch genuine
   blockers into one set of questions with recommendations; answer from house style what
   you can, and record that as a decision with its basis.
7. **Amending a claim or decision:** look it up in `.pi/knowledge/_references.md` first;
   keep the original (strike through `~~…~~` or mark *Superseded / Refuted / Amended* with a
   date and reason); fix every dependent doc it lists; then grep for the **old claim's
   wording** — dependents restate a premise in their own words.
8. **Links:** doc→doc references are relative markdown links, never bare backtick names.
   Headings stay plain text. Prefer `:` over `—` in headings you intend to link (GitHub
   slugs keep double hyphens).
9. **Never promise future behaviour from memory (D25).** "I'll remember", "when you say X,
   I'll do Y", "after the reboot we'll…" are only allowed once the item is written in
   `.pi/knowledge/next-actions.md` (trigger → action → log). Say "recorded in next-actions.md".
   The same applies to the operator's preferences, facts about their setup, and recommendations
   or questions you put to them: those go in the register **in the same turn**. The extension's
   commitment gate sends you back once if a run says such things without touching the KB; if
   nothing needs recording, answer with one line starting `No record needed:` and the reason.

## Procedure

Run this whenever the skill fires, and in full at the end of a session or when asked
"was everything recorded?". **Answer that question from this audit, not from memory.**

1. **Findings sweep.** List what you learned, decided, or corrected (including subagent
   verdicts). Each item is in the knowledge base with a citation, or add it now.
2. **Registers.** New questions have decision IDs; rulings are quoted and dated; the status
   table matches the headings; audits are in `verification-log.md`.
3. **Propagation sweep.** For each amendment, every dependent in `_references.md` agrees,
   and a grep for the *old* wording finds only struck-through or annotated copies.
4. **Index.** `.pi/knowledge/_index.md` lists any new doc; add a hard-won fact where a
   discovery would cost the next agent real time.
5. **Checker.** Run `python .pi/scripts/check_kb.py --index` **unpiped** and require exit 0
   (`… | tail` reports `tail`'s exit code, not the checker's).
6. **Open threads.** Rewrite the dated "Open threads" section at the top of `_index.md` for
   a reader with zero memory of this conversation. Delete threads that closed.
7. **Tidy.** No scratch files or `__pycache__` under `.pi/`.

If any step fails, say so: "recorded, except X" beats a false "all done".

## What the extension does and does not guarantee

The `kb-document` extension (`.pi/extensions/kb-document/`) injects this file when a trigger
word appears, and at the end of a run that changed the knowledge base it runs
`check_kb.py --verify-index` and sends you back (at most twice) if the check fails. That
proves the **mechanical** state: links, anchors, source paths, line ranges, and an up-to-date
index. It cannot prove every finding was written down — steps 1–3 are still yours.
