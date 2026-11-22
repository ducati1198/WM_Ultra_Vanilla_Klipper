#!/usr/bin/env python3
"""Renders every macro of rpi-cfg/rpi_calibration.cfg and rpi-cfg/rpi_nozzle.cfg with jinja2 (Klipper style: { } for expressions) and a mock printer.
Run: python3 tests/rpi_cfg_render.py      (needs jinja2; exit 0 = all good, 77 = jinja2 not installed)"""
import os, re, sys
try:
    import jinja2
except ImportError:
    sys.exit(77)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
text = open(os.path.join(ROOT, "rpi-cfg", "rpi_calibration.cfg")).read() + "\n" + open(os.path.join(ROOT, "rpi-cfg", "rpi_nozzle.cfg")).read()
macros = {m.group(1): m.group(2) for m in re.finditer(r'^\[gcode_macro (\S+)\]\n(?:.*\n)*?gcode:\n((?:(?:    .*|)\n)+)', text, re.M)}
HEAT = ['heater_bed', 'extruder', 'extruder1', 'extruder2', 'extruder3', 'heater_generic chamber']
class Raise(Exception): pass
env = jinja2.Environment(variable_start_string='{', variable_end_string='}')
def run(name, params=None, target=None, control='pid', printing='standby', chamber=True, sv=None, temps=None, docks=None, shell=True, ids=None, actual=None, canids=True, fil=None, ace=False, full=0, screws=True, homed='xyz', pend=None, done_t=-100.0):
    svars = {'thr_number': 4, 'current_extruder': 0, 'fail_flag': 0, 'fail_tool': 99, 'is_nozzle_setting': 0, 't0_offset': [0.0, 0.0, 0.0], 't1_offset': [0.28, 0.34, -0.026], 't2_offset': [0.27, 0.35, 0.059], 't3_offset': [0.30, 0.09, 0.136]}; svars.update(sv or {})
    printer = {'save_variables': {'variables': svars},
               'print_stats': {'state': printing}, 'heaters': {'available_heaters': HEAT}, 'toolhead': {'homed_axes': homed, 'estimated_print_time': 1000.0},
               'configfile': {'settings': dict({'bed_mesh': {'probe_count': [9, 9]}}, **{h: {'control': control} for h in (HEAT[:5] + (HEAT[5:] if chamber else []))})}}
    for h in HEAT: printer[h] = {'target': (target or {}).get(h, 0.0), 'temperature': (temps or {}).get(h, 25.0)}
    cs = printer['configfile']['settings']
    printer['configfile']['save_config_pending_items'] = pend or {}
    printer.setdefault('gcode_macro _WM_FIRST_RUN_CAL_DONE', {'done_t': done_t})
    for i, h in enumerate(HEAT[1:5]): cs[h]['nozzle_diameter'] = 0.4
    if screws: cs['screws_tilt_adjust'] = {}
    if shell: cs['gcode_shell_command wm_nozzle'] = {}
    if canids: cs['gcode_shell_command wm_canids'] = {}
    for i in range(4): cs['mcu t%d' % i] = {'canbus_uuid': (ids or ['ac8b57e80210', 'ac80ddd6ebe5', 'ac4068351d2c', 'ac6290884b96'])[i]}
    for mm in [m_ for m_ in re.finditer(r'^\[gcode_macro (\S+)\]\n((?:(?!\[).*\n)*)', text, re.M) if m_.group(1) in (name, '_WM_XYSTOP')]:   # only the macro that runs: other macros must stay absent from the printer object
        #\n((?:(?!\[).*\n)*)', text, re.M):   # the variable_ lines of every macro (the real macros keep their settings there)
        vs = {}
        for vl in re.finditer(r'^variable_(\w+):\s*([^#\n]*?)\s*(?:#.*)?$', mm.group(2), re.M):
            try: vs[vl.group(1)] = eval(vl.group(2), {}, {})
            except Exception: vs[vl.group(1)] = vl.group(2)
        printer.setdefault('gcode_macro ' + mm.group(1), {}).update(vs)
    printer['gcode_macro _WM_MATCH_STATE'] = {'actual': [0, 1, 2, 3] if actual is None else actual, 'full': full}
    for i in range(4):
        cs['filament_switch_sensor docked%d' % i] = {}
        printer['filament_switch_sensor docked%d' % i] = {'filament_detected': (docks or {}).get(i, True)}
    for i in range(4): printer['filament_switch_sensor filament%d' % i] = {'filament_detected': (fil or {}).get(i, True)}
    if ace: printer['ace'] = {}
    def raise_(m): raise Raise(m)
    info = []
    def respond_info(m): info.append(m); return ''
    try: out = env.from_string(macros[name]).render(printer=printer, params=params or {}, action_raise_error=raise_, action_respond_info=respond_info, **printer.get('gcode_macro ' + name, {}))
    except Raise as e: return ["INFO: " + x for x in info] + ["RAISE: " + str(e)]
    return [l.strip() for l in out.splitlines() if l.strip()]
bad = []
def want(label, lines, *must, none=()):
    j = "\n".join(lines)
    for m in must:
        if m not in j: bad.append("%s: missing %r in\n%s" % (label, m, j))
    for m in none:
        if m in j: bad.append("%s: unexpected %r in\n%s" % (label, m, j))
