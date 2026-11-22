#!/usr/bin/env python3
"""Offline check of config/rpi_estep.cfg: every gcode block must compile as a Klipper (Jinja2) template, and the main macros
are rendered with made-up printer data so the produced lines can be read. Needs jinja2. Run:  python3 tests/estep_render.py"""
import configparser
import os
import sys

import jinja2

HERE = os.path.dirname(os.path.abspath(__file__))
CFG = os.path.join(HERE, "..", "rpi-cfg", "rpi_nozzle.cfg")


def load():
    cp = configparser.RawConfigParser(strict=False, inline_comment_prefixes=None)
    cp.optionxform = str
    cp.read(CFG)
    return cp


def env():
    # same delimiters as Klipper's gcode_macro
    return jinja2.Environment("{%", "%}", "{", "}", trim_blocks=False)


class Dot(dict):
    __getattr__ = dict.get


def mk(d):
    return Dot({k: (mk(v) if isinstance(v, dict) else v) for k, v in d.items()})


def printer(state="standby", count=4, ext_temp=220.0, t=1, entry="", prev="extruder", cur=99, homed="xyz", fil=True, old=21.018):
    p = {
        "print_stats": {"state": state},
        "save_variables": {"variables": {"thr_number": count, "current_extruder": cur}},
        "toolhead": {"extruder": prev, "homed_axes": homed},
        "configfile": {"settings": {
            "gcode_shell_command wm_estep": {},
            "extruder": {"rotation_distance": 21.018}, "extruder1": {"rotation_distance": 21.018},
            "extruder2": {"rotation_distance": 21.018}, "extruder3": {"rotation_distance": 21.5}}},
        "gcode_macro _WM_ESTEP": {"t": t, "ext": "extruder%d" % t if t else "extruder", "prev": prev, "old": old,
                                  "entry": entry, "mark": 120, "len": 100, "temp": 220},
        "extruder": {"temperature": ext_temp}, "extruder1": {"temperature": ext_temp},
        "filament_switch_sensor filament0": {"filament_detected": False}, "filament_switch_sensor filament1": {"filament_detected": fil},
        "filament_switch_sensor filament2": {"filament_detected": True}, "filament_switch_sensor filament3": {"filament_detected": True},
        "gcode_macro _WM_HEAD_QUEUE": {},
    }
    return mk(p)


def render(cp, name, params=None, **kw):
    sec = "delayed_gcode " + name if name.endswith("HEATWATCH") else "gcode_macro " + name
    text = cp[sec]["gcode"]
    tpl = env().from_string(text)
    lines = [l.strip() for l in tpl.render(printer=printer(**kw), params=dict(params or {})).splitlines() if l.strip()]
    return lines


