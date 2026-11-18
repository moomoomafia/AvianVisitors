<?php
// W1 post-review probe (2026-11-17): drive the real `recent` endpoint with W1's param.
// Usage: php .pi/research/w1/recent_param_probe.php <repo-root>   (needs PHP_INI_SCAN_DIR for SQLite3)
// Discriminating: passes on the W1 commit, fails 3 checks on base 5950f807 (git archive into a temp dir).
declare(strict_types=1);
$repo = $argv[1];
$api = $repo . '/avian/api/birdnet-api.php';
define('AVIAN_EDUCATOR_STORE_LIBRARY_ONLY', true);
require_once $repo . '/avian/api/educator-scope.php';

$tmp = sys_get_temp_dir() . '/w1probe-' . bin2hex(random_bytes(4));
mkdir($tmp . '/educators', 0700, true);
file_put_contents($tmp . '/educators.lock', '');
file_put_contents($tmp . '/educators.state', "v1\t1\t7\n");
$birdsPath = $tmp . '/birds.db';
foreach ([
    'AV_EDUCATOR_STORE_FILE' => $tmp . '/educators/educators.db',
    'AV_EDUCATOR_LOCK_FILE' => $tmp . '/educators.lock',
    'AV_EDUCATOR_STATE_FILE' => $tmp . '/educators.state',
    'AV_EDUCATOR_MAINTENANCE_FILE' => $tmp . '/educators.maintenance',
    'AV_EDUCATOR_BIRDS_DB' => $birdsPath,
    'AV_EDUCATOR_STORE_TEST_METADATA' => '1',
    'AV_EDUCATOR_STATE_TEST_METADATA' => '1',
    'AV_REQUIRE_AUTH' => '0',
] as $k => $v) putenv("$k=$v");

$db = new SQLite3($birdsPath);
$db->exec('CREATE TABLE detections(Date TEXT,Time TEXT,Sci_Name TEXT NOT NULL,Com_Name TEXT NOT NULL,'
    . 'Confidence REAL,Lat REAL,Lon REAL,Cutoff REAL,Week INTEGER,Sens REAL,Overlap REAL,File_Name TEXT NOT NULL);'
    . 'CREATE TABLE avian_metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL) WITHOUT ROWID;');
$db->exec("INSERT INTO avian_metadata VALUES('educator_generation','" . str_repeat('a', 32) . "')");
$db->exec('CREATE TABLE ' . AVIAN_DETECTION_SEQUENCE_TABLE
    . ' (sequence INTEGER PRIMARY KEY AUTOINCREMENT, detection_rowid INTEGER NOT NULL UNIQUE)');
foreach (['insert', 'delete', 'update'] as $a) $db->exec(educator_detection_sequence_trigger_sql($a));
// yesterday 23:59:00 (inside rolling 24h, outside today) and one minute ago (today)
$now = $db->querySingle("SELECT DATETIME('now','localtime')");
if (substr($now, 11, 5) < '00:02') { fwrite(STDERR, "too close to midnight; rerun\n"); exit(2); }
$db->exec("INSERT INTO detections(Date,Time,Sci_Name,Com_Name,Confidence,File_Name) VALUES"
    . "(DATE('now','localtime','-1 day'),'23:59:00','Avis hesterna','Yesterday Bird',0.9,'y.mp3'),"
    . "(DATE('now','localtime'),TIME('now','localtime','-1 minute'),'Avis hodierna','Today Bird',0.9,'t.mp3')");
$db->close(); $store = educator_store_open(true); $store->close();

function call(string $api, array $get): array {
    $server = ['REQUEST_METHOD' => 'GET', 'REMOTE_ADDR' => '203.0.113.40', 'HTTP_HOST' => 'birds.example.com'];
    $code = '$_GET=' . var_export($get, true) . ';$_SERVER=' . var_export($server, true) . ';'
        . 'include ' . var_export($api, true) . ';';
    $p = proc_open([PHP_BINARY, '-d', 'display_errors=0', '-r', $code], [1 => ['pipe', 'w'], 2 => ['pipe', 'w']], $pipes);
    $out = stream_get_contents($pipes[1]); $err = stream_get_contents($pipes[2]); proc_close($p);
    if ($err !== '') fwrite(STDERR, "stderr: " . trim($err) . "\n");
    return json_decode((string)$out, true) ?? ['raw' => $out];
}
$fail = 0;
function chk(bool $ok, string $what): void { global $fail; if (!$ok) $fail++; echo ($ok ? '  ok  ' : 'FAIL  ') . $what . "\n"; }
$names = fn(array $r) => implode(',', array_column($r['species'] ?? [], 'sci'));

$base = ['action' => 'recent', 'hours' => '24'];
$off = call($api, $base);
chk(($off['midnight_clamped'] ?? null) === false && $names($off) === 'Avis hodierna,Avis hesterna', 'no param: rolling 24h incl. yesterday [' . $names($off) . ']');
chk(($off['reset_at_midnight'] ?? null) === false, 'no param: reset_at_midnight echo false');
$on = call($api, $base + ['reset_at_midnight' => '1']);
chk(($on['midnight_clamped'] ?? null) === true && $names($on) === 'Avis hodierna', '=1: clamped to today only [' . $names($on) . ']');
chk(($on['reset_at_midnight'] ?? null) === true && is_string($on['window_start'] ?? null) && substr($on['window_start'], 11) === '00:00:00', '=1: echo true, window_start at midnight ' . ($on['window_start'] ?? 'null'));
foreach (['0', 'true', '01'] as $v) {
    $r = call($api, $base + ['reset_at_midnight' => $v]);
    chk(($r['midnight_clamped'] ?? null) === false && $names($r) === $names($off), "=$v: ignored");
}
$arr = call($api, $base + ['reset_at_midnight' => ['1']]);
chk(($arr['midnight_clamped'] ?? null) === false && $names($arr) === $names($off), 'array value: ignored, no error');
$h72 = call($api, ['action' => 'recent', 'hours' => '72', 'reset_at_midnight' => '1']);
chk(($h72['midnight_clamped'] ?? null) === true && $names($h72) === 'Avis hodierna', 'hours=72 + =1: still clamped (D13: reset ignores hours)');
$all = call($api, ['action' => 'recent', 'hours' => '1000000', 'reset_at_midnight' => '1']);
chk(($all['midnight_clamped'] ?? null) === false, 'hours=1000000 (ALL) + =1: not clamped (upstream parity)');
$st0 = call($api, ['action' => 'stats']);
$st1 = call($api, ['action' => 'stats', 'reset_at_midnight' => '1']);
unset($st0['as_of'], $st1['as_of'], $st0['anchor'], $st1['anchor']); // both carry the current second
chk($st0 === $st1 && !isset($st0['raw']), 'stats: identical with and without the param');
echo $fail === 0 ? "probe: all passed\n" : "probe: $fail failed\n";
exit($fail ? 1 : 0);
