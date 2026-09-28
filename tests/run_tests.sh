#!/usr/bin/env bash
# Runs the full Cinderbound test-suite. Usage:  GODOT=/path/to/godot tests/run_tests.sh
# UI flow tests click through the real menus; they run headless, or visibly if DISPLAY is set.
set -u
GODOT="${GODOT:-godot}"
cd "$(dirname "$0")/.."
fail=0
run() { echo "=== $1"; shift; timeout 600 "$@" 2>&1 | grep -E "PASS|FAIL|checks passed|SELFTEST|checked|L[0-9]" ; [ "${PIPESTATUS[0]}" -eq 0 ] || fail=1; }
"$GODOT" --headless --import >/dev/null 2>&1
run "script compile check" "$GODOT" --headless res://tests/check_scripts.tscn
run "rules / save / progression tests" "$GODOT" --headless res://tests/logic_tests.tscn
run "data self-test" "$GODOT" --headless -- --selftest
for starter in kael_emberclaw mira_tidesong thorne_mossguard; do
  run "milestone flow part 1 ($starter)" "$GODOT" --headless res://tests/ui_flow.tscn -- --phase=1 --starter=$starter
  run "milestone flow part 2 - reopen + continue ($starter)" "$GODOT" --headless res://tests/ui_flow.tscn -- --phase=2 --starter=$starter
done
run "settings + corrupted save UI" "$GODOT" --headless res://tests/ui_flow.tscn -- --phase=3
run "phase 4 player flow (unlocks, summon, train, evolve, tower, missions, world 2)" "$GODOT" --headless res://tests/ui_flow.tscn -- --phase=4
echo "=== balance simulation (informational)"
timeout 900 "$GODOT" --headless res://tests/balance_sim.tscn 2>&1 | grep -E "^[a-z_]+ |^   "
[ $fail -eq 0 ] && echo "ALL TESTS PASSED" || echo "SOME TESTS FAILED"
exit $fail