for n in macros: env.from_string(macros[n])
want("all macros present", sorted(macros), *["WM_BED_LEVELING", "WM_SCREWS_CAL", "WM_PROBE_CALIBRATE", "_WM_PROBE_DONE", "WM_OFFSETS_RAPID", "_WM_OFFSETS_ACCURATE", "WM_VIBRATION_COMP", "WM_NOZZLE_FULL_PID", "_WM_CAL_STOP", "_WM_CAL_HELP", "WM_BED_PID", "WM_FIRST_RUN_CAL", "_WM_FIRST_RUN_CAL", "_WM_FIRST_RUN_CAL_DONE", "_WM_NOZZLE_TYPE", "_WM_NOZZLE_CHANGE_END", "WM_EXTRUDER_SETUP", "WM_NOZZLE_CHANGE"])
want("level asks first", run("WM_BED_LEVELING"), "_WM_CAL_ASK STAGE=level", none=("G29",))
want("level runs", run("WM_BED_LEVELING", {"CONFIRM": "1"}, homed=""), "G28", "G29", "TURN_OFF_HEATERS", "SAVE_CONFIG")
want("level runs when already homed: no second homing", run("WM_BED_LEVELING", {"CONFIRM": "1"}, homed="xyz"), "G29", "TURN_OFF_HEATERS", none=("G28", "homing all axes"))
want("level SAVE=0", run("WM_BED_LEVELING", {"CONFIRM": "1", "SAVE": "0"}), "G29", none=("SAVE_CONFIG",))
want("screws asks first", run("WM_SCREWS_CAL"), "_WM_CAL_ASK STAGE=screws", none=("G28", "SCREWS_TILT_CALCULATE"))
want("screws run: home, heat, wipe, measure, heaters off, four steps", run("WM_SCREWS_CAL", {"CONFIRM": "1"}), "G28", "M190 S55", "M109 S140", "WIPE_NOZZLE", "SCREWS_TILT_CALCULATE", "TURN_OFF_HEATERS", "step 1 of 4", "step 4 of 4", none=("\nT0",))
want("screws picks up T0 when another tool is on the carriage", run("WM_SCREWS_CAL", {"CONFIRM": "1"}, sv={"current_extruder": 2}), "\nT0", "picking up T0")
want("screws refuses a printer without [screws_tilt_adjust]", run("WM_SCREWS_CAL", {"CONFIRM": "1"}, screws=False), 'no [screws_tilt_adjust] section')
want("precheck: print running", run("_WM_CAL_PRECHECK", printing="printing"), '_WM_FAIL MSG="A print is running')
want("precheck: heater on", run("_WM_CAL_PRECHECK", target={"extruder1": 200.0}), '_WM_FAIL MSG="extruder1 has a target')
want("precheck: bed on", run("_WM_CAL_PRECHECK", target={"heater_bed": 60.0}), '_WM_FAIL MSG="heater_bed has a target')
want("precheck: bed allowed", run("_WM_CAL_PRECHECK", {"ALLOW_BED": "1"}, target={"heater_bed": 60.0}), none=("RAISE",))
want("probe warms bed then PROBE_CALIBRATE", run("WM_PROBE_CALIBRATE", {"CONFIRM": "1"}), "M190 S60", "PROBE_CALIBRATE", none=("SAVE_CONFIG",))
want("probe refuses a bed above 100", run("WM_PROBE_CALIBRATE", {"CONFIRM": "1", "BED": "120"}), "RAISE")
want("rapid: G28, every tool, park, heaters off", run("WM_OFFSETS_RAPID", {"CONFIRM": "1", "CLEANED": "1"}, homed=""), "G28", "RAPID_MODE T=0", "RAPID_MODE T=3", "PARK_CURRENT_TOOL", "TURN_OFF_HEATERS", none=("NOZZLE_PREPARE",))
want("rapid: two tools only", run("WM_OFFSETS_RAPID", {"CONFIRM": "1", "CLEANED": "1"}, sv={"thr_number": 2}), "RAPID_MODE T=1", none=("RAPID_MODE T=2",))
want("rapid asks first", run("WM_OFFSETS_RAPID"), "_WM_CAL_ASK STAGE=offsets MODE=rapid", none=("G28", "RAPID_MODE"))
want("accurate asks first", run("_WM_OFFSETS_ACCURATE"), "_WM_CAL_ASK STAGE=offsets MODE=accurate", none=("G28", "NOZZLE_PREPARE"))
want("accurate start: G28, prepare T0, debris window", run("_WM_OFFSETS_ACCURATE", {"CONFIRM": "1"}, homed=""), "G28", "NOZZLE_PREPARE S=220 T=0", "purged debris has been manually removed", "_WM_OFFSETS_ACCURATE STEP=clean N=0 TEMP=220", none=("NOZZLE_CALIBRATE_TOOL_OFFSET", "RAPID_MODE"))
want("accurate TEMP", run("_WM_OFFSETS_ACCURATE", {"CONFIRM": "1", "TEMP": "240"}), "NOZZLE_PREPARE S=240 T=0", "TEMP=240")
want("accurate TEMP out of range", run("_WM_OFFSETS_ACCURATE", {"CONFIRM": "1", "TEMP": "400"}), '_WM_FAIL MSG="TEMP=400 is outside')
want("accurate clean T1: wipe, then prepare T2", run("_WM_OFFSETS_ACCURATE", {"STEP": "clean", "N": "1", "TEMP": "230"}), "NOZZLE_CALIBRATE_TOOL_OFFSET T=1", "NOZZLE_PREPARE S=230 T=2", "STEP=clean N=2 TEMP=230", none=("RAPID_MODE", "G28"))
want("accurate clean last tool: rapid for all, park", run("_WM_OFFSETS_ACCURATE", {"STEP": "clean", "N": "3"}), "NOZZLE_CALIBRATE_TOOL_OFFSET T=3", "RAPID_MODE T=0", "RAPID_MODE T=3", "PARK_CURRENT_TOOL", "TURN_OFF_HEATERS", none=("NOZZLE_PREPARE",))
want("accurate clean last tool (2 tools)", run("_WM_OFFSETS_ACCURATE", {"STEP": "clean", "N": "1"}, sv={"thr_number": 2}), "RAPID_MODE T=1", none=("RAPID_MODE T=2", "NOZZLE_PREPARE"))
want("accurate clean while printing", run("_WM_OFFSETS_ACCURATE", {"STEP": "clean", "N": "0"}, printing="printing"), '_WM_FAIL MSG="A print is running')
want("accurate bad step", run("_WM_OFFSETS_ACCURATE", {"STEP": "x"}), '_WM_FAIL MSG="STEP must be')
want("shaper", run("WM_VIBRATION_COMP", {"CONFIRM": "1"}, homed=""), "G28", "SHAPER_CALIBRATE", "SAVE_CONFIG")
want("shaper when already homed: no second homing", run("WM_VIBRATION_COMP", {"CONFIRM": "1"}, homed="xyz"), "SHAPER_CALIBRATE", none=("G28", "homing all axes"))
want("pid tool 1", run("WM_NOZZLE_FULL_PID", {"CONFIRM": "1", "T": "1"}), "_WM_PID_HEAD T=1 TARGET=220 FAN=100", "M106 S0", "TURN_OFF_HEATERS")
_ph = run("_WM_PID_HEAD", {"T": "1", "TARGET": "220", "FAN": "70"})
_order = ["T1", "_WM_CAL_CLEARANCE", "G0 Y240.0 F12000", "G0 X-13.0 F12000", "M106 S178", "PID_CALIBRATE HEATER=extruder1 TARGET=220", "SET_HEATER_TEMPERATURE HEATER=extruder1 TARGET=220", "TEMPERATURE_WAIT SENSOR=extruder1 MINIMUM=217", "WIPE_NOZZLE", "SET_HEATER_TEMPERATURE HEATER=extruder1 TARGET=0", "M106 S255", "TEMPERATURE_WAIT SENSOR=extruder1 MAXIMUM=140", "M106 S0", "WIPE_NOZZLE"]
_txt = "\n".join(_ph)
_pos = []; _at = 0
for x in _order:
    _at = _txt.find(x, _at); _pos.append(_at); _at = _at + 1 if _at >= 0 else _at
want("pid head: wipe position, tune, heat back, wipe, cool to 140, wipe again (in this order)", ["ok" if all(p >= 0 for p in _pos) and _pos == sorted(_pos) and _txt.count("WIPE_NOZZLE") == 2 else "wrong order %s" % _pos], "ok")
want("pid head: not in the middle of the bed any more", _ph, "PID_CALIBRATE HEATER=extruder1", none=("X150",))
want("pid skips watermark", run("WM_NOZZLE_FULL_PID", {"CONFIRM": "1"}, control="watermark"), "Hotend PID skipped: T1, T2, T3, T4 do not use control: pid.", none=("_WM_PID_HEAD",))
want("pid refuses odd target", run("WM_NOZZLE_FULL_PID", {"TARGET": "400"}), '_WM_FAIL MSG="TARGET=400 is outside 150 to 280 C')
want("pid refuses unknown heater", run("WM_NOZZLE_FULL_PID", {"T": "7"}), '_WM_FAIL MSG="T must be all or a tool head from 0 to 3.')
want("bed pid asks first", run("WM_BED_PID"), "_WM_CAL_ASK STAGE=bedpid TARGET=60", none=("PID_CALIBRATE",))
want("bed pid runs", run("WM_BED_PID", {"CONFIRM": "1"}), "PID_CALIBRATE HEATER=heater_bed TARGET=60", "TURN_OFF_HEATERS", "SAVE_CONFIG")
want("bed pid SAVE=0", run("WM_BED_PID", {"CONFIRM": "1", "SAVE": "0"}), "PID_CALIBRATE", none=("SAVE_CONFIG",))
want("bed pid refuses watermark", run("WM_BED_PID", {"CONFIRM": "1"}, control="watermark"), "RAISE: heater_bed uses control: watermark")
# tool head LEDs (rpi-cfg/rpi_tool_leds.cfg): a delayed_gcode, not a macro
led = re.search(r'^\[delayed_gcode WM_TOOL_LEDS\]\n(?:.*\n)*?gcode:\n((?:(?:    .*|)\n)+)', open(os.path.join(ROOT, "rpi-cfg", "rpi_base.cfg")).read(), re.M).group(1)
def leds(detected, undefined=(), thr=4, cur=99, seen=(-1, -1, -1, -1)):
    pr = {"filament_switch_sensor filament%d" % i: {"filament_detected": detected[i]} for i in range(4) if i not in undefined}
    pr["save_variables"] = {"variables": {"thr_number": thr, "current_extruder": cur}}
    pr["gcode_macro _WM_LED_STATE"] = {"seen": list(seen)}
    return [l.strip() for l in env.from_string(led).render(printer=pr).splitlines() if l.strip()]
want("leds: first pass: filament = blue, none = red", leds([True, False, True, False]), "_RGB_LOAD T=0", "_RGB_UNLOAD T=1", "_RGB_LOAD T=2", "_RGB_UNLOAD T=3", "SET_GCODE_VARIABLE MACRO=_WM_LED_STATE VARIABLE=seen VALUE=[1,0,1,0]", "UPDATE_DELAYED_GCODE ID=WM_TOOL_LEDS DURATION=2")
want("leds: tool on the carriage with filament = green", leds([True, True, False, False], cur=1), "_RGB_LOAD T=0", "_RGB_CURRENT T=1", "VALUE=[1,2,0,0]")
want("leds: nothing changed -> no LED call", leds([True, False, True, False], seen=(1, 0, 1, 0)), "SET_GCODE_VARIABLE", none=("_RGB_",))
want("leds: only the tool that changed is called", leds([True, True, True, False], seen=(1, 0, 1, 0)), "_RGB_LOAD T=1", none=("T=0", "T=2", "T=3"))
want("leds: only the tool heads this printer has", leds([True] * 4, thr=2), "_RGB_LOAD T=1", none=("T=2", "T=3"))
want("leds: a missing sensor counts as no filament", leds([True] * 4, undefined=(2,)), "_RGB_UNLOAD T=2", "_RGB_LOAD T=3")
# print end watcher (rpi-cfg/rpi_print_end.cfg)
pe = re.search(r'^\[delayed_gcode WM_PRINT_END_WATCH\]\n(?:.*\n)*?gcode:\n((?:(?:    .*|)\n)+)', open(os.path.join(ROOT, "rpi-cfg", "rpi_base.cfg")).read(), re.M).group(1)
def pend(state, ready):
    pr = {"print_stats": {"state": state}, "gcode_macro START_PRINT": {"print_body_ready": ready}}
    return ["<<run PRINT_END>>" if l.strip() == "PRINT_END" else l.strip() for l in env.from_string(pe).render(printer=pr).splitlines() if l.strip()]
