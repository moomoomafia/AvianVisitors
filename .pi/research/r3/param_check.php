<?php
// R3 (b): execute the param-shape claims behind R1 / D3 for
//   $resetAtMidnight = $RESET_AT_MIDNIGHT || (($_GET['reset_at_midnight'] ?? null) === '1');
// Two layers: parse_str() (PHP's query parser) and, if URL R3_BASE is given, a real HTTP
// request to www/echo.php served by `php -S`, so $_GET comes from the real request parser.
declare(strict_types=1);

$checks = 0;
$fail = 0;
function check(bool $ok, string $what): void {
    global $checks, $fail;
    $checks++;
    if (!$ok) { $fail++; fwrite(STDERR, "FAIL: {$what}\n"); }
    else { echo "  ok  {$what}\n"; }
}
function flag(array $get, bool $station = false): bool {
    return $station || (($get['reset_at_midnight'] ?? null) === '1');
}

// [query string, expected with station flag OFF, label]
$cases = [
    ['', false, 'absent'],
    ['reset_at_midnight=1', true, 'canonical =1'],
    ['reset_at_midnight=%31', true, 'percent-encoded 1'],
    ['reset_at_midnight=0', false, '=0'],
    ['reset_at_midnight=', false, 'empty value'],
    ['reset_at_midnight', false, 'key without value'],
    ['reset_at_midnight=true', false, '=true'],
    ['reset_at_midnight=01', false, '=01'],
    ['reset_at_midnight=1%20', false, 'trailing space'],
    ['RESET_AT_MIDNIGHT=1', false, 'upper-case key (keys are case-sensitive)'],
    ['reset_at_midnight[]=1', false, 'array value'],
    ['reset_at_midnight[x]=1', false, 'array with key'],
    ['reset.at.midnight=1', true, 'dots mangled to underscores (PHP behaviour)'],
    ['reset%20at%20midnight=1', true, 'spaces mangled to underscores (PHP behaviour)'],
    ['reset_at_midnight=0&reset_at_midnight=1', true, 'duplicate: last wins (=1)'],
    ['reset_at_midnight=1&reset_at_midnight=0', false, 'duplicate: last wins (=0)'],
    ['hours=24&reset_at_midnight=1&action=recent', true, 'alongside the frame\'s other params'],
];

echo "== layer 1: parse_str ==\n";
foreach ($cases as [$qs, $want, $label]) {
    $get = [];
    parse_str($qs, $get);
    check(flag($get) === $want, "parse_str  {$label}  [{$qs}] -> " . var_export(flag($get), true));
}
echo "== station flag ON: the request can never switch it off ==\n";
foreach (['reset_at_midnight=0', '', 'reset_at_midnight[]=1'] as $qs) {
    $get = [];
    parse_str($qs, $get);
    check(flag($get, true) === true, "station ON + [{$qs}] stays true");
}

$base = getenv('R3_BASE');
if ($base) {
    echo "== layer 2: real HTTP request via php -S ({$base}) ==\n";
    foreach ($cases as [$qs, $want, $label]) {
        $body = @file_get_contents($base . '/echo.php' . ($qs === '' ? '' : '?' . $qs));
        $got = $body === false ? null : (json_decode($body, true)['resetAtMidnight'] ?? null);
        check($got === $want, "http       {$label}  [{$qs}] -> " . var_export($got, true));
    }
    $ctx = stream_context_create(['http' => ['header' => "X-Station-Flag: 1\r\n"]]);
    $body = @file_get_contents($base . '/echo.php?reset_at_midnight=0', false, $ctx);
    check(($body !== false) && json_decode($body, true)['resetAtMidnight'] === true, 'http station ON + =0 stays true');
} else {
    echo "== layer 2 skipped (set R3_BASE=http://127.0.0.1:PORT) ==\n";
}

echo "R3 param checks: {$checks} run, {$fail} failed\n";
exit($fail ? 1 : 0);
