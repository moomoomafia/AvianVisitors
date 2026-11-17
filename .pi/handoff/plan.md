# Worker handoff plan — BirdFrame midnight reset (Plan v0.3)

Transcribed **verbatim** from `.pi/reset-after-midnight Plan v0.3.md` and
`.pi/knowledge/open-decisions.md` on 2026-11-17 (gate G0 lifted). Never use the edit-surface
table in `.pi/knowledge/feature-midnight-reset.md` (superseded where it conflicts; Plan v0.3 +
`open-decisions.md` + `.pi/knowledge/minimal-footprint.md` win). If a ruling below proves
unimplementable, stop and report — do not deviate.

## Authorisation (G0, 2026-11-17)

Operator: *"Execute Gate G0 … then (5) dispatch W1 only (§4.1, the three-line station-API
change) as a single fresh `worker` child in this session."* Scope: W1–W3. **Stages V and H, §8
deployment, any push or PR remain unauthorised.** D21 stays `OPEN` (deferred to stage V).
This session dispatches **W1 only**.

## Open numbered questions (unanswered by the operator — do not decide them)

1. **§5 conditional row, `tests/test_midnight_reset.php` (owned by W1).** Attempt upstream's
   `edu_endpoint` pattern (`tests/test_educator_backend.php:64-76`) to run the full `recent`
   endpoint with `reset_at_midnight=1` cheaply. If it works cheaply, the plan allows one case
   there; **otherwise record the gap** (brief scenario 11 — other API clients unchanged — then
   rests on R1's argument and the `.pi/` R3 scripts). W1's station diff must stay exactly 3
   lines regardless; this question must not inflate it. Report which way it went to the parent;
   the operator rules on adding the test.

## Hard boundary (§4.6 "Not changed", verbatim) — applies to every child

### 4.6 Not changed

`install.sh`, `config_contract.py`, `birdframe-names`, systemd units, `apt.js`, the station's global
setting, any workflow file, `ActiveBundle.drawable_slugs`, signature hashing (D6 dropped),
`state.json` format (D9).

Frame code never writes station config (D3/D10). No §4.2–§4.5 or §5 frame work in W1.

## Plan v0.3 §3–§5 (verbatim)

## 3. Requirements → rulings (all decided; no open blockers)

| # | Requirement (v0.2 brief) | How it is met | Ruling |
|---|---|---|---|
| 1 | Today = station's calendar day from 00:00 | station clamps `recentWindow` with `hours=24` → `[midnight, now]` | D13, R3 (executed 30/30) |
| 2 | Show only today's species | the window above drives both the signature and the capture | D3, D17→superseded |
| 3 | Midnight resets logically, no redraw | decline when today has no **drawable** bird (exit 0, no capture, no `save_state`) | D1, D12 (+R5 amendment) |
| 4–5 | Keep the previous collage while today is empty, for any number of days | same decline; data-keyed, independent of `last_refresh` | D1, D7, D9 |
| 6 | First drawable detection replaces the collage | clamped species list → signature changes → normal refresh | D12a |
| 7 | Continue refreshing normally | unchanged signature/bucket logic | — |
| 8 | Never mix days | station-side clamp only; never capture without an honoured list | D16, R1 |
| 9 | Never overwrite with a blank screen because the window is empty | decline on **every** path: timer, heal, `--force`, `--no-signature`, `avian-bundle use/rollback`, `birdframe-names` | D1 |
| 10 | Heal cannot clear the collage | the decline runs before the gate | D7 |
| 11 | Survive restarts | decline is data-keyed; corrupt/missing state can't trigger a redraw | D9 |
| 12 | Off ⇒ unchanged | every new branch is behind the flag; no new param/hash/state otherwise | D3 condition |
| Iso | Station display, global `RESET_AT_MIDNIGHT`, history untouched | request-scoped param; frame never writes station config; read-only DB | D3, D10 |

Supporting rulings: **D2** local mode only (`species_source != "birdweather" and shoot is True`);
**D3** additive request param + config toggle `reset_at_midnight`, default `false`; **D4** CI = the
parent's existing jobs, no new workflow, hardware pass mandatory; **D11c** `.pi/` + `AGENTS.md`
are on this branch and must be stripped before any PR to the parent; **D14** outdated station ⇒
hold + exit 1; **D15** Educators scope ⇒ hold (falls into the D14 path); **D16** station
unreachable ⇒ timer skips (exit 0), forced run exits 1; **D20** minimal footprint.

## 4. Design

### 4.1 Station — `avian/api/birdnet-api.php` (R1 variant B′, +1 / 2 modified)

```php
// new line in the request-derived block, after $action (:135)
$resetAtMidnight = $RESET_AT_MIDNIGHT || (($_GET['reset_at_midnight'] ?? null) === '1');
// :169   (($educatorCacheDisabled || $resetAtMidnight) ? 'no-store' : 'public, max-age=30')
// :362   recentWindow($db, $hours, $ctx, $resetAtMidnight, $educatorScope !== null)
```

Facts this relies on (executed, R3): only exact `1` enables it; arrays, `0`, case variants are
ignored; PHP key mangling (`reset.at.midnight`) and last-wins duplicates behave as for every
upstream param; a request can never switch a station-wide ON off; educator scopes still win
(`:90`). Requests without the param are byte-identical to today. With the param, `no-store` applies
to whatever action carries it (parity with the global flag); the response field
`reset_at_midnight` then means "station flag OR param, not scoped" (no in-repo reader).

### 4.2 Frame — `frame/display.py`

1. `DEFAULTS["reset_at_midnight"] = False` (`:42-70`).
2. **One shared fetch.** Extract the body of `fetch_recent` (`:91-101`) into
   `fetch_recent_payload(base, hours, timeout, auth=None, reset_at_midnight=False)` returning the
   validated dict (same URL, same `read(2_000_000)`, same "no species list" `ValueError`), appending
   `&reset_at_midnight=1` only when asked. `fetch_recent` becomes a one-line wrapper returning
   `payload["species"]` — **identical behaviour**, pinned by the parent's
   `test_signature_fetch_rejects_missing_species_not_as_empty` and characterization C7. (Chosen over
   a duplicate helper to avoid copying upstream's URL/validation logic; D20. This deliberately
   departs from the superseded D17 bullet "add a flag-only helper rather than changing
   `fetch_recent`" — the parent's tests pin the wrapper's behaviour, copying the validation would
   be worse.)
3. **Activation** — `active = cfg.get("reset_at_midnight") is True and
   cfg.get("species_source") != "birdweather" and cfg.get("shoot") is True` (D2 amended). If the
   flag is set but not `active`, print one line ("reset_at_midnight applies only to local mode;
   ignored") and continue exactly as today.
4. **In `run()` (`:418`), when `active`, before the existing signature block:**

   | Step | Condition | Action | Exit |
   |---|---|---|---|
   | a | always (timer, heal, `--force`, `--no-signature`, preview) | `payload = fetch_recent_payload(base_url, 24, timeout, auth, reset_at_midnight=True)` | — |
   | b | fetch raised | timer run (`not force and use_signature`): print, **return True**; forced: print, **return False** | 0 / 1 |
   | c | `payload.get("midnight_clamped") is not True` | print "station did not apply the midnight window — update the station (Tools → Pull latest), or an Educators capture is active"; **return False** (preview: warn, continue) | 1 |
   | d | no species in `payload["species"]` is drawable (§4.4); with `bundle is None`, every species counts as drawable, so only an **empty** list declines | print "no drawable bird since midnight; keeping the current collage"; **return True** — no capture, no `push_panel`, no `save_state` (preview: continue and render) | 0 |
   | e | otherwise | `species = payload["species"]`. **The existing `if use_signature:` block (`frame/display.py:429-443`) is skipped**: if `use_signature`, set `sig = signature(species, "")` and apply the bundle salt exactly as at `:438-441`; `fetch_species` is **not** called — **exactly one station fetch per run**, and `changed` is decided on the clamped list. `--no-signature` keeps `changed = True` (`:445`). Then the **unchanged** gate: heal, quiet hours, capture, push, save. | as today |

   The steps sit in one `if active:` block; no restructuring of `run()` (it is already complexity 18
   upstream and the limit is not enforced on the parent's branch). The render lock is already held:
   `main()` takes it before calling `run()` (`frame/display.py:520-528`). Step (c) runs before (d) so
   an outdated station can never hide behind an exit-0 decline.
5. `obtain_image` (`:366`) passes `window_hours=24 if active else cfg["hours"]` and
   `reset_at_midnight=active` to `shoot()` (`:395-400`). The birdweather and image branches are
   untouched.

### 4.3 Frame — `frame/shoot.py`

`_make_api_handler(..., reset_at_midnight=False)` (`:243`): in the station branch after the existing
`hours` substitution (`:258`), append `reset_at_midnight=1` when asked and not already present.
`shoot(..., reset_at_midnight=False)` (`:412`) threads it to the route at `:448`. This is the
**single** injection point for every page `recent` request (verified, pre-v0.3 item 5); every other
query parameter is preserved verbatim (characterization C8). Upstream's re-sign from the captured
response (`frame/display.py:457-463`) keeps state truthful if the window changes between the fetch
and the capture.

### 4.4 "Drawable" (D12 + R5 amendment)

* **Frame bundle active** (the operator's setup, D12b): a species is drawable iff the bundle has a
  base pose for it — `"perched"` or `"variant-1"` in `bundle.index["assets"].get(slugify(sci), {})`.
  Equivalent to "its unsuffixed slug is a masks key" (install invariant,
  `frame/bundle_runtime.py:1883-1889`), i.e. exactly the collage's drop test
  (`avian/frontend/apt.js:3164-3186`). **Do not change `ActiveBundle.drawable_slugs`** (species-level;
  upstream BirdWeather filtering depends on it).
* **No frame bundle:** per the **D12 amendment of 2026-11-16** (parent-decided after the Oracle
  review; basis D20 and D12b) the frame does **not** fetch the station's mask table —
  `avian/frontend/masks.json` is ~800 KB, too heavy every 15 min on a Zero 2 W, and the operator's
  frame has its own bundle — so only an **empty** today-window declines. The residual risk (a
  station-default flight-only species) is fail-static: panel kept, capture times out, exit 1.

### 4.5 Config and docs

* `frame/config.example.toml`: add after `hours = 24` (`:26`):
  `# reset_at_midnight = false  # local mode only: show birds since the station's midnight; keeps the`
  `#                             # last collage until today's first drawable bird; needs an updated station`
* `frame/README.md`: one short paragraph after the bird-names section (`:87`): what it does, local
  mode only, `hours` is ignored while on, update the station first, `--force` will not repaint an
  empty day, set back to `false` to restore today's behaviour (no state reset needed). End-user
  voice, no internals. Also say: with an outdated station the frame keeps its collage and reports a
  failure every 15 minutes (including during quiet hours) until the station is updated (D14).

### 4.6 Not changed

`install.sh`, `config_contract.py`, `birdframe-names`, systemd units, `apt.js`, the station's global
setting, any workflow file, `ActiveBundle.drawable_slugs`, signature hashing (D6 dropped),
`state.json` format (D9).

## 5. Tests (in the parent's existing files, in their style)

| File | Add | Proves |
|---|---|---|
| `tests/test_frame_capture.py` | flag-on twins of characterization C1–C5: empty window ⇒ no capture/push/save, `run()` True; `--force` and `--no-signature` empty ⇒ same; heal-due empty ⇒ same; unreadable state + empty ⇒ same | req 3, 4, 5, 9, 10, 11 |
| ″ | flight-only-only today (bundle stand-in with `{"ardea-herodias": {"flight": …}}`) ⇒ decline; mixed list ⇒ draws | req 3, R5 |
| ″ | unclamped payload ⇒ `run()` False, no push (D14); fetch error ⇒ timer True / forced False, no push (D16) | D14, D16 |
| ″ | flag on, first drawable bird ⇒ capture receives the clamped list; signature from it; push + save | req 6, 7 |
| ″ | flag **off**: every C1–C8 case behaves exactly as characterized | req 12 |
| ″ | flag on in birdweather / image mode ⇒ one log line, behaviour identical to off | D2 |
| ″ | `_make_api_handler(..., reset_at_midnight=True)` appends the param once, sets `hours=24`, keeps other params | D3, C8 |
| ″ | `fetch_recent` unchanged; `fetch_recent_payload(..., reset_at_midnight=True)` URL ends `&reset_at_midnight=1` | C7 |
| ″ | flag on: **exactly one** `fetch_recent_payload` call per run and `fetch_species` **not** called | Oracle High |
| ″ | divergence fixture: clamped list differs from the rolling list ⇒ `changed` and the capture both use the clamped list | req 2, 6, 8 |
| ″ | first drawable bird during quiet hours ⇒ skip, no push; the next run outside quiet hours draws | D8 |
| ″ | `--preview` of an empty day ⇒ renders the preview file, never `push_panel`/`save_state` | D1 |
| ″ | flag on, `force=True, use_signature=False` (bundle `use`/`rollback`) with an empty day ⇒ `run()` returns True (bundle kept) | D1 |
| ″ | the flag-on URL and decision do not depend on the frame's clock (patch `time.time`/`datetime` far from the station's day) | brief scenario 9 |

Worker note: flag-on tests must patch `fetch_recent_payload`, not `fetch_species`.
| `tests/test_midnight_reset.php` | none required: the param read is after the library-only guard and the clamp it relies on is already pinned (`:33-36`). If the worker shows upstream's `edu_endpoint` pattern (`tests/test_educator_backend.php:64-76`) runs the full `recent` endpoint with the param cheaply, add one case there; **otherwise W1 must record the gap** (brief scenario 11 — other API clients unchanged — then rests on R1's argument and the `.pi/` R3 scripts). | req 1, 8, brief 11 |

Our own scaffolding stays in `.pi/`: the characterization suite
(`.pi/research/pre-v03/test_characterize_today.py`, 13/13 today) is re-run after the change to show
the intended flips with the flag on and no change with it off; the R3 scripts re-verify the PHP.

## Plan v0.3 §7 Execution (verbatim)

## 7. Execution (one child at a time; no recursive delegation)

Available agents: `scout`, `oracle`, `worker`, `reviewer` (no `tester`). Each `worker` starts
blank: hand it this plan, the relevant knowledge docs and an exact task. Commits are **local**;
nothing is pushed without the operator's say-so.

| Step | Agent | Task | Done when |
|---|---|---|---|
| G0 | operator | authorise building | explicit go-ahead |
| W1 | worker | §4.1 station change | diff = 3 lines in `avian/api/birdnet-api.php`; parent PHP tests + R3 scripts pass |
| W2 | worker | §4.2–4.4 frame change + §5 frame tests | §5 tests pass locally (stub loop); characterization flips as expected |
| W3 | worker | §4.5 docs | README paragraph + config line, end-user voice |
| R | reviewer | review the full diff vs this plan, D20 and every ruling | no unresolved High findings |
| V | parent | §6 local runs; push only if the operator authorises CI on the fork | results recorded in the verification log |
| O | oracle | drift/ruling audit of the result | verdict recorded |
| H | operator + parent | hardware pass on `birdpic` | checklist recorded |

The parent records each step in `.pi/knowledge/verification-log.md`, keeps the register current, and
runs `python .pi/tools/check_kb.py --index` (exit 0) at the end of each session.

## Recorded deviations (Plan v0.3 §9, verbatim)

* **Recorded deviations:** D12 amended for the no-bundle path (§4.4); §4.2 item 2 departs from the
  superseded D17 "flag-only helper" bullet.

## Rulings (verbatim from `.pi/knowledge/open-decisions.md`)

### D1 — May a forced render draw an empty today-window collage?

**Status:** `ANSWERED 2026-11-16`

> **Ruling:** **Decline on all forced paths.** Retention is a property of the *data*, not
> of the trigger. Every forced path declines, **exits 0**, and logs a line. `--preview`
> still renders for inspection.

Consequences the implementation must honour:

* The guard runs **before** capture, so a doomed refresh never burns a 70–120 s Chromium
  render on a Zero 2 W.
* Covers `--force`, `--no-signature`, `avian-bundle use` (when the selection changed),
  `avian-bundle rollback` (unconditional), and `birdframe-names on|off`.
* Exit **0** is not cosmetic: a non-zero exit makes `use`/`rollback` revert the bundle
  selection and re-render (`frame/bundle_runtime.py:1962-1972`).
* Logs must be greppable and calm — one line, not a stack trace, because this fires on
  every poll during a silent stretch.
* Requirement 12 (disabled ⇒ unchanged) is separate: with `reset_at_midnight = false` this
  guard must not exist at all, not merely be false.

Original options retained below for the record.

The brief says never overwrite the retained collage with a blank screen (req 9) and
that heal must not clear it (req 10). It does not say what an *explicit* render should
do, and there are four forced paths plus a fifth that nobody asked for:

| Path | Source |
|---|---|
| `display.py --force` (documented in `frame/README.md` as the standard post-`git pull` step) | `frame/display.py:446` |
| `--no-signature` (forces `changed = True`) | `display.py:445` |
| `avian-bundle use` when the selection changed | `bundle_runtime.py:1953-1955,1962-1963` |
| `avian-bundle rollback` — renders unconditionally | `bundle_runtime.py:1993-1997` |
| `birdframe-names on\|off` | `frame/birdframe-names:63-68` |

Options:
1. **Decline on every forced path** (recommended): the retention rule is a property of
   the *data*, not of the trigger. Exit **0** — a non-zero exit makes `use`/`rollback`
   revert the bundle selection and re-render (`bundle_runtime.py:1962-1972`), silently
   undoing the user's request.
2. Honour `--force` literally: an explicit `--force` draws whatever the window holds,
   including the empty nest; the automatic paths (bundle, names) still decline.
3. Only the gate declines; all forced paths draw (this is the naive reading of the
   brief and it wipes walls).

Consequence if unanswered: a Worker implements the gate only, which satisfies the letter
of req 9 for timer runs and blanks the panel on every `git pull` + `--force` update.
`--preview` is deliberately outside this decision — it cannot touch the panel
(`display.py:469-474`) and must keep rendering for inspection.

### D2 — Which frame modes does the feature apply to?

**Status:** `ANSWERED 2026-11-16`

> **Ruling:** **`local` mode only.** `birdweather` and `image` modes are documented as
> unsupported, mirroring the existing bundle caveat at `frame/display.py:402-405`.

What that means concretely:

* The clamp param and the retention guard activate **only** when
  `species_source` is empty (station-backed `local` mode).

  > **Amended 2026-11-16 (Audit 2, F-M1):** the test above is wrong — `image`/`image_url`
  > frames *also* have an empty `species_source` (`display.py:44,406-416`). The correct
  > activation test is **`cfg.get("species_source") != "birdweather" and cfg.get("shoot") is True`**,
  > the same predicate the codebase already uses to mean "this Pi renders the station"
  > (`frame/bundle_runtime.py:433,474`; `frame/config_contract.py:75`). The ruling itself (local only)
  > is unchanged.
* `birdweather` mode keeps `bw_days` semantics untouched — no BirdWeather parameter is
  changed, and its radius/triangulate/eBird fallback chain is out of scope.
* `image` / `image_url` modes keep fetching `recent` for the signature exactly as today;
  they do **not** send the param. Document that such a frame shows whatever its source
  rendered — same wording pattern the README already uses for bundles and for `labels=`.
* Worth a test: `reset_at_midnight = true` with `species_source = "birdweather"` must be a
  no-op (or a startup warning), not a silent partial effect. Decide which in the PR;
  a logged warning fits the house style better than silence.

Original options retained below for the record.

The brief is written entirely in terms of the BirdNET station window, but the frame has
three sources.

| Mode | Today-only meaningful? | Note |
|---|---|---|
| `local` | Yes | the whole brief |
| `birdweather` (`zip` / `bw_station_id`, `bw_days = 7`) | Different data source | "midnight" would have to be redefined against BirdWeather; its radius-growth / triangulate / eBird fallback chain would need to change too |
| `image_url` / `image` | No | pixels come from someone else's render; the frame still calls `fetch_recent(base_url)` for the signature (`display.py:430-443`) but cannot control what produced the image |

Options: **(A) `local` only**, other modes documented as unsupported — mirrors the
existing precedent at `display.py:402-405` ("an active illustration bundle requires
local or BirdWeather render mode"). (B) `local` + `birdweather` with a redefined window.
(C) All modes.

Recommendation: **(A)**. Consequence if unanswered: a mode-blind Task A can "make it
work" by mutating BirdWeather parameters — an unrequested behaviour change in a service
the brief never mentions.

### D3 — Station API: additive request param, name and shape?

**Status:** `ANSWERED 2026-11-16`

> **Ruling:** **Additive param + the frame serves its own list to the browser.**
> Operator condition attached, quoted: *"As long as in the config.toml file the user is
> able to define if this feature is turned on or off. As not all users will want this
> behavior."*

That condition is a hard requirement, not a preference — record it in every handoff:

* **`reset_at_midnight` lives in `~/.birdframe/config.toml`, defaults to `false`.** The
  station's own `RESET_AT_MIDNIGHT` stays untouched, so the feature is per-frame: two
  frames on one station can disagree, which is exactly what the request-scoped design
  allows (`recentWindow` already takes the flag per call).
* Default off ⇒ existing installs are bit-identical after an update: no new param on the
  wire, no new hash material, no new guard. This is requirement 12 satisfied by default.
* Must be documented in `frame/config.example.toml` next to `hours = 24` and in
  `frame/README.md` in end-user prose — including that it needs an updated station, and
  that flipping it back to `false` needs no `state.json` reset.
* Consider whether it deserves a companion CLI like `birdframe-names` (edit config →
  `display.py --force`). **Rejected here**: under D1 a forced render during an empty
  today-window declines, so such a command would silently not repaint. Document the
  config edit instead, and note this interaction so nobody "fixes" it later.

Mechanics (unchanged from the recommendation):

* Strict scalar param; absent ≠ false ≠ true; ignore PHP-folded aliases
  (`educator_scope_raw_parameter_count`, `avian/api/educator-scope.php:28-48`).
* `case 'recent'` only; `$scoped` still ignores display preferences; `hours >= 1000000`
  and historical `?date=` preserved; clamped response `no-store`; requests without the
  param keep today's `public, max-age=30`.
* Window form: `Date = :station_date AND DATETIME(Date||' '||Time) <= :anchor`.
* The frame serves its own fetched list to the browser (the `birdweather`-proven pattern,
  `frame/shoot.py:243-257`), which makes signature/pixel agreement structural rather than a
  two-place param injection. Note this removes no user control: the frame already rewrites
  `hours=` in the intercepted request (`shoot.py:259`), so the site's window picker has
  never driven the collage.

> **Amended 2026-11-16 (Audit 2).** The ruling stands; four mechanics bullets above were
> wrong or underspecified:
>
> 1. **Param values (F-M6):** not tri-state. Only the exact scalar `1` has an effect;
>    anything else (absent, `0`, arrays, folded aliases) is treated as absent.
>    *Amended by D20/R1 (2026-11-16):* "folded aliases … treated as absent" is **dropped**.
>    Upstream's idiom `($_GET['x'] ?? null) === '1'` rejects absent, `0`, other strings and
>    arrays, but honours PHP key mangling (`reset.at.midnight=1`) and last-wins duplicates,
>    exactly like every other upstream param. Harmless: the param only selects a read-only
>    display window and any client can send the canonical name. See the R1 brief, E8. A `=0` must
>    never be able to override the station's global flag — no requirement asks for that.
> 2. **Caching:** "requests without the param keep `public, max-age=30`" is wrong — the
>    global flag and Educators mode already force `no-store` (`avian/api/birdnet-api.php:165-171`).
>    Correct wording: *requests without the param get exactly today's headers*. Note
>    `Cache-Control` is sent at `:169-171`, **before** the `switch`, so `case 'recent'` must
>    re-send `no-store` when it honours the param.
> 3. **Window form:** contradicts "reuse `recentWindow`" elsewhere in the docs, and the two
>    differ whenever `hours < 24` or `hours = 1000000`. **Moved to D13 (OPEN).**
> 4. **Served list:** the `birdweather` pattern is *not* drop-in for `local` mode. It
>    answers `recent` with only `{hours, species, as_of}` (dropping `site_name`,
>    `educator_scope`) and answers every other action with `{}` (`shoot.py:250-256`).
>    The local-mode variant is specified in **D17**.

Original options retained below for the record.

The brief calls an API change optional; the constraints make one effectively necessary
([verification-log.md](verification-log.md) claims 5 and 7). If accepted:

* **Name:** `reset_at_midnight=1` (matches the existing config vocabulary and the
  `reset_at_midnight` response field) vs a more neutral `window=today`. Upstream PR
  review may prefer the former; a station operator reading logs will too.
* **Shape:** strict scalar; absent ≠ false ≠ true; must ignore PHP-folded aliases
  (`key[]`, `key\0`) — precedent `educator_scope_raw_parameter_count`
  (`avian/api/educator-scope.php:28-48`).
* **Scope:** `case 'recent'` only; `stats`/`hourly`/`rhythm`/`windowClause` untouched;
  educator `$scoped` must keep ignoring display preferences; `hours >= 1000000` and
  historical `?date=` behaviour preserved.
* **Window form:** `Date = :station_date AND DATETIME(Date||' '||Time) <= :anchor`
  (keep the ceiling at `birdnet-api.php:89`).
* **Caching:** clamped response `no-store` or at minimum its own cache key; requests
  without the param must keep today's `public, max-age=30`.

The alternative that avoids touching PHP entirely — serving the frame's own fetched list
to the browser in `local` mode, the pattern `birdweather` already uses
(`shoot.py:243-257`) — is **also a decision under D3**, because it changes where the
truth comes from. Recommendation: additive param, and evaluate the list-serving variant
as the mechanism that keeps signature and image structurally in sync.

Consequence if unanswered: two Workers can implement two different contracts (API param
vs frame-only), and the Phase 4 review has nothing to check against.

### D4 — What environment is the acceptance gate?

**Status:** `ANSWERED 2026-11-16`

> **Clause ruled (operator, 2026-11-16, after research R2): "No new workflow."** Feature tests go
> only into the parent's existing test files (`tests/test_midnight_reset.php`,
> `tests/test_frame_capture.py`) and run in the parent's existing CI, which already has PHP +
> SQLite3 on `ubuntu-latest` (R2, [verification-log.md](verification-log.md#r2-does-the-parents-ci-already-run-the-php-contract)).
> The Debian container, fake station and fake e-ink panel live in `.pi/` and run locally.
> The rest of the D4 ruling (container as the local gate; mandatory hardware pass) stands.
>
> **Clause re-opened by [D20](#d20--guiding-principle-minimal-footprint-aligned-with-the-parent-repo) (2026-11-16):** "mirror it as a GitHub Actions job" adds a workflow to
> the parent's tree. Upstream CI already runs `pytest` on Linux (`.github/workflows/python-app.yml`);
> the container + fakes can live in `.pi/` instead. Needs operator re-confirmation. See [minimal-footprint.md](minimal-footprint.md).

> **Ruling:** **Option A — Debian dev container + CI job.** "Build a docker image
> (php-cli, php-sqlite3, sqlite3, Python 3.11 venv, Playwright Chromium) with a
> fake-station fixture and the headless fake panel; mirror it as a GitHub Actions job so
> 'tests pass' is reproducible."

What this commits us to, per [test-environment.md](test-environment.md):

1. A `debian:bookworm-slim` image following the `frame/Dockerfile.install-security`
   precedent, with `php-cli`, `php-sqlite3`, `sqlite3`, a Python **3.11** venv
   (`requirements.txt` + `frame/requirements-frame.txt` + `frame/requirements-shoot.txt`),
   Playwright Chromium, and `xvfb` if the browser needs it.
2. A **fake station** fixture: real `avian/api/` served by `php -S` against a synthetic
   `birds.db` created from `scripts/createdb.sh` (indexes included), seeded relative to a
   chosen anchor so midnight rollover, silent multi-day stretches, first-detection-of-day,
   DST days, and an old station that ignores the new param are all reproducible.

> **Amended 2026-11-16 (Audit 2, F-H6) — the ruling (container + CI) stands; items 1–2
> above are not viable as written.** Parent re-verified each point against source.
>
> * **Packages:** do **not** install `requirements.txt` (the station's ML stack:
>   tensorflow, streamlit…) or `frame/requirements-frame.txt` (pulls real `inky` →
>   `spidev`, which needs a C toolchain bookworm-slim lacks, and defeats the fake panel).
>   Install Pillow + `frame/requirements-shoot.txt` (Playwright) + pytest; put the fake
>   `inky` on `PYTHONPATH`.
> * **`php -S` runs as SAPI `cli-server`, not `cli`.** Every test override in the API is
>   gated on `PHP_SAPI === 'cli'` (`avian/api/educator-store.php:39,46,52,101,421,492`;
>   `avian/api/educator-state.php:23,30`) and is therefore **ignored** — including
>   `AV_EDUCATOR_BIRDS_DB` and `AV_EDUCATOR_NOW`.
> * **Every request takes a root-owned lock first.** `educator_resolve_scope` calls
>   `educator_store_lock(false)` *before* checking whether Educators is enabled
>   (`avian/api/educator-scope.php:148-157`); the lock lives at `/var/lib/avian-visitors/educators.lock`
>   (root:caddy 0660, real `caddy` group, posix functions). Without it **every** API call
>   returns 503. Provision it in the image, or drive endpoints through the existing
>   `php -r` harness (`tests/test_educator_security.py:216-236`) where the `cli` overrides
>   work.
> * **Paths:** `birds.db` must be at `<served tree>/../../scripts/birds.db` and
>   `birdnet.conf` at `dirname(__DIR__,2)` (`avian/api/birdnet-api.php:35-36`) — serve a **copied**
>   tree, or fixtures land in the checkout's `scripts/`.
> * **No clock seam for `recent`.** Today and the anchor come from SQLite
>   `'now','localtime'` (`birdnet-api.php:280,294-296`); `AV_EDUCATOR_NOW` does not apply.
>   "Seed relative to a chosen anchor" is achievable only by seeding rows relative to
>   *real* now, by a `TZ` offset trick, or with `libfaketime`. Pick one explicitly.
> * **Fixture DDL:** `scripts/createdb.sh` sources `/etc/birdnet/birdnet.conf`, writes
>   `$HOME/BirdNET-Pi/...`, drops the table and `chown`s — copy the DDL out, don't run it.
> * **DST cases drop out** if D13 picks the `Date =` form (no time arithmetic left).
> * **CI may already cover part of D4:** `.github/workflows/python-app.yml` `build` runs `pytest` on Linux
>   (`fcntl` works there) and `frame-capture` installs Python 3.11 + Playwright Chromium.
>   Extend that job rather than inventing a parallel one. Whether the runner image has
>   `php` + sqlite3 (i.e. whether the PHP test is *already* non-vacuous in CI) is unverified.
> * Python 3.9 compatibility is not exercised by a 3.11-only container; only the flake8
>   matrix covers it (`.github/workflows/python-ci.yml:15`).
3. A **headless fake `inky`** on `PYTHONPATH`, in `tests/` only — never an env-var branch
   inside `frame/display.py`. Assertions are update counts plus captured PNG frames.
4. A CI job mirroring it, so "tests pass" means something reproducible and the Phase 5
   report cannot be built on vacuously-skipped tests.
5. **Tier 3 hardware pass on `birdpic` remains mandatory before merge** — burn-in/heal,
   the concurrent-push controller wedge, Zero 2 W capture timing, colour fidelity, SPI and
   mat geometry are not emulatable. Record the result in
   [verification-log.md](verification-log.md).

On this machine the daemon is not running: Docker Desktop must be started before the
first build. WSL2 Ubuntu stays a fine ad-hoc fallback but is no longer the gate.

> **Environment finding (2026-11-16, while attempting R3):** WSL2 **cannot start** on this
> machine — `Wsl/Service/CreateInstance/CreateVm/HCS/HCS_E_HYPERV_NOT_INSTALLED` (Virtual Machine Platform / virtualization not enabled). Docker
> Desktop needs the same virtualization, so the D4 container is **blocked here** until the
> operator enables it (admin `wsl.exe --install --no-distribution` + reboot, possibly a
> BIOS setting). The ruling stands; only its local feasibility changed. Parent CI (R2) is
> unaffected.

Original context retained below.

On this workstation nothing load-bearing is verifiable *(as of the D4 ruling; since 2026-11-16 PHP is
installed per-user and the PHP contract runs — [R3](verification-log.md#r3-execute-the-clamp-and-param-shape-claims-with-php))*: `php` is absent (PHP contract
tests **pass vacuously**, `tests/test_midnight_reset.py:7`), `fcntl` is absent (every
`display.py`-dependent test errors), the full suite aborts at collection, and there is
no e-ink panel.

Options (evidence in [test-environment.md](test-environment.md)):

* **(A) Container gate.** Debian-based dev container (matching
  `frame/Dockerfile.install-security`'s `debian:bookworm-slim` precedent) with
  `php-cli` + `php-sqlite3` + `sqlite3` + a Python 3.11 venv + Playwright Chromium, plus a
  **fake station** (`php -S` on the real `avian/api/` against a synthetic `birds.db`) and a
  **headless fake `inky` panel** that records update counts and PNGs. Mirror as a CI job.
  Strongest option: it makes the brief's time scenarios deterministic. Needs Docker
  Desktop started (it is installed; the daemon is not running).
* **(B) WSL2 Ubuntu.** Same toolchain via `apt`, no image to maintain, faster to stand up
  here (Ubuntu is installed, currently Stopped). Less reproducible than (A) unless the
  package list is checked in.
* **(C) Windows-native PHP only.** `choco`/`scoop`/`winget` can install PHP, which fixes
  the vacuous PHP tests but **not** the frame: `display.py` still cannot import (`fcntl`).
  Split verification story for no real gain — not recommended.
* **(D) CI-only + one hardware pass.** No local Linux env; rely on GitHub Actions plus a
  manual `birdpic` run. Cheapest now, weakest during development.

All options still require the tier-3 hardware pass: panel emulation cannot prove refresh
artifacts, burn-in/heal policy, the concurrent-push controller wedge
(`display.py:516-528`), Zero 2 W capture timing, or colour fidelity.

**Settled as a sub-answer of this decision:** the display *can* be emulated for
behavioural testing, but **not with upstream `inky.mock`** — its `_RESOLUTION` set stops
at 800×480 and the frame's panel is 1600×1200, `InkyMock` opens a Tk window unconditionally,
and `pip install inky` fails on Windows (`spidev`). A test-side fake `inky` package on
`PYTHONPATH` is the correct mechanism because `push_panel` lazy-imports the library.

Consequence if unanswered: the Phase 5 report will claim green tests that were skipped,
and Phase 6's PR-readiness verdict will be built on them.

---

### D12 — What does "nothing to draw" mean for the D1 decline?

**Status:** `ANSWERED 2026-11-16` (via sub-rulings D12a–c below)

Asked in small guiding steps (operator preference, 2026-11-16):

* **D12a — UX, `ANSWERED 2026-11-16`.** Q: "After midnight, the first bird heard today has
  no picture. What should the wall show?" Ruling: **"Keep yesterday's collage"** — treat
  *only undrawable birds* exactly like *no birds yet*; the wall changes on the first
  *drawable* bird. (Rejected: showing a 'listening' card, which would blank the wall.)
* **D12b — operator's setup, `ANSWERED 2026-11-16`.** Q: "Have you run
  `sudo avian-bundle use <BUNDLE_ID>` on the frame?" Answer: **"Yes, the frame has its own
  bundle."** ⇒ the primary path is exact: filter today's species by the active frame bundle's
  `drawable_slugs` (`frame/bundle_runtime.py:2023-2025`). The no-frame-bundle path (station
  mask table via `avian/api/bundle-assets.php`) is still supported, but tested second.
* **D12c — fallback, `ANSWERED 2026-11-16`.** Q: "If the frame can't tell which birds are
  drawable, what should it do?" Ruling: **"Behave like today"** — attempt the draw; worst
  case is today's fail-static behaviour (wall unchanged, retry later). Never blanks the wall.

**Combined ruling:** with `reset_at_midnight` on, decline (exit 0, no capture, no
`save_state`) when today's window contains **no drawable species**; drawable = frame-bundle
`drawable_slugs` when a frame bundle is active, else the station's mask table; if the
drawable set can't be determined, proceed as today.

> **Amended 2026-11-16 by R5 (`PARENT-DECIDED`, refines "drawable"; [R5 brief](../outputs/r5-drawable-base-pose.md), [R5](verification-log.md#r5-drawable-vs-base-pose-deep-research-brief--reviewer--live-feed-scan)).**
> "Drawable" now means what the collage actually draws on every capture: **some species in
> today's window has its unsuffixed slug as a key in the masks table the collage will load**
> (frame bundle: a `perched` or `variant-1` pose; station default: `slug in MASKS`, no suffix
> stripping, masks not dims). *Basis:* the collage draws only the base pose or `-2` and drops the
> tile otherwise (`avian/frontend/apt.js:3164-3186`; pose 2 only on a 15% roll); no validator
> requires a base pose; and an installable bundle in the live community feed
> (`community-peterdeboer-nl-cacd91aeb7749fec`) has **22 flight-only species**, which the
> species-level `drawable_slugs` would call drawable while the capture hangs on ~85% of runs.
> This implements D12a's ruling ("keep yesterday's collage" until the wall can show today's
> bird) more faithfully; it does not change it. Computed locally — **`ActiveBundle.drawable_slugs`
> stays species-level** (upstream uses it for BirdWeather filtering).

> **Amended 2026-11-16 after the [Plan v0.3 Oracle review](verification-log.md#plan-v03-oracle-review) (`PARENT-DECIDED`, no-bundle path only).**
> With **no frame bundle**, the frame does **not** fetch the station's mask table: only an
> **empty** today-window declines; every listed species counts as drawable. *Basis:* D20 (the
> station table `avian/frontend/masks.json` is ~800 KB — too heavy to fetch every 15 minutes on
> a Zero 2 W) and D12b (the operator's frame has its own bundle, where the exact base-pose test
> applies). The "else the station's mask table" clause above and the R5 "station default:
> `slug in MASKS`" clause are **superseded for the frame**. Residual risk (a station-default
> flight-only species, no frame bundle) is fail-static: panel kept, capture times out, exit 1.

**Why it blocks:** D1 as written declines on an *empty* list. But a non-empty list can be
undrawable: in `local` mode `fetch_species` ignores `drawable` (`frame/display.py:132-150`),
`renderCollage` drops tiles with no mask (`avian/frontend/apt.js:3179,3186`; cited as `:3181-3190`
before R5), and with zero placed tiles
`finishFrameRender` is never called (`apt.js:3359`) — so `FRAME_READY` never fires, capture
runs the full 180 s deadline, and the run **exits 1**: every timer cycle, and under
`avian-bundle use`/`rollback` exit 1 **reverts the bundle**. Pre-existing for rolling
windows; today-only makes it common because a day's first detection is often a single
(nocturnal) species. Mixed lists are fine (only drawn tiles are counted).

**Where a local frame can learn the drawable set:**

* Frame bundle active: exact — `bundle.drawable_slugs` (`frame/bundle_runtime.py:2023-2025`).
  *(Corrected by R5: species-level, so not exact — use the base-pose / masks-key test above.)*
* No frame bundle: the station's tables — `avian/frontend/masks.json` (`apt.js:1294`) or, if the station
  selected a bundle, `avian/api/bundle-assets.php`'s active `masks` table
  (`avian/api/bundle-assets.php:41,106`). The frame clone's own `avian/frontend/dims.json` is the **wrong**
  source (different checkout, possibly different version).

**Options:**

1. **Decline when no species in today's window is drawable** (recommended). Frame bundle ⇒
   filter by `drawable_slugs`; no bundle ⇒ read mask keys from the station's
   `bundle-assets.php` only when a capture is about to run; if that read fails, fall back
   to today's behaviour. Flag-gated only.
2. Keep "empty list only", and document the exit-1 storm + bundle-revert risk.

**Consequence if unanswered:** the first un-illustrated bird after midnight produces a
3-minute failed render every 15 minutes until a drawable bird arrives (req 6 delayed),
and any bundle switch in that window is silently undone.

### D13 — Does the today-window respect the `hours` setting?

**Status:** `ANSWERED 2026-11-16`

> **Amended by [D20](#d20--guiding-principle-minimal-footprint-aligned-with-the-parent-repo) (2026-11-16) — implementation only; the UX ruling stands.** Instead of a new
> SQL branch, reuse upstream `recentWindow`: the frame sends `hours=24` plus the param, and with a
> 24-hour window on today's anchor the clamp always applies (`anchor − 24h` < `start of day`), which
> is exactly "everything since midnight". Upstream already pins it ("24 hour window clamps after
> midnight", `tests/test_midnight_reset.php`). No new SQL, no echo fields. See [minimal-footprint.md](minimal-footprint.md).

> **Ruling:** **"Everything since midnight."** Asked as: *"With midnight reset turned on,
> which birds should the wall show during the day?"* — with reset on, the frame **ignores
> `hours`** and shows the whole station calendar day up to the anchor. Implementation
> consequence (from the recommendation): a separate branch
> `Date = :station_date AND DATETIME(Date||' '||Time) <= :anchor`, leaving `recentWindow` and
> its pinned test untouched; echo `window_start = "<date> 00:00:00"` and
> `midnight_clamped: true`. README must say `hours` is ignored while reset is on. The DST
> test cases drop out (no time arithmetic).

Original analysis retained below.

**Why it blocks:** the docs specify two contracts. `recentWindow` gives *intersection(last
`hours`, today)* and only clamps when `rolling <= midnight` (`avian/api/birdnet-api.php:104-116`;
pinned by "short window inside the day stays rolling", `tests/test_midnight_reset.php:38-40`).
The `Date = :station_date AND … <= :anchor` form ignores `hours`. They agree for
`hours >= 24`, differ for smaller values late in the day and for `hours = 1000000`.
`hours` is user-settable (`frame/display.py:51`).

**Options:**

1. **Ignore `hours` when the flag is on** (recommended): window = the station's calendar
   day up to the anchor. Only this satisfies req 1 ("starting at 00:00") literally. Implement
   as a **separate branch**, leaving `recentWindow` and its pinned test untouched; echo
   `window_start = "<date> 00:00:00"` and `midnight_clamped: true` so `avian/frontend/apt.js`'s
   "since midnight" label (`apt.js:3609`) stays coherent. Say so in the README.
2. Reuse `recentWindow` with the param as `$resetAtMidnight` — smallest diff; `hours < 24`
   means "last N hours, but not before midnight".

**Consequence if unanswered:** Workers implement one contract while tests and docs assume
the other; with option 2 and the old D5 signal, a correct new station returns
`midnight_clamped: false` for small `hours` and gets mistaken for a degraded one.

### D14 — How is an un-updated station detected, and with what exit code? (supersedes D5)

**Status:** `ANSWERED 2026-11-16`

> **Amended by [D20](#d20--guiding-principle-minimal-footprint-aligned-with-the-parent-repo) (2026-11-16) — detection only; exit 1 ruling stands.** No new echo field:
> detect on the existing `midnight_clamped`. Audit 2's objections vanish once the frame always sends
> `hours=24` (an old station with the global flag ON already returns correct, clamped rows). See [minimal-footprint.md](minimal-footprint.md).

> **Ruling (exit code):** **"Loud — mark it failed."** Asked as: *"Frame updated, station
> not; the frame keeps its last collage. How loud should it be?"* ⇒ hold the previous collage
> and **exit 1** with the existing "update both the mic and frame" wording, matching today's
> outdated-station behaviour (`frame/README.md:91`). Never blank, never mix.
>
> **Detection (parent-decided, technical):** a **distinct echo field** emitted only by the new
> station code and only when the param was honoured (e.g. `"window": "station_day"`); detect
> on that alone, never on `reset_at_midnight` / `midnight_clamped`. D1's exit 0 remains for
> the steady-state "nothing to draw today" case only.
>
> Known consequence, to state in the README: under `avian-bundle use` an outdated station
> makes the render exit 1, which reverts the bundle switch — the same as today's old-mic case.

Original analysis retained below.

**Why it blocks:** D5's signal is not definitive (see the D5 row). Separately, D5 said
"log one line" but never chose an exit code — and the README precedent for an old mic
("keeps its previous image and logs an update reminder", `frame/README.md:91`) currently
**exits 1** via capture failure (`frame/shoot.py:520`), so systemd shows the unit failed.

**Recommendation:**

* A **distinct echo field** emitted only by the new code, only when the param was honoured
  (e.g. `"window": "station_day"`); detect on that alone. Never infer from
  `reset_at_midnight` / `midnight_clamped`.
* Hold the previous collage and **exit 1** with the existing "update both the mic and frame"
  wording — a frame that will never update again should be loud, as it is today.
* D1's exit 0 remains for the *steady-state* empty window only.
* Note exit 1 under `avian-bundle use` reverts the bundle — consistent with today's old-mic
  behaviour, but worth a README sentence.

### D15 — Educators capture active while `reset_at_midnight` is on?

**Status:** `PARENT-DECIDED 2026-11-16`

> **Amended by [D20](#d20--guiding-principle-minimal-footprint-aligned-with-the-parent-repo) (2026-11-16):** no dedicated code. A scoped response reports
> `midnight_clamped: false` (`avian/api/birdnet-api.php:90`), so it takes the D14 hold path; only
> the log text widens to name both causes (outdated station, or an Educators capture). See [minimal-footprint.md](minimal-footprint.md).

> **Operator context:** asked *"Do you use the station's Educators (classroom) feature?"* —
> answer: **"No, I don't use it."** So this path is not reachable on the operator's setup and
> was not escalated further.
>
> **Decision (house style, fail-static):** option (a) — if the response shows an Educators
> scope (`educator_scope` present) while the flag is on, **hold the previous collage, log
> "educator capture active", exit 0**. Scope semantics win; the param never overrides a scope
> (that invariant is pinned by `tests/test_midnight_reset.php`). Revisit if the operator ever
> starts using Educators. Needs one test, no hardware.

Original analysis retained below.

**Why it blocks:** while Educators is enabled and a capture is `running`/`paused`, every
*unscoped* request is scoped automatically (`avian/api/educator-scope.php:182-191`;
`avian/api/educator-store.php:1108-1112`). Scoped requests ignore display preferences
(`avian/api/birdnet-api.php:90`) and anchor on the latest scoped detection (`:286-296`). So during a
classroom capture the frame either holds for its whole duration (with D14) or, naively,
mixes days.

**Options:** (a) **hold and log "educator capture active", exit 0** (recommended — scope
semantics win, frame stays fail-static); (b) show the scoped collage as today does;
(c) let the param override the scope (weakens an invariant the PHP tests pin).

### D16 — No validated list (fetch failed, or `--no-signature`) with the flag on?

**Status:** `ANSWERED 2026-11-16`

> **Ruling:** **"Report a failure, like today."** Asked as: *"You run a manual refresh (or
> switch bundles) while the station is unreachable. With midnight reset on, what should
> happen?"* ⇒ with the flag on in local mode the frame **never captures without a validated,
> honoured list**, so forced paths gain the fetch. **Timer run** + fetch failure ⇒ skip,
> exit 0, retry in 15 min (as today). **Forced run** (`--force`, `--no-signature`,
> `avian-bundle use`/`rollback`, `birdframe-names`) + fetch failure ⇒ **exit 1**, which
> makes a bundle switch revert so it can be retried — matching today's station-down
> behaviour. The wall is never touched either way.

Original analysis retained below.

**Why it blocks:** today a heal after a failed fetch captures with `species=None`
(`frame/display.py:444-453`), and `--no-signature` — used by both bundle paths — never fetches in
local mode (`display.py:429`; only the birdweather branch re-fetches, `:377-384`). With the
list-serving design, such a capture would let the page fetch `recent` *without* the param
(`frame/shoot.py:258`) and **mix days**.

**Recommendation:** with the flag on in local mode, **never capture without a validated,
honoured list**. Forced paths therefore gain the fetch. Timer run + fetch failure ⇒ skip,
exit 0 (as today); forced run + fetch failure ⇒ exit 1 (matches today's
station-unreachable behaviour).

### D17 — The local-mode served-list variant

**Status:** `SUPERSEDED 2026-11-16` — operator chose the parent repo's flow

> **Operator ruling (re-asked under D20):** asked *"How should the frame get today's birds onto
> the page it photographs?"* — **"Use the parent repo's way."** The page keeps fetching
> `recent` from the station exactly as upstream does; the frame adds the midnight param (and
> `hours=24`) to the request `frame/shoot.py` already rewrites (`frame/shoot.py:258`). No
> served-list code path. This also **replaces the "frame serves its own list" half of the D3
> ruling**; D3's other half (additive request param, config toggle default off) stands.
> Signature/pixel agreement is provided by upstream's existing re-sign from the captured
> response (`frame/display.py:457-463`). A/B R4 is no longer needed.

> **Re-opened by [D20](#d20--guiding-principle-minimal-footprint-aligned-with-the-parent-repo) (2026-11-16) — needs operator re-confirmation.** Its premise (signature and
> pixels must come from one response) is already handled upstream: `frame/display.py:457-463`
> re-signs from what the browser was served (`frame/shoot.py:272-275`). The upstream-aligned
> alternative keeps the page's own station request and adds the param to the existing `hours=`
> rewrite (`frame/shoot.py:258`). See [minimal-footprint.md](minimal-footprint.md) and A/B R4.

Amends D3's mechanics; does not change the ruling.

* Fulfil `recent` with the frame's **full** fetched response — every field (`site_name`,
  `educator_scope`, window metadata, `species`) — plus `frame_capture_id`. `small_floor`
  applies after the capture snapshot exactly as today (`frame/shoot.py:270-280`).
* **`continue_()` all other actions to the station**, as local mode does today
  (`shoot.py:253`). Do not adopt birdweather's `{}`.
* **Flag-gated.** With `reset_at_midnight = false`, `_make_api_handler` behaves exactly as
  today, so req 12 stays bit-identical (`site_name` and `educator_scope` pass-through is
  pinned by `tests/test_frame_capture.py:177-185`).
* The fetch helper returns the **whole response**, not `data["species"]` (needed by D14
  and D6). Add a flag-only helper rather than changing `fetch_recent` / `fetch_species`, so
  existing mocks and req 12 are untouched.
* ~~`run()` gains several branches; plan a helper to stay under flake8 `max-complexity = 15`.~~
  *Corrected 2026-11-16:* measured 2026-11-16 with the repo's `.flake8`: upstream `frame/display.py` `run()` = 18, `frame/shoot.py` `_make_api_handler` = 16, `shoot()` = 46 — the 15 limit is **not enforced**: `.github/workflows/python-ci.yml` (plain `flake8`) runs only on PRs to `main`, the parent's default branch is `avian-visitors`, and `.github/workflows/python-app.yml` gates only `E9,F63,F7,F82` (complexity is `--exit-zero`). Under D20, add the feature's branch(es) in upstream's style;
  do not restructure `run()`.

Basis: house style (additive, flag-gated, minimal blast radius) and the pinned tests above.

---

### D20 — Guiding principle: minimal footprint, aligned with the parent repo

**Status:** `ANSWERED 2026-11-16`

> **Ruling (operator's words):** "At all points whenever possible, we want to stick to
> aligning and defaulting to what the parent repo does. We only change the smallest amount of
> code to implement our desired change. If that requires additional research, AB testing,
> then plan it out, research it, document it. We walk lightly, quietly, and leave as little
> trace as possible the expense of us working harder."

**Precedence:** outranks every `PARENT-DECIDED` detail; operator rulings that conflict with it
are **re-asked**, not overridden. Applied in
[minimal-footprint.md](minimal-footprint.md) the same day: parent-decided details shrunk
(D13 implementation, D3 mechanics, D14 detection, D15, D6 dropped, `Date =` optimisation
dropped); two operator rulings flagged for re-confirmation (D3's "frame serves its own list"
half → [D17](#d17--the-local-mode-served-list-variant), and D4's "mirror it as a CI job").
**Outcomes:** D17 — operator chose the parent repo's flow (superseded). D4 CI clause — operator:
"Decide after research R2"; R2 done (parent CI already runs PHP + SQLite3); then **"No new
workflow."**

### D21 — May the parent open a PR inside the fork so the parent's CI runs?

**Status:** `OPEN` (not blocking until execution stage V of Plan v0.3)

**Why:** the parent's `.github/workflows/python-app.yml` runs only on pushes to
`main`/`test_me`/`avian-visitors` or PRs into `main`/`avian-visitors`, and has no
`workflow_dispatch` — pushing `feature/birdframe-midnight-reset` alone runs nothing (found by the
[Plan v0.3 Oracle review](verification-log.md#plan-v03-oracle-review)). Real Linux CI (real `fcntl`, PHP + SQLite3) needs a PR inside
`moomoomafia/AvianVisitors` into its `avian-visitors` branch, with Actions enabled on the fork.

**Options:** (1) yes, at stage V only, never targeting the parent (recommended); (2) push the
change to the fork's `avian-visitors` directly (also triggers CI, but changes the fork's main
branch); (3) no CI — rely on local runs + the hardware pass.

**Consequence if unanswered:** Plan v0.3's CI row cannot run; verification rests on local runs
(stubbed `fcntl`, scoop PHP) and hardware.

> **Deferred 2026-11-17 (at the G0 lift, operator):** stays `OPEN`; re-ask at stage V. Reason:
> nothing blocks W1–W3 — §6's local runs cover verification on this host, and pushing a feature
> branch alone triggers no CI. Do not open a PR into the fork's `avian-visitors` branch.

---

## Non-blocking — decided by the parent from house style, to be proposed in the PR

Recorded so no child re-opens them, and so Reviewer can check the implementation matches.

| ID | Question | Adopted answer | Basis |
|---|---|---|---|
| D5 | ~~Un-updated station ignores the param: fall back to rolling, or hold?~~ **SUPERSEDED by D14 (Audit 2).** | ~~Hold; detect via absent `midnight_clamped` / `window_start`~~ — those fields are **always present** on any station with the global-flag code (`avian/api/birdnet-api.php:392-397`), and an old station with the global flag ON already returns `midnight_clamped: true`, so they cannot prove the param was honoured | see D14 |
| D6 | First detection of the day hashes identically to yesterday — refresh? | **Dropped by [D20](#d20--guiding-principle-minimal-footprint-aligned-with-the-parent-repo) (2026-11-16): not implemented — near-cosmetic, adds hash material.** Force a refresh by putting the effective window identity in the existing `scope` argument of `signature()`. **Audit 2: optional / near-cosmetic** — if today's signature equals the saved one, the glass already shows that species+bucket set. The salt must come from the *same* response in both hashing sites (`frame/display.py:438-441,459-463`) | precedent `birdweather_signature_scope` (`display.py:125`); keeps the frozen unscoped hash contract (`tests/test_frame_birdweather.py:193-197`) |
| D7 | Suppress the 24 h heal while today's window is empty? | Yes, suppress; document the burn-in consequence. A heal cannot "redraw the retained image" — a clamped window structurally cannot return yesterday's rows. **Audit 2: needs no mechanism** — a data-keyed pre-capture guard already suppresses it | req 10 explicitly outranks heal; [`frame-refresh-decision.md`](frame-refresh-decision.md) |
| D8 | First detection inside quiet hours leaves yesterday up until quiet ends? | Yes — the brief says preserve quiet hours; state it in docs and cover with a test | `in_quiet_hours` (`display.py:348`) |
| D9 | Additive `state.json` keys; must older files still work? | **Amended (Audit 2): add no keys.** A data-keyed pre-capture guard is already immune to a corrupt/missing `state.json`, so the state format stays unchanged. Hard rule: **a decline must never call `save_state`** (it would stamp `last_refresh` without a push); today `save_state` is only reached after `push_panel` (`display.py:477-481`) — keep it that way. Covers the `OnBootSec=2min` boot-after-outage run | `display.py:329-335,477-481`; `frame/systemd/birdframe.timer:10` |
| D10 | Should any of this be pushed into `avian/frontend/apt.js` or the global flag? | No. The site must keep clearing on a genuinely empty window, and the global `RESET_AT_MIDNIGHT` is off-limits | `tests/smoke_collage_readiness.mjs:25`; brief isolation list |

---

(D9 is the row above; D17 is included only so its superseded status is visible — do **not** implement its served-list or flag-only-helper bullets.)
