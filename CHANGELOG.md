# Changelog

## 2.0.2

- **`--update` now refreshes the Pi-side WonderMaker modules** (`wm_*.py` in `~/klipper/klippy/extras`, for example the 2.0.1 warning fix in `wm_mcu_tweaks`). Before, a Pi installed with an earlier version kept its old copies, because the update never copies the bundled Klipper again. Each file is checked against the repository's checksum list; only changed files are copied; other files in `extras` are never touched. Klipper is restarted at the end of the update, which loads them.

## 2.0.1

- **No more "MCU has deprecated code" warnings in Fluidd.** WonderMaker's MCU firmware is older than the bundled Klipper and lacks two optional features (`get_canbus_status`, `STEPPER_STEP_BOTH_EDGE`), so Klipper filed one warning per board. `wm_mcu_tweaks` now skips those two (option `hide_mcu_deprecated`, default on; set it to `False` under `[wm_mcu_tweaks]` to see them again). Every other Klipper warning still shows. Needs a Klipper service restart to load (a plain RESTART does not reload Python files).
- Tested on the dev Pi: 0 warnings after the restart, Klipper ready. Not yet tested with a fresh install.

## 2.0.0

First release of **WM_Ultra_Vanilla_Klipper**. It starts from the wm-ultra-rpi installer (same options, same questions, same steps, same KlipperScreen on the Pi and on the screen board) and replaces WonderMaker's modified Klipper and Moonraker with the upstream ones.

- **Upstream Klipper and Moonraker, pinned and bundled.** `factory/<model>/klipper` is Klipper v0.13.0-827-g29d4ec2d6 (Klipper3d) and `factory/<model>/moonraker` is Moonraker v0.11.0-4-gb559b9a (Arksine), both as source copies with `lib/`. The installer deploys them like before (checksums first). Updates come from this repository.
- **WonderMaker's modules added to upstream Klipper**, as files in `klippy/extras/`: the 5 compiled modules (`cs1237`, `hx711`, `heater_air_core`, `heater_feng`, `xy_offset_calibrator_core`, unchanged, same checksums) and the Python modules the printer needs (`heater_air`, `probe_air`, `tools_calibrate`, `xy_offset_calibrator`, `echelon_stepper`, `custom_hall`, `lis2dw`, `stall_sensor`, ...).
- **Pi-side modules for upstream Klipper:** `wm_adaptive_mesh` (adaptive bed mesh without `SAVE_CONFIG_NO_RESTART`, so Fluidd no longer asks to save and restart after START_PRINT), `wm_mcu_tweaks` (probe "triggered prior to movement" fix), `wm_pin_pulse`, `wm_stepper_diag`, `wm_gcode_compat`, `wm_ready_compat`.
- **Printer settings from a running vanilla Pi.** The macros, `printer.cfg`, `moonraker.conf`, `tmt1.ini`, `wm_chamber_light.json` and `wm_fan_guard.cfg` come from the Pi that runs this setup. `wm_fan_guard.cfg` (pauses the print when a fan that is on reports 0 RPM for 30 seconds) only watches the part fan on an Ultra, so an Ultra (with `[include zru-s.cfg]` commented out) is not affected by the Ultra-S fans.
- **Clean start.** No bed mesh, PID results, input shaper, probe offset or tool offsets are shipped. `printer.cfg` has `z_offset:0` and the hotend and bed PID values in its body, and an empty `SAVE_CONFIG` block. `saved_variables.cfg` has tool offsets 0.
- **CAN ids:** main board, hub and extruder board have placeholders (`000000000000`, `000000000001`, `000000000002`); T0 to T3 and the load cell are empty and filled by the installer, as before. Set the real ones with `./installer.sh --first-start` or `./installer.sh --can-ids`.
- **Python:** Klipper runs in Python 3.9 (installed with `uv`, for the compiled modules). Moonraker runs in the system Python 3.11. `config/*-requirements.txt` are the exact package lists of the tested Pi.
- **Existing WonderMaker installs are refused with a clear message** (a Pi installed with wm-ultra-rpi, or one with WonderMaker's own Klipper). Use a fresh SD card.
- **Fluidd** still comes from the `wm-ultra-fluidd-acepro-panel` repository. **ACE Pro** is not installed automatically (asked, default no, add it later with `--update --acepro on`).
- **Left out of the installer for now:** the Moonraker `metadata.py` and Klipper `configfile.py` patches for WonderMaker's forks, and the `System_x.y.z` file (`~/iso_version.txt`). `tools/wm-release`, `--modules` and `--from-stage` stay in the repository but the installer does not advertise them.
- **MCU firmware** is WonderMaker's, unchanged (the installer never flashes anything). Upstream Klipper prints "deprecated code" warnings for it. They are harmless.
- Version numbers start again at 2.0.0 (wm-ultra-rpi stays at 1.23.x).
