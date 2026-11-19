"""Renders the tool setter position helper (rpi-cfg/rpi_calibration.cfg, WM_SETTER_PROBE_POSITION) against a fake printer.
python3 -I tests/setter_render.py rpi-cfg/rpi_calibration.cfg"""
import re
import sys
import jinja2

src = open(sys.argv[1], encoding="utf-8").read()


def macro(name):
    m = re.search(r"^\[gcode_macro %s\]\n(.*?)(?=^\[|^# -{20}|\Z)" % re.escape(name), src, re.S | re.M)
    body = m.group(1)
    v = {k: eval(val) for k, val in re.findall(r"^variable_(\w+):\s*(.*)$", body, re.M)}
    g = body.split("\ngcode:\n", 1)[1]
    return v, "\n".join(l[4:] if l.startswith("    ") else l for l in g.split("\n"))


class P:
    def __init__(s, x, y, z): s.x, s.y, s.z = x, y, z


class D(dict):
    __getattr__ = dict.get


class U(dict):   # like the real save_variables: a missing key is undefined, not None
    def __getattr__(s, k):
        if k in s: return s[k]
        raise AttributeError(k)


def T(found, x=0, y=0, z=0): return D(found=found, x=x, y=y, z=z)


SV, _ = macro("_WM_SETTER")
SV.update(dict(active=1, sx=297.68, sy=286.36, sz=9.23, zref=9.23, fx0=297.68, fy0=286.36, mx0=297.68, my0=286.36, mz0=9.23))
PP = (297.68, 286.36, 9.23, 6.9, 5.8)


def run(name, touch=None, params=None, pos=(297.68, 286.36, 9.23), module=True, state="standby", cur=0, backup=None, **over):
    s = dict(SV); s.update(over)
    _, g = macro(name)
    env = jinja2.Environment("{%", "%}", "{", "}")
    var = U(probe_position=PP, current_extruder=cur)
    if backup: var["probe_position_backup"] = backup
    pr = {"gcode_macro _WM_SETTER": D(s), "print_stats": D(state=state), "gcode_move": D(homing_origin=P(0, 0, 0)),
          "toolhead": D(position=P(*pos), homed_axes="xyz", axis_minimum=P(-15, -3, -5), axis_maximum=P(312, 350, 305)),
          "save_variables": D(variables=var), "configfile": D(settings=D(printer=D(max_accel=20000)))}
    if module: pr["wm_tool_touch"] = D(touch=D(touch or {}))
    out = env.from_string(g).render(params=params or {}, printer=D(pr))
    return [l.strip() for l in out.splitlines() if l.strip() and not l.strip().startswith("#")]


ok = bad = 0


def check(desc, cond):
    global ok, bad
    if cond: ok += 1
    else: bad += 1; print("  FAIL", desc)


def has(lines, text): return any(text in l for l in lines)


names = re.findall(r"^\[gcode_macro (_?WM_SETTER\w*)\]", src, re.M)
for n in names:   # every macro renders in the idle state
    try: run(n)
    except Exception as e: check("%s renders (%s)" % (n, e), False)
check("the helper has its macros and no leftover button macros", len(names) == 37 and "_WM_SETTER_MID_BTN" not in names and "_WM_SETTER_SCRATCH" not in names)
check("[wm_tool_touch] section is in the file", "\n[wm_tool_touch]\n" in src)

