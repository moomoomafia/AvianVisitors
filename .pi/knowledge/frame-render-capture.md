# How the picture is made

Two halves: `frame/shoot.py` turns live HTML into a validated 1200×1600 PNG, and
`frame/display.py` mats that PNG onto the panel and pushes it to the Inky driver.

## Modes of producing an image (`display.py:366 obtain_image`)

| Branch | Trigger | Function |
|---|---|---|
| BirdWeather offline render | `species_source == "birdweather"` | `shoot_birdweather(out, species, …)` → returns `Image.open(out)` |
| On-device capture of the station | `shoot == true` | `shoot(base_url, out, window_hours=cfg["hours"], …)` |
| Bundle without a renderer | bundle active and neither of the above | `ValueError("an active illustration bundle requires local or BirdWeather render mode")` |
| Pre-rendered source | `image_url` or `image` | `get_image()` (`frame/display.py:154`), with `?labels=` managed for URLs (`display.py:355`) |

Output paths: `~/.birdframe/frame.png` (birdweather) and `~/.birdframe/shot.png`
(local capture) — distinct files on purpose.

## The page ↔ capture handshake (`shoot.py`)

The frame does **not** scrape pixels blindly. It cooperates with `avian/frontend/apt.js`:

| Injected script | shoot.py line | Purpose |
|---|---|---|
| `HIDE_CSS` | `:57` | hides `.top`, `.slider`, menus, modals, `#v1`, `#v2`; freezes all animations/transitions; paints `--paper` background; `#collage img { visibility: hidden }` (artwork is composited later, not screenshotted) |
| `FRAME_READY` | `:66` | requires `#collage[data-frame-token]`, no `body.educator-data-loading`, `tiles.length === data-frame_count`, every `img.complete && naturalWidth > 0` (or one `.nest-img` when count is 0); returns `{token, revision}` |
| `FRAME_UNCHANGED` | `:77` | same identity re-checked before **and** after each strip |
| `CAPTURE_LAYOUT` | `:82` | per-`img` `src`/box/natural size/`object-fit`/`object-position`/`filter` + per-label box/font/color/opacity, with stable synthetic `id`s from a `WeakMap` |
| `FRAME_STABLE` | `:102` | requires the serialized layout to be byte-identical for ≥100 ms (deferred font/table retries fire at 60/80 ms) |

`window.__avianFrameCapture=true` is set by an init script (`shoot.py:~470`) and makes
the page behave differently: `apt.js` skips `DATA.recent` writes in `refreshAll`
(`apt.js:6030`), suppresses educator-scope realtime polling (`:6123`, `:6130`, `:6293`),
so the capture is deterministic.

`data-frame-token` is stamped by the page from the injected `frame_capture_id`
(`apt.js:3109-3112 finishFrameRender`), `data-frame-revision` increments on every
`renderCollage` call (`apt.js:~3120`). `shoot` requires
`str(observed["token"]) == ready["token"]` — Python's own counter must match the DOM's,
otherwise the render is stale and it retries.

Loop: **3 attempts max**, one shared `deadline` (`timeout_ms`, from `cfg["timeout"]`),
`remaining_ms()` raises past it. Retries happen only on *changed/invalidated*
snapshots (`_CaptureChanged`), never on asset/API failures — those abort immediately
(`observed["error"]`, `bundle_errors`). Do not add sleeps or widen the retry count.

## Artwork is composited, not screenshotted

`_composition_images` (`frame/shoot.py:172`) re-reads the **exact PNG/WebP response bodies**
Playwright observed for every `<img>` (missing/failed response ⇒ abort), enforces
`capture_art` budgets (`MAX_ASSET_BYTES` 16 MiB, `MAX_RETAINED_BYTES` 128 MiB,
`MAX_IMAGES` 512, `MAX_OUTPUT_PIXELS`/`MAX_ASSET_PIXELS` 8 M, `MAX_ASSET_EDGE` 8192),
and parses only two supported filter shapes (`drop-shadow(...)`).

`capture_text_overlay` (`shoot.py:127`) then screenshots only the **typography**:
transparent background, artwork hidden, in bounded horizontal strips
(`MAX_STRIP_PIXELS = 120_000`, row count rounded to a whole device-pixel unit so
Chromium cannot floor a fractional clip one row short), via CDP
`Emulation.setDeviceMetricsOverride`. Each strip re-verifies layout identity and
`check_snapshot()`. `capture_art.compose_capture` finally paints artwork + shadow +
the text overlay onto the paper colour read from `getComputedStyle(body)`.

Why: a full-page screenshot on a Zero 2 W produces torn/blank artwork; the strip +
response-body approach was added for exactly that
(`frame/README.md` "Slow, incomplete, or corrupt artwork… stay with the last good frame").

## Species-list render (`shoot.py:627 shoot_birdweather`)

Serves `avian/frontend/` from a localhost `SimpleHTTPRequestHandler`
(`_serve_frontend`, `:292`), feeds the species list through the same API handler
(`species=` set ⇒ `recent` fulfilled locally, everything else `{}`), routes cutouts to
`avian/assets/illustrations/` then 302s to raw GitHub
(`RAW_ILLUSTRATIONS`, `:52`). BirdWeather-specific look defaults:
`count_exp 1.0`, `headline_px 39`, `eyebrow_px 17`, `empty_text "no recent detections"`
(vs `"listening for birds…"` in mic mode).

