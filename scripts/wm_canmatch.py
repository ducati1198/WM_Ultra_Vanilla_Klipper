#!/usr/bin/env python3
"""wm_canmatch.py - find out which CAN board is which on a WonderMaker ZR Ultra / Ultra-S, with no stored ids, and write the ids into the config.

Why: a fresh install has placeholder CAN ids for the extruder board, the hub, T0 to T3 and the load cell. The installer cannot tell
which id on the bus belongs to which board. WonderMaker's own app does not need to, because the factory writes the ids at the factory.

How: every board tells its firmware name when Klipper connects to it:
    KLP_MCU_...   main board        KLP_HUB_...   hub             KLP_EXT_...   extruder board
    KLP_CELL_...  load cell board (factory firmware and V2 both start with KLP_CELL)
    KLP_THR_...   a toolhead (all four tool heads report the same name, so their ORDER is not known here)
Steps: 1) ask the bus which ids answer (Klipper's canbus_query.py, asked several times because one board answers only now and then),
2) connect to each id with a throw-away Klipper that has a one-line config and read the firmware name from its log,
3) with --apply write main, hub, extruder board and load cell, and the four tool heads in id order into wm_zru_thr0..3.cfg.
The tool head ORDER must be fixed afterwards by WM_EXTRUDER_SETUP (the printer picks up T0 to T3 and sees which dock each came out of).

Klipper has to be stopped while this runs (it uses the bus). Boards that were already given a node id by an earlier Klipper session do not
answer the scan until the printer's 24 V was switched off and on: do this scan right after power-up.

  wm_canmatch.py run [--config-dir DIR] [--backup-dir DIR] [--klipper-dir DIR] [--iface can0] [--apply]
Exit 0 = every board found and told apart (written with --apply), 1 = unclear (nothing written), 2 = nothing answers on the bus.
The last line is "RESULT ok", "RESULT unclear" or "RESULT none". For tests: WM_CANMATCH_FAKE=file.json (id -> [application, firmware name])
replaces the bus and Klipper."""
import argparse, json, os, re, shutil, subprocess, sys, tempfile, time

HOME = os.path.expanduser("~")
HEX12 = re.compile(r"^[0-9a-f]{12}$")
LINE = re.compile(r"^(\s*canbus_uuid\s*[:=]\s*)([^#;\s]*)(.*)$", re.I | re.M)
SINGLE = {"MCU": "wm_zru_mcu.cfg", "HUB": "wm_zru_hub.cfg", "EXT": "wm_zru_ext.cfg", "CELL": "wm_zru_load_cell.cfg"}
NAMES = {"MCU": "main board", "HUB": "hub", "EXT": "extruder board", "CELL": "load cell board", "THR": "tool head"}
THR_FILES = ["wm_zru_thr%d.cfg" % i for i in range(4)]
TAGS = (("MCU", "KLP_MCU"), ("HUB", "KLP_HUB"), ("EXT", "KLP_EXT"), ("CELL", "KLP_CELL"), ("THR", "KLP_THR"))


def kind(fw):
    """board type from the firmware name, None when there is no name"""
    if not fw:
        return None
    up = fw.upper()
    for k, tag in TAGS:
        if up.startswith(tag):
            return k
    return "OTHER"


def scan_bus(py, kdir, iface, rounds):
    """{id: application}. One board (the load cell) answers a scan only now and then, so ask several times and join the answers."""
    found = {}
    for i in range(rounds):
        try:
            out = subprocess.run([py, os.path.join(kdir, "scripts", "canbus_query.py"), iface], stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT, universal_newlines=True, timeout=30).stdout
        except Exception:
            out = ""
        for m in re.finditer(r"canbus_uuid=([0-9a-f]{12}),\s*Application:\s*(\S+)", out, re.I):
            found[m.group(1).lower()] = m.group(2)
        if i + 1 < rounds:
            time.sleep(1)
    return found


