#!/usr/bin/env python3
# wm_speed_limits.py ACCEL VELOCITY  (WonderMaker, F-050, run by RUN_SHELL_COMMAND CMD=wm_speed_limits)
# Writes max_accel and max_velocity into the [printer] section of printer.cfg. Makes a backup first.
# Only lines above the SAVE_CONFIG block are touched, nothing else in the file changes.
import os
import re
import shutil
import sys
import time

CFG = os.path.expanduser("~/printer_data/config/printer.cfg")


def out(msg):
    print("Speed limits: " + msg, flush=True)


def main():
    if len(sys.argv) != 3:
        out("FAILED, ACCEL and VELOCITY are needed. Nothing changed.")
        return 1
    try:
        a = int(float(sys.argv[1]))
        v = int(float(sys.argv[2]))
    except ValueError:
        out("FAILED, the values are not numbers. Nothing changed.")
        return 1
    if not (500 <= a <= 30000) or not (50 <= v <= 1200):
        out("FAILED, ACCEL must be 500 to 30000 and VELOCITY 50 to 1200. Nothing changed.")
        return 1
    with open(CFG, newline="") as f:
        lines = f.read().splitlines(keepends=True)
    sec = None
    done = {}
    pat = re.compile(r"^(max_accel|max_velocity)(\s*[:=]\s*)([^#;\r\n]*?)(\s*(?:[#;].*?)?)(\r?\n?)$")
    for i, line in enumerate(lines):
        if line.startswith("#*# <---- SAVE_CONFIG"):
            break
        m = re.match(r"^\[([^\]]+)\]", line)
        if m:
            sec = m.group(1).strip().lower()
            continue
        if sec != "printer":
            continue
        m = pat.match(line)
        if m and m.group(1) not in done:
            new = str(a if m.group(1) == "max_accel" else v)
            done[m.group(1)] = (m.group(3).strip(), new)
            lines[i] = m.group(1) + m.group(2) + new + m.group(4) + m.group(5)
    if set(done) != {"max_accel", "max_velocity"}:
        out("FAILED, max_accel or max_velocity not found in [printer]. Nothing changed.")
        return 1
    bak = CFG + ".wm-before-autospeed-" + time.strftime("%Y%m%d-%H%M%S")
    shutil.copy2(CFG, bak)
    tmp = CFG + ".wm-tmp"
    with open(tmp, "w", newline="") as f:
        f.write("".join(lines))
    os.replace(tmp, CFG)
    out("saved max_accel %s (was %s) and max_velocity %s (was %s). Backup %s. Restart Klipper to use them."
        % (done["max_accel"][1], done["max_accel"][0], done["max_velocity"][1], done["max_velocity"][0],
           os.path.basename(bak)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