want("print end: complete and PRINT_END not run yet -> runs it", pend("complete", True), "<<run PRINT_END>>", "UPDATE_DELAYED_GCODE ID=WM_PRINT_END_WATCH DURATION=2")
want("print end: already run (G-code called it) -> not twice", pend("complete", False), "UPDATE_DELAYED_GCODE ID=WM_PRINT_END_WATCH", none=("<<run",))
want("print end: printing / cancelled / idle -> nothing", pend("printing", True) + pend("cancelled", True) + pend("standby", True), "UPDATE_DELAYED_GCODE", none=("<<run",))
want("no chamber macro any more", sorted(macros), none=("WM_CHAMBER_PID",))
want("bed pid refuses odd target", run("WM_BED_PID", {"TARGET": "200"}), "RAISE")
want("full calibration: window, nothing runs", run("WM_FIRST_RUN_CAL"), "prompt_begin First Run Calibration", "_WM_FIRST_RUN_CAL", "Nozzle PID: tunes", none=("G29", "SAVE_CONFIG\n", "PID_CALIBRATE"))
want("full calibration: watermark says skipped", run("WM_FIRST_RUN_CAL", control="watermark"), "Nozzle PID: skipped")
want("full calibration: checks first", run("WM_FIRST_RUN_CAL")[:1], "_WM_CAL_PRECHECK")
want("full calibration (F-143): seven stages, setter position first, no extruder setup", run("_WM_FIRST_RUN_CAL", {"CLEANED": "1"}), "_WM_CAL_PRECHECK", "First run calibration - 1 of 8: tool setter position (saved)", "_WM_SETTER_AUTO", none=("_WM_MATCH", "VARIABLE=full", "extruder setup", "FIRMWARE_RESTART", "SAVE_CONFIG\n"))
want("full calibration: the precheck comes first", run("_WM_FIRST_RUN_CAL")[:2], "_WM_CAL_PRECHECK")
want("full calibration stages in your order: setter, offsets, shaper (SAVE=0), bed PID (SAVE=0), bed leveling after the bed PID, nozzle PID, one window at the end", run("_WM_FIRST_RUN_CAL", {"CLEANED": "1"}), "_WM_SETTER_AUTO\nRESPOND MSG=\"First run calibration - 2 of 8: tool offsets (rapid, saved)\"\nWM_OFFSETS_RAPID CONFIRM=1 XYLIMIT=3", "WM_VIBRATION_COMP CONFIRM=1 SAVE=0\nRESPOND MSG=\"First run calibration - 6 of 8: bed PID (saved at the end)\"\nWM_BED_PID CONFIRM=1 SAVE=0\nRESPOND MSG=\"First run calibration - 7 of 8: bed leveling (saved at the end)\"\nWM_BED_LEVELING CONFIRM=1 SAVE=0\nRESPOND MSG=\"First run calibration - 8 of 8: nozzle PID (saved at the end)\"\nWM_NOZZLE_FULL_PID TARGET=220 T=all CONFIRM=1 SAVE=0", "_WM_FIRST_RUN_CAL_DONE", "3 of 8: hot Z offsets skipped", none=("SAVE_CONFIG\n", "_WM_MATCH_RUN"))
want("full calibration skips PID on watermark", run("_WM_FIRST_RUN_CAL", {"CLEANED": "1"}, control="watermark"), "skipped")
want("full calibration window: seven stages, setter position first, says where the CAN ids are checked", run("WM_FIRST_RUN_CAL"), "1) Tool setter position", "3) Hot Z offsets", "7) Bed leveling", "8) Nozzle PID", "hang the extruders on the rear support", "WM_EXTRUDER_SETUP", "saved as each one finishes", none=("1) Extruder setup", "9)", "apply the new CAN ids"))
want("matching: no first-run mode any more (no flag, no jump into the calibration)", run("_WM_MATCH_FINISH"), "nothing was changed", "prompt_show", none=("_WM_FIRST_RUN_CAL", "VARIABLE=full"))
want("matching: other ids offer Apply and restart, nothing about a calibration", run("_WM_MATCH_FINISH", actual=[1, 0, 2, 3]), "_WM_MATCH_APPLY", none=("_WM_FIRST_RUN_CAL", "start WM_FIRST_RUN_CAL again", "VARIABLE=full"))
want("matching: duplicate ids stop", run("_WM_MATCH_FINISH", actual=[0, 0, 2, 3]), "same CAN id", none=("_WM_FIRST_RUN_CAL", "_WM_MATCH_APPLY", "did not go on"))
_pend = {"input_shaper": {"shaper_type_x": "mzv", "shaper_freq_x": 59.2, "shaper_type_y": "ei", "shaper_freq_y": 41.8},
         "heater_bed": {"pid_Kp": 63.167, "pid_Ki": 1.077, "pid_Kd": 926.193}, "bed_mesh default": {"version": 1},
         "extruder": {"pid_Kp": 17.568, "pid_Ki": 3.165, "pid_Kd": 24.375}, "extruder3": {"pid_Kp": 19.648, "pid_Ki": 7.705, "pid_Kd": 12.525}}
want("end window shows every result: saved ones, then the ones that wait for Save and Restart, bed mesh without values", run("_WM_FIRST_RUN_CAL_DONE", pend=_pend, sv={"probe_position": [297.63, 286.31, 9.17, 0, 0], "t1_offset": [0.28, 0.34, -0.026]}),
     "1) Tool setter position: X 297.63 Y 286.31 Z 9.17", "2) Tool offsets: T0 X 0.000 Y 0.000, T1 X 0.280 Y 0.340", "3) Hot Z offsets: T0 Z 0.000, T1 Z -0.026", "5) Input shaper: X mzv at 59.2 Hz, Y ei at 41.8 Hz",
     "6) Bed PID: Kp", "to 63.17", "7) Bed mesh\"", "8) Nozzle PID:", "T0 Kp 0.00 to 17.57", "T3 Kp 0.00 to 19.65", "Save and Restart|_WM_SAVE", none=("T1 Kp", "T2 Kp"))
want("end window without new values says so", run("_WM_FIRST_RUN_CAL_DONE"), "5) Input shaper: no new values", "7) Bed mesh: no new mesh", "8) Nozzle PID: not run")
want("start window is ignored when it arrives right after the end window", run("WM_FIRST_RUN_CAL", done_t=995.0), "was ignored", none=("prompt_begin First Run Calibration",))
want("start window opens normally a long time after the end window", run("WM_FIRST_RUN_CAL", done_t=500.0), "prompt_begin First Run Calibration", none=("was ignored",))
want("full calibration end window saves only on click", run("_WM_FIRST_RUN_CAL_DONE"), "Save and Restart|_WM_SAVE", "WM_PROBE_CALIBRATE")
# ---- 2.8.0: hot Z stage in the first run calibration, Z offset tools, unload menu, safety check, chamber light
def more(fname, folder="rpi-cfg"):
    t = open(os.path.join(ROOT, folder, fname)).read()
    return {m.group(1): m.group(2) for m in re.finditer(r'^\[(?:gcode_macro|delayed_gcode) (\S+)\]\n(?:.*\n)*?gcode:\n((?:(?:    .*|)\n)+)', t, re.M)}
ZO = more("rpi_calibration.cfg"); UN = more("rpi_base.cfg"); SA = more("rpi_base.cfg"); LI = more("rpi_light.cfg", "config")
for group in (ZO, UN, SA, LI):
    for n in group: env.from_string(group[n])
want("rpi_calibration.cfg has the Z offset macros", sorted(ZO), "WM_FULL_OFFSET_CAL", "WM_OFFSETS_Z_HOT", "WM_NOZZLE_GROWTH_CAL", "WM_Z_TRIM_MENU", "_WM_WAIT_TEMP", "_WM_WAIT_TEMP_STEP", "_WM_Z_TOUCH", none=("WM_Z_TRIM_SET",))
want("rpi_base.cfg has the unload macros", sorted(UN), "WM_UNLOAD_MENU", "_WM_UNLOAD_GO", "_WM_UNLOAD_STOP", none=("\nWM_UNLOAD_GO",))
def zrun(name, params=None, temp=25.0, warmup=1, extra=None, homed=""):
    w = {"z": [0.0] * 5, "g": [0.0] * 3, "temp": 140, "bed": 60, "samples": 5, "soak_s": 20, "max_drift": 0.02, "drip_s": 20, "wipes": 2, "retract_mm": 20, "warmup": warmup, "hot_ok": -1, "growth_ok": -1, "chain": 0}
    printer = {"save_variables": {"variables": {"thr_number": 4, "current_extruder": 0, "wipe_position": [-13.0, 240.0]}}, "print_stats": {"state": "standby"},
               "heaters": {"available_heaters": HEAT}, "gcode_macro _WM_ZHOT": w, "toolhead": {"homed_axes": homed}, "filament_switch_sensor filament0": {"filament_detected": False}}
    for h in HEAT: printer[h] = {"target": 0.0, "temperature": temp}
    printer.update(extra or {})
    out = env.from_string(ZO[name]).render(printer=printer, params=params or {})
    return [l.strip() for l in out.splitlines() if l.strip() and not l.strip().startswith("#")]
