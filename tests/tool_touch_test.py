"""wm_tool_touch.py (TOOL_CALIBRATE_TOUCH) against a fake printer.  python3 -I tests/tool_touch_test.py MODULE_FILE"""
import importlib.util
import sys

spec = importlib.util.spec_from_file_location("wm_tool_touch", sys.argv[1])
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class CmdError(Exception):
    pass


class Gcmd:
    error = CmdError
    def __init__(s, **p): s.p = {k.upper(): v for k, v in p.items()}; s.info = []
    def get(s, k, d=None): return s.p.get(k, d)
    def get_int(s, k, d=None, **kw): return int(s.p.get(k, d))
    def get_float(s, k, d=None, above=None, minval=None, maxval=None):
        v = float(s.p.get(k, d))
        if maxval is not None and v > maxval: raise CmdError("%s must be at most %s" % (k, maxval))
        return v
    def respond_info(s, m): s.info.append(m)


class Toolhead:
    def __init__(s): s.pos = [100.0, 50.0, 10.0, 0.0]; s.max_accel = 20000.0; s.moves = []; s.dwells = []
    def get_position(s): return list(s.pos)
    def manual_move(s, c, sp): s.moves.append(list(c)); s.pos[:3] = [c[i] if c[i] is not None else s.pos[i] for i in range(3)]
    def dwell(s, t): s.dwells.append(t)


class Endstop:
    def __init__(s): s.ended = 0
    def multi_probe_end(s): s.ended += 1


class Probe:
    def __init__(s, results): s.results = list(results); s.calls = []; s.mcu_probe = [Endstop(), Endstop(), Endstop()]
    def run_probe(s, direction, gcmd, speed_ratio=1.0, samples=None, max_distance=100.0):
        s.calls.append((direction, speed_ratio, samples, max_distance))
        r = s.results.pop(0)
        if isinstance(r, Exception): raise r
        return r


class Calibrate:
    def __init__(s, results): s.probe_multi_axis = Probe(results); s.lift_speed = 5.0


class Gcode:
    def __init__(s): s.scripts = []; s.cmds = {}
    def register_command(s, n, f, desc=None): s.cmds[n] = f
    def run_script_from_command(s, t): s.scripts.append(t)


class Coll:
    def __init__(s): s.off = 0
    def cmd_disable(s): s.off += 1


class Printer:
    command_error = CmdError
    def __init__(s, results, have=True):
        s.o = {"gcode": Gcode(), "toolhead": Toolhead(), "collision_detect": Coll()}
        if have: s.o["tools_calibrate"] = Calibrate(results)
    def lookup_object(s, n, d="x"):
        if n in s.o: return s.o[n]
        if d == "x": raise KeyError(n)
        return d
    def is_shutdown(s): return False


class Config:
    def __init__(s, pr): s.pr = pr
    def get_printer(s): return s.pr


def make(results, have=True):
    pr = Printer(results, have)
    return pr, mod.load_config(Config(pr))


ok = bad = 0


def check(desc, cond):
    global ok, bad
    if cond: ok += 1
    else: bad += 1; print("  FAIL", desc)


pr, t = make([[100.0, 54.2, 10.0]])
g = Gcmd(direction="y+", max="18", name="yn", optional="1")
t.cmd_TOOL_CALIBRATE_TOUCH(g)
st = t.get_status(0)["touch"]["yn"]
check("a touch: result kept under NAME, nozzle back at the start", st["found"] and st["y"] == 54.2 and pr.o["toolhead"].pos[:3] == [100.0, 50.0, 10.0])
check("a touch: low acceleration before, the old one after, a rest first", pr.o["gcode"].scripts == ["SET_VELOCITY_LIMIT ACCEL=14.0", "SET_VELOCITY_LIMIT ACCEL=20000.0"] and pr.o["toolhead"].dwells[0] == 0.6)
check("a side touch runs at full probe speed with the travel limit", pr.o["tools_calibrate"].probe_multi_axis.calls == [("y+", 1.0, 1, 18.0)])
check("registered as TOOL_CALIBRATE_TOUCH", "TOOL_CALIBRATE_TOUCH" in pr.o["gcode"].cmds)

