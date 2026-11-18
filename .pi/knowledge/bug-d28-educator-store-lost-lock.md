# D28: the Educators store drops its SQLite locks on Linux

Decision: [D28](open-decisions.md#d28--report-the-educator-store-lost-lock-bug-upstream). Found
2026-11-17 by the K1 container ([K1 log](verification-log.md#k1-build-and-baseline)); root cause by
the Oracle; reproduced independently by the parent with a standalone script
([D28 write-up log](verification-log.md#d28-write-up-and-independent-reproduction)).
This is a bug in the **parent repo's** code. It is identical on our base `5950f807` and on HEAD, and
nothing in the midnight-reset feature touches it. Under
[D20](open-decisions.md#d20--guiding-principle-minimal-footprint-aligned-with-the-parent-repo) we do
not fix it on our branch.

## For the operator: what it means in plain words

* The Educators feature keeps its own small database, `educators.db`.
* Each time the code opens that database, it first opens the file a second way to check it is the
  right, safe file, then opens it with SQLite, then **closes the checking handle**.
* On Linux, closing *any* handle to a file throws away *all* of that program's locks on it,
  including the locks SQLite was relying on. SQLite does not notice.
* With its locks gone, another request can conclude nobody else is using the database and tidy up
  its write-ahead log (`educators.db-wal`) while the first request is still using it. In a
  reproduction this loses a write or makes later reads fail with `disk I/O error`.
* **How likely on a real station:** probably rare, and not proven either way. The app also wraps
  every database open in its own lock file (`educators.lock`: shared for reads, exclusive for
  writes), and every caller found so far takes that lock first. That should stop a write from
  overlapping another request. Two readers can still overlap, so the plausible field symptom is an
  occasional Educators 503 rather than lost data. Nobody has measured it.
* **Why nobody noticed:** Windows locks work differently (per handle), so the bug cannot happen
  there, and the parent's CI never runs `tests/test_educator_backend.php`, the suite that exposes it.
* **What we do:** nothing in code. K1 accepts that suite's known failures only if they exactly match
  the parent's base (`.pi/k1/educator-backend.baseline`). Reporting it is your call (draft below).

## Technical detail

**Code path** (`avian/api/educator-store.php`, read 2026-11-17):

| Line | What happens |
|---|---|
| `:253` | `function educator_store_open(bool $initialize = false): SQLite3` |
| `:263` | `$probe = @fopen($path, 'r+');` (identity/metadata probe, then `fstat` dev/ino checks `:264-268`) |
| `:275` | `$db = new SQLite3($path, …)` |
| `:295-297` | `PRAGMA foreign_keys`, `journal_mode = WAL`, `synchronous = FULL` |
| `:321` | `if (is_resource($probe)) fclose($probe);` while `$db` stays open, then `return $db` |

Error paths also `fclose($probe)` (`:269`, `:278`, `:317`), but they close or never open `$db`, so
they are harmless.

**Mechanism.** POSIX advisory (`fcntl`) locks belong to the (process, inode) pair; `close()` on any
descriptor for the inode releases all of them. SQLite's unix VFS works around this only for
descriptors it opened itself; a foreign `fopen()`/`fclose()` pair still wipes its locks
(SQLite's "How To Corrupt An SQLite Database File", section 2.2: "Posix advisory locks canceled by a
separate thread doing close()"; cited from general knowledge, not re-fetched this session). In WAL
mode a connection holds a shared lock on the database file for its lifetime. When another
connection closes and finds no other lock holders, it checkpoints and deletes `-wal` and `-shm`.

**Callers** (all four found by grep in `avian/` and `scripts/` `*.php`), each preceded by the app lock:

| Caller | App lock |
|---|---|
| `avian/api/educator-scope.php:162` | shared, `:153` |
| `avian/api/educators.php:209` | shared, `:206` (GET, read-only path `:204-240`) |
| `avian/api/educators.php:277` | exclusive, `:274` |
| `avian/api/educator-store.php:1784` | exclusive, `:1782` |

`scripts/educators_control.sh` also takes `flock -s`/`-x` on `educators.lock` (`:335-337`) and runs the
`sqlite3` CLI on the store (`:906-916`). The lock implementation is `educator_store_lock()`
(`avian/api/educator-store.php:99-153`, `flock` at `:141`). **Not audited:** whether every `sqlite3`
CLI use in that script is inside the exclusive lock, and whether any shared-lock path writes.

**How the test suite trips it.** `tests/test_educator_backend.php` holds one connection in the test
process across many child requests (around `:1529`). After the probe `fclose`, a child's close
deletes the WAL under the parent connection (`/proc` showed `educators.db-wal (deleted)`), later
checks see stale state, and at `:2114` `educator_resolve_scope()` fails with the original error
`Unable to execute statement: disk I/O error` (from `educator-store.php:331`), rethrown as
`educator scope is unavailable` at `avian/api/educator-scope.php:229`. In real requests the app lock
separates writers from everything else, which the test's long-lived connection bypasses.

**Second, unrelated failure (PHP 8.2 only).** `tests/test_educator_backend.php:1336-1344` expects 503
when the tar binary is missing. On PHP 8.2, `proc_open` still returns a process, so
`avian/api/export.php` takes the 409 branch (`:627`) instead of the 503 one (`:610-616`). No bytes are
sent either way; it is a test/PHP-version gap, not a data bug. Seen on official `php:8.2-cli` vs
`php:8.5-cli` images (Oracle); the PHP-internal reason is unconfirmed.

## Evidence

| Evidence | Result | Who |
|---|---|---|
| K1 on base and HEAD | 17 FAIL + fatal, identical sets | parent |
| Probe kept open (container copy, test suite) | PHP 8.2: 1/199 fail (the proc_open one); PHP 8.5: 199/199 pass | Oracle, mission `7546dc80` |
| `/proc/<pid>/fd` during the suite | `educators.db-wal (deleted)`, `-shm (deleted)` | Oracle |
| `.pi/research/d28/wal_lock_repro.php`, 3 runs in K1 (PHP 8.2.35, SQLite 3.40.1) | shipped pattern: WAL deleted by the other process, writer sees 2 rows, a fresh process sees **1**; control (probe kept): WAL kept, both see 2 | parent |

**What would falsify it:** the repro showing consistent counts with the probe closed, or a station
whose SQLite build does not use POSIX locks (e.g. compiled with a different VFS).

**Unverified:** field frequency; the station's PHP version (assumed 8.2, Raspberry Pi OS bookworm,
not checked on `birdpic`); whether `birds.db` code has a similar probe pattern (not searched).

## Reproduce

```bash
# Linux, php-cli + php-sqlite3. From this repo with the K1 image:
tr -d '\r' < .pi/research/d28/wal_lock_repro.php \
  | docker run --rm -i avian-k1:local bash -c 'cat > /tmp/r.php && php /tmp/r.php'
```

Expected output (abridged):

```text
shipped (probe closed): {"wal_after_other_close":false,…,"writer_sees":2,"other_process_sees":"1"}
control (probe kept)  : {"wal_after_other_close":true,…,"writer_sees":2,"other_process_sees":"2"}
```

## Draft issue for the parent repo

Not filed. Filing is outward-facing and needs the operator (D28). Before filing: confirm the
station's PHP version, and paste the script inline (the `.pi/` path does not exist upstream).

> **Title:** Educators store: `educator_store_open()` drops SQLite's POSIX locks by closing its probe handle (Linux)
>
> **Summary.** `educator_store_open()` in `avian/api/educator-store.php` opens a probe handle with
> `fopen($path, 'r+')` (line 263), opens the SQLite connection, sets WAL mode, then closes the probe
> with `fclose($probe)` (line 321) while the connection stays open. On Linux, closing any descriptor
> for a file releases all of the process's POSIX advisory locks on it, including the shared lock
> SQLite holds for a WAL connection. Another connection that closes can then checkpoint and delete
> `educators.db-wal`/`-shm` under the live connection.
>
> **Impact.** In a standalone reproduction (PHP 8.2.35, SQLite 3.40.1, Debian bookworm) a write made
> after the probe is closed is invisible to other processes once a second process opens and closes
> the database. `tests/test_educator_backend.php` fails on Linux for the same reason (17 failures,
> then `educator scope is unavailable` / `disk I/O error`). It passes 199/199 on PHP 8.5 when the
> probe is kept open. In production, `educators.lock` serialises writers, so the field impact is
> probably limited to overlapping readers (possible 503s); we have not measured it. Windows is not
> affected (per-handle locks), and CI does not run this suite, which may explain why it was not seen.
>
> **Reproduction.** *(paste `wal_lock_repro.php`)* Output with the probe closed: the WAL is deleted
> and a fresh process sees 1 row while the writer sees 2. With the probe kept open: both see 2.
>
> **Possible fixes (maintainer's call).** Keep the probe open for the connection's lifetime (e.g.
> return or store it with the connection and close it after `$db->close()`), or replace the
> `fopen`/`fstat` identity check with `lstat`/`stat` comparisons that do not open the file.
>
> **Also noticed.** On PHP 8.2 the check "scoped tar reports process startup failure…" fails: with
> a missing tar binary, `proc_open` returns a process and `avian/api/export.php` answers 409 instead of 503.
> Harmless (no bytes sent); the test may need to accept either status on PHP < 8.x.
