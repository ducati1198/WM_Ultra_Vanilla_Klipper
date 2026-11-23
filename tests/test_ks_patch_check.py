#!/usr/bin/env python3
"""Offline test of zr_tools/patch_ks_wm.py --check (2.26.0): says whether the ZR changes are inside a KlipperScreen file, changes nothing.
Run:  python3 tests/test_ks_patch_check.py"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "..", "zr_tools", "patch_ks_wm.py")
DATA = json.load(open(os.path.join(HERE, "..", "zr_tools", "ks_wm_patches.json")))
fails = 0


def run(*a):
    r = subprocess.run([sys.executable, "-I", TOOL] + list(a), capture_output=True, text=True)
    return r.returncode, r.stdout


def check(name, cond):
    global fails
    print(("PASS  " if cond else "FAIL  ") + name)
    fails += 0 if cond else 1


t = tempfile.mkdtemp()
g = [h for h in DATA["gcodes"] if "old" in h][0]
p = os.path.join(t, "gcodes.py")
open(p, "w").write("# a\n" + g["old"])
before = open(p).read()
rc, out = run("--check", "gcodes", p)
check("a stock file says missing (exit 10) and is not changed", rc == 10 and "missing" in out and open(p).read() == before)
rc, _ = run("gcodes", p)
check("the normal run changes it (exit 10)", rc == 10)
rc, out = run("--check", "gcodes", p)
check("after the change the check says present (exit 0)", rc == 0 and "present" in out)
open(p, "w").write("# a\nsomething else entirely\n")
rc, out = run("--check", "gcodes", p)
check("lines KlipperScreen of another version has: different (exit 11)", rc == 11 and "different" in out)
k = [h for h in DATA["prompts"] if "old" in h and "def add_images" in h["new"]][0]
q = os.path.join(t, "prompts.py")
open(q, "w").write(k["new"])
rc, out = run("--check", "prompts", q)
check("only one change of the list in, the other lines are unknown: different (exit 11)", rc == 11)
rc, _ = run("--check", "nokey", p)
check("an unknown key is refused (exit 2)", rc == 2)
rc, _ = run("--check", "gcodes", os.path.join(t, "none.py"))
check("a missing file is refused (exit 2)", rc == 2)
print("%d failed" % fails)
sys.exit(1 if fails else 0)
