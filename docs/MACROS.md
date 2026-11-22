# MACROS.md - every macro of the WonderMaker Ultra / Ultra-S on the Raspberry Pi

Generated 2026-11-18 from the live config of the dev Pi (the dev Pi), snapshot `05-notes/reference/pi-config-snapshot-2026-11-18/`.  
Klipper v0.13.0-827-g29d4ec2d6 (upstream master 2026-11-10 + WonderMaker additions, see DIFFERENCES.md), Moonraker newer than 0.11.0, Fluidd v1.38.0 (patched, see FLUIDD.md), Debian 12.  
Checked against: Klipper docs of the installed version (`reference/klipper-docs-0.13.0-827-g29d4ec2d6/docs/G-Codes.md`, online https://www.klipper3d.org/G-Codes.html), the live command registry of the running Klipper (`/printer/gcode/help`) and the Klipper source on the Pi, 2026-11-18.

## How to read this
- **What it does** = the macro's own `description:` or a plain-words line written from reading its code. Entries marked *(structure only)* were not read line by line; the facts below that line (calls, variables, objects) are extracted by script from the file and are exact.
- **Calls / Called by**: other macros (names are case-insensitive in Klipper). **Variables**: the `variable_` settings of the macro. **Uses**: Klipper objects read (`printer.<object>`), macro variables set (`SET_GCODE_VARIABLE`) and saved variables written (`SAVE_VARIABLE`).
- **Commands**: every G-code command used in the body was looked up (macro, Klipper built-in, or module command). Result for all macros: **no unknown command** (see Known problems for notes).
- **Risk**: MOVES THE TOOLHEAD, HEATS, ACE, LOAD CELL / SETTER (set by script from the commands used). **Tested**: from FIX-LOG.md; *no per-macro record* means the log has no separate test line for it.
- **Fluidd**: the category of its button in Fluidd's macro list (`—` = hidden / not a button).

## Files and macro counts
| File | Macros / timers | What |
|---|---|---|
| change_macros.cfg | 32 | WonderMaker factory tool change (lock/unlock, T0-T3) |
| extruder0.cfg | 1 | Tool head 0: runout/insert handling |
| extruder1.cfg | 1 | Tool head 1 |
| extruder2.cfg | 1 | Tool head 2 |
| extruder3.cfg | 1 | Tool head 3 |
| fz-wipe-nozzle.cfg | 3 | Factory wipe macros |
| load_cell.cfg | 2 | Load cell trigger helpers |
| macros.cfg | 31 | WonderMaker factory print macros (start/end/pause/resume, heaters, filament load) |
| offset_calibrate.cfg | 15 | WonderMaker factory tool offset calibration |
| rpi_ace.cfg | 24 | ACE panel: ACE load/unload/dry macros |
| rpi_base.cfg | 52 | Installer part: safety, LEDs, head sensors, unload runner, z_rise, homing, bed soak, heat at wipe, purge |
| rpi_calibration.cfg | 97 | Installer part: calibration (first run, Z trim, setter, offsets, PID, shaper, mesh) |
| rpi_endless.cfg | 11 | ACE panel: endless spool |
| rpi_fan_guard.cfg | 2 | Installer part: fan failure guard |
| rpi_nozzle.cfg | 31 | Installer part: nozzle macros, flow matching, auto speed |
| rpi_pi.cfg | 1 | Installer part: Pi/board sensors, chamber light |
| rpi_stats.cfg | 5 | ACE panel: tool change and print time statistics |
| timelapse.cfg | 10 | moonraker-timelapse macros |
| zr_tools.cfg | 16 | ZR tools: tool info/mapping, chamber, load/unload without ACE |
| **total** | **336** | 26 of them are delayed_gcode timers |


## change_macros.cfg
WonderMaker factory tool change (lock/unlock, T0-T3)

### UNLOCK
- **File / lines**: change_macros.cfg L1-6 (gcode_macro)
- **What it does**: Releases the tool lock: homes the gear-shift (echelon) motor, then switches it off.
- **Calls**: -
- **Called by**: _CHECK_AND_UNLOCK, _LOCK_TOOL_FINISH, _UNLOCK_TOOL
- **Variables**: -
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: ECHELON_STEPPER_DISABLE, ECHELON_STEPPER_HOMING, M400) - checked 2026-11-18
- **Risk**: none  |  **Tags**: tool-change  |  **Fluidd**: WM Ultra Tool Change
- **Tested**: no per-macro record in FIX-LOG.md
### _UNLOCK_TOOL
- **File / lines**: change_macros.cfg L7-59 (gcode_macro)
- **What it does**: Puts the carried tool head back into its dock: moves to the dock position (homing XY first if needed), unlocks, checks it worked.
- **Calls**: SET_GCODE_OFFSET, UNLOCK, _CHECK_AND_UNLOCK, z_rise
- **Called by**: PARK_CURRENT_TOOL, PARK_CURRENT_TOOL_RETRY, _CHANGING_TOOL, _WM_NCHANGE_RUN
- **Variables**: -
- **Uses**: reads printer.gcode_move, printer.save_variables, printer.toolhead
- **Commands**: all exist (built-in/module commands used: G0, G28, G4, G90, M400) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, ACE (+ through the macros it calls: HEATS)  |  **Tags**: tool-change  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _CHECK_AND_UNLOCK
- **File / lines**: change_macros.cfg L60-78 (gcode_macro)
- **What it does**: After UNLOCK: checks that a head was really released; on failure stores a tool-change error.
- **Calls**: UNLOCK, UNLOCK_TOOL_FINISH
- **Called by**: _UNLOCK_TOOL
- **Variables**: -
- **Uses**: reads printer.save_variables; saves fail_flag VALUE, fail_tool VALUE
- **Commands**: all exist (built-in/module commands used: G0, M400, SAVE_VARIABLE) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, ACE  |  **Tags**: tool-change  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### UNLOCK_TOOL_FINISH
- **File / lines**: change_macros.cfg L79-97 (gcode_macro)
- **What it does**: Last step of an unlock: reports a failure or clears the saved current-tool value.
- **Calls**: -
- **Called by**: _CHECK_AND_UNLOCK
- **Variables**: -
- **Uses**: reads printer.custom_hall, printer.save_variables; saves current_extruder VALUE, fail_flag VALUE, fail_tool VALUE
- **Commands**: all exist (built-in/module commands used: SAVE_VARIABLE) - checked 2026-11-18
- **Risk**: none  |  **Tags**: tool-change  |  **Fluidd**: WM Ultra Tool Change
- **Tested**: no per-macro record in FIX-LOG.md
### LOCK
- **File / lines**: change_macros.cfg L98-109 (gcode_macro)
- **What it does**: Locks the tool head onto the carriage: homes the gear-shift motor and checks the lock.
- **Calls**: _LOCK_CHECK
- **Called by**: _CHECK_AND_LOCK
- **Variables**: -
- **Uses**: sets variables of _LOCK_CHECK
- **Commands**: all exist (built-in/module commands used: ECHELON_STEPPER_DISABLE, ECHELON_STEPPER_HOMING, M400, SET_GCODE_VARIABLE) - checked 2026-11-18
- **Risk**: none  |  **Tags**: tool-change  |  **Fluidd**: WM Ultra Tool Change
- **Tested**: no per-macro record in FIX-LOG.md
### _LOCK_CHECK
- **File / lines**: change_macros.cfg L110-122 (gcode_macro)
- **What it does**: Checks the lock; retries once through a counter variable (retry).
- **Calls**: -
- **Called by**: LOCK
- **Variables**: retry
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: ECHELON_STEPPER, M400) - checked 2026-11-18
- **Risk**: none  |  **Tags**: tool-change  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _LOCK_TOOL
- **File / lines**: change_macros.cfg L123-169 (gcode_macro)
- **What it does**: Picks a tool head up from its dock (homing XY first if needed), locks it, checks head order.
- **Calls**: SET_GCODE_OFFSET, _CHECK_AND_LOCK, _CHECK_T_SEQUENCE, z_rise
- **Called by**: _CHANGING_TOOL
- **Variables**: -
- **Uses**: reads printer.gcode_move, printer.save_variables, printer.toolhead
- **Commands**: all exist (built-in/module commands used: G0, G28, G90, M400) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, ACE (+ through the macros it calls: HEATS)  |  **Tags**: tool-change  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _CHECK_AND_LOCK
- **File / lines**: change_macros.cfg L170-184 (gcode_macro)
- **What it does**: After LOCK: checks that a head is on the carriage and locked; reports a failure.
- **Calls**: LOCK, _LOCK_TOOL_FINISH
- **Called by**: _LOCK_TOOL
- **Variables**: -
- **Uses**: reads printer.save_variables; saves fail_flag VALUE
- **Commands**: all exist (built-in/module commands used: SAVE_VARIABLE) - checked 2026-11-18
- **Risk**: ACE  |  **Tags**: tool-change  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _LOCK_TOOL_FINISH
- **File / lines**: change_macros.cfg L185-203 (gcode_macro)
- **What it does**: Last step of a lock: turns the gear-shift motor back to 0 degrees and checks the head order.
- **Calls**: UNLOCK
- **Called by**: _CHECK_AND_LOCK
- **Variables**: -
- **Uses**: reads printer.custom_hall, printer.save_variables; saves fail_flag VALUE
- **Commands**: all exist (built-in/module commands used: SAVE_VARIABLE) - checked 2026-11-18
- **Risk**: none  |  **Tags**: tool-change  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _CHECK_T_SEQUENCE
- **File / lines**: change_macros.cfg L204-223 (gcode_macro)
- **What it does**: Checks that the heads sit in the right order after a pick-up (error if mixed up).
- **Calls**: -
- **Called by**: _LOCK_TOOL
- **Variables**: -
- **Uses**: reads printer.save_variables; sets variables of _CHECK_CHANGE_TOOL; saves fail_flag VALUE
- **Commands**: all exist (built-in/module commands used: SAVE_VARIABLE, SET_GCODE_VARIABLE) - checked 2026-11-18
- **Risk**: none  |  **Tags**: misc  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### T0
- **File / lines**: change_macros.cfg L224-233 (gcode_macro)
- **What it does**: Tool change to head T0 (follows the box_modify_t0 remap); calls _CHANGE_TOOL.
- **Calls**: _CHANGE_TOOL
- **Called by**: CALIBRATE_TOOL_OFFSET, G29, WM_SCREWS_CAL, Z_HOMING, _WM_AUTO_SPEED_READY, _WM_BEDWARP_START, _WM_SETTER_GO
- **Variables**: -
- **Uses**: reads printer.gcode_move, printer.save_variables
- **Commands**: all exist (built-in/module commands used: G1) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD (+ through the macros it calls: ACE, HEATS)  |  **Tags**: tool-change  |  **Fluidd**: WM Ultra Tool Change
- **Tested**: no per-macro record in FIX-LOG.md
### T1
- **File / lines**: change_macros.cfg L234-242 (gcode_macro)
- **What it does**: Tool change to head T1 (follows box_modify_t1).
- **Calls**: _CHANGE_TOOL
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: reads printer.gcode_move, printer.save_variables
- **Commands**: all exist (built-in/module commands used: G1) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD (+ through the macros it calls: ACE, HEATS)  |  **Tags**: tool-change  |  **Fluidd**: WM Ultra Tool Change
- **Tested**: no per-macro record in FIX-LOG.md
### T2
- **File / lines**: change_macros.cfg L243-251 (gcode_macro)
- **What it does**: Tool change to head T2 (follows box_modify_t2).
- **Calls**: _CHANGE_TOOL
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: reads printer.gcode_move, printer.save_variables
- **Commands**: all exist (built-in/module commands used: G1) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD (+ through the macros it calls: ACE, HEATS)  |  **Tags**: tool-change  |  **Fluidd**: WM Ultra Tool Change
- **Tested**: no per-macro record in FIX-LOG.md
### T3
- **File / lines**: change_macros.cfg L252-262 (gcode_macro)
- **What it does**: Tool change to head T3 (follows box_modify_t3).
- **Calls**: _CHANGE_TOOL
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: reads printer.gcode_move, printer.save_variables
- **Commands**: all exist (built-in/module commands used: G1) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD (+ through the macros it calls: ACE, HEATS)  |  **Tags**: tool-change  |  **Fluidd**: WM Ultra Tool Change
- **Tested**: no per-macro record in FIX-LOG.md
### _CHANGE_TOOL
- **File / lines**: change_macros.cfg L263-301 (gcode_macro)
- **What it does**: The factory tool change: checks saved values, Hall sensor, head presence, then runs _CHANGING_TOOL and the end checks.
- **Calls**: _CHANGING_TOOL, _CHECK_CHANGE_TOOL, _CHECK_CHANGE_TOOL_AGAIN, _WM_CAL_CLEARANCE, _check_current_extruder_value, _check_hall_sensor, _check_tool_exist
- **Called by**: ACE_WM_LOAD, ACE_WM_UNLOAD, LOAD_FILAMENT, T0, T1, T2, T3, UNLOAD_FILAMENT, WM_ENDLESS_CONTINUE, WM_NOZZLE_GROWTH_CAL, WM_OFFSETS_Z_HOT, ZR_LOAD, ZR_RETRACT, _WM_START_PURGE_RUN, _WM_WIPE_PURGE
- **Variables**: save_position, target_tool
- **Uses**: reads printer.save_variables; sets variables of _CHANGE_TOOL, _CHECK_CHANGE_TOOL; saves changing_tool VALUE, current_extruder_backup VALUE, fail_flag VALUE, fail_tool VALUE
- **Commands**: all exist (built-in/module commands used: RESPOND, SAVE_VARIABLE, SET_GCODE_VARIABLE) - checked 2026-11-18
- **Risk**: none (+ through the macros it calls: ACE, HEATS, MOVES THE TOOLHEAD)  |  **Tags**: tool-change  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _CHECK_CHANGE_TOOL_AGAIN
- **File / lines**: change_macros.cfg L302-313 (gcode_macro)
- **What it does**: Retry of the tool-change check, then the tool change again.
- **Calls**: _CHECK_CHANGE_TOOL
- **Called by**: _CHANGE_TOOL
- **Variables**: -
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: M118) - checked 2026-11-18
- **Risk**: none (+ through the macros it calls: ACE, HEATS, MOVES THE TOOLHEAD)  |  **Tags**: tool-change  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _CHANGING_TOOL
- **File / lines**: change_macros.cfg L314-365 (gcode_macro)
- **What it does**: Does the physical tool change: raise Z, park the old head (_UNLOCK_TOOL), pick the new one (_LOCK_TOOL), lower Z; sets speed factors.
- **Calls**: _LOCK_TOOL, _UNLOCK_TOOL, _descend_z, _raise_z
- **Called by**: _CHANGE_TOOL, _CHECK_CHANGE_TOOL
- **Variables**: -
- **Uses**: reads printer.gcode_move, printer.save_variables, printer.toolhead; saves changing_tool VALUE
- **Commands**: all exist (built-in/module commands used: G28, M118, M220, QUERY_ENDSTOPS, RESTORE_GCODE_STATE, SAVE_GCODE_STATE, SAVE_VARIABLE) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD (+ through the macros it calls: ACE, HEATS)  |  **Tags**: tool-change  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _CHECK_CHANGE_TOOL
- **File / lines**: change_macros.cfg L366-430 (gcode_macro)
- **What it does**: End-of-tool-change check: saved current extruder, Hall sensor, head present; pauses the print and reports on a failure.
- **Calls**: M221, PAUSE, _CHANGING_TOOL, _ENABLE_SENSOR, _OFFSET_SET, _WAIT_TOOL_TEMPERATURE, _check_current_extruder_value, _check_hall_sensor, _check_tool_exist
- **Called by**: _CHANGE_TOOL, _CHECK_CHANGE_TOOL_AGAIN
- **Variables**: retry
- **Uses**: reads printer.print_stats, printer.save_variables; sets variables of _CHECK_CHANGE_TOOL; saves changing_tool VALUE, current_extruder VALUE, fail_flag VALUE
- **Commands**: all exist (built-in/module commands used: ACTIVATE_EXTRUDER, G1, G28, G90, SAVE_VARIABLE, SET_GCODE_VARIABLE, SET_PRESSURE_ADVANCE) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, ACE (+ through the macros it calls: HEATS)  |  **Tags**: tool-change  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _raise_z
- **File / lines**: change_macros.cfg L431-448 (gcode_macro)
- **What it does**: Raises Z before a tool change.
- **Calls**: -
- **Called by**: _CHANGING_TOOL
- **Variables**: -
- **Uses**: reads printer.configfile, printer.save_variables, printer.toolhead; sets variables of _descend_z
- **Commands**: all exist (built-in/module commands used: G1, G90, G91, M400, SET_GCODE_VARIABLE) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD  |  **Tags**: misc  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _descend_z
- **File / lines**: change_macros.cfg L449-460 (gcode_macro)
- **What it does**: Lowers Z again after a tool change (only if _raise_z raised it).
- **Calls**: -
- **Called by**: _CHANGING_TOOL
- **Variables**: need_descend
- **Uses**: sets variables of _descend_z
- **Commands**: all exist (built-in/module commands used: G1, G90, G91, M400, SET_GCODE_VARIABLE) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD  |  **Tags**: misc  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _check_tool_exist
- **File / lines**: change_macros.cfg L461-477 (gcode_macro)
- **What it does**: Checks that a tool head is present (Hall sensor value).
- **Calls**: -
- **Called by**: _CHANGE_TOOL, _CHECK_CHANGE_TOOL
- **Variables**: -
- **Uses**: reads printer.custom_hall, printer.save_variables; saves fail_flag VALUE
- **Commands**: all exist (built-in/module commands used: SAVE_VARIABLE) - checked 2026-11-18
- **Risk**: ACE  |  **Tags**: tool-change  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _check_hall_sensor
- **File / lines**: change_macros.cfg L478-490 (gcode_macro)
- **What it does**: Checks that the Hall sensors read normal values.
- **Calls**: -
- **Called by**: _CHANGE_TOOL, _CHECK_CHANGE_TOOL
- **Variables**: -
- **Uses**: reads printer.custom_hall, printer.save_variables; saves fail_flag VALUE
- **Commands**: all exist (built-in/module commands used: SAVE_VARIABLE) - checked 2026-11-18
- **Risk**: none  |  **Tags**: misc  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _check_current_extruder_value
- **File / lines**: change_macros.cfg L491-517 (gcode_macro)
- **What it does**: Checks the saved current_extruder value against the Hall sensors.
- **Calls**: -
- **Called by**: _CHANGE_TOOL, _CHECK_CHANGE_TOOL
- **Variables**: -
- **Uses**: reads printer.custom_hall, printer.save_variables; saves current_extruder VALUE
- **Commands**: all exist (built-in/module commands used: SAVE_VARIABLE) - checked 2026-11-18
- **Risk**: none  |  **Tags**: misc  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WAIT_TOOL_TEMPERATURE
- **File / lines**: change_macros.cfg L518-541 (gcode_macro)
- **What it does**: Waits for the real active heater (heats at the wipe position first, F-150) - does not use M109 Tx because of slot remapping.
- **Calls**: _WM_HEAT_AT_WIPE, _WM_HEAT_BACK
- **Called by**: _CHECK_CHANGE_TOOL
- **Variables**: -
- **Uses**: reads printer.print_stats, printer.toolhead
- **Commands**: all exist (built-in/module commands used: TEMPERATURE_WAIT) - checked 2026-11-18
- **Risk**: HEATS, ACE (+ through the macros it calls: MOVES THE TOOLHEAD)  |  **Tags**: tool-change  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### GET_TOOL_POSITION
- **File / lines**: change_macros.cfg L542-547 (gcode_macro)
- **What it does**: Reads the position of the tool dock (GET_T_POSITION) after homing.
- **Calls**: -
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: G1, G28, GET_T_POSITION) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD  |  **Tags**: tool-change  |  **Fluidd**: WM Factory Calibration
- **Tested**: no per-macro record in FIX-LOG.md
### SAVE_T_POSITON
- **File / lines**: change_macros.cfg L548-602 (gcode_macro)
- **What it does**: Saves a measured dock position after a range check (name spelled so in the factory file).
- **Calls**: -
- **Called by**: _SAVE_TOOL_POSITION
- **Variables**: -
- **Uses**: reads printer.save_variables; saves t{t}_position VALUE
- **Commands**: all exist (built-in/module commands used: SAVE_VARIABLE) - checked 2026-11-18
- **Risk**: none  |  **Tags**: misc  |  **Fluidd**: WM Factory Calibration
- **Tested**: no per-macro record in FIX-LOG.md
### _SAVE_TOOL_POSITION
- **File / lines**: change_macros.cfg L603-616 (gcode_macro)
- **What it does**: Helper for CALIBRATE_TOOL_POSITION: saves the measured dock position.
- **Calls**: SAVE_T_POSITON
- **Called by**: CALIBRATE_TOOL_POSITION
- **Variables**: -
- **Uses**: reads printer.custom_hall
- **Commands**: all exist (built-in/module commands used: none) - checked 2026-11-18
- **Risk**: none  |  **Tags**: tool-change  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### CALIBRATE_TOOL_POSITION
- **File / lines**: change_macros.cfg L617-622 (gcode_macro)
- **What it does**: Measures and saves the dock position of the current tool.
- **Calls**: _SAVE_TOOL_POSITION
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: GET_T_POSITION) - checked 2026-11-18
- **Risk**: none  |  **Tags**: calibration, tool-change  |  **Fluidd**: WM Factory Calibration
- **Tested**: no per-macro record in FIX-LOG.md
### _ENABLE_SENSOR
- **File / lines**: change_macros.cfg L623-633 (gcode_macro)
- **What it does**: Switches the filament sensor of the tool on or off (SET_FILAMENT_SENSOR).
- **Calls**: -
- **Called by**: _CHECK_CHANGE_TOOL
- **Variables**: -
- **Uses**: reads printer.save_variables
- **Commands**: all exist (built-in/module commands used: SET_FILAMENT_SENSOR) - checked 2026-11-18
- **Risk**: none  |  **Tags**: misc  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### PARK_CURRENT_TOOL
- **File / lines**: change_macros.cfg L634-644 (gcode_macro)
- **What it does**: Puts the tool on the carriage back into its dock.
- **Calls**: PARK_CURRENT_TOOL_RETRY, _UNLOCK_TOOL
- **Called by**: CANCEL_PRINT, EXTRUDE_FILAMENT, LOAD_FILAMENT, PRINT_END, UNLOAD_FILAMENT, WM_NOZZLE_FULL_PID, WM_NOZZLE_GROWTH_CAL, WM_OFFSETS_ACCURATE, WM_OFFSETS_RAPID, WM_OFFSETS_Z_HOT, ZR_RETRACT, _WM_HEAD_LOAD, _WM_MATCH_FINISH, _WM_MATCH_RUN, _WM_UNLOAD_END, _WM_ZR_LOAD_GO, _wm_ace_tick
- **Variables**: -
- **Uses**: reads printer.save_variables; saves changing_tool VALUE, fail_flag VALUE
- **Commands**: all exist (built-in/module commands used: RESPOND, SAVE_VARIABLE) - checked 2026-11-18
- **Risk**: none (+ through the macros it calls: ACE, HEATS, MOVES THE TOOLHEAD)  |  **Tags**: tool-change  |  **Fluidd**: WM Ultra Tool Change
- **Tested**: no per-macro record in FIX-LOG.md
### PARK_CURRENT_TOOL_RETRY
- **File / lines**: change_macros.cfg L645-654 (gcode_macro)
- **What it does**: Second try of PARK_CURRENT_TOOL after homing.
- **Calls**: _UNLOCK_TOOL
- **Called by**: PARK_CURRENT_TOOL
- **Variables**: -
- **Uses**: reads printer.save_variables; saves fail_flag VALUE
- **Commands**: all exist (built-in/module commands used: G28, SAVE_VARIABLE) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD (+ through the macros it calls: ACE, HEATS)  |  **Tags**: tool-change  |  **Fluidd**: WM Ultra Tool Change
- **Tested**: no per-macro record in FIX-LOG.md
### _OFFSET_SET
- **File / lines**: change_macros.cfg L655-687 (gcode_macro)
- **What it does**: Applies the XYZ offset of the active tool (+ live Z adjust) with SET_GCODE_OFFSET.
- **Calls**: SET_GCODE_OFFSET
- **Called by**: CALIBRATE_TOOL_Z_OFFSET, _CHECK_CHANGE_TOOL, _WM_ACE_HOME_Z, _WM_ENDLESS_4, _WM_LIVEZ_HEAT, _WM_Z_TOUCH, _WM_Z_TRIM_APPLY
- **Variables**: -
- **Uses**: reads printer.save_variables, printer.toolhead; sets variables of _WM_LIVEZ
- **Commands**: all exist (built-in/module commands used: G28, SET_GCODE_VARIABLE) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD (+ through the macros it calls: ACE, HEATS)  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md

## extruder0.cfg
Tool head 0: runout/insert handling

### delayed_pause0
- **File / lines**: extruder0.cfg L57-61 (delayed_gcode timer)
- **What it does**: Pauses the print 2.5 s after the runout sensor of T0 reported empty (cancelled by insert_gcode).
- **Calls**: PAUSE
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: RESPOND) - checked 2026-11-18
- **Risk**: none (+ through the macros it calls: HEATS, MOVES THE TOOLHEAD)  |  **Tags**: print  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md

## extruder1.cfg
Tool head 1

### delayed_pause1
- **File / lines**: extruder1.cfg L57-61 (delayed_gcode timer)
- **What it does**: Same for T1.
- **Calls**: PAUSE
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: RESPOND) - checked 2026-11-18
- **Risk**: none (+ through the macros it calls: HEATS, MOVES THE TOOLHEAD)  |  **Tags**: print  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md

## extruder2.cfg
Tool head 2

### delayed_pause2
- **File / lines**: extruder2.cfg L58-63 (delayed_gcode timer)
- **What it does**: Same for T2.
- **Calls**: PAUSE
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: RESPOND) - checked 2026-11-18
- **Risk**: none (+ through the macros it calls: HEATS, MOVES THE TOOLHEAD)  |  **Tags**: print  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md

## extruder3.cfg
Tool head 3

### delayed_pause3
- **File / lines**: extruder3.cfg L57-61 (delayed_gcode timer)
- **What it does**: Same for T3.
- **Calls**: PAUSE
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: RESPOND) - checked 2026-11-18
- **Risk**: none (+ through the macros it calls: HEATS, MOVES THE TOOLHEAD)  |  **Tags**: print  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md

## fz-wipe-nozzle.cfg
Factory wipe macros

### WIPE_NOZZLE
- **File / lines**: fz-wipe-nozzle.cfg L4-30 (gcode_macro)
- **What it does**: Wipes the nozzle on the wipe brush: Z up, moves to the saved wipe position, 4 strokes at wipe_speed.
- **Calls**: _WM_CAL_CLEARANCE, z_rise
- **Called by**: CANCEL_PRINT, EXTRUDE_FILAMENT, G29, LOAD_FILAMENT, PRINT_END, RESUME, START_PRINT, UNLOAD_FILAMENT, WM_OFFSETS_RAPID, WM_SCREWS_CAL, Z_HOMING, _WM_ACE_HOME, _WM_BEDWARP_START, _WM_PID_HEAD, _WM_UNLOAD_TIP, _WM_WIPE_PURGE_GO, _WM_ZR_LOAD_GO, _WM_Z_TOUCH, filament_insert_gcode
- **Variables**: wipe_speed
- **Uses**: reads printer.save_variables, printer.toolhead
- **Commands**: all exist (built-in/module commands used: G0, G28, G90, RESPOND, RESTORE_GCODE_STATE, SAVE_GCODE_STATE) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD  |  **Tags**: wipe  |  **Fluidd**: WM Ultra Filament
- **Tested**: no per-macro record in FIX-LOG.md
### _SAVE_WIPE_POSITION
- **File / lines**: fz-wipe-nozzle.cfg L31-40 (gcode_macro)
- **What it does**: Saves the dock hall position as the wipe position.
- **Calls**: -
- **Called by**: CALIBRATE_WIPE_POSITION
- **Variables**: -
- **Uses**: reads printer.custom_hall; saves wipe_position VALUE
- **Commands**: all exist (built-in/module commands used: SAVE_VARIABLE) - checked 2026-11-18
- **Risk**: none  |  **Tags**: wipe  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### CALIBRATE_WIPE_POSITION
- **File / lines**: fz-wipe-nozzle.cfg L41-45 (gcode_macro)
- **What it does**: Reads the head position and saves it as the wipe position.
- **Calls**: _SAVE_WIPE_POSITION
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: GET_T_POSITION) - checked 2026-11-18
- **Risk**: none  |  **Tags**: calibration, wipe  |  **Fluidd**: WM Factory Calibration
- **Tested**: no per-macro record in FIX-LOG.md

## load_cell.cfg
Load cell trigger helpers

### _LEVELING_TRIGGER
- **File / lines**: load_cell.cfg L34-38 (gcode_macro)
- **What it does**: Fires the load cell trigger pin once (pulse) during leveling/probing.
- **Calls**: -
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: G4, WM_PIN_PULSE) - checked 2026-11-18
- **Risk**: none  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _LEVELING_TRIGGER_S
- **File / lines**: load_cell.cfg L39-46 (gcode_macro)
- **What it does**: Fires the load cell trigger pin by hand (set pin low/high with waits).
- **Calls**: -
- **Called by**: Z_HOMING
- **Variables**: -
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: G4, SET_PIN) - checked 2026-11-18
- **Risk**: none  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md

## macros.cfg
WonderMaker factory print macros (start/end/pause/resume, heaters, filament load)

### PRINTER_INIT
- **File / lines**: macros.cfg L1-6 (delayed_gcode timer)
- **What it does**: At start (5 s after boot) restores the extruder flow percentage (RESET_FLOW_EXTRUDER).
- **Calls**: RESET_FLOW_EXTRUDER
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: none) - checked 2026-11-18
- **Risk**: none  |  **Tags**: print  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### START_PRINT
- **File / lines**: macros.cfg L7-108 (gcode_macro)
- **What it does**: Print start: light on, speeds, bed soak mark, heat bed and tool, home, mesh (adaptive or full), wipe, purge settings, tool offsets.
- **Change 2026-11-19 (F-160)**: the print start purge of F-105 (_WM_START_PURGE, one 20 mm purge per used toolhead + KAMP line) is no longer called; the factory left-edge purge (X0 Y70 to Y150, 20 mm) runs again. The F-105 macros stay in rpi_base.cfg, unused. Checked against FIX-LOG F-105, 2026-11-19.
- **Calls**: BED_MESH_CALIBRATE, M104, M109, M190, SET_GCODE_OFFSET, WIPE_NOZZLE, WM_CHAMBER_LIGHT, _WM_BED_SOAK, _WM_BED_SOAK_MARK, _WM_LIVEZ_RESET, _WM_START_PURGE
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: adaptive_mesh, adaptive_mesh_enable, print_body_ready
- **Uses**: reads printer.configfile, printer.max_accel, printer.max_velocity, printer.save_variables; sets variables of START_PRINT; saves box_modify_t0  value
- **Commands**: all exist (built-in/module commands used: BED_MESH_CLEAR, BED_MESH_PROFILE, G1, G28, G90, G91, M118, M140, M400, SAVE_VARIABLE, SET_GCODE_VARIABLE, SET_HEATER_TEMPERATURE, SET_VELOCITY_LIMIT) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, HEATS (+ through the macros it calls: ACE)  |  **Tags**: print  |  **Fluidd**: WM Ultra Print
- **Tested**: print start purge (F-105) tested in real prints 2026-11-17
### PRINT_END
- **File / lines**: macros.cfg L109-151 (gcode_macro)
- **What it does**: Print end: heaters off, fan off, wipe, park the tool head, motors off, reset flow.
- **Calls**: M107, PARK_CURRENT_TOOL, RESET_FLOW_EXTRUDER, WIPE_NOZZLE
- **Called by**: WM_PRINT_END_WATCH
- **Variables**: -
- **Uses**: reads printer.configfile, printer.gcode_move, printer.toolhead, printer.virtual_sdcard; sets variables of START_PRINT; saves box_modify_t0 VALUE, box_modify_t1 VALUE, box_modify_t2 VALUE, box_modify_t3 VALUE, box_modify_t{i}_backup VALUE
- **Commands**: all exist (built-in/module commands used: BED_MESH_CLEAR, G1, G90, M220, M400, M84, RESPOND, SAVE_VARIABLE, SDCARD_RESET_FILE, SET_GCODE_VARIABLE, SET_VELOCITY_LIMIT, TURN_OFF_HEATERS) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD (+ through the macros it calls: ACE, HEATS)  |  **Tags**: print  |  **Fluidd**: WM Ultra Print
- **Tested**: no per-macro record in FIX-LOG.md
### E_axis_move
- **File / lines**: macros.cfg L152-166 (gcode_macro)
- **What it does**: Small extruder-only move used by PAUSE/RESUME/CANCEL (retract/unretract).
- **Calls**: -
- **Called by**: CANCEL_PRINT, PAUSE, RESUME
- **Variables**: -
- **Uses**: reads printer.configfile, printer.toolhead
- **Commands**: all exist (built-in/module commands used: G1, G90, G91, M118, M83) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD  |  **Tags**: misc  |  **Fluidd**: WM Ultra Filament
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_PAUSE_STATE
- **File / lines**: macros.cfg L167-174 (gcode_macro)
- **What it does**: Remembers that PAUSE already ran for this pause. Running it clears a flag that is left over (WM_PRINT_END_WATCH runs it)
- **Calls**: -
- **Called by**: WM_PRINT_END_WATCH
- **Variables**: active
- **Uses**: reads printer.print_stats; sets variables of _WM_PAUSE_STATE
- **Commands**: all exist (built-in/module commands used: SET_GCODE_VARIABLE) - checked 2026-11-18
- **Risk**: none  |  **Tags**: print  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_LOG_STATE
- **File / lines**: macros.cfg (gcode_macro, new 2.23.0, before PAUSE)
- **What it does**: Support log: writes one console line `WMLOG <WHAT> T<tool> gcode X Y Z head X Y Z offset X Y Z homed .. nozzle t/target bed t/target speed % state ..`; the log digest copies it into wm-events.log as a STATE line.
- **Calls**: RESPOND
- **Called by**: PAUSE, RESUME, CANCEL_PRINT
- **Variables**: -
- **Uses**: reads printer.save_variables, printer.gcode_move, printer.toolhead, printer.extruder / extruderN, printer.heater_bed (guarded), printer.print_stats
- **Commands**: all exist (RESPOND) - checked 2026-11-21 on the pi400 devbox
- **Risk**: none (reads only)  |  **Tags**: misc  |  **Fluidd**: hidden (leading underscore)
- **Tested**: pi400 devbox 2026-11-21: pause, resume and cancel each wrote their lines with the right numbers
### PAUSE
- **File / lines**: macros.cfg L175-260 (gcode_macro) - renames the original to BASE_PAUSE
- **What it does**: Pause: keeps tool map and temperatures, retracts, raises Z and parks, turns heaters down after the idle timer.
- **Calls**: E_axis_move, M104, M106
- **Called by**: WM_FAN_GUARD, _CHECK_CHANGE_TOOL, delayed_pause0, delayed_pause1, delayed_pause2, delayed_pause3
- **Variables**: -
- **Uses**: reads printer.configfile, printer.extruder, printer.extruder1, printer.extruder2, printer.extruder3, printer.gcode_move, printer.print_stats, printer.save_variables, printer.toolhead; sets variables of RESUME, _WM_PAUSE_STATE; saves box_modify_t0 VALUE, box_modify_t1 VALUE, box_modify_t2 VALUE, box_modify_t3 VALUE, box_modify_t{i}_backup VALUE
- **Commands**: all exist (built-in/module commands used: G1, G90, G91, M25, RESPOND, SAVE_GCODE_STATE, SAVE_VARIABLE, SET_GCODE_VARIABLE, SET_IDLE_TIMEOUT, SET_STEPPER_ENABLE) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, HEATS  |  **Tags**: print  |  **Fluidd**: WM Ultra Print
- **Tested**: F-011 guards confirmed in a real print 2026-11-15
- **Change log**: 2.23.0 (2026-11-21): calls _WM_LOG_STATE at PAUSE_START (after the state is saved) and PAUSE_PARKED (end); behaviour unchanged.
### RESUME
- **File / lines**: macros.cfg L261-363 (gcode_macro) - renames the original to BASE_RESUME
- **What it does**: Resume: heats the tool at the wipe position (F-150), wipes, restores position, offsets and feed assist, continues the print.
- **Calls**: ACE_WM_ASSIST, E_axis_move, M104, M106, M109, M190, WIPE_NOZZLE, _WM_GO_WIPE, _WM_Z_TRIM_APPLY
- **Called by**: _WM_ENDLESS_3
- **Variables**: resume_temperature0, resume_temperature1, resume_temperature2, resume_temperature3, resume_bed, zhop, etemp, fan, afan, airfan
- **Uses**: reads printer.configfile, printer.print_stats, printer.save_variables; sets variables of _WM_ACE, _WM_PAUSE_STATE; saves box_modify_t0 VALUE, box_modify_t1 VALUE, box_modify_t2 VALUE, box_modify_t3 VALUE
- **Commands**: all exist (built-in/module commands used: G0, G90, M118, M24, M400, RESPOND, RESTORE_GCODE_STATE, SAVE_VARIABLE, SET_GCODE_VARIABLE, SET_IDLE_TIMEOUT) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, HEATS, ACE  |  **Tags**: print  |  **Fluidd**: WM Ultra Print
- **Tested**: F-011 confirmed 2026-11-15; F-150 heat-at-wipe NOT tested (pushed 2.21.0)
- **Change log**: 2.23.0 (2026-11-21): calls _WM_LOG_STATE at RESUME_START and RESUME_DONE (just before M24); behaviour unchanged.
### CANCEL_PRINT
- **File / lines**: macros.cfg L364-420 (gcode_macro) - renames the original to BASE_CANCEL_PRINT
- **What it does**: Cancel: heaters off, fan off, retract, wipe, park head, clear mesh, reset flow.
- **Calls**: E_axis_move, M107, PARK_CURRENT_TOOL, RESET_FLOW_EXTRUDER, WIPE_NOZZLE
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: runout_detected
- **Uses**: reads printer.configfile, printer.gcode_move, printer.save_variables, printer.toolhead; sets variables of START_PRINT; saves box_modify_t0 VALUE, box_modify_t1 VALUE, box_modify_t2 VALUE, box_modify_t3 VALUE, box_modify_t{i}_backup VALUE
- **Commands**: all exist (built-in/module commands used: BED_MESH_CLEAR, G1, G90, G92, M220, M400, M84, RESPOND, SAVE_VARIABLE, SDCARD_RESET_FILE, SET_GCODE_VARIABLE, SET_IDLE_TIMEOUT, SET_VELOCITY_LIMIT, TURN_OFF_HEATERS) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD (+ through the macros it calls: ACE, HEATS)  |  **Tags**: print  |  **Fluidd**: WM Ultra Print
- **Tested**: no per-macro record in FIX-LOG.md
- **Change log**: 2.23.0 (2026-11-21): calls _WM_LOG_STATE at CANCEL_START and CANCEL_DONE; behaviour unchanged.
### PROBE_CALIBRATE
- **File / lines**: macros.cfg L421-434 (gcode_macro) - renames the original to PROBE_CALIBRATE_BASE
- **What it does**: Z offset calibration, please enable bed preheating first
- **Calls**: -
- **Called by**: WM_PROBE_CALIBRATE
- **Variables**: -
- **Uses**: reads printer.toolhead
- **Commands**: all exist (built-in/module commands used: BED_MESH_CLEAR, G1, G28, G90, PROBE_CALIBRATE_BASE) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD  |  **Tags**: calibration  |  **Fluidd**: WM Factory Calibration
- **Tested**: no per-macro record in FIX-LOG.md
### G29
- **File / lines**: macros.cfg L435-475 (gcode_macro)
- **What it does**: Bed leveling (bed mesh) with tool pick-up, heating at the wipe position (F-150), wipe, then BED_MESH_CALIBRATE.
- **Calls**: BED_MESH_CALIBRATE, M104, M109, M190, T0, WIPE_NOZZLE, _WM_GO_WIPE
- **Called by**: WM_BED_LEVELING
- **Variables**: bed_leveling
- **Uses**: reads printer.configfile, printer.save_variables, printer.toolhead; sets variables of G29
- **Commands**: all exist (built-in/module commands used: G1, G28, M118, M140, M400, SET_GCODE_VARIABLE) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, HEATS (+ through the macros it calls: ACE)  |  **Tags**: misc  |  **Fluidd**: WM Factory Calibration
- **Tested**: no per-macro record in FIX-LOG.md
### G30
- **File / lines**: macros.cfg L476-479 (gcode_macro)
- **What it does**: Empty placeholder (no function).
- **Calls**: -
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: sets variables of START_PRINT
- **Commands**: all exist (built-in/module commands used: SET_GCODE_VARIABLE) - checked 2026-11-18
- **Risk**: none  |  **Tags**: misc  |  **Fluidd**: WM Ultra Print
- **Tested**: no per-macro record in FIX-LOG.md
### G31
- **File / lines**: macros.cfg L480-484 (gcode_macro)
- **What it does**: Empty placeholder (no function).
- **Calls**: -
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: sets variables of START_PRINT
- **Commands**: all exist (built-in/module commands used: SET_GCODE_VARIABLE) - checked 2026-11-18
- **Risk**: none  |  **Tags**: misc  |  **Fluidd**: WM Ultra Print
- **Tested**: no per-macro record in FIX-LOG.md
### BED_MESH_CALIBRATE
- **File / lines**: macros.cfg L485-507 (gcode_macro) - renames the original to BED_MESH_CALIBRATE_BASE
- **What it does**: Wraps the real BED_MESH_CALIBRATE: homes first, moves clear, honours the adaptive parameters.
- **Calls**: -
- **Called by**: G29, START_PRINT
- **Variables**: -
- **Uses**: reads printer.configfile, printer.toolhead
- **Commands**: all exist (built-in/module commands used: BED_MESH_CALIBRATE_BASE, G1, G28, G90) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD  |  **Tags**: bed, calibration  |  **Fluidd**: WM Factory Calibration
- **Tested**: no per-macro record in FIX-LOG.md
### M109
- **File / lines**: macros.cfg L508-545 (gcode_macro) - renames the original to M99109
- **What it does**: Wait for the tool temperature; maps slicer tool T to the real head (box_modify) and heats at the wipe position when idle.
- **Calls**: -
- **Called by**: EXTRUDE_FILAMENT, G29, LOAD_FILAMENT, NOZZLE_CALIBRATE_TOOL_OFFSET, NOZZLE_PREPARE, POP, RESUME, START_PRINT, UNLOAD_FILAMENT, WM_SCREWS_CAL, _WM_HEAD_LOAD, _WM_NOZZLE_PREPARE, filament_insert_gcode
- **Variables**: -
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: none) - checked 2026-11-18
- **Risk**: none  |  **Tags**: misc  |  **Fluidd**: none
- **Tested**: no per-macro record in FIX-LOG.md
### M104
- **File / lines**: macros.cfg L546-576 (gcode_macro) - renames the original to M99104
- **What it does**: Set the tool temperature with tool remapping (box_modify).
- **Change log**: 2.23.1 (2026-11-21): B-081, while a print runs a standby temperature (1 to 169 C, below the target) for a head that more than one slicer tool maps to (box_modify) is skipped with a message, so a tool change to that head does not wait for a cooldown and a reheat. Everything else unchanged.
- **Calls**: -
- **Called by**: G29, LOAD_FILAMENT, M191, NOZZLE_CALIBRATE_TOOL_OFFSET, NOZZLE_PREPARE, PAUSE, POP, RAPID_MODE, RESUME, START_PRINT, UNLOAD_FILAMENT, WM_SCREWS_CAL, _WM_HEAD_LOAD, _WM_NOZZLE_PREPARE
- **Variables**: -
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: none) - checked 2026-11-18
- **Risk**: none  |  **Tags**: misc  |  **Fluidd**: none
- **Tested**: no per-macro record in FIX-LOG.md
### M190
- **File / lines**: macros.cfg L577-587 (gcode_macro) - renames the original to M99190
- **What it does**: Wait for the bed temperature (wraps the original).
- **Calls**: -
- **Called by**: G29, RESUME, START_PRINT, WM_NOZZLE_GROWTH_CAL, WM_OFFSETS_Z_HOT, WM_PROBE_CALIBRATE, WM_SCREWS_CAL
- **Variables**: -
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: none) - checked 2026-11-18
- **Risk**: none  |  **Tags**: misc  |  **Fluidd**: none
- **Tested**: no per-macro record in FIX-LOG.md
### M106
- **File / lines**: macros.cfg L588-602 (gcode_macro) - renames the original to M99106
- **What it does**: Part cooling fan speed (wraps the original).
- **Calls**: -
- **Called by**: EXTRUDE_FILAMENT, M107, M191, NOZZLE_PREPARE, PAUSE, POP, RESUME, WM_NOZZLE_FULL_PID, WM_NOZZLE_GROWTH_CAL, WM_OFFSETS_RAPID, WM_OFFSETS_Z_HOT, _WM_CAL_STOP, _WM_FIRST_RUN_CAL, _WM_NOZZLE_PREPARE, _WM_OFFSET_CHECK, _WM_PID_HEAD, _WM_Z_TOUCH
- **Variables**: -
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: none) - checked 2026-11-18
- **Risk**: none  |  **Tags**: misc  |  **Fluidd**: none
- **Tested**: no per-macro record in FIX-LOG.md
### M107
- **File / lines**: macros.cfg L603-609 (gcode_macro) - renames the original to M1077
- **What it does**: Part cooling fan off (calls M106 S0).
- **Calls**: M106
- **Called by**: CANCEL_PRINT, PRINT_END
- **Variables**: -
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: none) - checked 2026-11-18
- **Risk**: none  |  **Tags**: misc  |  **Fluidd**: none
- **Tested**: no per-macro record in FIX-LOG.md
### M141
- **File / lines**: macros.cfg L610-615 (gcode_macro)
- **What it does**: Chamber heater target (SET_HEATER_TEMPERATURE chamber).
- **Calls**: -
- **Called by**: ZR_CHAMBER
- **Variables**: -
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: SET_HEATER_TEMPERATURE) - checked 2026-11-18
- **Risk**: HEATS  |  **Tags**: misc  |  **Fluidd**: none
- **Tested**: no per-macro record in FIX-LOG.md
### M191
- **File / lines**: macros.cfg L616-661 (gcode_macro)
- **What it does**: Wait for the chamber temperature; circulates air with the fans and heats the bed and nozzle meanwhile.
- **Calls**: M104, M106
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: max_chamber, part_fan_speed, aux_fan_speed, extruder_preheat_temp, bed_assist_temp
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: M117, M140, SET_FAN_SPEED, SET_HEATER_TEMPERATURE, TEMPERATURE_WAIT) - checked 2026-11-18
- **Risk**: HEATS, ACE  |  **Tags**: misc  |  **Fluidd**: none
- **Tested**: no per-macro record in FIX-LOG.md
### _RGB_LOAD
- **File / lines**: macros.cfg L662-676 (gcode_macro)
- **What it does**: Tool LED colour while loading.
- **Calls**: -
- **Called by**: WM_TOOL_LEDS
- **Variables**: -
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: SET_LED) - checked 2026-11-18
- **Risk**: none  |  **Tags**: light, load  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _RGB_UNLOAD
- **File / lines**: macros.cfg L677-691 (gcode_macro)
- **What it does**: Tool LED colour while unloading.
- **Calls**: -
- **Called by**: WM_TOOL_LEDS
- **Variables**: -
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: SET_LED) - checked 2026-11-18
- **Risk**: none  |  **Tags**: light, load, unload  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _RGB_CURRENT
- **File / lines**: macros.cfg L692-706 (gcode_macro)
- **What it does**: Tool LED colour of the head on the carriage.
- **Calls**: -
- **Called by**: WM_TOOL_LEDS
- **Variables**: -
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: SET_LED) - checked 2026-11-18
- **Risk**: none  |  **Tags**: light  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### EXTRUDE_FILAMENT
- **File / lines**: macros.cfg L707-734 (gcode_macro)
- **What it does**: Manual extrusion (Fluidd/screen): heats the tool, extrudes a length.
- **Calls**: M106, M109, PARK_CURRENT_TOOL, WIPE_NOZZLE, z_rise
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: extrude_length
- **Uses**: reads printer.configfile, printer.toolhead
- **Commands**: all exist (built-in/module commands used: G1, G90, G91, G92, M400, M83, RESPOND) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, HEATS (+ through the macros it calls: ACE)  |  **Tags**: load  |  **Fluidd**: WM Ultra Filament
- **Tested**: no per-macro record in FIX-LOG.md
### RETRACT_FILAMENT
- **File / lines**: macros.cfg L735-751 (gcode_macro)
- **What it does**: Manual retraction (Fluidd/screen).
- **Calls**: z_rise
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: G1, G4, G90, G91, G92, M400, M83, RESPOND) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD  |  **Tags**: load, unload  |  **Fluidd**: WM Ultra Filament
- **Tested**: no per-macro record in FIX-LOG.md
### LOAD_FILAMENT
- **File / lines**: macros.cfg L752-788 (gcode_macro)
- **What it does**: Manual load: picks the head up, heats at the wipe position (F-150), extrudes, wipes.
- **Calls**: M104, M109, PARK_CURRENT_TOOL, WIPE_NOZZLE, _CHANGE_TOOL, _WM_GO_WIPE_HEAT
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: extrude_length
- **Uses**: reads printer.save_variables, printer.toolhead
- **Commands**: all exist (built-in/module commands used: ACTIVATE_EXTRUDER, G1, G28, G90, G91, G92, M400, M83, RESPOND, SET_STEPPER_ENABLE) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, HEATS (+ through the macros it calls: ACE)  |  **Tags**: load  |  **Fluidd**: WM Ultra Filament
- **Tested**: no per-macro record in FIX-LOG.md
### UNLOAD_FILAMENT
- **File / lines**: macros.cfg L789-827 (gcode_macro)
- **What it does**: Manual unload: picks the head up, heats at the wipe position (F-150), retracts, wipes.
- **Calls**: M104, M109, PARK_CURRENT_TOOL, WIPE_NOZZLE, _CHANGE_TOOL, _WM_GO_WIPE_HEAT
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: extrude_length, retract_length
- **Uses**: reads printer.save_variables, printer.toolhead
- **Commands**: all exist (built-in/module commands used: ACTIVATE_EXTRUDER, G1, G28, G90, G91, G92, M400, M83, RESPOND, SET_STEPPER_ENABLE) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, HEATS (+ through the macros it calls: ACE)  |  **Tags**: load, unload  |  **Fluidd**: WM Ultra Filament
- **Tested**: no per-macro record in FIX-LOG.md
### M221
- **File / lines**: macros.cfg L828-835 (gcode_macro) - renames the original to M99221
- **What it does**: Flow percentage (wraps the original, remembers the value).
- **Calls**: -
- **Called by**: RESET_FLOW_EXTRUDER, _CHECK_CHANGE_TOOL, _WAIT_TIMELAPSE_TAKE_FRAME
- **Variables**: -
- **Uses**: saves t{params.T|int}_flow_extruder VALUE
- **Commands**: all exist (built-in/module commands used: M99221, SAVE_VARIABLE) - checked 2026-11-18
- **Risk**: none  |  **Tags**: misc  |  **Fluidd**: none
- **Tested**: no per-macro record in FIX-LOG.md
### RESET_FLOW_EXTRUDER
- **File / lines**: macros.cfg L836-843 (gcode_macro)
- **What it does**: restore the extruder flow percentage setting
- **Calls**: M221
- **Called by**: CANCEL_PRINT, PRINTER_INIT, PRINT_END
- **Variables**: -
- **Uses**: reads printer.save_variables
- **Commands**: all exist (built-in/module commands used: none) - checked 2026-11-18
- **Risk**: none  |  **Tags**: misc  |  **Fluidd**: WM Ultra Filament
- **Tested**: no per-macro record in FIX-LOG.md
### filament_insert_gcode
- **File / lines**: macros.cfg L844-855 (gcode_macro)
- **What it does**: Factory routine run after filament was inserted: heat, extrude, wipe.
- **Calls**: M109, WIPE_NOZZLE, z_rise
- **Called by**: _WM_HEAD_LOAD
- **Variables**: -
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: G1, G92, M400, M83) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, HEATS  |  **Tags**: load  |  **Fluidd**: WM Ultra Filament
- **Tested**: no per-macro record in FIX-LOG.md
### filament_insert
- **File / lines**: macros.cfg L856-862 (gcode_macro)
- **What it does**: Factory routine run when filament is inserted: first short extrusion.
- **Calls**: -
- **Called by**: _WM_HEAD_LOAD
- **Variables**: -
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: G1, G92, M83) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD  |  **Tags**: load  |  **Fluidd**: WM Ultra Filament
- **Tested**: no per-macro record in FIX-LOG.md

## offset_calibrate.cfg
WonderMaker factory tool offset calibration

### RESPOND_T_OFFSET
- **File / lines**: offset_calibrate.cfg L24-34 (gcode_macro)
- **What it does**: Prints the saved XYZ offsets of the tools.
- **Calls**: -
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: reads printer.save_variables
- **Commands**: all exist (built-in/module commands used: none) - checked 2026-11-18
- **Risk**: none  |  **Tags**: calibration  |  **Fluidd**: WM Factory Calibration
- **Tested**: no per-macro record in FIX-LOG.md
### SAVE_T_OFFSET
- **File / lines**: offset_calibrate.cfg L35-75 (gcode_macro)
- **What it does**: Saves measured tool offsets into saved_variables.
- **Calls**: -
- **Called by**: SAVE_TOOL_OFFSET, _WM_OFFSET_CHECK, _WM_ZHOT_RESULT
- **Variables**: -
- **Uses**: reads printer.save_variables; saves t{t}_offset VALUE
- **Commands**: all exist (built-in/module commands used: SAVE_VARIABLE) - checked 2026-11-18
- **Risk**: none  |  **Tags**: calibration  |  **Fluidd**: WM Factory Calibration
- **Tested**: no per-macro record in FIX-LOG.md
### RESPOND_T_POSITION
- **File / lines**: offset_calibrate.cfg L76-87 (gcode_macro)
- **What it does**: Prints the saved dock positions.
- **Calls**: -
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: reads printer.save_variables
- **Commands**: all exist (built-in/module commands used: none) - checked 2026-11-18
- **Risk**: none  |  **Tags**: calibration  |  **Fluidd**: WM Factory Calibration
- **Tested**: no per-macro record in FIX-LOG.md
### _APPLY_PRE_Z_OFFSET
- **File / lines**: offset_calibrate.cfg L88-104 (gcode_macro)
- **What it does**: Applies the pre-measured Z offset of the probe to the next calibration steps.
- **Calls**: -
- **Called by**: CALIBRATE_TOOL_OFFSET, NOZZLE_PREPARE, _WM_NOZZLE_PREPARE
- **Variables**: last_z_result
- **Uses**: reads printer.configfile, printer.probe; sets variables of _APPLY_PRE_Z_OFFSET
- **Commands**: all exist (built-in/module commands used: SET_GCODE_VARIABLE, TOOL_CALIBRATE_Z_OFFSET) - checked 2026-11-18
- **Risk**: none  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### NOZZLE_PREPARE
- **File / lines**: offset_calibrate.cfg L105-163 (gcode_macro)
- **What it does**: Prepares a nozzle for calibration: heats at the wipe position (F-150), homes Z, moves to a safe spot, applies the Z offset.
- **Calls**: M104, M106, M109, SET_GCODE_OFFSET, _APPLY_PRE_Z_OFFSET, _WM_CAL_CLEARANCE, _WM_GO_WIPE
- **Called by**: CALIBRATE_OFFSET_ALL_FINE_MODE
- **Variables**: -
- **Uses**: reads printer.save_variables
- **Commands**: all exist (built-in/module commands used: ACE_DISABLE_FEED_ASSIST, ACE_ENABLE_FEED_ASSIST, G1, G28, G90, G91, G92, M400, PROBE, RESTORE_GCODE_STATE, SAVE_GCODE_STATE, SET_HEATER_TEMPERATURE, TEMPERATURE_WAIT) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, HEATS, ACE  |  **Tags**: calibration  |  **Fluidd**: WM Factory Calibration
- **Tested**: no per-macro record in FIX-LOG.md
### NOZZLE_CALIBRATE_TOOL_OFFSET
- **File / lines**: offset_calibrate.cfg L164-185 (gcode_macro)
- **What it does**: Fine mode: heated nozzle goes to the tool setter and measures.
- **Calls**: M104, M109
- **Called by**: CALIBRATE_OFFSET_ALL_FINE_MODE, WM_OFFSETS_ACCURATE
- **Variables**: -
- **Uses**: reads printer.save_variables
- **Commands**: all exist (built-in/module commands used: G0, G1, M118) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, HEATS  |  **Tags**: calibration, tool-change  |  **Fluidd**: WM Factory Calibration
- **Tested**: no per-macro record in FIX-LOG.md
### RAPID_MODE
- **File / lines**: offset_calibrate.cfg L186-203 (gcode_macro)
- **What it does**: Rapid offset calibration of all tools (cold).
- **Calls**: CALIBRATE_TOOL_OFFSET, CALIBRATE_TOOL_Z_OFFSET, M104, SAVE_TOOL_OFFSET
- **Called by**: CALIBRATE_OFFSET_ALL_FINE_MODE, CALIBRATE_OFFSET_ALL_RAPID_MODE, WM_OFFSETS_ACCURATE, WM_OFFSETS_RAPID
- **Variables**: -
- **Uses**: reads printer.toolhead
- **Commands**: all exist (built-in/module commands used: G1, G28) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, HEATS (+ through the macros it calls: ACE, LOAD CELL / SETTER)  |  **Tags**: calibration  |  **Fluidd**: WM Factory Calibration
- **Tested**: no per-macro record in FIX-LOG.md
### CALIBRATE_TOOL_OFFSET
- **File / lines**: offset_calibrate.cfg L204-253 (gcode_macro)
- **What it does**: Measures the XY offset of one tool with the load cell/tool setter.
- **Calls**: SET_GCODE_OFFSET, T0, _APPLY_PRE_Z_OFFSET, _WM_CAL_CLEARANCE
- **Called by**: RAPID_MODE, _WM_SETTER_TEST
- **Variables**: -
- **Uses**: reads printer.save_variables
- **Commands**: all exist (built-in/module commands used: BED_MESH_CLEAR, COLLISION_DETECT_DISABLE, COLLISION_DETECT_ENABLE, G0, G1, G4, M400, PROBE, SET_COLLISION_THRESHOLD, TOOL_CALIBRATE_TOOL_OFFSET, TOOL_LOCATE_SENSOR) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, LOAD CELL / SETTER (+ through the macros it calls: ACE, HEATS)  |  **Tags**: calibration, tool-change  |  **Fluidd**: WM Factory Calibration
- **Tested**: no per-macro record in FIX-LOG.md
### CALIBRATE_OFFSET_ALL_RAPID_MODE
- **File / lines**: offset_calibrate.cfg L254-262 (gcode_macro)
- **What it does**: Calibrates all tool offsets in rapid mode.
- **Calls**: RAPID_MODE
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: reads printer.save_variables
- **Commands**: all exist (built-in/module commands used: BED_MESH_CLEAR, G28) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD (+ through the macros it calls: ACE, HEATS, LOAD CELL / SETTER)  |  **Tags**: calibration  |  **Fluidd**: WM Factory Calibration
- **Tested**: no per-macro record in FIX-LOG.md
### CALIBRATE_OFFSET_ALL_FINE_MODE
- **File / lines**: offset_calibrate.cfg L263-271 (gcode_macro)
- **What it does**: Calibrates all tool offsets in fine mode (heated).
- **Calls**: NOZZLE_CALIBRATE_TOOL_OFFSET, NOZZLE_PREPARE, RAPID_MODE
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: reads printer.save_variables
- **Commands**: all exist (built-in/module commands used: none) - checked 2026-11-18
- **Risk**: none (+ through the macros it calls: ACE, HEATS, LOAD CELL / SETTER, MOVES THE TOOLHEAD)  |  **Tags**: calibration  |  **Fluidd**: WM Factory Calibration
- **Tested**: no per-macro record in FIX-LOG.md
### CALIBRATE_TOOL_Z_OFFSET
- **File / lines**: offset_calibrate.cfg L272-293 (gcode_macro)
- **What it does**: Measures the Z offset of one tool.
- **Calls**: SET_GCODE_OFFSET, _OFFSET_SET, _SAVE_PROBE_POS, _WM_CAL_CLEARANCE
- **Called by**: RAPID_MODE
- **Variables**: -
- **Uses**: reads printer.save_variables
- **Commands**: all exist (built-in/module commands used: BED_MESH_CLEAR, G1, M400, PROBE) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD (+ through the macros it calls: ACE, HEATS)  |  **Tags**: calibration, tool-change  |  **Fluidd**: WM Factory Calibration
- **Tested**: no per-macro record in FIX-LOG.md
### _SAVE_PROBE_POS
- **File / lines**: offset_calibrate.cfg L294-305 (gcode_macro)
- **What it does**: Saves the probe position values.
- **Calls**: -
- **Called by**: CALIBRATE_TOOL_Z_OFFSET
- **Variables**: -
- **Uses**: reads printer.configfile, printer.probe; sets variables of SAVE_TOOL_OFFSET
- **Commands**: all exist (built-in/module commands used: SET_GCODE_VARIABLE) - checked 2026-11-18
- **Risk**: none  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### SAVE_TOOL_OFFSET
- **File / lines**: offset_calibrate.cfg L306-319 (gcode_macro)
- **What it does**: Saves one tool's measured offset (difference to T0).
- **Calls**: SAVE_T_OFFSET
- **Called by**: RAPID_MODE
- **Variables**: diff, z_pos, z0_pos
- **Uses**: reads printer.tools_calibrate; sets variables of SAVE_TOOL_OFFSET
- **Commands**: all exist (built-in/module commands used: SET_GCODE_VARIABLE) - checked 2026-11-18
- **Risk**: LOAD CELL / SETTER  |  **Tags**: calibration, tool-change  |  **Fluidd**: WM Factory Calibration
- **Tested**: no per-macro record in FIX-LOG.md
### POP
- **File / lines**: offset_calibrate.cfg L320-364 (gcode_macro)
- **What it does**: Frees a clogged/loaded nozzle: heats at the wipe position, extrudes/retracts in pulses with feed assist.
- **Calls**: M104, M106, M109, _WM_GO_WIPE
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: reads printer.save_variables, printer.toolhead
- **Commands**: all exist (built-in/module commands used: ACE_DISABLE_FEED_ASSIST, ACE_ENABLE_FEED_ASSIST, G1, G28, M400, RESTORE_GCODE_STATE, SAVE_GCODE_STATE, SET_HEATER_TEMPERATURE, TEMPERATURE_WAIT) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, HEATS, ACE  |  **Tags**: calibration  |  **Fluidd**: WM Ultra Filament
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_CAL_CLEARANCE
- **File / lines**: offset_calibrate.cfg L365-382 (gcode_macro)
- **What it does**: Raise the head to at least 7 mm above the bed before idle calibration, wipe and tool-change moves. Skipped while printing or when XYZ are not homed.
- **Calls**: -
- **Called by**: CALIBRATE_TOOL_OFFSET, CALIBRATE_TOOL_Z_OFFSET, NOZZLE_PREPARE, WIPE_NOZZLE, WM_OFFSETS_RAPID, _CHANGE_TOOL, _WM_BEDWARP_START, _WM_GO_WIPE, _WM_GO_WIPE_HEAT, _WM_PID_HEAD, _WM_SETTER_GO, _WM_Z_TOUCH
- **Variables**: minimum_z
- **Uses**: reads printer.gcode_move, printer.print_stats, printer.toolhead
- **Commands**: all exist (built-in/module commands used: G1, G90, RESTORE_GCODE_STATE, SAVE_GCODE_STATE) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md

## timelapse.cfg
moonraker-timelapse macros

### GET_TIMELAPSE_SETUP
- **File / lines**: timelapse.cfg L19-48 (gcode_macro)
- **What it does**: Print the Timelapse setup
- **Calls**: -
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: none) - checked 2026-11-18
- **Risk**: none  |  **Tags**: timelapse  |  **Fluidd**: Timelapse
- **Tested**: no per-macro record in FIX-LOG.md
### _SET_TIMELAPSE_SETUP
- **File / lines**: timelapse.cfg L49-231 (gcode_macro)
- **What it does**: Set user parameters for timelapse
- **Calls**: -
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: reads printer.cfg, printer.configfile, printer.kinematics, printer.toolhead; sets variables of TIMELAPSE_TAKE_FRAME
- **Commands**: all exist (built-in/module commands used: SET_GCODE_VARIABLE) - checked 2026-11-18
- **Risk**: none  |  **Tags**: timelapse  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### TIMELAPSE_TAKE_FRAME
- **File / lines**: timelapse.cfg L232-296 (gcode_macro)
- **What it does**: Take Timelapse shoot
- **Calls**: SET_GCODE_OFFSET, _TIMELAPSE_NEW_FRAME
- **Called by**: HYPERLAPSE, _HYPERLAPSE_LOOP
- **Variables**: enable, takingframe, park, extruder, speed, verbose, check_time, restore, macro, is_paused
- **Uses**: reads printer.gcode_move, printer.toolhead; sets variables of TIMELAPSE_TAKE_FRAME
- **Commands**: all exist (built-in/module commands used: G0, G10, G90, M400, M83, SET_GCODE_VARIABLE, UPDATE_DELAYED_GCODE) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD (+ through the macros it calls: ACE, HEATS)  |  **Tags**: timelapse  |  **Fluidd**: Timelapse
- **Tested**: no per-macro record in FIX-LOG.md
### _TIMELAPSE_NEW_FRAME
- **File / lines**: timelapse.cfg L297-303 (gcode_macro)
- **What it does**: action call for timelapse shoot. must be a seperate macro
- **Calls**: HYPERLAPSE
- **Called by**: TEST_STREAM_DELAY, TIMELAPSE_TAKE_FRAME
- **Variables**: -
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: none) - checked 2026-11-18
- **Risk**: none (+ through the macros it calls: ACE, HEATS, MOVES THE TOOLHEAD)  |  **Tags**: timelapse  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WAIT_TIMELAPSE_TAKE_FRAME
- **File / lines**: timelapse.cfg L304-343 (delayed_gcode timer)
- **What it does**: Waits until the frame is taken, then restores position/flow (timelapse plugin).
- **Calls**: M221
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: reads printer.gcode_move, printer.toolhead; sets variables of TIMELAPSE_TAKE_FRAME
- **Commands**: all exist (built-in/module commands used: G0, G11, G91, G92, M220, M82, SET_GCODE_VARIABLE, UPDATE_DELAYED_GCODE) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD  |  **Tags**: timelapse  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### HYPERLAPSE
- **File / lines**: timelapse.cfg L344-366 (gcode_macro)
- **What it does**: Start/Stop a hyperlapse recording
- **Calls**: TIMELAPSE_TAKE_FRAME
- **Called by**: _TIMELAPSE_NEW_FRAME
- **Variables**: cycle, run
- **Uses**: sets variables of HYPERLAPSE
- **Commands**: all exist (built-in/module commands used: SET_GCODE_VARIABLE, UPDATE_DELAYED_GCODE) - checked 2026-11-18
- **Risk**: none (+ through the macros it calls: ACE, HEATS, MOVES THE TOOLHEAD)  |  **Tags**: timelapse  |  **Fluidd**: Timelapse
- **Tested**: no per-macro record in FIX-LOG.md
### _HYPERLAPSE_LOOP
- **File / lines**: timelapse.cfg L367-381 (delayed_gcode timer)
- **What it does**: Loop of the hyperlapse recording.
- **Calls**: TIMELAPSE_TAKE_FRAME
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: UPDATE_DELAYED_GCODE) - checked 2026-11-18
- **Risk**: none (+ through the macros it calls: ACE, HEATS, MOVES THE TOOLHEAD)  |  **Tags**: timelapse  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### TIMELAPSE_RENDER
- **File / lines**: timelapse.cfg L382-392 (gcode_macro)
- **What it does**: Render Timelapse video and wait for the result
- **Calls**: -
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: render, run_identifier
- **Uses**: reads printer.configfile; sets variables of TIMELAPSE_RENDER
- **Commands**: all exist (built-in/module commands used: SET_GCODE_VARIABLE, UPDATE_DELAYED_GCODE) - checked 2026-11-18
- **Risk**: none  |  **Tags**: timelapse  |  **Fluidd**: Timelapse
- **Tested**: no per-macro record in FIX-LOG.md
### _WAIT_TIMELAPSE_RENDER
- **File / lines**: timelapse.cfg L393-411 (delayed_gcode timer)
- **What it does**: Waits for the timelapse render.
- **Calls**: -
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: reads printer.configfile; sets variables of TIMELAPSE_RENDER
- **Commands**: all exist (built-in/module commands used: M117, SET_GCODE_VARIABLE, UPDATE_DELAYED_GCODE) - checked 2026-11-18
- **Risk**: none  |  **Tags**: timelapse  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### TEST_STREAM_DELAY
- **File / lines**: timelapse.cfg L412-428 (gcode_macro)
- **What it does**: Helper macro to find stream and park delay
- **Calls**: _TIMELAPSE_NEW_FRAME
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: reads printer.toolhead
- **Commands**: all exist (built-in/module commands used: G0, G4) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, ACE (+ through the macros it calls: HEATS)  |  **Tags**: misc  |  **Fluidd**: Timelapse
- **Tested**: no per-macro record in FIX-LOG.md

## zr_tools.cfg
ZR tools: tool info/mapping, chamber, load/unload without ACE

### ZR_SET_TOOL_INFO
- **File / lines**: zr_tools.cfg L19-42 (gcode_macro)
- **What it does**: Store filament colour/material/temperature for a toolhead
- **Calls**: -
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: saves zr_t{t}_color VALUE, zr_t{t}_mat VALUE, zr_t{t}_temp VALUE
- **Commands**: all exist (built-in/module commands used: SAVE_VARIABLE) - checked 2026-11-18
- **Risk**: none  |  **Tags**: tool-change  |  **Fluidd**: ZR Tools
- **Tested**: no per-macro record in FIX-LOG.md
### ZR_SET_TOOL_PA
- **File / lines**: zr_tools.cfg L43-55 (gcode_macro)
- **What it does**: Save (and apply) pressure advance for a toolhead
- **Calls**: -
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: saves t{t}_pressure_advance VALUE
- **Commands**: all exist (built-in/module commands used: SAVE_VARIABLE, SET_PRESSURE_ADVANCE) - checked 2026-11-18
- **Risk**: none  |  **Tags**: tool-change  |  **Fluidd**: ZR Tools
- **Tested**: no per-macro record in FIX-LOG.md
### _ZR_APPLY_TOOL_SETTINGS
- **File / lines**: zr_tools.cfg L56-70 (gcode_macro)
- **What it does**: Applies pressure advance and filament settings of the active tool after a tool change.
- **Calls**: -
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: reads printer.save_variables
- **Commands**: all exist (built-in/module commands used: SET_PRESSURE_ADVANCE) - checked 2026-11-18
- **Risk**: none  |  **Tags**: tool-change  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### ZR_MAP_TOOL
- **File / lines**: zr_tools.cfg L71-84 (gcode_macro)
- **What it does**: Map slicer tool T to physical toolhead H
- **Calls**: -
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: reads printer.print_stats; saves box_modify_t{t} VALUE
- **Commands**: all exist (built-in/module commands used: RESPOND, SAVE_VARIABLE) - checked 2026-11-18
- **Risk**: none  |  **Tags**: tool-change  |  **Fluidd**: ZR Tools
- **Tested**: no per-macro record in FIX-LOG.md
### ZR_MAP_RESET
- **File / lines**: zr_tools.cfg L85-98 (gcode_macro)
- **What it does**: Reset tool mapping to 1:1 (T0->0, T1->1, ...)
- **Calls**: -
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: reads printer.print_stats; saves box_modify_t{i} VALUE
- **Commands**: all exist (built-in/module commands used: RESPOND, SAVE_VARIABLE) - checked 2026-11-18
- **Risk**: none  |  **Tags**: misc  |  **Fluidd**: ZR Tools
- **Tested**: no per-macro record in FIX-LOG.md
### ZR_CHAMBER
- **File / lines**: zr_tools.cfg L99-107 (gcode_macro)
- **What it does**: Set chamber temperature (0 = off). ZR_CHAMBER S=50
- **Calls**: M141
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: none) - checked 2026-11-18
- **Risk**: none (+ through the macros it calls: HEATS)  |  **Tags**: misc  |  **Fluidd**: ZR Tools
- **Tested**: no per-macro record in FIX-LOG.md
### ZR_AIR_FILTER
- **File / lines**: zr_tools.cfg L108-127 (gcode_macro)
- **What it does**: Air filter fan on/off. ZR_AIR_FILTER S=1 (needs air_filter=1 in tmt1.ini)
- **Calls**: -
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: SET_FAN_SPEED) - checked 2026-11-18
- **Risk**: ACE  |  **Tags**: misc  |  **Fluidd**: ZR Tools
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_LOAD_SETTINGS
- **File / lines**: zr_tools.cfg L128-150 (gcode_macro)
- **What it does**: Load and unload settings (ZR_LOAD, ZR_RETRACT, ZR_UNLOAD, ACE_WM_UNLOAD)
- **Calls**: -
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: default_temp, min_saved_temp, load_push_mm, load_speed, load_wait_s, tip_push_mm, tip_push_speed, snap_mm, snap_speed, cool_drop, cool_s, reshape_mm, reshape_speed, pull_mm, pull_speed
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: RESPOND) - checked 2026-11-18
- **Risk**: none  |  **Tags**: load  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_LOAD_TEMP
- **File / lines**: zr_tools.cfg L151-159 (gcode_macro)
- **What it does**: Helper: RESPOND the temperature ZR_LOAD / unload uses for toolhead T (saved filament temperature or default)
- **Calls**: -
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: reads printer.save_variables
- **Commands**: all exist (built-in/module commands used: RESPOND) - checked 2026-11-18
- **Risk**: none  |  **Tags**: load  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_GO_WIPE_HEAT
- **File / lines**: zr_tools.cfg L160-177 (gcode_macro)
- **What it does**: Helper: toolhead T (on the carriage) goes to the purge location (_WM_PURGE_LOCATION, X-13 Y60 Z7) while cold, then heats to S and waits (F-164, 2026-11-19, was the wipe area; changed on pi400 only, checked against pi400 files 2026-11-19)
- **Calls**: _WM_CAL_CLEARANCE, z_rise
- **Called by**: LOAD_FILAMENT, UNLOAD_FILAMENT, ZR_LOAD, _WM_ACE_GRAB, _WM_UNLOAD_TIP
- **Variables**: -
- **Uses**: reads printer.save_variables
- **Commands**: all exist (built-in/module commands used: G0, G90, RESPOND, RESTORE_GCODE_STATE, SAVE_GCODE_STATE, SET_HEATER_TEMPERATURE, TEMPERATURE_WAIT) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, HEATS  |  **Tags**: wipe  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_UNLOAD_TIP
- **File / lines**: zr_tools.cfg L178-213 (gcode_macro)
- **What it does**: Unload step: toolhead T (on the carriage) forms the filament tip at the wipe area at S C and pulls it out of the hotend, wipes, heater off
- **Calls**: WIPE_NOZZLE, _WM_GO_WIPE_HEAT
- **Called by**: ZR_RETRACT, _WM_ACE_UNLOAD_RUN
- **Variables**: -
- **Uses**: reads printer.configfile
- **Commands**: all exist (built-in/module commands used: G1, G4, G92, M400, M83, RESPOND, RESTORE_GCODE_STATE, SAVE_GCODE_STATE, SET_HEATER_TEMPERATURE, SET_STEPPER_ENABLE, TEMPERATURE_WAIT) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, HEATS  |  **Tags**: load, unload  |  **Fluidd**: —
- **Tested**: F-106/F-119 tested 2026-11-17
### ZR_LOAD
- **File / lines**: zr_tools.cfg L214-236 (gcode_macro)
- **What it does**: Load toolhead T without the ACE: picks it up and heats it at the wipe area; then insert the filament (the head sensor loads it). Already loaded: short push, wipe, park
- **Calls**: _CHANGE_TOOL, _WM_GO_WIPE_HEAT, _WM_ZR_LOAD_GO
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: waiting
- **Uses**: reads printer.print_stats, printer.save_variables; sets variables of ZR_LOAD
- **Commands**: all exist (built-in/module commands used: RESPOND, SET_GCODE_VARIABLE, UPDATE_DELAYED_GCODE) - checked 2026-11-18
- **Risk**: none (+ through the macros it calls: ACE, HEATS, MOVES THE TOOLHEAD)  |  **Tags**: load  |  **Fluidd**: ZR Tools
- **Tested**: F-106 tested ACE and no-ACE paths 2026-11-17
### _WM_ZR_LOAD_GO
- **File / lines**: zr_tools.cfg L237-269 (gcode_macro)
- **What it does**: The part of ZR_LOAD after the heating (reads the head sensor now)
- **Calls**: PARK_CURRENT_TOOL, SET_GCODE_OFFSET, WIPE_NOZZLE, _WM_PURGE_ASSIST
- **Called by**: ZR_LOAD
- **Variables**: -
- **Uses**: sets variables of ZR_LOAD
- **Commands**: all exist (built-in/module commands used: G1, M400, M83, RESPOND, RESTORE_GCODE_STATE, SAVE_GCODE_STATE, SET_GCODE_VARIABLE, SET_HEATER_TEMPERATURE, SET_STEPPER_ENABLE, UPDATE_DELAYED_GCODE) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, HEATS (+ through the macros it calls: ACE)  |  **Tags**: load  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _wm_zr_load_wait
- **File / lines**: zr_tools.cfg L270-281 (delayed_gcode timer)
- **What it does**: Timer of ZR_LOAD: waits for the head sensor to see filament, then continues.
- **Calls**: -
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: reads printer.print_stats; sets variables of ZR_LOAD
- **Commands**: all exist (built-in/module commands used: RESPOND, SET_GCODE_VARIABLE, SET_HEATER_TEMPERATURE) - checked 2026-11-18
- **Risk**: HEATS  |  **Tags**: load  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### ZR_RETRACT
- **File / lines**: zr_tools.cfg L282-304 (gcode_macro)
- **What it does**: Unload toolhead T without an ACE: pick it up, form the tip at the wipe area at its saved temperature, wipe, park; then pull the filament out
- **Calls**: PARK_CURRENT_TOOL, SET_GCODE_OFFSET, _CHANGE_TOOL, _WM_UNLOAD_TIP
- **Called by**: ZR_UNLOAD, _wm_unload_runner
- **Variables**: -
- **Uses**: reads printer.print_stats, printer.save_variables; sets variables of ZR_LOAD
- **Commands**: all exist (built-in/module commands used: RESPOND, SET_GCODE_VARIABLE, UPDATE_DELAYED_GCODE) - checked 2026-11-18
- **Risk**: none (+ through the macros it calls: ACE, HEATS, MOVES THE TOOLHEAD)  |  **Tags**: unload  |  **Fluidd**: ZR Tools
- **Tested**: no per-macro record in FIX-LOG.md
### ZR_UNLOAD
- **File / lines**: zr_tools.cfg L305-309 (gcode_macro)
- **What it does**: Unload toolhead T without an ACE (the same as ZR_RETRACT): tip at the wipe area at its saved temperature, park; then pull the filament out
- **Calls**: ZR_RETRACT
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: none) - checked 2026-11-18
- **Risk**: none (+ through the macros it calls: ACE, HEATS, MOVES THE TOOLHEAD)  |  **Tags**: load, unload  |  **Fluidd**: ZR Tools
- **Tested**: no per-macro record in FIX-LOG.md

## rpi_ace.cfg
ACE panel: ACE load/unload/dry macros

### _WM_ACE
- **File / lines**: rpi_ace.cfg L15-52 (gcode_macro)
- **What it does**: Settings and run state of the ACE load/unload (distances, speeds, timeouts, mode, queues) - no commands.
- **Calls**: -
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: ace_instance, max_total_mm, hub_to_head_mm, slow_tail_mm, fast_speed, slow_speed, retract_speed, tick_s, fast_timeout_s, slow_timeout_s, auto_synced, mode, tool, ticks, fed, fast_mm, assist, resync, manual, pstate, prev, baselined, hold_slot, hold, unload_hold, hold_ask, quiet_s, retry_max, queue, quiet, waited, retry
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: none) - checked 2026-11-18
- **Risk**: none  |  **Tags**: ace  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_ACE_FINISH
- **File / lines**: rpi_ace.cfg L53-69 (gcode_macro)
- **What it does**: Ends an ACE load/unload: resets mode, sets the hold, opens the 'slot ready' window.
- **Calls**: -
- **Called by**: ACE_WM_STOP, _WM_ACE_FAIL, _wm_ace_tick
- **Variables**: -
- **Uses**: sets variables of _WM_ACE
- **Commands**: all exist (built-in/module commands used: SET_GCODE_VARIABLE) - checked 2026-11-18
- **Risk**: ACE  |  **Tags**: ace  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_ACE_FAIL
- **File / lines**: rpi_ace.cfg L70-84 (gcode_macro)
- **What it does**: ACE load/unload failed: stops feeding/retracting, ends the run, aborts the unload runner.
- **Calls**: _WM_ACE_FINISH, _WM_UNLOAD_ABORT
- **Called by**: _wm_ace_tick
- **Variables**: -
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: ACE_STOP_FEED, ACE_STOP_RETRACT, RESPOND) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, ACE  |  **Tags**: ace  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_ACE_HEAD
- **File / lines**: rpi_ace.cfg L85-125 (gcode_macro)
- **What it does**: Called when the tool head sensor sees filament during an ACE load: measures/saves the tube length and starts the slow feed end.
- **Calls**: -
- **Called by**: _WM_HEAD_LOAD, _wm_ace_tick
- **Variables**: -
- **Uses**: reads printer.save_variables; sets variables of _WM_ACE; saves wm_ace_len_t{t} VALUE
- **Commands**: all exist (built-in/module commands used: ACE_ENABLE_FEED_ASSIST, ACE_STOP_FEED, G4, M400, RESPOND, SAVE_VARIABLE, SET_GCODE_VARIABLE, UPDATE_DELAYED_GCODE) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, ACE  |  **Tags**: ace  |  **Fluidd**: —
- **Tested**: measuring first load tested 2026-11-18 (T0 930, T1 942 mm)
### _WM_ACE_GRAB
- **File / lines**: rpi_ace.cfg L126-151 (gcode_macro)
- **What it does**: Filament reached the head: tool goes to the wipe position (F-150), heats, grabs a few mm of filament.
- **Calls**: _WM_GO_WIPE_HEAT
- **Called by**: _WM_HEAD_LOAD
- **Variables**: grab_mm, grab_speed
- **Uses**: reads printer.save_variables
- **Commands**: all exist (built-in/module commands used: G1, G92, M400, M83, RESPOND, SET_HEATER_TEMPERATURE, TEMPERATURE_WAIT) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, HEATS, ACE  |  **Tags**: ace, load  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_ACE_HEAD_DONE
- **File / lines**: rpi_ace.cfg L152-164 (gcode_macro)
- **What it does**: Last line of insert_gcode: the head's own insert routine is finished, feed assist off.
- **Calls**: -
- **Called by**: _WM_HEAD_LOAD
- **Variables**: -
- **Uses**: reads printer.print_stats
- **Commands**: all exist (built-in/module commands used: ACE_DISABLE_FEED_ASSIST) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, ACE  |  **Tags**: ace  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### SET_GCODE_OFFSET
- **File / lines**: rpi_ace.cfg L165-181 (gcode_macro) - renames the original to _WM_SET_GCODE_OFFSET
- **What it does**: Wrapper: applies the offset with live Z adjust per tool and ACE restore (calls _WM_SET_GCODE_OFFSET).
- **Calls**: _WM_LIVEZ_SGO
- **Called by**: CALIBRATE_TOOL_OFFSET, CALIBRATE_TOOL_Z_OFFSET, NOZZLE_PREPARE, START_PRINT, TIMELAPSE_TAKE_FRAME, ZR_RETRACT, Z_HOMING, _LOCK_TOOL, _OFFSET_SET, _UNLOCK_TOOL, _WM_ACE_HOME, _WM_BEDWARP_START, _WM_NOZZLE_PREPARE, _WM_SETTER_GO, _WM_ZR_LOAD_GO, _WM_Z_TOUCH
- **Variables**: -
- **Uses**: reads printer.toolhead
- **Commands**: all exist (built-in/module commands used: _WM_SET_GCODE_OFFSET) - checked 2026-11-18
- **Risk**: ACE (+ through the macros it calls: HEATS, MOVES THE TOOLHEAD)  |  **Tags**: ace, calibration  |  **Fluidd**: none
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_ACE_HOME
- **File / lines**: rpi_ace.cfg L182-230 (gcode_macro)
- **What it does**: Homes for an ACE load without hitting the bed (picks up the tool, G28, wipe).
- **Calls**: SET_GCODE_OFFSET, WIPE_NOZZLE, _WM_ACE_HOME_Z, z_rise
- **Called by**: ACE_WM_LOAD, ACE_WM_UNLOAD
- **Variables**: wipe_above, max_off_z, max_off_xy, apply_z
- **Uses**: reads printer.print_stats, printer.save_variables, printer.toolhead
- **Commands**: all exist (built-in/module commands used: G28, RESPOND) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, ACE (+ through the macros it calls: HEATS)  |  **Tags**: ace  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_ACE_HOME_Z
- **File / lines**: rpi_ace.cfg L231-251 (gcode_macro)
- **What it does**: Z touch with the tool on the carriage during ACE homing.
- **Calls**: _OFFSET_SET, z_rise
- **Called by**: _WM_ACE_HOME
- **Variables**: -
- **Uses**: reads printer.save_variables; sets variables of _CHANGE_TOOL
- **Commands**: all exist (built-in/module commands used: G1, G28, M400, RESPOND, SET_GCODE_VARIABLE, SET_KINEMATIC_POSITION) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, ACE (+ through the macros it calls: HEATS)  |  **Tags**: ace  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### ACE_WM_LOAD
- **File / lines**: rpi_ace.cfg L252-315 (gcode_macro)
- **What it does**: Feed ACE slot T (0-3) to the tool head sensor, fast first when the tube length is known. WM's own insert routine then takes over.
- **Calls**: _CHANGE_TOOL, _WM_ACE_HOME, _WM_GO_WIPE, z_rise
- **Called by**: _WM_ACE_ASK_YES, _wm_ace_watch
- **Variables**: -
- **Uses**: reads printer.print_stats, printer.save_variables, printer.toolhead; sets variables of _WM_ACE
- **Commands**: all exist (built-in/module commands used: ACE_FEED, M400, RESPOND, SET_GCODE_VARIABLE, UPDATE_DELAYED_GCODE) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, ACE (+ through the macros it calls: HEATS)  |  **Tags**: ace, load  |  **Fluidd**: AcePro
- **Tested**: first-load fast feed tested 2026-11-18 22:55 (T0 870 mm, T1 882 mm); queue T2/T3 NOT tested (cut by Klipper restart)
### ACE_WM_RETRACT
- **File / lines**: rpi_ace.cfg L316-332 (gcode_macro)
- **What it does**: ACE pulls filament T back into the ACE until the tool head sensor is clear and the ACE slot reports ready (run after WM's UNLOAD_FILAMENT).
- **Calls**: -
- **Called by**: _WM_ACE_UNLOAD_RUN
- **Variables**: -
- **Uses**: sets variables of _WM_ACE
- **Commands**: all exist (built-in/module commands used: ACE_RETRACT, SET_GCODE_VARIABLE, UPDATE_DELAYED_GCODE) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, ACE  |  **Tags**: ace, unload  |  **Fluidd**: AcePro
- **Tested**: no per-macro record in FIX-LOG.md
### ACE_WM_UNLOAD
- **File / lines**: rpi_ace.cfg L333-356 (gcode_macro)
- **What it does**: Full unload of tool T with a formed tip. Homes and picks up the tool by itself, then the extruder and the ACE pull together
- **Calls**: _CHANGE_TOOL, _WM_ACE_HOME, _WM_ACE_UNLOAD_RUN, z_rise
- **Called by**: _wm_unload_runner
- **Variables**: -
- **Uses**: reads printer.print_stats, printer.toolhead; sets variables of _WM_ACE
- **Commands**: all exist (built-in/module commands used: ACE_DISABLE_FEED_ASSIST, M400, SET_GCODE_VARIABLE) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, ACE (+ through the macros it calls: HEATS)  |  **Tags**: ace, load, unload  |  **Fluidd**: AcePro
- **Tested**: T0 unload tested 2026-11-18 22:32; queue (F-153) T1 ok, T0 cut at 23:08
### _WM_ACE_UNLOAD_RUN
- **File / lines**: rpi_ace.cfg L357-395 (gcode_macro)
- **What it does**: The pulling part of ACE_WM_UNLOAD (runs after the tool is picked up, use ACE_WM_UNLOAD)
- **Calls**: ACE_WM_RETRACT, _WM_UNLOAD_TIP
- **Called by**: ACE_WM_UNLOAD
- **Variables**: push_mm, snap_mm, snap_speed, pause_s, pull_mm, pull_speed, temp
- **Uses**: reads printer.save_variables, printer.toolhead
- **Commands**: all exist (built-in/module commands used: ACE_DISABLE_FEED_ASSIST, G1, G4, G92, M400, M83, SET_HEATER_TEMPERATURE, SET_STEPPER_ENABLE, TEMPERATURE_WAIT) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, HEATS, ACE  |  **Tags**: ace, load, unload  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### ACE_WM_STOP
- **File / lines**: rpi_ace.cfg L396-410 (gcode_macro)
- **What it does**: Emergency stop of any ACE feed/retract started by these macros.
- **Calls**: WM_UNLOAD_STOP, _WM_ACE_FINISH
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: ACE_STOP_FEED, ACE_STOP_RETRACT, RESPOND) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, ACE  |  **Tags**: ace  |  **Fluidd**: AcePro
- **Tested**: no per-macro record in FIX-LOG.md
### _wm_ace_tick
- **File / lines**: rpi_ace.cfg L411-507 (delayed_gcode timer)
- **What it does**: Every few seconds: watches an ACE load (fast part, slow part, timeouts, tube length) and finishes or fails it.
- **Calls**: PARK_CURRENT_TOOL, _WM_ACE_FAIL, _WM_ACE_FINISH, _WM_ACE_HEAD
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: reads printer.print_stats; sets variables of _WM_ACE
- **Commands**: all exist (built-in/module commands used: ACE_FEED, ACE_STOP_FEED, ACE_STOP_RETRACT, G4, M400, RESPOND, SET_GCODE_VARIABLE, UPDATE_DELAYED_GCODE) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, ACE (+ through the macros it calls: HEATS)  |  **Tags**: ace  |  **Fluidd**: —
- **Tested**: tested with the ACE_WM_LOAD runs of 2026-11-18
### _WM_ACE_ASSIST_SYNC
- **File / lines**: rpi_ace.cfg L508-554 (gcode_macro)
- **What it does**: Feed assist on for the tool on the carriage while printing, off otherwise (ACE_WM_ASSIST by hand wins until a print starts or ends)
- **Calls**: -
- **Called by**: _wm_ace_watch
- **Variables**: -
- **Uses**: reads printer.print_stats, printer.save_variables; sets variables of _WM_ACE
- **Commands**: all exist (built-in/module commands used: ACE_DISABLE_FEED_ASSIST, ACE_ENABLE_FEED_ASSIST, RESPOND, SET_GCODE_VARIABLE) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, ACE  |  **Tags**: ace  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _wm_ace_watch
- **File / lines**: rpi_ace.cfg L555-659 (delayed_gcode timer)
- **What it does**: Watches the ACE slots and the auto-load switch; starts loads by itself.
- **Calls**: ACE_WM_LOAD, _WM_ACE_ASK_LOAD, _WM_ACE_ASSIST_SYNC
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: reads printer.print_stats, printer.save_variables; sets variables of _WM_ACE; saves ace_auto_load VALUE
- **Commands**: all exist (built-in/module commands used: RESPOND, SAVE_VARIABLE, SET_GCODE_VARIABLE, SET_PIN, UPDATE_DELAYED_GCODE) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, ACE (+ through the macros it calls: HEATS)  |  **Tags**: ace  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_ACE_ASK_LOAD
- **File / lines**: rpi_ace.cfg L660-677 (gcode_macro)
- **What it does**: Window after an unload - the slot has filament again, load the tool or not (the auto load watch opens it)
- **Calls**: -
- **Called by**: _wm_ace_watch
- **Variables**: -
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: RESPOND) - checked 2026-11-18
- **Risk**: ACE  |  **Tags**: ace, load  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_ACE_ASK_YES
- **File / lines**: rpi_ace.cfg L678-688 (gcode_macro)
- **What it does**: Button Load of the window after an unload
- **Calls**: ACE_WM_LOAD
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: RESPOND) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, ACE (+ through the macros it calls: HEATS)  |  **Tags**: ace  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_ACE_ASK_NO
- **File / lines**: rpi_ace.cfg L689-695 (gcode_macro)
- **What it does**: Button No of the window after an unload
- **Calls**: -
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: RESPOND) - checked 2026-11-18
- **Risk**: ACE  |  **Tags**: ace  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### ACE_WM_ASSIST
- **File / lines**: rpi_ace.cfg L696-732 (gcode_macro)
- **What it does**: ACE_WM_ASSIST T=0-3 STATE=on|off|toggle - feed assist of one tool by hand. Stays until the next print starts or ends, also while paused
- **Calls**: -
- **Called by**: RESUME
- **Variables**: -
- **Uses**: sets variables of _WM_ACE
- **Commands**: all exist (built-in/module commands used: ACE_DISABLE_FEED_ASSIST, ACE_ENABLE_FEED_ASSIST, RESPOND, SET_GCODE_VARIABLE) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, ACE  |  **Tags**: ace  |  **Fluidd**: AcePro
- **Tested**: no per-macro record in FIX-LOG.md
### ACE_WM_AUTO
- **File / lines**: rpi_ace.cfg L733-739 (gcode_macro)
- **What it does**: ACE_WM_AUTO ENABLE=1|0 - auto load when a spool is inserted
- **Calls**: -
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: RESPOND, SET_PIN) - checked 2026-11-18
- **Risk**: ACE  |  **Tags**: ace  |  **Fluidd**: AcePro
- **Tested**: no per-macro record in FIX-LOG.md
### ACE_WM_DRY_START
- **File / lines**: rpi_ace.cfg L740-745 (gcode_macro)
- **What it does**: Start drying. TEMP (deg C, max 65) and DURATION (same unit as ACE_START_DRYING)
- **Calls**: -
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: ACE_START_DRYING) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, ACE  |  **Tags**: ace  |  **Fluidd**: AcePro
- **Tested**: no per-macro record in FIX-LOG.md
### ACE_WM_DRY_STOP
- **File / lines**: rpi_ace.cfg L746-751 (gcode_macro)
- **What it does**: Stop drying
- **Calls**: -
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: ACE_STOP_DRYING) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, ACE  |  **Tags**: ace  |  **Fluidd**: AcePro
- **Tested**: no per-macro record in FIX-LOG.md

### rpi_ace.cfg - line-by-line reading (all 750 lines read 2026-11-18, checked against Klipper 0.13.0-827-g29d4ec2d6 source and the panel repo's extras/ace/instance.py)
How the file works, in plain words: `_WM_ACE` holds the settings and the state machine. `ACE_WM_LOAD` picks the tool (`_CHANGE_TOOL`), sends it to the wipe position (`_WM_GO_WIPE`), and starts an ACE feed: fast for (saved tube length - 60 mm) when the length is known, otherwise slow for up to 1200 mm (this also measures the tube). The delayed_gcode `_wm_ace_tick` (every 0.3 s) polls the tool head sensor and the ACE slot status; when the sensor trips, `_WM_ACE_HEAD` saves the measured length (`wm_ace_len_t0..3`), stops the feed, turns feed assist on. WM's own insert routine (insert_gcode in extruderN.cfg) then calls `_WM_ACE_GRAB` (heat to 220 at the wipe position, 5 mm push) and `_WM_ACE_HEAD_DONE` (feed assist off unless printing). `ACE_WM_UNLOAD` picks up the tool, forms the tip (`_WM_UNLOAD_TIP`, or the built-in recipe when that macro is absent), then `ACE_WM_RETRACT` pulls back up to 3000 mm until the slot reports ready and the head sensor is clear (or the slot reports empty). `_wm_ace_watch` (every 1 s) restores the ACE_Auto_Load switch, runs `_WM_ACE_ASSIST_SYNC`, queues new spools (slot status becomes ready), loads them one at a time when the ACE has been quiet 5 s, and opens a Load window 5 s after an unload.
- Fields read from the ACE driver (`printer["ace_instance_0"]`): `slots[i].status` (strings preload, shifting, identifying, feeding, unwinding, ready, empty - all exist in extras/ace/config.py and protocol_ace2.py), `feed_assist_slot` (instance.py L2685), `connection_state` (instance.py L2767). All exist - checked 2026-11-18.
- Macros called that live in other files, all found: `_WM_GO_WIPE_HEAT`, `_WM_UNLOAD_TIP`, `_WM_LOAD_SETTINGS` (zr_tools.cfg), `_WM_GO_WIPE`, `_WM_UNLOAD`, `_WM_UNLOAD_ABORT`, `WM_UNLOAD_STOP`, `z_rise` (rpi_base.cfg), `PARK_CURRENT_TOOL`, `_OFFSET_SET`, `_CHANGE_TOOL` (change_macros.cfg, variable `save_position` exists), `WIPE_NOZZLE` (fz-wipe-nozzle.cfg), `_WM_LIVEZ_SGO` (rpi_calibration.cfg). Variables read: `_WM_UNLOAD.active`, `_WM_LOAD_SETTINGS.min_saved_temp`.
- Findings (reported, not fixed):
  1. `_wm_ace_tick` L~468-495 uses `printer["ace_instance_0"]` hard-coded in the two unload_hub branches, while the rest of the file uses `"ace_instance_" ~ w.ace_instance`. Same today (instance 0); wrong if `ace_instance` is ever changed.
  2. `_WM_ACE_HOME_Z` has `SET_KINEMATIC_POSITION Z={7.0 + oz}` with 7.0 and `G1 X150 Y135` hard-coded; `apply_z` is 0, so the line does not run today. The "paper test" that decides it is still open.
  3. `ACE_WM_AUTO` does not save the switch itself; the watcher saves `ace_auto_load` on the next 1 s check (works, but a restart within 1 s loses it).
  4. `ACE_WM_ASSIST` / `ACE_WM_UNLOAD` / `ACE_WM_LOAD` use `action_raise_error` inside the template; this ends the macro with an error (intended).
  5. The watcher calls `ACE_WM_LOAD` from inside a delayed_gcode; the load blocks the G-code queue for the whole tool change. The next watcher tick is set (`UPDATE_DELAYED_GCODE ... DURATION=1`) only after that load macro returns. Not a bug today; keep in mind when changing it.
  6. `_WM_ACE_HEAD_DONE` does not check that an ACE load is running: it turns feed assist off for any tool whose insert finishes while not printing (also a manual WM load without ACE). Probably intended; stated for completeness.
  7. Comment at the top still says "grab push and feed-assist-off ... not yet tested" - the file header is older than F-150.
- Risk marks confirmed after reading: `_WM_ACE_HOME`, `_WM_ACE_HOME_Z` (homing/Z touch, moves), `ACE_WM_LOAD` (tool change, moves, ACE), `_WM_ACE_GRAB` (heats to 220, extruder move), `ACE_WM_UNLOAD` / `_WM_ACE_UNLOAD_RUN` (moves, heats, ACE), `_WM_ACE_HEAD` (ACE, SAVE_VARIABLE), `_wm_ace_tick`, `_wm_ace_watch` (can start a load by itself), `SET_GCODE_OFFSET` wrapper (changes offsets/moves); no load cell use in this file.
- Tested: the ACE load/unload for T0-T3 were run on the printer (see FIX-LOG F-1xx entries); the grab push and feed-assist-off at the end are not yet tested (per the file header). checked against Klipper 0.13.0-827-g29d4ec2d6 source, 2026-11-18.

### rpi_nozzle.cfg - line-by-line reading (all 665 lines read 2026-11-18, checked against Klipper 0.13.0-827-g29d4ec2d6, Fluidd prompt protocol, and the autospeed module source in factory/ultra-s/klipper/klippy/extras/autospeed/main.py)
How the file works, in plain words: three groups of Fluidd windows (RESPOND `action:prompt_*` lines, buttons call the next macro). (1) Nozzle Type: `_WM_NOZZLE_TYPE` -> `_WM_NOZZLE_MATERIAL` -> `_WM_NOZZLE_DIAMETER` -> `_WM_NOZZLE_SURE` -> `_WM_NOZZLE_APPLY`, which does SAVE_VARIABLE nozzle_type<N> and runs `wm_nozzle.py set <t> <d> <type>` (writes nozzle_diameter into printer.cfg, backup first). (2) Nozzle change: `WM_NOZZLE_CHANGE` -> `_WM_NCHANGE_CHECK` (no print, all heaters target 0, hotends under 50 C) -> `_WM_NCHANGE_RUN` (`_UNLOCK_TOOL` of the tool on the carriage) -> `_WM_NCHANGE_AFTER` (sets is_nozzle_setting=1) -> Done = `_WM_NOZZLE_CHANGE_END` (sets it back to 0, looks at the dock sensors); `_WM_NCHANGE_FAILED` puts the switch back. (3) Extruder Setup: `WM_EXTRUDER_SETUP` -> `_WM_MATCH_CHECK` -> `_WM_MATCH_RUN` (G28 if needed, park the tool, is_nozzle_setting=1) -> `_WM_MATCH_STEP N` (T<N>, then `_WM_MATCH_AFTER`, which records the empty dock; the next tool is started through the delayed_gcode `_WM_MATCH_NEXT` after 0.5 s) -> `_WM_MATCH_FINISH` (parks, compares CAN ids, shows result) -> `_WM_MATCH_APPLY` (`wm_canids.py apply`, then FIRMWARE_RESTART) or `_WM_MATCH_STOP`. `_WM_RESTART_KLIPPER` closes the window and sends RESTART. The end of the file is the joined speed test (WM_AUTO_SPEED family, module auto_speed): `WM_AUTO_SPEED` (window), `_WM_AUTO_SPEED_READY` (precheck, homing, T0 when the carriage is empty), `_WM_AUTO_SPEED_RUN` (AUTO_SPEED LEVEL=0), `WM_AUTO_SPEED_VALIDATE`, `_WM_AUTO_SPEED_RESULT`, `_WM_AUTO_SPEED_SAVE` (wm_speed_limits.py writes max_accel / max_velocity into printer.cfg), `_WM_AUTO_SPEED_RESTART`, `_WM_AUTO_SPEED_SHAPER` (WM_VIBRATION_COMP CONFIRM=1, saves wm_as_reopen=1) and the delayed_gcode `_WM_AUTO_SPEED_REOPEN` (12 s after start, reopens the window once).
- Config objects: three `[gcode_shell_command]` (wm_nozzle, wm_canids, wm_speed_limits; module gcode_shell_command.py is one of the 36 added files) and `[auto_speed]` (module auto_speed.py + autospeed package, added files). Scripts under ~/printer_data/wm-tools/: wm_nozzle.py, wm_canids.py, wm_speed_limits.py (not read in this pass).
- Fields read: `printer.auto_speed.{shaper_accel, done, time, rec_accel, rec_velocity, max_accel, max_velocity, shaper_at_test, valid_done, valid_accel, valid_velocity, valid_ok, valid_missed_x, valid_missed_y}` - all produced by autospeed/main.py (`_wm_save_last`, `_wm_save_valid`, `get_status`); `done`, `time` etc. exist only after a result, the file uses `|default(0)` for `done`. `printer.configfile.settings.<section>`, `printer.heaters.available_heaters`, `printer.toolhead.homed_axes`, `printer.save_variables.variables.*`, `printer.print_stats.state`, `printer['filament_switch_sensor docked<N>'].filament_detected` - all standard (Klipper docs Status_Reference.md) - checked 2026-11-18.
- Macros called that live elsewhere, all found: `_WM_FAIL`, `_WM_CAL_PRECHECK`, `_WM_PROMPT_CLOSE`, `WM_VIBRATION_COMP`, `_WM_CAL_STOP`, `WM_NOZZLE_FULL_PID`, `WM_OFFSETS_RAPID`, `WM_OFFSETS_ACCURATE` (rpi_calibration.cfg), `_UNLOCK_TOOL`, `PARK_CURRENT_TOOL` (change_macros.cfg).
- Findings (reported, not fixed):
  1. `_WM_MATCH_STEP` calls `T{n}` and `_WM_AUTO_SPEED_READY` calls `T0`. WM's `T0..T3` macros go through `box_modify_t0..3` (change_macros.cfg L224+), `_CHANGE_TOOL T=<box_modify>`. With a changed print map the matching would pick another tool than the one it believes it asked for and write wrong CAN ids. Today all box_modify values are the identity (0,1,2,3), so no effect now. `rpi_ace.cfg` avoids this by calling `_CHANGE_TOOL` directly (its comment says the same).
  2. `_WM_NCHANGE_CHECK` and `_WM_MATCH_CHECK` define a Jinja `{% macro fail(why) %}` that prints prompt lines and raises the error; works because the whole text is rendered before running. The window is shown only when the render reaches that branch.
  3. `_WM_MATCH_CHECK` calls `_WM_NCHANGE_CHECK` as a G-code line, so the heater check runs AFTER the render checks of `_WM_MATCH_CHECK` (the dock sensors are checked first, the heaters second). No harm, only the order of messages.
  4. `_WM_MATCH_AFTER` reads `printer['filament_switch_sensor docked%d']` without an existence test; `_WM_MATCH_CHECK` guarantees it earlier.
  5. `WM_AUTO_SPEED_VALIDATE`: the guard `_WM_FAIL MSG="{"Speed test: ..."}"` has quotes inside quotes; it renders correctly (Jinja string in braces) and `_WM_FAIL` raises at run time, which stops the lines after it.
  6. `_WM_AUTO_SPEED_REOPEN` runs 12 s after every Klipper start; it acts only when `wm_as_reopen` is 1.
  7. The header comment says the speed-test macros "are at the end of this file"; the section `[auto_speed]` sets test_x_min/max, test_y_min/max, validate_* which are additions to the upstream klipper_auto_speed (commit 6331531) made for this printer - see DIFFERENCES.md.
  8. `_WM_MATCH_APPLY` writes new CAN ids to wm_zru_thr*.cfg then FIRMWARE_RESTART: a restart of the MCUs (not during a print; the macro checks print_stats first).
- Risk marks confirmed after reading: WM_NOZZLE_CHANGE chain (`_UNLOCK_TOOL` moves, unlocks gripper - the tool must be held), WM_EXTRUDER_SETUP chain (G28, tool changes, config write + FIRMWARE_RESTART), WM_AUTO_SPEED / _RUN / VALIDATE (very fast moves, loud, can only be stopped by the emergency stop), `_WM_AUTO_SPEED_SAVE` (writes printer.cfg), `_WM_NOZZLE_APPLY` (writes printer.cfg). No ACE or load cell use in this file.
- Tested: see FIX-LOG.md for the nozzle change, matching and speed-test tests; the merged speed test (WM_AUTO_SPEED after the file join) is NOT tested after the move (open item). checked against Klipper 0.13.0-827-g29d4ec2d6 source, 2026-11-18.

### rpi_base.cfg - line-by-line reading (all 1463 lines read 2026-11-19, checked against Klipper 0.13.0-827-g29d4ec2d6 source on the Pi (gcode.py, probe.py, G-Codes.md))
How the file works, in plain words (it is the Pi's always-on layer, joined from six files): `[wm_virtual_pins]` (module for on/off switches); `WM_SAFETY_START` -> `_WM_SAFETY_CHECK` (8 s after start: puts if_check_extruder_status back to 1, reports an open is_nozzle_setting); `WM_PRINT_END_WATCH` (every 2 s: runs PRINT_END once when the print state is "complete" and START_PRINT.print_body_ready is still True; also runs `_WM_PAUSE_STATE` while it is active); `WM_TOOL_LEDS` (every 2 s, calls `_RGB_CURRENT/_LOAD/_UNLOAD` only when the state of a tool changes, remembered in `_WM_LED_STATE.seen`); head sensor watcher `WM_HEAD_SENSOR_WATCH` (every 2 s: switches head sensors back on when no print/ACE/tool change runs, queues filament pushed in while busy, `_WM_HEAD_MARK` is the first line of each insert_gcode, `_WM_HEAD_LOAD` repeats the factory insert steps: heat to 220, `filament_insert`, `filament_insert_gcode`, park); unload menu `WM_UNLOAD_MENU` -> `_WM_UNLOAD_ASK` -> `_WM_UNLOAD_GO` -> delayed_gcode `_wm_unload_runner` (one tool after the other: `ACE_WM_UNLOAD` with an ACE connected, else `ZR_RETRACT`), `_WM_UNLOAD_END`, `WM_UNLOAD_STOP`, `_WM_UNLOAD_ABORT`, `_WM_UNLOAD_RESET`; the `SET_GCODE_OFFSET` wrapper (same block as in rpi_ace.cfg, identical, merged by Klipper); `_WM_HEAT_AT_WIPE` / `_WM_HEAT_BACK` (during a print a nozzle that still has to heat by more than 5 C waits at the wipe position, then goes back); homing: `z_rise` + `_z_rise_run` (lowers the bed 5 mm before X/Y moves unless a print runs), `[homing_override]`, `Z_HOMING`, `[idle_timeout]` (600 s: during a pause only the nozzles go off, else all heaters and motors off); bed warp: `WM_BED_WARP_MEASURE` -> `_WM_BEDWARP_START` -> `_WM_BEDWARP_ROUND` / `_STORE` / `_REPORT` (5 spots x 4 touches, T0 at 140 C, load cell probe) driven by `_WM_BEDWARP_TICK` (every 5 s), `_WM_BEDWARP_FINISH` (summary, `_WM_BED_SOAK_STORE`), `WM_BED_WARP_STOP`, and the wait itself: `_WM_BED_SOAK_MARK` / `_WM_BED_SOAK` (called by START_PRINT), `WM_BED_SOAK`, `WM_BED_SOAK_MENU`, `WM_BED_SOAK_PIN_WATCH`, `[output_pin Bed_Warp_Stabilisation]`; print start purge (item 32): `_WM_START_PURGE` -> `_WM_START_PURGE_RUN` -> `_WM_WIPE_PURGE` / `_WM_WIPE_PURGE_GO` per used head (last one draws the line `_WM_LINE_PURGE`), helpers `_WM_GO_WIPE`, `_WM_PURGE_HEAT`, `_WM_PURGE_ASSIST` (ACE feed assist during the purge, B-056).
- Timers started by themselves (initial_duration): WM_SAFETY_START 8 s, WM_PRINT_END_WATCH 5 s, WM_TOOL_LEDS 5 s, WM_HEAD_SENSOR_WATCH 12 s, WM_BED_SOAK_PIN_WATCH 9 s, then they re-arm every 2 s. Together they run forever while Klipper is up.
- Klipper commands/params checked in the installed source: `SET_KINEMATIC_POSITION ... SET_HOMED=Z / CLEAR_HOMED=Z` (G-Codes.md L604-625, force_move.py), `printer.probe.last_probe_position` (probe.py L73), `printer.exclude_object.objects` ([exclude_object] is in printer.cfg L353), `[wm_print_info]` (printer.cfg L370), `printer.custom_hall.Raw` ([custom_hall] in change_extruder.cfg). All exist - checked 2026-11-19.
- Macros called that live elsewhere, all found: `_WM_CAL_CLEARANCE` (offset_calibrate.cfg), `ZR_RETRACT` (zr_tools.cfg), `filament_insert`, `filament_insert_gcode`, `_RGB_CURRENT/_LOAD/_UNLOAD`, `_WM_PAUSE_STATE`, `START_PRINT` (variable print_body_ready exists, macros.cfg L10), `PRINT_END` (macros.cfg), `_LEVELING_TRIGGER_S` (load_cell.cfg), `_WM_LIVEZ_HEAT`, `_WM_FAIL`, `_WM_CAL_PRECHECK`, `_WM_PROMPT_CLOSE` (rpi_calibration.cfg), `PARK_CURRENT_TOOL`, `_CHANGE_TOOL`, `_UNLOCK_TOOL` (change_macros.cfg).
- How delayed_gcode timers work here (confirmed from Klipper's delayed_gcode.py logic): a timer's text is rendered when it fires, and `UPDATE_DELAYED_GCODE` of its own ID inside its script only sets the next wake after the script has finished. So a long macro inside a timer (the unload runner, `ACE_WM_LOAD` from the ACE watcher) does not get a second timer run in the middle.
- Findings (reported, not fixed):
  1. (CORRECTED 2026-11-19, earlier version of this line was wrong) `[homing_override]` line `{% if ... %} #XYZ: plain G28, or all three axes named`: NOT a problem. Klipper's config reader (`klippy/configfile.py` L172, Python 3: `inline_comment_prefixes=(';', '#')`) removes everything from a `#` or `;` that follows a space, when the config is loaded, so `#XYZ: ...` never reaches G-code. Checked against configfile.py of the installed Klipper, 2026-11-19.
  2. Hard-coded values: wipe default `[-13.0, 240.0]` in `_WM_HEAT_AT_WIPE`, `_WM_GO_WIPE`, `_WM_PURGE_HEAT` (the saved `wipe_position` wins when present); `G1 Z7.0` in `_WM_PURGE_HEAT`, `G1 Z7` after Z homing; bed warp spots X30-270 Y30-240 and centre X150 Y135; `X150 Y135` in `Z_HOMING`.
  3. `Z_HOMING` and `_WM_BEDWARP_START` use `T0`, which goes through `box_modify_t0` (change_macros.cfg L224); today it is the identity, with a changed print map the Z touch would use another tool (same remark as in rpi_nozzle.cfg).
  4. `_WM_UNLOAD_*` / `_wm_unload_runner`: `ok=1` is set when `ACE_WM_UNLOAD` returns, which is when the retract has only STARTED (the ACE state machine finishes later); the runner then waits until `_WM_ACE.mode` is idle again. Works as designed; a failure inside the ACE state machine reaches the runner through `_WM_ACE_FAIL` -> `_WM_UNLOAD_ABORT`.
  5. `WM_UNLOAD_MENU` `slot.color|sum`: fails if the ACE driver ever reports `color` as None instead of a list (it reports a list today).
  6. `_WM_HEAT_AT_WIPE` saves the G-code state (`SAVE_GCODE_STATE NAME=_wm_heat`) and `_WM_HEAT_BACK` restores it; when a heat is stopped (cancel, error) the saved state stays unused until the next run (harmless, noted in the macro).
  7. The bed warp measurement works at 140 C with the load cell (PROBE) and runs inside a timer for about 20 to 25 min; `WM_BED_WARP_STOP` is the only soft stop.
  8. `_WM_BED_SOAK` waits with `G4` steps rendered at once, so the wait cannot be cancelled except by M112 / CANCEL_PRINT (G4 stays in the queue).
- Risk marks confirmed after reading: `[homing_override]` / `Z_HOMING` / `z_rise` (moves, homing, SET_KINEMATIC_POSITION), `_WM_HEAT_AT_WIPE` (moves during a print, heats), `_WM_HEAD_LOAD` (heats to 220, extruder, tool change, park), `_wm_unload_runner` chain (heats, tool changes, ACE), `WM_BED_WARP_MEASURE` chain (heats bed and nozzle, load cell touches, ~25 min), `_WM_BED_SOAK` (waits), `_WM_START_PURGE` chain (tool changes, heats, extrudes, ACE feed assist), `_WM_LINE_PURGE` (moves, extrudes), `[idle_timeout]` (turns everything off), `WM_PRINT_END_WATCH` (runs PRINT_END by itself).
- Tested: tests are recorded in FIX-LOG.md by item (F-103 join, F-105 purge, B-021/B-031 head sensors, B-040/B-056 ACE assist, bed warp 2026-11-15); the list is in FIX-LOG.md, not repeated here. checked against Klipper 0.13.0-827-g29d4ec2d6 source, 2026-11-19.

### rpi_calibration.cfg - line-by-line reading (all 2978 lines, 97 sections read 2026-11-19, checked against Klipper 0.13.0-827-g29d4ec2d6 on the Pi, offset_calibrate.cfg, macros.cfg, change_extruder.cfg, saved_variables.cfg snapshot)
How the file works, in plain words (two files joined: rpi_calibration.cfg and rpi_zoffset.cfg): Fluidd windows (RESPOND `action:prompt_*`) in front of the factory calibration macros. Helpers: `_WM_CAL_PRECHECK` (no print, `is_nozzle_setting` 0, every heater target 0 unless ALLOW_BED=1), `_WM_FAIL` (raises the error after the window was closed), `_WM_CAL_ASK` (Start/Cancel window per stage), `_WM_CAL_STOP`, `_WM_SAVE`, `_WM_PROMPT_CLOSE`.
- Calibrations: `WM_BED_LEVELING` (G29 + SAVE_CONFIG), `WM_SCREWS_CAL` (bed 55 C, T0 140 C, WIPE_NOZZLE, SCREWS_TILT_CALCULATE), `WM_PROBE_CALIBRATE` (bed warm, the PROBE_CALIBRATE wrapper in macros.cfg L421 homes by itself when needed), `WM_VIBRATION_COMP` (COLLISION_DETECT_DISABLE, SHAPER_CALIBRATE, SAVE_CONFIG), `WM_BED_PID`, `WM_NOZZLE_FULL_PID` (windows for temperature, fan and head, then `_WM_PID_HEAD` per head and `_WM_NOZZLE_FULL_PID_RESULT` reads `printer.configfile.save_config_pending_items`), `WM_OFFSETS_RAPID` (per tool: clean at the wipe area, `RAPID_MODE T=`, `_WM_OFFSET_CHECK` puts the old offsets back with `SAVE_T_OFFSET` when X or Y moved more than 0.2 mm), `WM_OFFSETS_ACCURATE` (`_WM_NOZZLE_PREPARE`, button, `NOZZLE_CALIBRATE_TOOL_OFFSET`, then rapid), `WM_FIRST_RUN_CAL` -> `_WM_FIRST_RUN_CAL` (7 stages: setter position, offsets, hot Z, shaper, bed PID, mesh, nozzle PID) -> `_WM_FIRST_RUN_CAL_DONE` (result window; `done_t` makes it ignore a call queued during the run).
- Z offset part: `_WM_ZHOT` (settings), `WM_OFFSETS_Z_HOT` -> `_WM_Z_TOUCH` / `_WM_Z_TOUCH_STORE` / `_WM_ZHOT_RESULT` (T0, T1..T3, T0 again; saves with SAVE_T_OFFSET only when T0 drift <= 0.02 mm), `WM_NOZZLE_GROWTH_CAL` / `_WM_GROWTH_RESULT`, `WM_NOZZLE_GROWTH`, switch `[output_pin Nozzle_Heat_Growth]` with `_WM_GROWTH_PIN*` and `WM_GROWTH_PIN_WATCH` (every 2 s), `WM_Z_TRIM` + `_WM_Z_TRIM_MIGRATE` (3 s after start) + `_WM_Z_TRIM_APPLY` + menu/window/step/reset macros, `WM_FULL_OFFSET_CAL` + `_WM_ZCAL_WIN` / `_RUN` / `_AFTER_ACCURATE` / `_DONE`, `_WM_WAIT_TEMP` (renders 360 steps of 5 s = at most 30 min, each `_WM_WAIT_TEMP_STEP` reads the temperature when it runs), live Z adjust per tool (F-035): `_WM_LIVEZ`, `_WM_LIVEZ_SGO` (called by the SET_GCODE_OFFSET wrapper), `WM_LIVE_Z_ZERO`, `_WM_LIVEZ_RESET` (top of START_PRINT), `_WM_LIVEZ_HEAT` (called by M104/M109), `WM_LIVE_Z_MENU`, `_WM_LIVEZ_SAVE` / `_DROP`, `_WM_LIVEZ_WATCH` (every 2 s; opens the Save/Do not save window after a print), `Z_OFFSET_APPLY_PROBE` / `Z_OFFSET_APPLY_ENDSTOP` (rename_existing: they no longer change the probe z_offset or the endstop).
- Tool setter position helper (module `[wm_tool_touch]`, command TOOL_CALIBRATE_TOUCH): `WM_SETTER_PROBE_POSITION` -> `_WM_SETTER_GO` / `_MOVE` / `_SENSE` / `_DOWN` / `_WIN` / `_STEP` / `_SAVE` / `_AFTER` / `_AWAY` / `_CLOSE` / `_TEST` / `_RAPID` / `_RESTORE`; Find automatically `_WM_SETTER_FIND` -> `_FIND_TOP` -> `_FIND_SIDES` -> `_FIND_FAR` -> `_FIND_DONE` -> `_FOUND` (or `_FIND_FAIL`, `_WIDE_ASK`, `_WIDE_CANCEL`); Find from scratch `_SCRATCH_GO` -> `_SCRATCH_Y` -> `_SCRATCH_DONE`; block middles `_WM_SETTER_MID` -> `_MID_B/C/D/E` -> `_MID_DONE` -> `_MID_SAVE`; First Run stage 1 `_WM_SETTER_AUTO` (cal=2) + `_AUTO_CHECK` + `_AUTO_FINISH`. All nest: each step calls the next as its last line, so the whole chain runs inside the first call. The saved `probe_position` is a 5-number tuple (x, y, z, x_offset, y_offset), e.g. `(298.19, 286.08, 9.14, 6.37, 6.06)` in saved_variables.cfg; SAVE_VARIABLE with `VALUE=a,b,c,d,e` stores it in that form (checked against the snapshot).
- Fields and objects read: `printer.configfile.save_config_pending_items` (keys `pid_Kp` capital, `printer.configfile.settings.<heater>.pid_kp` lower - both used correctly), `printer.probe.last_probe_position`, `printer.toolhead.axis_minimum/axis_maximum`, `printer.gcode_move.homing_origin`, `printer.wm_tool_touch.touch.<name>.found/x/y/z` (module wm_tool_touch, added file), `printer.exclude_object` not used here. Commands: `SET_VELOCITY_LIMIT`, `RESTORE_GCODE_STATE ... MOVE=1 MOVE_SPEED=`, `SET_COLLISION_THRESHOLD`, `COLLISION_DETECT_ENABLE/DISABLE` (module collision_detect, added file), `TOOL_CALIBRATE_TOUCH` (module wm_tool_touch), `PID_CALIBRATE`, `SHAPER_CALIBRATE`, `SCREWS_TILT_CALCULATE`, `PROBE` - all exist - checked 2026-11-19. Macros found elsewhere: `SAVE_T_OFFSET`, `RAPID_MODE`, `NOZZLE_CALIBRATE_TOOL_OFFSET`, `CALIBRATE_TOOL_OFFSET`, `_APPLY_PRE_Z_OFFSET`, `_WM_CAL_CLEARANCE` (offset_calibrate.cfg), `_OFFSET_SET`, `_CHANGE_TOOL`, `PARK_CURRENT_TOOL` (change_macros.cfg), `WIPE_NOZZLE` (fz-wipe-nozzle.cfg), `_WM_RESTART_KLIPPER` (rpi_nozzle.cfg), `WM_OFFSETS_Z_HOT`, `_WM_ZCAL_AFTER_ACCURATE` (same file).
- Findings (reported, not fixed):
  1. `T{t}` / `T0` go through `box_modify_tN` (change_macros.cfg L224): used by `WM_OFFSETS_RAPID` (`T{t}`), `_WM_NOZZLE_PREPARE` (`T{T}`), `_WM_PID_HEAD` (`T{t}`), `WM_SCREWS_CAL` and `_WM_SETTER_GO` (`T0`), `_WM_AUTO_SPEED_READY`, `Z_HOMING`. With the print map changed they would pick another tool than the macro believes. `WM_OFFSETS_Z_HOT` and `WM_NOZZLE_GROWTH_CAL` use `_CHANGE_TOOL T=` directly (correct). The map is the identity today (saved_variables.cfg L8-15).
  2. The collision threshold: `SET_COLLISION_THRESHOLD THRESHOLD=12.0 WINDOW=2 ACTION=shutdown` is set (6 places in this file, same as offset_calibrate.cfg L240) and not put back to the configured 25 / pause (change_extruder.cfg L60-68). `COLLISION_DETECT_ENABLE` is called only in offset_calibrate.cfg L241 and in these setter helpers, and the helpers switch it off again; the 12/shutdown threshold stays set until Klipper restarts. No effect while detection is off; it would matter only if something else switches detection on.
  3. `SET_VELOCITY_LIMIT ACCEL=14` (touch_accel) is set before the touches in `_WM_SETTER_SENSE`, `_FIND_TOP`, `_MID_B`, `_MID_D` and put back to `max_accel` afterwards; if TOOL_CALIBRATE_TOUCH raises a real error (not just "not found", which OPTIONAL=1 allows) in between, acceleration stays at 14 until the next SET_VELOCITY_LIMIT or a restart. `_WM_SETTER_FIND_FAIL` restores it when it is reached.
  4. `_WM_Z_TRIM_APPLY` calls `_OFFSET_SET` (which moves Z when the offsets change) without a print-state check, so a Z trim button pressed during a print moves the nozzle at once (looks intended: live adjust).
  5. Hard-coded: `G1 X150.0 Y1` and Z80 in `_WM_NOZZLE_PREPARE`; `Y250` in `_WM_SETTER_AWAY`; `X150 Y135` in several; default wipe `[-13.0, 240.0]` in `WM_OFFSETS_RAPID`, `_WM_PID_HEAD`, `_WM_Z_TOUCH`; the 220 / 140 / 100 C values in the offset macros; the NOZZLE_CALIBRATE_TOOL_OFFSET hard-coded X-13 Y240 open item belongs to the factory side (offset_calibrate.cfg).
  6. `_WM_WAIT_TEMP` queues 360 lines per wait; after 30 minutes it falls through to `TEMPERATURE_WAIT` without a limit (blocks until the temperature is reached).
  7. Typos in the file: none found that change behaviour. One cosmetic: in `WM_FIRST_RUN_CAL` the help text says tools are measured "rapid"; in `_WM_FIRST_RUN_CAL` it runs `WM_OFFSETS_RAPID ... XYLIMIT=3` (limit 3 mm, not the default 0.2) so a new install is not stopped.
  8. `WM_PROBE_CALIBRATE` has no homing of its own; the PROBE_CALIBRATE wrapper (macros.cfg L421-431) does `G28` when not homed, otherwise `G1 Z5`. OK.
  9. `WM_VIBRATION_COMP` switches collision detection off and never switches it on (nothing in the printer switches it on outside the offset calibration), so with SAVE=0 it stays off until restart - same state as normal operation.
- Risk marks confirmed after reading (moves, heats, load cell, ACE): `WM_BED_LEVELING`, `WM_SCREWS_CAL`, `WM_PROBE_CALIBRATE`, `WM_OFFSETS_RAPID`, `WM_OFFSETS_ACCURATE`, `_WM_NOZZLE_PREPARE` (extrudes 120 mm, ACE feed assist), `WM_VIBRATION_COMP` (shakes), `WM_NOZZLE_FULL_PID`, `WM_BED_PID`, `WM_FIRST_RUN_CAL` chain (70 to 95 min, everything), `WM_OFFSETS_Z_HOT`, `WM_NOZZLE_GROWTH_CAL` (250 C, retracts and re-feeds filament), `_WM_Z_TOUCH`, the whole tool setter family (touches with a hot or cold nozzle; collision detection with action shutdown), `_WM_Z_TRIM_APPLY` / `_WM_LIVEZ_*` (Z moves), `_WM_SAVE` / `WM_BED_LEVELING` / `WM_BED_PID` / `WM_VIBRATION_COMP` (SAVE_CONFIG restarts Klipper), `_WM_SETTER_SAVE` / `_MID_SAVE` / `_RESTORE` (write saved_variables.cfg).
- Tested: see FIX-LOG.md by item (First Run Calibration real test still open; tool setter helper F-09x/B-065 tested 2026-11-17; hot Z, growth, trim, live Z F-035 tested earlier). checked against Klipper 0.13.0-827-g29d4ec2d6 source, 2026-11-19.

### ACE driver (panel repo `extras/ace/*.py`, 25 files, 19,079 lines, plus `extras/temperature_ace.py` 214 and `extras/virtual_pins.py` 246) - read line by line (2026-11-19)
Checked against the driver source of panel 1.16.3 (repo copy), the Pi snapshot `rpi_ace_driver.cfg` and `_gcode_help.json` of 2026-11-18, 2026-11-19. Every file was read from the first to the last line: manager.py 5215, instance.py 2970, commands.py 2796, serial_manager.py 1725, runout_monitor.py 1080, protocol_ace2.py 855, config.py 710, protocol.py 453, endless_spool.py 436, ace2_ota.py 427, moonraker_lane_sync.py 413, intake_gated.py 330, persistent_state.py 266, protocol_ace1.py 247, setup_tools.py 203, ace2_bus.py 189, tool_map.py 183, print_tools.py 101, __init__.py 100, version.py 93, connection_pause.py 68, tool_base.py 62, monitor_events.py 55, rollback_assist.py 54, idle_assist.py 48. Correction: the earlier heading said "19,539 lines"; 460 of those lines are the two files in `extras/` outside the `ace/` folder.
**How the Pi uses the driver**: `[ace]` with `register_tool_commands: False`, no toolhead sensor named, `ace_count: 1`, `protocol: auto`, `baud: auto`. So the printer's own macros own `T0..T3` (the driver does not register them; this replaces the earlier note that both own them), and the driver acts as feeder and dryer controller only. Its own tool-change path (`ACE_CHANGE_TOOL`, endless spool swap, runout handling) is never reached by your macros.
**Commands actually sent by this setup** (counted in the Pi config files and in the patched Fluidd source): `ACE_ENABLE_FEED_ASSIST`, `ACE_DISABLE_FEED_ASSIST`, `ACE_FEED`, `ACE_RETRACT`, `ACE_STOP_FEED`, `ACE_STOP_RETRACT`, `ACE_START_DRYING`, `ACE_STOP_DRYING` (all registered in commands.py), plus our own `ACE_WM_*` macros. Correction: the earlier list also named `ACE_SET_SLOT`, `ACE_SMART_LOAD`, `ACE_SMART_UNLOAD`, `ACE_CHANGE_TOOL`, `ACE_GET_STATUS`, `ACE_RECONNECT` as called by macros and Fluidd; none of the config files or the Fluidd source sends them. They exist in the driver and work when typed by hand.
**Fields read by the macros and Fluidd** (all exist): `ace_instance_N` printer objects (`__init__.py` L91-97 registers them; the old header comment still says "ace", "ace 1" and is out of date), `.slots[i].status`, `.feed_assist_slot` (instance.py L2685), `.connection_state` (instance.py L2767; values disabled, initializing, connecting, connected, reconnecting), `.dryer_status`, `.temp`, `.humidity`, `.model`, `.firmware`.
**What runs on the Pi and what does not**
- ACE-1 (active) `extras/temperature_ace.py`: the sensor `acepro_temp_1` has `max_temp: 70` in rpi_ace_driver.cfg. When the ACE reports more than 70 C, or between 0 and `min_temp`, the module calls `printer.invoke_shutdown`: the **whole printer shuts down** (FIRMWARE_RESTART needed), also during a print. The Pi limits the dryer to 65 C (`max_dryer_temperature`), so the margin is 5 C; a wrong reading from the ACE has the same effect. Not changed; risk noted.
- ACE-2 (active) `moonraker_lane_sync.py`: a background thread writes `lane1..lane4` into the Moonraker database namespace `lane_data` through `http://127.0.0.1:7125` (2 s timeout), skips while printing or paused and retries afterwards, deletes `lane*` keys that are no longer in the payload. If Moonraker is down it prints one console line. The calls to `gcode.respond_info` at L189 and L210 are made from that worker thread, not from Klipper's main thread; this happens only on the error paths and I did not check Klipper's source for thread safety (could not verify). Matches MOONRAKER.md (namespace `lane_data`).
- ACE-3 (active) `persistent_state.py`: the driver shares `saved_variables.cfg` with our macros. Default mode `deferred`: `set()` and `set_and_save()` change only RAM and mark the key dirty; the file is written at `flush()` (print end, disconnect, `ACE_FLUSH`). A power cut before a flush loses those changes (the file header says so). `flush_direct` writes all variables with `repr()`, which Klipper reads back with `literal_eval`, so our keys survive. `ACE_CLEANUP_STALE_VARS` and the start-up clean-up touch only `ace2_bus_bindings_*` and `ace_inventory_N` with N >= `ace_count`; your `ace_auto_load`, `ace_global_enabled`, `ace_feed_assist_index_0` and `box_modify_*` keys do not match. A string value that contains a double quote would break `SAVE_VARIABLE` in `_write_to_disk` (not seen in the Pi file).
- ACE-4 (active) `serial_manager.py`: 1 Hz status polling through a high-priority queue, 4 requests in flight, 5 s request timeout, writes through `select` without waiting (so a stuck port cannot stall the reactor during a homing move), a port that takes no data for 2 s is reconnected; communication is declared unhealthy at 15 timeouts AND 15 unsolicited messages inside 30 s; "unstable" means 4 reconnects in 180 s. Request ids run 1..65535. Duplicate replies are dropped with a warning about two units on one device id.
- ACE-5 (idle) `idle_assist.py`: on `idle_timeout:idle` it stops feed assist of the tool in `ace_current_index`. On your printer that index stays -1 (the driver never sees a tool change), `get_ace_instance_and_slot_for_tool(-1)` returns `(None, -1)` (config.py L409-431), so the hook does nothing and does not touch the assist your macros set. Verified in the code.
- ACE-6 (idle) `runout_monitor.py`: with `ace_current_index == -1` the loop returns early (L358-362) every 0.1 s, so runout, tangle and "resume without filament" logic never runs. The tangle detector would also need `[output_pin TANGLE_DETECTION]` or the config flag; neither is set on the Pi.
- ACE-7 (idle) `connection_pause.py` and `monitor_events.py`: queue `_ACE_CONNECTION_PAUSE` / `_ACE_MONITOR_EVENT` so that `PAUSE` runs after the running command (our `PAUSE` macro would be called). They are reached only from the runout monitor and the manager's connection check, and only for a loaded driver tool.
- ACE-8 (not used) `endless_spool.py`, `tool_map.py`, `intake_gated.py`, `rollback_assist.py`, `ace2_ota.py`, `ace2_bus.py`, `print_tools.py`, `tool_base.py`, `setup_tools.py`: read; the printer has its own endless spool (rpi_endless.cfg) and its own tool map (`box_modify_tN`, `wm_map_file`); the driver's `ACE_SET_TOOL_MAP` (key `ace_tool_map`) is a separate mechanism that only affects the driver's `T<n>`, which is not registered here. The Fluidd patch does not send it.
**Wrong, missing or risky when the driver is used the other way (nothing here changed)**
1. The driver's prompts and tool-change path call `_ACE_STATE`, `_ACE_PRE_TOOLCHANGE`, `_ACE_POST_TOOLCHANGE`, `_ACE_PREPARE_FOR_RETRACTION`, `_ACE_ROUTE_TOOL`, `_EXTRUDE` and `_RETRACT`. None of them exists on the Pi (no hit in `_gcode_help.json`, no `gcode_macro` section). Typing `ACE_CHANGE_TOOL TOOL=n` would fail in `_ACE_PRE_TOOLCHANGE`, and the "Tool Change Failed" and runout prompts would show buttons (`Extrude 100mm`, `Retract 100mm`) that raise "Unknown command".
2. `ACE_SELFTEST` (setup_tools.py) reports one FAIL on your printer: it looks for `filament_switch_sensor filament_runout_nozzle` and you have no toolhead sensor by design. It passes the `_ACE_VARS` check (because `register_tool_commands` is False). The FAIL is a false alarm.
3. `ACE_SETUP_SAVE` / `ACE_SETUP_CONFIRM` write into `acepro_macros.cfg` next to printer.cfg (it makes `acepro_macros.cfg.before-setup` first). That file does not exist on the Pi, so both commands refuse.
4. The driver's endless spool and runout code call `RESUME PURGE=0` after a swap. Our `RESUME` (macros.cfg L261, factory) reads only `E`; Klipper ignores the unknown `PURGE` parameter, so the driver's "no purge" request would have no effect. The path is not used here (checked against the Pi snapshot, 2026-11-19).
5. `connect()` docstring in serial_manager.py L715-732 contains pasted code lines (cosmetic, inside the string). The temperature-change debug line in `_status_update_callback` (L1717-1725) compares two consecutive 1 s samples, so the 5 C change message practically never fires (debug logging only).
6. `ace_current_index` stays -1 after a reconnect, so the driver's "restore feed assist after reconnect" logic (restores only the slot named by `ace_current_index`) restores nothing. The Pi's saved variables hold `ace_feed_assist_index_0 = -1`, `feed_assist_active_after_ace_connect` is False, and the log has no restore lines (checked 2026-11-19, read-only look). Your macros' own watcher (`rpi_ace.cfg` L533, `connection_state == "connected"` and `feed_assist_slot`) re-asserts assist; it does not depend on the driver restore.
7. ACE 2 dryer `remain_time` is passed on in the unit the box sends (protocol_ace2.py L448, no division), while `duration` is divided by 60 to minutes (L447). The ACE 1 value comes straight from the box in minutes. Fluidd's `zrAceDryRemaining` guesses the unit; still open, no change.
**Third-party files**: `virtual_pins.py` is Pedro Lamas' klipper-virtual-pins (GPLv3, 2023); `temperature_ace.py` is the ACE sensor above. Both load on the Pi (`[virtual_pins]`, `[temperature_ace]`). I did not compare them with upstream and did not check `virtual_pins.py` against the Klipper 0.13.0-827 pin API (could not verify); the module works on your printer today (the pins `ACE_Pro` and `ACE_Auto_Load` are listed in Fluidd).
- Not verified: a diff against the upstream ACE driver; behaviour with an ACE 2 on a shared bus (no unit available here); the driver on a printer that registers its own tool commands.

### rpi_endless.cfg (278 lines), rpi_stats.cfg (111), zr_tools.cfg (308) - line-by-line reading (2026-11-19; checked against Klipper 0.13.0-827-g29d4ec2d6, macros.cfg RESUME variables, hub.cfg, the repo copies of the files)
Note: I read the repo copies (panel repo `config/`, installer `zr_tools/`); the Pi copies were not compared line by line in this pass (trust the files on the Pi if they differ).
Comments in macro bodies (corrected 2026-11-19): when Klipper reads the config (`klippy/configfile.py` L172, Python 3) every `#` or `;` that follows a space, and every full line starting with `#` or `;`, is removed together with the rest of the line, also inside a multi-line macro. So the `# ...` and `; ...` notes in these macros are harmless, and **a text that needs ` #` or ` ;` inside a message (e.g. `RESPOND MSG="... #3"`) would be cut at that point** - no such message was found in the rpi_* files, factory files not searched for this.
**rpi_endless.cfg**: `_WM_ENDLESS` (state variables), `WM_ENDLESS_SET` (three saved switches wm_endless / _auto / _tangle), `_WM_ENDLESS_TANGLE` (called from hub.cfg, exists, guarded by an existence check there), `WM_ENDLESS_FIXED`, `WM_ENDLESS_PLAN` (message only), `_WM_ENDLESS_WATCH` (timer: 8 s after start, then every 3 s) -> `_WM_ENDLESS_TICK`, `_WM_ENDLESS_PROMPT_CLOSE`, `WM_ENDLESS_CONTINUE` -> `_CHANGE_TOOL T=` -> `_WM_ENDLESS_3` (copies the resume temperature of the empty head to the spare head in the factory `RESUME` variables `resume_temperature0..3` - they exist, macros.cfg L263-266 - and points `box_modify_tN_backup` at the spare) -> `RESUME` -> `_WM_ENDLESS_4` (moves by the difference of the two heads' offsets, relative move inside SAVE/RESTORE_GCODE_STATE).
- Fields read: `printer.print_stats.state/print_duration/filename`, `printer.gcode_move.homing_origin`, `printer["filament_switch_sensor filamentN"].filament_detected` (exist on the Ultra-S), `printer["gcode_macro _WM_ACE"].ace_instance` (variable exists in rpi_ace.cfg), `ace_instance_N.connection_state`, `.slots[c].status` (checked in the driver), `printer["gcode_macro _WM_PAUSE_STATE"].active` (exists in rpi_base.cfg, guarded). All present - checked 2026-11-19.
- Findings: (1) `_WM_ENDLESS_TICK` reads `filament_switch_sensor filament0..3` for four heads without an existence check; on a printer without these sensors it would raise every 3 s (file is installed on the Ultra-S only). (2) The swap runs inside the timer (`WM_ENDLESS_CONTINUE` is called from the delayed_gcode): it is protected by the `tried` flag and by the timer rule (next wake after the script ends); when the swap fails the print stays paused and `tried` stays 1 until the print state changes - intended, but nothing tells the user a second time. (3) `_WM_ENDLESS_4` moves with `G1 X Y Z F600` relative, Z too; if the difference is large (different Z offsets) the move goes straight with no lift. (4) The macro depends on `RESTORE_GCODE_STATE` keeping the new head's offsets (`variable_keeps: 1`, "WonderMaker's Klipper and upstream with wm_gcode_compat"); with plain upstream behaviour the correction would be wrong - it was not tested here. (5) `WM_ENDLESS_CONTINUE` refuses when `current_extruder` differs from FROM, fine. Test status: see FIX-LOG.md (endless spool is marked EXPERIMENTAL in the file header).
**rpi_stats.cfg**: `_WM_STATS` (state), `_WM_STATS_TICK` (every 2 s from `_WM_STATS_POLL`: counts a change when `current_extruder` differs from the last value seen; adds the growth of `print_stats.print_duration` to the head on the carriage; saves `wm_stat_time<N>` when the head changes or 60 s have collected), `WM_STATS_RESET`, `WM_SET_TOOL_MAP`.
- Findings: (1) Two tool changes inside 2 s (A to B to A) are counted as none, a change seen only at the poll. (2) `WM_SET_TOOL_MAP MAP=0:2,1:3` writes only the tools it lists; tools not listed keep the previous map (the Fluidd window writes all four, the Orca plugin line is only the listed ones), so a map left from an older print can stay for the unlisted tools. (3) `WM_SET_TOOL_MAP` refuses only while paused, not while printing (the line sits at the top of the G-code, so it normally runs before the print starts). (4) Print time is lost for the part of a minute before a power cut (stated in the header).
**zr_tools.cfg**: `ZR_SET_TOOL_INFO` (zr_tN_color/mat/temp), `ZR_SET_TOOL_PA` + `_ZR_APPLY_TOOL_SETTINGS` (pressure advance per head), `ZR_MAP_TOOL`, `ZR_MAP_RESET`, `ZR_CHAMBER` (M141, max 65), `ZR_AIR_FILTER`, `_WM_LOAD_SETTINGS` (all load/unload numbers: default 220 C, push 50 mm at 300 mm/min, wait 180 s; tip: snap 20 mm at 58 mm/s, cool 30 C, pull 45 mm at 20 mm/s), `_WM_LOAD_TEMP`, `_WM_GO_WIPE_HEAT`, `_WM_UNLOAD_TIP`, `ZR_LOAD` -> `_WM_ZR_LOAD_GO` + timer `_wm_zr_load_wait`, `ZR_RETRACT`, `ZR_UNLOAD` (same as RETRACT).
- Findings: (1) `ZR_LOAD`, `ZR_RETRACT` and `ZR_UNLOAD` refuse only while `printing`; while a print is **paused** they would run `_CHANGE_TOOL` and heat (the Fluidd card blocks paused too, a console or screen call does not). (2) `ZR_MAP_TOOL` and `ZR_MAP_RESET` write `box_modify_tN` but not `box_modify_tN_backup` (the Fluidd Print window and `WM_SET_TOOL_MAP` write both; RESUME and the endless spool restore from the backup) - the backup stays at the old value. (3) `ZR_CHAMBER` accepts negative numbers (only max 65 is checked). (4) `_WM_GO_WIPE_HEAT` and `_WM_UNLOAD_TIP` wait with `TEMPERATURE_WAIT` and no time limit (heating to target, and cooling by 30 C by itself). (5) Hard-coded wipe default `[-13.0, 240.0]` in `_WM_GO_WIPE_HEAT`. (6) The snap speed 58 mm/s needs the extruder to allow it (no `max_extrude_only_velocity` is set in extruder0.cfg, Klipper's default applies; not tested here beyond the B-069 history). (7) The comment says WonderMaker resets the map to 1:1 at PRINT_END and CANCEL_PRINT; that was not re-read in macros.cfg in this block (see the macros.cfg block).

### offset_calibrate.cfg (381 lines) - line-by-line reading (2026-11-19; checked against Klipper 0.13.0-827-g29d4ec2d6 factory modules `tools_calibrate_core.py`, ACE driver commands, saved_variables.cfg snapshot)
Source read: the installer repo copy (it already holds our F-150 changes and `_WM_CAL_CLEARANCE`); the Pi copy was not compared line by line.
Macros: `[tools_calibrate]` settings (3 samples, tolerance 0.05, 6 retries, probe_position default 299.0, 290.0, 8.5, 6.9, 5.8; the printer uses the saved variable `probe_position`, e.g. 298.19, 286.08, 9.14, 6.37, 6.06), `RESPOND_T_OFFSET`, `SAVE_T_OFFSET`, `RESPOND_T_POSITION`, `_APPLY_PRE_Z_OFFSET`, `NOZZLE_PREPARE`, `NOZZLE_CALIBRATE_TOOL_OFFSET`, `RAPID_MODE`, `CALIBRATE_TOOL_OFFSET`, `CALIBRATE_OFFSET_ALL_RAPID_MODE`, `CALIBRATE_OFFSET_ALL_FINE_MODE`, `CALIBRATE_TOOL_Z_OFFSET`, `_SAVE_PROBE_POS`, `SAVE_TOOL_OFFSET`, `POP`, `_WM_CAL_CLEARANCE`.
Fields and commands verified: `printer.tools_calibrate.last_result` (tools_calibrate_core.py), `printer.probe.last_probe_position`, `printer.configfile.settings.probe.z_offset`, `thr_number = 4` in saved_variables, `ACE_ENABLE_FEED_ASSIST` / `ACE_DISABLE_FEED_ASSIST` with `T=` (commands.py), the object `ace` (instance 0, driver `__init__.py` L90), `printer.toolhead.axis_maximum` (used by `_WM_CAL_CLEARANCE`; same status as used elsewhere) - checked 2026-11-19.
Findings (reported, not fixed):
1. **Collision detection can stay on with threshold 12 / shutdown**: `CALIBRATE_TOOL_OFFSET` sets `SET_COLLISION_THRESHOLD THRESHOLD=12.0 WINDOW=2 ACTION=shutdown`, calls `COLLISION_DETECT_ENABLE`, then `TOOL_LOCATE_SENSOR` or `TOOL_CALIBRATE_TOOL_OFFSET`, and only afterwards `COLLISION_DETECT_DISABLE` (L251). If the touch command raises an error (sensor not found, tolerance retries used up) the macro stops before L251, so detection stays enabled with the low threshold and the shutdown action until Klipper restarts. The rpi_calibration.cfg setter helpers switch it off on their failure path; this factory macro does not.
2. `_APPLY_PRE_Z_OFFSET` keeps the T0 probe result in its own variable `last_z_result` (0 after every Klipper start). For T1..T3 it uses `probe_z - last_z_result`; if Klipper restarted between the T0 and T1 steps the pre-offset would be wrong without any message.
3. `T{T}` / `T{tool}` (NOZZLE_PREPARE, CALIBRATE_TOOL_OFFSET, CALIBRATE_TOOL_Z_OFFSET, POP) go through `box_modify_tN` (print map); the default value 99 produces the command `T99` when T is not given. Identity map today.
4. `CALIBRATE_TOOL_Z_OFFSET` reads `current_extruder` when the macro text is rendered, before its own `T{tool}` runs. Called for a tool that is not on the carriage it prints the warning "result will not saved" and does not save (by design of the warning); called after `CALIBRATE_TOOL_OFFSET T=` (as RAPID_MODE does) it saves.
5. Hard-coded values: `G1 X150.0 Y1` and `Z80` (NOZZLE_PREPARE), `G0 Y240` / `X-13` / `Y275` (NOZZLE_CALIBRATE_TOOL_OFFSET wipe strokes, the known open item), `G1 X150 Y135` (CALIBRATE_TOOL_OFFSET, CALIBRATE_TOOL_Z_OFFSET), `G1 Y2 Z2` (POP, absolute move), 140 / 160 / 220 / 222 C and a 100 C cool-down.
6. `TEMPERATURE_WAIT` without a time limit in NOZZLE_PREPARE (cool to 100 C) and POP (cool to 102 C).
7. `NOZZLE_PREPARE` `G28 Z` (T0 only) and `RAPID_MODE` `G28 Z` need X and Y homed; the homing override handles it only when it is active. `CALIBRATE_OFFSET_ALL_FINE_MODE` passes `S=220` that `NOZZLE_PREPARE` ignores.
8. `SAVE_T_OFFSET` with a T outside 0..3 and not 99 leaves `origin_x` undefined and fails with a template error; 99 is the "not given" marker for X, Y, Z so an offset of exactly 99 cannot be set.
9. Cosmetic: "POSITON" in `RESPOND_T_POSITION`; F-150 notes in the file are comments only.
10. `_WM_CAL_CLEARANCE` (our macro): raises the head to at least 7.0 mm only when XYZ are homed and no print runs; raises an error when the lift would pass the Z maximum. Used by 11 macros in 5 files (checked by name search).

### change_macros.cfg (686 lines) - line-by-line reading (2026-11-19; checked against Klipper 0.13.0-827-g29d4ec2d6, `custom_hall.py`, zr_tools.cfg, and the Pi snapshot of 2026-11-18: the pressure-advance line is at L425 in both)
Macros: lock/unlock chain `UNLOCK`, `_UNLOCK_TOOL`, `_CHECK_AND_UNLOCK`, `UNLOCK_TOOL_FINISH`, `LOCK`, `_LOCK_CHECK`, `_LOCK_TOOL`, `_CHECK_AND_LOCK`, `_LOCK_TOOL_FINISH`, `_CHECK_T_SEQUENCE`; `T0..T3` (read `box_modify_tN`, call `_CHANGE_TOOL T=`, then give the feed rate back, our `_wmp_entry_f` change); `_CHANGE_TOOL`, `_CHECK_CHANGE_TOOL_AGAIN`, `_CHANGING_TOOL`, `_CHECK_CHANGE_TOOL`, `_raise_z`, `_descend_z`, `_check_tool_exist`, `_check_hall_sensor`, `_check_current_extruder_value`, `_WAIT_TOOL_TEMPERATURE`, `GET_TOOL_POSITION`, `SAVE_T_POSITON` (sic), `_SAVE_TOOL_POSITION`, `CALIBRATE_TOOL_POSITION`, `_ENABLE_SENSOR`, `PARK_CURRENT_TOOL`, `PARK_CURRENT_TOOL_RETRY`, `_OFFSET_SET` (our version: adds Z trim, nozzle heat growth and the live Z number to the saved tool offset).
How a tool change runs, in plain words: `_CHANGE_TOOL T=n` clears the failure flags, checks the saved current tool against the Hall sensor, checks the tool exists, runs `_CHANGING_TOOL` (home X Y when needed, raise Z 2 mm, put the old tool back with `_UNLOCK_TOOL`, pick up the new tool with `_LOCK_TOOL`, lower Z), then `_CHECK_CHANGE_TOOL` (on success: saves `current_extruder`, applies the offsets with `_OFFSET_SET`, sets the flow, enables only that tool's filament sensor, activates the extruder, sets pressure advance 0.04, waits for the temperature). One failure: it retries once; a second failure while printing homes X Y, moves to X150 Y1 and PAUSEs, with a message per fail flag (-1 not in its place, -2 lock failed, -3 put-back failed, -4 Hall sensor error, -5 wrong order, -6 print misalignment).
Fields and commands verified: `printer.custom_hall.Raw` and `.last_toolhead_position` (custom_hall.py), `GET_T_POSITION` (custom_hall.py L32), `ECHELON_STEPPER*` (factory), `printer["filament_switch_sensor dockedN"]`, `sensor_b`, `printer.toolhead.homed_axes/position/extruder`, `printer.configfile.settings.stepper_z.position_endstop`, `_WM_HEAT_AT_WIPE` and `_WM_HEAT_BACK` (rpi_base.cfg, guarded by existence checks), `_WM_LIVEZ` (rpi_calibration.cfg, guarded) - checked 2026-11-19.
Findings (reported, not fixed):
1. **Pressure advance is always reset to 0.04 at a tool change** (L425, hard-coded). The per-toolhead values saved by `ZR_SET_TOOL_PA` (`tN_pressure_advance`) and the helper `_ZR_APPLY_TOOL_SETTINGS` in zr_tools.cfg are never called by any macro, in the repo and on the Pi (checked by search, also in the Pi snapshot); the comment in zr_tools.cfg expects a patch of this line that is not applied. A PA set by the slicer or by `ZR_SET_TOOL_PA` is overwritten at the next tool change.
2. **Dead code in `_CHANGING_TOOL` (L337, L351)**: the test `printer_state == "printing" and save_position == 1` uses two names that do not exist in that macro (`printer_state` is set in `_CHECK_CHANGE_TOOL`, `save_position` is a variable of `_CHANGE_TOOL`). An undefined name compares as false, so `SAVE_GCODE_STATE NAME=CHANGE_TOOL_PARK` and the restore after the change never run. The variable `save_position` that `_CHANGE_TOOL` sets to 1 at its end is therefore unused.
3. `_OFFSET_SET` tests `retry == 1` (L657), a name that does not exist in that macro; always false, harmless.
4. `T0..T3` always map through `box_modify_tN`; `_CHANGE_TOOL` itself does not (it is the physical tool). All macros that call `T{n}` instead of `_CHANGE_TOOL T=` follow the print map (see the remap findings above).
5. `_CHANGE_TOOL` has no print-state check: it runs in a paused print or at any time when called (the Fluidd card and `ZR_*` guards are outside).
6. `_WAIT_TOOL_TEMPERATURE` waits with `TEMPERATURE_WAIT` and no time limit; only during printing or paused.
7. Hard-coded: dock Y positions 270 / 310 (`_UNLOCK_TOOL`, `_LOCK_TOOL`, `G0 Y{position_y+0.4}`, `position_y-15`), Hall limits 3450 / 4700 / 6000, `G1 X150 Y1` (failure park), `G1 X150 Y200`, dock windows in `SAVE_T_POSITON` (T0 X 40-50, T1 100-110, T2 163-173, T3 225-235, Y 335-347; values outside are refused and the old position kept), lock retry distance -125 - 10 x retry.
8. `_raise_z` takes the Z limit from `stepper_z.position_endstop`; if that option did not exist on a printer the macro would fail (it exists here).
9. `_ENABLE_SENSOR` switches the runout action of all filament sensors off and the current one on at every tool change (the detected state still updates, so Fluidd and the endless spool still see all four).
10. Typos kept in names: `SAVE_T_POSITON`, "TOOl", "form". Cosmetic.

### macros.cfg (861 lines) - line-by-line reading (2026-11-19; checked against Klipper 0.13.0-827-g29d4ec2d6, the Pi snapshot (same RESUME variables and line numbers), rpi_base.cfg, rpi_calibration.cfg)
Macros: `PRINTER_INIT` (timer, 5 s after start: `RESET_FLOW_EXTRUDER`), `START_PRINT`, `PRINT_END`, `E_axis_move`, `_WM_PAUSE_STATE`, `PAUSE`, `RESUME`, `CANCEL_PRINT`, `PROBE_CALIBRATE` (wrapper), `G29`, `G30`, `G31`, `BED_MESH_CALIBRATE` (wrapper), `M109`, `M104`, `M190`, `M106`, `M107`, `M141`, `M191`, `_RGB_LOAD`, `_RGB_UNLOAD`, `_RGB_CURRENT`, `EXTRUDE_FILAMENT`, `RETRACT_FILAMENT`, `LOAD_FILAMENT`, `UNLOAD_FILAMENT`, `M221` (wrapper), `RESET_FLOW_EXTRUDER`, `filament_insert_gcode`, `filament_insert`. This repo/Pi copy already holds our changes (live Z, bed soak, F-105 start purge, F-150 heat at wipe, the `_wmp` items), marked in the comments.
How the print runs, in plain words: `START_PRINT` (from the slicer's start G-code) turns the chamber light on, resets live Z, sets the bed, **forces `box_modify_t0` to 0 until the end of the mesh**, heats T0 to 140 and homes, heats the bed, runs the bed warp wait, wipes, makes the bed mesh (adaptive when the slicer sends the mesh area, else full), puts the saved mapping of T0 back, runs our `_WM_START_PURGE` (or the factory left-edge purge) and picks up `INITIAL_TOOL`. `PAUSE` stores the temperatures of all heads, saves the print position and the print map to the `_backup` variables (only after START_PRINT is finished), moves to X150 Y1, turns all heaters and fans off; `RESUME` heats the bed and all heads that had a target, puts the map back from the backup, purges 20 mm at the wipe area, wipes, returns to the print and calls `M24`. `PRINT_END` and `CANCEL_PRINT` raise Z, heaters off, wipe, park the tool, `M84`, reset flow and **reset the print map and its backup to 1:1**.
Fields and commands verified: `printer.virtual_sdcard.is_active`, `printer.toolhead.axis_maximum.z`, `printer.configfile.settings.stepper_z.position_endstop`, `printer.configfile.settings.idle_timeout.timeout`, `printer["fan_generic auxiliary_fan"]`, `printer["heater_generic chamber"]`, `rename_existing` names (M99109, M99104, M99190, M99106, M1077, M99221, BASE_PAUSE, BASE_RESUME, BASE_CANCEL_PRINT, BED_MESH_CALIBRATE_BASE, PROBE_CALIBRATE_BASE), `_WM_START_PURGE`, `_WM_BED_SOAK`, `_WM_BED_SOAK_MARK`, `_WM_GO_WIPE`, `_WM_HEAT_AT_WIPE`, `_WM_HEAT_BACK`, `_WM_LIVEZ_HEAT`, `_WM_LIVEZ_RESET`, `_WM_Z_TRIM_APPLY` (all exist; every one is guarded by an existence check) - checked 2026-11-19.
Findings (reported, not fixed):
1. `START_PRINT` sets `box_modify_t0` to 0 at L51 and puts it back at L83. If the print stops between the two (cancel, error in `BED_MESH_CALIBRATE`, a pause during the long bed warp wait), `box_modify_t0` stays at 0 until `CANCEL_PRINT` / `PRINT_END` resets everything to 1:1; after a pause during START_PRINT the PAUSE macro does not save the backup (print_body_ready is False), so RESUME restores the backup that the Fluidd Print window wrote (fine) - not tested.
2. `RESUME` calls `M24` itself and neither `BASE_RESUME` nor `BASE_PAUSE`/`BASE_CANCEL_PRINT` are called by the wrappers (`PAUSE` uses `M25`); the state of Klipper's pause_resume module is therefore not used. Works today; any module that waits for `BASE_PAUSE` (e.g. some third-party macros) would not see the pause.
3. `PAUSE` retracts 2.5 mm, parks, then pushes the 2.5 mm back at the park position (L239) and `RESUME` retracts `E|int` = 2 mm (default 2.5 becomes 2 with `|int`): a 0.5 mm difference between the two, and filament pushed out at the park spot. Factory behaviour.
4. **No time limit** on `TEMPERATURE_WAIT` in `M109` (our wrapper), `M190` (waits until within 1 C, also downward after an overshoot), `M191` (chamber), `START_PRINT` (`M109 S140 T0`, `M190`), `RESUME` (`M190`, `M109`), `G29`, `LOAD_FILAMENT`.
5. `M191` heats the bed to `bed_assist_temp` = 100 C while it waits, when the slicer does not send `BED_TEMP=`; fans, the nozzle on the carriage (150 C) and the bed are changed and only the fans and nozzle are switched off again at the end, the bed stays at the value given.
6. `T0`, `T{INITIAL_TOOL}` and `M104/M109 ... T{n}` follow `box_modify_tN` (our `M104`/`M109` wrappers map the head; the print map is the intended use); `G29` uses `T0` and `START_PRINT` M109 T0 depends on the forced 0 map above.
7. `G29`: heats the bed to 55 and leaves it on; picks `T0` through the map; the `G28 Z` condition tests `"xy" not in homed_axes` at render time, before its own `G28 X Y` ran, so Z is homed only when XY was not homed when G29 started (the `BED_MESH_CALIBRATE` wrapper homes everything when needed, so the mesh still runs).
8. `EXTRUDE_FILAMENT` checks the temperature of the active extruder but heats and extrudes with whatever is active, not tool `T=` (no tool change); the Fluidd card uses `ZR_LOAD` / `LOAD_FILAMENT` (patched F-150 version with tool change) and not this macro.
9. Hard-coded: `M109 S140` and X150 Y135 (G29), `X-13 Y80` / `Y232` (EXTRUDE, RETRACT, filament_insert_gcode), `M109 S220` (LOAD, UNLOAD, filament_insert_gcode), left-edge purge at X0 Y70-150 (fallback), PAUSE park X150 Y1 Z+10, `z_max` from `position_endstop|int`.
10. `PAUSE` reads `printer["fan_generic auxiliary_fan"].speed` without an existence check (the `air_fan` has one); a printer without `auxiliary_fan` would fail to pause. Present here.
11. `CANCEL_PRINT` computes `current_temp` (unused) and calls `SDCARD_RESET_FILE` without the `virtual_sdcard.is_active` test that `PRINT_END` has; it is the Klipper-supported way to stop a file here (not changed).
12. Section header comments (`[gcode_macro START_PRINT] #start-print macro`, `[gcode_macro M107]    #added ...`) are removed by Klipper's config reader (see the comment note above); `M107` is renamed `M1077` (original name not `M107`), only used through `M106 S0`.

### timelapse.cfg (427 lines) - line-by-line reading (2026-11-19; checked against Config_Changes.md of this Klipper and the live printer, read-only query)
Third-party file (moonraker-timelapse macro version 1.15, header "DO NOT CHANGE ANY MACRO"); I did not diff it against the upstream release in this pass. Macros: `GET_TIMELAPSE_SETUP`, `_SET_TIMELAPSE_SETUP`, `TIMELAPSE_TAKE_FRAME`, `_TIMELAPSE_NEW_FRAME`, timer `_WAIT_TIMELAPSE_TAKE_FRAME`, `HYPERLAPSE`, timer `_HYPERLAPSE_LOOP`, `TIMELAPSE_RENDER`, timer `_WAIT_TIMELAPSE_RENDER`, `TEST_STREAM_DELAY`.
Live state read from the printer (read-only, 2026-11-19): `macro` = pause BASE_PAUSE, resume BASE_RESUME (so the timelapse uses Klipper's own pause, **not** our `PAUSE` / `RESUME` wrappers), `enable` true, `park.enable` false (no park, no pause per frame), HYPERLAPSE not running.
Findings (reported, not fixed): (1) deprecated accessor `printer.gcode_move.gcode_position.e` at L264 (`.e` removed in the new G-code position handling, Config_Changes.md 20251106); only used when `park.enable` is true, which is off now. (2) With park enabled, `_WAIT_TIMELAPSE_TAKE_FRAME` polls every 0.5 s with no time limit; if Moonraker never answers `takingframe` stays true and the head stays parked and paused. (3) If `_SET_TIMELAPSE_SETUP` has not run, the default `macro` is `PAUSE` / `RESUME`, which would call our wrappers (heaters off, wipe purge) for every frame; the live printer has BASE_*, so this does not happen today. (4) `TIMELAPSE_RENDER` pauses with BASE_PAUSE at the end and resumes after the render; nothing in `PRINT_END` calls it. (5) The macros restore `M82`/`G92 E` and speed factors after a frame; our M83/M221 wrappers are not involved.

## rpi_base.cfg
Installer part: safety, LEDs, head sensors, unload runner, z_rise, homing, bed soak, heat at wipe, purge

### WM_SAFETY_START
- **File / lines**: rpi_base.cfg L30-34 (delayed_gcode timer)
- **What it does**: After boot checks the saved variables/safety (_WM_SAFETY_CHECK).
- **Calls**: _WM_SAFETY_CHECK
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: none) - checked 2026-11-18
- **Risk**: none  |  **Tags**: safety  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_SAFETY_CHECK
- **File / lines**: rpi_base.cfg L35-59 (gcode_macro)
- **What it does**: Start-up check of the saved switches if_check_extruder_status and is_nozzle_setting
- **Calls**: -
- **Called by**: WM_SAFETY_START
- **Variables**: -
- **Uses**: reads printer.save_variables; saves if_check_extruder_status VALUE
- **Commands**: all exist (built-in/module commands used: RESPOND, SAVE_VARIABLE) - checked 2026-11-18
- **Risk**: none  |  **Tags**: safety  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### WM_PRINT_END_WATCH
- **File / lines**: rpi_base.cfg L60-82 (delayed_gcode timer)
- **What it does**: Watches for a finished print and runs PRINT_END cleanup once.
- **Calls**: PRINT_END, _WM_PAUSE_STATE
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: reads printer.print_stats
- **Commands**: all exist (built-in/module commands used: RESPOND, UPDATE_DELAYED_GCODE) - checked 2026-11-18
- **Risk**: none (+ through the macros it calls: ACE, HEATS, MOVES THE TOOLHEAD)  |  **Tags**: print  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_LED_STATE
- **File / lines**: rpi_base.cfg L83-86 (gcode_macro)
- **What it does**: Remembers LED state between runs of WM_TOOL_LEDS.
- **Calls**: -
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: seen
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: none) - checked 2026-11-18
- **Risk**: none  |  **Tags**: light  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### WM_TOOL_LEDS
- **File / lines**: rpi_base.cfg L87-137 (delayed_gcode timer)
- **What it does**: Sets the tool-head LEDs (load/unload/current) by state every few seconds.
- **Calls**: _RGB_CURRENT, _RGB_LOAD, _RGB_UNLOAD
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: reads printer.save_variables; sets variables of _WM_LED_STATE
- **Commands**: all exist (built-in/module commands used: SET_GCODE_VARIABLE, UPDATE_DELAYED_GCODE) - checked 2026-11-18
- **Risk**: ACE  |  **Tags**: light, tool-change  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_HEAD_QUEUE
- **File / lines**: rpi_base.cfg L138-146 (gcode_macro)
- **What it does**: State of the head sensor watcher and the load queue (do not run)
- **Calls**: -
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: prev, marks, cand, queue
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: RESPOND) - checked 2026-11-18
- **Risk**: none  |  **Tags**: misc  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_HEAD_MARK
- **File / lines**: rpi_base.cfg L147-157 (gcode_macro)
- **What it does**: First line of each insert_gcode (extruder0-3.cfg): Klipper started the load of tool T
- **Calls**: -
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: sets variables of _WM_HEAD_QUEUE
- **Commands**: all exist (built-in/module commands used: SET_GCODE_VARIABLE) - checked 2026-11-18
- **Risk**: none  |  **Tags**: misc  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_HEAD_LOAD
- **File / lines**: rpi_base.cfg L158-193 (gcode_macro)
- **What it does**: Load of a queued tool T: the same steps as the factory insert_gcode in extruderN.cfg
- **Calls**: M104, M109, PARK_CURRENT_TOOL, _WM_ACE_GRAB, _WM_ACE_HEAD, _WM_ACE_HEAD_DONE, filament_insert, filament_insert_gcode
- **Called by**: WM_HEAD_SENSOR_WATCH
- **Variables**: -
- **Uses**: reads printer.print_stats; saves if_check_extruder_status value
- **Commands**: all exist (built-in/module commands used: ACTIVATE_EXTRUDER, RESPOND, SAVE_VARIABLE, UPDATE_DELAYED_GCODE) - checked 2026-11-18
- **Risk**: HEATS, ACE (+ through the macros it calls: MOVES THE TOOLHEAD)  |  **Tags**: load  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### WM_HEAD_SENSOR_WATCH
- **File / lines**: rpi_base.cfg L194-282 (delayed_gcode timer)
- **What it does**: Watches the head sensors: starts _WM_HEAD_LOAD when new filament appears that Klipper did not start loading.
- **Calls**: _WM_HEAD_LOAD
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: reads printer.idle_timeout, printer.print_stats, printer.save_variables; sets variables of _WM_HEAD_QUEUE
- **Commands**: all exist (built-in/module commands used: RESPOND, SET_FILAMENT_SENSOR, SET_GCODE_VARIABLE, UPDATE_DELAYED_GCODE) - checked 2026-11-18
- **Risk**: ACE (+ through the macros it calls: HEATS, MOVES THE TOOLHEAD)  |  **Tags**: misc  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_UNLOAD
- **File / lines**: rpi_base.cfg L283-295 (gcode_macro)
- **What it does**: State of the unload menu (nothing to run here)
- **Calls**: -
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: active, queue, total, step, current, ok, done
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: RESPOND) - checked 2026-11-18
- **Risk**: none  |  **Tags**: load, unload  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_UNLOAD_CLOSE
- **File / lines**: rpi_base.cfg L296-303 (gcode_macro)
- **What it does**: Close the popup (the Cancel buttons)
- **Calls**: -
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: M118, RESPOND) - checked 2026-11-18
- **Risk**: none  |  **Tags**: load, unload  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_UNLOAD_RESET
- **File / lines**: rpi_base.cfg L304-318 (gcode_macro)
- **What it does**: Back to idle (list cleared, ACE unload temperature back to 220)
- **Calls**: -
- **Called by**: WM_UNLOAD_STOP, _WM_UNLOAD_ABORT, _WM_UNLOAD_END, _wm_unload_runner
- **Variables**: -
- **Uses**: sets variables of _WM_ACE_UNLOAD_RUN, _WM_UNLOAD
- **Commands**: all exist (built-in/module commands used: SET_GCODE_VARIABLE) - checked 2026-11-18
- **Risk**: ACE  |  **Tags**: load, unload  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### WM_UNLOAD_MENU
- **File / lines**: rpi_base.cfg L319-396 (gcode_macro)
- **What it does**: Popup to unload one tool or all tools (ACE or not)
- **Calls**: -
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: reads printer.print_stats, printer.save_variables
- **Commands**: all exist (built-in/module commands used: RESPOND) - checked 2026-11-18
- **Risk**: ACE  |  **Tags**: load, unload  |  **Fluidd**: WM Ultra Filament
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_UNLOAD_ASK
- **File / lines**: rpi_base.cfg L397-416 (gcode_macro)
- **What it does**: Confirm popup (T=0..3 or T=ALL)
- **Calls**: -
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: RESPOND) - checked 2026-11-18
- **Risk**: none  |  **Tags**: load, unload  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_UNLOAD_GO
- **File / lines**: rpi_base.cfg L417-450 (gcode_macro)
- **What it does**: _WM_UNLOAD_GO T=0..3 or T=ALL - unload one tool or all tools, one after the other
- **Calls**: -
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: reads printer.print_stats; sets variables of _WM_UNLOAD
- **Commands**: all exist (built-in/module commands used: RESPOND, SET_GCODE_VARIABLE, UPDATE_DELAYED_GCODE) - checked 2026-11-18
- **Risk**: ACE  |  **Tags**: load, unload  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### WM_UNLOAD_STOP
- **File / lines**: rpi_base.cfg L451-461 (gcode_macro)
- **What it does**: Drop the rest of the unload list. The tool that is running finishes its step.
- **Calls**: _WM_UNLOAD_RESET
- **Called by**: ACE_WM_STOP
- **Variables**: -
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: RESPOND) - checked 2026-11-18
- **Risk**: none (+ through the macros it calls: ACE)  |  **Tags**: load, unload  |  **Fluidd**: WM Ultra Filament
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_UNLOAD_ABORT
- **File / lines**: rpi_base.cfg L462-471 (gcode_macro)
- **What it does**: Called when the ACE reports a failure (from _WM_ACE_FAIL)
- **Calls**: _WM_UNLOAD_RESET
- **Called by**: _WM_ACE_FAIL
- **Variables**: -
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: RESPOND) - checked 2026-11-18
- **Risk**: none (+ through the macros it calls: ACE)  |  **Tags**: load, unload  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_UNLOAD_END
- **File / lines**: rpi_base.cfg L472-489 (gcode_macro)
- **What it does**: All tools of the list are handled - heaters off, tool back in its dock
- **Calls**: PARK_CURRENT_TOOL, _WM_UNLOAD_RESET
- **Called by**: _wm_unload_runner
- **Variables**: -
- **Uses**: reads printer.save_variables
- **Commands**: all exist (built-in/module commands used: RESPOND, SET_HEATER_TEMPERATURE) - checked 2026-11-18
- **Risk**: HEATS, ACE (+ through the macros it calls: MOVES THE TOOLHEAD)  |  **Tags**: load, unload  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _wm_unload_runner
- **File / lines**: rpi_base.cfg L490-560 (delayed_gcode timer)
- **What it does**: Starts a queued unload (ACE_WM_UNLOAD or ZR_RETRACT) when the machine is free.
- **Calls**: ACE_WM_UNLOAD, ZR_RETRACT, _WM_UNLOAD_END, _WM_UNLOAD_RESET
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: reads printer.print_stats, printer.save_variables; sets variables of _WM_ACE_UNLOAD_RUN, _WM_UNLOAD
- **Commands**: all exist (built-in/module commands used: RESPOND, SET_GCODE_VARIABLE, UPDATE_DELAYED_GCODE) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, ACE (+ through the macros it calls: HEATS)  |  **Tags**: load, unload  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### SET_GCODE_OFFSET
- **File / lines**: rpi_base.cfg L561-577 (gcode_macro) - renames the original to _WM_SET_GCODE_OFFSET
- **What it does**: Wrapper: applies the offset with live Z adjust per tool and ACE restore (calls _WM_SET_GCODE_OFFSET).
- **Calls**: _WM_LIVEZ_SGO
- **Called by**: CALIBRATE_TOOL_OFFSET, CALIBRATE_TOOL_Z_OFFSET, NOZZLE_PREPARE, START_PRINT, TIMELAPSE_TAKE_FRAME, ZR_RETRACT, Z_HOMING, _LOCK_TOOL, _OFFSET_SET, _UNLOCK_TOOL, _WM_ACE_HOME, _WM_BEDWARP_START, _WM_NOZZLE_PREPARE, _WM_SETTER_GO, _WM_ZR_LOAD_GO, _WM_Z_TOUCH
- **Variables**: -
- **Uses**: reads printer.toolhead
- **Commands**: all exist (built-in/module commands used: _WM_SET_GCODE_OFFSET) - checked 2026-11-18
- **Risk**: HEATS, ACE (+ through the macros it calls: MOVES THE TOOLHEAD)  |  **Tags**: calibration  |  **Fluidd**: none
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_HEAT_AT_WIPE
- **File / lines**: rpi_base.cfg L578-615 (gcode_macro)
- **What it does**: T=heater number S=target: go to the wipe position before waiting for the nozzle on the carriage (in a print only)
- **Calls**: -
- **Called by**: _WAIT_TOOL_TEMPERATURE
- **Variables**: back, ox, oy, min_below, speed, hop, hopped
- **Uses**: reads printer.gcode_move, printer.print_stats, printer.save_variables, printer.toolhead; sets variables of _WM_HEAT_AT_WIPE
- **Commands**: all exist (built-in/module commands used: G0, G1, G90, G91, RESPOND, SAVE_GCODE_STATE, SET_GCODE_VARIABLE) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD  |  **Tags**: wipe  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_HEAT_BACK
- **File / lines**: rpi_base.cfg L616-639 (gcode_macro)
- **What it does**: After the heating: back to where the nozzle was before _WM_HEAT_AT_WIPE moved it
- **Calls**: -
- **Called by**: _WAIT_TOOL_TEMPERATURE
- **Variables**: -
- **Uses**: reads printer.cfg; sets variables of _WM_HEAT_AT_WIPE
- **Commands**: all exist (built-in/module commands used: G0, G1, G90, G91, RESTORE_GCODE_STATE, SET_GCODE_VARIABLE) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD  |  **Tags**: misc  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### z_rise
- **File / lines**: rpi_base.cfg L640-652 (gcode_macro)
- **What it does**: Lowers the bed 5 mm before X/Y moves and homing.
- **Calls**: _z_rise_run
- **Called by**: ACE_WM_LOAD, ACE_WM_UNLOAD, EXTRUDE_FILAMENT, RETRACT_FILAMENT, WIPE_NOZZLE, _LOCK_TOOL, _UNLOCK_TOOL, _WM_ACE_HOME, _WM_ACE_HOME_Z, _WM_GO_WIPE, _WM_GO_WIPE_HEAT, filament_insert_gcode
- **Variables**: -
- **Uses**: reads printer.print_stats
- **Commands**: all exist (built-in/module commands used: QUERY_ENDSTOPS) - checked 2026-11-18
- **Risk**: none (+ through the macros it calls: MOVES THE TOOLHEAD)  |  **Tags**: misc  |  **Fluidd**: none
- **Tested**: no per-macro record in FIX-LOG.md
### _z_rise_run
- **File / lines**: rpi_base.cfg L653-677 (gcode_macro)
- **What it does**: Does the actual z_rise move (treats Z as homed for one move).
- **Calls**: -
- **Called by**: z_rise
- **Variables**: drop
- **Uses**: reads printer.print_stats, printer.query_endstops, printer.toolhead
- **Commands**: all exist (built-in/module commands used: G1, G90, G91, RESPOND, SET_KINEMATIC_POSITION) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD  |  **Tags**: misc  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### Z_HOMING
- **File / lines**: rpi_base.cfg L720-746 (gcode_macro)
- **What it does**: Z homing with the probe/load cell: wipes, positions, G28 Z.
- **Calls**: SET_GCODE_OFFSET, T0, WIPE_NOZZLE, _LEVELING_TRIGGER_S
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: z_raise
- **Uses**: reads printer.print_stats; sets variables of Z_HOMING, _CHANGE_TOOL
- **Commands**: all exist (built-in/module commands used: BED_MESH_CLEAR, G1, G28, M118, M400, SET_GCODE_VARIABLE, STEPPER_DIAG_DISABLE, STEPPER_DIAG_ENABLE) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD (+ through the macros it calls: ACE, HEATS)  |  **Tags**: misc  |  **Fluidd**: WM Ultra Tool Change
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_BED_SOAK_PARAMS
- **File / lines**: rpi_base.cfg L800-817 (gcode_macro)
- **What it does**: Settings of the bed warp wait (edit the values here, then restart Klipper). Like _START_END_PARAMS on the K1
- **Calls**: -
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: bed_warp_wait_multiplier, bed_warp_fraction_wait, bed_warp_wait_interval, bed_warp_no_wait, bed_warp_measured_floor, bed_warp_min_bed
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: RESPOND) - checked 2026-11-18
- **Risk**: none  |  **Tags**: bed  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_BEDWARP
- **File / lines**: rpi_base.cfg L818-837 (gcode_macro)
- **What it does**: State of the bed warp measurement (do not run)
- **Calls**: -
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: running, stop, bed, after_s, start_t, reached, round, z, first, last, hist, points, samples, tol, names
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: RESPOND) - checked 2026-11-18
- **Risk**: none  |  **Tags**: bed  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### WM_BED_WARP_MEASURE
- **File / lines**: rpi_base.cfg L838-849 (gcode_macro)
- **What it does**: Window: measure how the bed moves while it heats (5 spots, 4 touches each, about 20 to 25 min). The measured wait is saved by itself
- **Calls**: -
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: RESPOND) - checked 2026-11-18
- **Risk**: ACE  |  **Tags**: bed  |  **Fluidd**: RPI Calibration
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_BEDWARP_START
- **File / lines**: rpi_base.cfg L850-896 (gcode_macro)
- **What it does**: Starts the bed warp measurement (Start button of WM_BED_WARP_MEASURE)
- **Calls**: SET_GCODE_OFFSET, T0, WIPE_NOZZLE, _WM_BEDWARP_ROUND, _WM_BEDWARP_SETSTART, _WM_CAL_CLEARANCE, _WM_CAL_PRECHECK, _WM_FAIL
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: reads printer.heater_bed, printer.save_variables; sets variables of _WM_BEDWARP
- **Commands**: all exist (built-in/module commands used: BED_MESH_CLEAR, G1, G28, G90, PROBE, RESPOND, SET_GCODE_VARIABLE, SET_HEATER_TEMPERATURE, TEMPERATURE_WAIT, UPDATE_DELAYED_GCODE) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, HEATS (+ through the macros it calls: ACE)  |  **Tags**: bed  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_BEDWARP_SETSTART
- **File / lines**: rpi_base.cfg L897-901 (gcode_macro)
- **What it does**: Keeps the start time of the measurement
- **Calls**: -
- **Called by**: _WM_BEDWARP_START
- **Variables**: -
- **Uses**: reads printer.toolhead; sets variables of _WM_BEDWARP
- **Commands**: all exist (built-in/module commands used: SET_GCODE_VARIABLE) - checked 2026-11-18
- **Risk**: none  |  **Tags**: bed  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_BEDWARP_ROUND
- **File / lines**: rpi_base.cfg L902-916 (gcode_macro)
- **What it does**: One round: 5 touches (centre, front left, front right, back right, back left), then one console line
- **Calls**: _WM_BEDWARP_REPORT, _WM_BEDWARP_STORE
- **Called by**: _WM_BEDWARP_START, _WM_BEDWARP_TICK
- **Variables**: -
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: G1, G90, PROBE) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD  |  **Tags**: bed  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_BEDWARP_STORE
- **File / lines**: rpi_base.cfg L917-928 (gcode_macro)
- **What it does**: Store the last touch height (runs right after PROBE)
- **Calls**: -
- **Called by**: _WM_BEDWARP_ROUND
- **Variables**: -
- **Uses**: reads printer.configfile, printer.probe; sets variables of _WM_BEDWARP
- **Commands**: all exist (built-in/module commands used: SET_GCODE_VARIABLE) - checked 2026-11-18
- **Risk**: none  |  **Tags**: bed  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_BEDWARP_REPORT
- **File / lines**: rpi_base.cfg L929-950 (gcode_macro)
- **What it does**: One console line for the round just done
- **Calls**: -
- **Called by**: _WM_BEDWARP_ROUND
- **Variables**: -
- **Uses**: reads printer.heater_bed, printer.toolhead; sets variables of _WM_BEDWARP
- **Commands**: all exist (built-in/module commands used: RESPOND, SET_GCODE_VARIABLE) - checked 2026-11-18
- **Risk**: none  |  **Tags**: bed  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_BEDWARP_TICK
- **File / lines**: rpi_base.cfg L951-969 (delayed_gcode timer)
- **What it does**: One step of the bed warp wait (measures until the bed is flat).
- **Calls**: _WM_BEDWARP_FINISH, _WM_BEDWARP_ROUND
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: reads printer.heater_bed, printer.toolhead; sets variables of _WM_BEDWARP
- **Commands**: all exist (built-in/module commands used: RESPOND, SET_GCODE_VARIABLE, UPDATE_DELAYED_GCODE) - checked 2026-11-18
- **Risk**: none (+ through the macros it calls: ACE, HEATS, MOVES THE TOOLHEAD)  |  **Tags**: bed  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### WM_BED_WARP_STOP
- **File / lines**: rpi_base.cfg L970-979 (gcode_macro)
- **What it does**: Stops a running bed warp measurement (after the round it is in), heaters off
- **Calls**: -
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: sets variables of _WM_BEDWARP
- **Commands**: all exist (built-in/module commands used: RESPOND, SET_GCODE_VARIABLE) - checked 2026-11-18
- **Risk**: none  |  **Tags**: bed  |  **Fluidd**: RPI Calibration
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_BEDWARP_FINISH
- **File / lines**: rpi_base.cfg L980-1039 (gcode_macro)
- **What it does**: End of the bed warp measurement: heaters off, head up, summary
- **Calls**: _WM_BED_SOAK_STORE
- **Called by**: _WM_BEDWARP_TICK
- **Variables**: -
- **Uses**: sets variables of _WM_BEDWARP
- **Commands**: all exist (built-in/module commands used: G1, G90, RESPOND, SET_GCODE_VARIABLE, SET_HEATER_TEMPERATURE, UPDATE_DELAYED_GCODE) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, HEATS, ACE  |  **Tags**: bed  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_BED_SOAK_STATE
- **File / lines**: rpi_base.cfg L1045-1051 (gcode_macro)
- **What it does**: State of the bed warp wait (do not run)
- **Calls**: -
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: synced, start_bed
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: RESPOND) - checked 2026-11-18
- **Risk**: none  |  **Tags**: bed  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### WM_BED_SOAK_PIN_WATCH
- **File / lines**: rpi_base.cfg L1052-1069 (delayed_gcode timer)
- **What it does**: Keeps the Fluidd switch for the bed soak in sync with the saved choice.
- **Calls**: -
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: reads printer.save_variables; sets variables of _WM_BED_SOAK_STATE; saves wm_bed_soak VALUE
- **Commands**: all exist (built-in/module commands used: RESPOND, SAVE_VARIABLE, SET_GCODE_VARIABLE, SET_PIN, UPDATE_DELAYED_GCODE) - checked 2026-11-18
- **Risk**: none  |  **Tags**: bed  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### WM_BED_SOAK
- **File / lines**: rpi_base.cfg L1070-1107 (gcode_macro)
- **What it does**: Bed warp wait before the bed mesh. WM_BED_SOAK shows the settings, ENABLE=0 or 1 switches it, SECONDS_PER_DEGREE=0.5 to 5 sets the time
- **Calls**: _WM_FAIL
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: reads printer.save_variables; saves wm_bed_soak VALUE, wm_bed_soak_spd VALUE, {k} VALUE
- **Commands**: all exist (built-in/module commands used: RESPOND, SAVE_VARIABLE, SET_PIN) - checked 2026-11-18
- **Risk**: ACE  |  **Tags**: bed  |  **Fluidd**: none
- **Tested**: no per-macro record in FIX-LOG.md
### WM_BED_SOAK_MENU
- **File / lines**: rpi_base.cfg L1108-1135 (gcode_macro)
- **What it does**: Window: bed warp wait on or off, and the bed measurement
- **Calls**: -
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: reads printer.save_variables
- **Commands**: all exist (built-in/module commands used: RESPOND) - checked 2026-11-18
- **Risk**: ACE  |  **Tags**: bed  |  **Fluidd**: RPI Calibration
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_BED_SOAK_STORE
- **File / lines**: rpi_base.cfg L1136-1146 (gcode_macro)
- **What it does**: Saves a measured wait S (seconds) for bed temperature T: the newest run replaces the old value, at least 2 s per degree
- **Calls**: -
- **Called by**: _WM_BEDWARP_FINISH
- **Variables**: -
- **Uses**: reads printer.save_variables; saves wm_bed_soak_t{t} VALUE
- **Commands**: all exist (built-in/module commands used: RESPOND, SAVE_VARIABLE) - checked 2026-11-18
- **Risk**: none  |  **Tags**: bed  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_BED_SOAK_MARK
- **File / lines**: rpi_base.cfg L1147-1151 (gcode_macro)
- **What it does**: Called by START_PRINT before the bed heater is set: keeps the bed temperature at the start of the print
- **Calls**: -
- **Called by**: START_PRINT
- **Variables**: -
- **Uses**: reads printer.heater_bed; sets variables of _WM_BED_SOAK_STATE
- **Commands**: all exist (built-in/module commands used: SET_GCODE_VARIABLE) - checked 2026-11-18
- **Risk**: none  |  **Tags**: bed  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_BED_SOAK
- **File / lines**: rpi_base.cfg L1152-1219 (gcode_macro)
- **What it does**: Called by START_PRINT after M190: waits so the bed plate stops bending before the wipe and the bed mesh
- **Calls**: -
- **Called by**: START_PRINT
- **Variables**: -
- **Uses**: reads printer.heater_bed, printer.save_variables; sets variables of _WM_BED_SOAK_STATE
- **Commands**: all exist (built-in/module commands used: G4, RESPOND, SET_GCODE_VARIABLE) - checked 2026-11-18
- **Risk**: ACE  |  **Tags**: bed  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_PURGE_SETTINGS
- **File / lines**: rpi_base.cfg L1220-1238 (gcode_macro)
- **What it does**: Print start purge settings (item 32): the nine K1 / KAMP line purge settings and the wipe area purge
- **Calls**: -
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: purge_height, tip_distance, purge_margin, purge_amount, flow_rate, smart_park_height, line_purge_z_hop, line_purge_retract, line_purge_retract_speed, wipe_purge_length, wipe_purge_speed, line
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: RESPOND) - checked 2026-11-18
- **Risk**: none  |  **Tags**: purge  |  **Fluidd**: —
- **Tested**: F-105 tested 2026-11-17
### _WM_START_PURGE
- **File / lines**: rpi_base.cfg L1239-1246 (gcode_macro)
- **What it does**: Print start purge (START_PRINT): INITIAL_TOOL= EXTRUDER= [TOOLS=0,2 instead of reading the file]
- **Calls**: _WM_START_PURGE_RUN
- **Called by**: START_PRINT
- **Variables**: -
- **Uses**: reads printer.print_stats
- **Commands**: all exist (built-in/module commands used: WM_PRINT_INFO_READ) - checked 2026-11-18
- **Risk**: none (+ through the macros it calls: ACE, HEATS, MOVES THE TOOLHEAD)  |  **Tags**: purge  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_START_PURGE_RUN
- **File / lines**: rpi_base.cfg L1247-1292 (gcode_macro)
- **What it does**: The purge part of _WM_START_PURGE (runs after WM_PRINT_INFO_READ, use _WM_START_PURGE)
- **Calls**: _CHANGE_TOOL, _WM_LINE_PURGE, _WM_PURGE_HEAT, _WM_WIPE_PURGE
- **Called by**: _WM_START_PURGE
- **Variables**: -
- **Uses**: reads printer.print_stats, printer.save_variables, printer.wm_print_info
- **Commands**: all exist (built-in/module commands used: RESPOND) - checked 2026-11-18
- **Risk**: ACE (+ through the macros it calls: HEATS, MOVES THE TOOLHEAD)  |  **Tags**: purge  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_GO_WIPE
- **File / lines**: rpi_base.cfg L1293-1314 (gcode_macro)
- **What it does**: Moves the tool on the carriage to the wipe position (the saved wipe_position, Y first then X) at clearance height. No heating and no wipe. Does nothing when the head is already there. Used so the nozzle heats where it can drip (F-150)
- **Calls**: _WM_CAL_CLEARANCE, z_rise
- **Called by**: ACE_WM_LOAD, G29, NOZZLE_PREPARE, POP, RESUME, _WM_NOZZLE_PREPARE
- **Variables**: -
- **Uses**: reads printer.save_variables, printer.toolhead
- **Commands**: all exist (built-in/module commands used: G0, G28, G90, M400, RESTORE_GCODE_STATE, SAVE_GCODE_STATE) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD  |  **Tags**: wipe  |  **Fluidd**: —
- **Tested**: F-150 pushed, NOT tested
### _WM_PURGE_HEAT
- **File / lines**: rpi_base.cfg L1315-1331 (gcode_macro)
- **What it does**: Heat toolhead T (real head, not mapped) to S at the wipe position and wait (print start purge)
- **Calls**: _WM_LIVEZ_HEAT
- **Called by**: _WM_START_PURGE_RUN, _WM_WIPE_PURGE_GO
- **Variables**: -
- **Uses**: reads printer.save_variables
- **Commands**: all exist (built-in/module commands used: G0, G1, G90, SET_HEATER_TEMPERATURE, TEMPERATURE_WAIT) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, HEATS (+ through the macros it calls: ACE)  |  **Tags**: purge  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_WIPE_PURGE
- **File / lines**: rpi_base.cfg L1332-1341 (gcode_macro)
- **What it does**: Print start purge of one toolhead: T= (real head) S= temperature LAST=1 keeps the heater on (it prints first)
- **Calls**: _CHANGE_TOOL, _WM_WIPE_PURGE_GO
- **Called by**: _WM_START_PURGE_RUN
- **Variables**: -
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: RESPOND) - checked 2026-11-18
- **Risk**: none (+ through the macros it calls: ACE, HEATS, MOVES THE TOOLHEAD)  |  **Tags**: purge, wipe  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_WIPE_PURGE_GO
- **File / lines**: rpi_base.cfg L1342-1375 (gcode_macro)
- **What it does**: The part of _WM_WIPE_PURGE after the tool change (reads the head sensor of the tool now on the carriage)
- **Calls**: WIPE_NOZZLE, _WM_PURGE_ASSIST, _WM_PURGE_HEAT
- **Called by**: _WM_WIPE_PURGE
- **Variables**: -
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: G1, M400, M83, RESPOND, RESTORE_GCODE_STATE, SAVE_GCODE_STATE, SET_HEATER_TEMPERATURE) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, HEATS, ACE  |  **Tags**: purge, wipe  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_PURGE_ASSIST
- **File / lines**: rpi_base.cfg L1376-1404 (gcode_macro)
- **What it does**: ACE feed assist for the print start purge: T= STATE=on|off (nothing without an ACE)
- **Calls**: -
- **Called by**: _WM_WIPE_PURGE_GO, _WM_ZR_LOAD_GO
- **Variables**: -
- **Uses**: sets variables of _WM_ACE
- **Commands**: all exist (built-in/module commands used: ACE_DISABLE_FEED_ASSIST, ACE_ENABLE_FEED_ASSIST, SET_GCODE_VARIABLE) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, ACE  |  **Tags**: purge  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_LINE_PURGE
- **File / lines**: rpi_base.cfg L1405-1464 (gcode_macro)
- **What it does**: KAMP purge line near the printed parts (print start), settings in _WM_PURGE_SETTINGS
- **Calls**: -
- **Called by**: _WM_START_PURGE_RUN
- **Variables**: -
- **Uses**: reads printer.configfile, printer.exclude_object, printer.toolhead
- **Commands**: all exist (built-in/module commands used: G0, G1, G90, G92, M83, RESPOND, RESTORE_GCODE_STATE, SAVE_GCODE_STATE) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD  |  **Tags**: purge  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md

## rpi_calibration.cfg
Installer part: calibration (first run, Z trim, setter, offsets, PID, shaper, mesh)

### WM_CAL_HELP
- **File / lines**: rpi_calibration.cfg L39-54 (gcode_macro)
- **What it does**: List the Pi calibration macros
- **Calls**: -
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: reads printer.configfile
- **Commands**: all exist (built-in/module commands used: RESPOND) - checked 2026-11-18
- **Risk**: LOAD CELL / SETTER  |  **Tags**: calibration  |  **Fluidd**: RPI Calibration
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_CAL_STOP
- **File / lines**: rpi_calibration.cfg L55-62 (gcode_macro)
- **What it does**: Heaters and fan off (use after an interrupted calibration)
- **Calls**: M106
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: RESPOND, TURN_OFF_HEATERS) - checked 2026-11-18
- **Risk**: none  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_PROMPT_CLOSE
- **File / lines**: rpi_calibration.cfg L63-70 (gcode_macro)
- **What it does**: Close the Fluidd / screen window, then show MSG (used by the window buttons)
- **Calls**: -
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: M118, RESPOND) - checked 2026-11-18
- **Risk**: none  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_SAVE
- **File / lines**: rpi_calibration.cfg L71-76 (gcode_macro)
- **What it does**: Close the Fluidd / screen window, then SAVE_CONFIG (Klipper restarts)
- **Calls**: -
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: RESPOND, SAVE_CONFIG) - checked 2026-11-18
- **Risk**: none  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_FAIL
- **File / lines**: rpi_calibration.cfg L77-81 (gcode_macro)
- **What it does**: Stop a macro with an error AFTER its window was closed (action_raise_error inside the macro text runs before any line of it)
- **Calls**: -
- **Called by**: WM_AUTO_SPEED_VALIDATE, WM_BED_SOAK, WM_NOZZLE_FULL_PID, WM_NOZZLE_GROWTH_CAL, WM_OFFSETS_ACCURATE, WM_SCREWS_CAL, WM_SETTER_PROBE_POSITION, _WM_AUTO_SPEED_RESTART, _WM_AUTO_SPEED_RESULT, _WM_AUTO_SPEED_RUN, _WM_AUTO_SPEED_SAVE, _WM_BEDWARP_START, _WM_CAL_PRECHECK, _WM_NOZZLE_FULL_PID_RESULT, _WM_NOZZLE_PREPARE, _WM_OFFSET_CHECK, _WM_SETTER_AUTO_CHECK, _WM_SETTER_AUTO_FINISH, _WM_SETTER_DOWN, _WM_SETTER_FIND, _WM_SETTER_FIND_FAIL, _WM_SETTER_FOUND, _WM_SETTER_GO, _WM_SETTER_MID, _WM_SETTER_MID_SAVE, _WM_SETTER_MOVE, _WM_SETTER_RESTORE, _WM_SETTER_SAVE, _WM_SETTER_SCRATCH_GO, _WM_SETTER_STEP, _WM_SETTER_WIN, _WM_ZCAL_RUN, _WM_ZCAL_WIN, _WM_Z_TOUCH, _WM_Z_TRIM_STEP, _WM_Z_TRIM_WIN
- **Variables**: -
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: none) - checked 2026-11-18
- **Risk**: none  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_CAL_PRECHECK
- **File / lines**: rpi_calibration.cfg L82-99 (gcode_macro)
- **What it does**: Stop unless the printer is idle and every heater is off (ALLOW_BED=1 lets the bed be warm)
- **Calls**: _WM_FAIL
- **Called by**: WM_BED_LEVELING, WM_BED_PID, WM_FIRST_RUN_CAL, WM_NOZZLE_FULL_PID, WM_NOZZLE_GROWTH_CAL, WM_OFFSETS_ACCURATE, WM_OFFSETS_RAPID, WM_OFFSETS_Z_HOT, WM_PROBE_CALIBRATE, WM_SCREWS_CAL, WM_VIBRATION_COMP, _WM_AUTO_SPEED_READY, _WM_BEDWARP_START, _WM_FIRST_RUN_CAL, _WM_SETTER_GO, _WM_SETTER_TEST
- **Variables**: -
- **Uses**: reads printer.heaters, printer.print_stats, printer.save_variables
- **Commands**: all exist (built-in/module commands used: RESPOND) - checked 2026-11-18
- **Risk**: none  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_CAL_ASK
- **File / lines**: rpi_calibration.cfg L100-147 (gcode_macro)
- **What it does**: Show the Start / Cancel window in Fluidd for one stage (STAGE=level|probe|offsets|screws|shaper|bedpid|pid)
- **Calls**: -
- **Called by**: WM_BED_LEVELING, WM_BED_PID, WM_OFFSETS_ACCURATE, WM_OFFSETS_RAPID, WM_PROBE_CALIBRATE, WM_SCREWS_CAL, WM_VIBRATION_COMP
- **Variables**: -
- **Uses**: reads printer.configfile
- **Commands**: all exist (built-in/module commands used: RESPOND) - checked 2026-11-18
- **Risk**: LOAD CELL / SETTER  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### WM_BED_LEVELING
- **File / lines**: rpi_calibration.cfg L148-173 (gcode_macro)
- **What it does**: App "Bed Leveling": G29 (full mesh, probe_count of [bed_mesh]), then save
- **Calls**: G29, _WM_CAL_ASK, _WM_CAL_PRECHECK
- **Called by**: _WM_FIRST_RUN_CAL
- **Variables**: -
- **Uses**: reads printer.configfile, printer.toolhead
- **Commands**: all exist (built-in/module commands used: G28, RESPOND, SAVE_CONFIG, TURN_OFF_HEATERS) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD (+ through the macros it calls: ACE, HEATS, LOAD CELL / SETTER)  |  **Tags**: bed, calibration  |  **Fluidd**: RPI Calibration
- **Tested**: no per-macro record in FIX-LOG.md
### WM_SCREWS_CAL
- **File / lines**: rpi_calibration.cfg L174-204 (gcode_macro)
- **What it does**: Bed screws: heats, wipes, then SCREWS_TILT_CALCULATE probes the four bed screws and prints how far to turn each one. Run it again until every screw says 00:00
- **Calls**: M104, M109, M190, T0, WIPE_NOZZLE, _WM_CAL_ASK, _WM_CAL_PRECHECK, _WM_FAIL
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: reads printer.cfg, printer.configfile, printer.save_variables
- **Commands**: all exist (built-in/module commands used: G1, G28, M140, RESPOND, SCREWS_TILT_CALCULATE, TURN_OFF_HEATERS) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, HEATS (+ through the macros it calls: ACE, LOAD CELL / SETTER)  |  **Tags**: calibration  |  **Fluidd**: RPI Calibration
- **Tested**: no per-macro record in FIX-LOG.md
### WM_PROBE_CALIBRATE
- **File / lines**: rpi_calibration.cfg L205-222 (gcode_macro)
- **What it does**: App "PROBE_CALIBRATE": warm the bed, then WonderMaker's PROBE_CALIBRATE; you finish with TESTZ / ACCEPT
- **Calls**: M190, PROBE_CALIBRATE, _WM_CAL_ASK, _WM_CAL_PRECHECK
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: RESPOND) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, HEATS (+ through the macros it calls: LOAD CELL / SETTER)  |  **Tags**: calibration  |  **Fluidd**: RPI Calibration
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_PROBE_DONE
- **File / lines**: rpi_calibration.cfg L223-234 (gcode_macro)
- **What it does**: After ACCEPT: bed off, then save (SAVE=0 to skip the save)
- **Calls**: -
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: M140, RESPOND, SAVE_CONFIG) - checked 2026-11-18
- **Risk**: HEATS  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_OFFSET_CHECK
- **File / lines**: rpi_calibration.cfg L235-258 (gcode_macro)
- **What it does**: After RAPID_MODE of one tool (T, OX OY OZ = the offsets saved when the run started, KEEPZ, LIMIT): keep the hot Z, stop and put the old values back when X or Y moved more than LIMIT
- **Calls**: M106, SAVE_T_OFFSET, _WM_FAIL
- **Called by**: WM_OFFSETS_ACCURATE, WM_OFFSETS_RAPID
- **Variables**: -
- **Uses**: reads printer.save_variables
- **Commands**: all exist (built-in/module commands used: RESPOND, TURN_OFF_HEATERS) - checked 2026-11-18
- **Risk**: none  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### WM_OFFSETS_RAPID
- **File / lines**: rpi_calibration.cfg L259-335 (gcode_macro)
- **What it does**: App "Extruder Offsets Calibration" - Rapid: G28, then for every tool a nozzle clean at the wipe area (220 C, retract, drip, wipes, part fan, below 100 C) and RAPID_MODE, then PARK_CURRENT_TOOL
- **Calls**: M106, PARK_CURRENT_TOOL, RAPID_MODE, WIPE_NOZZLE, _WM_CAL_ASK, _WM_CAL_CLEARANCE, _WM_CAL_PRECHECK, _WM_OFFSET_CHECK, _WM_WAIT_TEMP
- **Called by**: _WM_FIRST_RUN_CAL, _WM_SETTER_FIND_DONE, _WM_SETTER_RAPID
- **Variables**: clean, clean_temp, retract_mm, drip_s, wipes, soft_wipe, touch_max, xy_limit
- **Uses**: reads printer.save_variables, printer.toolhead
- **Commands**: all exist (built-in/module commands used: G0, G1, G28, G4, G90, M400, M83, RESPOND, RESTORE_GCODE_STATE, SAVE_GCODE_STATE, SET_HEATER_TEMPERATURE, TURN_OFF_HEATERS) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, HEATS (+ through the macros it calls: ACE, LOAD CELL / SETTER)  |  **Tags**: calibration  |  **Fluidd**: RPI Calibration
- **Tested**: rapid offsets tested 2026-11-17 (240 touches, 0 retries)
### WM_OFFSETS_ACCURATE
- **File / lines**: rpi_calibration.cfg L336-424 (gcode_macro)
- **What it does**: App "Extruder Offsets Calibration" - Accurate (TEMP=220). Per tool NOZZLE_PREPARE, you remove the purged debris and click OK, NOZZLE_CALIBRATE_TOOL_OFFSET; then RAPID_MODE for every tool
- **Calls**: NOZZLE_CALIBRATE_TOOL_OFFSET, PARK_CURRENT_TOOL, RAPID_MODE, _WM_CAL_ASK, _WM_CAL_PRECHECK, _WM_FAIL, _WM_NOZZLE_PREPARE, _WM_OFFSET_CHECK, _WM_ZCAL_AFTER_ACCURATE
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: xy_limit
- **Uses**: reads printer.print_stats, printer.save_variables, printer.toolhead
- **Commands**: all exist (built-in/module commands used: G28, M400, RESPOND, SET_HEATER_TEMPERATURE, TURN_OFF_HEATERS) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, HEATS (+ through the macros it calls: ACE, LOAD CELL / SETTER)  |  **Tags**: calibration  |  **Fluidd**: RPI Calibration
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_NOZZLE_PREPARE
- **File / lines**: rpi_calibration.cfg L425-472 (gcode_macro)
- **What it does**: Nozzle preparation for WM_OFFSETS_ACCURATE (S=hot temperature, T=tool). The factory NOZZLE_PREPARE steps, with the ACE feed assist on during the button purge when an ACE is present.
- **Calls**: M104, M106, M109, SET_GCODE_OFFSET, _APPLY_PRE_Z_OFFSET, _WM_FAIL, _WM_GO_WIPE
- **Called by**: WM_OFFSETS_ACCURATE
- **Variables**: -
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: ACE_DISABLE_FEED_ASSIST, ACE_ENABLE_FEED_ASSIST, G1, G28, G90, G91, G92, M400, PROBE, RESTORE_GCODE_STATE, SAVE_GCODE_STATE) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, HEATS, ACE  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### WM_VIBRATION_COMP
- **File / lines**: rpi_calibration.cfg L473-499 (gcode_macro)
- **What it does**: App "Vibration Compensation": input shaper test (needs the lis2dw accelerometer on the EX_T board)
- **Calls**: _WM_CAL_ASK, _WM_CAL_PRECHECK
- **Called by**: _WM_AUTO_SPEED_SHAPER, _WM_FIRST_RUN_CAL
- **Variables**: -
- **Uses**: reads printer.toolhead
- **Commands**: all exist (built-in/module commands used: COLLISION_DETECT_DISABLE, G28, M400, RESPOND, SAVE_CONFIG, SHAPER_CALIBRATE) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD (+ through the macros it calls: LOAD CELL / SETTER)  |  **Tags**: calibration  |  **Fluidd**: RPI Calibration
- **Tested**: no per-macro record in FIX-LOG.md
### WM_NOZZLE_FULL_PID
- **File / lines**: rpi_calibration.cfg L500-640 (gcode_macro)
- **What it does**: Hotend PID of all four tool heads (or one) one after the other, each at the wipe position, then heated back and wiped, cooled to 140 C and wiped again. Windows ask the temperature (210 to 280), the fan speed (30, 50, 70, 100) and the head, then one Save and Restart at the end
- **Calls**: M106, PARK_CURRENT_TOOL, _WM_CAL_PRECHECK, _WM_FAIL, _WM_NOZZLE_FULL_PID_RESULT, _WM_PID_HEAD
- **Called by**: _WM_FIRST_RUN_CAL
- **Variables**: -
- **Uses**: reads printer.cfg, printer.configfile, printer.heaters, printer.toolhead
- **Commands**: all exist (built-in/module commands used: G28, RESPOND, TURN_OFF_HEATERS) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD (+ through the macros it calls: ACE, HEATS)  |  **Tags**: calibration  |  **Fluidd**: RPI Calibration
- **Tested**: F-147 pushed, NOT tested
### _WM_PID_HEAD
- **File / lines**: rpi_calibration.cfg L641-666 (gcode_macro)
- **What it does**: One hotend PID run of WM_NOZZLE_FULL_PID - pick up the tool, tune at the wipe position, heat back to the target and wipe, cool to 140 C and wipe a second time
- **Calls**: M106, WIPE_NOZZLE, _WM_CAL_CLEARANCE
- **Called by**: WM_NOZZLE_FULL_PID
- **Variables**: -
- **Uses**: reads printer.save_variables
- **Commands**: all exist (built-in/module commands used: G0, G90, PID_CALIBRATE, RESPOND, SET_HEATER_TEMPERATURE, TEMPERATURE_WAIT) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, HEATS  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_NOZZLE_FULL_PID_RESULT
- **File / lines**: rpi_calibration.cfg L667-695 (gcode_macro)
- **What it does**: Show the new hotend PID values that wait to be saved (also after a stopped run), with Save and Restart / Discard
- **Calls**: _WM_FAIL
- **Called by**: WM_NOZZLE_FULL_PID
- **Variables**: -
- **Uses**: reads printer.configfile
- **Commands**: all exist (built-in/module commands used: RESPOND) - checked 2026-11-18
- **Risk**: none  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### WM_BED_PID
- **File / lines**: rpi_calibration.cfg L696-733 (gcode_macro)
- **What it does**: Heated bed PID (PID_CALIBRATE HEATER=heater_bed). TARGET=60 (40 to 110). Only if the bed uses control: pid
- **Calls**: _WM_CAL_ASK, _WM_CAL_PRECHECK
- **Called by**: _WM_FIRST_RUN_CAL
- **Variables**: -
- **Uses**: reads printer.cfg, printer.configfile, printer.heaters, printer.toolhead
- **Commands**: all exist (built-in/module commands used: G28, PID_CALIBRATE, RESPOND, SAVE_CONFIG, TURN_OFF_HEATERS) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, HEATS (+ through the macros it calls: LOAD CELL / SETTER)  |  **Tags**: bed, calibration  |  **Fluidd**: RPI Calibration
- **Tested**: no per-macro record in FIX-LOG.md
### WM_FIRST_RUN_CAL
- **File / lines**: rpi_calibration.cfg L734-761 (gcode_macro)
- **What it does**: One click calibration of the Pi: tool setter position, tool offsets, hot Z offsets, input shaper, bed PID, bed mesh, nozzle PID. Explains it in a Fluidd window first
- **Calls**: _WM_CAL_PRECHECK
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: reads printer.configfile, printer.heaters, printer.toolhead
- **Commands**: all exist (built-in/module commands used: RESPOND) - checked 2026-11-18
- **Risk**: LOAD CELL / SETTER  |  **Tags**: calibration  |  **Fluidd**: RPI Calibration
- **Tested**: F-143 pushed (2.21.0), NOT tested on the printer
### _WM_FIRST_RUN_CAL
- **File / lines**: rpi_calibration.cfg L762-793 (gcode_macro)
- **What it does**: The work of WM_FIRST_RUN_CAL (use WM_FIRST_RUN_CAL instead, it asks first). Seven stages (stage 2 runs with XYLIMIT=3: the saved offsets of a new install come from the repo, so only a gross error stops it): setter position, offsets and hot Z are saved as they finish (no restart); shaper, bed PID, bed mesh and hotend PID are saved by the one Save and Restart window at the end
- **Calls**: M106, WM_BED_LEVELING, WM_BED_PID, WM_NOZZLE_FULL_PID, WM_OFFSETS_RAPID, WM_OFFSETS_Z_HOT, WM_VIBRATION_COMP, _WM_CAL_PRECHECK, _WM_FIRST_RUN_CAL_DONE, _WM_SETTER_AUTO
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: reads printer.configfile
- **Commands**: all exist (built-in/module commands used: RESPOND, TURN_OFF_HEATERS) - checked 2026-11-18
- **Risk**: LOAD CELL / SETTER (+ through the macros it calls: ACE, HEATS, MOVES THE TOOLHEAD)  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: F-143/F-148 pushed (2.21.0), NOT tested on the printer
### _WM_FIRST_RUN_CAL_DONE
- **File / lines**: rpi_calibration.cfg L794-888 (gcode_macro)
- **What it does**: Window shown when WM_FIRST_RUN_CAL has finished: the result of every test, then Save and Restart / Not now
- **Calls**: -
- **Called by**: _WM_FIRST_RUN_CAL
- **Variables**: done_t
- **Uses**: reads printer.configfile, printer.save_variables, printer.toolhead; sets variables of _WM_FIRST_RUN_CAL_DONE
- **Commands**: all exist (built-in/module commands used: RESPOND, SET_GCODE_VARIABLE) - checked 2026-11-18
- **Risk**: ACE, LOAD CELL / SETTER  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_ZHOT
- **File / lines**: rpi_calibration.cfg L889-909 (gcode_macro)
- **What it does**: Settings and memory of WM_OFFSETS_Z_HOT and WM_NOZZLE_GROWTH_CAL (nothing to run here)
- **Calls**: -
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: z, g, temp, bed, samples, soak_s, max_drift, drip_s, wipes, retract_mm, warmup, hot_ok, growth_ok, chain
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: RESPOND) - checked 2026-11-18
- **Risk**: none  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### WM_Z_TRIM
- **File / lines**: rpi_calibration.cfg L910-930 (gcode_macro)
- **What it does**: WM_Z_TRIM T=0-3 Z=mm - saved first layer fine adjustment of one tool. Plus is further from the bed. Without Z it shows the four values
- **Calls**: _WM_Z_TRIM_APPLY
- **Called by**: _WM_Z_TRIM_STEP
- **Variables**: -
- **Uses**: reads printer.save_variables; saves wm_z_trim_t{t} VALUE
- **Commands**: all exist (built-in/module commands used: RESPOND, SAVE_VARIABLE) - checked 2026-11-18
- **Risk**: none (+ through the macros it calls: ACE, HEATS, MOVES THE TOOLHEAD)  |  **Tags**: calibration  |  **Fluidd**: RPI Calibration
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_Z_TRIM_MIGRATE
- **File / lines**: rpi_calibration.cfg L931-944 (delayed_gcode timer)
- **What it does**: One-time migration of saved Z trim variables.
- **Calls**: -
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: reads printer.save_variables; saves wm_z_trim_all VALUE, wm_z_trim_t{t} VALUE
- **Commands**: all exist (built-in/module commands used: RESPOND, SAVE_VARIABLE) - checked 2026-11-18
- **Risk**: none  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_Z_TRIM_APPLY
- **File / lines**: rpi_calibration.cfg L945-953 (gcode_macro)
- **What it does**: Put the offsets of the tool on the carriage in place again (after a trim or growth value changed)
- **Calls**: _OFFSET_SET
- **Called by**: RESUME, WM_LIVE_Z_ZERO, WM_NOZZLE_GROWTH, WM_Z_TRIM, _WM_GROWTH_PIN_SYNC, _WM_LIVEZ_DROP, _WM_LIVEZ_SAVE, _WM_Z_TRIM_RESET
- **Variables**: -
- **Uses**: reads printer.save_variables, printer.toolhead
- **Commands**: all exist (built-in/module commands used: none) - checked 2026-11-18
- **Risk**: none (+ through the macros it calls: ACE, HEATS, MOVES THE TOOLHEAD)  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### WM_Z_TRIM_MENU
- **File / lines**: rpi_calibration.cfg L954-973 (gcode_macro)
- **What it does**: Window to set the saved Z trims with buttons: shows the four values, you pick a tool, then Closer / Further
- **Calls**: -
- **Called by**: _WM_Z_TRIM_RESET
- **Variables**: -
- **Uses**: reads printer.save_variables
- **Commands**: all exist (built-in/module commands used: RESPOND) - checked 2026-11-18
- **Risk**: none  |  **Tags**: calibration  |  **Fluidd**: RPI Calibration
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_Z_TRIM_WIN
- **File / lines**: rpi_calibration.cfg L974-1018 (gcode_macro)
- **What it does**: Second window of WM_Z_TRIM_MENU: Closer / Further buttons for TARGET=0 to 3
- **Calls**: _WM_FAIL
- **Called by**: _WM_Z_TRIM_STEP
- **Variables**: -
- **Uses**: reads printer.save_variables, printer.toolhead
- **Commands**: all exist (built-in/module commands used: RESPOND) - checked 2026-11-18
- **Risk**: none  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_Z_TRIM_STEP
- **File / lines**: rpi_calibration.cfg L1019-1037 (gcode_macro)
- **What it does**: Button of the Z trim window: add D to the trim of TARGET (or ZERO=1), save it with WM_Z_TRIM, open the window again
- **Calls**: WM_Z_TRIM, _WM_FAIL, _WM_Z_TRIM_WIN
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: reads printer.save_variables
- **Commands**: all exist (built-in/module commands used: RESPOND) - checked 2026-11-18
- **Risk**: none (+ through the macros it calls: ACE, HEATS, MOVES THE TOOLHEAD)  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_Z_TRIM_RESET
- **File / lines**: rpi_calibration.cfg L1038-1058 (gcode_macro)
- **What it does**: Button of the Z trim window: asks first, with CONFIRM=1 sets the four tool trims to 0
- **Calls**: WM_Z_TRIM_MENU, _WM_Z_TRIM_APPLY
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: saves wm_z_trim_t{t} VALUE
- **Commands**: all exist (built-in/module commands used: RESPOND, SAVE_VARIABLE) - checked 2026-11-18
- **Risk**: none (+ through the macros it calls: ACE, HEATS, MOVES THE TOOLHEAD)  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### WM_NOZZLE_GROWTH
- **File / lines**: rpi_calibration.cfg L1059-1084 (gcode_macro)
- **What it does**: WM_NOZZLE_GROWTH [VALUE=mm per degree] - nozzle heat growth correction. 0 switches it off. Without VALUE it shows the value
- **Calls**: _WM_GROWTH_PIN_SET, _WM_Z_TRIM_APPLY
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: reads printer.save_variables; saves wm_nozzle_growth VALUE, wm_nozzle_growth_meas VALUE
- **Commands**: all exist (built-in/module commands used: RESPOND, SAVE_VARIABLE) - checked 2026-11-18
- **Risk**: ACE (+ through the macros it calls: HEATS, MOVES THE TOOLHEAD)  |  **Tags**: calibration  |  **Fluidd**: RPI Calibration
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_GROWTH_PIN
- **File / lines**: rpi_calibration.cfg L1090-1095 (gcode_macro)
- **What it does**: Memory of the Nozzle Heat Growth switch (nothing to run here)
- **Calls**: -
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: synced
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: RESPOND) - checked 2026-11-18
- **Risk**: none  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_GROWTH_PIN_SET
- **File / lines**: rpi_calibration.cfg L1096-1103 (gcode_macro)
- **What it does**: Put the Nozzle Heat Growth switch at VALUE (used by the macros that change the correction)
- **Calls**: -
- **Called by**: WM_NOZZLE_GROWTH, _WM_GROWTH_PIN_SYNC, _WM_GROWTH_RESULT
- **Variables**: -
- **Uses**: sets variables of _WM_GROWTH_PIN
- **Commands**: all exist (built-in/module commands used: SET_GCODE_VARIABLE, SET_PIN) - checked 2026-11-18
- **Risk**: none  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_GROWTH_PIN_SYNC
- **File / lines**: rpi_calibration.cfg L1104-1129 (gcode_macro)
- **What it does**: Follow the Nozzle Heat Growth switch: at start-up the switch gets the saved state, later a change of the switch turns the correction on or off
- **Calls**: _WM_GROWTH_PIN_SET, _WM_Z_TRIM_APPLY
- **Called by**: WM_GROWTH_PIN_WATCH
- **Variables**: -
- **Uses**: reads printer.save_variables; saves wm_nozzle_growth VALUE, wm_nozzle_growth_meas VALUE
- **Commands**: all exist (built-in/module commands used: RESPOND, SAVE_VARIABLE) - checked 2026-11-18
- **Risk**: none (+ through the macros it calls: ACE, HEATS, MOVES THE TOOLHEAD)  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### WM_GROWTH_PIN_WATCH
- **File / lines**: rpi_calibration.cfg L1130-1142 (delayed_gcode timer)
- **What it does**: Keeps the nozzle growth switch in sync with the saved state.
- **Calls**: _WM_GROWTH_PIN_SYNC
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: reads printer.save_variables
- **Commands**: all exist (built-in/module commands used: UPDATE_DELAYED_GCODE) - checked 2026-11-18
- **Risk**: none (+ through the macros it calls: ACE, HEATS, MOVES THE TOOLHEAD)  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_WAIT_TEMP
- **File / lines**: rpi_calibration.cfg L1143-1156 (gcode_macro)
- **What it does**: Quiet wait until a heater is between MINIMUM and MAXIMUM, with a console line every 30 s (NAME at x C, waiting for TARGET C). Used by the Z calibrations
- **Calls**: _WM_WAIT_TEMP_STEP
- **Called by**: WM_NOZZLE_GROWTH_CAL, WM_OFFSETS_RAPID, WM_OFFSETS_Z_HOT, _WM_Z_TOUCH
- **Variables**: -
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: TEMPERATURE_WAIT) - checked 2026-11-18
- **Risk**: HEATS  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_WAIT_TEMP_STEP
- **File / lines**: rpi_calibration.cfg L1157-1171 (gcode_macro)
- **What it does**: One 5 s step of _WM_WAIT_TEMP (nothing to run here)
- **Calls**: -
- **Called by**: _WM_WAIT_TEMP
- **Variables**: -
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: G4, RESPOND) - checked 2026-11-18
- **Risk**: none  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_Z_TOUCH
- **File / lines**: rpi_calibration.cfg L1172-1267 (gcode_macro)
- **What it does**: Tool T goes to the wipe spot and is brought to TEMP there, is wiped, touches the bed centre, and the height is stored in list LIST slot SLOT. DRIP=1 lets the nozzle drip at the wipe spot first and wipes once more while cooling, PULL=1 pulls loaded filament back at a hot step, PUSH=1 puts it back after the touch
- **Calls**: M106, SET_GCODE_OFFSET, WIPE_NOZZLE, _OFFSET_SET, _WM_CAL_CLEARANCE, _WM_FAIL, _WM_WAIT_TEMP, _WM_Z_TOUCH_STORE
- **Called by**: WM_NOZZLE_GROWTH_CAL, WM_OFFSETS_Z_HOT
- **Variables**: -
- **Uses**: reads printer.save_variables
- **Commands**: all exist (built-in/module commands used: BED_MESH_CLEAR, G0, G1, G4, G90, M400, M83, PROBE, RESPOND, RESTORE_GCODE_STATE, SAVE_GCODE_STATE, SET_HEATER_TEMPERATURE, TURN_OFF_HEATERS) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, HEATS, ACE  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_Z_TOUCH_STORE
- **File / lines**: rpi_calibration.cfg L1268-1283 (gcode_macro)
- **What it does**: Store the last touch height (runs right after PROBE)
- **Calls**: -
- **Called by**: _WM_Z_TOUCH
- **Variables**: -
- **Uses**: reads printer.configfile, printer.probe; sets variables of _WM_ZHOT
- **Commands**: all exist (built-in/module commands used: RESPOND, SET_GCODE_VARIABLE) - checked 2026-11-18
- **Risk**: none  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### WM_OFFSETS_Z_HOT
- **File / lines**: rpi_calibration.cfg L1284-1330 (gcode_macro)
- **What it does**: Z offset of every tool head measured hot: nozzle at 140 C, wiped, several touches, bed warm, T0 first and last. Replaces only the Z numbers
- **Calls**: M106, M190, PARK_CURRENT_TOOL, _CHANGE_TOOL, _WM_CAL_PRECHECK, _WM_WAIT_TEMP, _WM_ZHOT_RESULT, _WM_Z_TOUCH
- **Called by**: _WM_FIRST_RUN_CAL, _WM_ZCAL_RUN
- **Variables**: -
- **Uses**: reads printer.save_variables, printer.toolhead; sets variables of _WM_ZHOT
- **Commands**: all exist (built-in/module commands used: G28, M140, M400, RESPOND, SET_GCODE_VARIABLE, TURN_OFF_HEATERS) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, HEATS, ACE  |  **Tags**: calibration  |  **Fluidd**: RPI Calibration
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_ZHOT_RESULT
- **File / lines**: rpi_calibration.cfg L1331-1368 (gcode_macro)
- **What it does**: Last step of WM_OFFSETS_Z_HOT: check the touches and save the Z offsets
- **Calls**: SAVE_T_OFFSET
- **Called by**: WM_OFFSETS_Z_HOT
- **Variables**: -
- **Uses**: reads printer.save_variables; sets variables of _WM_ZHOT; saves wm_hot_z_done VALUE
- **Commands**: all exist (built-in/module commands used: RESPOND, SAVE_VARIABLE, SET_GCODE_VARIABLE) - checked 2026-11-18
- **Risk**: ACE  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### WM_NOZZLE_GROWTH_CAL
- **File / lines**: rpi_calibration.cfg L1369-1420 (gcode_macro)
- **What it does**: One time: measure how much a nozzle grows with heat. WM_NOZZLE_GROWTH_CAL [T=0] [HOT=250]. Touches hot, at 140 C, hot again, then switches the correction on
- **Calls**: M106, M190, PARK_CURRENT_TOOL, _CHANGE_TOOL, _WM_CAL_PRECHECK, _WM_FAIL, _WM_GROWTH_RESULT, _WM_WAIT_TEMP, _WM_Z_TOUCH
- **Called by**: _WM_ZCAL_RUN
- **Variables**: -
- **Uses**: reads printer.toolhead; sets variables of _WM_ZHOT
- **Commands**: all exist (built-in/module commands used: G28, M140, M400, RESPOND, SET_GCODE_VARIABLE, TURN_OFF_HEATERS) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, HEATS (+ through the macros it calls: ACE)  |  **Tags**: calibration  |  **Fluidd**: RPI Calibration
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_GROWTH_RESULT
- **File / lines**: rpi_calibration.cfg L1421-1450 (gcode_macro)
- **What it does**: Last step of WM_NOZZLE_GROWTH_CAL: check the touches and save the growth value
- **Calls**: _WM_GROWTH_PIN_SET
- **Called by**: WM_NOZZLE_GROWTH_CAL
- **Variables**: -
- **Uses**: sets variables of _WM_ZHOT; saves wm_nozzle_growth VALUE, wm_nozzle_growth_meas VALUE, wm_z_ref_temp VALUE
- **Commands**: all exist (built-in/module commands used: RESPOND, SAVE_VARIABLE, SET_GCODE_VARIABLE) - checked 2026-11-18
- **Risk**: none  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### WM_FULL_OFFSET_CAL
- **File / lines**: rpi_calibration.cfg L1451-1483 (gcode_macro)
- **What it does**: Guided offset calibration in windows: step 1 X and Y offsets with clean nozzles (WM_OFFSETS_ACCURATE), step 2 hot Z offsets, step 3 nozzle heat growth. After it you print a first layer test and adjust the Z trim
- **Calls**: -
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: reads printer.save_variables; sets variables of _WM_ZHOT
- **Commands**: all exist (built-in/module commands used: RESPOND, SET_GCODE_VARIABLE) - checked 2026-11-18
- **Risk**: ACE, LOAD CELL / SETTER  |  **Tags**: calibration  |  **Fluidd**: RPI Calibration
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_ZCAL_WIN
- **File / lines**: rpi_calibration.cfg L1484-1563 (gcode_macro)
- **What it does**: Window of one step of WM_FULL_OFFSET_CAL (STEP=1 to 3, 4 is what comes after): what it does, how to, Start
- **Calls**: _WM_FAIL
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: reads printer.save_variables; sets variables of _WM_ZHOT
- **Commands**: all exist (built-in/module commands used: RESPOND, SET_GCODE_VARIABLE) - checked 2026-11-18
- **Risk**: ACE, LOAD CELL / SETTER  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_ZCAL_RUN
- **File / lines**: rpi_calibration.cfg L1564-1586 (gcode_macro)
- **What it does**: Start button of WM_FULL_OFFSET_CAL: runs step 1 (WM_OFFSETS_ACCURATE), step 2 (WM_OFFSETS_Z_HOT) or step 3 (WM_NOZZLE_GROWTH_CAL), then the result window
- **Calls**: WM_NOZZLE_GROWTH_CAL, WM_OFFSETS_Z_HOT, _WM_FAIL, _WM_SETTER_GO, _WM_ZCAL_DONE
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: sets variables of _WM_SETTER, _WM_ZHOT
- **Commands**: all exist (built-in/module commands used: RESPOND, SET_GCODE_VARIABLE) - checked 2026-11-18
- **Risk**: LOAD CELL / SETTER (+ through the macros it calls: ACE, HEATS, MOVES THE TOOLHEAD)  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_ZCAL_AFTER_ACCURATE
- **File / lines**: rpi_calibration.cfg L1587-1594 (gcode_macro)
- **What it does**: Called at the very end of WM_OFFSETS_ACCURATE: when it was started from WM_FULL_OFFSET_CAL it opens the result window of step 1, otherwise it does nothing
- **Calls**: _WM_ZCAL_DONE
- **Called by**: WM_OFFSETS_ACCURATE
- **Variables**: -
- **Uses**: sets variables of _WM_ZHOT
- **Commands**: all exist (built-in/module commands used: SET_GCODE_VARIABLE) - checked 2026-11-18
- **Risk**: none (+ through the macros it calls: ACE, HEATS, LOAD CELL / SETTER)  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_ZCAL_DONE
- **File / lines**: rpi_calibration.cfg L1595-1686 (gcode_macro)
- **What it does**: Result window of WM_FULL_OFFSET_CAL after step 1, 2 or 3: saved or not, the new values, Repeat or Next
- **Calls**: -
- **Called by**: _WM_SETTER_DOWN, _WM_SETTER_FIND_DONE, _WM_SETTER_FIND_FAIL, _WM_ZCAL_AFTER_ACCURATE, _WM_ZCAL_RUN
- **Variables**: -
- **Uses**: reads printer.save_variables
- **Commands**: all exist (built-in/module commands used: RESPOND) - checked 2026-11-18
- **Risk**: HEATS, ACE, LOAD CELL / SETTER  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_LIVEZ
- **File / lines**: rpi_calibration.cfg L1687-1699 (gcode_macro)
- **What it does**: Memory of the live Z adjust of each tool during a print (nothing to run here)
- **Calls**: -
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: l0, l1, l2, l3, show, heat_t, asked, limit
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: RESPOND) - checked 2026-11-18
- **Risk**: none  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_LIVEZ_SGO
- **File / lines**: rpi_calibration.cfg L1700-1723 (gcode_macro)
- **What it does**: Called by SET_GCODE_OFFSET with the same parameters. Keeps a Z_ADJUST in the live adjust of the tool on the carriage. In a print a plain Z=0 zeroes only that live adjust
- **Calls**: WM_LIVE_Z_ZERO
- **Called by**: SET_GCODE_OFFSET
- **Variables**: -
- **Uses**: reads printer.print_stats, printer.save_variables, printer.toolhead; sets variables of _WM_LIVEZ
- **Commands**: all exist (built-in/module commands used: RESPOND, SET_GCODE_VARIABLE, _WM_SET_GCODE_OFFSET) - checked 2026-11-18
- **Risk**: ACE (+ through the macros it calls: HEATS, MOVES THE TOOLHEAD)  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### WM_LIVE_Z_ZERO
- **File / lines**: rpi_calibration.cfg L1724-1736 (gcode_macro)
- **What it does**: Set the live Z adjust of the tool on the carriage to 0. Tool offset, Z trim and heat growth stay
- **Calls**: _WM_Z_TRIM_APPLY
- **Called by**: _WM_LIVEZ_SGO
- **Variables**: -
- **Uses**: reads printer.save_variables; sets variables of _WM_LIVEZ
- **Commands**: all exist (built-in/module commands used: RESPOND, SET_GCODE_VARIABLE) - checked 2026-11-18
- **Risk**: none (+ through the macros it calls: ACE, HEATS, MOVES THE TOOLHEAD)  |  **Tags**: calibration  |  **Fluidd**: RPI Calibration
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_LIVEZ_RESET
- **File / lines**: rpi_calibration.cfg L1737-1746 (gcode_macro)
- **What it does**: Called at the top of START_PRINT: every tool starts the print with live Z adjust 0
- **Calls**: -
- **Called by**: START_PRINT
- **Variables**: -
- **Uses**: sets variables of _WM_LIVEZ
- **Commands**: all exist (built-in/module commands used: SET_GCODE_VARIABLE) - checked 2026-11-18
- **Risk**: none  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_LIVEZ_HEAT
- **File / lines**: rpi_calibration.cfg L1747-1761 (gcode_macro)
- **What it does**: Called by M104 and M109 with T=heater number S=new target. In a print, when the target of the tool on the carriage goes UP, the heat growth part of its Z offset is worked out again. A cooldown is not followed
- **Calls**: _OFFSET_SET
- **Called by**: _WM_PURGE_HEAT
- **Variables**: -
- **Uses**: reads printer.print_stats, printer.save_variables, printer.toolhead
- **Commands**: all exist (built-in/module commands used: none) - checked 2026-11-18
- **Risk**: none (+ through the macros it calls: ACE, HEATS, MOVES THE TOOLHEAD)  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### WM_LIVE_Z_MENU
- **File / lines**: rpi_calibration.cfg L1762-1792 (gcode_macro)
- **What it does**: Window: the live Z adjust of each tool, with Save all (into the Z trim of each tool) or Do not save
- **Calls**: -
- **Called by**: Z_OFFSET_APPLY_ENDSTOP, Z_OFFSET_APPLY_PROBE, _WM_LIVEZ_WATCH
- **Variables**: -
- **Uses**: reads printer.save_variables
- **Commands**: all exist (built-in/module commands used: RESPOND) - checked 2026-11-18
- **Risk**: ACE  |  **Tags**: calibration  |  **Fluidd**: RPI Calibration
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_LIVEZ_SAVE
- **File / lines**: rpi_calibration.cfg L1793-1817 (gcode_macro)
- **What it does**: Save all button of WM_LIVE_Z_MENU: add the live Z adjust of each tool to its saved Z trim, then set the live adjusts to 0
- **Calls**: _WM_Z_TRIM_APPLY
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: reads printer.save_variables; sets variables of _WM_LIVEZ; saves wm_z_trim_t{t} VALUE
- **Commands**: all exist (built-in/module commands used: RESPOND, SAVE_VARIABLE, SET_GCODE_VARIABLE) - checked 2026-11-18
- **Risk**: none (+ through the macros it calls: ACE, HEATS, MOVES THE TOOLHEAD)  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_LIVEZ_DROP
- **File / lines**: rpi_calibration.cfg L1818-1829 (gcode_macro)
- **What it does**: Do not save button of WM_LIVE_Z_MENU: set the live Z adjust of every tool to 0, the saved Z trims stay as they are
- **Calls**: _WM_Z_TRIM_APPLY
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: sets variables of _WM_LIVEZ
- **Commands**: all exist (built-in/module commands used: RESPOND, SET_GCODE_VARIABLE) - checked 2026-11-18
- **Risk**: none (+ through the macros it calls: ACE, HEATS, MOVES THE TOOLHEAD)  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_LIVEZ_WATCH
- **File / lines**: rpi_calibration.cfg L1830-1839 (delayed_gcode timer)
- **What it does**: Opens the live Z adjust window while a print runs.
- **Calls**: WM_LIVE_Z_MENU
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: reads printer.print_stats; sets variables of _WM_LIVEZ
- **Commands**: all exist (built-in/module commands used: SET_GCODE_VARIABLE, UPDATE_DELAYED_GCODE) - checked 2026-11-18
- **Risk**: none (+ through the macros it calls: ACE)  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### Z_OFFSET_APPLY_PROBE
- **File / lines**: rpi_calibration.cfg L1840-1846 (gcode_macro) - renames the original to _WM_Z_OFFSET_APPLY_PROBE_KLIPPER
- **What it does**: On this printer the live Z adjust is saved as Z trim of each tool. Opens the Save all / Do not save window. The probe z_offset is not changed
- **Calls**: WM_LIVE_Z_MENU
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: RESPOND) - checked 2026-11-18
- **Risk**: none (+ through the macros it calls: ACE)  |  **Tags**: calibration  |  **Fluidd**: none
- **Tested**: no per-macro record in FIX-LOG.md
### Z_OFFSET_APPLY_ENDSTOP
- **File / lines**: rpi_calibration.cfg L1847-1856 (gcode_macro) - renames the original to _WM_Z_OFFSET_APPLY_ENDSTOP_KLIPPER
- **What it does**: On this printer the live Z adjust is saved as Z trim of each tool. Opens the Save all / Do not save window. The Z endstop position is not changed
- **Calls**: WM_LIVE_Z_MENU
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: RESPOND) - checked 2026-11-18
- **Risk**: LOAD CELL / SETTER (+ through the macros it calls: ACE)  |  **Tags**: calibration  |  **Fluidd**: none
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_SETTER
- **File / lines**: rpi_calibration.cfg L1860-1927 (gcode_macro)
- **What it does**: State of the tool setter position helper (saved start position, helper active)
- **Calls**: -
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: active, sx, sy, sz, xy_range, z_below, z_above, xy_speed, z_speed, tip_half, top_bias, find_lift, find_below, width, fx0, fy0, ftop, fz, fdx, fdy, zref, scratch, reach, lane_step, past, scratch_z, cx, touch_accel, top_band, mid_left, mid_front, block_w, block_tol, mid_drop, mid_wadd, mid_tol, mskip, mok, mbx, mwx, mry, mwy, mnx, mny, mx0, my0, mz0, auto, cal, cal_tol, cal_ok
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: RESPOND) - checked 2026-11-18
- **Risk**: LOAD CELL / SETTER  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### WM_SETTER_PROBE_POSITION
- **File / lines**: rpi_calibration.cfg L1928-1949 (gcode_macro)
- **What it does**: Tool setter position: put the T0 nozzle at the start position of the offset calibration, adjust it in small steps in a window, save it (probe_position in saved_variables.cfg)
- **Calls**: _WM_FAIL
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: reads printer.print_stats, printer.save_variables; sets variables of _WM_SETTER
- **Commands**: all exist (built-in/module commands used: RESPOND, SET_GCODE_VARIABLE) - checked 2026-11-18
- **Risk**: ACE, LOAD CELL / SETTER  |  **Tags**: calibration  |  **Fluidd**: RPI Calibration
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_SETTER_GO
- **File / lines**: rpi_calibration.cfg L1950-1980 (gcode_macro)
- **What it does**: Start button of the tool setter position helper: home, pick up T0, go to the saved position
- **Calls**: SET_GCODE_OFFSET, T0, _WM_CAL_CLEARANCE, _WM_CAL_PRECHECK, _WM_FAIL, _WM_SETTER_MOVE
- **Called by**: _WM_SETTER_AUTO, _WM_ZCAL_RUN
- **Variables**: -
- **Uses**: reads printer.save_variables, printer.toolhead; sets variables of _WM_SETTER
- **Commands**: all exist (built-in/module commands used: BED_MESH_CLEAR, COLLISION_DETECT_DISABLE, G1, G28, G90, M400, RESPOND, SET_GCODE_VARIABLE) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, LOAD CELL / SETTER (+ through the macros it calls: ACE, HEATS)  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_SETTER_MOVE
- **File / lines**: rpi_calibration.cfg L1981-2000 (gcode_macro)
- **What it does**: Tool setter position helper: from the middle of the bed to the saved position (X, then Y, then slowly down), then the window
- **Calls**: _WM_FAIL, _WM_SETTER_SENSE
- **Called by**: _WM_SETTER_FIND_FAIL, _WM_SETTER_GO, _WM_SETTER_WIDE_CANCEL
- **Variables**: -
- **Uses**: reads printer.save_variables, printer.toolhead
- **Commands**: all exist (built-in/module commands used: COLLISION_DETECT_DISABLE, G0, G4, G90, M400) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, LOAD CELL / SETTER (+ through the macros it calls: ACE, HEATS)  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_SETTER_SENSE
- **File / lines**: rpi_calibration.cfg L2001-2015 (gcode_macro)
- **What it does**: Tool setter position helper: come down to the saved Z with the touch sensor on (when the module wm_tool_touch is loaded), so the nozzle stops when it meets something
- **Calls**: _WM_SETTER_DOWN
- **Called by**: _WM_SETTER_MOVE
- **Variables**: -
- **Uses**: reads printer.toolhead
- **Commands**: all exist (built-in/module commands used: G4, SET_VELOCITY_LIMIT, TOOL_CALIBRATE_TOUCH) - checked 2026-11-18
- **Risk**: LOAD CELL / SETTER (+ through the macros it calls: ACE, HEATS, MOVES THE TOOLHEAD)  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_SETTER_DOWN
- **File / lines**: rpi_calibration.cfg L2016-2047 (gcode_macro)
- **What it does**: Tool setter position helper: go down to the saved Z when the way was free, stay up when the nozzle met something; then the adjust window
- **Calls**: _WM_FAIL, _WM_SETTER_AWAY, _WM_SETTER_FIND, _WM_SETTER_WIN, _WM_ZCAL_DONE
- **Called by**: _WM_SETTER_SENSE
- **Variables**: -
- **Uses**: reads printer.configfile, printer.max_accel, printer.wm_tool_touch; sets variables of _WM_SETTER
- **Commands**: all exist (built-in/module commands used: G0, G90, M400, RESPOND, SET_GCODE_VARIABLE, SET_VELOCITY_LIMIT) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, LOAD CELL / SETTER (+ through the macros it calls: ACE, HEATS)  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_SETTER_WIN
- **File / lines**: rpi_calibration.cfg L2048-2104 (gcode_macro)
- **What it does**: Window of the tool setter position helper: saved and current position, step buttons, Save
- **Calls**: _WM_FAIL
- **Called by**: _WM_SETTER_DOWN, _WM_SETTER_STEP
- **Variables**: -
- **Uses**: reads printer.toolhead
- **Commands**: all exist (built-in/module commands used: RESPOND) - checked 2026-11-18
- **Risk**: ACE, LOAD CELL / SETTER  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_SETTER_STEP
- **File / lines**: rpi_calibration.cfg L2105-2146 (gcode_macro)
- **What it does**: Step button of the tool setter position helper: AXIS=X Y or Z, D=step in mm (1 mm at most), slow, inside the limits
- **Calls**: _WM_FAIL, _WM_SETTER_WIN
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: reads printer.print_stats, printer.save_variables, printer.toolhead; sets variables of _WM_SETTER
- **Commands**: all exist (built-in/module commands used: G0, G91, M400, RESPOND, RESTORE_GCODE_STATE, SAVE_GCODE_STATE, SET_GCODE_VARIABLE) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, LOAD CELL / SETTER (+ through the macros it calls: ACE)  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_SETTER_SAVE
- **File / lines**: rpi_calibration.cfg L2147-2178 (gcode_macro)
- **What it does**: Save button of the tool setter position helper: shows old and new, with CONFIRM=1 writes probe_position and keeps the old one as probe_position_backup
- **Calls**: _WM_FAIL, _WM_SETTER_AFTER
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: reads printer.save_variables, printer.toolhead; sets variables of _WM_SETTER; saves probe_position VALUE, probe_position_backup VALUE
- **Commands**: all exist (built-in/module commands used: RESPOND, SAVE_VARIABLE, SET_GCODE_VARIABLE) - checked 2026-11-18
- **Risk**: LOAD CELL / SETTER  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_SETTER_AFTER
- **File / lines**: rpi_calibration.cfg L2179-2213 (gcode_macro)
- **What it does**: Window after Save or after the test of the tool setter position helper: Test with T0, Offsets rapid, Restore the old position, Adjust again, Close
- **Calls**: -
- **Called by**: _WM_SETTER_MID_SAVE, _WM_SETTER_RESTORE, _WM_SETTER_SAVE, _WM_SETTER_TEST
- **Variables**: -
- **Uses**: reads printer.save_variables
- **Commands**: all exist (built-in/module commands used: RESPOND) - checked 2026-11-18
- **Risk**: LOAD CELL / SETTER  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_SETTER_AWAY
- **File / lines**: rpi_calibration.cfg L2214-2229 (gcode_macro)
- **What it does**: Tool setter position helper: lift the nozzle 5 mm and move it away from the tool setter to Y250 (only while the helper is active)
- **Calls**: -
- **Called by**: _WM_SETTER_AUTO_FINISH, _WM_SETTER_CLOSE, _WM_SETTER_DOWN, _WM_SETTER_FIND_DONE, _WM_SETTER_FIND_FAIL, _WM_SETTER_MID_SAVE, _WM_SETTER_RAPID, _WM_SETTER_RESTORE, _WM_SETTER_TEST
- **Variables**: -
- **Uses**: reads printer.print_stats, printer.toolhead; sets variables of _WM_SETTER
- **Commands**: all exist (built-in/module commands used: G0, G90, G91, M400, RESTORE_GCODE_STATE, SAVE_GCODE_STATE, SET_GCODE_VARIABLE) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, LOAD CELL / SETTER  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_SETTER_CLOSE
- **File / lines**: rpi_calibration.cfg L2230-2237 (gcode_macro)
- **What it does**: Close button of the tool setter position helper: the nozzle lifts and moves away, the window closes
- **Calls**: _WM_SETTER_AWAY
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: sets variables of _WM_SETTER
- **Commands**: all exist (built-in/module commands used: RESPOND, SET_GCODE_VARIABLE) - checked 2026-11-18
- **Risk**: LOAD CELL / SETTER (+ through the macros it calls: MOVES THE TOOLHEAD)  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_SETTER_TEST
- **File / lines**: rpi_calibration.cfg L2238-2252 (gcode_macro)
- **What it does**: Test button of the tool setter position helper: the real T0 touch of the offset calibration from the saved position, nothing is saved
- **Calls**: CALIBRATE_TOOL_OFFSET, _WM_CAL_PRECHECK, _WM_SETTER_AFTER, _WM_SETTER_AWAY
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: reads printer.toolhead
- **Commands**: all exist (built-in/module commands used: G28, M400, RESPOND) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, LOAD CELL / SETTER (+ through the macros it calls: ACE, HEATS)  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_SETTER_RAPID
- **File / lines**: rpi_calibration.cfg L2253-2259 (gcode_macro)
- **What it does**: Offsets rapid button of the tool setter position helper: the nozzle moves away, then the start window of WM_OFFSETS_RAPID
- **Calls**: WM_OFFSETS_RAPID, _WM_SETTER_AWAY
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: RESPOND) - checked 2026-11-18
- **Risk**: LOAD CELL / SETTER (+ through the macros it calls: ACE, HEATS, MOVES THE TOOLHEAD)  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_SETTER_RESTORE
- **File / lines**: rpi_calibration.cfg L2260-2289 (gcode_macro)
- **What it does**: Restore button of the tool setter position helper: asks first, with CONFIRM=1 writes probe_position_backup back to probe_position
- **Calls**: _WM_FAIL, _WM_SETTER_AFTER, _WM_SETTER_AWAY
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: reads printer.save_variables; saves probe_position VALUE, probe_position_backup VALUE
- **Commands**: all exist (built-in/module commands used: RESPOND, SAVE_VARIABLE) - checked 2026-11-18
- **Risk**: ACE, LOAD CELL / SETTER (+ through the macros it calls: MOVES THE TOOLHEAD)  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_SETTER_FIND
- **File / lines**: rpi_calibration.cfg L2290-2318 (gcode_macro)
- **What it does**: Find automatically button of the tool setter position helper (T0 only): touch the top of the back block at 5 spots
- **Calls**: _WM_FAIL, _WM_SETTER_FIND_TOP
- **Called by**: _WM_SETTER_DOWN
- **Variables**: -
- **Uses**: reads printer.gcode_move, printer.print_stats, printer.save_variables, printer.toolhead; sets variables of _WM_SETTER
- **Commands**: all exist (built-in/module commands used: RESPOND, SET_GCODE_VARIABLE) - checked 2026-11-18
- **Risk**: LOAD CELL / SETTER (+ through the macros it calls: ACE, HEATS, MOVES THE TOOLHEAD)  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_SETTER_FIND_TOP
- **File / lines**: rpi_calibration.cfg L2319-2346 (gcode_macro)
- **What it does**: Find automatically, step 1 (also the end of Find from scratch): touch the top of the back block from above at 5 spots, 0.75 mm apart, straight behind the start point
- **Calls**: _WM_SETTER_FIND_SIDES
- **Called by**: _WM_SETTER_FIND, _WM_SETTER_SCRATCH_DONE
- **Variables**: -
- **Uses**: reads printer.configfile, printer.max_accel, printer.save_variables
- **Commands**: all exist (built-in/module commands used: COLLISION_DETECT_DISABLE, G0, G4, G90, M400, RESPOND, SET_VELOCITY_LIMIT, TOOL_CALIBRATE_TOUCH) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, LOAD CELL / SETTER (+ through the macros it calls: ACE, HEATS)  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_SETTER_FIND_FAIL
- **File / lines**: rpi_calibration.cfg L2347-2377 (gcode_macro)
- **What it does**: Find automatically stopped: detection off, nozzle up, message, back to the saved position and the adjust window
- **Calls**: _WM_FAIL, _WM_SETTER_AWAY, _WM_SETTER_MOVE, _WM_SETTER_WIDE_ASK, _WM_ZCAL_DONE
- **Called by**: _WM_SETTER_FIND_DONE, _WM_SETTER_FIND_FAR, _WM_SETTER_FIND_SIDES, _WM_SETTER_SCRATCH_DONE, _WM_SETTER_SCRATCH_Y
- **Variables**: -
- **Uses**: reads printer.configfile, printer.max_accel; sets variables of _WM_SETTER
- **Commands**: all exist (built-in/module commands used: COLLISION_DETECT_DISABLE, G0, G90, M400, RESPOND, SET_GCODE_VARIABLE, SET_VELOCITY_LIMIT) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, LOAD CELL / SETTER (+ through the macros it calls: ACE, HEATS)  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_SETTER_WIDE_ASK
- **File / lines**: rpi_calibration.cfg L2378-2390 (gcode_macro)
- **What it does**: Window after a failed quick search of Find automatically: says why, offers the wide search (Start) or back to the saved position (Cancel)
- **Calls**: -
- **Called by**: _WM_SETTER_FIND_FAIL
- **Variables**: -
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: RESPOND) - checked 2026-11-18
- **Risk**: LOAD CELL / SETTER  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_SETTER_WIDE_CANCEL
- **File / lines**: rpi_calibration.cfg L2391-2398 (gcode_macro)
- **What it does**: Cancel button of the wide search window: back to the saved position and the adjust window
- **Calls**: _WM_SETTER_MOVE
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: sets variables of _WM_SETTER
- **Commands**: all exist (built-in/module commands used: RESPOND, SET_GCODE_VARIABLE) - checked 2026-11-18
- **Risk**: LOAD CELL / SETTER (+ through the macros it calls: ACE, HEATS, MOVES THE TOOLHEAD)  |  **Tags**: calibration, print  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_SETTER_FIND_SIDES
- **File / lines**: rpi_calibration.cfg L2399-2458 (gcode_macro)
- **What it does**: Find automatically, step 2: take the highest top touch that a second spot confirms, go to top minus half the tip, touch the back block and the right block from the near side
- **Calls**: _WM_SETTER_FIND_FAIL, _WM_SETTER_FIND_FAR
- **Called by**: _WM_SETTER_FIND_TOP
- **Variables**: -
- **Uses**: reads printer.configfile, printer.max_accel, printer.wm_tool_touch; sets variables of _WM_SETTER
- **Commands**: all exist (built-in/module commands used: COLLISION_DETECT_ENABLE, G0, G90, M400, RESPOND, SET_COLLISION_THRESHOLD, SET_GCODE_VARIABLE, SET_VELOCITY_LIMIT, TOOL_CALIBRATE_TOUCH) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, ACE, LOAD CELL / SETTER (+ through the macros it calls: HEATS)  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_SETTER_FIND_FAR
- **File / lines**: rpi_calibration.cfg L2459-2485 (gcode_macro)
- **What it does**: Find automatically, step 3: touch the back block from behind and the right block from the right (over the top, 6 mm beyond, like the driver)
- **Calls**: _WM_SETTER_FIND_DONE, _WM_SETTER_FIND_FAIL
- **Called by**: _WM_SETTER_FIND_SIDES
- **Variables**: -
- **Uses**: reads printer.wm_tool_touch
- **Commands**: all exist (built-in/module commands used: COLLISION_DETECT_DISABLE, G0, G90, M400, RESPOND, TOOL_CALIBRATE_TOUCH) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, ACE, LOAD CELL / SETTER (+ through the macros it calls: HEATS)  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_SETTER_FIND_DONE
- **File / lines**: rpi_calibration.cfg L2486-2543 (gcode_macro)
- **What it does**: Find automatically, result: work out X Y from the four side touches, move the nozzle there, open the result window
- **Calls**: WM_OFFSETS_RAPID, _WM_SETTER_AWAY, _WM_SETTER_FIND_FAIL, _WM_SETTER_FOUND, _WM_SETTER_MID, _WM_ZCAL_DONE
- **Called by**: _WM_SETTER_FIND_FAR
- **Variables**: -
- **Uses**: reads printer.save_variables, printer.wm_tool_touch; sets variables of _WM_SETTER
- **Commands**: all exist (built-in/module commands used: G0, G90, M400, RESPOND, SET_GCODE_VARIABLE) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, LOAD CELL / SETTER (+ through the macros it calls: ACE, HEATS)  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_SETTER_FOUND
- **File / lines**: rpi_calibration.cfg L2544-2606 (gcode_macro)
- **What it does**: Result window of Find automatically: saved and found position, block top, touched widths, Save / Adjust by hand / Find again / Close
- **Calls**: _WM_FAIL
- **Called by**: _WM_SETTER_FIND_DONE, _WM_SETTER_MID_DONE
- **Variables**: -
- **Uses**: reads printer.toolhead
- **Commands**: all exist (built-in/module commands used: RESPOND) - checked 2026-11-18
- **Risk**: ACE, LOAD CELL / SETTER  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_SETTER_SCRATCH_GO
- **File / lines**: rpi_calibration.cfg L2607-2650 (gcode_macro)
- **What it does**: Find from scratch, step 1: go in front and to the left of the saved position, three sweeps to the right to meet the right block
- **Calls**: _WM_FAIL, _WM_SETTER_SCRATCH_Y
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: reads printer.gcode_move, printer.print_stats, printer.save_variables, printer.toolhead; sets variables of _WM_SETTER
- **Commands**: all exist (built-in/module commands used: COLLISION_DETECT_DISABLE, COLLISION_DETECT_ENABLE, G0, G4, G90, M400, RESPOND, SET_COLLISION_THRESHOLD, SET_GCODE_VARIABLE, TOOL_CALIBRATE_TOUCH) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, LOAD CELL / SETTER (+ through the macros it calls: ACE, HEATS)  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_SETTER_SCRATCH_Y
- **File / lines**: rpi_calibration.cfg L2651-2681 (gcode_macro)
- **What it does**: Find from scratch, step 2: the sweep that went furthest right met the right block; work out the start X, then one sweep to the back to meet the back block
- **Calls**: _WM_SETTER_FIND_FAIL, _WM_SETTER_SCRATCH_DONE
- **Called by**: _WM_SETTER_SCRATCH_GO
- **Variables**: -
- **Uses**: reads printer.save_variables, printer.wm_tool_touch; sets variables of _WM_SETTER
- **Commands**: all exist (built-in/module commands used: G0, G4, G90, M400, RESPOND, SET_GCODE_VARIABLE, TOOL_CALIBRATE_TOUCH) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, ACE, LOAD CELL / SETTER (+ through the macros it calls: HEATS)  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_SETTER_SCRATCH_DONE
- **File / lines**: rpi_calibration.cfg L2682-2706 (gcode_macro)
- **What it does**: Find from scratch, step 3: work out the start Y from the back block, go there, hand over to the fine search
- **Calls**: _WM_SETTER_FIND_FAIL, _WM_SETTER_FIND_TOP
- **Called by**: _WM_SETTER_SCRATCH_Y
- **Variables**: -
- **Uses**: reads printer.save_variables, printer.wm_tool_touch; sets variables of _WM_SETTER
- **Commands**: all exist (built-in/module commands used: COLLISION_DETECT_DISABLE, G0, G90, M400, RESPOND, SET_GCODE_VARIABLE) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, LOAD CELL / SETTER (+ through the macros it calls: ACE, HEATS)  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_SETTER_MID
- **File / lines**: rpi_calibration.cfg L2707-2748 (gcode_macro)
- **What it does**: Measure block middles (T0 only), from the base point mx0 my0 mz0: touch 1, the left end of the back block
- **Calls**: _WM_FAIL, _WM_SETTER_MID_B
- **Called by**: _WM_SETTER_FIND_DONE
- **Variables**: -
- **Uses**: reads printer.configfile, printer.gcode_move, printer.max_accel, printer.print_stats, printer.save_variables, printer.toolhead; sets variables of _WM_SETTER
- **Commands**: all exist (built-in/module commands used: COLLISION_DETECT_DISABLE, COLLISION_DETECT_ENABLE, G0, G4, G90, M400, RESPOND, SET_COLLISION_THRESHOLD, SET_GCODE_VARIABLE, SET_VELOCITY_LIMIT, TOOL_CALIBRATE_TOUCH) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, LOAD CELL / SETTER (+ through the macros it calls: ACE)  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_SETTER_MID_B
- **File / lines**: rpi_calibration.cfg L2749-2772 (gcode_macro)
- **What it does**: Measure block middles, touch 2, part 1: go over the place right of the back block and come down with the sensor on
- **Calls**: _WM_SETTER_MID_C
- **Called by**: _WM_SETTER_MID
- **Variables**: -
- **Uses**: reads printer.configfile, printer.max_accel, printer.save_variables, printer.wm_tool_touch
- **Commands**: all exist (built-in/module commands used: G0, G4, G90, M400, RESPOND, SET_VELOCITY_LIMIT, TOOL_CALIBRATE_TOUCH) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, LOAD CELL / SETTER (+ through the macros it calls: ACE)  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_SETTER_MID_C
- **File / lines**: rpi_calibration.cfg L2773-2811 (gcode_macro)
- **What it does**: Measure block middles, touch 2 part 2 (right end of the back block, when the way down was free) and touch 3 (front end of the right block)
- **Calls**: _WM_SETTER_MID_D
- **Called by**: _WM_SETTER_MID_B
- **Variables**: -
- **Uses**: reads printer.save_variables, printer.wm_tool_touch; sets variables of _WM_SETTER
- **Commands**: all exist (built-in/module commands used: COLLISION_DETECT_DISABLE, COLLISION_DETECT_ENABLE, G0, G4, G90, M400, RESPOND, SET_COLLISION_THRESHOLD, SET_GCODE_VARIABLE, TOOL_CALIBRATE_TOUCH) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, LOAD CELL / SETTER (+ through the macros it calls: ACE)  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_SETTER_MID_D
- **File / lines**: rpi_calibration.cfg L2812-2840 (gcode_macro)
- **What it does**: Measure block middles, touch 4, part 1: go over the place behind the right block and come down with the sensor on
- **Calls**: _WM_SETTER_MID_DONE, _WM_SETTER_MID_E
- **Called by**: _WM_SETTER_MID_C
- **Variables**: -
- **Uses**: reads printer.configfile, printer.max_accel, printer.save_variables, printer.wm_tool_touch; sets variables of _WM_SETTER
- **Commands**: all exist (built-in/module commands used: G0, G4, G90, M400, RESPOND, SET_GCODE_VARIABLE, SET_VELOCITY_LIMIT, TOOL_CALIBRATE_TOUCH) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, LOAD CELL / SETTER (+ through the macros it calls: ACE)  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_SETTER_MID_E
- **File / lines**: rpi_calibration.cfg L2841-2866 (gcode_macro)
- **What it does**: Measure block middles, touch 4 part 2 (back end of the right block, when the way down was free), then back to the saved position
- **Calls**: _WM_SETTER_MID_DONE
- **Called by**: _WM_SETTER_MID_D
- **Variables**: -
- **Uses**: reads printer.wm_tool_touch; sets variables of _WM_SETTER
- **Commands**: all exist (built-in/module commands used: COLLISION_DETECT_DISABLE, COLLISION_DETECT_ENABLE, G0, G4, G90, M400, RESPOND, SET_COLLISION_THRESHOLD, SET_GCODE_VARIABLE, TOOL_CALIBRATE_TOUCH) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, LOAD CELL / SETTER (+ through the macros it calls: ACE)  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_SETTER_MID_DONE
- **File / lines**: rpi_calibration.cfg L2867-2912 (gcode_macro)
- **What it does**: Measure block middles, result: work out the middles and the two offsets, open the result window
- **Calls**: _WM_SETTER_AUTO_FINISH, _WM_SETTER_FOUND
- **Called by**: _WM_SETTER_MID_D, _WM_SETTER_MID_E
- **Variables**: -
- **Uses**: reads printer.save_variables, printer.wm_tool_touch; sets variables of _WM_SETTER
- **Commands**: all exist (built-in/module commands used: RESPOND, SET_GCODE_VARIABLE) - checked 2026-11-18
- **Risk**: LOAD CELL / SETTER (+ through the macros it calls: ACE, MOVES THE TOOLHEAD)  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_SETTER_MID_SAVE
- **File / lines**: rpi_calibration.cfg L2913-2949 (gcode_macro)
- **What it does**: Save new numbers button of Measure block middles: writes the start point on the block middles and the two offsets, keeps the old line as probe_position_backup, moves the nozzle to the new start point
- **Calls**: _WM_FAIL, _WM_SETTER_AFTER, _WM_SETTER_AWAY
- **Called by**: _WM_SETTER_AUTO_FINISH
- **Variables**: -
- **Uses**: reads printer.save_variables, printer.toolhead; sets variables of _WM_SETTER; saves probe_position VALUE, probe_position_backup VALUE
- **Commands**: all exist (built-in/module commands used: G0, G90, M400, RESPOND, SAVE_VARIABLE, SET_GCODE_VARIABLE) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD, LOAD CELL / SETTER  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_SETTER_AUTO
- **File / lines**: rpi_calibration.cfg L2950-2958 (gcode_macro)
- **What it does**: First Run Calibration, stage 1: the tool setter position with T0 without windows: quick search, block middles, SAVE (probe_position, no restart). Any problem raises an error and stops the calibration
- **Calls**: _WM_SETTER_AUTO_CHECK, _WM_SETTER_GO
- **Called by**: _WM_FIRST_RUN_CAL
- **Variables**: -
- **Uses**: sets variables of _WM_SETTER
- **Commands**: all exist (built-in/module commands used: RESPOND, SET_GCODE_VARIABLE) - checked 2026-11-18
- **Risk**: LOAD CELL / SETTER (+ through the macros it calls: ACE, HEATS, MOVES THE TOOLHEAD)  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: F-143 pushed, NOT tested
### _WM_SETTER_AUTO_CHECK
- **File / lines**: rpi_calibration.cfg L2959-2966 (gcode_macro)
- **What it does**: End of _WM_SETTER_AUTO: stops the calibration when the position was not saved
- **Calls**: _WM_FAIL
- **Called by**: _WM_SETTER_AUTO
- **Variables**: -
- **Uses**: sets variables of _WM_SETTER
- **Commands**: all exist (built-in/module commands used: SET_GCODE_VARIABLE) - checked 2026-11-18
- **Risk**: LOAD CELL / SETTER  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_SETTER_AUTO_FINISH
- **File / lines**: rpi_calibration.cfg L2967-2979 (gcode_macro)
- **What it does**: End of the block middle measurement in the First Run Calibration: saves the position when it is complete, otherwise stops
- **Calls**: _WM_FAIL, _WM_SETTER_AWAY, _WM_SETTER_MID_SAVE
- **Called by**: _WM_SETTER_MID_DONE
- **Variables**: -
- **Uses**: sets variables of _WM_SETTER
- **Commands**: all exist (built-in/module commands used: SET_GCODE_VARIABLE) - checked 2026-11-18
- **Risk**: LOAD CELL / SETTER (+ through the macros it calls: MOVES THE TOOLHEAD)  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md

## rpi_endless.cfg
ACE panel: endless spool

### _WM_ENDLESS
- **File / lines**: rpi_endless.cfg L27-47 (gcode_macro)
- **What it does**: Settings and run state of the endless spool (swap pair, files, tries).
- **Calls**: -
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: from, to, swap_file, tried, ofx, ofy, ofz, ocx, ocy, ocz, pending, keeps, tangle, out0, out1, out2, out3, fake
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: none) - checked 2026-11-18
- **Risk**: none  |  **Tags**: endless  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### WM_ENDLESS_SET
- **File / lines**: rpi_endless.cfg L48-65 (gcode_macro)
- **What it does**: WM_ENDLESS_SET ENABLE=1|0 AUTO=1|0 TANGLE=1|0 - endless spool, swap automatically, swap on a tangle (all saved on the printer)
- **Calls**: -
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: reads printer.save_variables; saves wm_endless VALUE, wm_endless_auto VALUE, wm_endless_tangle VALUE
- **Commands**: all exist (built-in/module commands used: RESPOND, SAVE_VARIABLE) - checked 2026-11-18
- **Risk**: none  |  **Tags**: endless  |  **Fluidd**: AcePro
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_ENDLESS_TANGLE
- **File / lines**: rpi_endless.cfg L66-73 (gcode_macro)
- **What it does**: Called by the tangle sensors (hub.cfg, path_N) after they paused the print: remembers which toolhead tangled
- **Calls**: -
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: reads printer.print_stats; sets variables of _WM_ENDLESS
- **Commands**: all exist (built-in/module commands used: SET_GCODE_VARIABLE) - checked 2026-11-18
- **Risk**: none  |  **Tags**: endless  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### WM_ENDLESS_FIXED
- **File / lines**: rpi_endless.cfg L74-84 (gcode_macro)
- **What it does**: WM_ENDLESS_FIXED T=0 - the spool of this toolhead is free or replaced after a tangle: it may take over again
- **Calls**: -
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: sets variables of _WM_ENDLESS
- **Commands**: all exist (built-in/module commands used: RESPOND, SET_GCODE_VARIABLE) - checked 2026-11-18
- **Risk**: none  |  **Tags**: endless  |  **Fluidd**: AcePro
- **Tested**: no per-macro record in FIX-LOG.md
### WM_ENDLESS_PLAN
- **File / lines**: rpi_endless.cfg L85-101 (gcode_macro)
- **What it does**: WM_ENDLESS_PLAN - shows the sets of identical toolheads and who takes over for whom, moves nothing
- **Calls**: -
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: reads printer.print_stats, printer.save_variables
- **Commands**: all exist (built-in/module commands used: RESPOND) - checked 2026-11-18
- **Risk**: ACE  |  **Tags**: endless  |  **Fluidd**: AcePro
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_ENDLESS_WATCH
- **File / lines**: rpi_endless.cfg L102-107 (delayed_gcode timer)
- **What it does**: Timer: calls _WM_ENDLESS_TICK every 3 s.
- **Calls**: _WM_ENDLESS_TICK
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: UPDATE_DELAYED_GCODE) - checked 2026-11-18
- **Risk**: none (+ through the macros it calls: ACE, HEATS, MOVES THE TOOLHEAD)  |  **Tags**: endless  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_ENDLESS_TICK
- **File / lines**: rpi_endless.cfg L108-184 (gcode_macro)
- **What it does**: Called every 3 s by _WM_ENDLESS_WATCH: a paused print whose toolhead is empty or tangled gets its identical spare
- **Calls**: WM_ENDLESS_CONTINUE
- **Called by**: _WM_ENDLESS_WATCH
- **Variables**: -
- **Uses**: reads printer.print_stats, printer.save_variables; sets variables of _WM_ENDLESS
- **Commands**: all exist (built-in/module commands used: RESPOND, SET_GCODE_VARIABLE) - checked 2026-11-18
- **Risk**: ACE (+ through the macros it calls: HEATS, MOVES THE TOOLHEAD)  |  **Tags**: endless  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_ENDLESS_PROMPT_CLOSE
- **File / lines**: rpi_endless.cfg L185-188 (gcode_macro)
- **What it does**: Closes the endless spool prompt window.
- **Calls**: -
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: RESPOND) - checked 2026-11-18
- **Risk**: none  |  **Tags**: endless  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### WM_ENDLESS_CONTINUE
- **File / lines**: rpi_endless.cfg L189-224 (gcode_macro)
- **What it does**: WM_ENDLESS_CONTINUE FROM= TO= - while PAUSED: swap the empty head FROM for the loaded head TO and resume
- **Calls**: _CHANGE_TOOL, _WM_ENDLESS_3
- **Called by**: _WM_ENDLESS_TICK
- **Variables**: -
- **Uses**: reads printer.gcode_move, printer.print_stats, printer.save_variables; sets variables of _WM_ENDLESS
- **Commands**: all exist (built-in/module commands used: RESPOND, SET_GCODE_VARIABLE) - checked 2026-11-18
- **Risk**: ACE (+ through the macros it calls: HEATS, MOVES THE TOOLHEAD)  |  **Tags**: endless  |  **Fluidd**: AcePro
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_ENDLESS_3
- **File / lines**: rpi_endless.cfg L225-255 (gcode_macro)
- **Change 2026-11-20 (F-202)**: before RESUME it sets _WM_RTOOL.purge to _WM_ENDLESS.swap_purge (50 mm) when that is longer than the current purge (20), and sets it back to 20 after RESUME. Why: after a swap the spare head's filament was never pushed (B-079), the 20 mm purge was too short to prime it. Checked against the real file rpi_endless.cfg on .35, 2026-11-20.
- **What it does**: Step 3 of an endless spool swap: RESUME with the spare head, restores tool mapping.
- **Calls**: RESUME, _WM_ENDLESS_4
- **Called by**: WM_ENDLESS_CONTINUE
- **Variables**: -
- **Uses**: reads printer.gcode_move, printer.save_variables; sets variables of RESUME, _WM_ENDLESS; saves box_modify_t{L}_backup VALUE
- **Commands**: all exist (built-in/module commands used: RESPOND, SAVE_VARIABLE, SET_GCODE_VARIABLE) - checked 2026-11-18
- **Risk**: none (+ through the macros it calls: ACE, HEATS, MOVES THE TOOLHEAD)  |  **Tags**: endless  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_ENDLESS_4
- **File / lines**: rpi_endless.cfg L256-279 (gcode_macro)
- **What it does**: After RESUME: put the nozzle of the spare head exactly where the nozzle of the empty head stopped
- **Calls**: _OFFSET_SET
- **Called by**: _WM_ENDLESS_3
- **Variables**: -
- **Uses**: sets variables of _WM_ENDLESS
- **Commands**: all exist (built-in/module commands used: G1, G91, RESPOND, RESTORE_GCODE_STATE, SAVE_GCODE_STATE, SET_GCODE_VARIABLE) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD (+ through the macros it calls: ACE, HEATS)  |  **Tags**: endless  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md

## rpi_fan_guard.cfg
Installer part: fan failure guard

### _WM_FAN_GUARD_STATE
- **File / lines**: rpi_fan_guard.cfg L6-12 (gcode_macro)
- **What it does**: Settings and state of the fan guard (enabled, interval, limit).
- **Calls**: -
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: enabled, interval, limit, zero
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: none) - checked 2026-11-18
- **Risk**: none  |  **Tags**: safety  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### WM_FAN_GUARD
- **File / lines**: rpi_fan_guard.cfg L13-43 (delayed_gcode timer)
- **What it does**: Checks fans that should run: 0 RPM for 30 s pauses the print and shows an error.
- **Calls**: PAUSE
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: reads printer.print_stats; sets variables of _WM_FAN_GUARD_STATE
- **Commands**: all exist (built-in/module commands used: RESPOND, SET_GCODE_VARIABLE, UPDATE_DELAYED_GCODE) - checked 2026-11-18
- **Risk**: none (+ through the macros it calls: HEATS, MOVES THE TOOLHEAD)  |  **Tags**: safety  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md

## rpi_nozzle.cfg
Installer part: nozzle macros, flow matching, auto speed

### _WM_NOZZLE_TYPE
- **File / lines**: rpi_nozzle.cfg L45-70 (gcode_macro)
- **What it does**: Set the nozzle material and diameter of a tool head, in a Fluidd window (app: General > Nozzle Type)
- **Calls**: -
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: reads printer.configfile, printer.print_stats, printer.save_variables
- **Commands**: all exist (built-in/module commands used: RESPOND) - checked 2026-11-18
- **Risk**: none  |  **Tags**: misc  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_NOZZLE_MATERIAL
- **File / lines**: rpi_nozzle.cfg L71-84 (gcode_macro)
- **What it does**: Nozzle Type, step 2: material of nozzle T (0-3)
- **Calls**: -
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: RESPOND) - checked 2026-11-18
- **Risk**: none  |  **Tags**: misc  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_NOZZLE_DIAMETER
- **File / lines**: rpi_nozzle.cfg L85-101 (gcode_macro)
- **What it does**: Nozzle Type, step 3: diameter of nozzle T (0-3), material TYPE (0 hardened, 1 stainless)
- **Calls**: -
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: RESPOND) - checked 2026-11-18
- **Risk**: none  |  **Tags**: misc  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_NOZZLE_SURE
- **File / lines**: rpi_nozzle.cfg L102-116 (gcode_macro)
- **What it does**: Nozzle Type, step 4: show what will be written
- **Calls**: -
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: reads printer.cfg
- **Commands**: all exist (built-in/module commands used: RESPOND) - checked 2026-11-18
- **Risk**: none  |  **Tags**: misc  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_NOZZLE_APPLY
- **File / lines**: rpi_nozzle.cfg L117-142 (gcode_macro)
- **What it does**: Nozzle Type, last step: write the material and the diameter
- **Calls**: -
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: reads printer.configfile, printer.print_stats; saves nozzle_type{t} VALUE
- **Commands**: all exist (built-in/module commands used: RESPOND, RUN_SHELL_COMMAND, SAVE_VARIABLE) - checked 2026-11-18
- **Risk**: none  |  **Tags**: misc  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### WM_NOZZLE_CHANGE
- **File / lines**: rpi_nozzle.cfg L143-157 (gcode_macro)
- **What it does**: Release the tool heads so you can change nozzles, in a Fluidd window (Pi only: the app has no such page)
- **Calls**: _WM_NCHANGE_CHECK
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: RESPOND) - checked 2026-11-18
- **Risk**: none  |  **Tags**: tool-change  |  **Fluidd**: ZR Tools
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_NCHANGE_CHECK
- **File / lines**: rpi_nozzle.cfg L158-180 (gcode_macro)
- **What it does**: Stop unless it is safe to release the tool heads
- **Calls**: -
- **Called by**: WM_NOZZLE_CHANGE, _WM_MATCH_CHECK, _WM_NCHANGE_RUN
- **Variables**: -
- **Uses**: reads printer.heaters, printer.print_stats
- **Commands**: all exist (built-in/module commands used: none) - checked 2026-11-18
- **Risk**: none  |  **Tags**: tool-change  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_NCHANGE_RUN
- **File / lines**: rpi_nozzle.cfg L181-197 (gcode_macro)
- **What it does**: Change nozzles, step 2: tool change check off, park and unlock the tool on the carriage
- **Calls**: _UNLOCK_TOOL, _WM_NCHANGE_AFTER, _WM_NCHANGE_CHECK, _WM_NCHANGE_FAILED
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: reads printer.save_variables
- **Commands**: all exist (built-in/module commands used: M400, RESPOND) - checked 2026-11-18
- **Risk**: none (+ through the macros it calls: ACE, HEATS, MOVES THE TOOLHEAD)  |  **Tags**: tool-change  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_NCHANGE_AFTER
- **File / lines**: rpi_nozzle.cfg L198-214 (gcode_macro)
- **What it does**: Change nozzles, step 3: tell the result of the unlock
- **Calls**: _WM_NCHANGE_FAILED
- **Called by**: _WM_NCHANGE_RUN
- **Variables**: -
- **Uses**: reads printer.save_variables; saves is_nozzle_setting VALUE
- **Commands**: all exist (built-in/module commands used: RESPOND, SAVE_VARIABLE) - checked 2026-11-18
- **Risk**: none  |  **Tags**: tool-change  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_NCHANGE_FAILED
- **File / lines**: rpi_nozzle.cfg L215-224 (gcode_macro)
- **What it does**: Nozzle change stopped: put the switch back and say why
- **Calls**: -
- **Called by**: _WM_NCHANGE_AFTER, _WM_NCHANGE_RUN
- **Variables**: -
- **Uses**: saves is_nozzle_setting VALUE
- **Commands**: all exist (built-in/module commands used: RESPOND, SAVE_VARIABLE) - checked 2026-11-18
- **Risk**: none  |  **Tags**: light, tool-change  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_NOZZLE_CHANGE_END
- **File / lines**: rpi_nozzle.cfg L225-252 (gcode_macro)
- **What it does**: Finish the nozzle change: tool change check back on (is_nozzle_setting = 0), and a look at the docks
- **Calls**: -
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: reads printer.configfile, printer.save_variables; saves is_nozzle_setting VALUE
- **Commands**: all exist (built-in/module commands used: RESPOND, SAVE_VARIABLE) - checked 2026-11-18
- **Risk**: none  |  **Tags**: tool-change  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_MATCH_STATE
- **File / lines**: rpi_nozzle.cfg L253-258 (gcode_macro)
- **What it does**: Memory of WM_EXTRUDER_SETUP (Set Up): the dock that was empty after each pick (do not run)
- **Calls**: -
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: actual, next
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: none) - checked 2026-11-18
- **Risk**: none  |  **Tags**: misc  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_MATCH_NEXT
- **File / lines**: rpi_nozzle.cfg L259-262 (delayed_gcode timer)
- **What it does**: Next step of the flow matching run.
- **Calls**: _WM_MATCH_STEP
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: none) - checked 2026-11-18
- **Risk**: none (+ through the macros it calls: ACE, HEATS, MOVES THE TOOLHEAD)  |  **Tags**: misc  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_MATCH_CHECK
- **File / lines**: rpi_nozzle.cfg L263-297 (gcode_macro)
- **What it does**: Stop unless the matching can start
- **Calls**: _WM_NCHANGE_CHECK
- **Called by**: WM_EXTRUDER_SETUP, _WM_MATCH_RUN
- **Variables**: -
- **Uses**: reads printer.configfile, printer.save_variables
- **Commands**: all exist (built-in/module commands used: none) - checked 2026-11-18
- **Risk**: none  |  **Tags**: misc  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### WM_EXTRUDER_SETUP
- **File / lines**: rpi_nozzle.cfg L298-318 (gcode_macro)
- **What it does**: The screen's Extruder Setup page: instructions and Set Up, which matches the tool heads to their CAN ids (app: General > Extruder Setup)
- **Calls**: _WM_MATCH_CHECK
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: reads printer.configfile, printer.save_variables
- **Commands**: all exist (built-in/module commands used: RESPOND) - checked 2026-11-18
- **Risk**: ACE  |  **Tags**: misc  |  **Fluidd**: RPI Calibration
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_MATCH_RUN
- **File / lines**: rpi_nozzle.cfg L319-337 (gcode_macro)
- **What it does**: Matching, step 2: home, park the tool on the carriage, then pick the tools one by one
- **Calls**: PARK_CURRENT_TOOL, _WM_MATCH_CHECK, _WM_MATCH_STEP
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: reads printer.save_variables, printer.toolhead; sets variables of _WM_MATCH_STATE; saves is_nozzle_setting VALUE
- **Commands**: all exist (built-in/module commands used: G28, M400, RESPOND, SAVE_VARIABLE, SET_GCODE_VARIABLE) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD (+ through the macros it calls: ACE, HEATS)  |  **Tags**: misc  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_MATCH_STEP
- **File / lines**: rpi_nozzle.cfg L338-352 (gcode_macro)
- **What it does**: Matching: pick up tool N and see which dock came out empty
- **Calls**: _WM_MATCH_AFTER, _WM_MATCH_STOP
- **Called by**: _WM_MATCH_NEXT, _WM_MATCH_RUN
- **Variables**: -
- **Uses**: reads printer.save_variables
- **Commands**: all exist (built-in/module commands used: G4, M400, RESPOND) - checked 2026-11-18
- **Risk**: none (+ through the macros it calls: ACE, HEATS, MOVES THE TOOLHEAD)  |  **Tags**: misc  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_MATCH_AFTER
- **File / lines**: rpi_nozzle.cfg L353-380 (gcode_macro)
- **What it does**: Matching: note the empty dock after the pick of tool N, then go on with the next tool or finish
- **Calls**: _WM_MATCH_FINISH, _WM_MATCH_STOP
- **Called by**: _WM_MATCH_STEP
- **Variables**: -
- **Uses**: reads printer.save_variables; sets variables of _WM_MATCH_STATE
- **Commands**: all exist (built-in/module commands used: RESPOND, SET_GCODE_VARIABLE, UPDATE_DELAYED_GCODE) - checked 2026-11-18
- **Risk**: none (+ through the macros it calls: ACE, HEATS, MOVES THE TOOLHEAD)  |  **Tags**: misc  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_MATCH_FINISH
- **File / lines**: rpi_nozzle.cfg L381-432 (gcode_macro)
- **What it does**: Matching: park the tool, switch off, show what the result means
- **Calls**: PARK_CURRENT_TOOL
- **Called by**: _WM_MATCH_AFTER
- **Variables**: -
- **Uses**: reads printer.configfile, printer.save_variables; saves is_nozzle_setting VALUE
- **Commands**: all exist (built-in/module commands used: M400, RESPOND, SAVE_VARIABLE) - checked 2026-11-18
- **Risk**: none (+ through the macros it calls: ACE, HEATS, MOVES THE TOOLHEAD)  |  **Tags**: misc  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_RESTART_KLIPPER
- **File / lines**: rpi_nozzle.cfg L433-439 (gcode_macro)
- **What it does**: Close the open Fluidd window, then restart Klipper (the Restart Klipper now button)
- **Calls**: -
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: G4, RESPOND, RESTART) - checked 2026-11-18
- **Risk**: none  |  **Tags**: misc  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_MATCH_APPLY
- **File / lines**: rpi_nozzle.cfg L440-453 (gcode_macro)
- **What it does**: Matching, last step: write the four CAN ids and restart the firmware
- **Calls**: -
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: reads printer.configfile, printer.print_stats
- **Commands**: all exist (built-in/module commands used: FIRMWARE_RESTART, RESPOND, RUN_SHELL_COMMAND) - checked 2026-11-18
- **Risk**: none  |  **Tags**: misc  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_MATCH_STOP
- **File / lines**: rpi_nozzle.cfg L454-490 (gcode_macro)
- **What it does**: Matching stopped: switch is_nozzle_setting off and say why, nothing is written
- **Calls**: -
- **Called by**: _WM_MATCH_AFTER, _WM_MATCH_STEP
- **Variables**: -
- **Uses**: reads printer.cfg; saves is_nozzle_setting VALUE
- **Commands**: all exist (built-in/module commands used: RESPOND, SAVE_VARIABLE) - checked 2026-11-18
- **Risk**: none  |  **Tags**: misc  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### WM_AUTO_SPEED
- **File / lines**: rpi_nozzle.cfg L509-527 (gcode_macro)
- **What it does**: Window: speed test of the X and Y motors (finds the highest acceleration and speed without lost steps). Needs a calibrated input shaper
- **Calls**: -
- **Called by**: _WM_AUTO_SPEED_REOPEN
- **Variables**: -
- **Uses**: reads printer.auto_speed
- **Commands**: all exist (built-in/module commands used: RESPOND) - checked 2026-11-18
- **Risk**: none  |  **Tags**: calibration  |  **Fluidd**: RPI Calibration
- **Tested**: moved into rpi_nozzle.cfg 2026-11-18 (2.21.1), NOT tested after the move
### _WM_AUTO_SPEED_READY
- **File / lines**: rpi_nozzle.cfg L528-539 (gcode_macro)
- **What it does**: Checks before a speed test, then homes when needed and takes T0 when the carriage is empty
- **Calls**: T0, _WM_CAL_PRECHECK
- **Called by**: WM_AUTO_SPEED_VALIDATE, _WM_AUTO_SPEED_RUN
- **Variables**: -
- **Uses**: reads printer.save_variables, printer.toolhead
- **Commands**: all exist (built-in/module commands used: G28, RESPOND) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD (+ through the macros it calls: ACE, HEATS)  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_AUTO_SPEED_RUN
- **File / lines**: rpi_nozzle.cfg L540-553 (gcode_macro)
- **What it does**: Runs the speed test (called by the Start button of WM_AUTO_SPEED). Refused without a calibrated input shaper
- **Calls**: _WM_AUTO_SPEED_READY, _WM_AUTO_SPEED_RESULT, _WM_FAIL
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: reads printer.auto_speed
- **Commands**: all exist (built-in/module commands used: AUTO_SPEED, RESPOND) - checked 2026-11-18
- **Risk**: none (+ through the macros it calls: ACE, HEATS, MOVES THE TOOLHEAD)  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### WM_AUTO_SPEED_VALIDATE
- **File / lines**: rpi_nozzle.cfg L554-570 (gcode_macro)
- **What it does**: Runs a fast pattern 50 times with ACCEL and VELOCITY and checks for lost steps. Without values it uses the limits of the printer
- **Calls**: _WM_AUTO_SPEED_READY, _WM_AUTO_SPEED_RESULT, _WM_FAIL
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: reads printer.configfile, printer.max_accel, printer.max_velocity
- **Commands**: all exist (built-in/module commands used: AUTO_SPEED_VALIDATE, G1, G90, RESPOND) - checked 2026-11-18
- **Risk**: MOVES THE TOOLHEAD (+ through the macros it calls: ACE, HEATS)  |  **Tags**: calibration  |  **Fluidd**: RPI Calibration
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_AUTO_SPEED_RESULT
- **File / lines**: rpi_nozzle.cfg L576-616 (gcode_macro)
- **What it does**: Window with the last speed test result: Check first, Save (writes printer.cfg), Do not save. No Save without input shaper
- **Calls**: _WM_FAIL
- **Called by**: WM_AUTO_SPEED_VALIDATE, _WM_AUTO_SPEED_RUN
- **Variables**: -
- **Uses**: reads printer.auto_speed, printer.cfg, printer.configfile
- **Commands**: all exist (built-in/module commands used: RESPOND) - checked 2026-11-18
- **Risk**: ACE  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_AUTO_SPEED_SAVE
- **File / lines**: rpi_nozzle.cfg L617-638 (gcode_macro)
- **What it does**: Writes ACCEL and VELOCITY into [printer] of printer.cfg (Save button of the speed test window)
- **Calls**: _WM_FAIL
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: reads printer.auto_speed, printer.cfg, printer.print_stats
- **Commands**: all exist (built-in/module commands used: RESPOND, RUN_SHELL_COMMAND) - checked 2026-11-18
- **Risk**: none  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_AUTO_SPEED_RESTART
- **File / lines**: rpi_nozzle.cfg L639-648 (gcode_macro)
- **What it does**: Restarts Klipper after the speed limits were saved (refused while a print runs)
- **Calls**: _WM_FAIL
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: reads printer.print_stats
- **Commands**: all exist (built-in/module commands used: RESPOND, RESTART) - checked 2026-11-18
- **Risk**: none  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_AUTO_SPEED_SHAPER
- **File / lines**: rpi_nozzle.cfg L649-655 (gcode_macro)
- **What it does**: Calibrate input shaper button (WM_VIBRATION_COMP, SAVE_CONFIG restarts Klipper, then the speed test window opens again)
- **Calls**: WM_VIBRATION_COMP
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: saves wm_as_reopen VALUE
- **Commands**: all exist (built-in/module commands used: RESPOND, SAVE_VARIABLE) - checked 2026-11-18
- **Risk**: none (+ through the macros it calls: LOAD CELL / SETTER, MOVES THE TOOLHEAD)  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_AUTO_SPEED_REOPEN
- **File / lines**: rpi_nozzle.cfg L656-666 (delayed_gcode timer)
- **What it does**: Reopens the auto-speed result window after the run.
- **Calls**: WM_AUTO_SPEED
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: reads printer.auto_speed, printer.save_variables; saves wm_as_reopen VALUE
- **Commands**: all exist (built-in/module commands used: RESPOND, SAVE_VARIABLE) - checked 2026-11-18
- **Risk**: none  |  **Tags**: calibration  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md

## rpi_pi.cfg
Installer part: Pi/board sensors, chamber light

### WM_CHAMBER_LIGHT
- **File / lines**: rpi_pi.cfg L80-89 (gcode_macro)
- **What it does**: Chamber light STATE=on, off or toggle (default toggle)
- **Calls**: -
- **Called by**: START_PRINT
- **Variables**: -
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: none) - checked 2026-11-18
- **Risk**: none  |  **Tags**: light  |  **Fluidd**: ZR Tools
- **Tested**: F-008 tested 2026-11-14

## rpi_stats.cfg
ACE panel: tool change and print time statistics

### _WM_STATS
- **File / lines**: rpi_stats.cfg L22-28 (gcode_macro)
- **What it does**: Counters for tool changes and print time per head (state only).
- **Calls**: -
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: last, last_dur, pend, pend_tool
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: none) - checked 2026-11-18
- **Risk**: none  |  **Tags**: stats  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_STATS_TICK
- **File / lines**: rpi_stats.cfg L29-64 (gcode_macro)
- **What it does**: Counts tool changes and the print time of the toolhead on the carriage (called every 2 s by _WM_STATS_POLL)
- **Calls**: -
- **Called by**: _WM_STATS_POLL
- **Variables**: -
- **Uses**: reads printer.print_stats, printer.save_variables; sets variables of _WM_STATS; saves wm_stat_changes VALUE, wm_stat_head{cur} VALUE, wm_stat_time{pt} VALUE
- **Commands**: all exist (built-in/module commands used: SAVE_VARIABLE, SET_GCODE_VARIABLE) - checked 2026-11-18
- **Risk**: none  |  **Tags**: stats  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### _WM_STATS_POLL
- **File / lines**: rpi_stats.cfg L65-70 (delayed_gcode timer)
- **What it does**: Timer: calls _WM_STATS_TICK every 2 s.
- **Calls**: _WM_STATS_TICK
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: -
- **Commands**: all exist (built-in/module commands used: UPDATE_DELAYED_GCODE) - checked 2026-11-18
- **Risk**: none  |  **Tags**: stats  |  **Fluidd**: —
- **Tested**: no per-macro record in FIX-LOG.md
### WM_STATS_RESET
- **File / lines**: rpi_stats.cfg L71-81 (gcode_macro)
- **What it does**: Set the tool-change counters and the print time per toolhead back to 0
- **Calls**: -
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: sets variables of _WM_STATS; saves wm_stat_changes VALUE, wm_stat_head{h} VALUE, wm_stat_time{h} VALUE
- **Commands**: all exist (built-in/module commands used: RESPOND, SAVE_VARIABLE, SET_GCODE_VARIABLE) - checked 2026-11-18
- **Risk**: none  |  **Tags**: stats  |  **Fluidd**: AcePro
- **Tested**: no per-macro record in FIX-LOG.md
### WM_SET_TOOL_MAP
- **File / lines**: rpi_stats.cfg L82-112 (gcode_macro)
- **What it does**: WM_SET_TOOL_MAP MAP=0:2,1:3 [FILE=name] [KEEP_EXISTING=1] - print tool -> toolhead, for the next print
- **Calls**: -
- **Called by**: - (entry point: Fluidd / screen / slicer / console)
- **Variables**: -
- **Uses**: reads printer.print_stats, printer.save_variables; saves box_modify_t{p[0]} VALUE, box_modify_t{p[0]}_backup VALUE
- **Commands**: all exist (built-in/module commands used: RESPOND, SAVE_VARIABLE) - checked 2026-11-18
- **Risk**: ACE  |  **Tags**: tool-change  |  **Fluidd**: AcePro
- **Tested**: no per-macro record in FIX-LOG.md

## Call map (macro -> macros it calls)
```
_UNLOCK_TOOL -> SET_GCODE_OFFSET, UNLOCK, _CHECK_AND_UNLOCK, z_rise
_CHECK_AND_UNLOCK -> UNLOCK, UNLOCK_TOOL_FINISH
LOCK -> _LOCK_CHECK
_LOCK_TOOL -> SET_GCODE_OFFSET, _CHECK_AND_LOCK, _CHECK_T_SEQUENCE, z_rise
_CHECK_AND_LOCK -> LOCK, _LOCK_TOOL_FINISH
_LOCK_TOOL_FINISH -> UNLOCK
T0 -> _CHANGE_TOOL
T1 -> _CHANGE_TOOL
T2 -> _CHANGE_TOOL
T3 -> _CHANGE_TOOL
_CHANGE_TOOL -> _CHANGING_TOOL, _CHECK_CHANGE_TOOL, _CHECK_CHANGE_TOOL_AGAIN, _WM_CAL_CLEARANCE, _check_current_extruder_value, _check_hall_sensor, _check_tool_exist
_CHECK_CHANGE_TOOL_AGAIN -> _CHECK_CHANGE_TOOL
_CHANGING_TOOL -> _LOCK_TOOL, _UNLOCK_TOOL, _descend_z, _raise_z
_CHECK_CHANGE_TOOL -> M221, PAUSE, _CHANGING_TOOL, _ENABLE_SENSOR, _OFFSET_SET, _WAIT_TOOL_TEMPERATURE, _check_current_extruder_value, _check_hall_sensor, _check_tool_exist
_WAIT_TOOL_TEMPERATURE -> _WM_HEAT_AT_WIPE, _WM_HEAT_BACK
_SAVE_TOOL_POSITION -> SAVE_T_POSITON
CALIBRATE_TOOL_POSITION -> _SAVE_TOOL_POSITION
PARK_CURRENT_TOOL -> PARK_CURRENT_TOOL_RETRY, _UNLOCK_TOOL
PARK_CURRENT_TOOL_RETRY -> _UNLOCK_TOOL
_OFFSET_SET -> SET_GCODE_OFFSET
delayed_pause0 -> PAUSE
delayed_pause1 -> PAUSE
delayed_pause2 -> PAUSE
delayed_pause3 -> PAUSE
WIPE_NOZZLE -> _WM_CAL_CLEARANCE, z_rise
CALIBRATE_WIPE_POSITION -> _SAVE_WIPE_POSITION
PRINTER_INIT -> RESET_FLOW_EXTRUDER
START_PRINT -> BED_MESH_CALIBRATE, M104, M109, M190, SET_GCODE_OFFSET, WIPE_NOZZLE, WM_CHAMBER_LIGHT, _WM_BED_SOAK, _WM_BED_SOAK_MARK, _WM_LIVEZ_RESET, _WM_START_PURGE
PRINT_END -> M107, PARK_CURRENT_TOOL, RESET_FLOW_EXTRUDER, WIPE_NOZZLE
PAUSE -> E_axis_move, M104, M106
RESUME -> ACE_WM_ASSIST, E_axis_move, M104, M106, M109, M190, WIPE_NOZZLE, _WM_GO_WIPE, _WM_Z_TRIM_APPLY
CANCEL_PRINT -> E_axis_move, M107, PARK_CURRENT_TOOL, RESET_FLOW_EXTRUDER, WIPE_NOZZLE
G29 -> BED_MESH_CALIBRATE, M104, M109, M190, T0, WIPE_NOZZLE, _WM_GO_WIPE
M107 -> M106
M191 -> M104, M106
EXTRUDE_FILAMENT -> M106, M109, PARK_CURRENT_TOOL, WIPE_NOZZLE, z_rise
RETRACT_FILAMENT -> z_rise
LOAD_FILAMENT -> M104, M109, PARK_CURRENT_TOOL, WIPE_NOZZLE, _CHANGE_TOOL, _WM_GO_WIPE_HEAT
UNLOAD_FILAMENT -> M104, M109, PARK_CURRENT_TOOL, WIPE_NOZZLE, _CHANGE_TOOL, _WM_GO_WIPE_HEAT
RESET_FLOW_EXTRUDER -> M221
filament_insert_gcode -> M109, WIPE_NOZZLE, z_rise
NOZZLE_PREPARE -> M104, M106, M109, SET_GCODE_OFFSET, _APPLY_PRE_Z_OFFSET, _WM_CAL_CLEARANCE, _WM_GO_WIPE
NOZZLE_CALIBRATE_TOOL_OFFSET -> M104, M109
RAPID_MODE -> CALIBRATE_TOOL_OFFSET, CALIBRATE_TOOL_Z_OFFSET, M104, SAVE_TOOL_OFFSET
CALIBRATE_TOOL_OFFSET -> SET_GCODE_OFFSET, T0, _APPLY_PRE_Z_OFFSET, _WM_CAL_CLEARANCE
CALIBRATE_OFFSET_ALL_RAPID_MODE -> RAPID_MODE
CALIBRATE_OFFSET_ALL_FINE_MODE -> NOZZLE_CALIBRATE_TOOL_OFFSET, NOZZLE_PREPARE, RAPID_MODE
CALIBRATE_TOOL_Z_OFFSET -> SET_GCODE_OFFSET, _OFFSET_SET, _SAVE_PROBE_POS, _WM_CAL_CLEARANCE
SAVE_TOOL_OFFSET -> SAVE_T_OFFSET
POP -> M104, M106, M109, _WM_GO_WIPE
_WM_ACE_FAIL -> _WM_ACE_FINISH, _WM_UNLOAD_ABORT
_WM_ACE_GRAB -> _WM_GO_WIPE_HEAT
SET_GCODE_OFFSET -> _WM_LIVEZ_SGO
_WM_ACE_HOME -> SET_GCODE_OFFSET, WIPE_NOZZLE, _WM_ACE_HOME_Z, z_rise
_WM_ACE_HOME_Z -> _OFFSET_SET, z_rise
ACE_WM_LOAD -> _CHANGE_TOOL, _WM_ACE_HOME, _WM_GO_WIPE, z_rise
ACE_WM_UNLOAD -> _CHANGE_TOOL, _WM_ACE_HOME, _WM_ACE_UNLOAD_RUN, z_rise
_WM_ACE_UNLOAD_RUN -> ACE_WM_RETRACT, _WM_UNLOAD_TIP
ACE_WM_STOP -> WM_UNLOAD_STOP, _WM_ACE_FINISH
_wm_ace_tick -> PARK_CURRENT_TOOL, _WM_ACE_FAIL, _WM_ACE_FINISH, _WM_ACE_HEAD
_wm_ace_watch -> ACE_WM_LOAD, _WM_ACE_ASK_LOAD, _WM_ACE_ASSIST_SYNC
_WM_ACE_ASK_YES -> ACE_WM_LOAD
WM_SAFETY_START -> _WM_SAFETY_CHECK
WM_PRINT_END_WATCH -> PRINT_END, _WM_PAUSE_STATE
WM_TOOL_LEDS -> _RGB_CURRENT, _RGB_LOAD, _RGB_UNLOAD
_WM_HEAD_LOAD -> M104, M109, PARK_CURRENT_TOOL, _WM_ACE_GRAB, _WM_ACE_HEAD, _WM_ACE_HEAD_DONE, filament_insert, filament_insert_gcode
WM_HEAD_SENSOR_WATCH -> _WM_HEAD_LOAD
WM_UNLOAD_STOP -> _WM_UNLOAD_RESET
_WM_UNLOAD_ABORT -> _WM_UNLOAD_RESET
_WM_UNLOAD_END -> PARK_CURRENT_TOOL, _WM_UNLOAD_RESET
_wm_unload_runner -> ACE_WM_UNLOAD, ZR_RETRACT, _WM_UNLOAD_END, _WM_UNLOAD_RESET
SET_GCODE_OFFSET -> _WM_LIVEZ_SGO
z_rise -> _z_rise_run
Z_HOMING -> SET_GCODE_OFFSET, T0, WIPE_NOZZLE, _LEVELING_TRIGGER_S
_WM_BEDWARP_START -> SET_GCODE_OFFSET, T0, WIPE_NOZZLE, _WM_BEDWARP_ROUND, _WM_BEDWARP_SETSTART, _WM_CAL_CLEARANCE, _WM_CAL_PRECHECK, _WM_FAIL
_WM_BEDWARP_ROUND -> _WM_BEDWARP_REPORT, _WM_BEDWARP_STORE
_WM_BEDWARP_TICK -> _WM_BEDWARP_FINISH, _WM_BEDWARP_ROUND
_WM_BEDWARP_FINISH -> _WM_BED_SOAK_STORE
WM_BED_SOAK -> _WM_FAIL
_WM_START_PURGE -> _WM_START_PURGE_RUN
_WM_START_PURGE_RUN -> _CHANGE_TOOL, _WM_LINE_PURGE, _WM_PURGE_HEAT, _WM_WIPE_PURGE
_WM_GO_WIPE -> _WM_CAL_CLEARANCE, z_rise
_WM_PURGE_HEAT -> _WM_LIVEZ_HEAT
_WM_WIPE_PURGE -> _CHANGE_TOOL, _WM_WIPE_PURGE_GO
_WM_WIPE_PURGE_GO -> WIPE_NOZZLE, _WM_PURGE_ASSIST, _WM_PURGE_HEAT
_WM_CAL_STOP -> M106
_WM_CAL_PRECHECK -> _WM_FAIL
WM_BED_LEVELING -> G29, _WM_CAL_ASK, _WM_CAL_PRECHECK
WM_SCREWS_CAL -> M104, M109, M190, T0, WIPE_NOZZLE, _WM_CAL_ASK, _WM_CAL_PRECHECK, _WM_FAIL
WM_PROBE_CALIBRATE -> M190, PROBE_CALIBRATE, _WM_CAL_ASK, _WM_CAL_PRECHECK
_WM_OFFSET_CHECK -> M106, SAVE_T_OFFSET, _WM_FAIL
WM_OFFSETS_RAPID -> M106, PARK_CURRENT_TOOL, RAPID_MODE, WIPE_NOZZLE, _WM_CAL_ASK, _WM_CAL_CLEARANCE, _WM_CAL_PRECHECK, _WM_OFFSET_CHECK, _WM_WAIT_TEMP
WM_OFFSETS_ACCURATE -> NOZZLE_CALIBRATE_TOOL_OFFSET, PARK_CURRENT_TOOL, RAPID_MODE, _WM_CAL_ASK, _WM_CAL_PRECHECK, _WM_FAIL, _WM_NOZZLE_PREPARE, _WM_OFFSET_CHECK, _WM_ZCAL_AFTER_ACCURATE
_WM_NOZZLE_PREPARE -> M104, M106, M109, SET_GCODE_OFFSET, _APPLY_PRE_Z_OFFSET, _WM_FAIL, _WM_GO_WIPE
WM_VIBRATION_COMP -> _WM_CAL_ASK, _WM_CAL_PRECHECK
WM_NOZZLE_FULL_PID -> M106, PARK_CURRENT_TOOL, _WM_CAL_PRECHECK, _WM_FAIL, _WM_NOZZLE_FULL_PID_RESULT, _WM_PID_HEAD
_WM_PID_HEAD -> M106, WIPE_NOZZLE, _WM_CAL_CLEARANCE
_WM_NOZZLE_FULL_PID_RESULT -> _WM_FAIL
WM_BED_PID -> _WM_CAL_ASK, _WM_CAL_PRECHECK
WM_FIRST_RUN_CAL -> _WM_CAL_PRECHECK
_WM_FIRST_RUN_CAL -> M106, WM_BED_LEVELING, WM_BED_PID, WM_NOZZLE_FULL_PID, WM_OFFSETS_RAPID, WM_OFFSETS_Z_HOT, WM_VIBRATION_COMP, _WM_CAL_PRECHECK, _WM_FIRST_RUN_CAL_DONE, _WM_SETTER_AUTO
WM_Z_TRIM -> _WM_Z_TRIM_APPLY
_WM_Z_TRIM_APPLY -> _OFFSET_SET
_WM_Z_TRIM_WIN -> _WM_FAIL
_WM_Z_TRIM_STEP -> WM_Z_TRIM, _WM_FAIL, _WM_Z_TRIM_WIN
_WM_Z_TRIM_RESET -> WM_Z_TRIM_MENU, _WM_Z_TRIM_APPLY
WM_NOZZLE_GROWTH -> _WM_GROWTH_PIN_SET, _WM_Z_TRIM_APPLY
_WM_GROWTH_PIN_SYNC -> _WM_GROWTH_PIN_SET, _WM_Z_TRIM_APPLY
WM_GROWTH_PIN_WATCH -> _WM_GROWTH_PIN_SYNC
_WM_WAIT_TEMP -> _WM_WAIT_TEMP_STEP
_WM_Z_TOUCH -> M106, SET_GCODE_OFFSET, WIPE_NOZZLE, _OFFSET_SET, _WM_CAL_CLEARANCE, _WM_FAIL, _WM_WAIT_TEMP, _WM_Z_TOUCH_STORE
WM_OFFSETS_Z_HOT -> M106, M190, PARK_CURRENT_TOOL, _CHANGE_TOOL, _WM_CAL_PRECHECK, _WM_WAIT_TEMP, _WM_ZHOT_RESULT, _WM_Z_TOUCH
_WM_ZHOT_RESULT -> SAVE_T_OFFSET
WM_NOZZLE_GROWTH_CAL -> M106, M190, PARK_CURRENT_TOOL, _CHANGE_TOOL, _WM_CAL_PRECHECK, _WM_FAIL, _WM_GROWTH_RESULT, _WM_WAIT_TEMP, _WM_Z_TOUCH
_WM_GROWTH_RESULT -> _WM_GROWTH_PIN_SET
_WM_ZCAL_WIN -> _WM_FAIL
_WM_ZCAL_RUN -> WM_NOZZLE_GROWTH_CAL, WM_OFFSETS_Z_HOT, _WM_FAIL, _WM_SETTER_GO, _WM_ZCAL_DONE
_WM_ZCAL_AFTER_ACCURATE -> _WM_ZCAL_DONE
_WM_LIVEZ_SGO -> WM_LIVE_Z_ZERO
WM_LIVE_Z_ZERO -> _WM_Z_TRIM_APPLY
_WM_LIVEZ_HEAT -> _OFFSET_SET
_WM_LIVEZ_SAVE -> _WM_Z_TRIM_APPLY
_WM_LIVEZ_DROP -> _WM_Z_TRIM_APPLY
_WM_LIVEZ_WATCH -> WM_LIVE_Z_MENU
Z_OFFSET_APPLY_PROBE -> WM_LIVE_Z_MENU
Z_OFFSET_APPLY_ENDSTOP -> WM_LIVE_Z_MENU
WM_SETTER_PROBE_POSITION -> _WM_FAIL
_WM_SETTER_GO -> SET_GCODE_OFFSET, T0, _WM_CAL_CLEARANCE, _WM_CAL_PRECHECK, _WM_FAIL, _WM_SETTER_MOVE
_WM_SETTER_MOVE -> _WM_FAIL, _WM_SETTER_SENSE
_WM_SETTER_SENSE -> _WM_SETTER_DOWN
_WM_SETTER_DOWN -> _WM_FAIL, _WM_SETTER_AWAY, _WM_SETTER_FIND, _WM_SETTER_WIN, _WM_ZCAL_DONE
_WM_SETTER_WIN -> _WM_FAIL
_WM_SETTER_STEP -> _WM_FAIL, _WM_SETTER_WIN
_WM_SETTER_SAVE -> _WM_FAIL, _WM_SETTER_AFTER
_WM_SETTER_CLOSE -> _WM_SETTER_AWAY
_WM_SETTER_TEST -> CALIBRATE_TOOL_OFFSET, _WM_CAL_PRECHECK, _WM_SETTER_AFTER, _WM_SETTER_AWAY
_WM_SETTER_RAPID -> WM_OFFSETS_RAPID, _WM_SETTER_AWAY
_WM_SETTER_RESTORE -> _WM_FAIL, _WM_SETTER_AFTER, _WM_SETTER_AWAY
_WM_SETTER_FIND -> _WM_FAIL, _WM_SETTER_FIND_TOP
_WM_SETTER_FIND_TOP -> _WM_SETTER_FIND_SIDES
_WM_SETTER_FIND_FAIL -> _WM_FAIL, _WM_SETTER_AWAY, _WM_SETTER_MOVE, _WM_SETTER_WIDE_ASK, _WM_ZCAL_DONE
_WM_SETTER_WIDE_CANCEL -> _WM_SETTER_MOVE
_WM_SETTER_FIND_SIDES -> _WM_SETTER_FIND_FAIL, _WM_SETTER_FIND_FAR
_WM_SETTER_FIND_FAR -> _WM_SETTER_FIND_DONE, _WM_SETTER_FIND_FAIL
_WM_SETTER_FIND_DONE -> WM_OFFSETS_RAPID, _WM_SETTER_AWAY, _WM_SETTER_FIND_FAIL, _WM_SETTER_FOUND, _WM_SETTER_MID, _WM_ZCAL_DONE
_WM_SETTER_FOUND -> _WM_FAIL
_WM_SETTER_SCRATCH_GO -> _WM_FAIL, _WM_SETTER_SCRATCH_Y
_WM_SETTER_SCRATCH_Y -> _WM_SETTER_FIND_FAIL, _WM_SETTER_SCRATCH_DONE
_WM_SETTER_SCRATCH_DONE -> _WM_SETTER_FIND_FAIL, _WM_SETTER_FIND_TOP
_WM_SETTER_MID -> _WM_FAIL, _WM_SETTER_MID_B
_WM_SETTER_MID_B -> _WM_SETTER_MID_C
_WM_SETTER_MID_C -> _WM_SETTER_MID_D
_WM_SETTER_MID_D -> _WM_SETTER_MID_DONE, _WM_SETTER_MID_E
_WM_SETTER_MID_E -> _WM_SETTER_MID_DONE
_WM_SETTER_MID_DONE -> _WM_SETTER_AUTO_FINISH, _WM_SETTER_FOUND
_WM_SETTER_MID_SAVE -> _WM_FAIL, _WM_SETTER_AFTER, _WM_SETTER_AWAY
_WM_SETTER_AUTO -> _WM_SETTER_AUTO_CHECK, _WM_SETTER_GO
_WM_SETTER_AUTO_CHECK -> _WM_FAIL
_WM_SETTER_AUTO_FINISH -> _WM_FAIL, _WM_SETTER_AWAY, _WM_SETTER_MID_SAVE
_WM_ENDLESS_WATCH -> _WM_ENDLESS_TICK
_WM_ENDLESS_TICK -> WM_ENDLESS_CONTINUE
WM_ENDLESS_CONTINUE -> _CHANGE_TOOL, _WM_ENDLESS_3
_WM_ENDLESS_3 -> RESUME, _WM_ENDLESS_4
_WM_ENDLESS_4 -> _OFFSET_SET
WM_FAN_GUARD -> PAUSE
WM_NOZZLE_CHANGE -> _WM_NCHANGE_CHECK
_WM_NCHANGE_RUN -> _UNLOCK_TOOL, _WM_NCHANGE_AFTER, _WM_NCHANGE_CHECK, _WM_NCHANGE_FAILED
_WM_NCHANGE_AFTER -> _WM_NCHANGE_FAILED
_WM_MATCH_NEXT -> _WM_MATCH_STEP
_WM_MATCH_CHECK -> _WM_NCHANGE_CHECK
WM_EXTRUDER_SETUP -> _WM_MATCH_CHECK
_WM_MATCH_RUN -> PARK_CURRENT_TOOL, _WM_MATCH_CHECK, _WM_MATCH_STEP
_WM_MATCH_STEP -> _WM_MATCH_AFTER, _WM_MATCH_STOP
_WM_MATCH_AFTER -> _WM_MATCH_FINISH, _WM_MATCH_STOP
_WM_MATCH_FINISH -> PARK_CURRENT_TOOL
_WM_AUTO_SPEED_READY -> T0, _WM_CAL_PRECHECK
_WM_AUTO_SPEED_RUN -> _WM_AUTO_SPEED_READY, _WM_AUTO_SPEED_RESULT, _WM_FAIL
WM_AUTO_SPEED_VALIDATE -> _WM_AUTO_SPEED_READY, _WM_AUTO_SPEED_RESULT, _WM_FAIL
_WM_AUTO_SPEED_RESULT -> _WM_FAIL
_WM_AUTO_SPEED_SAVE -> _WM_FAIL
_WM_AUTO_SPEED_RESTART -> _WM_FAIL
_WM_AUTO_SPEED_SHAPER -> WM_VIBRATION_COMP
_WM_AUTO_SPEED_REOPEN -> WM_AUTO_SPEED
_WM_STATS_POLL -> _WM_STATS_TICK
TIMELAPSE_TAKE_FRAME -> SET_GCODE_OFFSET, _TIMELAPSE_NEW_FRAME
_TIMELAPSE_NEW_FRAME -> HYPERLAPSE
_WAIT_TIMELAPSE_TAKE_FRAME -> M221
HYPERLAPSE -> TIMELAPSE_TAKE_FRAME
_HYPERLAPSE_LOOP -> TIMELAPSE_TAKE_FRAME
TEST_STREAM_DELAY -> _TIMELAPSE_NEW_FRAME
ZR_CHAMBER -> M141
_WM_GO_WIPE_HEAT -> _WM_CAL_CLEARANCE, z_rise
_WM_UNLOAD_TIP -> WIPE_NOZZLE, _WM_GO_WIPE_HEAT
ZR_LOAD -> _CHANGE_TOOL, _WM_GO_WIPE_HEAT, _WM_ZR_LOAD_GO
_WM_ZR_LOAD_GO -> PARK_CURRENT_TOOL, SET_GCODE_OFFSET, WIPE_NOZZLE, _WM_PURGE_ASSIST
ZR_RETRACT -> PARK_CURRENT_TOOL, SET_GCODE_OFFSET, _CHANGE_TOOL, _WM_UNLOAD_TIP
ZR_UNLOAD -> ZR_RETRACT
```

## Files done / files left (reading status, updated 2026-11-19)
| File | Status |
|---|---|
| printer.cfg, zru-s.cfg, wm_zru_*.cfg, tmt1.ini, rpi-ultra-install.conf, hub.cfg, load_cell.cfg, change_extruder.cfg, extruder0.cfg, fz-wipe-nozzle.cfg, rpi_pi.cfg, rpi_fan_guard.cfg, rpi_ace_driver.cfg, moonraker.conf | **read line by line** |
| macros.cfg, change_macros.cfg, offset_calibrate.cfg, zr_tools.cfg, timelapse.cfg, rpi_endless.cfg, rpi_stats.cfg | **read line by line 2026-11-19** (repo copies; change_macros.cfg and the macros.cfg RESUME variables were confirmed equal to the Pi snapshot, the other copies were not compared line by line) |
| rpi_ace.cfg (24) | **read line by line 2026-11-18** (see its section) |
| rpi_nozzle.cfg (31) | **read line by line 2026-11-18** (see its section) |
| rpi_base.cfg (52) | **read line by line 2026-11-19** (see its section) |
| rpi_calibration.cfg (97) | **read line by line 2026-11-19** (see its section) |
| extruder1-3.cfg, crowsnest.conf, saved_variables.cfg, timelapse sections, `.json` status files | not read line by line (extruder1-3 are copies of extruder0 with the number changed) |
| Fluidd patch (31 commits, 8158 lines) | **final patched files read 2026-11-19** (see FLUIDD.md "Patch read line by line"); style blocks, specs and SVGs not read |
| ACE driver `extras/ace/*.py` (25 files, 19,079 lines) + `extras/temperature_ace.py`, `extras/virtual_pins.py` (460 lines) | **read line by line 2026-11-19** (see its section); not compared with upstream |
| Panel repo scripts/, other extras | file lists and README read only |

Everything under "Calls / Called by / Variables / Uses / Commands / Risk" is extracted by script from the whole text of every file, so it covers all files; only the plain-words line for macros marked *(structure only)* and any deeper logic checks are still open.

## Known problems (found while building this document; reported, not fixed)
0. **Correction 2026-11-19**: the earlier note about a possible `#XYZ:` G-code line in `[homing_override]` (rpi_base.cfg) was wrong; Klipper strips ` #` and ` ;` comments when it reads the config. Not a problem.
1. **Deprecated accessor** `printer.gcode_move.gcode_position.e` in timelapse.cfg L264 (the `.e` accessor is deprecated since Klipper 20251106, Config_Changes.md). Still works today; use `position[printer.gcode_move.axis_map.E]` later. (Third-party moonraker-timelapse file.)
2. **Input shaper** in SAVE_CONFIG is `3hump_ei` X 96.2 Hz: Klipper changed the definitions of EI, 2HUMP_EI and 3HUMP_EI on 20250916 and recommends recalibrating those shapers (Config_Changes.md).
3. **PID_CALIBRATE** was corrected on 20261018 (older runs recommended values twice too large). The extruder PIDs were measured on this Klipper (November 2026, fine). The bed PID (63.167 / 1.077 / 926.193) has no date in the file: if it was measured before 2026-10-18 and the bed oscillates, run it again.
4. **Duplicate section on purpose**: `[gcode_macro SET_GCODE_OFFSET]` is in rpi_base.cfg L561 and in the panel's rpi_ace.cfg L165 (same code, `rename_existing: _WM_SET_GCODE_OFFSET`). Klipper merges identical sections, it works; if one copy is ever changed without the other, the merged result is unpredictable.
5. **Fixed wipe default** `[-13.0, 240.0]` appears as a fallback in many macros (WIPE_NOZZLE, _WM_HEAT_AT_WIPE, _WM_GO_WIPE, ...). Real value comes from `wipe_position` in saved_variables; open item NOZZLE_CALIBRATE_TOOL_OFFSET hard-coded X-13 Y240.
6. **Compiled factory modules** (`cs1237`, `heater_air_core`, `heater_feng`, `hx711`, `xy_offset_calibrator_core`) are `cpython-39` binaries: they load only in the Python 3.9 virtualenv `~/klippy-env`. A rebuild of that venv with another Python breaks the load cell, heater and offset modules.
7. **MCU firmware is not upstream**: boards run `KLP_*_WM_ZRU_*` builds (T0-T3 from 2025-11-14, main board 2026-04-08, CELL RPI_V2 2026-11-17) with Klipper host v0.13.0-827; the `wm_mcu_tweaks` module hides the missing `get_canbus_status` and `STEPPER_STEP_BOTH_EDGE` messages. The firmware does not know all commands of the newer host.
8. **Fluidd macro list**: 13 macros are stored without category and hidden on purpose (M104, M106, M107, M109, M141, M190, M191, M221, SET_GCODE_OFFSET, WM_BED_SOAK, Z_OFFSET_APPLY_ENDSTOP, Z_OFFSET_APPLY_PROBE, z_rise); every visible macro (103) has a category.
9. **Open items from the to-do list that touch macros** (see FIX-LOG.md): First Run Calibration real run (F-143..F-148, pushed not tested), T1 offset check (+0.33/0.34 mm), B-009/B-011 (tool change retry while printing, collision_detect), B-025 (FIRMWARE_RESTART after C016), F-150 heat-at-wipe (pushed not tested), F-152..F-155 (ACE first-load fast, unload queue, light watcher).
10. **Not verified (updated 2026-11-19)**: the `printer.<object>.<field>` reads were checked in the files read line by line (listed per block); the 36 added modules' own status keys were checked only where a macro reads them; each G-code command was checked for existence, not for correct parameters.

## Change log
- 2026-11-19 (ACE driver): all 25 files of `extras/ace/` plus `temperature_ace.py` and `virtual_pins.py` read line by line; section rewritten (it said "NOT read line by line" and "19,539 lines"); two corrections: both T0..T3 owners statement and the list of commands called. Backup: MACROS.md.bak-2026-11-19-before-ace-driver-read.
- 2026-11-19 (later): line-by-line blocks added for rpi_endless.cfg, rpi_stats.cfg, zr_tools.cfg, offset_calibrate.cfg, change_macros.cfg, macros.cfg, timelapse.cfg; the wrong `#XYZ:` finding in rpi_base.cfg was corrected (Klipper strips ` #` and ` ;` when it loads the config). Backups: ...-before-endless-stats-zrtools, ...-before-hash-correction.
- 2026-11-19: line-by-line blocks added for rpi_ace.cfg, rpi_nozzle.cfg, rpi_base.cfg, rpi_calibration.cfg; ACE driver field check block; Files done table updated. Backups: MACROS.md.bak-2026-11-18-before-ace-read, ...-before-nozzle-read, MACROS.md.bak-2026-11-19-before-base-read, ...-before-calib-read, ...-before-ace-driver-note.
- 2026-11-18: document created from the live config (336 macros / timers in 19 files). Nothing on the printer was changed.

## F-156 purge (added 2026-11-19, checked against the files on the dev Pi, 2026-11-19; not in the repos yet)
### WM_PURGE_MENU
- **File**: rpi_base.cfg (end of file, F-156 block). **What it does**: Fluidd prompt window: toolhead, temperature, speed, amount, Start purge, Cancel. **Risk**: MOVES THE TOOLHEAD, HEATS, ACE. **Fluidd**: WM Ultra Filament. **Tested**: window renders (console); start from it not tested.
### _WM_PURGE (hidden)
- **What it does**: T= [S= temperature, 0 = the filament's own] [SPEED= mm/s] [LEN= mm] [FINISH=1|0|2]. Checks (not printing, no unload, ACE idle, limits 170..max_temp-10 C, 1..30 mm/s, 1..300 mm, filament in the head), homes if needed, then _WM_PURGE_GO. **Called by**: WM_PURGE_MENU Start button, KlipperScreen Purge page (FINISH=1), Fluidd Purge dialog (FINISH=2). **Tested**: T1 10 mm OK 2026-11-19.
### _WM_PURGE_GO, _WM_PURGE_DONE, _WM_PURGE_PICK, _WM_PURGE_SEL (hidden)
- _GO: tool change (read after the homing), _WM_GO_WIPE_HEAT, _WM_PURGE_ASSIST on, push, assist off, then DONE / message / window. _DONE: closes the prompt, wipe, heater off, M106 S255 until below 140 C, M107, park. _PICK: one window button. _SEL: window choices (t, temp, speed, len, hot).
- **Change log**: 2026-11-19 new. Replaces the "better purge macro" to-do (ZR_PURGE was removed in F-104).
### _WM_PURGE_LOCATION (hidden, F-156, 2026-11-19, not in the repos yet)
- **What it does**: the place where the purge heats and pushes: variables x -13, y 60, z 7. Moves there (z_rise, _WM_CAL_CLEARANCE, G0 Y, G0 X, G1 Z) and, with T= S=, heats toolhead T and waits. **Used by**: _WM_PURGE_GO; free for other macros. **Change log**: 2026-11-19 new, replaces the wipe position X-13 Y240 for the purge. **Tested**: not yet.

## Index in the config files (2026-11-19, F-158)
Each rpi_*.cfg (except rpi_pi.cfg) and zr_tools.cfg starts with its header and an auto index of its macros (visible / hidden, with description). The index is made by `~/idx-test/mkindex.py FILE --write` on the dev Pi. Checked against the files on the Pi, 2026-11-19.

### WM_PURGE_MENU change (F-161, 2026-11-19, pi400 only, checked against the files on pi400, 2026-11-19)
- Old: showed the prompt window (RESPOND action:prompt_*). New: after the checks it sets _WM_PURGE_SEL.show=1; the Fluidd panel (Dashboard) opens its own purge window (same as the PURGE button) and sets show=0; if nothing answers within 2 s, delayed_gcode _WM_PURGE_SHOW_CHECK shows the prompt window through the new hidden macro _WM_PURGE_PROMPT (_WM_PURGE_PICK calls it too). Why: same window in the macro list as in the panel. Tested on the dev box (pi400). Not on .35, not in the repos.

### Z trim window change (F-162, 2026-11-19, pi400 only, checked against the files on pi400, 2026-11-19)
- WM_Z_TRIM was renamed _WM_Z_TRIM (hidden in Fluidd; same behaviour, limit 0.30 mm; only _WM_Z_TRIM_STEP calls it; the console still accepts it). WM_Z_TRIM no longer exists as a visible macro. _WM_Z_TRIM_WIN: rows 0.01 0.02 0.05 0.1 for both Closer and Further (same order, aligned); footer "Save and back" (returns to WM_Z_TRIM_MENU) replaces "Back". Why: user request. Tested on the dev box.


## Change log F-164 (2026-11-19, pi400 only)
Purge, push and heat spots moved from the wipe area (X-13 Y240) and X-13 Y80 to `_WM_PURGE_LOCATION` (X-13 Y60 Z7): `_WM_GO_WIPE_HEAT`, `_WM_HEAT_AT_WIPE` (X/Y only), `_WM_PURGE_HEAT`, `ACE_WM_LOAD` (waiting spot), `RESUME` (heat + 20 mm purge), `M109` (trip made before the heater is set = cold nozzle), `EXTRUDE_FILAMENT`, `filament_insert_gcode`. `WIPE_NOZZLE` stays at the wiper. See FIX-LOG F-164. Checked against pi400 files, 2026-11-19. Backups on pi400 in printer_data/config/backup (wm-before-purgeloc).

## Change log F-165 (2026-11-19, pi400 only)
`_WM_PURGE_LOCATION`: Y 60 -> 80; the fixed Z7 is replaced by a bed drop of 10 mm from the current Z (Z up = bed down), limited to 2 mm before the Z endstop (Z298), skipped when Z is not homed. Variables now x, y, drop, stop_before. Checked against pi400 files, 2026-11-19.

## Change log F-165 revised (2026-11-19, pi400 only)
`_WM_PURGE_LOCATION`: the 10 mm bed drop is removed; it moves only to X-13 Y80 (clearance from `z_rise` and `_WM_CAL_CLEARANCE`). Variables x, y. Checked against pi400 files, 2026-11-19.

## Change log F-166 steps 1-2 (2026-11-19, pi400 only)
`PAUSE` now saves `wm_pause_tool` (the tool on the carriage). `RESUME` checks that tool first: empty head sensor = error and stays paused; docked = `_CHANGE_TOOL` picks it up. extruder0-3.cfg `insert_gcode`: while paused, the print's tool is not parked after its load (other tools are). Why: B-075 (RESUME printed without a tool). Checked against pi400 files, 2026-11-19.
- 2026-11-19 F-166 step 3: WM_LOAD_MENU, _WM_LOAD_* helpers, _wm_load_runner added to rpi_base.cfg; paused unload allowed (WM_UNLOAD_MENU/_WM_UNLOAD_GO/_WM_UNLOAD_END, _wm_unload_runner); ZR_RETRACT/_WM_ZR_LOAD_GO keep print tool on carriage while paused (zr_tools.cfg); _WM_ACE_HEAD_DONE marks load done (rpi_ace.cfg); insert_gcode extruder0-3 keep print tool while paused.
- 2026-11-19 F-166 step 4: new WM_RESUME_TOOL, WM_RESUME_TOOL_GO and hidden _WM_RTOOL* (rpi_base.cfg); RESUME purge length variable (macros.cfg). Fluidd category: WM Ultra Filament (not set yet).
- 2026-11-19 F-166 step 5: WM_RESUME_TOOL_GO pre-check of the print's tool map (rpi_base.cfg).
- 2026-11-19 F-166 step 6: WM_RESUME_TOOL_GO renamed _WM_RESUME_TOOL_GO (hidden helper). Fluidd category WM Ultra Filament: WM_LOAD_MENU, WM_LOAD_STOP, WM_RESUME_TOOL, WM_PURGE_MENU.
- 2026-11-19 F-167: renamed WM_ENDLESS_SET/FIXED/PLAN/CONTINUE, WM_STATS_RESET, WM_LOAD_STOP, WM_UNLOAD_STOP to _WM_... (hidden helpers). WM_SET_TOOL_MAP kept (Orca plugin), hidden in Fluidd only.
- 2026-11-19 F-167 part 2: 19 macros renamed with _ (ZR_LOAD/UNLOAD/RETRACT/MAP_*/SET_TOOL_*/CHAMBER/AIR_FILTER, WM_BED_WARP_STOP, WM_LIVE_Z_ZERO, WM_AUTO_SPEED_VALIDATE, WM_CAL_HELP, Z_HOMING, ACE_WM_ASSIST/AUTO/DRY_START/DRY_STOP/RETRACT); 24 factory macros hidden in Fluidd only.
- 2026-11-19 F-168: _WM_LOAD_SHOW and _WM_RTOOL_SHOW1 button labels shortened (T0 print tool · in head).

- 2026-11-19 (F-170 Resume tool two pages + messages 1-4): user messages of _WM_HEAD_QUEUE (sensors back on, Loading T..), _WM_UNLOAD_GO/_WM_UNLOAD runner, _WM_LOAD_GO/_WM_LOAD runner and _WM_RESUME_TOOL_GO now count toolheads 1-4 (before: 0-3) to match the screens. Checked against rpi_base.cfg on pi400, 2026-11-19. Backup config/backup/rpi_base.cfg.wm-before-numbering-*.
- 2026-11-19 F-174: _WM_RTOOL_SHOW1/_WM_RTOOL_PICK/_WM_RTOOL_SHOW2/_WM_LOAD_SHOW: Toolhead 1-4 numbers, plain wording, empty tool in Resume tool opens Load for it, swap sentence "T2 takes over from T1". Checked against files, 2026-11-19. Note: running pi400 Klipper reads printer_data/devbox/config.
- 2026-11-19 F-175: message texts of _ZR_UNLOAD/_ZR_LOAD runner, _WM_UNLOAD*, _WM_HEAT_AT_WIPE, ACE unload messages, _CHANGE_TOOL, wipe: Toolhead 1-4 numbers (parameters unchanged). Checked against files, 2026-11-19.
- 2026-11-19 F-176/F-177: _WM_ENDLESS_CONTINUE/_WM_ENDLESS_3 etc: messages in T1-T4; _WM_ENDLESS_3 now saves wm_pause_tool = new tool before RESUME (stops RESUME changing back to the empty head). Checked against files, 2026-11-19.
- 2026-11-19 T-001: all macro changes of F-166..F-177 (renames with _, Load menu, Resume tool, endless, Toolhead 1-4 messages) copied from pi400 to main RPi4 (.35); Fluidd build replaced; checked against files, 2026-11-19.
- 2026-11-19 F-178: WM_UNLOAD_MENU button labels and rpi_calibration tool lists in T1-T4 (parameters unchanged). Checked against files, 2026-11-19.

- Change log 2026-11-19 (F-181): START_PRINT now sets G90 right after "START_PRINT begin"; _Z_HOMING sets G90 before G1 X150 Y135 (WIPE_NOZZLE restores the old mode). Why: a failed Fluidd jog left G91 on and broke the print start. Backups .bak-2026-11-19-f181, config/backup/*.wm-before-g90-*. Checked against the real files, 2026-11-19.

- Change log 2026-11-19 (F-183, F-184): _ACE_WM_RETRACT starts the watcher _wm_ace_tick before ACE_RETRACT; ACE texts show T1-T4. Backups .bak-2026-11-19-f183, config/backup/rpi_ace.cfg.wm-before-f183-*. Checked against the real files, 2026-11-19.
- 2026-11-19 F-186: START_PRINT calls `_WM_START_PURGE` unconditionally; the factory left-edge purge fallback (X0 Y70-150) was removed.
- 2026-11-19 F-187: RETRACT_FILAMENT now moves to _WM_PURGE_LOCATION (was X-13 Y232); LOAD_FILAMENT, filament_insert_gcode and the pause/resume prime call _WM_PURGE_LOCATION unconditionally (own X/Y fallbacks removed). Checked against MACROS.md and the real files, 2026-11-19.
- 2026-11-20 RULE (user): the purge location of the calibration macros WM_OFFSETS_ACCURATE (calls _WM_NOZZLE_PREPARE) and CALIBRATE_OFFSET_ALL_FINE_MODE / _RAPID_MODE (call NOZZLE_PREPARE, POP) is never changed. They heat at the wiper (_WM_GO_WIPE), go back, and push 120/120/88 mm where the head was; they do NOT use _WM_PURGE_LOCATION, on purpose. _WM_GO_WIPE stays (also used by G29). Checked against the real files on .35, 2026-11-20.
- 2026-11-20 F-188: WM_FIRST_RUN_CAL / _WM_FIRST_RUN_CAL / _WM_FIRST_RUN_CAL_DONE: new stage 4 `WM_NOZZLE_GROWTH_CAL CONFIRM=1` after WM_OFFSETS_Z_HOT (eight stages now, calls WM_NOZZLE_GROWTH_CAL in addition); result window shows the growth value; no extra homing (both macros home only when not homed). pi400 only, tested windows, not a full run. Checked against the real file on pi400, 2026-11-20.
- 2026-11-20 F-188 part 2: WM_FIRST_RUN_CAL window explains step 4 (growth) and the Z trim; _WM_FIRST_RUN_CAL_DONE shows the growth effect and the 3 Z trim steps (copied from the guided WM_FULL_OFFSET_CAL windows). pi400 only. Checked against the real file on pi400, 2026-11-20.

- F-189 (B-077) 2026-11-20: `_WM_START_PURGE_RUN`, `_WM_WIPE_PURGE`, `_WM_WIPE_PURGE_GO` messages show Toolhead 1-4 (head+1). Text only. pi400 done, .35 pending.

- F-190 2026-11-20: line per head. `_WM_PURGE_SETTINGS` (+head_lines, line_spacing), `_WM_START_PURGE_RUN` (N/TOTAL, no trailing line when head_lines), `_WM_WIPE_PURGE` (message), `_WM_WIPE_PURGE_GO` (calls `_WM_LINE_PURGE N= TOTAL=` instead of 20 mm push), `_WM_LINE_PURGE` (params N, TOTAL, spacing). head_lines=0 = old way. pi400 done, .35 pending.

- F-190 TEST 2026-11-20: new file wm_test_head_lines.cfg: WM_TEST_HEAD_LINES (visible, WM Ultra Print), _WM_TEST_START_PURGE_RUN, _WM_TEST_WIPE_PURGE, _WM_TEST_WIPE_PURGE_GO, _WM_TEST_LINE_PURGE. On .35 and pi400. Test only, START_PRINT not using them.

- F-190 2026-11-20: real on .35 and pi400 (rpi_base.cfg md5 6fc1011e). Test file and WM_TEST_HEAD_LINES removed (_WM_TEST_* macros no longer exist).
- F-192 2026-11-20: _WM_LOAD_SHOW window text shortened (macro name and wipe sentence removed). pi400 done, .35 pending.

- F-202 2026-11-20: _WM_ENDLESS new variable swap_purge (50 mm); _WM_ENDLESS_3 raises the resume purge to it for a swap. .35 (restart 21:42) and pi400 devbox/config (22:00). Backups rpi_endless.cfg.20261120-2140-before-F202 (config/backup on .35), MACROS.md.bak-2026-11-20-f202.

### Purge while PAUSED change (F-203, 2026-11-20, pi400 only, not tested, checked against pi400 files rpi_base.cfg, 2026-11-20)
- `WM_PURGE_MENU`, `_WM_PURGE`: old: refused "not while printing or paused". New: refuse only while printing; while paused `_WM_PURGE` accepts only the tool on the carriage (save_variables.current_extruder), another tool -> error "use Resume tool".
- `_WM_PURGE_DONE`: new paused branch: closes the window, `_WM_PURGE_ASSIST` off, `WIPE_NOZZLE`, heater of that tool off, message; no park and no tool change (RESUME goes to `_WM_PURGE_LOCATION`, heats and restores the saved position). Not paused: unchanged (wipe, cool, park).
- Why: purge to engage the filament while the print is paused (B-079). Backup: pi400 devbox/config/backup/rpi_base.cfg.*-before-pausepurge. Screen/Fluidd side in FIX-LOG F-203.

### Resume tool confirmation (F-204, 2026-11-20, pi400 only, checked against pi400 rpi_base.cfg, 2026-11-20)
- `_WM_RTOOL_SHOW2`: the footer button "Resume with T*" now calls `_WM_RTOOL_CONFIRM` (before: `_WM_RESUME_TOOL_GO` at once).
- `_WM_RTOOL_CONFIRM` (new, hidden helper, Fluidd: -): Resume tool window 3. Needs a paused print and a chosen tool. Shows what will happen (same tool or swap, temperature, no purge length), the reminder to check the filament, "Do you confirm?" and the buttons Resume (`_WM_RESUME_TOOL_GO`) and Back (`_WM_RTOOL_SHOW2`). Risk: none (only a window). Tested on the pi400 simulation. KlipperScreen has the same page in zr_tools.py (show_resume_confirm). Backup: pi400 devbox/config/backup/rpi_base.cfg.*-before-F204.

- 2026-11-20 F-204 change 2: `_WM_RTOOL_CONFIRM` text shortened (swap = 3 steps), the line "Do you confirm?" removed. md5 rpi_base.cfg 262eccf4 (pi400). Checked against pi400 file, 2026-11-20.

### WM_OFFSETS_Z_HOT change (F-205, 2026-11-21, pi400 only, checked against pi400 rpi_calibration.cfg, 2026-11-21)
- Old: touches started right after the bed reached its temperature. New: waits `_WM_ZHOT.bed_soak_min` minutes (new setting, 15, 0 = no wait) after M190, one console line per minute; window and start message say about 25 minutes. Why: the bed plate keeps moving 0.03-0.06 mm for minutes after heating (measured 2026-11-21). Backup: pi400 devbox/config/backup/rpi_calibration.cfg.*-before-F205. Tested on the simulator only.
- 2026-11-21 F-202 change: `_WM_ENDLESS.swap_purge` set back from 50 to 20 mm (user request). `_WM_ENDLESS_3` then leaves the resume purge as it is. Checked against the real file on .35, 2026-11-21.

### Print start purge switch (F-206, 2026-11-21, pi400 only, checked against pi400 rpi_base.cfg, 2026-11-21)
- `[output_pin Purge_Line_Every_Toolhead]` (new, Fluidd switch): ON = every used toolhead draws its own purge line (F-190); OFF = only the first tool draws one line, the other heads are not purged at the start. Saved in `wm_purge_all_heads`.
- `WM_PURGE_LINES_PIN_WATCH` (new delayed_gcode, every 2 s): gives the switch its saved state at start-up and saves a change made in Fluidd. Risk: none.
- `_WM_START_PURGE_RUN`: old: always purged every used head. New: when `wm_purge_all_heads` is 0 it purges only the first tool. `_WM_PURGE_SETTINGS` has the new variable `pin_synced`.
- Why: user wants to choose between four lines and one line. Tested on the simulator. Backup: pi400 devbox/config/backup/rpi_base.cfg.*-before-F206.

- 2026-11-21 F-205 change 2: `WM_OFFSETS_Z_HOT` no longer waits a fixed 15 minutes; it calls `_WM_BED_SOAK_MARK` before heating the bed and `_WM_BED_SOAK` after it (the print start's bed warp wait). `_WM_ZHOT.bed_soak_min` removed. On pi400 and the main RPi4 .35 (md5 fd3c8687). Checked against the real file on .35, 2026-11-21.

## 2026-11-21 F-208 (test pair only, zr_tools.cfg)
- NEW _ZR_MAP_SET MAP=a,b,c,d : sets the whole tool map (slicer T0..T3 -> toolhead 0..3). Validates 4 entries 0-3, refused while printing/paused. Writes box_modify_tN and box_modify_tN_backup.
- CHANGED _ZR_MAP_TOOL and _ZR_MAP_RESET: also write box_modify_tN_backup.
- New saved variables (written by the screen page): wm_last_map_file, wm_last_map.
- Checked against pi400 devbox zr_tools.cfg md5 1f47a136, 2026-11-21.

## Change log F-162 final wording (2026-11-21, pi400 devbox only)
- `_WM_Z_TRIM_WIN` (rpi_calibration.cfg): the top line of the Z trim window was a button "T0 trim now +0.00 mm"; it is now plain text "T0 TRIM IS 0.00 MM" (prompt_text, two decimals, minus sign when negative). Reason: user request, a button that does nothing looked pressable. Backup: backup/rpi_calibration.cfg.20261121-before-F162-topline (config and devbox/config). Checked against pi400 devbox rpi_calibration.cfg md5 d2abe2ec, 2026-11-21.
