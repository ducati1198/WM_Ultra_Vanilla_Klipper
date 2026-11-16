"""Renders _WM_HEAT_AT_WIPE and _WM_HEAT_BACK (rpi-cfg/rpi_base.cfg) against a fake printer.  python3 -I tests/heat_wipe_render.py FILE"""
import re, sys
import jinja2

src = open(sys.argv[1], encoding="utf-8").read()


def macro(name):
    m = re.search(r"^\[gcode_macro %s\]\n(.*?)(?=^\[|\Z)" % re.escape(name), src, re.S | re.M)
    body = m.group(1)
    v = {k: eval(val.split("#")[0].strip()) for k, val in re.findall(r"^variable_(\w+):\s*(.*)$", body, re.M)}
    g = body.split("\ngcode:\n", 1)[1]
    return v, "\n".join(l[4:] if l.startswith("    ") else l for l in g.split("\n"))


class P:   # position with .x .y .z
    def __init__(s, x, y, z): s.x, s.y, s.z = x, y, z


def run(name, params=None, state="printing", cur=0, temp=30.0, homed="xyz", over=None, z=5.0):
    v, g = macro(name)
    w, _ = macro("_WM_HEAT_AT_WIPE")
    w.update(over or {})
    env = jinja2.Environment("{%", "%}", "{", "}")
    printer = {"save_variables": {"variables": {"current_extruder": cur}}, "print_stats": {"state": state},
               "toolhead": {"homed_axes": homed, "position": P(100, 50, z), "axis_maximum": P(312, 350, 310)},
               "gcode_move": {"gcode_position": P(100.0, 50.0, z)}, "gcode_macro _WM_HEAT_AT_WIPE": w,
               "extruder": {"temperature": temp}, "extruder1": {"temperature": temp}}
    ctx = dict(w) if name == "_WM_HEAT_AT_WIPE" else dict(v)
    out = env.from_string(g).render(params=params or {}, printer=printer, **ctx)
    return [l.strip() for l in out.splitlines() if l.strip() and not l.strip().startswith("#")]


ok = bad = 0


def check(desc, cond):
    global ok, bad
    if cond: ok += 1
    else: bad += 1; print("  FAIL", desc)


o = run("_WM_HEAT_AT_WIPE", {"T": "0", "S": "220"})
check("cold nozzle on the carriage in a print: lift, Y then X to the wipe position, old spot remembered", "G1 Z2.0 F900" in o and o.index("G0 Y240.0 F12000") < o.index("G0 X-13.0 F12000") and "SET_GCODE_VARIABLE MACRO=_WM_HEAT_AT_WIPE VARIABLE=ox VALUE=100.0" in o and "SET_GCODE_VARIABLE MACRO=_WM_HEAT_AT_WIPE VARIABLE=back VALUE=1" in o and "SAVE_GCODE_STATE NAME=_wm_heat" in o)
check("paused counts as in a print", any(l.startswith("G0 X") for l in run("_WM_HEAT_AT_WIPE", {"T": "0", "S": "220"}, state="paused")))
check("not in a print: no trip", run("_WM_HEAT_AT_WIPE", {"T": "0", "S": "220"}, state="standby") == [])
check("a toolhead in its dock: no trip", run("_WM_HEAT_AT_WIPE", {"T": "1", "S": "220"}) == [])
check("already within 5 C: no trip", run("_WM_HEAT_AT_WIPE", {"T": "0", "S": "220"}, temp=216.0) == [])
check("not homed: no trip", run("_WM_HEAT_AT_WIPE", {"T": "0", "S": "220"}, homed="xy") == [])
check("target 0: no trip", run("_WM_HEAT_AT_WIPE", {"T": "0", "S": "0"}) == [])
check("near the top of the printer: no lift", "SET_GCODE_VARIABLE MACRO=_WM_HEAT_AT_WIPE VARIABLE=hopped VALUE=0.0" in run("_WM_HEAT_AT_WIPE", {"T": "0", "S": "220"}, z=309.0))
check("a left-over flag is cleared when no trip is made", run("_WM_HEAT_AT_WIPE", {"T": "0", "S": "220"}, state="standby", over={"back": 1}) == ["SET_GCODE_VARIABLE MACRO=_WM_HEAT_AT_WIPE VARIABLE=back VALUE=0"])
o = run("_WM_HEAT_BACK", over={"back": 1, "ox": 100.0, "oy": 50.0, "hopped": 2.0})
check("back: X then Y to the old spot, down again, state restored", o.index("G0 X100.0 F12000") < o.index("G0 Y50.0 F12000") < o.index("G1 Z-2.0 F900") < o.index("RESTORE_GCODE_STATE NAME=_wm_heat") and "SET_GCODE_VARIABLE MACRO=_WM_HEAT_AT_WIPE VARIABLE=back VALUE=0" in o)
check("back without a trip: nothing", run("_WM_HEAT_BACK") == [])
print("heat at wipe: %d ok, %d failed" % (ok, bad))
sys.exit(1 if bad else 0)
