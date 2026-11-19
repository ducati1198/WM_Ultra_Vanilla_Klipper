# DIFFERENCES.md - where WM_Ultra_Vanilla_Klipper differs from upstream Klipper

Written 2026-11-18. **Compared byte for byte (rsync checksum, dry run)** the Klipper folder of the dev Pi (`~/klipper`, version string `v0.13.0-827-g29d4ec2d6`) with a checkout of upstream `Klipper3d/klipper` commit `29d4ec2d6d840ee839333306003a400da186d41d` (2026-11-10, "trdispatch: Fix signed comparison when extending trsync timeout"; exists upstream, 6427 commits). Raw result: `05-notes/reference/klipper-vs-upstream-rsync-2026-11-18.txt`. Checked against: upstream commit above, 2026-11-18. Python caches (`__pycache__`, `*.pyc`) were ignored.

## Result in one line
**One upstream file is changed, 36 files are added, 3 are symlinks into the panel repo. Nothing else differs** (`src/` MCU code, `lib/`, `scripts/`, `config/`, `docs/`, all other `klippy/` files are identical to upstream). The MCU firmware on the boards is NOT built from this tree (see "Boards").

## 1. Modified upstream file
| File | Difference | Re-check after an update |
|---|---|---|
| `klippy/extras/lis2dw.py` | Older, simpler version: no LIS3DH chip, no I2C bus, no `CTRL_REG4/5`, one scale, data rate fixed 1600. Diff: `05-notes/reference/lis2dw.py.diff-vs-upstream-29d4ec2d6.txt` | Upstream gained LIS3DH and I2C support; this copy lacks it. If upstream changes `lis2dw.py` again, keep ours or merge by hand. Used by `[lis2dw]` (accelerometer on the EX_T board, `resonance_tester`, `collision_detect`). |

## 2. Added files in `klippy/` (not in upstream)
The "What" column is written from file names, file headers and the config that uses each module; the Python files themselves were **not read line by line** (to do). The compiled `.so` files cannot be read at all.
| File | Lines | What | Source |
|---|---|---|---|
| `klippy/.version` | 1 | version string `v0.13.0-827-g29d4ec2d6` (the Pi has no `.git` folder) | installer |
| `klippy/chelper/c_helper.so` | binary | compiled C helper (Klipper builds it itself) | built on the Pi |
| `extras/air.py` | 475 | air filter / chamber air handling | WonderMaker factory |
| `extras/heater_air.py`, `extras/probe_air.py` | 5 / 4 | thin wrappers that load the compiled cores | factory |
| `extras/heater_air_core.cpython-39-aarch64-linux-gnu.so` | binary | compiled heater/air controller | factory (binary only) |
| `extras/cs1237.cpython-39-aarch64-linux-gnu.so` | binary | compiled CS1237 ADC (load cell) | factory (binary only) |
| `extras/hx711.cpython-39-aarch64-linux-gnu.so` | binary | compiled HX711 ADC | factory (binary only) |
| `extras/heater_feng.cpython-39-aarch64-linux-gnu.so` | binary | compiled heater | factory (binary only) |
| `extras/xy_offset_calibrator.py` (3) + `xy_offset_calibrator_core...so` | 3 / binary | XY tool offset calibrator (the c_sensor load cell touch) | factory |
| `extras/tools_calibrate.py` (3), `tools_calibrate_core.py` | 3 / 517 | tool offset calibration helper | factory |
| `extras/custom_hall.py` | 104 | Hall sensors that detect which tool head is on the carriage; `last_toolhead_position` | factory |
| `extras/echelon_stepper.py` | 209 | the gear-shift ("echelon") motor that locks/unlocks tool heads (`ECHELON_STEPPER*`) | factory |
| `extras/feed_slot.py` | 501 | feed slot module | factory |
| `extras/fm17550.py` | 132 | RFID reader chip driver | factory |
| `extras/collision_detect.py` | 281 | collision detection from the accelerometer (`COLLISION_DETECT_ENABLE/DISABLE`, `SET_COLLISION_THRESHOLD`) | factory |
| `extras/stall_sensor.py` | 66 | TMC DIAG stall pin sensor (`QUERY_STALL`) | factory |
| `extras/gcode_shell_command.py` | 95 | `[gcode_shell_command]` (needed by auto speed and nozzle macros) | community extension |
| `extras/auto_speed.py` + `extras/autospeed/` (`main.py` 1040, `move.py`, `funcs.py`, `wrappers.py`, `__init__.py`, LICENSE) | 12 + ~1275 | Klipper Auto Speed (`AUTO_SPEED`) | community project |
| `extras/wm_adaptive_mesh.py` | 48 | adaptive bed mesh parameters | ours |
| `extras/wm_gcode_compat.py` | 135 | G-code compatibility (factory commands the Pi needs) | ours |
| `extras/wm_mcu_tweaks.py` | 89 | hides the "MCU lacks get_canbus_status / STEPPER_STEP_BOTH_EDGE" messages for factory firmware | ours |
| `extras/wm_pin_pulse.py` | 55 | `WM_PIN_PULSE` for the load cell trigger | ours |
| `extras/wm_print_info.py` | 115 | print info for purge / Fluidd | ours |
| `extras/wm_ready_compat.py` | 53 | "ready" state compatibility | ours |
| `extras/wm_stepper_diag.py` | 77 | `STEPPER_DIAG_ENABLE` | ours |
| `extras/wm_tool_touch.py` | 117 | tool setter touch helper | ours |
| `extras/wm_virtual_pins.py` | 149 | virtual pins (`Nozzle_Heat_Growth`) | ours (F-013) |
Symlinks created by the panel installer: `extras/ace` -> `~/wm-ultra-fluidd-acepro-panel/extras/ace` (ACE Pro driver), `extras/temperature_ace.py`, `extras/virtual_pins.py` (same folder).

