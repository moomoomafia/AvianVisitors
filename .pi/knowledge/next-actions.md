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

1. **Trigger:** the operator says to push (opened 2026-11-17; D22 and D27 parts done: T1 `db9ff938`,
   K2 `6eb0658b`).
   **Action:** `git push origin feature/birdframe-midnight-reset` (`origin` is at `5f90208c`; never
   `upstream`), then verify with `git ls-remote origin`. Pushing the feature branch triggers no CI.
   **Log to:** [verification-log.md](verification-log.md) (push record) and the open threads.
2. **Trigger:** the operator answers
   [D30](open-decisions.md#d30--which-stage-next-after-k2-o-v-or-h) (opened 2026-11-17).
   **Action:** O → dispatch `oracle` for a drift/ruling audit of `git diff 5950f807 HEAD -- avian frame
   tests` against Plan v0.5 §4/§7, D1–D3, D12–D17, D20 and the safety rails; re-verify its counter-claims;
   log it. V → needs a push and D21 first. H → write the hardware checklist from plan §6 for the
   operator; §8 deployment needs its own yes.
   **Log to:** the D30 entry, [verification-log.md](verification-log.md), `.pi/handoff/ledger.md`.

## Done

1. 2026-11-17: post-reboot virtualization checks: all three passed; D24 and D23 put to the
   operator. Log: [post-reboot check](verification-log.md#post-reboot-virtualization-check-2026-11-17).
