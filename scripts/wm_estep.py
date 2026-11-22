#!/usr/bin/env python3
# wm_estep.py T NEW OLD  (run by RUN_SHELL_COMMAND CMD=wm_estep, from rpi_estep.cfg)
# Writes the new rotation_distance of tool T (0 to 3) into its extruder section of printer.cfg (or the file it includes
# that holds the section) and keeps the old value behind it:
#       rotation_distance: 21.018 # old value 22.127
# Any other comment at the end of that line is replaced. Only that one line changes. A backup of the file is made first.
# Only lines above the SAVE_CONFIG block are touched. OLD must be what the file holds now, else nothing is written.
# Klipper uses the new value after a restart.
import glob
import os
import re
import shutil
import sys
import time

CFG = os.environ.get("WM_ESTEP_CFG", os.path.expanduser("~/printer_data/config/printer.cfg"))
SAVE_MARK = re.compile(r"^#\*# <-+ SAVE_CONFIG")
LINE = re.compile(r"^(rotation_distance)(\s*[:=]\s*)([^#;\r\n]*?)([ \t]*)((?:[#;].*?)?)(\r?\n?)$")


def out(msg):
    print("E-step: " + msg, flush=True)


def fmt(x):
    return ("%.3f" % x).rstrip("0").rstrip(".") if "." in ("%.3f" % x) else "%.3f" % x


def include_files(path, depth=0, seen=None):
    """The file itself first, then the files it includes (in file order)."""
    seen = set() if seen is None else seen
    path = os.path.realpath(path)
    if path in seen or depth > 6 or not os.path.isfile(path):
        return []
    seen.add(path)
    found = [path]
    base = os.path.dirname(path)
    with open(path, newline="") as f:
        for line in f:
            if SAVE_MARK.match(line):
                break
            m = re.match(r"^\[include\s+([^\]]+?)\s*\]", line)
            if m:
                pattern = m.group(1).strip()
                if not os.path.isabs(pattern):
                    pattern = os.path.join(base, pattern)
                for p in sorted(glob.glob(pattern)):
                    for q in include_files(p, depth + 1, seen):
                        if q not in found:
                            found.append(q)
    return found


def find_line(path, section):
    """(index, lines, match) of rotation_distance in [section], or None. Lines below SAVE_CONFIG are ignored."""
    with open(path, newline="") as f:
        lines = f.read().splitlines(keepends=True)
    sec = None
    for i, line in enumerate(lines):
        if SAVE_MARK.match(line):
            break
        m = re.match(r"^\[([^\]]+)\]", line)
        if m:
            sec = m.group(1).strip().lower()
            continue
        if sec == section:
            m = LINE.match(line)
            if m:
                return i, lines, m
    return None


def main():
    if len(sys.argv) != 4:
        out("FAILED, T NEW OLD are needed. Nothing changed.")
        return 1
    try:
        t = int(sys.argv[1])
        new = float(sys.argv[2])
        old = float(sys.argv[3])
    except ValueError:
        out("FAILED, the values are not numbers. Nothing changed.")
        return 1
    if not (0 <= t <= 3):
        out("FAILED, T must be 0 to 3. Nothing changed.")
        return 1
    if old <= 0 or new <= 0 or not (old * 0.5 <= new <= old * 1.5):
        out("FAILED, the new value %s is not within 50 percent of the old value %s. Nothing changed." % (fmt(new), fmt(old)))
        return 1
    section = "extruder" if t == 0 else "extruder%d" % t
    hit = None
    for path in include_files(CFG):
        hit = find_line(path, section)
        if hit:
            break
    if not hit:
        out("FAILED, rotation_distance not found in [%s] above the SAVE_CONFIG block of printer.cfg or the files it "
            "includes. Nothing changed." % section)
        return 1
    i, lines, m = hit
    try:
        in_file = float(m.group(3))
    except ValueError:
        out("FAILED, the value in [%s] (%s) is not a number. Nothing changed." % (section, m.group(3).strip()))
        return 1
    if abs(in_file - old) > 0.0005:
        out("FAILED, [%s] holds %s now, not %s. The file was changed during the test. Nothing changed."
            % (section, m.group(3).strip(), fmt(old)))
        return 1
    old_text = m.group(3).strip()
    nl = m.group(6) or "\n"
    lines[i] = "%s%s%s # old value %s%s" % (m.group(1), m.group(2), "%.3f" % new, old_text, nl)
    target = path
    bakdir = os.path.join(os.path.dirname(target), "backup")   # F-157: backups go in the backup folder, not next to printer.cfg
    os.makedirs(bakdir, exist_ok=True)
    bak = os.path.join(bakdir, os.path.basename(target) + ".wm-before-estep-" + time.strftime("%Y%m%d-%H%M%S"))
    shutil.copy2(target, bak)
    tmp = target + ".wm-tmp"
    with open(tmp, "w", newline="") as f:
        f.write("".join(lines))
    shutil.copymode(target, tmp)
    os.replace(tmp, target)
    extra = ""
    if m.group(5).strip():
        extra = " The comment that was on that line (%s) was replaced." % m.group(5).strip()
    out("saved [%s] rotation_distance %s (was %s) in %s.%s Backup %s. Restart Klipper to use it."
        % (section, "%.3f" % new, old_text, os.path.basename(target), extra, "backup/" + os.path.basename(bak)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
