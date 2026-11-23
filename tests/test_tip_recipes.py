#!/usr/bin/env python3
"""F-223: the unload tip recipe is chosen by the material saved for the toolhead (zr_tools.cfg _WM_LOAD_SETTINGS / _WM_UNLOAD_TIP).
Reads the config the way Klipper does (cuts at # and ;), renders _WM_UNLOAD_TIP and checks which recipe each material gets."""
import ast, configparser, os, sys
import jinja2

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = os.path.join(ROOT, "zr_tools", "zr_tools.cfg")
KEYS = ("pre_cool", "snap_mm", "snap_speed", "cool_drop", "cool_s", "cool_moves", "cool_move_mm", "cool_move_speed", "pull_mm", "pull_speed")
fails = []


def check(name, ok):
    print(("  ok   " if ok else "  FAIL ") + name)
    if not ok:
        fails.append(name)


def macro(name):
    cp = configparser.RawConfigParser(strict=False, inline_comment_prefixes=("#", ";"))
    cp.optionxform = str
    cp.read(CFG)
    return cp["gcode_macro " + name]


st = macro("_WM_LOAD_SETTINGS")
v = {k[9:]: ast.literal_eval(x) for k, x in st.items() if k.startswith("variable_")}
env = jinja2.Environment(variable_start_string="{", variable_end_string="}")
tpl = env.from_string(macro("_WM_UNLOAD_TIP")["gcode"])


def render(mat, temp, minx=175):
    sv = {} if mat is None else {"zr_t1_mat": mat}
    printer = {"gcode_macro _WM_LOAD_SETTINGS": v, "configfile": {"settings": {"extruder1": {"min_extrude_temp": minx}}},
               "save_variables": {"variables": sv}}
    out = tpl.render(printer=printer, params={"T": "1", "S": str(temp)})
    return [l.strip() for l in out.split("\n") if l.strip()]


def recipe_of(lines):
    for l in lines:
        if "forming the tip (" in l:
            return l.split("forming the tip (")[1].split(" recipe")[0].lower()
    return ""


check("every recipe has every value and the default recipe exists",
      v["tip_default"] in v["tip_recipes"] and all(set(KEYS) <= set(r) for r in v["tip_recipes"].values()))
check("every material in the list points at a recipe that exists, and the codes are text",
      all(isinstance(k, str) and r in v["tip_recipes"] for k, r in v["tip_materials"].items()))
check("PLA family (codes 1 to 5) gets the PLA recipe", all(recipe_of(render(m, 210)) == "pla" for m in (1, 2, 3, 4, 5)))
check("PETG and PETG-CF (6, 7) get the PETG recipe", all(recipe_of(render(m, 240)) == "petg" for m in (6, 7)))
check("ABS (8) gets the ABS recipe", recipe_of(render(8, 260)) == "abs")
check("no material saved, code 0 and an unknown code get the default recipe",
      all(recipe_of(render(m, 220)) == v["tip_default"] for m in (None, 0, 11, 15, 99)))
check("a material code saved as text works too", recipe_of(render("6", 240)) == "petg")
o = render(6, 240)
r = v["tip_recipes"]["petg"]
check("PETG at 240: snap of the recipe, cooling target 240 - cool_drop, the moves, then the pull",
      "G1 E-%s F%s" % (r["snap_mm"], float(r["snap_speed"]) * 60) in o
      and "SET_HEATER_TEMPERATURE HEATER=extruder1 TARGET=%s" % (240.0 - r["cool_drop"]) in o
      and sum(1 for l in o if l == "G1 E-%s F%s" % (r["cool_move_mm"], float(r["cool_move_speed"]) * 60)) == r["cool_moves"]
      and "G1 E-%s F%s" % (r["pull_mm"], float(r["pull_speed"]) * 60) in o)
o = render(1, 185)
targets = [float(l.split("TARGET=")[1]) for l in o if "TARGET=" in l and not l.endswith("TARGET=0")]
check("no cooling target goes below min_extrude_temp + 5 (PLA at 185 C, limit 175)", all(t >= 180 for t in targets))
check("prompt-safe console text: no ; # * in the RESPOND lines", all(not any(c in l for c in ";#*") for l in o if l.startswith("RESPOND")))
print("\n%d checks, %d failed" % (10, len(fails)))
sys.exit(1 if fails else 0)
