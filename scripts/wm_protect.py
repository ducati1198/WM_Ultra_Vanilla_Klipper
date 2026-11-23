#!/usr/bin/env python3
"""wm_protect.py - keeps what belongs to the user while the installer updates (F-222).

  wm_protect.py snapshot CONFIG_DIR SNAP_DIR   copy the protected values before an update
  wm_protect.py verify   CONFIG_DIR SNAP_DIR   after the update: put back anything protected that changed
  wm_protect.py show     CONFIG_DIR            list what is protected (changes nothing)

Protected (by value, so a value the installer or Klipper adds on top stays):
  saved_variables.cfg   every "name = value" of the [Variables] section (your calibration, trims, probe position)
  printer.cfg           the SAVE_CONFIG block (everything below the marker line) and every rotation_distance line
  crowsnest.conf        the whole file (the installer never overwrites it)
Exit code 0 = nothing changed, 10 = something was put back (listed on stdout), 2 = a problem."""
import os
import re
import shutil
import sys

MARK = "#*# <---------------------- SAVE_CONFIG ---------------------->"
WHOLE = ["crowsnest.conf"]


def read(path):
    try:
        with open(path, encoding="utf-8", errors="surrogateescape", newline="") as f:
            return f.read()
    except OSError:
        return None


def write(path, text):
    tmp = path + ".wm-protect-tmp"
    with open(tmp, "w", encoding="utf-8", errors="surrogateescape", newline="") as f:
        f.write(text)
    shutil.copymode(path, tmp) if os.path.exists(path) else None
    os.replace(tmp, path)


def sv_values(text):
    """name -> (value, line) of the [Variables] section."""
    out, sec = {}, None
    for line in text.splitlines():
        m = re.match(r"^\s*\[([^\]]+)\]", line)
        if m:
            sec = m.group(1).strip().lower()
            continue
        if sec == "variables":
            m = re.match(r"^\s*([^#;=\s][^=:]*?)\s*[=:]\s*(.*?)\s*$", line)
            if m:
                out[m.group(1)] = (m.group(2), line)
    return out


def rot_values(text):
    """(section, occurrence) -> value of every rotation_distance line outside the SAVE_CONFIG block."""
    body = text.split(MARK)[0]
    out, sec, count = {}, "", {}
    for i, line in enumerate(body.splitlines()):
        m = re.match(r"^\s*\[([^\]]+)\]", line)
        if m:
            sec = m.group(1).strip()
            count[sec] = 0
            continue
        m = re.match(r"^\s*rotation_distance\s*[:=]\s*(\S+)", line)
        if m:
            count[sec] = count.get(sec, 0) + 1
            out[(sec, count[sec])] = (m.group(1), line)
    return out


def save_block(text):
    """The auto-generated lines below the marker ("#*#" lines). Other lines below the marker (for example a stray include that
    the installer moves above it) are not part of it."""
    if MARK not in text:
        return None
    return [l for l in text.split(MARK, 1)[1].split("\n") if l.startswith("#*#")]


def snapshot(cfg, snap):
    os.makedirs(snap, exist_ok=True)
    n = 0
    for name in ["saved_variables.cfg", "printer.cfg"] + WHOLE:
        src = os.path.join(cfg, name)
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(snap, name))
            n += 1
    print("protected: %d file(s) copied to %s" % (n, snap))
    return 0


def verify(cfg, snap):
    put_back = []
    # saved_variables.cfg: values
    old, cur_path = read(os.path.join(snap, "saved_variables.cfg")), os.path.join(cfg, "saved_variables.cfg")
    if old is not None:
        cur = read(cur_path)
        if cur is None:
            write(cur_path, old)
            put_back.append("saved_variables.cfg was missing: put back")
        else:
            ov, cv = sv_values(old), sv_values(cur)
            for k, (v, line) in ov.items():
                if k not in cv:
                    if "[Variables]" in cur:
                        cur = cur.replace("[Variables]", "[Variables]\n" + line, 1)
                    else:
                        cur = cur.rstrip("\n") + "\n[Variables]\n" + line + "\n"
                    put_back.append("saved_variables.cfg: %s was missing, put back (%s)" % (k, v))
                elif cv[k][0] != v:
                    cur = cur.replace(cv[k][1], line, 1)
                    put_back.append("saved_variables.cfg: %s was %s, put back to %s" % (k, cv[k][0], v))
            if put_back:
                write(cur_path, cur)
    # printer.cfg: rotation_distance and the SAVE_CONFIG block
    old, cur_path = read(os.path.join(snap, "printer.cfg")), os.path.join(cfg, "printer.cfg")
    if old is not None:
        cur = read(cur_path)
        if cur is None:
            write(cur_path, old)
            put_back.append("printer.cfg was missing: put back")
        else:
            changed = False
            ov, cv = rot_values(old), rot_values(cur)
            for k, (v, line) in ov.items():
                if k in cv and cv[k][0] != v:
                    cur = cur.replace(cv[k][1], line, 1)
                    changed = True
                    put_back.append("printer.cfg: rotation_distance of [%s] was %s, put back to %s" % (k[0], cv[k][0], v))
            ob, cb = save_block(old), save_block(cur)
            if ob is not None and ob != cb:
                head, tail = cur.split(MARK, 1)
                parts = tail.split("\n")
                keep = [l for l in parts[1:] if not l.startswith("#*#")]
                while keep and keep[-1] == "":
                    keep.pop()
                cur = head + MARK + parts[0] + "\n" + "\n".join(ob + keep) + "\n"
                changed = True
                put_back.append("printer.cfg: the SAVE_CONFIG block was different, put back")
            if changed:
                write(cur_path, cur)
    # whole files
    for name in WHOLE:
        old, cur_path = read(os.path.join(snap, name)), os.path.join(cfg, name)
        if old is not None and read(cur_path) != old:
            write(cur_path, old)
            put_back.append("%s was different: put back" % name)
    if put_back:
        print("Put back after the update:")
        for p in put_back:
            print("  " + p)
        return 10
    print("Your settings: untouched (saved variables, rotation_distance, SAVE_CONFIG block)")
    return 0


def show(cfg):
    sv = sv_values(read(os.path.join(cfg, "saved_variables.cfg")) or "")
    pc = read(os.path.join(cfg, "printer.cfg")) or ""
    print("saved_variables.cfg: %d values" % len(sv))
    print("printer.cfg: %d rotation_distance line(s), SAVE_CONFIG block %s" % (len(rot_values(pc)), "present" if save_block(pc) is not None else "none"))
    for name in WHOLE:
        print("%s: %s" % (name, "present" if os.path.isfile(os.path.join(cfg, name)) else "none"))
    return 0


def main(argv):
    if len(argv) >= 3 and argv[1] == "snapshot" and len(argv) == 4:
        return snapshot(argv[2], argv[3])
    if len(argv) == 4 and argv[1] == "verify":
        return verify(argv[2], argv[3])
    if len(argv) == 3 and argv[1] == "show":
        return show(argv[2])
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
