# Illustration bundles

A **bundle** is a signed, content-addressed pack of bird cutout PNGs + geometry
(dims/masks) that replaces the repo's built-in illustrations. Station-side UI is
**Settings → Bird bundle**; on a station or BirdFrame the CLI is `avian-bundle`.

Runtime code: `frame/bundle_runtime.py` (2175 lines). Station-side PHP:
`avian/api/bundle-runtime.php`, `avian/api/bundles.php`, `avian/api/bundle-assets.php`,
`avian/api/bundle-species.php`, `avian/api/bundle-preview.php`, `avian/api/cutout.php`.

## Command chain (defence in depth, worth knowing before you touch it)

```
avian-bundle (frame/avian-bundle)            checkout launcher, refuses root,
   │                                         resolves its own symlinks ≤16 hops,
   │                                         PATH=/usr/bin:/bin, exec setpriv
   ▼                                         --no-new-privs --reset-env
frame/vendor/avian-bundle-control            release-pinned wrapper (15 lines)
   ▼
frame/avian-bundle-installed                 installed launcher
   ▼
frame/bundle_runtime.py main()               use / rollback / (list)
```

`--reset-env` is why credentials are read from files, not the environment (see
[birdweather-source.md](birdweather-source.md#ebird-credential-handling-_private_ebird_key-276)).

Install creates the symlinks: `birdframe-names` and the `avian-bundle` control link
(`frame/install.sh:557-559`).

## Selection flow

```bash
sudo avian-bundle use '<BUNDLE_ID>'      # from https://avianvisitors.com/bundles
```

1. Resolve the selector against the community catalogue
   (`CATALOG_URL = https://avianvisitors.com/api/bundles/catalog/community-v1.json`,
   `:46`; host allow-list `ALLOWED_HOSTS = {"avianvisitors.com"}`, `:50`).
2. Determine a **selection basis** from the frame's own config
   (`_mirror_selection_basis` `:396`, `_resolve_selection_basis` `:432`) — the
   mirrored station's location, or the configured BirdWeather ZIP/station
   (`station_location()` in `frame/birdweather.py`). No location ⇒ full bundle;
   `--all-species` requests it explicitly.
3. Download + verify manifest and every object (`_validate_manifest` `:1252`,
   `_validate_install_contents` `:1826`), PNG-validated on read
   (`_validate_webp`/`decode_capture_image` live in `frame/capture_art.py`).
4. Activate **atomically** (`_exchange_directories` `:582`, `_atomic` `:614`,
   `operation_lock` `:638`); state in `<bundle_root>/state` (`_state_path` `:1911`).
5. If the selection changed, trigger a render (`_render_callback` `:2083`).
   Failure at any step leaves the previous bundle active.

Budgets/limits worth remembering (`:63-77`): catalogue 2 MiB, history 4 MiB /
10 000 entries, manifest 4 MiB, geometry tables 24 MiB, image 4 MiB, total 1 GiB,
5000 species, 6 previews, 4096 px edge, 16 M pixels, 128 MiB free-space reserve,
config 256 KiB, selection 2 MiB. Licenses allow-list at `:78`.
`rollback()` `:1976` re-activates the prior reference.

## What `display.py` consumes

`active_bundle(root)` (`:2071`) → `ActiveBundle` (`:2007`) or `None`:

| Member | Use in `frame/display.py` / `frame/shoot.py` |
|---|---|
| `.reference["revision"]` / `["selection_revision"]` | mixed into the refresh signature (`display.py:438-441`, `:459-463`) — a bundle change forces a redraw |
| `.drawable_slugs` | passed as `fetch_species(..., drawable=…)` so the species list is filtered to the bundle, not the repo set |
| `.resolve(sci, pose)` | cutout resolver ⇒ `shoot` fulfils `avian/api/cutout.php` requests from verified files (`shoot.py:307 _make_cutout_handler`) |
| `.dims_path` / `.masks_path` | routed over `**/dims.json*` and `**/masks.json*` (`shoot.py:~490`) |
| `.assets_response()` | served for `**/avian/api/bundle-assets.php*` (`shoot.py:367`) |

`obtain_image` turns these into `shoot()` kwargs `cutout_resolver`, `dims_path`,
`masks_path`, `bundle_assets` (`display.py:367-375`).

Pose mapping in the cutout route (`shoot.py:316-321`): `pose=1` → `perched` (base
slug), `2` → `flight` (`slug-2`), `3..32` → `variant-N` (`slug-N`). The handler also
demands that the request's `bundle=`/`content=` match the active bundle's
`{revision, content_revision}` identity or it 404s/500s — the frame refuses to mix
artwork revisions inside one capture.

Integrity failures are sticky: `bundle_errors` set anywhere ⇒ the capture aborts with
`"active bundle failed integrity validation"`, and `run()` refuses to draw at all if
`active_bundle()` raised (`display.py:426-428`).

## Mode interactions

* Bundle switching applies to **local and birdweather render modes only**. An
  `--image-url` frame shows someone else's pixels — choose the bundle on that source
  (`frame/README.md`).
* Without a selected bundle, birdweather mode renders from this repo's illustrations:
  local `avian/assets/illustrations/` first, then 302 to
  `https://raw.githubusercontent.com/Twarner491/AvianVisitors/avian-visitors/avian/assets/illustrations/`
  (`frame/shoot.py:52`). So a `git pull` can deliver new art without a redeploy.
* Bundled illustrations centre on the western US; the installer flags species it
  cannot draw and the frame skips them. Generate the missing ones off-device with
  `frame/generate_illustrations.py --zip 10001 --gemini-key …` (or `--station-id`);
  it uses the same rembg cutout path, which the Pi cannot fit in memory.
* Repo-side pipeline lives in `avian/scripts/` (`avian/scripts/bundle_canonical.py`,
  `avian/scripts/bundle_moderate.py`, `avian/scripts/bundle_validate.py`, `avian/scripts/bundle_publish.py`, `avian/scripts/build_masks.py`,
  `avian/scripts/pregen.py`, `avian/scripts/cutout.py`, …) with publication docs in
  `docs/official-bundle-publication.md`, `docs/bundle-catalog-migration.md`,
  `docs/bundle-review-zero-trust.md` and workflows `.github/workflows/publish-bundle.yml`,
  `.github/workflows/validate-bundle.yml`.
* Tests: `frame/test_bundle_runtime.py`, `frame/test_bundle_render_integration.py`,
  `tests/test_bundle_*.py`, `tests/test_station_bundle_catalog.py`.
