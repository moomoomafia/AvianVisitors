<?php
// R3 (a): execute the claim that recentWindow(hours=24) always clamps a today-window to the
// station's midnight, using the parent's real function in library mode (as its own tests do).
// Run from the repo root:  php -d extension=sqlite3 .pi/research/r3/clamp_check.php
declare(strict_types=1);

define('AVIAN_BIRDNET_API_LIBRARY_ONLY', true);
require dirname(__DIR__, 3) . '/avian/api/birdnet-api.php';

$checks = 0;
$fail = 0;
function check(bool $ok, string $what): void {
    global $checks, $fail;
    $checks++;
    if (!$ok) { $fail++; fwrite(STDERR, "FAIL: {$what}\n"); }
}
function countRows(SQLite3 $db, array $window): int {
    $st = $db->prepare('SELECT COUNT(*) AS n FROM detections WHERE ' . $window['where']);
    foreach ($window['bind'] as $k => $v) $st->bindValue($k, $v, SQLITE3_TEXT);
    return (int)($st->execute()->fetchArray(SQLITE3_ASSOC)['n'] ?? 0);
}

$db = new SQLite3(':memory:');

// 1. hours=24, reset on, today: clamped to that day's 00:00:00 at every time of day,
//    including both edges and a US DST-change date (2026-03-08) and a leap day.
$anchors = [
    '2026-09-02 00:00:00', '2026-09-02 00:00:01', '2026-09-02 06:30:00',
    '2026-09-02 12:00:00', '2026-09-02 23:59:59',
    '2026-03-08 12:00:00', '2026-11-01 01:30:00', '2028-02-29 23:59:59',
];
foreach ($anchors as $anchor) {
    $w = recentWindow($db, 24, ['anchor' => $anchor, 'is_today' => true], true, false);
    $day = substr($anchor, 0, 10);
    check($w['midnight_clamped'] === true, "24h clamps at {$anchor}");
    check($w['window_start'] === "{$day} 00:00:00", "24h window_start is {$day} 00:00:00 at {$anchor} (got {$w['window_start']})");
    check($w['reset_at_midnight'] === true, "echo field true at {$anchor}");
}

// 2. Contrast cases that show WHY the frame must send hours=24 (decision D13):
$noon = ['anchor' => '2026-09-02 15:30:00', 'is_today' => true];
$short = recentWindow($db, 12, $noon, true, false);
check($short['midnight_clamped'] === false, 'hours=12 at 15:30 is NOT clamped (rolling start inside today)');
$all = recentWindow($db, 1000000, $noon, true, false);
check($all['midnight_clamped'] === false && $all['window_start'] === null, 'hours=ALL is never clamped');
$off = recentWindow($db, 24, $noon, false, false);
check($off['midnight_clamped'] === false, 'reset off: 24h stays rolling');
$scoped = recentWindow($db, 24, $noon, true, true);
check($scoped['midnight_clamped'] === false && $scoped['reset_at_midnight'] === false, 'educator scope ignores reset (D15 path)');

// 3. Rows: yesterday excluded, midnight included, the anchor ceiling excludes "future" rows.
$db->exec('CREATE TABLE detections (Date TEXT NOT NULL, Time TEXT NOT NULL)');
$db->exec("INSERT INTO detections VALUES
    ('2026-09-01','23:59:59'),   -- yesterday: excluded
    ('2026-09-02','00:00:00'),   -- exactly midnight: included (>=)
    ('2026-09-02','15:30:00'),   -- exactly the anchor: included (<=)
    ('2026-09-02','15:30:01')    -- after the anchor (clock skew / future row): excluded");
$w = recentWindow($db, 24, $noon, true, false);
check(countRows($db, $w) === 2, 'clamped 24h window returns exactly midnight..anchor rows (2)');
// Contrast: with reset OFF the rolling 24h window (2026-09-01 15:30 .. 2026-09-02 15:30] keeps
// yesterday's 23:59:59 bird as well — exactly the day-mixing the feature exists to prevent.
$rolling = recentWindow($db, 24, $noon, false, false);
check(countRows($db, $rolling) === 3, 'rolling 24h (reset off) includes yesterday 23:59:59 + midnight + anchor (3)');

echo "R3 clamp checks: {$checks} run, {$fail} failed\n";
exit($fail ? 1 : 0);
