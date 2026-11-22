#!/usr/bin/env python3
"""rpi_pi.cfg: the Raspberry Pi side of the printer in one file, written by the installer from the parts this Pi uses.

  host-mcu     [mcu rpi], the host MCU (service klipper-mcu)                    added by ./installer.sh --pi-sensors
  pi-temp      [temperature_sensor raspberry_pi], the Pi's own temperature      added by the rpi-cfg step (Klipper with temperature_host)
  board-temps  [temperature_sensor mcu_*], the chip temperature of every board  added by ./installer.sh --pi-sensors
  light        WM_CHAMBER_LIGHT, the chamber light of the screen board          added by ./installer.sh --light
  other        sections found in an old rpi_pi.cfg that are none of the above (kept as they were)

Each part sits between "# ===== part NAME" and "# ===== end NAME" lines, always in the order above, so the installer can add, replace
or remove one part without touching the others. Until 2.9.0 these were separate files (rpi_mcu.cfg, rpi_pi.cfg, rpi_mcu_temps.cfg,
rpi_light.cfg); "migrate" moves an old Pi to this file.

  wm_rpi_pi.py set     CONFIG_DIR PART [FILE]     put FILE (or stdin) into PART (replaces it); creates rpi_pi.cfg when needed
  wm_rpi_pi.py del     CONFIG_DIR PART            remove PART
  wm_rpi_pi.py has     CONFIG_DIR PART            exit 0 when rpi_pi.cfg has PART
  wm_rpi_pi.py parts   CONFIG_DIR                 list the parts
  wm_rpi_pi.py migrate CONFIG_DIR BACKUP_DIR      the old separate files and an old rpi_pi.cfg become parts; their include lines
                                                  leave printer.cfg; the old files go to BACKUP_DIR (copies of rpi_pi.cfg and
                                                  printer.cfg too). Prints one line per change. Exit 0 nothing to do, 10 changed.
Exit code 2 = usage."""
import os
import re
import shutil
import sys

ORDER = ["host-mcu", "pi-temp", "board-temps", "light", "other"]
NAME = "rpi_pi.cfg"
HEAD = ["# rpi_pi.cfg  -  the Raspberry Pi side: host MCU, the Pi's and every board's temperature, the chamber light macro.",
        "# Written by the installer (scripts/wm_rpi_pi.py) from the parts this Pi uses. A part may be rewritten by ./installer.sh",
        "# (--update, --pi-sensors, --light); put your own sections in another file."]
OLD_FILES = {"rpi_mcu.cfg": "host-mcu", "rpi_mcu_temps.cfg": "board-temps", "rpi_light.cfg": "light"}
INC = re.compile(r"^\s*\[include\s+(\S+?)\s*\]\s*$")


def path(cd):
    return os.path.join(cd, NAME)


def read_parts(cd):
    """-> dict part -> text, or None when rpi_pi.cfg does not exist; a file without part lines -> {"legacy": text}"""
    p = path(cd)
    if not os.path.isfile(p):
        return None
    text = open(p).read()
    parts, cur, buf = {}, None, []
    found = False
    for ln in text.split("\n"):
        m = re.match(r"^# ===== part (\S+)\s*$", ln)
        if m:
            found = True
            cur, buf = m.group(1), []
            continue
        m = re.match(r"^# ===== end (\S+)\s*$", ln)
        if m and cur:
            parts[cur] = "\n".join(buf).strip("\n")
            cur = None
            continue
        if cur:
            buf.append(ln)
    if not found:
        return {"legacy": text}
    return parts


def write_parts(cd, parts):
    out = list(HEAD)
    for k in ORDER:
        if parts.get(k, "").strip():
            out += ["", "# ===== part %s" % k, parts[k].strip("\n"), "# ===== end %s" % k]
    text = "\n".join(out) + "\n"
    try:                                              # the index of the macros (F-158); without the helper the file is written as before
        import importlib.util
        sp = importlib.util.spec_from_file_location("wm_cfg_index", os.path.join(os.path.dirname(os.path.abspath(__file__)), "wm_cfg_index.py"))
        mod = importlib.util.module_from_spec(sp)
        sp.loader.exec_module(mod)
        text = mod.index_text(text, NAME)
    except (OSError, ImportError, AttributeError):
        pass
    tmp = path(cd) + ".wm-tmp"
    with open(tmp, "w") as f:
        f.write(text)
    os.replace(tmp, path(cd))


def _trim(lines):
    while lines and (not lines[-1].strip() or lines[-1].startswith("#")):
        lines = lines[:-1]                  # comment lines at the end belong to what comes next
    return "\n".join(lines)


