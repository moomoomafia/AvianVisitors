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

1. **Trigger:** the operator answers ~~D22, D27~~ or "push" *(D27 answered 2026-11-17: TZ shift first; K2 in progress)* (opened 2026-11-17; the `ask_user`
   batch timed out unanswered after W2R). *D22 part done 2026-11-17: T1 `db9ff938`,
   [log](verification-log.md#t1-smoke-alarm-for-w1-d22).*
   **Action:** D27 ruled → build K2 in `.pi/` (fake
   station + fake `inky` + midnight scenarios incl. the F1 straddle). Push authorised →
   `git push origin feature/birdframe-midnight-reset` (`origin` is at `5f90208c`).
   Recommendation: D27 per-run `TZ` offset.
   **Log to:** the register entries (quote the ruling), [verification-log.md](verification-log.md),
   `.pi/handoff/ledger.md`.

## Done

1. 2026-11-17: post-reboot virtualization checks: all three passed; D24 and D23 put to the
   operator. Log: [post-reboot check](verification-log.md#post-reboot-virtualization-check-2026-11-17).
