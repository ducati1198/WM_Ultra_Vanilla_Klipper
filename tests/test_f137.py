#!/usr/bin/env python3
"""2.19.0 (F-137): the ZR Tools screen changes. python3 -I tests/test_f137.py REPO_ROOT
The KlipperScreen changes ('prompts' and 'screen' of zr_tools/ks_wm_patches.json) must apply once, apply nowhere twice, and a file that
has them (the "done" mark) is left alone; the panel files must compile and carry the new design."""
import json, os, subprocess, sys, tempfile

root = sys.argv[1]
ok = bad = 0


def check(desc, cond):
    global ok, bad
    if cond:
        ok += 1
    else:
        bad += 1
        print("  FAIL", desc)


d = json.load(open(root + "/zr_tools/ks_wm_patches.json"))
for key, mark in (("prompts", "def zr_style("), ("screen", "F-137: the message banner sits at the very top edge")):
    hs = [h for h in d[key] if "old" in h]
    done = [h for h in d[key] if h.get("done")]
    check(key + ": one done mark, and it is in the new text of the F-137 changes", len(done) == 1 and any(done[0]["done"] in h["new"] for h in hs))
    check(key + ": no change can apply twice (its old lines are not in its new lines)", all(h["old"] not in h["new"] for h in hs))
    # a file that has the old lines of every change gets patched (exit 10), a second run changes nothing (0), the mark makes a patched file final
    with tempfile.TemporaryDirectory() as t:
        p = os.path.join(t, key + ".py")
        base = "".join("# part %d\n%s\n" % (i, h["old"]) for i, h in enumerate(hs))
        open(p, "w").write(base)
        r1 = subprocess.run([sys.executable, "-I", root + "/zr_tools/patch_ks_wm.py", key, p]).returncode
        patched = open(p).read()
        r2 = subprocess.run([sys.executable, "-I", root + "/zr_tools/patch_ks_wm.py", key, p]).returncode
        check(key + ": the patch applies (10), then there is nothing to do (0)", r1 == 10 and r2 == 0 and open(p).read() == patched)
        check(key + ": the done mark is in the patched file", done[0]["done"] in patched)
        open(p, "w").write("# a file of the new version\n" + done[0]["done"] + "\nand lines the old changes do not know\n")
        check(key + ": a file with the done mark is left alone (0)", subprocess.run([sys.executable, "-I", root + "/zr_tools/patch_ks_wm.py", key, p]).returncode == 0)

zl = open(root + "/zr_tools/zr_logic.py").read()
zt = open(root + "/zr_tools/zr_tools.py").read()
zv = open(root + "/zr_tools/zr_views.py").read()
for f in ("zr_tools", "zr_views", "zr_logic", "wm_ztrim", "wm_setter"):
    try:
        compile(open("%s/zr_tools/%s.py" % (root, f)).read(), f, "exec"); check(f + ".py compiles", True)
    except SyntaxError as e:
        check("%s.py compiles (%s)" % (f, e), False)
check("Back goes to the previous page: back() and a history", "def back(self" in zt and "_hist" in zt)
check("every ZR confirm is a page: _ask_page with a blue Yes and a dark Cancel", "def _ask_page" in zt and "zr_btn_primary" in zt)
# F-197: the Select button of the Filament page is pink on purpose (the user chose a colour not used elsewhere on that page); nothing else is
pk = [f for f in ("zr_tools", "zr_views", "wm_ztrim", "wm_setter") if open("%s/zr_tools/%s.py" % (root, f)).read().count("zr_btn_pink") > (1 if f == "zr_tools" else 0)]
check("no pink button is used except the Select button of the Filament page (the style stays defined in zr_logic) " + str(pk), not pk)
check("switches hold the tapped value until Klipper reports it (no flicker)", "_sw_hold" in zv or "_toggled" in zv)
check("Unload menu pages exist", "def show_unload" in zt and "def _unload_open" in zt)
print("f137 tests: passed %d failed %d" % (ok, bad))
sys.exit(1 if bad else 0)