want("first run calibration: hot Z stage right after the rapid offsets when rpi_zoffset.cfg is installed",
     [l.strip() for l in env.from_string(macros["_WM_FIRST_RUN_CAL"]).render(printer={"gcode_macro WM_OFFSETS_Z_HOT": {}, "configfile": {"settings": {"heater_bed": {"control": "pid"}}}}, params={"CLEANED": "1"}).splitlines() if l.strip() and not l.strip().startswith("#")],
     "WM_OFFSETS_RAPID CONFIRM=1 XYLIMIT=3\nRESPOND MSG=\"First run calibration - 3 of 8: hot Z offsets (saved)\"\nWM_OFFSETS_Z_HOT CONFIRM=1\nRESPOND MSG=\"First run calibration - 4 of 8")
t = zrun("_WM_Z_TOUCH", {"T": "0", "TEMP": "140", "SLOT": "0"})
want("Z touch: one touch that is not counted, lift, then the counted touches", t, "PROBE SAMPLES=1\nM400\nG90\nG1 Z5 F600\nM400\nPROBE SAMPLES=5", "_WM_WAIT_TEMP SENSOR=extruder MINIMUM=138 MAXIMUM=142 NAME=T0 TARGET=140")
want("Z touch: warmup 0 switches the extra touch off", zrun("_WM_Z_TOUCH", {"T": "0", "TEMP": "140", "SLOT": "0"}, warmup=0), "PROBE SAMPLES=5", none=("PROBE SAMPLES=1",))
wt = zrun("_WM_WAIT_TEMP", {"SENSOR": "extruder", "MINIMUM": "138", "MAXIMUM": "142", "NAME": "T0", "TARGET": "140"})
want("quiet wait: 360 steps of 5 s, then the real wait", [str(len(wt)), wt[0], wt[-1]], "361", "_WM_WAIT_TEMP_STEP SENSOR=extruder", "N=0", "TEMPERATURE_WAIT SENSOR=extruder MINIMUM=138.0 MAXIMUM=142.0")
P = {"SENSOR": "extruder", "MINIMUM": "138", "MAXIMUM": "142", "NAME": "T0", "TARGET": "140"}
want("quiet wait step: not there yet, a console line every 30 s", zrun("_WM_WAIT_TEMP_STEP", dict(P, N="6"), temp=201.4), 'RESPOND MSG="T0 at 201 C, waiting for 140 C"', "G4 P5000")
want("quiet wait step: between the lines it only waits", zrun("_WM_WAIT_TEMP_STEP", dict(P, N="5"), temp=201.4), "G4 P5000", none=("RESPOND",))
want("quiet wait step: at temperature it does nothing", zrun("_WM_WAIT_TEMP_STEP", dict(P, N="6"), temp=140.0), none=("G4", "RESPOND"))
want("hot Z run when already homed: no second homing", zrun("WM_OFFSETS_Z_HOT", {"CONFIRM": "1"}, homed="xyz"), "M140 S60", none=("G28",))
want("growth run when not homed: G28", zrun("WM_NOZZLE_GROWTH_CAL", {"CONFIRM": "1", "T": "0"}, homed=""), "G28")
want("growth run when already homed: no second homing", zrun("WM_NOZZLE_GROWTH_CAL", {"CONFIRM": "1", "T": "0"}, homed="xyz"), "Nozzle heat growth", none=("G28",))
want("hot Z run: bed wait with console lines, T0 first and last", zrun("WM_OFFSETS_Z_HOT", {"CONFIRM": "1"}), "M140 S60\n_WM_WAIT_TEMP SENSOR=heater_bed MINIMUM=59 MAXIMUM=61 NAME=Bed TARGET=60\nM190 S60", "_WM_Z_TOUCH T=0 TEMP=140 SLOT=0 LIST=z", "_WM_Z_TOUCH T=0 TEMP=140 SLOT=4 LIST=z")
for group, gname in ((ZO, "rpi_zoffset.cfg"), (UN, "rpi_unload.cfg"), (SA, "rpi_safety.cfg")):
    for n, body in group.items():
        for line in body.splitlines():
            if "RESPOND" in line and 'MSG="' in line and "prompt_" not in line:
                msg = line.split('MSG="', 1)[1]
                msg = re.sub(r'\{[^{}]*\}', '', msg)   # what is inside { } is an expression, computed before the line is sent
                if any(c in msg for c in ";#*"): bad.append("%s %s: a ; # or * inside a RESPOND message: %s" % (gname, n, line.strip()))
