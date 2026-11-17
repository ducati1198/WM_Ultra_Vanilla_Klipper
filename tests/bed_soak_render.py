"""Renders the bed warp wait of rpi-cfg/rpi_base.cfg (Klipper-style jinja2, mock printer) and checks its rules.
Run: python3 -I tests/bed_soak_render.py"""
import os, re, sys
import jinja2

P = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "rpi-cfg", "rpi_base.cfg")
macros, cur, body = {}, None, None
for line in open(P, encoding="utf-8"):
    m = re.match(r"^\[(gcode_macro|delayed_gcode)\s+(\S+)\]", line)
    if m:
        cur = m.group(2); macros[cur] = []; body = None; continue
    if line.startswith("["):
        cur = None
    if cur is None:
        continue
    if re.match(r"^gcode:\s*$", line):
        body = macros[cur]
    elif body is not None:
        body.append(line[4:] if line.startswith("    ") else line)
macros = {k: "".join(v) for k, v in macros.items()}
PARAMS = {"bed_warp_wait_multiplier": 2.0, "bed_warp_fraction_wait": 0.75, "bed_warp_wait_interval": 15, "bed_warp_no_wait": 0.99,
          "bed_warp_measured_floor": 2.0, "bed_warp_min_bed": 30}
FAILED = []


def wait(target, start, sv=None):
    env = jinja2.Environment("{%", "%}", "{", "}")
    printer = {"save_variables": {"variables": dict(sv or {})}, "heater_bed": {"target": target, "temperature": start},
               "gcode_macro _WM_BED_SOAK_PARAMS": PARAMS, "gcode_macro _WM_BED_SOAK_STATE": {"start_bed": start}}
    out = env.from_string(macros["_WM_BED_SOAK"]).render(printer=printer, params={"BED": str(target)})
    lines = [l.strip() for l in out.splitlines() if l.strip() and not l.strip().startswith("#")]
    total = sum(int(l.split("P")[1]) for l in lines if l.startswith("G4 P")) // 1000
    return total, lines


def check(name, cond):
    print(("  ok    " if cond else "  FAIL  ") + name)
    if not cond:
        FAILED.append(name)


t, l = wait(55, 22.7)
check("cold bed, 55 C: 2 s per degree x 55 = 110 s, with a line every 15 s", t == 110 and sum(1 for x in l if "s left" in x) == 7 and any("110 s" in x for x in l))
t, l = wait(60, 50)
check("bed already at 50 of 60 C (above 75 percent): only the missing 10 degrees x 2 = 20 s", t == 20)
t, l = wait(55, 56.5)
check("bed already at the target: no wait", t == 0 and any("no wait" in x for x in l))
t, l = wait(60, 20, {"wm_bed_soak": 0})
check("switch off: no wait", t == 0 and any("is off" in x for x in l))
t, l = wait(0, 20)
check("bed not heated: no wait", t == 0 and any("not heated" in x for x in l))
t, l = wait(60, 20, {"wm_bed_soak_t60": 200})
check("measured 200 s at 60 C: 60 C waits 200 s", t == 200 and any("measured at 60 C" in x for x in l))
t, l = wait(100, 20, {"wm_bed_soak_t60": 200})
check("other temperature: nearest measured value scaled per degree (100 C = 333 s)", t == 333)
t, l = wait(60, 20, {"wm_bed_soak_t60": 30})
check("a measured wait is never under 2 s per degree (60 C at least 120 s)", t == 120)
check("the switch is on by default ([output_pin Bed_Warp_Stabilisation] value 1, saved default 1)",
      re.search(r"\[output_pin Bed_Warp_Stabilisation\]\npin: wm_pin:bed_warp_stabilisation\npwm: False\nvalue: 1", open(P).read()) is not None
      and "wm_bed_soak|default(1)" in macros["_WM_BED_SOAK"])
check("no digit followed by letters in a macro name (Klipper would read it as a command plus a parameter)",
      not [n for n in macros if re.search(r"\d[A-Za-z]", n)])
print("\npassed: %d  failed: %d" % (10 - len(FAILED), len(FAILED)))
sys.exit(1 if FAILED else 0)