## apt.js tunables the frame rewrites at request time

`_make_js_handler` (`frame/shoot.py:391`) substitutes inside the served `avian/frontend/apt.js` and
**fails the capture if any pattern stops matching**
(`"apt.js tunables not found (N); refusing to ship a half-tuned frame"`):

| Pattern | Replaced with | Config |
|---|---|---|
| `var xBias = narrow ? 1 : T.ellipseAspectBias;` | `var xBias = <v>;` | `cluster_xbias` (1.0) |
| `var yBias = narrow ? 1.7 : 1;` | `var yBias = <v>;` | `cluster_ybias` (1.2) |
| `countExp: [\d.]+,` | `countExp: <v>,` | `shoot_count_exp` (0.65 device / 0.4 lib / 1.0 birdweather) |
| `var pad = narrow ? Math.max(1, COLLAGE_PAD - 1) : COLLAGE_PAD;` | `var pad = <v>;` | `cluster_pad` (1) |
| `var LABEL_MIN_PX = \d+;` | `var LABEL_MIN_PX = <v>;` | `label_min_px` (11) |

The packer itself is `maskPack` (`apt.js:~2938`): grid-stamped silhouette masks
(mask-packing, not bounding boxes), spiral placement from centre with elliptical
bias, label sub-boxes reserved with a lighter dilation, deterministic PRNG so the
layout is stable across resizes, and off-screen (`-99999`) placement instead of
overlap when a bird cannot fit.

`?labels=1|0` overrides the `bird:labels` localStorage default
(`apt.js:1809`, default `'on'` at `:1812`); `shoot.py` rewrites the same param
(`_frame_url`, `:234`). Bird names on ⇒ the frame also self-serves
`avian/frontend/fonts/Caveat.ttf` and hard-fails if any tile lacks a
`.gtile-label text` (`shoot.py:~450-480`).

## Empty nest

`renderCollage` (`avian/frontend/apt.js:3121-3144`) renders
`<div class="empty-nest"><img class="nest-img" src="nest.webp"><p class="empty window-empty">…`
when the species list is empty; `EMPTY_WINDOW_COPY = 'no detections heard in this window'`
(`apt.js:101`). `FRAME_READY` accepts this state (count 0, one `.nest-img`).
**So an empty window is a perfectly valid, drawable frame** — the only thing
preventing a blank panel is the caller's species list. Directly relevant to
midnight-reset work: see [frame-refresh-decision.md](frame-refresh-decision.md).

> **2026-11-17:** because `FRAME_READY` accepts the empty nest, the `reset_at_midnight` path re-checks
> the **captured** list after the capture and declines an empty one (`frame/display.py:513-516` at HEAD;
> review R F1, confirmed end to end by K2). With the flag on, the page's window caption reads
> "since midnight" (`avian/frontend/apt.js:3609`, upstream). `frame/display.py` cites in this doc are at
> base `5950f807`; see the mapping in
> [frame-pipeline.md](frame-pipeline.md#line-numbers-after-w2-read-this-before-following-a-frame-cite).

## Layout inside the A5 opening (`display.py:233 mat_and_center`)

```
PANEL_W, PANEL_H = 1200, 1600            # portrait buffer (:35)
opening = 1:sqrt(2) rect, height = PANEL_H * cfg["opening"]   # 0.7071 == A5 (:179)
paper   = median of the 4 corners        # _paper, :170
mask    = |img - paper| > 34             # ink mask
split   = first ≥60 px empty row band below the top of content   # headline/eyebrow gap stays whole
TITLE_H_FRAC, COLLAGE_FRAC, GAP_FRAC = 0.065, 0.66, 0.1          # :230
title   scaled to box_h * 0.065 (fixed size, always)
collage scaled to min(box_w*0.66/w, (box_h - title_h - gap)/h)
collage centred by INK WEIGHT centroid (_centroid_x :219), not bbox; if the
          mirrored centroid width 2*half exceeds box_w, shrink the collage only
```

* No ink at all ⇒ returns the image untouched (`:242`); no usable split ⇒ whole-content
  `_place()` fallback (`:253`).
* `cfg["mat"]` shrinks content further inside the opening; `cfg["opening"]` is validated
  `0 < x <= 1`, bool rejected (`opening_size`).
* `--preview` maps to 6 approximate Spectra-6 inks with Floyd–Steinberg
  (`quantize_spectra6`, `:291`) — **approximation only**; on hardware Inky maps to the
  real palette.

## Panel push (`display.py:308`)

Lazy `inky` import (module stays importable without hardware). `panel == "el133uf1"`
forces `Inky(resolution=(1600,1200))`, else `inky.auto.auto()`. Image is rotated
`cfg["rotate"]` with `expand`, resized to the driver's true size if needed,
`set_image(buf, saturation=…)` only when that kwarg exists, then `show()`.
Invalid rotate prints a warning and falls back to 90.

Deps: `frame/requirements-frame.txt` (device: `Pillow>=10,<12`, `inky>=2.1,<3`,
`tomli` on <3.11) vs `frame/requirements-shoot.txt` (capture host:
`playwright==1.62.0`, `Pillow`). Capture needs Pillow **and** Playwright even for
standalone `frame/shoot.py` use (`frame/README.md`).