want("window buttons close the screen window first", run("_WM_SAVE"), "action:prompt_end", "SAVE_CONFIG")
want("cancel closes the window and says so", run("_WM_PROMPT_CLOSE", params={"MSG": "Cancelled"}), "action:prompt_end", "M118 Cancelled")
want("the start path closes the window first", run("_WM_CAL_STOP"), "action:prompt_end", "TURN_OFF_HEATERS")
want("both files' macros present", sorted(macros), "_WM_NOZZLE_TYPE", "_WM_NOZZLE_MATERIAL", "_WM_NOZZLE_DIAMETER", "_WM_NOZZLE_SURE", "_WM_NOZZLE_APPLY", "WM_NOZZLE_CHANGE", "_WM_NCHANGE_CHECK", "_WM_NCHANGE_RUN", "_WM_NCHANGE_AFTER", "_WM_NCHANGE_FAILED", "_WM_NOZZLE_CHANGE_END")
want("nozzle type: refuses while printing", run("_WM_NOZZLE_TYPE", printing="printing"), "RAISE")
want("nozzle type: one button per tool, shows the current values", run("_WM_NOZZLE_TYPE"), "prompt_begin Nozzle Type", "Nozzle 1: hardened steel, 0.4 mm", "_WM_NOZZLE_MATERIAL T=0", "_WM_NOZZLE_MATERIAL T=3")
want("nozzle type: only as many buttons as tools", run("_WM_NOZZLE_TYPE", sv={"thr_number": 2}), "_WM_NOZZLE_MATERIAL T=1", none=("_WM_NOZZLE_MATERIAL T=2",))
want("nozzle type: shows a saved stainless nozzle", run("_WM_NOZZLE_TYPE", sv={"nozzle_type2": 1}), "Nozzle 3: stainless steel")
want("nozzle type: material step carries the tool", run("_WM_NOZZLE_MATERIAL", {"T": "2"}), "Nozzle 3: material", "_WM_NOZZLE_DIAMETER T=2 TYPE=0", "_WM_NOZZLE_DIAMETER T=2 TYPE=1")
want("nozzle type: diameter step", run("_WM_NOZZLE_DIAMETER", {"T": "1", "TYPE": "1"}), "_WM_NOZZLE_SURE T=1 TYPE=1 D=0.2", "D=0.4", "D=0.6", "D=0.8")
want("nozzle type: confirm writes nothing", run("_WM_NOZZLE_SURE", {"T": "0", "TYPE": "0", "D": "0.6"}), "_WM_NOZZLE_APPLY T=0 TYPE=0 D=0.6", "hardened steel, 0.6 mm", none=("RUN_SHELL_COMMAND", "SAVE_VARIABLE"))
want("nozzle type: apply saves and edits printer.cfg", run("_WM_NOZZLE_APPLY", {"T": "3", "TYPE": "1", "D": "0.8"}), "SAVE_VARIABLE VARIABLE=nozzle_type3 VALUE=1", 'RUN_SHELL_COMMAND CMD=wm_nozzle PARAMS="set 3 0.8 1"', "RESTART")
want("nozzle type: apply refuses without the shell command", run("_WM_NOZZLE_APPLY", {"T": "0"}, shell=False), "RAISE: The wm_nozzle shell command is not loaded")
want("nozzle type: apply refuses while printing", run("_WM_NOZZLE_APPLY", {"T": "0"}, printing="paused"), "RAISE")
want("nozzle change: window explains and nothing moves", run("WM_NOZZLE_CHANGE"), "hang the extruders on the rear support", "_WM_NCHANGE_RUN", none=("_UNLOCK_TOOL", "SAVE_VARIABLE", "G28"))
want("nozzle change: refuses while printing", run("_WM_NCHANGE_CHECK", printing="printing"), "RAISE")
want("nozzle change: the refusal also opens a Fluidd window", run("_WM_NCHANGE_CHECK", printing="printing"), "INFO: action:prompt_begin Cannot start", "INFO: action:prompt_text A print is running", "INFO: action:prompt_footer_button Close", "INFO: action:prompt_show", "RAISE")
want("matching: a tool head out of its dock opens a Fluidd window naming it", run("_WM_MATCH_CHECK", docks={0: False}), "INFO: action:prompt_text Tool head 1 is not seen in its dock", "INFO: action:prompt_show", "RAISE")
want("nozzle change: refuses with a heater on", run("_WM_NCHANGE_CHECK", target={"heater_bed": 60.0}), "RAISE: heater_bed")
want("nozzle change: refuses with a hot nozzle", run("_WM_NCHANGE_CHECK", temps={"extruder2": 120.0}), "RAISE: extruder2 is still at 120")
want("nozzle change: cold printer passes", run("_WM_NCHANGE_CHECK"), none=("RAISE",))
want("nozzle change: park the tool on the carriage first (the dock sensor check stays on while unlocking)", run("_WM_NCHANGE_RUN", sv={"current_extruder": 2}), "_UNLOCK_TOOL T=2", "_WM_NCHANGE_AFTER", none=("is_nozzle_setting VALUE=1",))
want("nozzle change: the switch goes on after the unlock worked", run("_WM_NCHANGE_AFTER"), "SAVE_VARIABLE VARIABLE=is_nozzle_setting VALUE=1")
want("nozzle change: no tool on the carriage, nothing to unlock", run("_WM_NCHANGE_RUN", sv={"current_extruder": 99}), "_WM_NCHANGE_AFTER", none=("_UNLOCK_TOOL",))
want("nozzle change: a stale fail_flag stops it and puts the switch back", run("_WM_NCHANGE_RUN", sv={"fail_flag": -3}), "_WM_NCHANGE_FAILED", none=("_UNLOCK_TOOL",))
want("nozzle change: unlock success asks for Done", run("_WM_NCHANGE_AFTER"), "tools released", "_WM_NOZZLE_CHANGE_END")
want("nozzle change: unlock failure", run("_WM_NCHANGE_AFTER", sv={"fail_flag": -3, "fail_tool": 1}), "_WM_NCHANGE_FAILED", none=("_WM_NOZZLE_CHANGE_END|primary",))
want("nozzle change: failed puts the switch back", run("_WM_NCHANGE_FAILED", {"REASON": "x"}), "is_nozzle_setting VALUE=0")
want("nozzle change end: switch off, docks fine", run("_WM_NOZZLE_CHANGE_END"), "is_nozzle_setting VALUE=0", "Every tool head is seen in its dock")
want("nozzle change end: names an empty dock", run("_WM_NOZZLE_CHANGE_END", docks={1: False, 3: False}), "is_nozzle_setting VALUE=0", "tool head 2, 4 shows an empty dock")
want("match: all macros present", sorted(macros), "WM_EXTRUDER_SETUP", "_WM_MATCH_STATE", "_WM_MATCH_CHECK", "_WM_MATCH_RUN", "_WM_MATCH_STEP", "_WM_MATCH_AFTER", "_WM_MATCH_FINISH", "_WM_MATCH_APPLY", "_WM_MATCH_STOP")
want("match: window shows the ids, nothing moves", run("WM_EXTRUDER_SETUP"), "prompt_begin Extruder Setup", "hang the extruders on the rear support", "T0 ac8b57e80210", "T3 ac6290884b96", "Set Up|_WM_MATCH_RUN", none=("T0\n", "SAVE_VARIABLE", "G28", "PARK_CURRENT_TOOL"))
want("match: check runs the Extruder Setup safety check first", run("WM_EXTRUDER_SETUP")[:1], "_WM_MATCH_CHECK")
want("match: check refuses without the wm_canids shell command", run("_WM_MATCH_CHECK", canids=False), "RAISE: The wm_canids shell command is not loaded")
want("match: check refuses while a nozzle change is on", run("_WM_MATCH_CHECK", sv={"is_nozzle_setting": 1}), "RAISE: The nozzle change is still on")
want("match: check refuses with fail_flag set", run("_WM_MATCH_CHECK", sv={"fail_flag": -3}), "RAISE: WonderMaker's tool change error flag")
want("match: check refuses when a head is not in its dock", run("_WM_MATCH_CHECK", docks={2: False}), "RAISE: Tool head 3 is not seen in its dock")
want("match: check refuses a missing CAN id", run("_WM_MATCH_CHECK", ids=["ac8b57e80210", "", "ac4068351d2c", "ac6290884b96"]), "RAISE: [mcu T1] has no canbus_uuid")
want("match: check passes on a good printer", run("_WM_MATCH_CHECK"), none=("RAISE",))
want("match: run switches on, homes if needed, parks, starts at T0", run("_WM_MATCH_RUN", sv={"current_extruder": 1}), "SET_GCODE_VARIABLE MACRO=_WM_MATCH_STATE VARIABLE=actual VALUE=\"[]\"", "is_nozzle_setting VALUE=1", "PARK_CURRENT_TOOL", "_WM_MATCH_STEP N=0")
want("match: run does not park when no tool is on the carriage", run("_WM_MATCH_RUN", sv={"current_extruder": 99}), "_WM_MATCH_STEP N=0", none=("PARK_CURRENT_TOOL",))
want("match: step picks the tool and checks", run("_WM_MATCH_STEP", {"N": "2"}), "T2", "M400", "_WM_MATCH_AFTER N=2")
want("match: step stops on a stale fail_flag", run("_WM_MATCH_STEP", {"N": "1"}, sv={"fail_flag": -1}), "_WM_MATCH_STOP", none=("\nT1\n",))
want("match: after notes the empty dock and goes on", run("_WM_MATCH_AFTER", {"N": "0"}, docks={0: False}, actual=[]), 'VALUE="[0]"', "VARIABLE=next VALUE=1", "UPDATE_DELAYED_GCODE ID=_WM_MATCH_NEXT DURATION=0.5", none=("_WM_MATCH_STEP N=",))
want("match: after records a different dock", run("_WM_MATCH_AFTER", {"N": "1"}, docks={3: False}, actual=[0]), 'VALUE="[0, 3]"', "empty dock is tool head 4", "VARIABLE=next VALUE=2", "UPDATE_DELAYED_GCODE ID=_WM_MATCH_NEXT")
want("match: after the last tool finishes", run("_WM_MATCH_AFTER", {"N": "3"}, docks={3: False}, actual=[0, 1, 2]), 'VALUE="[0, 1, 2, 3]"', "_WM_MATCH_FINISH", none=("_WM_MATCH_STEP",))
want("match: after stops when no dock is empty", run("_WM_MATCH_AFTER", {"N": "1"}, actual=[0]), "_WM_MATCH_STOP", "no dock sensor shows an empty dock", none=("_WM_MATCH_STEP",))
want("match: after stops when the pick failed", run("_WM_MATCH_AFTER", {"N": "1"}, docks={1: False}, actual=[0], sv={"fail_flag": -1, "fail_tool": 1}), "_WM_MATCH_STOP", "T1 could not be picked up", none=("_WM_MATCH_STEP",))
want("match: finish with identity changes nothing", run("_WM_MATCH_FINISH"), "PARK_CURRENT_TOOL", "is_nozzle_setting VALUE=0", "nothing was changed", none=("_WM_MATCH_APPLY", "RUN_SHELL_COMMAND", "FIRMWARE_RESTART"))
want("match: finish with a swap offers the new ids, writes nothing", run("_WM_MATCH_FINISH", actual=[0, 2, 1, 3]), "T1: ac80ddd6ebe5 -> ac4068351d2c (from dock 3)", "T2: ac4068351d2c -> ac80ddd6ebe5 (from dock 2)", "_WM_MATCH_APPLY ID0=ac8b57e80210 ID1=ac4068351d2c ID2=ac80ddd6ebe5 ID3=ac6290884b96", none=("RUN_SHELL_COMMAND", "FIRMWARE_RESTART", "T0: ", "T3: "))
want("match: finish with a duplicate writes nothing", run("_WM_MATCH_FINISH", actual=[0, 2, 2, 3]), "T1 and T2 would get the same CAN id", "nothing was written", "T1: dock 3", none=("_WM_MATCH_APPLY", "RUN_SHELL_COMMAND"))
want("match: apply writes the four ids, then restarts the firmware", run("_WM_MATCH_APPLY", {"ID0": "a", "ID1": "b", "ID2": "c", "ID3": "d"}), 'RUN_SHELL_COMMAND CMD=wm_canids PARAMS="apply a b c d"', "FIRMWARE_RESTART")
want("match: apply refuses without the shell command", run("_WM_MATCH_APPLY", {"ID0": "a"}, canids=False), "RAISE: The wm_canids shell command is not loaded")
want("match: apply refuses while printing", run("_WM_MATCH_APPLY", {"ID0": "a"}, printing="printing"), "RAISE")
want("match: stop switches off and writes nothing", run("_WM_MATCH_STOP", {"REASON": "x"}), "is_nozzle_setting VALUE=0", "Nothing was written", none=("RUN_SHELL_COMMAND", "SAVE_CONFIG"))
want("nozzle change end: offers only Nozzle Type, no Extruder Setup", run("_WM_NOZZLE_CHANGE_END"), "Nozzle Type|_WM_NOZZLE_TYPE|primary", none=("WM_EXTRUDER_SETUP",))
want("nozzle change windows do not mention the Extruder Setup", run("WM_NOZZLE_CHANGE") + run("_WM_NCHANGE_AFTER"), "record the new nozzle", none=("EXTRUDER_SETUP", "Extruder Setup"))
want("_WM_CAL_HELP lists the full calibration, extruder setup and the hidden helpers", run("_WM_CAL_HELP"), "WM_EXTRUDER_SETUP", "WM_EXTRUDER_SETUP", "_WM_CAL_STOP", "_WM_NOZZLE_CHANGE_END", "_WM_NOZZLE_TYPE")
want("calibration refuses while Extruder Setup or a nozzle change is on", run("_WM_CAL_PRECHECK", sv={"is_nozzle_setting": 1}), '_WM_FAIL MSG="Extruder Setup or a nozzle change is still on')

