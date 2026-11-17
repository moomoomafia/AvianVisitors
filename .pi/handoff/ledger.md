# Task ledger — Plan v0.3 §7

Columns from `.pi/knowledge/orchestration.md` (task ledger template); rows are Plan v0.3 §7 steps
only. Update after every child returns. One child at a time; no recursive delegation.

| ID | Phase | Agent | Status | Deps | Key findings / artifacts | Remaining |
|---|---|---|---|---|---|---|
| G0 | Gate | operator | done 2026-11-17: lifted by the operator for W1–W3 | — | quoted in `.pi/knowledge/open-decisions.md` (gate amendment) and `.pi/knowledge/verification-log.md`; handoff `.pi/handoff/{plan,context,ledger}.md` committed | V, H, §8, push/PR still need separate permission; D21 deferred to V |
| W1 | §4.1 station change | worker | dispatched 2026-11-17 | G0 | target: 3 lines in `avian/api/birdnet-api.php` (`:135`, `:169`, `:362`) | Q1 (plan.md): `edu_endpoint` attempt vs recorded gap — unanswered, operator rules |
| W2 | §4.2–4.4 frame + §5 frame tests | worker | not started | W1 | — | not dispatched this session |
| W3 | §4.5 docs | worker | not started | W2 | — | not dispatched this session |
| R | Review | reviewer | not started | W1, W2, W3 | — | — |
| V | §6 local runs; push only if authorised | parent | closed (needs separate permission) | R | — | D21 re-ask here |
| O | Drift/ruling audit | oracle | not started | V | — | — |
| H | Hardware pass on `birdpic` | operator + parent | closed (needs separate permission) | O | — | — |