o = run("WM_SETTER_PROBE_POSITION")
check("first window: pictures, Start and Cancel", has(o, "prompt_image setter-height setter-place setter-compare") and has(o, "Start|_WM_SETTER_GO|primary") and has(o, "Cancel|_WM_PROMPT_CLOSE"))
check("first window: refused in a print", has(run("WM_SETTER_PROBE_POSITION", state="printing"), "_WM_FAIL"))
o = run("_WM_SETTER_MOVE", pos=(150, 135, 15))
check("start: X, then Y, 5 s of rest, then the sensed lowering", o.index("G0 X297.68 F6000") < o.index("G0 Y286.36 F6000") < o.index("G4 P5000") < o.index("_WM_SETTER_SENSE"))
o = run("_WM_SETTER_SENSE", pos=(297.68, 286.36, 15))
check("sensed lowering: one touch down to the saved Z, two samples that must agree", has(o, "TOOL_CALIBRATE_TOUCH DIRECTION=z- MAX=5.77 NAME=start OPTIONAL=1 SAMPLES=2 SAMPLES_TOLERANCE=0.15"))
check("without the module the lowering is a plain move", run("_WM_SETTER_SENSE", pos=(297.68, 286.36, 15), module=False) == ["_WM_SETTER_DOWN SENSED=0"] and has(run("_WM_SETTER_DOWN", params={"SENSED": "0"}, module=False), "G0 Z9.23 F180"))
o = run("_WM_SETTER_DOWN", {"start": T(True, 0, 0, 10.4)}, {"SENSED": "1"})
check("something met on the way down: the nozzle stays up, error line, window", not has(o, "G0 Z9.23") and has(o, "RESPOND TYPE=error") and o[-1] == "_WM_SETTER_WIN")
o = run("_WM_SETTER_WIN")
check("adjust window: one Find button, step buttons, pictures", sum("prompt_button Find" in l for l in o) == 1 and has(o, "Find automatically|_WM_SETTER_FIND|primary") and sum("_WM_SETTER_STEP AXIS=" in l for l in o) == 24 and has(o, "prompt_image"))
check("step: moves relative, slow", has(run("_WM_SETTER_STEP", params={"AXIS": "Z", "D": "-0.5"}), "G0 Z-0.5 F180"))
check("step: more than 10 mm from the saved X is refused", has(run("_WM_SETTER_STEP", params={"AXIS": "X", "D": "1"}, pos=(307.5, 286.36, 9.23)), "refused") and not has(run("_WM_SETTER_STEP", params={"AXIS": "X", "D": "1"}, pos=(307.5, 286.36, 9.23)), "G0 X"))
check("step: more than 3 mm under the saved Z is refused", has(run("_WM_SETTER_STEP", params={"AXIS": "Z", "D": "-0.5"}, pos=(297.68, 286.36, 6.4)), "refused"))
check("step: another tool head on the carriage stops it", has(run("_WM_SETTER_STEP", params={"AXIS": "X", "D": "1"}, cur=2), "_WM_FAIL"))

