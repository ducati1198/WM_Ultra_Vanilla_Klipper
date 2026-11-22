#!/usr/bin/env python3
"""Offline test of wm-tools/wm_estep.py on copies of made-up config files. Run:  python3 tests/test_wm_estep.py"""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "scripts", "wm_estep.py")

PRINTER = """[printer]
kinematics: corexy

[include extruder1.cfg]

[extruder]
step_pin: PA1
rotation_distance: 21.018    # old value 22.127 (comment of an earlier test)
gear_ratio: 50:10

[extruder2]
rotation_distance = 21.018
gear_ratio: 50:10

#*# <---------------------- SAVE_CONFIG ---------------------->
#*# DO NOT EDIT THIS BLOCK OR BELOW. The contents are auto-generated.
#*#
#*# [extruder3]
#*# rotation_distance = 21.018
"""
EXT1 = "[extruder1]\r\nstep_pin: PB1\r\nrotation_distance: 21.018\r\ngear_ratio: 50:10\r\n"


def run(cfg, *args):
    env = dict(os.environ, WM_ESTEP_CFG=cfg)
    r = subprocess.run([sys.executable, SCRIPT] + [str(a) for a in args], env=env, capture_output=True, text=True)
    return r.returncode, r.stdout.strip()


def main():
    fails = 0

    def check(name, cond, info=""):
        nonlocal fails
        print(("PASS  " if cond else "FAIL  ") + name + (("   " + info) if (info and not cond) else ""))
        fails += 0 if cond else 1

    with tempfile.TemporaryDirectory() as d:
        cfg = os.path.join(d, "printer.cfg")
        open(cfg, "w", newline="").write(PRINTER)
        open(os.path.join(d, "extruder1.cfg"), "w", newline="").write(EXT1)

        rc, o = run(cfg, 0, 22.127, 21.018)
        txt = open(cfg).read()
        check("T0 saved, exit 0", rc == 0 and "saved [extruder]" in o, o)
        check("T0 line has new value and old value comment", "rotation_distance: 22.127 # old value 21.018\n" in txt)
        check("T0 old comment was replaced and reported", "earlier test" not in txt and "replaced" in o)
        check("nothing else changed in printer.cfg",
              txt.replace("rotation_distance: 22.127 # old value 21.018", "rotation_distance: 21.018    # old value 22.127 (comment of an earlier test)") == PRINTER)
        check("a backup exists, in the backup folder and not next to printer.cfg", os.path.isdir(os.path.join(d, "backup")) and any(f.startswith("printer.cfg.wm-before-estep-") for f in os.listdir(os.path.join(d, "backup"))) and not any(f.startswith("printer.cfg.wm-before-estep-") for f in os.listdir(d)))

        rc, o = run(cfg, 1, 20.5, 21.018)
        t1 = open(os.path.join(d, "extruder1.cfg"), newline="").read()
        check("T1 saved in the included file, CRLF kept", rc == 0 and "rotation_distance: 20.500 # old value 21.018\r\n" in t1, o + repr(t1))

        rc, o = run(cfg, 2, 21.5, 21.018)
        txt = open(cfg).read()
        check("T2 keeps the = separator", rc == 0 and "rotation_distance = 21.500 # old value 21.018\n" in txt, o)

        rc, o = run(cfg, 3, 20.0, 21.018)
        check("T3 only in the SAVE_CONFIG block is refused", rc == 1 and "not found" in o, o)

        # the exact line format of the real printer (.35): no space after the colon, two old-value comments
        real = os.path.join(d, "real.cfg")
        open(real, "w", newline="").write("[extruder1]\nfull_steps_per_rotation:200  # Number of pulses\nrotation_distance:21.018#25.12 #22.0175\nnozzle_diameter: 0.400000\n\n"
                                          "#*# <---------------------- SAVE_CONFIG ---------------------->\n#*# [extruder1]\n#*# rotation_distance = 99\n")
        rc, o = run(real, 1, 21.5, 21.018)
        rt = open(real).read()
        check("real printer line: saved, other comments replaced", rc == 0 and "rotation_distance:21.500 # old value 21.018\n" in rt and "25.12" not in rt, o + rt)
        check("real printer line: neighbours and SAVE_CONFIG block untouched", "full_steps_per_rotation:200  # Number of pulses\n" in rt and "#*# rotation_distance = 99\n" in rt)

        before = open(cfg).read()
        rc, o = run(cfg, 0, 21.0, 21.018)
        check("wrong OLD (file holds 22.127) is refused", rc == 1 and "holds" in o and open(cfg).read() == before, o)
        rc, o = run(cfg, 0, 40.0, 22.127)
        check("a change over 50 percent is refused", rc == 1 and open(cfg).read() == before, o)
        rc, o = run(cfg, 7, 21.0, 21.018)
        check("T=7 is refused", rc == 1, o)
        rc, o = run(cfg, 0, "abc", 21.018)
        check("a non-number is refused", rc == 1, o)
        rc, o = run(cfg, 0)
        check("missing arguments are refused", rc == 1, o)
    print("%d failed" % fails)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
