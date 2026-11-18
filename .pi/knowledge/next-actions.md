# Next actions: pending commitments

Promises made to the operator that must survive a lost session
([D25](open-decisions.md#d25--harden-kb-document-so-commitments-and-operator-statements-are-recorded-automatically)).
The `kb-document` extension injects the **Pending** section below into the first prompt of every
session, so a fresh agent sees it without having to choose to read it.

Rules:

* One item per commitment: **Trigger** (what the operator will say or what will happen), then
  **Action** (what to do, in order), then **Log to** (where the result is recorded).
* Never tell the operator "I'll remember" or "when you say X, I'll do Y" unless the item is
  already written here. Say "recorded in next-actions.md" instead.
* When an item is done and logged, move it to **Done** with the date and a link to the log.
  Keep **Pending** short: it costs context on every session start.
* Decisions and questions belong in [open-decisions.md](open-decisions.md), not here. This file
  is only for *actions owed*.

## Pending

1. **Trigger:** the operator says to push the post-Oracle commits (opened 2026-11-17).
   **Action:** `git push origin feature/birdframe-midnight-reset`, verify with `git ls-remote origin`.
   **Log to:** [verification-log.md](verification-log.md) and the open threads.
2. **Trigger:** the operator picks the next stage: V (answer D21) or H (hardware) (opened 2026-11-17;
   recommended: V first).
   **Action:** V → per D21, open a PR **inside the fork** into its `avian-visitors` branch (Actions
   enabled), never the parent; read the CI result. H → write the hardware checklist from plan §6 for
   the operator; §8 deployment needs its own yes.
   **Log to:** D21 / the plan's V or H row, [verification-log.md](verification-log.md), `.pi/handoff/ledger.md`.

## Done

1. 2026-11-17: post-reboot virtualization checks: all three passed; D24 and D23 put to the
   operator. Log: [post-reboot check](verification-log.md#post-reboot-virtualization-check-2026-11-17).
2. 2026-11-17: push after K2: `5f90208c..a66fe045` to `origin`. Log:
   [push record](verification-log.md#push-to-origin-after-k2).
3. 2026-11-17: D30 Oracle review/fix loop: HAPPY at round 2. Logs:
   [round 1](verification-log.md#oracle-loop-round-1), [round 2](verification-log.md#oracle-loop-round-2).
