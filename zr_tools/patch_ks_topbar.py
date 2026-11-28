"""F-278: KlipperScreen's top bar shows the nozzle temperature of ALL tools (T0-T3) next to the bed and chamber, and the tool on the
carriage gets a blue outline (stock KlipperScreen shows only the current extruder). Idempotent.
usage: patch_ks_topbar.py /path/to/KlipperScreen/panels/base_panel.py   (exit 0 patched or already patched, 1 the file does not match)"""
import sys

MARK = "WM F-278"
NLIMIT = """            nlimit = int(round(log(self._screen.width, 10) * 5 - 10.5))
"""
IFCUR = """            if len(self._printer.get_tools()) > (nlimit - 1):
"""
SETLBL = """                self.titlebar_labels[device].set_label(f"{name}{temp:.0f}°")
"""

p = sys.argv[1]
s = open(p).read()
if MARK in s:
    sys.exit(0)
try:
    assert s.count(NLIMIT) == 1 and s.count(IFCUR) == 1 and s.count(SETLBL) == 1
    s = s.replace(NLIMIT, NLIMIT + "            nlimit = max(nlimit, len(self._printer.get_tools()) + 2)    # WM F-278: every nozzle (T0-T3) + bed + chamber are shown together\n")
    s = s.replace(IFCUR, "            if False:     # WM F-278: no single \"current extruder\" item any more\n")
    s = s.replace(SETLBL, SETLBL + """                if device.startswith("extruder") and f"{device}_eventbox" in self.titlebar_labels:     # WM F-278: the tool on the carriage is outlined
                    _ctx = self.titlebar_labels[f"{device}_eventbox"].get_style_context()
                    if device == self._printer.get_stat("toolhead", "extruder"):
                        _ctx.add_class("wm_tool_active")
                    else:
                        _ctx.remove_class("wm_tool_active")
""")
    compile(s, p, "exec")
except Exception as e:
    print("patch_ks_topbar: base_panel.py does not match (%s)" % e)
    sys.exit(1)
open(p, "w").write(s)