def closes_first(label, lines):   # the window must close BEFORE the error line runs (Klipper reads the whole macro first, so the error cannot be raised inside the macro text)
    fi = next((i for i, l in enumerate(lines) if "_WM_FAIL" in l), None); ci = next((i for i, l in enumerate(lines) if "action:prompt_end" in l), None)
    if fi is None or ci is None or ci > fi: bad.append("%s: prompt_end must come before _WM_FAIL in\n%s" % (label, "\n".join(lines)))
closes_first("precheck closes the window before it fails", run("_WM_CAL_PRECHECK", printing="printing"))
closes_first("accurate: bad temp closes the window before it fails", run("_WM_OFFSETS_ACCURATE", {"CONFIRM": "1", "TEMP": "400"}))
closes_first("accurate: clean while printing closes the window before it fails", run("_WM_OFFSETS_ACCURATE", {"STEP": "clean", "N": "0"}, printing="printing"))
want("_WM_FAIL raises the message", run("_WM_FAIL", {"MSG": "No filament in T1."}), "RAISE: No filament in T1.")
want("accurate popup tells to load filament in every tool", run("_WM_CAL_ASK", {"STAGE": "offsets", "MODE": "accurate"}), "Filament must be loaded in every tool head")
want("rapid popup has no filament sentence", run("_WM_CAL_ASK", {"STAGE": "offsets", "MODE": "rapid"}), "Calibrates every tool head", none=("Filament must be loaded",))
def fails_before(label, lines, *later):   # the render prints every line, but Klipper stops at _WM_FAIL, so the error line must come before anything that moves or heats
    fi = next((i for i, l in enumerate(lines) if "_WM_FAIL" in l), None)
    if fi is None: bad.append("%s: no _WM_FAIL in\n%s" % (label, "\n".join(lines))); return
    for w in later:
        li = next((i for i, l in enumerate(lines) if l.startswith(w)), None)
        if li is not None and li < fi: bad.append("%s: %r runs before _WM_FAIL in\n%s" % (label, w, "\n".join(lines)))
want("accurate: an empty tool is named in the error", run("_WM_OFFSETS_ACCURATE", {"CONFIRM": "1"}, fil={2: False}), '_WM_FAIL MSG="No filament in T3')
fails_before("accurate: an empty tool stops it before G28", run("_WM_OFFSETS_ACCURATE", {"CONFIRM": "1"}, fil={2: False}), "G28", "_WM_NOZZLE_PREPARE", "RESPOND MSG=\"Accurate tool offset calibration started")
closes_first("accurate: missing filament closes the window before it fails", run("_WM_OFFSETS_ACCURATE", {"CONFIRM": "1"}, fil={1: False}))
want("accurate: only the tools in use are checked", run("_WM_OFFSETS_ACCURATE", {"CONFIRM": "1"}, sv={"thr_number": 2}, fil={3: False}, homed=""), "G28", none=("_WM_FAIL",))
want("prepare: no filament", run("_WM_NOZZLE_PREPARE", {"S": "220", "T": "1"}, fil={1: False}), '_WM_FAIL MSG="No filament in T1')
fails_before("prepare: no filament stops before it moves or heats", run("_WM_NOZZLE_PREPARE", {"S": "220", "T": "1"}, fil={1: False}), "T1", "G28", "M109", "G1")

def assist_check(label, lines, ace, extrude=("G1 E120", "G1 E88", "G1 E{", "G1 E100")):   # feed assist only with an ACE, switched on before the purge and off after it
    on = [i for i, l in enumerate(lines) if "ACE_ENABLE_FEED_ASSIST" in l]; off = [i for i, l in enumerate(lines) if "ACE_DISABLE_FEED_ASSIST" in l]
    ex = [i for i, l in enumerate(lines) if l.startswith("G1 E") and not l.startswith("G1 E-")]
    if not ex: bad.append("%s: no purge in\n%s" % (label, "\n".join(lines))); return
    if not ace:
        if on or off or any("ACE_" in l for l in lines): bad.append("%s: ACE commands without an ACE in\n%s" % (label, "\n".join(lines)))
    elif not (len(on) == 1 and len(off) == 1 and on[0] < ex[0] and ex[-1] < off[0]): bad.append("%s: feed assist must go on before and off after the purge in\n%s" % (label, "\n".join(lines)))
for a in (False, True):
    assist_check("_WM_NOZZLE_PREPARE ace=%s" % a, run("_WM_NOZZLE_PREPARE", {"S": "220", "T": "1"}, ace=a), a)
    want("_WM_NOZZLE_PREPARE ace=%s steps" % a, run("_WM_NOZZLE_PREPARE", {"S": "220", "T": "0"}, ace=a), "G28 Z", "PROBE", "M109 S220 T0", "G1 E120 F800", "G1 E-3 F800", "M109 S100 T0", "G1 Z80")
    if a: want("_WM_NOZZLE_PREPARE assist is for the tool", run("_WM_NOZZLE_PREPARE", {"S": "220", "T": "2"}, ace=True), "ACE_ENABLE_FEED_ASSIST T=2", "ACE_DISABLE_FEED_ASSIST T=2")

# the other macros that push filament outside a print (factory offset_calibrate.cfg for both models, ZR Tools): feed assist only with an ACE
def macros_of(path):
    t = open(os.path.join(ROOT, path)).read()
    return {m.group(1): m.group(2) for m in re.finditer(r'^\[gcode_macro (\S+)\]\n(?:.*\n)*?gcode:\n((?:(?:    .*|)\n)+)', t, re.M)}
def run_other(ms, name, params, ace, extra_vars=None, printing=False):
    printer = {'save_variables': {'variables': {'current_extruder': 0, 'zr_t1_temp': 220, 'box_modify_t0': 0, 'box_modify_t1': 1, 'box_modify_t2': 2, 'box_modify_t3': 3}}, 'print_stats': {'state': 'printing' if printing else 'standby'},
               'toolhead': {'homed_axes': 'xyz', 'extruder': 'extruder2'}, 'extruder2': {'target': 0.0}}
    if ace: printer['ace'] = {}
    for mname, vs in (extra_vars or {}).items(): printer['gcode_macro ' + mname] = vs
    def raise_(m): raise Raise(m)
    try: out = env.from_string(ms[name]).render(printer=printer, params=params, action_raise_error=raise_, action_respond_info=lambda m: '')
    except Raise as e: return ["RAISE: " + str(e)]
    return [l.strip() for l in out.splitlines() if l.strip()]
for path in ("factory/ultra/config/offset_calibrate.cfg", "factory/ultra-s/config/offset_calibrate.cfg"):
    ms = macros_of(path)
    for a in (False, True):
        assist_check("%s NOZZLE_PREPARE ace=%s" % (path, a), run_other(ms, "NOZZLE_PREPARE", {"T": "2"}, a), a)
        assist_check("%s POP ace=%s" % (path, a), run_other(ms, "POP", {"T": "3"}, a), a)
    want(path + " NOZZLE_PREPARE assist tool", run_other(ms, "NOZZLE_PREPARE", {"T": "2"}, True), "ACE_ENABLE_FEED_ASSIST T=2", "ACE_DISABLE_FEED_ASSIST T=2")
    want(path + " POP assist tool", run_other(ms, "POP", {"T": "3"}, True), "ACE_ENABLE_FEED_ASSIST T=3", "ACE_DISABLE_FEED_ASSIST T=3")
zms = macros_of("zr_tools/zr_tools.cfg")
def _vars(path, name):
    t = open(os.path.join(ROOT, path)).read(); m = re.search(r'^\[gcode_macro %s\]\n((?:(?!\[).*\n)*)' % re.escape(name), t, re.M); out = {}
    for vl in re.finditer(r'^variable_(\w+):\s*([^#\n]*?)\s*(?:#.*)?$', m.group(1), re.M):
        try: out[vl.group(1)] = eval(vl.group(2), {}, {})
        except Exception: out[vl.group(1)] = vl.group(2)
    return out
ZV = {"_WM_LOAD_SETTINGS": _vars("zr_tools/zr_tools.cfg", "_WM_LOAD_SETTINGS")}
for a in (False, True):
    zl = run_other(zms, "_ZR_LOAD", {"T": "1"}, a, ZV)
    want("_ZR_LOAD ace=%s: picks up the tool and heats at the wipe area, no purge of its own" % a, zl, "_WM_ZR_LOAD_GO T=1", none=("G1 E100", "ZR_PURGE"))
    if not a and any("ACE_" in l for l in zl): bad.append("_ZR_LOAD without an ACE calls ACE commands:\n" + "\n".join(zl))
want("_ZR_LOAD refuses while printing", run_other(zms, "_ZR_LOAD", {"T": "1"}, False, ZV, printing=True), "RAISE")
# every macro the file calls that is not defined here must be a WonderMaker or Klipper command that exists in the repo's factory files