def sections(text):
    """-> list of (name, block text including the comment lines right above it)"""
    lines = text.split("\n")
    out, pend, cur, buf = [], [], None, []
    for ln in lines:
        m = re.match(r"^\[([^\]]+)\]", ln)
        if m:
            if cur is not None:
                out.append((cur, _trim(buf)))
            cur, buf = " ".join(m.group(1).split()), pend + [ln]
            pend = []
            continue
        if cur is None:
            if ln.startswith("#") and not ln.startswith("# ====="):
                pend.append(ln)
            elif not ln.strip():
                pend = []
            continue
        buf.append(ln)
    if cur is not None:
        out.append((cur, _trim(buf)))
    return out


def classify(name, block):
    n = name.lower()
    if n == "mcu rpi":
        return "host-mcu"
    if n == "temperature_sensor raspberry_pi":
        return "pi-temp"
    if n.startswith("temperature_sensor ") and "temperature_mcu" in block:
        return "board-temps"
    if n == "gcode_macro wm_chamber_light":
        return "light"
    if n == "gcode_macro set_gcode_offset":
        return None                       # lives in rpi_base.cfg since 2.10.0
    return "other"


def add_blocks(parts, blocks):
    for name, block in blocks:
        k = classify(name, block)
        if k is None:
            continue
        cur = parts.get(k, "")
        if re.search(r"^\[%s\]" % re.escape(name), cur, re.M | re.I):
            continue                      # already there
        parts[k] = (cur.rstrip("\n") + "\n\n" + block).strip("\n")


def main():
    a = sys.argv[1:]
    if len(a) < 2:
        print(__doc__)
        return 2
    cmd, cd = a[0], a[1]
    if cmd in ("set", "del", "has") and (len(a) < 3 or a[2] not in ORDER):
        print(__doc__)
        return 2
    parts = read_parts(cd)
    if cmd == "has":
        return 0 if parts and "legacy" not in parts and parts.get(a[2], "").strip() else 1
    if cmd == "parts":
        print(" ".join(k for k in ORDER if parts and parts.get(k, "").strip()))
        return 0
    if parts and "legacy" in parts:
        print("rpi_pi.cfg is still the old kind: run migrate first", file=sys.stderr)
        return 1
    parts = parts or {}
    if cmd == "set":
        text = open(a[3]).read() if len(a) > 3 else sys.stdin.read()
        parts[a[2]] = text.strip("\n")
        write_parts(cd, parts)
        return 0
    if cmd == "del":
        parts.pop(a[2], None)
        write_parts(cd, parts)
        return 0
    print(__doc__)
    return 2


def migrate(cd, bk):
    parts = read_parts(cd)
    changed = []
    prn = os.path.join(cd, "printer.cfg")
    olds = [f for f in OLD_FILES if os.path.isfile(os.path.join(cd, f))]
    legacy = parts is not None and "legacy" in parts
    if not olds and not legacy:
        return 0
    os.makedirs(bk, exist_ok=True)
    for f in [NAME, "printer.cfg"]:
        if os.path.isfile(os.path.join(cd, f)):
            shutil.copy2(os.path.join(cd, f), os.path.join(bk, f))
    new = {} if (parts is None or legacy) else dict(parts)
    if legacy:
        add_blocks(new, sections(parts["legacy"]))
        changed.append("rpi_pi.cfg rebuilt from its old sections (the SET_GCODE_OFFSET wrapper is in rpi_base.cfg now)")
    for f in olds:
        add_blocks(new, sections(open(os.path.join(cd, f)).read()))
        changed.append("%s moved into rpi_pi.cfg (part %s)" % (f, OLD_FILES[f]))
    write_parts(cd, new)
    if os.path.isfile(prn) and olds:
        lines = open(prn).read().split("\n")
        keep = [ln for ln in lines if not (INC.match(ln) and INC.match(ln).group(1) in olds)]
        if keep != lines:
            with open(prn + ".wm-tmp", "w") as fh:
                fh.write("\n".join(keep))
            os.replace(prn + ".wm-tmp", prn)
            changed.append("printer.cfg: include lines of %s removed" % ", ".join(olds))
    for f in olds:
        shutil.move(os.path.join(cd, f), os.path.join(bk, f))
    for c in changed:
        print(c)
    return 10


if __name__ == "__main__":
    if sys.argv[1:2] == ["migrate"]:
        if len(sys.argv) != 4:
            print(__doc__)
            sys.exit(2)
        sys.exit(migrate(sys.argv[2], sys.argv[3]))
    sys.exit(main())