def main():
    cp = load()
    bad = 0
    for sec in cp.sections():
        if sec.startswith("gcode_macro") or sec.startswith("delayed_gcode"):
            try:
                env().from_string(cp[sec]["gcode"])
            except Exception as e:
                print("FAIL compile", sec, e)
                bad += 1
    print("compiled %d macro blocks, %d errors" % (len([s for s in cp.sections() if "gcode" in s]), bad))
    shots = [
        ("WM_ESTEP_CAL", {}, {}), ("WM_ESTEP_CAL", {"T": 2}, {}), ("WM_ESTEP_CAL", {}, {"state": "printing"}),
        ("_WM_ESTEP_START", {"T": 1}, {}), ("_WM_ESTEP_WAIT", {"MSG": "Please wait, test."}, {}), ("_WM_ESTEP_MARK", {}, {}), ("_WM_ESTEP_UNLOAD", {}, {}), ("_WM_ESTEP_UNLOAD", {}, {"state": "printing"}), ("_WM_ESTEP_REMOVE", {}, {}), ("_WM_ESTEP_ZERO", {}, {}), ("_WM_ESTEP_BACK", {}, {}), ("_WM_ESTEP_WAIT", {}, {}), ("_WM_ESTEP_HEATWIN", {}, {"ext_temp": 150.0}), ("_WM_ESTEP_HEATWATCH", {}, {"ext_temp": 150.0}), ("_WM_ESTEP_HEATWATCH", {}, {"ext_temp": 219.0}), ("_WM_ESTEP_HEATWATCH", {}, {"state": "printing"}), ("_WM_ESTEP_MOVE", {"LEN": 100, "SPEED": 60, "WAIT": "Please wait."}, {}), ("_WM_ESTEP_S1", {}, {}), ("_WM_ESTEP_HEAT", {}, {}), ("_WM_ESTEP_S2", {}, {}),
        ("_WM_ESTEP_MOVE", {"LEN": 100, "SPEED": 60}, {}), ("_WM_ESTEP_INSERT", {}, {}), ("_WM_ESTEP_GUARD", {}, {}), ("_WM_ESTEP_AFTER_INSERT", {}, {"fil": True}), ("_WM_ESTEP_AFTER_INSERT", {}, {"fil": False}), ("_WM_ESTEP_NOFIL", {}, {}), ("_WM_ESTEP_RUN", {}, {"fil": False}), ("_WM_ESTEP_RUN", {}, {"fil": True}), ("_WM_ESTEP_CANCEL", {}, {"cur": 1}),
        ("_WM_ESTEP_MOVE", {"LEN": -100, "SPEED": 600}, {}), ("_WM_ESTEP_MOVE", {"LEN": 30}, {}),
        ("_WM_ESTEP_HOTCHECK", {}, {"ext_temp": 120.0}),
        ("_WM_ESTEP_POS", {}, {"cur": 99, "homed": "xyz"}), ("_WM_ESTEP_POS", {}, {"cur": 99, "homed": ""}),
        ("_WM_ESTEP_POS", {}, {"cur": 1, "homed": "xyz"}), ("_WM_ESTEP_POS", {}, {"cur": 0, "homed": ""}),
        ("_WM_ESTEP_POS", {}, {"cur": 2, "homed": "xy"}),
        ("_WM_ESTEP_POS2", {}, {"homed": "xyz"}), ("_WM_ESTEP_POS2", {}, {"homed": "xy"}), ("_WM_ESTEP_POS2", {}, {"homed": ""}),
        ("_WM_ESTEP_PARK", {}, {"cur": 1}), ("_WM_ESTEP_PARK", {}, {"cur": 99}), ("_WM_ESTEP_PARK", {}, {"cur": 1, "state": "printing"}),
        ("_WM_ESTEP_MEASPIC", {}, {}), ("_WM_ESTEP_S3", {}, {"entry": "20.0"}), ("_WM_ESTEP_S3", {}, {"entry": "17.0", "old": 0.0}), ("_WM_ESTEP_S3", {}, {"entry": "", "old": 0.0}), ("_WM_ESTEP_S3", {}, {"entry": "17.0"}), ("_WM_ESTEP_S3", {}, {"entry": "3.0"}), ("_WM_ESTEP_S3", {}, {"entry": "0.0"}), ("_WM_ESTEP_S3", {}, {"entry": "24.5"}),
        ("_WM_ESTEP_STEP", {"D": -1}, {"entry": "20.0"}), ("_WM_ESTEP_STEP", {"D": -0.1}, {"entry": "17.0"}), ("_WM_ESTEP_STEP", {"D": 5}, {"entry": "58.0"}),
        ("_WM_ESTEP_STEP", {"D": -5}, {"entry": "2.0"}), ("_WM_ESTEP_SET", {"MEAS": "17.3"}, {}), ("_WM_ESTEP_SET", {"MEAS": "99"}, {}), ("_WM_ESTEP_SET", {}, {}),
        ("_WM_ESTEP_CONFIRM", {}, {"entry": "17.0"}), ("_WM_ESTEP_SAVE", {}, {"entry": "17.0"}), ("_WM_ESTEP_SAVE", {}, {"entry": "0.0"}), ("_WM_ESTEP_SAVE", {}, {"entry": "62"}),
        ("_WM_ESTEP_WIPEPARK", {}, {"cur": 0}), ("_WM_ESTEP_WIPEPARK", {}, {"cur": 99}), ("_WM_ESTEP_WIPEPARK", {}, {"cur": 0, "state": "printing"}),
        ("_WM_ESTEP_BACK", {}, {}), ("_WM_ESTEP_FINISH", {}, {}),
    ]
    for name, params, kw in shots:
        print("\n== %s %s %s" % (name, params or "", kw or ""))
        try:
            for l in render(cp, name, params, **kw):
                print("   " + l)
        except Exception as e:
            print("   FAIL render:", e)
            bad += 1
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
