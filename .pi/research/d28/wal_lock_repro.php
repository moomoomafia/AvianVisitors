<?php
// D28 standalone reproduction: closing a second fopen() handle on a SQLite database file
// drops the process's POSIX locks, so another process can delete the live WAL.
// Mirrors avian/api/educator-store.php educator_store_open(): probe fopen (:263), SQLite open,
// PRAGMA journal_mode = WAL (:296), then fclose($probe) (:321) while $db stays open.
// Usage (Linux, php-cli + php-sqlite3):  php wal_lock_repro.php
// Exit 0 = both modes behaved as described; output shows "shipped" vs "control".
declare(strict_types=1);

function run_mode(bool $closeProbe): array {
    $dir = sys_get_temp_dir() . '/d28-' . ($closeProbe ? 'shipped' : 'control') . '-' . getmypid();
    @mkdir($dir);
    $path = $dir . '/store.db';
    $init = new SQLite3($path);
    $init->exec('PRAGMA journal_mode = WAL');
    $init->exec('CREATE TABLE t (v INTEGER)');
    $init->close();

    // --- what educator_store_open() does ---
    $probe = fopen($path, 'r+');
    $db = new SQLite3($path, SQLITE3_OPEN_READWRITE);
    $db->busyTimeout(5000);
    $db->exec('PRAGMA journal_mode = WAL');
    $db->exec('PRAGMA synchronous = FULL');
    if ($closeProbe) fclose($probe);          // shipped behaviour (:321)
    // --------------------------------------

    $db->exec('INSERT INTO t VALUES (1)');
    $walBefore = file_exists("$path-wal");

    // A second request (another PHP process) opens and closes its own connection.
    $child = 'php -r ' . escapeshellarg('$d = new SQLite3($argv[1]); $d->busyTimeout(5000); echo $d->querySingle("SELECT count(*) FROM t"); $d->close();')
        . ' ' . escapeshellarg($path);
    shell_exec($child);
    clearstatcache();
    $walAfterOther = file_exists("$path-wal");

    // The first connection keeps working and writes again.
    $err = '';
    try { $db->exec('INSERT INTO t VALUES (2)'); } catch (Throwable $e) { $err = $e->getMessage(); }
    $selfCount = (int)@$db->querySingle('SELECT count(*) FROM t');

    // A fresh process reads what is durably visible.
    $seen = trim((string)shell_exec($child . ' 2>&1'));

    $db->close();
    if (!$closeProbe) fclose($probe);
    foreach (glob("$dir/*") as $f) @unlink($f);
    @rmdir($dir);
    return ['wal_before' => $walBefore, 'wal_after_other_close' => $walAfterOther,
            'second_insert_error' => $err, 'writer_sees' => $selfCount, 'other_process_sees' => $seen];
}

printf("PHP %s, SQLite %s, %s\n", PHP_VERSION, SQLite3::version()['versionString'], PHP_OS);
$shipped = run_mode(true);
$control = run_mode(false);
echo 'shipped (probe closed): ' . json_encode($shipped) . "\n";
echo 'control (probe kept)  : ' . json_encode($control) . "\n";
$lost = $shipped['writer_sees'] !== (int)$shipped['other_process_sees'] || $shipped['second_insert_error'] !== '';
$ok = $control['writer_sees'] === 2 && (int)$control['other_process_sees'] === 2;
echo $lost ? "RESULT: shipped pattern LOSES/ERRORS a write; " : "RESULT: shipped pattern did not lose a write; ";
echo $ok ? "control is consistent\n" : "control is NOT consistent\n";
exit($lost && $ok ? 0 : 1);
