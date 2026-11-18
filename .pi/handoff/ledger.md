# Task ledger — Plan v0.5 §7

Columns from `.pi/knowledge/orchestration.md` (task ledger template); rows are Plan v0.5 §7 steps
only (~~v0.3~~, ~~v0.4~~ superseded 2026-11-17; v0.4 added P2 and T1; v0.5 added K1/K2). Update after every child returns. One child at a time; no recursive delegation.

| ID | Phase | Agent | Status | Deps | Key findings / artifacts | Remaining |
|---|---|---|---|---|---|---|
| G0 | Gate | operator | done 2026-11-17: lifted by the operator for W1–W3 | — | quoted in `.pi/knowledge/open-decisions.md` (gate amendment) and `.pi/knowledge/verification-log.md`; handoff `.pi/handoff/{plan,context,ledger}.md` committed | V, H, §8, push/PR still need separate permission; D21 deferred to V |
| W1 | §4.1 station change | worker | done 2026-11-17 (local commit "feat(api): accept reset_at_midnight=1 per request") | G0 | +3/−2 in `avian/api/birdnet-api.php` (now `:136`, `:170`, `:363`); PHP 20+6 checks, R3 30/0 + 20/0 re-verified by parent | Q1 (now D22, open): `edu_endpoint` works (needs lock + real clock); operator decides whether to add the case. 2026-11-17 parent review: end-to-end verified by `.pi/research/w1/recent_param_probe.php` (base fails 3, HEAD passes); no committed test yet; Cache-Control unverified |
| P2 | W2 pre-dispatch (Plan v0.5 §7) | parent | done 2026-11-17 | W1 | D23 done (`94663e4b`); `.pi/handoff/plan.md` + `context.md` regenerated from v0.5 with the "§4 wins" rule and W2 commit rules | — |
| K1 | `.pi/` Linux test container | parent | done 2026-11-17 | D26 | `bash .pi/k1/run.sh`; base and HEAD baselines in the verification log; educator backend gated A/B (parent bug D28) | re-run after each worker step |
| W2 | §4.2–4.4 frame + §5 frame tests | worker | done 2026-11-17, local commit `dece12cf` | W1, P2, K1 | +302/−9 in 3 files, 14 new tests; parent: K1 green on `dece12cf` (91 passed), characterization 13/13, all new tests fail on pre-W2 code | review R: `run()` complexity 28, preview on fetch failure, missing `sci` |
| K2 | fake station + fake panel + scenarios | parent | not started | W2, D27 | — | operator rules D27 first |
| W3 | §4.5 docs | worker | done 2026-11-17, local commit `ec5cdc7d` | W2 | +4 lines (README paragraph, commented config line); parent: README test 14 passed in K1, TOML parses | — |
| T1 | optional PHP case (Plan v0.4 §5, only if D22 = a) | worker | not started (D22 open) | W1 | added 2026-11-17 by Plan v0.4 | case must pass on HEAD and fail on base `5950f807` |
| R | Review | reviewer | not started | W1, W2, W3 (+T1 if any) | — | — |
| V | §6 local runs; push only if authorised | parent | closed (needs separate permission) | R | — | D21 re-ask here |
| O | Drift/ruling audit | oracle | not started | V | — | — |
| H | Hardware pass on `birdpic` | operator + parent | closed (needs separate permission) | O | — | — |
