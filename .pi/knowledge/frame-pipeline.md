# Frame pipeline (end to end)

The frame is a **poll-and-redraw client**, not a daemon. One short-lived Python
process per refresh, launched by systemd.

## Schedule

`frame/install.sh` generates the installed units (`frame/install.sh:576-612`); the
in-repo copies `frame/systemd/birdframe.{service,timer}` are the reference.

```
birdframe.timer   OnActiveSec=2min  OnBootSec=2min  OnUnitActiveSec=15min  Persistent=true
birdframe.service Type=oneshot, User=<installer user>, Nice=10, NoNewPrivileges=true,
                  TimeoutStartSec=300, EnvironmentFile=-/etc/avian-birdframe/environment
                  ExecStart=<frame>/.venv/bin/python <frame>/display.py --config ~/.birdframe/config.toml
```

Notes:
* `Persistent=true` is **inert** here: systemd only applies it to `OnCalendar=` timers, and this
  unit has none. The boot-after-outage render comes from `OnBootSec=2min`. The timer's own
  bootstrap deadline comment
  (`frame/systemd/birdframe.timer:4-9`) — a stopped/unloaded pair can otherwise
  end up with no next deadline, hence `OnActiveSec` **and** `OnBootSec`.
* `TimeoutStartSec=300` vs `timeout = 180` config default: a Zero 2 W needs
  ~70–120 s to render the collage in headless Chromium. Raising one without the
  other breaks the frame.
* `install.sh --now` enables the timer immediately, not only at boot
  (`frame/install.sh:758`).
* `birdframe-names on|off` rewrites config then runs `display.py --force`
  (`frame/birdframe-names:63-68`) — that's the pattern for "change a setting and
  redraw now".

## One run, step by step (`frame/display.py:418 run()`)

```
main()                                    display.py:494
 ├─ load_config(path)                     display.py:486   DEFAULTS ⊕ config.toml
 │    CLI overrides only base_url / image / image_url / rotate / force / preview
 └─ flock ~/.birdframe/.render.lock       display.py:520-528   LOCK_NB → "another render
                                                                is in progress; skipping", rc 0
run(cfg, preview, force, use_signature, mat_box)
 ├─ active_bundle(cfg["bundle_root"])     display.py:424-425   (bundle_runtime)
 │    raises ⇒ print "active bundle validation failed" and return False — NO redraw
 ├─ if use_signature:
 │    species = fetch_species(cfg, auth, drawable=bundle.drawable_slugs)   :132
 │    sig = signature(species, scope)                                       :103
 │    scope = birdweather_signature_scope(cfg) when birdweather else ""      :125
 │    sig = sha256(sig + ":" + bundle selection_revision) if a bundle is active :438-441
 │    any exception ⇒ print "signature fetch failed", sig stays None  (== "no change")
 ├─ heal_due = now - state.last_refresh >= heal_hours*3600                   :444
 ├─ changed = not use_signature or (sig and sig != state.signature)          :445
 ├─ GATE (skipped entirely when force or preview):                           :446-452
 │    in_quiet_hours(now.hour) → "quiet hours; skip", True
 │    not changed and not heal_due → "no change; skip", True
 │    else print "refresh: changed|heal"
 ├─ img = fit_panel(obtain_image(cfg, species, bundle, capture={}))          :366 / :170
 │    species is None (only with --no-signature) ⇒ obtain_image re-fetches it  :377-382
 │    capture["species"] is the list the browser was actually served          :457-461
 │    ⇒ sig is RECOMPUTED from captured data (so state never claims a signature
 │      the panel isn't showing)
 │    exception ⇒ "could not get image", return False, state NOT written
 ├─ img = mat_and_center(img, cfg["mat"], cfg["opening"])                     :233
 ├─ if --preview: quantize_spectra6 → optional _draw_mat_box → save PNG, return True
 │    (a preview run never touches the panel and never saves state)
 ├─ push_panel(img, rotate, saturation, panel)                                :308
 │    exception ⇒ "panel push failed", return False, state NOT written
 └─ save_state(cfg["state"], sig if sig is not None else state.signature, now) :337
```

Exit code: `0` on success **and** on "skipped", `1` on failure (`frame/display.py:529-536`).
So a non-zero exit means a real fault, and a zero exit does **not** mean a redraw.

## Three sources, one renderer

