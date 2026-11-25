#!/bin/bash
# Quick checks, about one minute. Run after every edit, before the long suite:   bash tools/quick_check.sh
# Read-only: it changes nothing in the repository. Exit 1 when a check fails.
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT"
PASS=0; FAIL=0; W="$(mktemp -d)"; trap 'rm -rf "$W"' EXIT
qc() {  # name, command
    if eval "$2" >"$W/out" 2>&1; then PASS=$((PASS+1)); echo "  ok   $1"
    else FAIL=$((FAIL+1)); echo "  FAIL $1"; tail -n 6 "$W/out" | sed 's/^/        /'; fi; }
echo "== quick check ($(head -n1 VERSION), screen $(head -n1 SCREEN_VERSION))"
qc "shell scripts: syntax" "for f in installer.sh scripts/*.sh tests/run_tests.sh tools/quick_check.sh screen_rescue/wm-screen-rescue screen_rescue/wm-screen-mode; do bash -n \$f || exit 1; done"
qc "python files: syntax" "python3 -I -c \"import ast,glob,sys
for f in glob.glob('scripts/*.py')+glob.glob('zr_tools/*.py')+glob.glob('tools/*.py')+glob.glob('screen_rescue/*.py')+glob.glob('tests/*.py'):
    ast.parse(open(f, encoding='utf-8', errors='replace').read(), f)\""
qc "json files: valid" "python3 -I -c \"import json; json.load(open('scripts/wm_macro_patches.json')); json.load(open('zr_tools/ks_wm_patches.json'))\""
qc "version numbers: VERSION is x.y.z, SCREEN_VERSION is Sx.y.z, and the first CHANGELOG entry is this VERSION" "grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+$' VERSION && grep -Eq '^S[0-9]+\.[0-9]+\.[0-9]+$' SCREEN_VERSION && [ \"\$(grep -m1 '^## ' CHANGELOG.md)\" = \"## \$(head -n1 VERSION)\" ]"
qc "macro index: rpi-cfg and zr_tools.cfg carry an up-to-date index (fix: python3 scripts/wm_cfg_index.py file rpi-cfg/*.cfg zr_tools/zr_tools.cfg)" "mkdir -p $W/idx && cp rpi-cfg/rpi_base.cfg rpi-cfg/rpi_calibration.cfg rpi-cfg/rpi_nozzle.cfg zr_tools/zr_tools.cfg $W/idx/ && python3 -I scripts/wm_cfg_index.py file $W/idx/*.cfg >/dev/null; for f in rpi_base.cfg rpi_calibration.cfg rpi_nozzle.cfg; do cmp -s $W/idx/\$f rpi-cfg/\$f || { echo \"stale index: \$f\"; exit 1; }; done; cmp -s $W/idx/zr_tools.cfg zr_tools/zr_tools.cfg || { echo 'stale index: zr_tools.cfg'; exit 1; }"
qc "macro patch list: up to date with the factory files (same check as the suite)" "c=\$(grep -o 'tools/make_macro_patches.py [0-9a-f]* [0-9.]* --check' tests/run_tests.sh | head -n1); [ -n \"\$c\" ] && { [ ! -d .git ] || python3 \$c; }"
qc "screen bundle: up to date (fix: bash scripts/make_screen_bundle.sh)" "bash scripts/make_screen_bundle.sh --check"
qc "screen python tests" "python3 -I -W ignore tests/test_screen.py"
qc "no private addresses in repo files" "! grep -rIlE '10\.11\.88\.|192\.168\.1\.' . --exclude-dir=.git --exclude-dir=klipper --exclude-dir=moonraker --exclude=*.patch"
if [ -d .git ] && [ -n "$(git status --porcelain -- factory 2>/dev/null)" ]; then
    echo "  NOTE factory/ has uncommitted changes. Commit them before the long suite: the installer's repair step puts factory/ back to the last commit inside the test copy."
fi
echo; echo "quick check: passed $PASS  failed $FAIL"; [ "$FAIL" = 0 ]