# F-116 / F-117: homing only when needed, all extruders to 140 C, hot Z kept, X and Y limit (items 39 and 40, idea 2 of item 41)
want("rapid: homed already, no G28", run("WM_OFFSETS_RAPID", {"CONFIRM": "1", "CLEANED": "1"}), "RAPID_MODE T=0", none=("G28",))
want("rapid: not homed, G28", run("WM_OFFSETS_RAPID", {"CONFIRM": "1", "CLEANED": "1"}, homed="x"), "G28")
want("rapid (F-218): no heating, all four nozzles wait until under 80 C", run("WM_OFFSETS_RAPID", {"CONFIRM": "1", "CLEANED": "1"}), "waiting until all nozzles are under 80 C", "TEMPERATURE_WAIT SENSOR=extruder MAXIMUM=80", "TEMPERATURE_WAIT SENSOR=extruder1 MAXIMUM=80", "TEMPERATURE_WAIT SENSOR=extruder2 MAXIMUM=80", "TEMPERATURE_WAIT SENSOR=extruder3 MAXIMUM=80", none=("TARGET=140",))
want("rapid (F-218): two tools, only two nozzles wait", run("WM_OFFSETS_RAPID", {"CONFIRM": "1", "CLEANED": "1"}, sv={"thr_number": 2}), "SENSOR=extruder1 MAXIMUM=80", none=("SENSOR=extruder2 MAXIMUM=80",))
want("rapid: hot Z done, the check keeps Z and the limit is 0.2", run("WM_OFFSETS_RAPID", {"CONFIRM": "1", "CLEANED": "1"}, sv={"wm_hot_z_done": 1}), "the saved hot Z offsets are kept", "_WM_OFFSET_CHECK T=1 OX=0.28 OY=0.34 OZ=-0.026 KEEPZ=1 LIMIT=0.2", "_WM_OFFSET_CHECK T=3 OX=0.3 OY=0.09 OZ=0.136 KEEPZ=1 LIMIT=0.2", none=("_WM_OFFSET_CHECK T=0",))
want("rapid: hot Z never done, the Z of the run is saved", run("WM_OFFSETS_RAPID", {"CONFIRM": "1", "CLEANED": "1"}), "hot Z was never done", "KEEPZ=0")
want("rapid: XYLIMIT overrides the limit", run("WM_OFFSETS_RAPID", {"CONFIRM": "1", "CLEANED": "1", "XYLIMIT": "0.01"}), "LIMIT=0.01")
want("accurate start: all extruders to 140 C, no G28 when homed", run("_WM_OFFSETS_ACCURATE", {"CONFIRM": "1"}), "HEATER=extruder3 TARGET=140", "NOZZLE_PREPARE S=220 T=0", none=("G28",))
want("accurate last tool: the check after every tool, hot Z kept", run("_WM_OFFSETS_ACCURATE", {"STEP": "clean", "N": "3"}, sv={"wm_hot_z_done": 1}), "RAPID_MODE T=1", "_WM_OFFSET_CHECK T=1 OX=0.28 OY=0.34 OZ=-0.026 KEEPZ=1 LIMIT=0.2", "_WM_OFFSET_CHECK T=3", none=("_WM_OFFSET_CHECK T=0",))
want("accurate last tool, flag missing: the Z of the run is saved", run("_WM_OFFSETS_ACCURATE", {"STEP": "clean", "N": "3"}), "KEEPZ=0")
want("check: inside the limit keeps Z and reports", run("_WM_OFFSET_CHECK", {"T": "1", "OX": "0.28", "OY": "0.34", "OZ": "-0.026", "KEEPZ": "1", "LIMIT": "0.2"}), "SAVE_T_OFFSET T=1 Z=-0.026", "Z kept at the hot Z value -0.0260", none=("_WM_FAIL", "TURN_OFF_HEATERS"))
want("check: no flag, Z of the run stays", run("_WM_OFFSET_CHECK", {"T": "1", "OX": "0.28", "OY": "0.34", "OZ": "-0.026", "KEEPZ": "0", "LIMIT": "0.2"}), "Z of this run saved", none=("SAVE_T_OFFSET", "_WM_FAIL"))
want("check: X moved over the limit puts the old values back and stops", run("_WM_OFFSET_CHECK", {"T": "1", "OX": "0.0", "OY": "0.34", "OZ": "-0.026", "KEEPZ": "1", "LIMIT": "0.2"}), "SAVE_T_OFFSET T=1 X=0.0 Y=0.34 Z=-0.026", "TURN_OFF_HEATERS", "M106 S0", "_WM_FAIL MSG=", "T1 moved X +0.280", none=("Z kept",))
want("check: Y moved over the limit also stops", run("_WM_OFFSET_CHECK", {"T": "2", "OX": "0.27", "OY": "0.01", "OZ": "0.059", "KEEPZ": "0", "LIMIT": "0.2"}), "_WM_FAIL MSG=", "T2 moved X +0.000 and Y +0.340")

# F-150: heating at the wipe position (RESUME, G29, NOZZLE_PREPARE, POP, LOAD_FILAMENT, UNLOAD_FILAMENT, _WM_ACE_GRAB, ACE_WM_LOAD, _WM_GO_WIPE)
def run_gw(name, params, path, extra=None, cur=0, homed="xyz", pos=None, ms=None, ace=False, ev=None, state='standby'):
    ms = ms or macros_of(path)
    vs = _vars(path, name) if path else {}
    printer = {'save_variables': {'variables': {'current_extruder': cur, 'wipe_position': [-13.0, 240.0], 'thr_number': 4, 'box_modify_t0': 0, 'box_modify_t1': 1, 'box_modify_t2': 2, 'box_modify_t3': 3, 'box_modify_t0_backup': 0, 'box_modify_t1_backup': 1, 'box_modify_t2_backup': 2, 'box_modify_t3_backup': 3}}, 'print_stats': {'state': state},
               'toolhead': {'homed_axes': homed, 'position': pos or {'x': 150.0, 'y': 1.0, 'z': 20.0}, 'extruder': 'extruder'}, 'heater_bed': {'target': 0.0}, 'extruder': {'temperature': 25.0}, 'extruder1': {'temperature': 25.0}}
    if ace: printer['ace'] = {}
    for mname in (extra or []): printer['gcode_macro ' + mname] = {}
    for k, v in (ev or {}).items(): printer[k] = v
    def raise_(m): raise Raise(m)
    try: out = env.from_string(ms[name]).render(printer=printer, params=params, action_raise_error=raise_, action_respond_info=lambda m: '', **vs)
    except Raise as e: return ["RAISE: " + str(e)]
    return [l.strip() for l in out.splitlines() if l.strip()]