Totals: 36 files listed as new + 3 symlinks = every difference found. Line counts from `wc -l` on the Pi.

## 3. Python and binaries
- Klipper runs in `~/klippy-env`, **Python 3.9.25**; the system Python is 3.11.2. The five compiled factory modules are `cpython-39` and only load in the 3.9 venv. Rebuilding the venv with another Python would break the load cell, the heater module and the offset calibration.

## 4. Boards (firmware is not from this tree)
| Board | Firmware version string | Note |
|---|---|---|
| `mcu` (main) | `KLP_MCU_WM_ZRU_20260408_185504` | factory build |
| `T0..T3` (tool heads) | `KLP_THR_WM_ZRU_20251114_151129` | factory build, lacks `get_canbus_status` and `STEPPER_STEP_BOTH_EDGE` |
| `HUB` | `KLP_HUB_WM_ZRU_20251114_151549` | factory build |
| `EX_T` | `KLP_EXT_WM_ZRU_20251114_151429` | factory build |
| `CELL` (load cell) | `KLP_CELL_WM_ZRU_RPI_V2_20261117` | **our own patched firmware V2** (F-113), repo ducati1198/wm-load-cell-mcu |
| `rpi` (host MCU) | `v0.13.0-827-g29d4ec2d6-20261118_161451-wmultra` | built on the Pi from this tree (service `klipper-mcu`) |
The host speaks Klipper 0.13.0-827 to firmware built from older Klipper sources; this works (the Pi starts and prints) because the protocol is backward compatible, but a new upstream change in the MCU protocol can break it. After a Klipper update test one start and one tool change.

## 5. Config-level differences from a stock Klipper install
`printer.cfg` enables the extra modules `[wm_adaptive_mesh] [wm_mcu_tweaks] [wm_stepper_diag] [wm_gcode_compat] [wm_pin_pulse] [wm_ready_compat] [wm_print_info]`, `[custom_hall]`, `[echelon_stepper trans_stepper]`, `[collision_detect]`, `[stall_sensor ...]`, `[probe_air]`, `[tools_calibrate]` (via factory files), `[gcode_shell_command ...]` (3 sections in rpi_nozzle), `[ace]`, `[temperature_ace]`, `[virtual_pins]`, `[heater_generic chamber]`, and 10 `[temperature_sensor ...]` for boards. The standard macros `PAUSE`, `RESUME`, `CANCEL_PRINT`, `PROBE_CALIBRATE`, `BED_MESH_CALIBRATE`, `M104`, `M106`, `M107`, `M109`, `M190`, `M221`, `SET_GCODE_OFFSET`, `Z_OFFSET_APPLY_PROBE`, `Z_OFFSET_APPLY_ENDSTOP` are **renamed and wrapped** with `rename_existing` (originals reachable as BASE_PAUSE, M99104, ...): see MACROS.md.

## 6. Deprecated or removed things found in the config (Config_Changes.md of the installed Klipper, 143 entries scanned for names used in our files)
| Finding | Where | Entry |
|---|---|---|
| `.e` accessor on `gcode_position` is deprecated | timelapse.cfg L264 | 20251106 |
| Input shaper `3hump_ei` definition changed, recalibration recommended | SAVE_CONFIG `[input_shaper]` | 20250916 |
| `PID_CALIBRATE` corrected: older results were twice too large | bed PID in SAVE_CONFIG (date unknown) | 20261018 |
| `max_accel_to_decel` / `ACCEL_TO_DECEL` removed | only a comment in macros.cfg L114 (`#ACCEL_TO_DECEL`) - harmless | 20250811 |
| `BED_MESH_PROFILE LOAD="default"` is needed because the default profile is not auto-loaded | present in macros.cfg L78 (START_PRINT) - fine | 20230201 |
Nothing else in the 143 entries touches an option or command used here. The printer starts without config errors, so every option is valid for this version; macro bodies are rendered only when they run, so a deprecated `printer.*` field inside a macro body could still hide: only the fields named in Config_Changes.md were searched.

## Change log
- 2026-11-18: document created; compared with upstream commit 29d4ec2d6.