def firmware_name(py, kdir, iface, uuid, tmp):
    """connect with a throw-away Klipper (one [mcu] section) and read 'Loaded MCU ... (KLP_xxx_...)' from its log"""
    cfg = os.path.join(tmp, uuid + ".cfg"); log = os.path.join(tmp, uuid + ".log"); sock = os.path.join(tmp, uuid + ".sock")
    with open(cfg, "w") as f:
        f.write("[mcu]\ncanbus_uuid: %s\ncanbus_interface: %s\n\n[printer]\nkinematics: none\nmax_velocity: 100\nmax_accel: 100\n" % (uuid, iface))
    p = subprocess.Popen([py, os.path.join(kdir, "klippy", "klippy.py"), cfg, "-l", log, "-a", sock],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    name = None; t0 = time.time()
    while time.time() - t0 < 20 and not name:
        time.sleep(0.5)
        try:
            with open(log, errors="replace") as f:
                m = re.search(r"Loaded MCU '[^']*' \d+ commands \((KLP_[A-Za-z0-9_]+)", f.read())
        except OSError:
            m = None
        if m:
            name = m.group(1)
    p.terminate()
    try:
        p.wait(5)
    except Exception:
        p.kill()
    return name


def write_id(cfgdir, fname, uuid, backup, stamp):
    p = os.path.join(cfgdir, fname)
    with open(p, errors="replace") as f:
        s = f.read()
    if not LINE.search(s):
        raise SystemExit("%s has no canbus_uuid line" % fname)
    os.makedirs(backup, exist_ok=True)
    shutil.copy2(p, os.path.join(backup, fname))   # the copy goes OUT of the config folder: a copy next to the file is found by tools that read every file there
    with open(p, "w") as f:
        f.write(LINE.sub(lambda m: m.group(1) + uuid + m.group(3), s, count=1))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["run"])
    ap.add_argument("--config-dir", default=os.path.join(HOME, "printer_data", "config"))
    ap.add_argument("--backup-dir", default=os.path.join(HOME, "ultra-backup", "canmatch-" + time.strftime("%Y%m%d-%H%M%S")))
    ap.add_argument("--klipper-dir", default=os.path.join(HOME, "klipper"))
    ap.add_argument("--python", default=os.path.join(HOME, "klippy-env", "bin", "python"))
    ap.add_argument("--iface", default="can0")
    ap.add_argument("--rounds", type=int, default=5)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    fake = os.environ.get("WM_CANMATCH_FAKE")
    if fake:
        with open(fake) as f:
            data = json.load(f)
        found = {u.lower(): (v[0], v[1]) for u, v in data.items()}      # id -> (application, firmware name)
    else:
        apps = scan_bus(a.python, a.klipper_dir, a.iface, a.rounds)
        found = {}
        if apps:
            tmp = tempfile.mkdtemp(prefix="wmcanmatch-")
            try:
                for u in sorted(apps):
                    if apps[u].lower() != "klipper":
                        found[u] = (apps[u], None)       # a board sitting in its bootloader (Katapult): no Klipper firmware to read
                        continue
                    found[u] = (apps[u], firmware_name(a.python, a.klipper_dir, a.iface, u, tmp))
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
    if not found:
        print("Nothing answers on the CAN bus (printer off? CAN cable? can0 up?).")
        print("RESULT none")
        return 2

    print("On the bus: %d board(s)" % len(found))
    by = {}
    for u in sorted(found):
        app, fw = found[u]
        k = kind(fw)
        by.setdefault(k, []).append(u)
        label = NAMES.get(k, "?") if k not in (None, "OTHER") else ("only the bootloader (%s) answers" % app if fw is None and app.lower() != "klipper" else "unknown")
        print("  %s  %-36s %s" % (u, fw or "-", label))

    problems = []
    for k in ("MCU", "HUB", "EXT", "CELL"):
        n = len(by.get(k, []))
        if n != 1:
            problems.append("%s: %d found, need exactly 1%s" % (NAMES[k], n, (" (" + ", ".join(by[k]) + ")") if n else ""))
    if len(by.get("THR", [])) != 4:
        problems.append("tool heads: %d found, need 4" % len(by.get("THR", [])))
    for bad in (None, "OTHER"):
        if by.get(bad):
            problems.append("board(s) that could not be identified: %s%s" % (", ".join(by[bad]),
                            " (a board that was already connected by Klipper answers only after the printer's 24 V was switched off and on)"))
    if problems:
        print("Not clear, nothing was written:")
        for p in problems:
            print("  - " + p)
        print("RESULT unclear")
        return 1

    plan = [(SINGLE[k], by[k][0]) for k in ("MCU", "HUB", "EXT", "CELL")] + list(zip(THR_FILES, sorted(by["THR"])))
    for f, u in plan:
        if not os.path.isfile(os.path.join(a.config_dir, f)):
            print("%s is missing in %s, nothing was written." % (f, a.config_dir))
            print("RESULT unclear")
            return 1
    print("Plan:")
    for f, u in plan:
        print("  %-22s <- %s" % (f, u))
    if a.apply:
        stamp = time.strftime("%Y%m%d-%H%M%S")
        for f, u in plan:
            write_id(a.config_dir, f, u, a.backup_dir, stamp)
        print("Written. Copies of the old files: %s" % a.backup_dir)
    print("RESULT ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
