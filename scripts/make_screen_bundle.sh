#!/bin/bash
# Builds the small download for the screen board: screen_board_bundle/wm-screen-board.tar.gz (about 0.5 MB instead of the whole repo).
# It holds only the files scripts/screen_board.sh reads. Same bytes every time (sorted, fixed dates), so "git diff" shows real changes only.
#   bash scripts/make_screen_bundle.sh            rebuild the bundle (run it, then commit it, whenever one of these files changes)
#   bash scripts/make_screen_bundle.sh --check    exit 1 when the committed bundle is out of date
set -eu
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$ROOT/screen_board_bundle/wm-screen-board.tar.gz"
cd "$ROOT"
FILES="$( { printf '%s\n' scripts/screen_board.sh scripts/lib_free_space.sh scripts/screen_board_inspect.sh scripts/screen_board_precheck.sh \
    config/pins/addons.txt VERSION CHANGELOG.md; find zr_tools screen_rescue usb_flags -type f ! -name '*.pyc' ! -path '*__pycache__*'; } | LC_ALL=C sort )"
TMP="$(mktemp)"; trap 'rm -f "$TMP"' EXIT
# shellcheck disable=SC2086
echo "$FILES" | tar --sort=name --mtime='2020-01-01 00:00:00' --owner=0 --group=0 --numeric-owner --mode=u+rwX,go+rX,go-w -cf - -T - | gzip -n -9 > "$TMP"
if [ "${1:-}" = "--check" ]; then
    [ -f "$OUT" ] && cmp -s "$TMP" "$OUT" && { echo "screen bundle is up to date"; exit 0; }
    echo "screen bundle is OUT OF DATE: run bash scripts/make_screen_bundle.sh and commit it"; exit 1
fi
mkdir -p "$(dirname "$OUT")"; cp "$TMP" "$OUT"
echo "built $OUT ($(wc -c < "$OUT") bytes, $(echo "$FILES" | wc -l) files)"
