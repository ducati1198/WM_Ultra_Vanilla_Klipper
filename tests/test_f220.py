#!/usr/bin/env python3
"""2.23.2: the KlipperScreen patch list. F-220 (one standard popup writing: Large, bold) and F-212 (Nozzle clean window colours) are the key
'prompts2'; the Fine Tuning zero button calls _WM_LIVE_Z_ZERO (a board patched earlier with WM_LIVE_Z_ZERO is renamed)."""
import json, os, subprocess, sys, tempfile
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
fails = 0
def check(name, ok):
    global fails
    print(("ok   " if ok else "FAIL ") + name)
    if not ok: fails += 1
def run(key, path):
    return subprocess.run([sys.executable, "-I", root + "/zr_tools/patch_ks_wm.py", key, path]).returncode
d = json.load(open(root + "/zr_tools/ks_wm_patches.json"))
hs = [h for h in d["prompts2"] if "old" in h]
done = [h for h in d["prompts2"] if h.get("done")]
check("prompts2: one done mark, and it is in the new text", len(done) == 1 and any(done[0]["done"] in h["new"] for h in hs))
check("prompts2: no change can apply twice", all(h["old"] not in h["new"] for h in hs))
check("prompts2: every popup line is Large bold (F-220) and the Nozzle clean colours are in (F-212)", any('size=\\"large\\" weight=\\"bold\\"' in h["new"] for h in hs) and any("wm_yellow" in h["new"] for h in hs))
with tempfile.TemporaryDirectory() as t:
    p = os.path.join(t, "prompts.py")
    open(p, "w").write("".join("# part %d\n%s\n" % (i, h["old"]) for i, h in enumerate(hs)))
    r1 = run("prompts2", p); patched = open(p).read(); r2 = run("prompts2", p)
    check("prompts2: the patch applies (10), then nothing to do (0)", r1 == 10 and r2 == 0 and open(p).read() == patched)
    check("prompts2: the done mark is in the patched file", done[0]["done"] in patched)
    open(p, "w").write("# a file of the new version\n" + done[0]["done"] + "\n")
    check("prompts2: a file with the done mark is left alone (0)", run("prompts2", p) == 0)
    open(p, "w").write("class Foo:\n    pass\n")
    check("prompts2: lines that are different change nothing and say so (11)", run("prompts2", p) == 11 and open(p).read() == "class Foo:\n    pass\n")
check("fine_tune: the zero button calls _WM_LIVE_Z_ZERO", any('script = "_WM_LIVE_Z_ZERO" if self.wm_live_on()' in h.get("new", "") for h in d["fine_tune"]) and not any('"WM_LIVE_Z_ZERO"' in h.get("new", "") for h in d["fine_tune"]))
with tempfile.TemporaryDirectory() as t:
    p = os.path.join(t, "fine_tune.py")
    fh = [h for h in d["fine_tune"] if "old" in h]
    open(p, "w").write("".join(h["old"] + "\n" for h in fh))
    r1 = run("fine_tune", p)
    text = open(p).read().replace('"_WM_LIVE_Z_ZERO"', '"WM_LIVE_Z_ZERO"')
    open(p, "w").write(text)
    r2 = run("fine_tune", p); text2 = open(p).read()
    check("fine_tune: a board patched with the old name is renamed (10), a second run changes nothing (0)", r1 == 10 and r2 == 10 and '"_WM_LIVE_Z_ZERO"' in text2 and '"WM_LIVE_Z_ZERO"' not in text2 and run("fine_tune", p) == 0)
sys.exit(1 if fails else 0)
