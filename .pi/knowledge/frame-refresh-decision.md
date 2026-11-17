# Frame refresh decision logic

Everything about *whether* the panel gets a new image. If you are changing refresh
behaviour (midnight reset, quiet hours, cadence, blank-screen bugs), this is the
file to read first.

## The signature

```python
def slugify(sci):                    # display.py:80
    return re.sub(r"[^a-z0-9]+", "-", sci.lower()).strip("-")

def _bucket(n):                      # display.py:84
    for i, edge in enumerate((1, 2, 5, 15, 40, 100, 300, 1000)):
        if n <= edge: return i
    return 8

def signature(species, scope=""):    # display.py:103
    items = sorted((slugify(s["sci"]), _bucket(int(s.get("n") or 1))) for s in species)
    material = [scope, items] if scope else items
    return hashlib.sha256(json.dumps(material).encode()).hexdigest()[:16]
```

Properties that matter:

* **Species set + coarse count bracket only.** Ordering is sorted out; `com`, `best_conf`,
  `last_seen`, `top_file` are all ignored. A count moving 3 → 4 is invisible
  (both bucket 2); 2 → 5 is visible (bucket 1 → 2). This is intentional — e-ink
  should not flicker on every call.
* **`scope` disambiguates BirdWeather sources** so a station/ZIP/days change is a
  change even if the species list happens to match
  (`birdweather_signature_scope`, `frame/display.py:125`):
  `birdweather:station:<id>:days:<n>` or `birdweather:zip:<country>:<zip>:days:<n>`.
  Empty string for local mode → hash input is the bare `items` list (byte-compatible
  with older frames, deliberately preserved; see
  `tests/test_frame_birdweather.py::test_unscoped_signature_stays_compatible_with_existing_frames`).
* **Bundle revision is mixed in afterwards**, not inside `signature()`
  (`display.py:438-441` and `:459-463`):
  `sha256(sig + ":" + reference.get("selection_revision", reference["revision"]))[:16]`.
  So swapping illustration bundles redraws even with an identical species list.
* **`signature([])` = `4f53cda18c2baa0c`** (verified by running it). An empty list is
  a *real, distinct* signature, not a sentinel. **Nothing in this path treats "no
  species" as "no data."** Any feature that can produce an empty window will
  otherwise blank the panel into the empty-nest collage.
* Counts are `int(s.get("n") or 1)` — a `0`, `None`, or missing count collapses to
  bucket 0, same as 1.

## The gate

`frame/display.py:444-452`:

```python
heal_due = now - state.get("last_refresh", 0) >= cfg["heal_hours"] * 3600
changed  = (not use_signature) or (sig is not None and sig != state.get("signature"))
if not force and not preview:
    if in_quiet_hours(cfg, datetime.now().hour): print("quiet hours; skip"); return True
    if not changed and not heal_due:              print("no change; skip");    return True
    print("refresh:", "changed" if changed else "heal")
```

Truth table (no `--force`/`--preview`):

| condition | result |
|---|---|
| inside quiet hours | skip, regardless of change/heal |
| `sig == state.signature`, heal not due | skip |
| `sig == state.signature`, heal due | **refresh (heal)** |
| `sig != state.signature` | refresh (changed) |
| signature fetch raised (`sig is None`), heal not due | skip ("treat as no change") |
| signature fetch raised, heal due | **refresh (heal)** — with `sig` still `None` |
| `--no-signature` | always refresh |
| `--force` | always refresh (quiet hours bypassed too) |

`in_quiet_hours` (`display.py:348`) uses `datetime.now().hour` — the **frame Pi's**
local clock, whole hours, wrap-around supported (`s<=h<e`, else `h>=s or h<e`);
`s == e` means never quiet. Defaults `0/0` = always refresh, deliberately, so
nocturnal detections still show (`frame/config.example.toml` comment).

`heal_hours = 24` exists to re-burn the panel periodically (e-ink burn-in hygiene /
missed refreshes while offline), not for correctness of the data.

## State

```python
def load_state(path):   # display.py:329 — ANY exception ⇒ {"signature": None, "last_refresh": 0}
def save_state(path, sig, when):  # display.py:337 — tmp + flush + fsync + os.replace
```

`{"signature": "<16 hex>", "last_refresh": <unix epoch float>}`.
`last_refresh` is stamped **only on a successful panel push**, and `sig` is
re-stamped from the *captured* species when a capture happened
(`frame/display.py:457-463`) so the saved signature always describes what is physically on
the glass — see
`tests/test_frame_capture.py::test_saved_signature_describes_captured_data_not_earlier_fetch`.

On save, `sig if sig is not None else state.get("signature")` (`display.py:481`): a
heal refresh whose signature fetch failed keeps the **old** signature instead of
clearing it, so the next cycle does not immediately re-refresh.

## Failure rules (the frame is fail-static, not fail-open)

