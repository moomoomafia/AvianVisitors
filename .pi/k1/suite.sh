#!/bin/bash
# K1 suite: runs inside the container on an LF tree extracted to /src.
# Every named suite is run; a skip counts as not-passed (no vacuous green).
set -u
cd /src || exit 2
results=()
overall=0

record() { # name status detail
  results+=("$(printf '%-52s %-5s %s' "$1" "$2" "$3")")
  [ "$2" = PASS ] || overall=1
}

run_php() { # name, args...
  local name=$1; shift
  local out rc
  out=$(php "$@" 2>&1); rc=$?
  printf '\n===== %s (exit %s)\n%s\n' "$name" "$rc" "$(printf '%s\n' "$out" | tail -40)"
  local tail1; tail1=$(printf '%s\n' "$out" | grep -v '^\s*$' | tail -1)
  if [ $rc -eq 0 ]; then record "$name" PASS "$tail1"; else record "$name" FAIL "exit $rc: $tail1"; fi
}

run_pytest() { # file
  local f=$1 out rc summary
  out=$(python -m pytest -q -rs -p no:cacheprovider "$f" 2>&1); rc=$?
  printf '\n===== pytest %s (exit %s)\n%s\n' "$f" "$rc" "$(printf '%s\n' "$out" | tail -60)"
  summary=$(printf '%s\n' "$out" | grep -E '[0-9]+ (passed|failed|error|skipped)|no tests ran' | tail -1)
  if [ $rc -eq 0 ] && ! printf '%s' "$summary" | grep -q skipped; then
    record "pytest $f" PASS "$summary"
  elif [ $rc -eq 0 ]; then
    record "pytest $f" SKIP "$summary"
  else
    record "pytest $f" FAIL "exit $rc: $summary"
  fi
}

echo "K1 suite: $(php -r 'echo PHP_VERSION;') / $(python --version 2>&1) / $(id -un)"

run_php "php -l avian/api/birdnet-api.php" -l avian/api/birdnet-api.php
run_php "php tests/test_midnight_reset.php" tests/test_midnight_reset.php
run_php "php tests/test_site_name_api.php" tests/test_site_name_api.php
# test_educator_backend.php fails on Linux on the parent's base too (store fclose drops SQLite's
# POSIX locks; PHP 8.2 proc_open): see verification-log "K1 build and baseline". Gate it as an
# A/B: PASS = its FAIL lines + fatal are exactly the recorded base-5950f807 set.
edu=$(php tests/test_educator_backend.php 2>&1); edu_rc=$?
printf '\n===== php tests/test_educator_backend.php (exit %s)\n%s\n' "$edu_rc" "$(printf '%s\n' "$edu" | tail -40)"
edu_set=$(printf '%s\n' "$edu" | grep -E '^FAIL:|^PHP Fatal error')
if [ $edu_rc -eq 0 ]; then
  record "php tests/test_educator_backend.php" PASS "$(printf '%s\n' "$edu" | tail -1)"
elif [ -f .pi/k1/educator-backend.baseline ] && [ "$edu_set" = "$(cat .pi/k1/educator-backend.baseline)" ]; then
  record "php tests/test_educator_backend.php (A/B)" PASS "same $(printf '%s\n' "$edu_set" | wc -l) known lines as base"
elif [ -f .pi/k1/educator-backend.baseline ]; then
  record "php tests/test_educator_backend.php (A/B)" FAIL "differs from base: $(diff <(cat .pi/k1/educator-backend.baseline) <(printf '%s\n' "$edu_set") | grep -c '^[<>]') changed lines"
else
  record "php tests/test_educator_backend.php" BASE "exit $edu_rc, $(printf '%s\n' "$edu_set" | wc -l) FAIL/fatal lines (no baseline file in this ref)"
fi

for f in tests/test_midnight_reset.py tests/test_frame_capture.py tests/test_frame_birdweather.py \
         tests/test_frame_capture_browser.py tests/test_educator_security.py frame/test_bundle_runtime.py; do
  run_pytest "$f"
done

# .pi/ research checks exist only on refs that carry them (HEAD, not base).
[ -f .pi/research/w1/recent_param_probe.php ] && run_php "php .pi/research/w1/recent_param_probe.php" .pi/research/w1/recent_param_probe.php /src
[ -f .pi/research/r3/clamp_check.php ] && run_php "php .pi/research/r3/clamp_check.php" .pi/research/r3/clamp_check.php
[ -f .pi/research/pre-v03/test_characterize_today.py ] && run_pytest .pi/research/pre-v03/test_characterize_today.py

out=$(python -m flake8 --select=E9,F63,F7,F82 --count frame tests 2>&1); rc=$?
printf '\n===== flake8 fatal set (exit %s)\n%s\n' "$rc" "$out"
if [ $rc -eq 0 ]; then record "flake8 E9,F63,F7,F82 frame tests" PASS "$(printf '%s' "$out" | tail -1)"; else record "flake8 E9,F63,F7,F82 frame tests" FAIL "$(printf '%s' "$out" | tail -1)"; fi

printf '\n===== K1 SUMMARY\n'
printf '%s\n' "${results[@]}"
exit $overall