o = run("_WM_SETTER_FIND")
check("Find automatically: quick search first (auto 1, scratch 0)", has(o, "VARIABLE=auto VALUE=1") and has(o, "VARIABLE=scratch VALUE=0") and o[-1] == "_WM_SETTER_FIND_TOP")
check("Find automatically: T0 only, and needs the module", has(run("_WM_SETTER_FIND", cur=1), "T0 only") and has(run("_WM_SETTER_FIND", module=False), "wm_tool_touch"))
o = run("_WM_SETTER_FIND_TOP")
check("top: 5 spots behind the start point, low acceleration, 2 samples within 0.05", sum("DIRECTION=z-" in l and "SAMPLES=2 SAMPLES_TOLERANCE=0.05 SAMPLES_TOLERANCE_RETRIES=5" in l for l in o) == 5 and has(o, "G0 X297.68 Y292.16 F600") and has(o, "SET_VELOCITY_LIMIT ACCEL=14") and has(o, "SET_VELOCITY_LIMIT ACCEL=20000"))
tops = {"top0": T(True, 0, 0, 9.70), "top1": T(True, 0, 0, 9.83), "top2": T(True, 0, 0, 9.66), "top3": T(True, 0, 0, 8.65), "top4": T(False)}
o = run("_WM_SETTER_FIND_SIDES", tops)
check("height: average of the touches on the block minus half the tip", has(o, "VARIABLE=ftop VALUE=9.73") and has(o, "VARIABLE=fz VALUE=9.23"))
check("sides: 3 samples within 0.1", sum("SAMPLES=3 SAMPLES_TOLERANCE=0.1 SAMPLES_TOLERANCE_RETRIES=5" in l for l in o) == 2)
check("no top touched: the search fails", run("_WM_SETTER_FIND_SIDES", {})[0].startswith("_WM_SETTER_FIND_FAIL"))
check("top 3 mm off: the search fails", run("_WM_SETTER_FIND_SIDES", {"top0": T(True, 0, 0, 5.0), "top1": T(True, 0, 0, 5.1)})[0].startswith("_WM_SETTER_FIND_FAIL"))
# F-093: the run of 2026-11-16 21:06, one false touch in the air at 10.23 above the real top 9.68 / 9.67
o = run("_WM_SETTER_FIND_SIDES", {"top0": T(True, 0, 0, 9.6831), "top1": T(True, 0, 0, 10.2262), "top2": T(True, 0, 0, 9.6678), "top3": T(True, 0, 0, 8.7756), "top4": T(True, 0, 0, 8.6591)})
check("a lone highest top touch is dropped, the two that agree are the top", has(o, "VARIABLE=ftop VALUE=9.675") and has(o, "VARIABLE=fz VALUE=9.175"))
o = run("_WM_SETTER_FIND_SIDES", {"top0": T(True, 0, 0, 9.68), "top1": T(True, 0, 0, 10.23), "top3": T(True, 0, 0, 8.77)})
check("no two top touches agree: the search fails", o[0].startswith("_WM_SETTER_FIND_FAIL") and "did not agree" in o[0])
o = run("_WM_SETTER_FIND_FAIL", params={"MSG": "x."}, auto=1, scratch=0)
check("failed quick search: nozzle up, window that asks before the wide search", has(o, "G0 Z17.23") and o[-1].startswith("_WM_SETTER_WIDE_ASK") and not has(o, "_WM_SETTER_MOVE"))
o = run("_WM_SETTER_WIDE_ASK", params={"MSG": "x."})
check("wide search window: Start and Cancel", has(o, "Start the wide search|_WM_SETTER_SCRATCH_GO|primary") and has(o, "Cancel|_WM_SETTER_WIDE_CANCEL"))
o = run("_WM_SETTER_FIND_FAIL", params={"MSG": "x."}, auto=1, scratch=1)
check("failed wide search: stops, back to the saved position", has(o, "RESPOND TYPE=error") and o[-1] == "_WM_SETTER_MOVE")
o = run("_WM_SETTER_SCRATCH_GO")
check("wide search: starts 10 mm left of the saved X, 3 sweeps of 22 mm, 4 mm apart", has(o, "G0 X287.68 Y286.36 F3000") and sum("DIRECTION=x+ MAX=22.0" in l for l in o) == 3 and has(o, "Y282.36") and has(o, "Y290.36"))
full = dict(yn=T(True, 297.7, 290.77, 9.23), xn=T(True, 303.17, 286.3, 9.23), yf=T(True, 297.7, 293.55, 9.23), xf=T(True, 305.98, 286.3, 9.23))
o = run("_WM_SETTER_FIND_DONE", full, fz=9.23, auto=1)
check("found: X Y from the four faces, then the block middles", has(o, "G0 X297.68 Y286.36 F1200") and has(o, "VARIABLE=mx0 VALUE=297.68") and o[-1] == "_WM_SETTER_MID")
o = run("_WM_SETTER_FIND_DONE", dict(full, xf=T(True, 307.2, 286.3, 9.23)), fz=9.23, auto=1)
check("wrong touched width: the search fails", o[0].startswith("_WM_SETTER_FIND_FAIL") and "widths" in o[0])
o = run("_WM_SETTER_MID")
check("block middles: touch 1 starts 4.5 mm left at the back block's depth", has(o, "G0 X293.18 F1200") and has(o, "G0 Y292.16 F1200") and has(o, "DIRECTION=x+ MAX=6.5 NAME=ml"))
# F-114: the ends are touched 1.0 mm below the block top, the cone makes a block look about 0.6 mm longer (6.44 and 6.68 mm here, as measured on the printer)
ends = dict(ml=T(True, 295.245, 292.16, 9.23), mr=T(True, 301.685, 292.16, 9.23), mf=T(True, 304.58, 282.555, 9.23), mb=T(True, 304.58, 289.235, 9.23))
check("block middles: the place right of the back block is never past the right block's middle + 1.5", has(run("_WM_SETTER_MID_B", dict(ends, ml=T(True, 299.9, 0, 0))), "G0 X306.08 Y292.16"))
check("block middles: something under the nozzle skips that end", has(run("_WM_SETTER_MID_C", dict(ends, d2=T(True, 0, 0, 9.7))), "VARIABLE=mskip VALUE=1") and not has(run("_WM_SETTER_MID_C", dict(ends, d2=T(True, 0, 0, 9.7))), "NAME=mr"))
o = run("_WM_SETTER_MID_DONE", ends, mskip=0, auto=1)
check("block middles: middles, widths and the two offsets", has(o, "VARIABLE=mbx VALUE=298.465") and has(o, "VARIABLE=mwx VALUE=6.44") and has(o, "VARIABLE=mwy VALUE=6.68") and has(o, "VARIABLE=mry VALUE=285.895") and has(o, "VARIABLE=mnx VALUE=6.11") and has(o, "VARIABLE=mny VALUE=6.27") and has(o, "VARIABLE=mok VALUE=1") and o[-1] == "_WM_SETTER_FOUND")
o = run("_WM_SETTER_MID_DONE", dict(ends, mb=T(False, 0, 0, 0)), mskip=0, auto=1)
check("block middles: the right block back end missing, its middle from the front end and the known length (F-114)", has(o, "VARIABLE=mry VALUE=285.775") and has(o, "VARIABLE=mwy VALUE=6.44") and has(o, "VARIABLE=mok VALUE=1") and has(o, "taken from the front end"))
check("block middles: a wrong width is not offered for saving", has(run("_WM_SETTER_MID_DONE", dict(ends, mr=T(True, 303.0, 0, 0)), mskip=0, auto=1), "VARIABLE=mok VALUE=0"))
r = dict(mok=1, mbx=298.465, mwx=5.93, mry=285.895, mwy=6.13, mnx=6.12, mny=6.26, auto=1, fdx=2.81, fdy=2.78, ftop=9.73)
o = run("_WM_SETTER_FOUND", ends, **r)
check("result window: Save with middles first, Save found second, pictures", has(o, "Save with middles|_WM_SETTER_MID_SAVE|primary") and has(o, "Save found|_WM_SETTER_SAVE CONFIRM=1|secondary") and has(o, "prompt_image") and has(o, "BACK BLOCK") and has(o, "RIGHT BLOCK"))
o = run("_WM_SETTER_FOUND", ends, **dict(r, mok=0, mwx=0, mwy=0))
check("result window without the middles: only Save found", has(o, "Save found|_WM_SETTER_SAVE CONFIRM=1|primary") and not has(o, "Save with middles"))
o = run("_WM_SETTER_MID_SAVE", ends, **r)
check("Save with middles: start on the middles, the two offsets, old line kept", has(o, "SAVE_VARIABLE VARIABLE=probe_position_backup VALUE=297.68,286.36,9.23,6.9,5.8") and any(re.match(r"SAVE_VARIABLE VARIABLE=probe_position VALUE=298\.4[67],285\.(?:89|9),9\.23,6\.12,6\.26$", l) for l in o) and has(o, "VARIABLE=sz VALUE=9.23") and o[-1] == "_WM_SETTER_AFTER")
check("Save with middles: refuses offsets far from the usual ones", has(run("_WM_SETTER_MID_SAVE", ends, **dict(r, mnx=12.0)), "_WM_FAIL"))
o = run("_WM_SETTER_SAVE", params={"CONFIRM": "1"}, pos=(297.7, 286.4, 9.3))
check("Save found: X Y Z of the nozzle, the two last numbers stay, old line kept", has(o, "SAVE_VARIABLE VARIABLE=probe_position VALUE=297.7,286.4,9.3,6.9,5.8") and has(o, "VARIABLE=probe_position_backup VALUE=297.68,286.36,9.23,6.9,5.8"))
o = run("_WM_SETTER_AFTER", backup=(298.5, 285.5, 9.3, 6.9, 5.8), active=0)
check("after a save: Test with T0, Offsets rapid, Restore old", has(o, "Test with T0|_WM_SETTER_TEST|primary") and has(o, "Run Offsets rapid|_WM_SETTER_RAPID") and has(o, "Restore old|_WM_SETTER_RESTORE|error"))
o = run("_WM_SETTER_RESTORE", params={"CONFIRM": "1"}, backup=(298.5, 285.5, 9.3, 6.9, 5.8))
check("Restore old: the two lines change places", has(o, "SAVE_VARIABLE VARIABLE=probe_position VALUE=298.5,285.5,9.3,6.9,5.8") and has(o, "SAVE_VARIABLE VARIABLE=probe_position_backup VALUE=297.68,286.36,9.23,6.9,5.8"))
# F-143: cal = 2, the First Run Calibration's own setter stage: find, measure the middles, save, no windows, any problem raises
o = run("_WM_SETTER_AUTO")
check("first run stage 1: sets cal 2 and cal_ok 0, then starts the helper and checks the result", has(o, "VARIABLE=cal VALUE=2") and has(o, "VARIABLE=cal_ok VALUE=0") and o.index("_WM_SETTER_GO") > [i for i, l in enumerate(o) if "VARIABLE=cal VALUE=2" in l][0] and o[-1] == "_WM_SETTER_AUTO_CHECK")
check("first run stage 1: the check stops the calibration when nothing was saved", has(run("_WM_SETTER_AUTO_CHECK", cal_ok=0), "_WM_FAIL") and not has(run("_WM_SETTER_AUTO_CHECK", cal_ok=1), "_WM_FAIL"))
o = run("_WM_SETTER_FIND_DONE", full, fz=9.23, auto=1, cal=2)
check("first run stage 1: a good quick search goes on to the block middles, no window, no offsets", o[-1] == "_WM_SETTER_MID" and has(o, "VARIABLE=mx0 VALUE=297.68") and not has(o, "_WM_ZCAL_DONE") and not has(o, "WM_OFFSETS_RAPID") and not has(o, "VARIABLE=cal VALUE=0"))
o = run("_WM_SETTER_FIND_FAIL", params={"MSG": "no luck"}, cal=2, auto=1)
check("first run stage 1: a failed search raises an error and opens no window", has(o, "_WM_FAIL") and not has(o, "_WM_SETTER_WIDE_ASK") and not has(o, "_WM_ZCAL_DONE") and has(o, "VARIABLE=cal VALUE=0"))
o = run("_WM_SETTER_DOWN", {"start": T(True, 0, 0, 9.5)}, params={"SENSED": "1"}, cal=2)
check("first run stage 1: the nozzle meeting something on the way down raises an error", has(o, "_WM_FAIL") and has(o, "VARIABLE=cal VALUE=0"))
o = run("_WM_SETTER_MID_DONE", ends, mskip=0, auto=1, cal=2)
check("first run stage 1: the middles go to the quiet save, not to the result window", o[-1] == "_WM_SETTER_AUTO_FINISH" and not has(o, "_WM_SETTER_FOUND"))
check("first run stage 1: complete middles are saved quietly, incomplete ones stop", has(run("_WM_SETTER_AUTO_FINISH", mok=1), "_WM_SETTER_MID_SAVE QUIET=1") and has(run("_WM_SETTER_AUTO_FINISH", mok=0), "_WM_FAIL") and not has(run("_WM_SETTER_AUTO_FINISH", mok=0), "_WM_SETTER_MID_SAVE"))
o = run("_WM_SETTER_MID_SAVE", ends, params={"QUIET": "1"}, **r)
check("first run stage 1: the quiet save writes probe_position, sets cal_ok 1, opens no window", has(o, "SAVE_VARIABLE VARIABLE=probe_position VALUE=") and has(o, "VARIABLE=cal_ok VALUE=1") and not has(o, "_WM_SETTER_AFTER") and has(o, "_WM_SETTER_AWAY"))
check("the normal Save with middles still opens its window", has(run("_WM_SETTER_MID_SAVE", ends, **r), "_WM_SETTER_AFTER") and not has(run("_WM_SETTER_MID_SAVE", ends, **r), "VARIABLE=cal_ok VALUE=1"))
check("no window text holds a character that breaks RESPOND", not re.search(r'action:prompt_(?:text|button|begin)[^\n"]*[;#*]', src[src.index("tool setter position helper"):]))
print("tool setter helper: %d ok, %d failed" % (ok, bad))
sys.exit(1 if bad else 0)
