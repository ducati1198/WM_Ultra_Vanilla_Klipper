#!/bin/bash
# Fast test, about 6-8 minutes (the full suite takes about 37). Run before a commit, after the 1-minute quick check passes.
#   bash tools/test_fast.sh
# 1) tools/quick_check.sh  2) every tests/test_*.py  3) the suite sections for backup, restore, repair, update, undo and the
# saved_variables safeguard, with the sections they need. Sections that are only needed are not counted. The full suite stays the last word.
# The suite part runs in a copy; the repository is not changed.
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT"
OWN="${WM_FAST_SECTIONS:-2,23,37,38,55}"   # 2 saved_variables safeguard, 23 check-updates and zr_tools backup, 37 backup/restore, 38 repair/update/undo, 55 backup before update
T0=$(date +%s); FAIL=0; W="$(mktemp -d "$HOME/.wm-fast.XXXXXX")"; trap 'rm -rf "$W"' EXIT
echo "== fast test: 1/3 quick check"; bash tools/quick_check.sh > "$W/qc.out" 2>&1 || FAIL=1; tail -n 3 "$W/qc.out"
echo "== fast test: 2/3 python tests"
for t in tests/test_*.py; do
    if python3 -I -W ignore "$t" $([ "$t" = tests/test_f137.py ] && echo "$ROOT") >"$W/py.out" 2>&1; then echo "  ok   $t"; else echo "  FAIL $t"; tail -n 5 "$W/py.out" | sed 's/^/        /'; FAIL=1; fi
done
echo "== fast test: 3/3 suite sections $OWN (and what they need)"
ALL=$(python3 -I tools/split_suite.py closure "$OWN") || exit 1
mkdir -p "$W/c"; cp -a "$ROOT/." "$W/c/"
python3 -I tools/split_suite.py build "$W/c/tests/.shard.sh" "$ALL" "$OWN" || exit 1
WM_TESTS_IN_COPY=1 bash "$W/c/tests/.shard.sh" > "$W/suite.out" 2>&1
R=$(sed -n 's/^passed: \([0-9]*\)  failed: \([0-9]*\)$/passed \1  failed \2/p' "$W/suite.out" | tail -n1)
F=$(sed -n 's/^passed: [0-9]*  failed: \([0-9]*\)$/\1/p' "$W/suite.out" | tail -n1)
echo "  sections run: $ALL   counted: $OWN"; echo "  suite part: ${R:-no result line}"
if [ -z "$F" ] || [ "$F" != 0 ]; then FAIL=1; grep -h -A6 '^  FAIL' "$W/suite.out" | head -n 40; fi
echo; echo "fast test: $([ $FAIL = 0 ] && echo PASSED || echo FAILED) in $(( $(date +%s) - T0 )) s (commit $(git rev-parse --short HEAD 2>/dev/null))"; [ $FAIL = 0 ]
