# R5 — Can a bird pass the "drawable" check and still not be drawn?

**Question.** D12 keeps yesterday's collage until today's window holds a bird the frame *can
draw*, judged from the frame bundle's species list (`ActiveBundle.drawable_slugs`,
`frame/bundle_runtime.py:2023-2025`). Can a species be in that list yet be dropped by the collage,
recreating the 180-second capture hang D12 exists to prevent?

**Answer: yes — and it is reachable today.** No validator requires a base pose; the collage
draws only the base pose or `-2`; and an installable bundle in the **live community feed**
(`community-peterdeboer-nl-cacd91aeb7749fec`, 329 species) has **22 species with only a flight
pose**. If such a bird is today's only bird, the collage draws it on ~15% of captures and hangs
(180 s, exit 1, bundle revert under `avian-bundle use`/`rollback`) on the other ~85%.

**Recommendation — refine D12's predicate (option A):** *today has a drawable bird* ⇔ some species
in today's window has its **unsuffixed slug as a key in the masks table the collage will load**
(equivalently, a `perched`/`variant-1` pose in the frame bundle). This is the collage's own drop
test (`avian/frontend/apt.js:3176-3179` with `:1613-1614`). Computed locally in the frame; **do not
redefine `ActiveBundle.drawable_slugs`**, which upstream uses at species level for BirdWeather
filtering. Needs a dated amendment to D12 (it refines the operator's word "drawable").

*Revision 2 (2026-11-16), after an independent reviewer pass and a scan of the live community
feed: revision 1 concluded "in practice no", which was wrong — see "Changes from revision 1".*

All file references are to this checkout at `5950f807` (parent `avian-visitors` tip).

## Evidence

### E1 — The collage draws only the base slug or `-2`, and drops the tile otherwise

`avian/frontend/apt.js:3164-3186`: `hasFlight = !!DIMS[base + '-2']` (`:3166`); pose `2` is rolled
with `Math.random() < FLY_PROB` only when `hasFlight` (`:3172`; `FLY_PROB = 0.15`, `:1557`); `slug`
is `base + '-2'` or `base` (`:3176`); the only fallback is pose 2 → base (`:3178`), never base →
`-2`; **`if (!mask) return null`** (`:3179`) then `.filter(Boolean)` (`:3186`). `loadMask` returns
`null` when `MASKS[slug]` is absent (`:1611-1614`). `collagePose` is assigned only at
`:3173,3175,3178`; numbered variants are used only by the postcard picker
(`configurePostcardChoices`, `:9439-9445`). The frame's `apt.js` rewrite does not touch `FLY_PROB`
(`frame/shoot.py:393-401`). **No path reaches `variant-3`+ in the collage.**

**E1b — the roll is fresh each capture.** Each capture launches a new Chromium and a new context
(`frame/shoot.py:425,434`); `collagePose` is an in-memory `var` (`apt.js:1559`) with no storage
persistence; the roll happens after `tablesReady` (`:3147`) — one independent 15% draw per capture.

| Species' poses | Collage behaviour |
|---|---|
| has a base pose (`perched` / `variant-1`) | always drawable |
| only `flight` / `variant-2` | drawn on ~15% of captures, **dropped on ~85%** |
| only `variant-3`+ | **never drawn** |

### E2 — No validator or tool requires a base pose; the parent's exporter can produce flight-only species

| Layer | Rule | Source |
|---|---|---|
| Frame install | v1 1–2 poses from `{perched, flight}`; v2 1–32 `variant-N` | `frame/bundle_runtime.py:1237-1238,1270,1414-1415,1429-1430` |
| Frame install geometry | dims/masks keys must equal the species×pose set; masks non-empty | `frame/bundle_runtime.py:1883-1889,1605-1606` |
| Frame selection | a selection keeps each chosen species' full pose dict | `frame/bundle_runtime.py:1651-1652` |
| Authoring contract (v1) | 1–2 poses with ids in `{perched, flight}` | `avian/scripts/bundle_validation_contract.py:179-184` |
| Station installer | no base-pose rule | `avian/scripts/bundle_manager.py:371,459-469,2043` |
| Station PHP | any non-empty pose set | `avian/api/bundle-runtime.php:596-606` |
| Station frontend tables | key sets must match; species counted after suffix strip | `avian/frontend/apt.js:1235-1270` |
| **Exporter (producer)** | labels any `<slug>-2.png` as `flight` (`:400-401`) and orders only the poses that exist (`:847`) ⇒ a library with `foo-2.png` but no `foo.png` exports a flight-only species that passes every validator | `avian/scripts/bundle_export.py:398-408,845-848` |

Upstream also anticipates a missing `perched` in its preview tool (`poses[0]` fallback,
`avian/scripts/bundle_preview_geometry.py:107`).

### E3 — Scan of every catalog a frame installs from

The frame installs from the vendored official catalog **plus the live community feed**:
`avian-bundle use` → `refresh_catalog` (`frame/bundle_runtime.py:1949-1950`) downloads `CATALOG_URL`
(`:46`, `:1152-1155`) and merges community rows that are `review: community`,
`availability: installable` (`_validate_community_pack`, `:826-839`). The station installer uses
the same feed (`avian/scripts/bundle_manager.py:110`).

`.pi/research/r5/manifest_scan.py` (revision 2) fetched both, plus the station UI snapshot for
reference, downloaded every manifest over HTTPS from `avianvisitors.com`, verified each against
its catalog SHA-256, checked the manifest's `species` list exists and matches the catalog's
`species_count`, and classified every species. **12 unique manifests, 0 problems** (2026-11-16):

| Source | Bundle | Manifest | Species | Base pose | Only `-2` (~15%) | Never drawn |
|---|---|---|---|---|---|---|
| vendored | Japanese Woodblock | v1 | 333 | 333 | 0 | 0 |
| vendored | Evolutionary Impressionist | v1 | 333 | 333 | 0 | 0 |
| vendored | Birds of America | v2 | 439 | 439 | 0 | 0 |
| live feed | `community-bassrelic-9aa94fdebc1f30c6` | v1 | 35 | 35 | 0 | 0 |
| live feed | `community-canberra-act-kachoe` | v1 | 403 | 403 | 0 | 0 |
| live feed | `community-lloydalexporter-a508c0ae358416fb` | v1 | 724 | 724 | 0 | 0 |
| live feed | **`community-peterdeboer-nl-cacd91aeb7749fec`** | v1 | 329 | 307 | **22** | 0 |
| live feed | `community-roquealonso-e824a0e5dde69d4b` | v1 | 442 | 442 | 0 | 0 |
| live feed | `local-station-aa75e3488915ae13688f35ab76899820` | v1 | 20 | 20 | 0 | 0 |
| live feed | `local-station-fd30c12368c0714cca80d3525fcd85e5` | v1 | 54 | 54 | 0 | 0 |

The 22 flight-only species in the Netherlands bundle: *Anas acuta, Ardea herodias, Baeolophus
bicolor, Bubo virginianus, Buteo platypterus, Cardellina canadensis, Coccyzus americanus,
Corthylio calendula, Fulica americana, Leiothlypis ruficapilla, Meleagris gallopavo, Nannopterum
auritum, Parkesia noveboracensis, Piranga rubra, Pluvialis squatarola, Porzana carolina, Rallus
limicola, Sphyrapicus varius, Spizella pallida, Spizella pusilla, Thryothorus ludovicianus,
Tringa melanoleuca.*

This is a **pre-existing upstream behaviour** (the station's own collage drops these birds the same
way); it only becomes a *hang* when the frame captures a window in which such birds are the only
ones.

### E4 — Install sources

The frame installs only catalog rows (`ALLOWED_HOSTS`, `:50`; `resolve_selector`, `:1217-1231`), but
"the catalog" includes the live community feed (E3), so the bound is *any community bundle in the
feed, now or later* — not only future official ones. A dev-only override, `_dev_download` with
`AVIAN_FRAME_BUNDLE_DEV_ROOT` (`:692-711`), can serve local catalogs and manifests; they pass the
same validators.

### E5 — With a frame bundle active, the collage's tables are the bundle's own

`frame/display.py:371-374` passes `cutout_resolver`, `dims_path`, `masks_path` and `bundle_assets`;
`frame/shoot.py:470-482` routes `dims.json`, `masks.json` **and** `avian/api/bundle-assets.php` (the
modern loader, `apt.js:1375`) to the same bundle directory (`frame/bundle_runtime.py:2026-2052`).
`index["assets"][slug]` is keyed by pose id (`:1455-1458`), and install guarantees masks keys equal
`slug + _pose_suffix(pose)` (`:1883-1889`). So **"has `perched` or `variant-1`" ⇔ "unsuffixed slug is
a masks key"** — option A's predicate is exactly the collage's drop test.

## Options for D12's predicate

| Option | "Today has a drawable bird" means | Matches the collage | Safe for every installable bundle today |
|---|---|---|---|
| **A (recommended)** | some species' **unsuffixed slug is a masks key** (frame bundle: `perched`/`variant-1` present) | ✔ exactly (drawn every capture) | ✔ |
| A′ | some species has a base **or** `-2` pose ("drawn sometimes") | ✖ | ✖ — a flight-only-only day hangs ~85% of runs |
| B | species-level `slug in bundle.drawable_slugs` (D12 as recorded) | ✖ | ✖ — Netherlands bundle (E3) |

**Why A, under D20.** B is the parent's own idiom for "drawable" — `frame/birdweather.py:339-361`
collapses `-2` to species level, and `drawable_slugs` is species-level (used for filtering at
`frame/display.py:383,434`). A deliberately deviates from that *definition* because the thing D12
must predict is **`renderCollage`'s** behaviour, and A mirrors that consumer exactly. The cost is the
same single expression over data the frame already holds; no new mechanism. Treating a flight-only
species as undrawable is the correct D12 behaviour: D12a's ruling is "keep yesterday's collage" when
the wall cannot show today's bird, and a redraw that fails ~85% of the time is exactly the
fail-and-retry storm D12 was ruled to avoid.

**Station-default path (no frame bundle).** Same predicate: `slug in MASKS` keys, **no suffix
stripping** — use the masks table, not dims (`hasFlight` reads DIMS but the drop reads MASKS, and the
legacy path fetches them separately, `apt.js:1289-1294`). The station can install community bundles
from the same feed (`avian/scripts/bundle_manager.py:110`), so this matters there too.

**Do not** change `ActiveBundle.drawable_slugs`: that would alter upstream BirdWeather filtering.

## Open / unverified

* E3 is a snapshot of the live feed on 2026-11-16; new community bundles may add more flight-only
  species — option A is safe regardless.
* The station-default path's own masks table was not scanned (it comes from the station's active
  bundle or the bundled `masks.json`).
* A separate, pre-existing hang — a tile with a mask but left unplaced after the shrink passes — is
  out of scope (Audit 2).
* Not implemented; nothing observed on a live station.

## Changes from revision 1

| Item | Revision 1 | Revision 2 |
|---|---|---|
| Headline | "In principle yes; in practice no" | **Yes, reachable today** (Netherlands community bundle, 22 flight-only species) |
| E3 scope | vendored catalog + station UI snapshot | + the **live community feed** the frame actually installs from (`refresh_catalog`) |
| Option B | "correct today" | ✖ unsafe today |
| E2 | validators only | + exporter produces flight-only species; station installer; selections keep all poses |
| E5 | `dims.json`/`masks.json` routes | + `bundle-assets.php` route and the masks-key ⇔ base-pose invariant |
| D20 framing | — | B is upstream's species-level idiom; A deviates to mirror `renderCollage`; don't touch `drawable_slugs` |
| Scan robustness | `or []` could silently report 0 | missing `species` list, SHA mismatch, fetch failure and catalog `species_count` mismatch all fail the scan |
| Line refs | E1 drop `:3163-3190`; contract `:179-183` | drop `:3179/:3186`; contract `:179-184` |
