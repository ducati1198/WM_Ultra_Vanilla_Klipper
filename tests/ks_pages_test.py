"""Touchscreen pages of 2.15.0 (zr_tools/wm_setter.py, zr_tools/wm_ztrim.py) and the prompts changes that open them.
python3 -I tests/ks_pages_test.py REPO_ROOT"""
import ast
import json
import re
import sys

root = sys.argv[1]
ok = bad = 0


def check(desc, cond):
    global ok, bad
    if cond: ok += 1
    else: bad += 1; print("  FAIL", desc)


hunks = [h for h in json.load(open(root + "/zr_tools/ks_wm_patches.json"))["prompts"] if "old" in h]
new = [h for h in hunks if "wm_mark" in h["new"] or "wm_show_page" in h["new"]]
check("three prompts changes for the pages, none can apply twice", len(new) == 3 and all(h["old"] not in h["new"] for h in new))
fix = ("import logging\nclass Prompt:\n    def decode(self, data):\n        if data.startswith('prompt_button '):\n            if len(params) > 3:\n"
       + new[0]["old"] + new[1]["old"] + "\n    def set_footer_button(self, name, gcode, style='default'):\n" + new[2]["old"] + "        pass\n")
s = fix
for h in new:
    check("change applies once: " + h["new"].split("\n")[2].strip()[:40], s.count(h["old"]) == 1)
    s = s.replace(h["old"], h["new"])
try:
    compile(s, "prompts.py", "exec"); check("patched file compiles", True)
except SyntaxError as e:
    check("patched file compiles (%s)" % e, False)

body = new[2]["new"].split("    def wm_mark", 1)[1].rsplit("    def show(self):", 1)[0]
ns = {}
exec("import logging\nclass P:\n    text = 'T'\n    ended = 0\n    def end(self):\n        self.ended += 1\n    def wm_mark" + body, ns)


class Saver:
    def close(self): pass


class Panel:
    def __init__(self): self.got = []
    def wm_refresh(self, d): self.got.append(d)


class Screen:
    def __init__(self, loads=True):
        self._cur_panels = ["main_menu"]; self.panels = {}; self.screensaver = Saver(); self.loads = loads; self.shown = []
    def show_panel(self, page, title=None):
        self.shown.append((page, title))
        if self.loads:
            self.panels[page] = Panel(); self._cur_panels.append(page)


p = ns["P"](); p.screen = Screen()
check("an ordinary window has no page", p.wm_show_page() is False and p.ended == 0)
p.wm_mark(["Start", "_WM_SETTER_GO", "primary"])
check("another macro's button does not mark the window", p.wm_show_page() is False)
p.wm_mark(["- 1", "_WM_SETTER_STEP AXIS=X D=-1", "warning"])
check("tool setter adjust window: page wm_setter opens with the window text, the window is not shown",
      p.wm_show_page() is True and p.screen.shown == [("wm_setter", "Tool setter position")] and p.screen.wm_setter_data == "T" and p.ended == 1)
p2 = ns["P"](); p2.screen = p.screen; p2.text = "T2"; p2.wm_mark(["+ 1", "_WM_SETTER_STEP AXIS=X D=1"])
check("page already open: refreshed, not opened again", p2.wm_show_page() is True and len(p.screen.shown) == 1 and p.screen.panels["wm_setter"].got == ["T2"])
z = ns["P"](); z.screen = Screen()
for name, g in (("T0  +0.05", "_WM_Z_TRIM_WIN TARGET=0"), ("T1  -0.10", "_WM_Z_TRIM_WIN TARGET=1"), ("T2  +0.00", "_WM_Z_TRIM_WIN TARGET=2"), ("T3  +0.03", "_WM_Z_TRIM_WIN TARGET=3")):
    z.wm_mark([name, g, "info"])
check("Z trim menu window: four values read from the buttons, no tool chosen",
      z.wm_ztrim == {"values": {0: 0.05, 1: -0.1, 2: 0.0, 3: 0.03}, "target": None} and z.wm_show_page() is True and z.screen.shown == [("wm_ztrim", "Z trim")])
z2 = ns["P"](); z2.screen = Screen()
z2.wm_mark(["T2 trim now   +0.07 mm", "_WM_Z_TRIM_WIN TARGET=2", "secondary"]); z2.wm_mark(["- 0.1", "_WM_Z_TRIM_STEP TARGET=2 D=-0.1", "warning"])
check("Z trim step window: value and chosen tool", z2.wm_ztrim == {"values": {2: 0.07}, "target": 2})
f = ns["P"](); f.screen = Screen(loads=False); f.wm_mark(["- 1", "_WM_SETTER_STEP AXIS=X D=-1"])
check("page cannot load: False, so the window is shown as before", f.wm_show_page() is False and f.ended == 0)

# the pages themselves (GTK is not here: syntax, and the pure function)
for name in ("wm_setter", "wm_ztrim"):
    src = open("%s/zr_tools/%s.py" % (root, name)).read()
    try:
        tree = ast.parse(src); good = True
    except SyntaxError:
        good = False
    check(name + ".py parses and has Panel.wm_refresh", good and "def wm_refresh(self" in src and "class Panel(ScreenPanel)" in src)
src = open(root + "/zr_tools/wm_setter.py").read()
m = re.search(r"^WM_SETTER_NUM = .*?(?=^class Panel)", src, re.S | re.M)
ns2 = {"re": re}; exec(m.group(0), ns2)
now, saved = ns2["wm_setter_parse"]("NOZZLE NOW: X 298.31  Y 285.90  Z 9.26     SAVED: X 298.21  Y 285.90  Z 9.21     MOVED: X +0.10  Y +0.00  Z +0.05")
check("tool setter page reads now and saved from the first line of the window", now == [298.31, 285.9, 9.26] and saved == [298.21, 285.9, 9.21])
check("no numbers in the text: nothing invented", ns2["wm_setter_parse"]("hello") == (None, None))
check("tool setter page calls the helper's macros only", all(k in src for k in ("_WM_SETTER_STEP AXIS=%s D=%s%s", "_WM_SETTER_FIND", "_WM_SETTER_SAVE", "_WM_SETTER_MOVE", "_WM_SETTER_CLOSE")) and "G0 " not in src and "G1 " not in src)
zs = open(root + "/zr_tools/wm_ztrim.py").read()
check("Z trim page: Z only, calls the Z trim macros", "_WM_Z_TRIM_STEP TARGET=%d D=%s%s" in zs and "_WM_Z_TRIM_RESET" in zs and "ZERO=1" in zs and "AXIS" not in zs)
sb = open(root + "/scripts/screen_board.sh").read()
check("screen_board.sh copies both pages at install, update and repair", sb.count("wm_setter") >= 5 and sb.count("wm_ztrim") >= 5)
print("touchscreen pages: %d ok, %d failed" % (ok, bad))
sys.exit(1 if bad else 0)
