#!/usr/bin/env python3
"""Offline test of scripts/wm_protect.py (F-222). Run: python3 tests/test_protect.py"""
import os, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
S = os.path.join(HERE, "..", "scripts", "wm_protect.py")
MARK = "#*# <---------------------- SAVE_CONFIG ---------------------->"
PRINTER = "[printer]\nkinematics: corexy\n\n[extruder]\nrotation_distance: 21.649 # old value 21.018\n\n[extruder1]\nrotation_distance = 22.1\n\n" + MARK + "\n#*# DO NOT EDIT\n#*#\n#*# [extruder2]\n#*# rotation_distance = 21.5\n"
SV = "[Variables]\nprobe_x = 12.5\nz_trim_t1 = -0.045\nname = 'abc'\n"
fails = 0


def run(*a):
    p = subprocess.run([sys.executable, S] + list(a), capture_output=True, text=True)
    return p.returncode, p.stdout


def check(name, ok):
    global fails
    print(("PASS  " if ok else "FAIL  ") + name)
    fails += 0 if ok else 1


def mk():
    d = tempfile.mkdtemp()
    c, s = os.path.join(d, "config"), os.path.join(d, "snap")
    os.makedirs(c)
    for n, t in (("printer.cfg", PRINTER), ("saved_variables.cfg", SV), ("crowsnest.conf", "[crowsnest]\nmode: ustreamer\n")):
        open(os.path.join(c, n), "w").write(t)
    return c, s


def rd(c, n):
    return open(os.path.join(c, n)).read()


c, s = mk()
check("snapshot works", run("snapshot", c, s)[0] == 0)
rc, out = run("verify", c, s)
check("nothing changed: exit 0 and 'untouched'", rc == 0 and "untouched" in out)
open(os.path.join(c, "saved_variables.cfg"), "a").write("new_key = 1\n")
open(os.path.join(c, "printer.cfg"), "a").write("#*# [extruder3]\n#*# rotation_distance = 9\n")
open(os.path.join(c, "printer.cfg"), "r+").close()
t = rd(c, "printer.cfg").replace("[printer]", "[printer]\nmax_velocity: 300")
open(os.path.join(c, "printer.cfg"), "w").write(t.replace("#*# [extruder3]\n#*# rotation_distance = 9\n", ""))
rc, out = run("verify", c, s)
check("a value the installer adds is left alone (new key, new setting)", rc == 0 and "new_key = 1" in rd(c, "saved_variables.cfg") and "max_velocity: 300" in rd(c, "printer.cfg"))
# changes of protected values
open(os.path.join(c, "saved_variables.cfg"), "w").write(SV.replace("-0.045", "0.0") + "new_key = 1\n")
open(os.path.join(c, "printer.cfg"), "w").write(PRINTER.replace("21.649", "22.0").replace("= 22.1", "= 99").replace("= 21.5", "= 1.0"))
rc, out = run("verify", c, s)
check("exit 10 and each change is listed", rc == 10 and "z_trim_t1" in out and "[extruder]" in out and "[extruder1]" in out and "SAVE_CONFIG" in out)
check("saved variable put back, new key kept", "z_trim_t1 = -0.045" in rd(c, "saved_variables.cfg") and "new_key = 1" in rd(c, "saved_variables.cfg"))
check("rotation_distance and the SAVE_CONFIG block are the old ones again", rd(c, "printer.cfg") == PRINTER)
# missing key and missing file
open(os.path.join(c, "saved_variables.cfg"), "w").write("[Variables]\nprobe_x = 12.5\n")
rc, out = run("verify", c, s)
check("a missing variable is put back", rc == 10 and "z_trim_t1 = -0.045" in rd(c, "saved_variables.cfg") and "name = 'abc'" in rd(c, "saved_variables.cfg"))
os.remove(os.path.join(c, "crowsnest.conf"))
rc, out = run("verify", c, s)
check("a missing crowsnest.conf is put back", rc == 10 and os.path.isfile(os.path.join(c, "crowsnest.conf")) and "crowsnest.conf" in out)
open(os.path.join(c, "crowsnest.conf"), "w").write("changed\n")
rc, out = run("verify", c, s)
check("a changed crowsnest.conf is put back", rc == 10 and rd(c, "crowsnest.conf").startswith("[crowsnest]"))
# a stray include below the marker that the installer moves above it is not undone
c2, s2 = mk()
open(os.path.join(c2, "printer.cfg"), "w").write(PRINTER.replace("#*# DO NOT EDIT", "[include stray.cfg]\n#*# DO NOT EDIT"))
run("snapshot", c2, s2)
moved = "[include stray.cfg]\n" + PRINTER
open(os.path.join(c2, "printer.cfg"), "w").write(moved)
rc, out = run("verify", c2, s2)
check("an include the installer moved from below the marker to above it stays moved", rc == 0 and rd(c2, "printer.cfg") == moved)
open(os.path.join(c2, "printer.cfg"), "w").write(moved.replace("#*# rotation_distance = 21.5", "#*# rotation_distance = 7"))
rc, out = run("verify", c2, s2)
check("a changed SAVE_CONFIG line is put back and the moved include stays", rc == 10 and "rotation_distance = 21.5" in rd(c2, "printer.cfg") and rd(c2, "printer.cfg").startswith("[include stray.cfg]"))
check("show lists what is protected", run("show", c)[0] == 0)
check("a wrong call is refused", run("verify")[0] == 2)
print("%d failed" % fails)
sys.exit(1 if fails else 0)
