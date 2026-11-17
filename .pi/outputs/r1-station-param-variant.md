# R1 — How should the station read the frame's midnight-reset request?

**Question.** Should the station change be **one line** (fold the new request option into the
existing `$RESET_AT_MIDNIGHT` variable) or **three lines** (a separate variable, so the existing
one keeps meaning "station setting")? Governing principle: decision D20 — align with the parent
repo, change the least code; alignment outranks raw line count
([minimal-footprint.md](../knowledge/minimal-footprint.md)).

**Answer: Variant B′ — one new local `$resetAtMidnight` (station flag OR request), and swap that
one token in at the two existing use sites. +1 line added, 2 lines modified.**

```php
// in the request-derived block, after :135 ($action)
$resetAtMidnight = $RESET_AT_MIDNIGHT || (($_GET['reset_at_midnight'] ?? null) === '1');
// :169   (($educatorCacheDisabled || $resetAtMidnight) ? 'no-store' : 'public, max-age=30')
// :362   recentWindow($db, $hours, $ctx, $resetAtMidnight, $educatorScope !== null)
```

*Revision 2 (2026-11-16), after an independent reviewer pass: added B′, corrected E1/E7/E8,
re-ranked C below A, and added the echo-field and all-actions notes. See "Changes from revision
1" at the end.*

All file references are to this checkout at `5950f807` (parent `avian-visitors` tip).

## Candidates

| | Variant | Diff in `avian/api/birdnet-api.php` | Reset ⇒ `no-store` (D3 requirement) | `$RESET_AT_MIDNIGHT` keeps meaning "config" |
|---|---|---|---|---|
| A | Fold the param into the config variable at `:129` | 1 modified | yes | **no** |
| B | New request-only local (e.g. `$resetAtMidnightRequested`) OR'd in at `:169` and `:362` | +1, 2 modified | yes | yes |
| **B′** | New *effective-flag* local `$resetAtMidnight = $RESET_AT_MIDNIGHT \|\| (…)`, one-token swap at `:169` and `:362` | +1, 2 modified | yes | yes |
| C | Inline OR only at the `recentWindow` call (`:362`) | 1 modified | **no** — needs an operator amendment of D3 | yes |

**A, B and B′ behave identically at runtime**: each affects exactly the two consumers of the
flag, so the window and the header change in the same way. The differences among them are naming
and future-proofing only. C behaves differently (no `no-store` on clamped responses).

Common to every variant (reviewer-confirmed):

* **No change without the param** — the OR term is `false`, so requests that don't send it get
  today's window and headers exactly.
* **`=0` can never switch a station-wide ON off** — it is an OR.
* **Educator scopes still win** — `$enabled = $resetAtMidnight && !$scoped` (`:90`).
* **D14 detection is unaffected** — new station + param + `hours=24` ⇒ `midnight_clamped: true`;
  old station with the global flag off ⇒ `false` (hold, exit 1); old station with the flag on ⇒
  `true` with correctly clamped rows; scoped ⇒ `false` (D15 hold).
* **The `reset_at_midnight` response field changes meaning** to "station flag OR param, and not
  scoped" (`:95,121,394`). No reader of that field exists in the repo (the frontend reads only
  `midnight_clamped`, `avian/frontend/apt.js:3609`); `.pi/knowledge/birdnet-api.md` must be
  updated when this is implemented.
* **In A, B and B′ the `no-store` header applies to every action carrying the param**, not only
  `recent` (the header is set before the `switch`, `:169`). That is parity with the global flag,
  and satisfies D3's recorded rule that requests *without* the param get exactly today's headers;
  only the frame sends the param, and only on `recent`.

## Evidence

**E1 — UPPER_CASE top-level variables hold server-side values, never client data.** All
top-level `$UPPER_CASE =` assignments in `avian/api/*.php`: **18 names at 30 sites** (28 at
column 0) — paths, environment lookups, constants, config reads (`birdnet-api.php:36-37,129`;
`birdnet-status.php:46`; `config.php:30`; `generate.php:41-42`; …). The closest case is
`$EXTRACTED` (`export.php:452,459`), re-assigned under a request-dependent condition
(`$what === 'recordings'`, `:453`) to a value read from Caddy's server environment
(`educator_configured_extracted_root($_SERVER)`, `AVIAN_EXTRACTED_ROOT`) — still a server-side
value. **No UPPER_CASE variable holds client-supplied input.** Variant A would be the first.
*(Corrected: revision 1 said 15 names / 24 sites and missed `$EXTRACTED`.)*

**E2 — Request-derived values are camelCase locals** declared together at `birdnet-api.php:131-136`
(`$educatorDirectRequest`, `$educatorSavedRequest`, `$action`, `$educatorScopeProbe`), with derived
flags like `$educatorIncludePrivateScope` (`:133-134`) and `$educatorCacheDisabled` (`:167-168`).
B′'s line belongs in this block.

**E3 — Upstream's idiom for a second `no-store` reason** is an OR of a camelCase local with the
config flag: `(($educatorCacheDisabled || $RESET_AT_MIDNIGHT) ? 'no-store' : …)` (`:169-171`),
introduced by commits `116471c1` and `f1cb3add` (both 2026-09-02). B′ swaps one operand.

**E4 — Upstream pairs "reset on" with `no-store`** (`:169-171`; same commit `f1cb3add`). D3's
recorded mechanics also require it ("clamped response `no-store`"). C drops it.