| Mode | Config | Species come from | Image comes from |
|---|---|---|---|
| `local` (default) | `base_url`, `shoot = true` | `GET {base}/avian/api/birdnet-api.php?action=recent&hours=N` (`frame/display.py:91`) | `frame/shoot.py` screenshots the station site (`display.py:391-401`) |
| `birdweather` | `species_source = "birdweather"` + `zip` **or** `bw_station_id` | `frame/birdweather.py` (GraphQL → radius → triangulate → eBird) | `shoot.py shoot_birdweather()` renders the bundled frontend on `127.0.0.1` (`display.py:377-390`, `shoot.py:627`) |
| `image` | `shoot = false` + `image_url` or `image` | none — no signature fetch when `species_source` is not birdweather, so `fetch_species` still hits `recent` for the signature | fetch/serve the PNG (`display.py:402-415`) |

Gotchas:
* In `image` mode the frame **still queries `action=recent`** on `base_url` to
  build the signature, then separately GETs the image URL. `base_url` is set to the
  URL origin by the installer (`frame/install.sh:723`).
* An active illustration bundle requires local or birdweather render: `image` mode
  with a bundle raises `ValueError` (`display.py:402-405`).
* For a remote `image_url` the frame appends `labels=1|0`
  (`display.py:355 frame_url`, mirrored in `shoot.py:234`) — a source that ignores
  the param simply keeps sending what it always sent.
* `obtained image` is always resized to 1200×1600 **portrait** (`fit_panel`),
  while the physical panel is 1600×1200 landscape; `push_panel` rotates by
  `cfg["rotate"]` (90/270) and resizes to the driver's real size
  (`display.py:308-327`).

## Auth & networking

* Optional HTTP basic auth for a whole-site-protected station: `basic_user` /
  `basic_pass` → `_auth()` builds the header (`frame/display.py:72-77`); it is applied to
  both the API fetch and the image fetch, and passed into `shoot()` so Playwright
  uses `http_credentials` plus an `authorization` header on intercepted fetches.
* Every outbound request sends `User-Agent: AvianVisitors-frame/1.0` and a bounded
  read (`r.read(2_000_000)` for JSON, `20_000_000` for images).
* BirdWeather/eBird lookups are separate, keyless-by-default paths
  ([birdweather-source.md](birdweather-source.md)).

## Device-side files

| Path | Written by | Notes |
|---|---|---|
| `~/.birdframe/config.toml` | `frame/install.sh` (never overwritten on rerun) | mode marker comment `# birdframe-mode: <mode>` on line 1 |
| `~/.birdframe/state.json` | `save_state()` | `{"signature": ..., "last_refresh": <epoch>}`; atomic tmp+`fsync`+`os.replace` |
| `~/.birdframe/.render.lock` | `main()` | flock, dropped on exit |
| `~/.birdframe/frame.png` / `shot.png` | `frame/shoot.py` | last capture; atomic replace preserving owner/mode |
| `~/.birdframe/geocode.json` | `birdweather.geocode()` | ZIP→coords never move, cached forever |
| `~/.birdframe/bundles/` | `bundle_runtime` | verified bundles + selection state |
| `~/.birdframe/ebird-api-key` | installer | 0600, single-link, ≤4096 B, `[A-Za-z0-9]` only (`frame/birdweather.py:276-306`) |
| `/etc/avian-birdframe/environment` | installer | `EBIRD_API_KEY=...`, root-owned 0600, loaded by the service |

## Manual operation on a frame Pi

```bash
# force a redraw now (the canonical "update both mic and frame" step)
cd ~/AvianVisitors/frame && git pull --ff-only && \
  .venv/bin/python display.py --config ~/.birdframe/config.toml --force

# check the look without hardware (6-ink dither preview, optional mat outline)
.venv/bin/python display.py --config ~/.birdframe/config.toml \
  --preview /tmp/look.png --mat-box

# skip change detection entirely (also re-fetches species inside obtain_image)
.venv/bin/python display.py --config ~/.birdframe/config.toml --no-signature --force

birdframe-names status|on|off
sudo avian-bundle use '<BUNDLE_ID>'
```

`--preview` deliberately bypasses the refresh gate **and** never saves state, so
previewing cannot desync the panel from `state.json`
(`frame/display.py:446` gate condition `not force and not preview`; `:466-471` early return).

## Where this doc's claims came from

`frame/display.py` (full read), `frame/shoot.py` (full read),
`frame/README.md`, `frame/install.sh`, `frame/systemd/*`, `frame/birdframe-names`.
Related: [frame-refresh-decision.md](frame-refresh-decision.md),
[frame-render-capture.md](frame-render-capture.md).
