#!/bin/bash
# Applies an installer update on the Pi after Fluidd's Update button downloaded it.
#
# Fluidd's update manager only runs "git pull" on this folder. The systemd unit wm-pi-update.path notices that
# (the git log of HEAD changed) and starts wm-pi-update.service, which runs this script: it runs
#   ./installer.sh --update --yes
# exactly like you would in SSH (backup first, then packages, configs, Fluidd panel, add-ons, restart of Klipper
# and Moonraker at the end). It runs from systemd, not from Moonraker, so the restart of Moonraker does not stop it.
#
# It does nothing when: the installed version already is this folder's version, a print is running or paused,
# another update is running, or the user has no passwordless sudo (then run  ./installer.sh --update  in SSH).
# Log: ~/wm-pi-update.log
# Test hooks: WM_PI_UPDATE_CMD (replaces the installer command), WM_PI_UPDATE_DELAY (seconds, default 5),
#             WM_TEST_PRINT_STATE, WM_PI_UPDATE_SKIP_SUDO=1.
set -u
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG="$HOME/wm-pi-update.log"
say() { echo "$(date '+%F %T') $*" >> "$LOG"; }

exec 9>"$HOME/.wm-pi-update.lock"
flock -n 9 || { say "another update is running, skipped"; exit 0; }
sleep "${WM_PI_UPDATE_DELAY:-5}"          # let Moonraker finish its own update step

installed="$(sed -n 's/^VERSION=//p' "$HOME/wm-rpi-backup/install.conf" 2>/dev/null | head -n1)"
new="$(tr -d '[:space:]' < "$REPO/VERSION" 2>/dev/null)"
[ -n "$new" ] || { say "no VERSION file in $REPO, skipped"; exit 0; }
if [ -z "$installed" ]; then say "nothing is installed by this installer yet, skipped"; exit 0; fi
if [ "$installed" = "$new" ]; then exit 0; fi   # nothing new (also the case after a manual ./installer.sh --update)

state="${WM_TEST_PRINT_STATE:-}"
if [ -z "$state" ]; then
    state="$(curl -fsS -m 5 'http://127.0.0.1:7125/printer/objects/query?print_stats' 2>/dev/null | python3 -c 'import sys,json
try: print(json.load(sys.stdin)["result"]["status"]["print_stats"]["state"])
except Exception: print("")' 2>/dev/null)"
fi
case "$state" in
    printing|paused) say "a print is active ($state): the update to $new was NOT applied. After the print run: ./installer.sh --update"; exit 0 ;;
esac

if [ "${WM_PI_UPDATE_SKIP_SUDO:-0}" != 1 ] && ! sudo -n true 2>/dev/null; then
    say "this user has no passwordless sudo, so the update to $new was NOT applied. Run in SSH: cd $REPO && ./installer.sh --update  (the installer can set up passwordless sudo for the screen board only)"
    exit 0
fi

say "applying the update $installed -> $new (installer --update --yes)"
if [ -n "${WM_PI_UPDATE_CMD:-}" ]; then bash -c "$WM_PI_UPDATE_CMD" >> "$LOG" 2>&1; rc=$?
else ( cd "$REPO" && bash "$REPO/installer.sh" --update --yes ) >> "$LOG" 2>&1; rc=$?; fi
say "update finished, exit code $rc"
exit 0