**E5 — For the frame the cache header is practically irrelevant.** The signature fetch is a plain
`urlopen` (`frame/display.py:91-97`); the capture launches a fresh browser + context per run
(`frame/shoot.py:425,434`) and fetches `recent` via `route.fetch` (`:262`); the site's own
`fetchJson` already sends `cache: 'no-store'` (`avian/frontend/apt.js:3651-3652`); Caddy sets
`Cache-Control` only for `@shell` and the bundle catalog (`scripts/update_caddyfile.sh:746,807`)
and has no cache handler; `avian/forwarding/cloudflared.yml` and `caddy-auth.caddy` configure no
caching. *Assumption, not verifiable from the repo: Cloudflare edge behaviour.* This makes C's
practical cost near zero — but C still fails a recorded requirement (E4).

**E6 — `$RESET_AT_MIDNIGHT` has exactly two consumers** (`:169`, `:362`; defined `:129`). The
only files that include `birdnet-api.php` (`tests/test_midnight_reset.php:5`,
`tests/test_site_name_api.php:5`) define the library-only constant and return before `:129`.
Under A, any *future* upstream consumer of `$RESET_AT_MIDNIGHT` would silently inherit the
request param; under B/B′/C it would not. Low churn: lines 129/169/362 were touched only by
`f1cb3add`, `116471c1`, `ffdf97e1`; the file has 9 commits.

**E7 — Testability.** The library-only guard (`:127`) sits above `:129`, so the library-mode PHP
contract cannot reach the param read in any variant; it does pin the clamp the design relies on,
`recentWindow($db, 24, $today, true, false)` (`tests/test_midnight_reset.php:33-36`). **But
upstream already has an end-to-end harness that can**: `edu_endpoint()` runs the full endpoint in
a PHP subprocess with injected `$_GET`/`$_SERVER` (`tests/test_educator_backend.php:64-76`) and
already calls `recent` with `hours=1000000` (`:666`). So the param read is testable *in
upstream's own style*; whether to add that test there or keep end-to-end coverage in the `.pi/`
fake-station harness is a separate D4/D20 placement choice for Plan v0.3. *(Corrected: revision 1
said upstream's `$hours` read is not unit-tested.)*

**E8 — Parameter shape.** `($_GET['reset_at_midnight'] ?? null) === '1'` matches upstream's idiom
(`:135,281,356,403-406`; also `?? null` + strict check at `bundle-preview.php:27`,
`cutout.php:55`) and rejects absent, `0`, other strings and arrays. **It does not reject PHP's
key mangling** (`reset.at.midnight=1` or `reset at midnight=1` arrive as `reset_at_midnight`)
and, with duplicates, **the last value wins** — exactly as for every other upstream parameter
(`hours`, `date`, `action`). This is harmless here: the param only selects a read-only display
window, any client may send the canonical name anyway, and mangled aliases grant nothing
extra. It does **contradict D3's recorded amendment** ("folded aliases … treated as absent"), so
D3 is amended by D20/R1 to follow upstream's idiom. *(Argued from PHP semantics; not executed —
no `php` here, see R3.) (Corrected: revision 1 omitted this.)*

## Decision rationale

| Criterion (D20 order) | A | B | **B′** | C |
|---|---|---|---|---|
| Meets every recorded requirement (D3: reset ⇒ `no-store`) | ✔ | ✔ | ✔ | ✖ needs operator amendment |
| No client data in an UPPER_CASE config name (E1) | ✖ | ✔ | ✔ | ✔ |
| Upstream naming for derived flags (E2, `recentWindow(…, bool $resetAtMidnight, …)` `:82-88`) | ~ | ✔ | ✔✔ same name as the parameter it feeds | ✔ |
| Upstream cache-line idiom (E3) | implicit | +1 operand | ✔ one-token swap | n/a |
| Future upstream consumers stay config-only (E6) | ✖ | ✔ | ✔ | ✔ |
| Smallest diff | ✔ 1 | 3 | 3 | ✔ 1 |

**Ranking: B′ > B > A > C.** B′ is the only variant that meets every recorded requirement and every
alignment criterion; it costs one line more than A, and **A and B′ are runtime-identical** — the
extra line buys naming hygiene and merge safety, nothing behavioural. C is cheaper in practice
(E5) but drops a recorded requirement, so it is **not a fallback**: choosing it needs the
operator to amend D3. A remains acceptable if one line ever matters more than the naming invariant.

Naming: `$resetAtMidnight` — the effective flag, identical to the `recentWindow` parameter it is
passed as (`:86`). It differs from `$RESET_AT_MIDNIGHT` only by case, which a reviewer may find
odd; `$resetAtMidnightEffective` is an acceptable alternative. Avoid client-specific names such as
`$frameResetRequested` (revision 1): any client may call the station API.

## Open / unverified

* E8's mangling/duplicate behaviour and the E7 clamp are argued, not executed — R3 runs them in
  the `.pi/` container with `php`.
* Commit attributions and churn in E3/E4/E6 come from the parent's `git` reads; the reviewer had
  no git and could not independently confirm them.
* Not implemented (building is not authorised); nothing observed on a live station or proxy.

## Changes from revision 1

| Item | Revision 1 | Revision 2 |
|---|---|---|
| Recommendation | B (`$frameResetRequested`), C as fallback | **B′** (`$resetAtMidnight`); ranking B′ > B > A > C; C needs a D3 amendment |
| E1 | 15 names / 24 sites; "none derived from request" | 18 / 30; `$EXTRACTED` noted; claim narrowed to "no client data" |
| E7 | "`$hours` read not unit-tested" | wrong — upstream's `edu_endpoint` harness reaches it |
| E8 | "alias machinery unnecessary" | key mangling + last-wins acknowledged; D3 amendment required |
| Added | — | runtime equivalence of A/B/B′; echo-field meaning change; `no-store` on all actions carrying the param |
