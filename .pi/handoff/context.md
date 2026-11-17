# Worker context — BirdFrame midnight reset

Prepared by the parent on 2026-11-17 from the knowledge base (no fresh scout: the base already
holds the scout phase). Authoritative design: `.pi/handoff/plan.md` (verbatim Plan v0.3 +
register). Ledger: `.pi/handoff/ledger.md`.

## Files retrieved (read by the parent this session)

* `avian/api/birdnet-api.php:135` — `$action = $_GET['action'] ?? 'stats';` (the new
  `$resetAtMidnight` line goes right after it, per plan §4.1).
* `avian/api/birdnet-api.php:169-171` — `header('Cache-Control: ' . (($educatorCacheDisabled || $RESET_AT_MIDNIGHT) ? 'no-store' : 'public, max-age=30'));`
* `avian/api/birdnet-api.php:358-364` — `recentWindow($db, $hours, $ctx, $RESET_AT_MIDNIGHT, $educatorScope !== null)`.
* `avian/api/birdnet-api.php:104-116` — `recentWindow` clamp (`hours=24` always clamps to midnight).
* `tests/test_educator_backend.php:64-76` — `edu_endpoint(...)` harness (for open question Q1).
* `tests/test_midnight_reset.php` — pins the clamp; run with `php tests/test_midnight_reset.php`.
* `.pi/research/r3/clamp_check.php`, `.pi/research/r3/param_check.php` — R3 probes, run with
  `php -d extension=sqlite3 <file>`.

## Environment (this Windows host)

* PHP 8.5 via scoop; a shell older than the install fails with `Class "SQLite3" not found`
  (environment, not product) — pass `-d extension=sqlite3` or a fresh `PHP_INI_SCAN_DIR`.
* WSL2/Docker cannot start (`HCS_E_HYPERV_NOT_INSTALLED`); no e-ink panel; `fcntl` absent.
* The bash tool may run under cmd.exe: wrap multi-step shell in `bash -lc '...'`.
* `core.autocrlf=true`: keep files LF.

## Rules for every child

* You have **no subagent tool**; do not spawn agents or shell out to `pi`.
* Do not touch, commit, or clean untracked files (`.pi-tasks/`, `.pi/ask-log/`); never
  `git add -A`, never `git clean -x`/`-X`. No push, no PR.
* §4.6 "Not changed" (in `plan.md`) is a hard boundary.

## Start here

W1: plan §4.1, then the "Done when" row for W1 in §7.
