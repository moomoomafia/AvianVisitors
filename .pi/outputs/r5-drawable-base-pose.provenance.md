# Provenance — R5 brief

* **Brief:** [r5-drawable-base-pose.md](r5-drawable-base-pose.md) (revision 2)
* **Date:** 2026-11-16 · **Workflow:** `deep-research` skill, adapted as for R1: output in
  `.pi/outputs/` (D20); evidence gathered by the parent from local code plus the catalogs' manifest
  URLs over HTTPS; no `verifier` agent exists, so one `reviewer` child verifies.
* **Repository state:** product code at `5950f807`; notes through `124fa0f9` (+ uncommitted R5).

## Sources

| Evidence | Source | How obtained |
|---|---|---|
| E1, E1b | `avian/frontend/apt.js:1557,1559,1611-1614,3147,3164-3186,9439-9445`; `frame/shoot.py:393-401,425,434` | read |
| E2 | `frame/bundle_runtime.py:1237-1238,1270,1414-1415,1429-1430,1605-1606,1651-1652,1883-1889`; `avian/scripts/bundle_validation_contract.py:179-184`; `avian/scripts/bundle_manager.py:371,459-469,2043`; `avian/api/bundle-runtime.php:596-606`; `avian/frontend/apt.js:1235-1270`; `avian/scripts/bundle_export.py:398-408,845-848`; `avian/scripts/bundle_preview_geometry.py:107` | read + grep |
| E3 | `frame/vendor/catalog-v1.json`; live `https://avianvisitors.com/api/bundles/catalog/community-v1.json`; reference `avian/frontend/assets/bundle-catalog/catalog-snapshot.js`; every manifest at `https://avianvisitors.com/api/bundles/manifests/<sha256>.json` | `.pi/research/r5/manifest_scan.py` revision 2 (https-only, host pinned to `avianvisitors.com`; SHA-256 verified; `species` list and catalog `species_count` checked; fails on any problem) |
| E4 | `frame/bundle_runtime.py:46,50,692-711,826-839,1152-1155,1217-1231,1949-1950`; `avian/scripts/bundle_manager.py:110` | read |
| E5 | `frame/display.py:371-374`; `frame/shoot.py:470-482`; `frame/bundle_runtime.py:1455-1458,1883-1889,2026-2052`; `avian/frontend/apt.js:1375` | read |
| D20 framing | `frame/birdweather.py:339-361`; `frame/display.py:383,434` | read |

## Executed

* Revision 1 scan (vendored catalog + station snapshot only): 3 unique manifests, 0 species
  without a base pose — correct but **incomplete scope**.
* Revision 2 scan, 2026-11-16: vendored catalog (3) + live community feed (7) + snapshot reference;
  **12 unique manifests, 0 problems; 1 bundle with 22 flight-only species**
  (`community-peterdeboer-nl-cacd91aeb7749fec`).

## Verification

Independent `reviewer` pass (run `b53c28e4-782b-48a4-bb3e-cd81d20e82c6`) on revision 1 — verdict
**OK with notes**: E1, E1b, E2, E5 confirmed; E3, E4 partial (live community feed not scanned —
P1); headline overstated (P1); several P2s. Revision 2 applies every finding and adds the live-feed
scan that turned the reviewer's "unverified" into a positive finding. Full record:
[../knowledge/verification-log.md](../knowledge/verification-log.md) (section "R5").
