#!/bin/bash
# wm_sv_guard.sh  backup | restore
# Keeps ONE good copy of saved_variables.cfg and puts it back when the live file comes up empty.
# Why: Klipper (and the ACE driver) rewrite saved_variables.cfg by wiping it first and then writing it. A power cut in that moment
# leaves an empty file, and Klipper then starts with no tool offsets or calibration. The installer runs "restore" just before Klipper
# starts, "backup" after Klipper stops and every 10 minutes (wm-sv-guard.timer). The log is ~/printer_data/logs/wm_sv_guard.log.
F="${HOME}/printer_data/config/saved_variables.cfg"
G="$F.wm-good"
LOG="${HOME}/printer_data/logs/wm_sv_guard.log"
healthy() {   # a real file: over 1000 bytes and holding WonderMaker's tool position and tool map
    [ -f "$1" ] && [ "$(stat -c %s "$1")" -gt 1000 ] && grep -q "^t0_position" "$1" && grep -q "^box_modify_t0 " "$1"
}
say() { mkdir -p "$(dirname "$LOG")" 2>/dev/null; echo "$(date "+%F %T") $*" >> "$LOG"; }
# the install, the 10-minute timer and Klipper's stop can overlap: one run at a time, and a temp name of its own
LOCK="${HOME}/printer_data/.wm_sv_guard.lock"
if command -v flock >/dev/null 2>&1; then exec 9>"$LOCK" && flock -w 30 9; fi
case "${1:-}" in
  backup)
    healthy "$F" || { say "backup skipped: live file not healthy"; exit 0; }
    cmp -s "$F" "$G" && exit 0
    T="$(mktemp "$G.tmp.XXXXXX")" || { say "backup failed: no temp file"; exit 0; }
    if cp "$F" "$T" && healthy "$T"; then mv -f "$T" "$G" && sync && say "backup saved"; else rm -f "$T"; say "backup failed"; fi
    ;;
  restore)
    healthy "$F" && exit 0
    if healthy "$G"; then
        [ -f "$F" ] && cp "$F" "$F.wm-bad-$(date +%H%M%S)" 2>/dev/null
        cp "$G" "$F" && sync && say "RESTORED live file from the good copy (the live file was not healthy)"
    else
        say "live file not healthy and there is no good copy"
    fi
    ;;
  *) echo "usage: $0 backup|restore"; exit 1 ;;
esac