| Failure | Behaviour | Why |
|---|---|---|
| active bundle invalid | `run()` returns `False` before anything else; nothing redrawn | never render a half-verified pack |
| signature fetch raises | logged, `sig=None`, treated as no change | a station blip must not blank the wall |
| image acquisition raises | `"could not get image"`, `False`, state untouched | keeps last panel image; next cycle retries — `test_capture_failure_preserves_panel_state_and_next_cycle_retries` |
| capture integrity mismatch | `shoot()` raises after bounded retries; same as above | never burn a torn/blank collage |
| panel push raises | `False`, state untouched | next cycle sees `changed` again |
| another render holds the lock | prints `"another render is in progress; skipping"`, exit **0** | concurrent pushes on the 13.3" (two half-panel controllers) show a split image and can wedge a controller until a full power cycle (`frame/display.py:516-528`) |

Consequence: **there is currently no code path that deliberately draws a blank
panel.** The only blank is the legitimate empty-nest collage, which `avian/frontend/apt.js` draws only
when the species list is **empty** (`apt.js:3124`).

> **Corrected (Audit 2):** this used to say "zero *drawable* species". Wrong: a
> *non-empty* list whose species all lack masks does **not** draw an empty nest — every tile
> is dropped (`apt.js:3181-3190`), `finishFrameRender` is never called (`:3359`),
> `FRAME_READY` never fires, and the capture times out → `"could not get image"` → exit 1,
> panel retained. Same for a tile left unplaced after the shrink passes. See [D12](open-decisions.md#d12--what-does-nothing-to-draw-mean-for-the-d1-decline).

## Edit surface for "reset at midnight"

> **Historical (v0.1-era). Superseded** by the decided design in
> [feature-midnight-reset.md](feature-midnight-reset.md) and the register in
> [open-decisions.md](open-decisions.md): the guard is no longer "at `:445`/`:446`" but a
> pre-capture decision on every forced path ([D1](open-decisions.md#d1--may-a-forced-render-draw-an-empty-today-window-collage)), keyed on drawable species ([D12](open-decisions.md#d12--what-does-nothing-to-draw-mean-for-the-d1-decline)), with
> no new state keys ([D9](open-decisions.md#non-blocking--decided-by-the-parent-from-house-style-to-be-proposed-in-the-pr)) and the served-list render path ([D17](open-decisions.md#d17--the-local-mode-served-list-variant)). Kept for the reasoning.

Requirement recap (from [`.pi/reset-after-midnight Plan v0.1.md`](../reset-after-midnight%20Plan%20v0.1.md)): after midnight,
show only today's birds, but **never** refresh/clear the panel merely because the
day rolled over; the first detection of the new day replaces yesterday's collage.

Minimal, in-order surface:

1. `frame/display.py:42 DEFAULTS` — add `"reset_at_midnight": False`.
   `load_config` is a plain `DEFAULTS ⊕ toml` merge, so no other plumbing is needed.
2. `frame/display.py:91 fetch_recent()` — the only place the recent URL is built
   (`?action=recent&hours={hours}`). A request-level window param goes here.
3. `frame/display.py:132 fetch_species()` — same list feeds signature *and* render;
   keep them identical or the panel and state will disagree.
4. `frame/display.py:366 obtain_image()` → `shoot(..., window_hours=cfg["hours"])` —
   `shoot.py:243 _make_api_handler` rewrites `hours=\d+` in the intercepted page
   request. A param that is not `hours` passes through untouched, but if you widen
   the window representation you must keep both sides in sync.
5. **The empty-window guard is the crux** — `frame/display.py:445` (`changed`) or the gate at
   `:446`. When `reset_at_midnight` is on and today's window yields zero species,
   do not treat that as a change; keep the previous signature and skip. This also
   covers the heal path (`heal_due` + `changed` would otherwise redraw an empty
   nest once a day) and the restart path (`load_state` failure → `signature: None`
   → `sig != None` is a change → blank panel on reboot before the first detection).
   Note requirement 7 explicitly forbids refreshing "solely because the date or
   detection window changed".
6. `frame/config.example.toml` (+ `frame/README.md`) — document the key near
   `hours = 24`.
7. `frame/config_contract.py` — only if the key should participate in mode
   verification (it probably should **not**: it is orthogonal to local/image/
   birdweather, and `verify()` compares an allow-list of source selectors).
8. Tests: `tests/test_frame_capture.py` (display mocked at module level — see
   [testing-and-ci.md](testing-and-ci.md#test-mocking-conventions)) and
   `tests/test_frame_birdweather.py`; station-side window semantics belong in
   `tests/test_midnight_reset.php`.

Timezone trap: the station computes midnight from its own SQLite `localtime`
(`avian/api/birdnet-api.php:300-306` + `dateContext`), the frame's gate uses the
frame Pi's clock, and `hours` is a *rolling* window. Prefer letting the **station**
decide the boundary and reading it back from the response (`midnight_clamped`,
`window_start`, `anchor`, `is_today`) over computing midnight on the frame.
