<?php
// R3 (b) helper: served by `php -S` so $_GET is built by PHP's real request parser.
// Applies exactly the R1 variant B' expression, with the station flag passed in the request
// as `station` (test-only) so both OR branches can be exercised.
declare(strict_types=1);
header('Content-Type: application/json');
$RESET_AT_MIDNIGHT = ($_SERVER['HTTP_X_STATION_FLAG'] ?? '0') === '1';
$resetAtMidnight = $RESET_AT_MIDNIGHT || (($_GET['reset_at_midnight'] ?? null) === '1');
echo json_encode(['get' => $_GET, 'resetAtMidnight' => $resetAtMidnight]);