gwm = macros_of("rpi-cfg/rpi_base.cfg")
want("_WM_GO_WIPE: far away goes to the wipe position", run_gw("_WM_GO_WIPE", {}, "rpi-cfg/rpi_base.cfg", ms=gwm), "G0 Y240.0 F12000", "G0 X-13.0 F12000", "_WM_CAL_CLEARANCE", "RESTORE_GCODE_STATE NAME=_wm_go_wipe")
want("_WM_GO_WIPE: already there does nothing", run_gw("_WM_GO_WIPE", {}, "rpi-cfg/rpi_base.cfg", ms=gwm, pos={'x': -13.0, 'y': 240.0, 'z': 20.0}), none=("G0 ", "z_rise"))
want("_WM_GO_WIPE: not homed homes X Y first", run_gw("_WM_GO_WIPE", {}, "rpi-cfg/rpi_base.cfg", ms=gwm, homed=""), "G28 X Y", "G0 Y240.0 F12000")
for path in ("factory/ultra/config/macros.cfg", "factory/ultra-s/config/macros.cfg"):
    rm = run_gw("RESUME", {}, path, extra=["_WM_GO_WIPE"], state="paused", ev={'configfile': {'settings': {'idle_timeout': {'timeout': 600}}}})
    j = "\n".join(rm); gi = j.find("_WM_GO_WIPE"); hi = j.find("M104 S")
    if not (0 <= gi < hi): bad.append("%s RESUME: _WM_GO_WIPE must come before the first nozzle heating in\n%s" % (path, j))
    want(path + " RESUME without the helper keeps working", run_gw("RESUME", {}, path, state="paused", ev={'configfile': {'settings': {'idle_timeout': {'timeout': 600}}}}), none=("_WM_GO_WIPE",))
    want(path + " G29 heats and wipes at the wipe position", run_gw("G29", {}, path, extra=["_WM_GO_WIPE"], ev={'configfile': {'settings': {'bed_mesh': {'probe_count': [7, 7]}}}}), "_WM_GO_WIPE", "M109 S140", none=("G1 X150 Y135",))
    want(path + " G29 without the helper heats at the bed centre as before", run_gw("G29", {}, path, ev={'configfile': {'settings': {'bed_mesh': {'probe_count': [7, 7]}}}}), "G1 X150 Y135 F3000", none=("_WM_GO_WIPE",))
    for T, cn in (("1", "1"), ("0", "0")):
        ld = run_gw("LOAD_FILAMENT", {"T": T}, path, extra=["_WM_GO_WIPE_HEAT"], cur=(0 if T == "1" else 0))
        want("%s LOAD_FILAMENT T%s heats at the wipe position, wipes after, parks" % (path, T), ld, "_WM_GO_WIPE_HEAT T=%s S=220" % T, "WIPE_NOZZLE", "PARK_CURRENT_TOOL", "M104 S0 T%s" % T, none=("M109 S220",))
        if ld.index("WIPE_NOZZLE") < max(i for i, l in enumerate(ld) if l.startswith("G1 E")): bad.append("%s LOAD_FILAMENT: the wipe must come after the load in\n%s" % (path, "\n".join(ld)))
    want(path + " LOAD_FILAMENT T1 picks the head up when T0 is on the carriage", run_gw("LOAD_FILAMENT", {"T": "1"}, path, extra=["_WM_GO_WIPE_HEAT"], cur=0), "_CHANGE_TOOL T=1")
    want(path + " LOAD_FILAMENT T1 does not change tool when it is already on the carriage", run_gw("LOAD_FILAMENT", {"T": "1"}, path, extra=["_WM_GO_WIPE_HEAT"], cur=1), "_WM_GO_WIPE_HEAT T=1 S=220", none=("_CHANGE_TOOL",))
    want(path + " LOAD_FILAMENT not homed homes first", run_gw("LOAD_FILAMENT", {"T": "0"}, path, extra=["_WM_GO_WIPE_HEAT"], homed=""), "G28")
    want(path + " LOAD_FILAMENT without zr_tools heats where it is as before", run_gw("LOAD_FILAMENT", {"T": "0"}, path), "M109 S220 T0", none=("_WM_GO_WIPE_HEAT", "WIPE_NOZZLE", "PARK_CURRENT_TOOL", "_CHANGE_TOOL"))
    ul = run_gw("UNLOAD_FILAMENT", {"T": "2"}, path, extra=["_WM_GO_WIPE_HEAT"], cur=2)
    want(path + " UNLOAD_FILAMENT heats at the wipe position, retracts, wipes, parks", ul, "_WM_GO_WIPE_HEAT T=2 S=220", "G1 E-45 F600", "WIPE_NOZZLE", "SET_STEPPER_ENABLE STEPPER=extruder2 ENABLE=0", none=("M109 S220", "_CHANGE_TOOL"))
    if ul.index("WIPE_NOZZLE") < ul.index("G1 E-45 F600"): bad.append("%s UNLOAD_FILAMENT: the wipe must come after the retract in\n%s" % (path, "\n".join(ul)))
for path in ("factory/ultra/config/offset_calibrate.cfg", "factory/ultra-s/config/offset_calibrate.cfg"):
    npj = run_gw("NOZZLE_PREPARE", {"T": "1"}, path, extra=["_WM_GO_WIPE"])
    want(path + " NOZZLE_PREPARE heats to 220 at the wipe position and goes back", npj, "SAVE_GCODE_STATE NAME=_wm_prep", "_WM_GO_WIPE", "M109 S220 T1", "RESTORE_GCODE_STATE NAME=_wm_prep MOVE=1")
    j = "\n".join(npj)
    if not (j.find("PROBE") < j.find("_WM_GO_WIPE") < j.find("M109 S220") < j.find("RESTORE_GCODE_STATE NAME=_wm_prep") < j.find("G1 E120")): bad.append("%s NOZZLE_PREPARE: order probe, wipe position, heat, back, purge broken in\n%s" % (path, j))
    want(path + " NOZZLE_PREPARE without the helper heats at the purge spot as before", run_gw("NOZZLE_PREPARE", {"T": "1"}, path), "M109 S220 T1", none=("_WM_GO_WIPE", "_wm_prep"))
    pp = run_gw("POP", {"T": "1"}, path, extra=["_WM_GO_WIPE"], cur=0)
    j = "\n".join(pp)
    want(path + " POP heats to 222 at the wipe position and goes back", pp, "_WM_GO_WIPE", "M109 S222 T1", "RESTORE_GCODE_STATE NAME=_wm_pop MOVE=1", "G1 Y2 Z2")
    if not (j.find("_WM_GO_WIPE") < j.find("M109 S222") < j.find("RESTORE_GCODE_STATE NAME=_wm_pop") < j.find("G1 Y2 Z2")): bad.append("%s POP: order broken in\n%s" % (path, j))
cwm = macros_of("rpi-cfg/rpi_calibration.cfg")
want("_WM_NOZZLE_PREPARE heats to the hot temperature at the wipe position", run_gw("_WM_NOZZLE_PREPARE", {"S": "230", "T": "1"}, "rpi-cfg/rpi_calibration.cfg", ms=cwm, extra=["_WM_GO_WIPE"], ev={'filament_switch_sensor filament1': {'filament_detected': True}}), "_WM_GO_WIPE", "M109 S230 T1", "RESTORE_GCODE_STATE NAME=_wm_prep MOVE=1")
if os.path.exists(os.path.join(ROOT, "../wm-ultra-fluidd-acepro-panel/config/rpi_ace.cfg")):   # the panel repo lies next to this one (a test copy of this repo has no neighbour: these checks are skipped there)
    acem = macros_of("../wm-ultra-fluidd-acepro-panel/config/rpi_ace.cfg")
    want("_WM_ACE_GRAB: the tool on the carriage heats at the wipe position", run_gw("_WM_ACE_GRAB", {"T": "1"}, "../wm-ultra-fluidd-acepro-panel/config/rpi_ace.cfg", ms=acem, extra=["_WM_GO_WIPE_HEAT", "_WM_ACE"], cur=1, ev={'extruder1': {'temperature': 25.0}}), "_WM_GO_WIPE_HEAT T=1 S=220", none=("TEMPERATURE_WAIT", "WIPE_NOZZLE"))
    want("_WM_ACE_GRAB: a head that is not on the carriage heats where it is", run_gw("_WM_ACE_GRAB", {"T": "1"}, "../wm-ultra-fluidd-acepro-panel/config/rpi_ace.cfg", ms=acem, extra=["_WM_GO_WIPE_HEAT", "_WM_ACE"], cur=0, ev={'extruder1': {'temperature': 25.0}}), "SET_HEATER_TEMPERATURE HEATER=extruder1 TARGET=220", "TEMPERATURE_WAIT", none=("_WM_GO_WIPE_HEAT",))
    want("_WM_ACE_GRAB: already hot does not heat", run_gw("_WM_ACE_GRAB", {"T": "1"}, "../wm-ultra-fluidd-acepro-panel/config/rpi_ace.cfg", ms=acem, extra=["_WM_GO_WIPE_HEAT", "_WM_ACE"], cur=1, ev={'extruder1': {'temperature': 220.0}}), none=("_WM_GO_WIPE_HEAT", "SET_HEATER_TEMPERATURE"))
    _ap = "../wm-ultra-fluidd-acepro-panel/config/rpi_ace.cfg"
    def _ace(mode, since=-1, uq=""):
        return {'gcode_macro _WM_ACE': {'mode': mode, 'unloading_since': since, 'unload_queue': uq, 'unload_wait': 0}, 'toolhead': {'homed_axes': 'xyz', 'position': {'x': 0, 'y': 0, 'z': 20}, 'extruder': 'extruder', 'estimated_print_time': 1000.0}}
    want("ACE_WM_UNLOAD while the ACE is busy waits (F-153)", run_gw("ACE_WM_UNLOAD", {"T": "1"}, _ap, ms=acem, ev=_ace("unload_hub")), "UNLOAD_QUEUE VALUE='\"1\"'".replace("UNLOAD_QUEUE", "VARIABLE=unload_queue"), "UPDATE_DELAYED_GCODE ID=_wm_ace_unload_next DURATION=2", none=("RAISE", "_CHANGE_TOOL", "z_rise"))
    want("ACE_WM_UNLOAD while another unload picks up its tool waits (F-153)", run_gw("ACE_WM_UNLOAD", {"T": "1"}, _ap, ms=acem, ev=_ace("idle", since=990)), "UPDATE_DELAYED_GCODE ID=_wm_ace_unload_next DURATION=2", none=("RAISE", "_CHANGE_TOOL"))
    want("ACE_WM_UNLOAD with the ACE free runs and marks the start (F-153)", run_gw("ACE_WM_UNLOAD", {"T": "1"}, _ap, ms=acem, ev=_ace("idle")), "VARIABLE=unloading_since VALUE=1000", "_CHANGE_TOOL T=1", "_WM_ACE_UNLOAD_RUN T=1", none=("RAISE", "unload_queue"))
    want("ACE_WM_UNLOAD with an old unfinished start (over 10 minutes) runs again (F-153)", run_gw("ACE_WM_UNLOAD", {"T": "1"}, _ap, ms=acem, ev=_ace("idle", since=100)), "_CHANGE_TOOL T=1", none=("RAISE", "unload_queue"))

if bad: print("\n".join(bad)); sys.exit(1)
print("all %d macros render and behave" % len(macros))
