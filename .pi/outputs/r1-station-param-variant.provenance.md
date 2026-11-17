# Provenance — R1 brief

* **Brief:** [r1-station-param-variant.md](r1-station-param-variant.md)
* **Date:** 2026-11-16 · **Workflow:** `deep-research` skill, adapted:
  * Output in `.pi/outputs/` instead of a repo-root `outputs/` — decision D20 keeps our
    artifacts out of the parent repo's tree.
  * The skill names `researcher`, `verifier`, `reviewer`. The question is answered by local
    code and git history, not the web, so the parent gathered evidence directly (no
    `researcher`); there is **no `verifier` agent** in this environment, so independent
    verification is done by one `reviewer` child (read-only).
* **Repository state:** worktree `AvianVisitors-birdframe-midnight-reset`, product code at
  `5950f807` (unchanged parent tip); notes commit `a5a1c4db`.

## Sources (all local, read-only)

| Evidence | Source | How obtained |
|---|---|---|
| E1, E2 | `avian/api/*.php` top-level assignments | one-off scan script (deleted after use) matching `^\$[A-Z][A-Z0-9_]+\s*=` and `^\$[a-z]\w*\s*=` |
| E3, E4 | commits `116471c1`, `f1cb3add` | `git show`, `git log -S educatorCacheDisabled` |
| E5 | `frame/display.py:93-96`, `frame/shoot.py:425,434`, `scripts/update_caddyfile.sh` | grep |
| E6 | `git log -L129,129`, `-L169,169`, `-L362,362` on `avian/api/birdnet-api.php` | git |
| E7 | `avian/api/birdnet-api.php:127`, `tests/test_midnight_reset.php:4,33` | read |
| E8 | `avian/api/birdnet-api.php:135,281,356,403-406` | read; PHP semantics argued |

## Not executed

No PHP interpreter on this machine. E7's clamp and E8's array-param rejection are argued from
code and language semantics; research item R3 executes them in the `.pi/` container.

## Verification

* **Reviewer pass:** one `reviewer` child, run `199f88cc-69de-4453-bf68-b7dac284e421`, read-only,
  no git, no `php`. Verdict **OK with notes**: E2 confirmed; E3/E4/E6 confirmed in source, commit
  attribution unverifiable without git; E5 confirmed and strengthened; **E1, E7, E8 partial** —
  two P1 findings (C wrongly ranked as a fallback; E8 omitted key mangling contrary to D3) and six P2.
* **Parent re-verification of the counter-claims** (all held): `avian/api/export.php:450-459`
  (`$EXTRACTED`); `tests/test_educator_backend.php:64-76,664-668` (`edu_endpoint`, `recent`);
  `.pi/knowledge/open-decisions.md:181` (D3 "folded aliases" amendment);
  `.pi/knowledge/minimal-footprint.md:96` (R1 originally specified `$resetAtMidnight`).
* **Revision 2** of the brief applies every finding; see its "Changes from revision 1" table.
  Full record: [../knowledge/verification-log.md](../knowledge/verification-log.md) (section "R1").