pr, t = make([[100.0, 50.0, 7.5]])
t.cmd_TOOL_CALIBRATE_TOUCH(Gcmd(direction="z-", max="11", name="top0", optional="1"))
check("a touch from above runs at half speed", pr.o["tools_calibrate"].probe_multi_axis.calls[0][1] == 0.5 and t.get_status(0)["touch"]["top0"]["z"] == 7.5)

pr, t = make([[100.0, 50.05, 10.0], [100.0, 54.2, 10.0]])
g = Gcmd(direction="y+", name="yn", optional="1", max="18")
t.cmd_TOOL_CALIBRATE_TOUCH(g)
check("a result without travel is a false touch: repeated", t.get_status(0)["touch"]["yn"]["y"] == 54.2 and len(pr.o["tools_calibrate"].probe_multi_axis.calls) == 2 and any("tripped" in m for m in g.info))

pr, t = make([[100.0, 50.0, 10.0]] * 5)
g = Gcmd(direction="y+", name="yn", optional="1", max="18")
t.cmd_TOOL_CALIBRATE_TOUCH(g)
check("five false touches in a row: no result, no error with OPTIONAL=1", t.get_status(0)["touch"]["yn"]["found"] is False and any("did not agree" in m for m in g.info) and pr.o["gcode"].scripts[-1] == "SET_VELOCITY_LIMIT ACCEL=20000.0")

pr, t = make([CmdError("No trigger on probe after full movement")])
g = Gcmd(direction="x+", name="lane0", optional="1", max="22")
t.cmd_TOOL_CALIBRATE_TOUCH(g)
check("no touch within MAX with OPTIONAL=1: found False, back at the start, acceleration back", t.get_status(0)["touch"]["lane0"]["found"] is False and any("no touch within 22.00" in m for m in g.info) and pr.o["gcode"].scripts[-1] == "SET_VELOCITY_LIMIT ACCEL=20000.0" and pr.o["tools_calibrate"].probe_multi_axis.mcu_probe[0].ended == 1)

pr, t = make([CmdError("Probe samples exceed samples_tolerance")])
g = Gcmd(direction="x+", name="xn", optional="1")
t.cmd_TOOL_CALIBRATE_TOUCH(g)
check("touches that do not agree with OPTIONAL=1: found False", t.get_status(0)["touch"]["xn"]["found"] is False and any("did not agree" in m for m in g.info))

pr, t = make([CmdError("No trigger on probe after full movement")])
try:
    t.cmd_TOOL_CALIBRATE_TOUCH(Gcmd(direction="x+", name="xn")); raised = False
except CmdError:
    raised = True
check("without OPTIONAL a miss is an error, collision detection off, acceleration back", raised and pr.o["collision_detect"].off == 1 and pr.o["gcode"].scripts[-1] == "SET_VELOCITY_LIMIT ACCEL=20000.0")

for bad_args, why in ((dict(direction="z+"), "DIRECTION"), (dict(direction="x+", max="41"), "MAX")):
    pr, t = make([[0, 0, 0]])
    try:
        t.cmd_TOOL_CALIBRATE_TOUCH(Gcmd(**bad_args)); raised = False
    except CmdError:
        raised = True
    check("refuses a wrong %s" % why, raised and pr.o["gcode"].scripts == [])
pr, t = make([], have=False)
try:
    t.cmd_TOOL_CALIBRATE_TOUCH(Gcmd(direction="x+")); raised = False
except CmdError:
    raised = True
check("without [tools_calibrate]: a clear error", raised)
print("wm_tool_touch: %d ok, %d failed" % (ok, bad))
sys.exit(1 if bad else 0)
