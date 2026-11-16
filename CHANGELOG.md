# Changelog

## 2.13.0

The hub sensors are tangle sensors, and the touchscreen comes back by itself. Goes with wm-ultra-fluidd-acepro-panel 1.12.0.

- **The four hub sensors (`path_0`..`path_3`) are filament tangle sensors, not filament sensors** (`hub.cfg`, both models, and through the macro patches on a Pi that is already installed). They fire when the filament is pulled tight: a tangle on the spool, or a finished spool whose end is fixed to the spool. They still pause the print; the message now says so ("Filament tangle on T0 (tool 1): the filament is pulled tight. The print is paused. Free the filament, then resume.") instead of "Filament runout on path 0". Each one also tells the endless spool of the Fluidd panel which toolhead tangled (`_WM_ENDLESS_TANGLE`, only when that macro is installed), so an identical toolhead can take over.
- **A nozzle that has to heat during a print waits at the wipe position** (`rpi-cfg/rpi_base.cfg`: `_WM_HEAT_AT_WIPE`, `_WM_HEAT_BACK`, called by `M109` in `macros.cfg` and `_WAIT_TOOL_TEMPERATURE` in `change_macros.cfg`, both models, and through the macro patches). Before, it heated wherever it stood: at the park position after a pause, and after a tool change **on the part**, because the printer returns to the print position and lowers Z before it waits for the temperature. Now the nozzle on the carriage lifts 2 mm, goes to the wipe position, heats there and goes back to the spot it left, so what drips while heating falls at the wipe area. Only in a print (its start and a pause too), only when the nozzle is more than 5 C under its target, only with X Y Z homed; a toolhead heating in its dock does not move, and loading filament outside a print is unchanged.
- **Touchscreen: KlipperScreen keeps trying to reach the Pi** (screen board, `screen.py` through `patch_ks_wm.py`). It stopped after 4 failed tries and stayed on "Connecting to ..." until somebody tapped Retry, also when the Pi was back a minute later (seen twice after a Wi-Fi hang of the Pi). Now it starts a new round of tries 30 seconds after it stopped, again and again, until the Pi answers.

## 2.12.0

For the endless spool of the Fluidd panel (wm-ultra-fluidd-acepro-panel 1.11.0), and a clearer Doctor.

- **The saved tool mapping is reset when a print ends or is cancelled** (`PRINT_END`, `CANCEL_PRINT` in `macros.cfg`, both models, and through the macro patches on a Pi that is already installed). They already put `box_modify_t0`..`t3` back to 0 1 2 3; the saved copies `box_modify_tN_backup`, which `RESUME` reads, kept their last values. After an endless spool swap (tool 0 printed by toolhead 1) a pause during the heating of the next print, followed by a resume, would have given tool 0 the wrong toolhead.
- **`RESUME` purges 20 mm** at the wipe position before the print continues (WonderMaker: 10 mm). This is every resume, also the one after an endless spool swap, where it is the only purge.
- **Doctor: each Pi config file is named by what it does.** A missing or not included `rpi_homing.cfg` was reported as "calibration macros ... WM_BED_LEVELING". Now every file of `rpi-cfg/` has its own name and its own consequence; for `rpi_homing.cfg`: G28 without the 5 mm bed drop, and tool changes, the nozzle wipe and ACE loads stop with "Unknown command z_rise".
- Checked, nothing to fix: `z_rise` is defined once (`rpi_homing.cfg`), loaded, and found by all 19 callers; the factory `printer.cfg` files have none on purpose.

## 2.11.0

Bed warp wait before the bed mesh, `ADAPTIVE=1` as a number, the Wi-Fi hang, and a lighter touchscreen. Goes with wm-ultra-fluidd-acepro-panel 1.10.0. Tested on a ZR Ultra-S and a TM-T1 screen board.

- **Bed warp wait (`rpi-cfg/rpi_bed_soak.cfg`, `START_PRINT` in `factory/<model>/config/macros.cfg`).** After the bed reached its temperature, before the wipe and the bed mesh, the print waits so the bed plate stops bending: 2 s per degree (110 s at 55 C), a warm bed only for the missing degrees, with a line every 15 s. Switch `Bed_Warp_Stabilisation` (on by default, kept after a restart), window `WM_BED_SOAK_MENU`, Bed warp button on the touchscreen's ZR Tools page. `WM_BED_WARP_MEASURE` measures how the bed moves while it heats and saves the wait for that temperature by itself (the saving is new and not yet run on a printer). Tested in a print: 110 s at 55 C, then the mesh. An update adds the two `START_PRINT` lines to an installed `macros.cfg` through the macro patch list (README 4.8).
- **Main board fan is called MCU Fan (`printer.cfg`, both models and all variants).** `[controller_fan motherboard_fan]` is now `[controller_fan MCU_fan]`, so Fluidd shows "MCU Fan". Nothing else uses the name. At an update the printer.cfg merge renames the section (only its header line), so values you changed in it stay and the fan is never there twice (two sections on pin PA8 would stop Klipper).
- **`START_PRINT ADAPTIVE=1` (B-008, `macros.cfg`).** Klipper passes `ADAPTIVE=1` as the text "1", and the factory macro compared it with the number 1, which is never true: a start line with `ADAPTIVE=1` and no mesh corners always got the full 7 x 7 bed mesh. It is compared as a number now, so Klipper's adaptive mesh runs. Prints whose start line sends the mesh corners (the OrcaSlicer setup of README 4.2) are not affected. Tested: 3 x 3 adaptive mesh around the object.

- **No temperature graph on the screen board's main menu and Temperature page (`zr_tools/ks_wm_patches.json`, keys `main_menu` and `temperature`).** The graph drew up to 1200 points per line for every heater in Python on a board without a GPU, and took a whole core once its 20 minutes were full: KlipperScreen 96 percent, X 16 percent. Without it: 13 and 2 percent. The temperatures are still shown as numbers, and Cooldown, the presets and the number pad are unchanged.
- **A KlipperScreen stop or restart no longer opens the rescue window (`scripts/screen_board.sh`).** `xinit` answers a stop with exit code 1, so systemd counted every restart as a crash and opened the rescue window, and the next start then hit the rescue window's own X server ("Server is already active"). `/usr/local/sbin/wm-ks-start` now ends `xinit` on a stop and exits 0 (a real crash keeps its code; 3 crashes in 2 minutes still open the rescue window), and `KlipperScreen.service` is ordered after `wm-screen-rescue.service`. Boards installed before get both at the next update (copies `*.wm-before-stopfix-<time>`), and every restart of the script clears a failed state and starts KlipperScreen again when needed.
- **The Pi's Wi-Fi hang (`scripts/wm-wifi-watchdog`, `config/wm-wifi-watchdog.service`, `./installer.sh --wifi`).** Seen on a Pi 400: the Wi-Fi chip (brcmfmac over SDIO) stopped answering ("CMD53 sg block write failed -110") while the Pi, Klipper and Moonraker kept running, so Fluidd, SSH and the touchscreen lost the printer until a power cycle (the black box showed the Pi alive the whole time). On a Pi whose network is Wi-Fi through NetworkManager, every install and update now turns Wi-Fi power saving off on the active connection (a copy of the connection file is kept) and installs a watchdog that pings the router every 30 s: 3 misses turn the Wi-Fi off and on, still nothing 2 minutes later reloads the Wi-Fi driver. It never reboots the Pi and never touches Klipper; its steps are in `journalctl -t wm-wifi-watchdog`. A Pi on a cable is left alone. The doctor checks it, uninstalling stops the watchdog.
- **Touchscreen status for Fluidd (`zr_tools/wm-chamber-light-http`).** The board's light service answers `GET /status` (version, newest version on GitHub read at most every 6 hours, board CPU, KlipperScreen CPU, free memory, KlipperScreen state) and uploads the same every minute as `wm_screen_status.json` into the Pi's config folder. The Toolheads card of the Fluidd panel (wm-ultra-fluidd-acepro-panel 1.10.0) shows it, with an "update" chip when the board is behind.

## 2.10.0

Fewer files in the config folder. Nothing in the macros changed: the same sections, only in fewer files. Tested on a ZR Ultra-S (Klipper restarts, every macro and switch loaded, G28, host MCU, temperatures, chamber light).

- **`rpi-cfg/rpi_base.cfg`** holds the small always-on helpers that were separate files: `rpi_virtual_pins.cfg` (first, so the switch pins exist before anything uses them), `rpi_safety.cfg`, `rpi_print_end.cfg`, `rpi_tool_leds.cfg`, `rpi_head_sensors.cfg`, `rpi_unload.cfg`, and the `SET_GCODE_OFFSET` wrapper (from `rpi_pi.cfg`). Each part starts with its old file name.
- **`rpi-cfg/rpi_calibration.cfg`** now also holds the Z offset tools (was `rpi_zoffset.cfg`).
- **`rpi-cfg/rpi_homing.cfg`** (new): `homing_override`, `Z_HOMING`, `z_rise`, `_z_rise_run` and `idle_timeout`, moved out of the factory `printer.cfg` (both models, all 8 variants). `printer.cfg` keeps the hardware settings.
- **`rpi_pi.cfg` is written by the installer** (`scripts/wm_rpi_pi.py`) from the parts this Pi uses: `host-mcu` (`[mcu rpi]`), `pi-temp` (`config/rpi_pi_temp.cfg`), `board-temps`, `light` (`WM_CHAMBER_LIGHT`). These were `rpi_mcu.cfg`, `rpi_pi.cfg`, `rpi_mcu_temps.cfg` and `rpi_light.cfg`. The `--pi-sensors` step still restarts Klipper after adding a part and puts everything back when Klipper does not come up.
- **Update from 2.9.0 or older:** the old files leave `printer.cfg` and are kept in `~/wm-backups/rpi-join-<time>` and `~/wm-backups/rpi-pi-<time>`; the homing sections leave `printer.cfg` through the printer.cfg merge (it asks first). The doctor reports `rpi_pi.cfg` and homing sections that are still in `printer.cfg`.
- A lost `[include]` line of an `rpi_` file is added again below `rpi_base.cfg` (before, at the top: a lost `rpi_calibration.cfg` line would have come back above the switch pins and Klipper would not start).
- In the config folder: 20 `rpi_` files on the test printer became 11 (the ACE panel's four files are unchanged).
- Not changed on purpose: WonderMaker's own files (`extruder0-3.cfg`, `wm_zru_*.cfg`, ...): each `extruderN.cfg` is one toolhead and the include lines choose how many toolheads a printer has; tools and WonderMaker's scripts use them by name.

## 2.9.0

The fixes and tools made on the dev Pi since 2.8.0 that were tested on a ZR Ultra-S. Held back for a later version (built, not yet tested in a print): the bed warp wait before the mesh (Bed Warp Stabilisation) and `START_PRINT ADAPTIVE=1` read as a number.

**New**

- **Live Z adjust per tool (`rpi_zoffset.cfg`, `_OFFSET_SET` in `change_macros.cfg`, `SET_GCODE_OFFSET` in `rpi_pi.cfg`).** Z+ / Z- during a print changes only the tool on the carriage, and each tool gets its own adjust back at every tool change (before, a tool change reset it). Every print starts at 0. After the print (also after a cancel) the window `WM_LIVE_Z_MENU` offers **Save all** (added to the Z trim of each tool) or **Do not save**. `Z_OFFSET_APPLY_PROBE` and `Z_OFFSET_APPLY_ENDSTOP` (Fluidd's and the touchscreen's save buttons) open that window instead of baking the tool offset, trim and heat growth into the probe. `WM_LIVE_Z_ZERO` zeroes only the live adjust. The heat growth follows a nozzle temperature that goes up during the print. Tested in a print with 4 tools and 12 tool changes.
- **One Z trim per tool.** The trim for all tools is gone (two values that add up were easy to set by mistake). A trim for all tools left from 2.8.0 is added to each tool's trim once at the first start (`_WM_Z_TRIM_MIGRATE`); the print height does not change. `WM_Z_TRIM` needs `T=`.
- **Head filament sensors of the docked tools back on, and a load queue (`rpi-cfg/rpi_head_sensors.cfg`).** The tool change switched the sensors of the docked tools off and nothing switched them on again, so filament pushed into a docked tool by hand did not load. `WM_HEAD_SENSOR_WATCH` switches them on whenever no print runs or is paused and Klipper is idle. A filament pushed in while Klipper was busy (another tool loading) was dropped by Klipper; it is now queued and loaded afterwards, in order. Each `insert_gcode` (`extruder0-3.cfg`) marks its load with `_WM_HEAD_MARK` (only when that macro exists).
- **Speed test with a Save window (`rpi-cfg/rpi_auto_speed.cfg`, `scripts/wm_speed_limits.py`).** `WM_AUTO_SPEED` (klipper_auto_speed by Anonoei, MIT, shipped in `factory/<model>/klipper/klippy/extras/`) finds the highest acceleration and speed without lost steps, inside a zone that keeps clear of the tool docks. It needs a calibrated input shaper: without one it offers **Calibrate input shaper** first and comes back after the restart (tested: speed 390 without the shaper, 700 with it). The result window has **Check first**, **Save** (writes `max_accel` and `max_velocity` into `printer.cfg` with a copy, never above the input shaper's limit, then offers a Klipper restart) and **Do not save**. Needs the gcode shell command extension; removing the extension takes it out too.
- **Touchscreen (screen board and KlipperScreen on the Pi):** a **Sensors** page and a sensor strip with friendly labels, buttons for the Z calibration macros on Calibrate and the Unload menu on More, the live Z adjust on the print and Fine Tuning pages with a **Save Z Trim** button after a print, windows that show every text line and close at once, and the sensors read again after the start. KlipperScreen's own files are changed by `zr_tools/patch_ks_wm.py` (list `zr_tools/ks_wm_patches.json`, a copy `<file>.wm-orig` first).
- **The Pi finds its screen board (B-034).** The Pi never asked for the screen board's address; the board announces it to the Pi for the chamber light (`rpi_chamber_light.json`). `./installer.sh --board add` without an address now takes that board, and the Pi install and update offer to add it when it is not added yet (asks the board's ssh password once).
- **Screen board time zone (B-033).** The board comes set to China time. The board install asks for the time zone while it is still on China time (`--tz NAME` answers it ahead), `screen_board.sh --set-tz NAME` sets it alone, and the Pi gives every board it knows its own time zone at `--board add` and at every board update; the doctor reports a board on another zone.

**Faster**

- X and Y home at 80 mm/s (was 50). `z_rise` does nothing during a print (it asked the endstops at every dock move). The wait before the tool unlocks is 0.3 s (was 1 s) and the carriage backs off the dock at 12000 mm/min. Z speeds stay (a faster Z tripped the Z stall detection). Tested in prints.

**Fixed**

- **Idle timeout during a pause (`printer.cfg`).** It turned off the heaters of a paused print. Now during a pause only the nozzles go off; bed, chamber and motors stay so RESUME works. Outside a pause it turns off all heaters and the motors (before: only the nozzles).
- **`G28 X Z`, `G28 Y Z` and `G28 X Y Z` homed nothing (`printer.cfg`, `homing_override`).** They now home the axes named.
- **Touchscreen windows** showed only their last text line, and a Dismiss or button press waited until a busy Klipper had finished. Sensors showed off after a Klipper restart.
- **Cleanup:** dead macros removed: `_SAVE_SPEED`, `_RESTORE_SPEED`, `_OFFSET_RESET` (`change_macros.cfg`), `_START_PROBE`, `_RGB_CLOSE` (`macros.cfg`), `_CALIBRATE_MOVE_OVER_PROBE` (`offset_calibrate.cfg`), `_GANTRY_TRIGGER` (`load_cell.cfg`), `WIPE_NOZZLE_SIMPLE` (`fz-wipe-nozzle.cfg`). Nothing called them. On a Pi that is already installed the last two stay (harmless); the others go with the macro fixes step.

**Update on a Pi that is already installed**

- The `printer.cfg` changes (homing, `z_rise`, `homing_override`, idle timeout) come with the printer.cfg merge of the update (`./installer.sh --cfg-merge`), which asks first. `max_velocity` and `max_accel` are not touched.
- The macro fixes step also handles a fix whose lines a later version changed again (it no longer reports those as "different on this Pi"), and `tools/make_macro_patches.py` handles a block removed at the end of a file.
- The speed test module and `wm_speed_limits.py` are copied by the update; `rpi_head_sensors.cfg` and `rpi_auto_speed.cfg` are added to `printer.cfg` like the other rpi-cfg files.
- Tests: new checks for all of the above.

## 2.8.0

Z offset tools with a guided calibration, an unload menu, pause guards, the chamber light through Moonraker, and the fixes found on the dev Pi since 2.7.10. Everything was used on a ZR Ultra-S unless a line says otherwise.

**New**

- **Z offset tools (`rpi-cfg/rpi_zoffset.cfg`, README 4.3).**
  - `WM_OFFSETS_Z_HOT`: the Z offset of every tool measured the way a print takes its reference: bed 60 C, nozzle 140 C, wiped, touches at the bed centre, T0 first and last. Only Z is replaced. Nothing is saved when the two T0 results are more than 0.02 mm apart.
  - `WM_NOZZLE_GROWTH_CAL`: one-time measurement of how much a nozzle grows with heat (touch at 250 C, 140 C, 250 C). The correction is applied at every tool change above 140 C. On / off switch **Nozzle Heat Growth** in Fluidd, Outputs.
  - `WM_Z_TRIM` and the window `WM_Z_TRIM_MENU`: a saved first layer adjustment for all tools and per tool, kept across tool changes and restarts.
  - `WM_FULL_OFFSET_CAL`: a window that runs the three steps one after the other (X and Y with `WM_OFFSETS_ACCURATE`, hot Z, heat growth) and explains the first layer test print and the trims.
  - `_OFFSET_SET` (`change_macros.cfg`) adds the trims and the heat growth to the saved tool offset. All are 0 until you set them.
  - `START_PRINT` wipes T0 once more right before the bed mesh.
  - One touch that is not counted before the counted touches, and a console line every 30 s while a nozzle or the bed heats or cools (`_WM_WAIT_TEMP`). These two were only checked offline, not in a run on the printer.
- **`first-layer-stl/`:** flat test squares, one per tool head with its number cut out, and a 5 patch bed test. Also `Trim_Test_80x80.3mf`, a ready-made OrcaSlicer project: four squares of 80 x 80 mm, 0.2 mm high, one per tool head (square 1 = T0 to square 4 = T3), PLA 220 C, bed 55 C. Open, slice, print, then correct with `WM_Z_TRIM_MENU`.
- **`WM_FULL_CALIBRATION` is now `WM_FIRST_RUN_CAL`** (window title First Run Calibration, also on the touchscreen's Calibration page). It has 7 stages: the new stage 4 runs `WM_OFFSETS_Z_HOT` right after the rapid offsets, because those measure Z cold. The new stage was only checked offline.
- **Unload menu `WM_UNLOAD_MENU` (`rpi-cfg/rpi_unload.cfg`):** one tool or all tools, with or without an ACE Pro, confirm window, saved temperature, empty tools skipped, refused during a print or pause. `WM_UNLOAD_STOP` drops the rest.
- **Own virtual pin driver `wm_virtual_pins.py`** (`rpi-cfg/rpi_virtual_pins.cfg`, pins named `wm_pin:`), so Fluidd switches work with or without the ACE driver. Based on Pedro Lamas's virtual_pins (GPLv3).
- **Chamber light through Moonraker.** The light is the power device `chamber_light` (`scripts/wm_light_conf.py` writes it into `moonraker.conf` from the address the screen board announces, and corrects it when the board gets a new address). New macro `WM_CHAMBER_LIGHT` (`config/rpi_light.cfg`), and a print turns the light on at its start. The two Light buttons of the touchscreen now switch that device instead of calling the root helper, so Fluidd and the screen always agree; a board patched by an older version is brought up to date by its Update. New command `./installer.sh --light`; an install, `--update` and the Doctor do it too. The light service and the root helper on the board stay.
- **Start-up safety check (`rpi-cfg/rpi_safety.cfg`):** the grip check is switched on again when an interrupted filament insert left it off.
- **One good copy of `saved_variables.cfg`** (2.7.11, never published on its own): see below.

**Fixed**

- **`PAUSE` twice, `RESUME` without a pause (`macros.cfg`, `rpi_print_end.cfg`).** A second `PAUSE` during a pause ran the whole pause again and lost the tool map of the print. It now does nothing and says so. `RESUME` outside a pause says "Nothing to resume". The tool map is kept for the resume.
- **`ZR_RETRACT` skipped the tool pick-up when the tool was in its dock (`zr_tools.cfg`).** It compared the active extruder name, which stays the same after a tool is docked. Not yet tried on a printer without an ACE Pro.
- **A filament runout outside a print no longer starts the pause countdown** (`extruder0.cfg` to `extruder3.cfg`).
- **`TEST_W4` removed** (`offset_calibrate.cfg`), nothing used it.
- `_WM_UNLOAD_GO` is hidden (it was `WM_UNLOAD_GO`); the menu runs it.

**Update on a Pi that is already installed**

- **New step "Fixes inside WonderMaker's macro files" (`scripts/wm_macro_patches.py`).** An update never replaced `macros.cfg`, `change_macros.cfg`, `offset_calibrate.cfg` and `extruder0-3.cfg`, so fixes inside them only reached new installs. The update now makes each fix as a small text change: old lines found are replaced, a fix that is already in is left, and lines you changed yourself are left alone and listed. A copy of every changed file is kept. The list is `scripts/wm_macro_patches.json`, built by `tools/make_macro_patches.py`.
- The new `rpi-cfg` files are copied and included by the update. `rpi_virtual_pins.cfg` is included above `rpi_zoffset.cfg`, and the driver is copied first.
- Update the screen board too (its Update button, or `./installer.sh --update-boards`): it gets the First run calibration button and the Light buttons that go through Moonraker. Update the Fluidd panel to 1.8.0 for its chamber light button.

**Tests:** new checks for the macro patches, the chamber light (`moonraker.conf` section, both screen patches and their upgrade), the Z offset macros and the hot Z stage.


## 2.7.11

Safeguard for `saved_variables.cfg` against a power cut. Tested on the dev Pi.

- **One good copy of `saved_variables.cfg` is kept and put back when the file comes up empty.** Klipper and the ACE driver rewrite that file by wiping it first; a power cut in that moment left it empty, and Klipper then started with no tool offsets, calibration or ACE data (and stopped with "Unable to save variable"). New `scripts/wm_sv_guard.sh` (installed to `~/printer_data/scripts`): `backup` saves the live file as `saved_variables.cfg.wm-good` only when it is healthy (over 1000 bytes with `t0_position` and `box_modify_t0`); `restore` puts the good copy back when the live file is not healthy and keeps the bad one as `.wm-bad-<time>`. `klipper.service` runs `restore` before Klipper starts and `backup` after it stops; the new `wm-sv-guard.timer` runs `backup` every 10 minutes. Log: `~/printer_data/logs/wm_sv_guard.log`. Installed by install, update and repair (`step_svguard`), removed by `--uninstall`.

## 2.7.10

Cleanup from the 2026-11-14 code audit (both models). Nothing changes on a print; tested on the dev Pi.

- **`_raise_z` (`change_macros.cfg`): removed a branch that never ran.** It tested `printer.query_endstops.last_query.z`, a name that only WonderMaker's Klipper has, and would have called `SET_KINEMATIC_POSITION` (marking Z homed at an unknown position). The 2 mm raise during prints (first branch) is unchanged.
- **`TEST_ROUND` removed** (`change_macros.cfg`). It called `CALIBRATE_TOOL_OFFSETS`, which does not exist, and nothing used it.
- **Five dead duplicate macros removed from `offset_calibrate.cfg`:** `_OFFSET_RESET`, `_OFFSET_SET`, `_SAVE_TOOL_POSITION`, `CALIBRATE_TOOL_POSITION`, `SAVE_T_POSITON`. `change_macros.cfg` is included after it, so its copies were the ones that ran (the same order as on the factory screen board).
- **`_OFFSET_RESET` now prints "OFFSET_RESET" in the console**, like the removed copy did (`_OFFSET_SET` already printed its message).

## 2.7.9

- **`M191` now reads `BED_TEMP=` correctly, so the bed heats.** On an M command Klipper hands `BED_TEMP=65` to the macro as the text `=65`, which the macro read as 0 and skipped `M140`. The `=` is now removed first (`macros.cfg`, both models). Tested on the Pi: the print's start line `M191 S50 BED_TEMP=65` now sets the bed.
- **README: new section "Heating the chamber from OrcaSlicer"** with the start G-code line, what `M191` does, its variables and the 65 C limit.

## 2.7.8

- **`M191` heats the bed even when the slicer sends no `BED_TEMP=`.** Orca writes its own `M191 S<chamber>` line when the start G-code has no `M191`, and that line has no `BED_TEMP=`, so the bed assist did nothing. New variable `bed_assist_temp` (default 100 C, 0 = off) is used then. To use the first-layer bed temperature instead, put `M191 S[chamber_temperature] BED_TEMP=[bed_temperature_initial_layer_single]` above `START_PRINT` in Orca's Machine start G-code.

## 2.7.7

- **`M191` (wait for the chamber temperature) improved** in `macros.cfg` of both models. Orca's `M191 S[chamber_temperature] BED_TEMP=[bed_temperature_initial_layer_single]` now also starts the part fan (50 %) and the auxiliary fan (100 %) to circulate the air, warms the nozzle on the carriage to 150 C, and uses the bed to help heating when `BED_TEMP` is given; the fans and the nozzle are switched off again when the chamber is at its target. A target above 65 C is refused (the same limit as `ZR_CHAMBER`). The speeds, the preheat temperature and the limit are variables at the top of the macro (0 = off). `M141` is unchanged.

## 2.7.6

- **More filament materials** in the ZR Tools list (`zr_logic.py`, shared with the Fluidd panel through `tmt1.ini`): PLA+, PLA-CF, PETG-CF, PA, PA-CF, PC, ABS-CF, PA-GF, PC-ABS, PP and BVOH, added at the end so no saved index moves. The factory touchscreen may not know the new ones.

## 2.7.5

- **`ZR_PURGE` lowers the bed first.** `z_rise` now runs at the start of `ZR_PURGE` (`zr_tools.cfg`). Before, the move to the purge position (X-13 Y80) happened with no drop when X and Y were already homed, because the drop only ran inside the homing.

## 2.7.4

- **The Z drop before X/Y moves works on upstream Klipper.** The factory `z_rise` checked `printer.query_endstops.last_query.z`, a name only WonderMaker's own Klipper uses (it shortens `stepper_z` to `z`). On upstream Klipper the endstop is `stepper_z`, so `z_rise` never did anything and the bed was not lowered before homing or tool changes. `printer.cfg` (all variants) now has a fixed `z_rise` (with a helper `_z_rise_run`): it lowers the bed 5 mm when Z is below 5 mm and the Z endstop is not triggered, never while a print runs or is paused, and in the not-homed case it marks only Z as homed for that one move and clears it again.
- **`z_rise` runs first in the macros that move X or Y by themselves:** `_UNLOCK_TOOL`, `_LOCK_TOOL` (every tool swap and park), `WIPE_NOZZLE`, `WIPE_NOZZLE_SIMPLE`, `EXTRUDE_FILAMENT`, `RETRACT_FILAMENT` and `filament_insert_gcode`. Homing already calls it through `homing_override`. Both models and the four printer variants. `--cfg-merge` brings the change to a Pi that is already installed.

## 2.7.3

- **`SET_GCODE_OFFSET` wrapper in `rpi_pi.cfg`** (moved from the ACE panel's `rpi_ace.cfg`). While Z is not homed it sets the offsets without the move (`MOVE=1` becomes `MOVE=0`), so WonderMaker's tool change no longer stops with "Must home axis first" on upstream Klipper. With Z homed it passes everything through unchanged. The built-in command is kept as `_WM_SET_GCODE_OFFSET`.

## 2.7.2

- **Tool head LEDs use the factory macros.** `WM_TOOL_LEDS` (`rpi_tool_leds.cfg`) calls `_RGB_CURRENT` (green, tool on the carriage with filament), `_RGB_LOAD` (blue, filament in another tool head) and `_RGB_UNLOAD` (red, no filament), the same colours as the factory screen. It still checks every 2 s but only calls a macro when a tool's state changes (kept in `_WM_LED_STATE`), so the automatic filament load is not blocked.

## 2.7.1

- **Tool head LEDs no longer stop the automatic filament load.** `WM_TOOL_LEDS` (`rpi_tool_leds.cfg`, runs every 2 s) now sends the LED colour with `SYNC=0`. Before, each colour update woke the toolhead and put Klipper's idle timeout into "Printing", and upstream Klipper ignores a filament-inserted event in that state, so WonderMaker's own load (heat, push, wipe, park) never started when you pushed filament in or after an ACE load.

## 2.7.0

- **Update everything from one place.** Fluidd's Update button for the **Fluidd panel (ACE Pro project)** now applies the update on the Pi, like the installer's own Update button: backup, install, Klipper restart (`wm-panel-update.path` watches the panel folder, `scripts/pi_update.sh --panel` applies it; refused during a print; log `~/wm-pi-update.log`). Before, it only downloaded the files.
- **Screen boards updated from the Pi.** `./installer.sh --board add t13dp@<board-ip>` asks for the board's password once and sets up an ssh key; `--board list|remove` manage the list. `./installer.sh --update-boards` runs each board's own Update (the same root script the Update button on its screen runs), and the Pi's Update now does it after the installer update. Only boards you add are ever touched.
- **`./installer.sh --update-all`** downloads and applies the installer, the Fluidd panel and then the boards. `--check-updates` now also lists the panel and the boards (installed and latest).
- **Doctor** checks all three against GitHub and offers "update everything now" for what is behind (it skips quietly when the Pi has no internet).
- **Update Pi button on the screen:** lists what is new (installer, Fluidd panel) and has two choices, "Not now" and "Update now".

## 2.6.0

- **The config files this installer puts on the Pi are now called rpi_ instead of wm_.** `rpi_calibration.cfg`, `rpi_nozzle.cfg`, `rpi_pi.cfg`, `rpi_print_end.cfg`, `rpi_tool_leds.cfg`, `rpi_fan_guard.cfg`, `rpi_chamber_light.json`, `rpi_mcu_temps.cfg`, `rpi_mcu.cfg` (was `wm_rpi_mcu.cfg`), and the ACE Pro files `rpi_ace_driver.cfg`, `rpi_ace.cfg`, `rpi_endless.cfg`, `rpi_stats.cfg`, `rpi-ultra-install.conf` (ACE panel project 1.6.0). Macro names (`WM_BED_LEVELING`, `_WM_NOZZLE_TYPE`, `ACE_WM_ASSIST` ...), variable names and the helper script `wm_nozzle.py` keep their names.
- **`./installer.sh --update` renames an existing Pi once.** Copies of the old files and of every config file it edits go to `~/wm-backups/rename-<time>/`, the files are renamed, the `[include ...]` lines in `printer.cfg` (and in other config files) are changed, and the uninstall list is updated. Your own edits in these files are kept. If an old and a new file both exist, the new one is kept. Doctor tells you when the old names are still there. Klipper reads the new names at its next restart (the update restarts it).
- **Chamber light:** the screen board service now uploads `rpi_chamber_light.json`, and the Fluidd panel (ACE project 1.6.0) reads it. Update the Pi, Fluidd panel and screen board together; until the board is updated the Chamber light button stays hidden.

## 2.5.3

- **RESUME now says "Print resumed" in the console** and, when an ACE Pro is present, hands feed assist back to the automatic watcher after the print restarts (the manual choice is set to "no choice"). This was already on the dev Pi and is now in both factory `macros.cfg` files (Ultra and Ultra-S).

## 2.5.2

- **Feed assist button moved next to Purge** on the toolhead Filament page (ACE Pro only). The bottom row is now Purge, Feed assist, Cool, all the same size. The button is purple with a green "ON" badge when feed assist is on, and dark grey with a red "OFF" badge when it is off, so you can see the state at a glance.

## 2.5.1

- **New "Update Pi" button on the screen** (More page, also on the Pi's own KlipperScreen). It does what Fluidd's Update button does: asks Moonraker whether GitHub has a newer installer, shows the installed and latest version, asks to confirm, then downloads it; `wm-pi-update.service` applies it (backup, configs, add-ons, restart of Klipper and Moonraker, log `~/wm-pi-update.log`). It is refused during a print, and it explains when the installer folder on the Pi has local changes. The screen board's old "Update" button is now named "Update screen".

## 2.5.0

- **Console messages for the important steps.** Wipe nozzle (which tool goes to the wipe area, and when it is done), resume ("Resuming the print", "Print resumed"), tool change ("Changing tool: T? to T?"), parking a tool in its dock, and load, unload, extrude and retract filament now print a line in the console.
- **RESUME primes the nozzle.** Before the wipe, the tool goes to the wipe spot and purges 10 mm at 300 mm/min (ACE feed assist is on for that tool when an ACE is connected). There is no retract after it yet; it will be tuned after real resume tests.
- **Tool changes keep the slicer's speed.** T0-T3 give the print its feedrate back, so moves after a tool change no longer crawl at the dock or wipe speed.
- **Faster wipe, 200 mm/s** (variable `wipe_speed` in WIPE_NOZZLE, was 50 mm/s). The wipe saves and restores the G-code state.
- **Cooldown waits do not reheat.** The cooldown at the end of NOZZLE_PREPARE and POP waits only until the nozzle is below 102.5 C (104.5 C in POP) instead of heating back up after an undershoot, and it uses the physical heater of the slot.
- **7 mm clearance for idle moves.** New macro `_WM_CAL_CLEARANCE` raises the head to at least 7 mm above the bed before idle calibration, idle wipes and idle tool changes. It is skipped during a print or pause, and when X, Y and Z are not homed.
- **Startup purge on the left edge** (X0, Y100 to Y150, 20 mm) instead of the front edge, which could reach the front panel.
- **Maximum acceleration is 5000 mm/s2** (was 20000) in the factory printer.cfg.
- Ideas from the Wondermaker+ project (anselor) were checked against this setup; only the items above were taken.

## 2.4.0

- **Timelapse really works.** The installer now adds the `[timelapse]` section to `moonraker.conf` (before, Moonraker never loaded the timelapse part, so every layer printed "Timelapse: disabled, take frame ignored" and no video was made). The question now reads "Install and activate timelapse".
- **The console shows why the printer paused or stopped.** The four filament path sensors now print "Filament runout on path N (tool N). The print is paused." (before, Klipper paused without a word). PAUSE, CANCEL_PRINT and PRINT_END print one line each.
- **The Fluidd console keeps 5000 lines** (`[data_store] gcode_store_size`, was 1000, about an hour of a print) so messages are not pushed out by temperature lines. A value you set yourself is kept.
- **Extruder `max_error` is 120** (Klipper's default) in the factory extruder files. The tool head LEDs follow the number of tool heads, and the dock sensor check stays on while a nozzle is unlocked in the Change nozzles macro.
- **KlipperScreen: Feed assist on/off button** on each tool's Filament page when an ACE is connected. It works during a print and a pause.

## 2.3.1

- **Fluidd install is safer.** The new web page is unpacked next to the old one and checked; it replaces the old one only when complete. A damaged download leaves the old Fluidd untouched and says so. Only one copy of the old Fluidd is kept.
- **A failed Fluidd install is no longer recorded as done**, so the next `--update` tries again.
- **`--update` now shows the warnings** it collected (they were hidden before).

## 2.3.0

- **New macro `WM_SCREWS_CAL`: bed screws.** It homes, heats the bed to 55 C and a nozzle to 140 C (like the bed leveling; T0 is picked up if another tool is on the carriage), wipes the nozzle and runs Klipper's `SCREWS_TILT_CALCULATE` on the four screws of `[screws_tilt_adjust]`, then turns the heaters off. The console shows how far to turn each screw (00:15 = a quarter turn); run it again until every screw says 00:00. It asks first in a Start / Cancel window, refuses during a print or with heaters on, prints "step 1 of 4" to "step 4 of 4", saves nothing and is listed in `WM_CAL_HELP`. Fluidd puts it in the Raspberry Pi category (blue) with the other `WM_*` macros.

## 2.2.1

- **The Klipper, Moonraker and Fluidd versions note is removed.** Fluidd never shows the `info_tags` of an update entry, so the note could not be seen. The installer's entry in Fluidd keeps its plain description, which now says that the Update button applies the update (the `wm-pi-update` watcher of 2.2.0 stays).

## 2.2.0

- **Fluidd's Update button applies the installer update.** Moonraker only runs `git pull` on the installer folder. A small systemd watcher (`wm-pi-update.path`, started by the install and by `--update`) notices the new commit and runs `./installer.sh --update --yes` for you (`scripts/pi_update.sh`), outside Moonraker so its restart does not stop it. It does nothing when the installed version already is the new one, when a print is running or paused (Moonraker also refuses to update during a print), or when your user has no passwordless sudo (then run `./installer.sh --update` in SSH). Log: `~/wm-pi-update.log`. The units are removed by the uninstall.

## 2.1.1

- **Step messages in the single-stage calibration macros.** `WM_BED_LEVELING`, `WM_VIBRATION_COMP` and `WM_BED_PID` now say which step they are on ("step 1 of 3: homing", "step 2 of 3: probing 49 points ...", "step 3 of 3: saving"), so a long wait is no longer silent.

## 2.1.0

- **Webcams (crowsnest) are set up for you.** The install asks how many cameras (1 to 4), the picture size (480p, 720p, 1080p or `WIDTHxHEIGHT`) and `max_fps`; or give `--cameras N --cam-resolution ... --cam-fps N`. The camera ports are found automatically (USB by-id names, ribbon cameras through libcamera). Pi 4 / CM4 use camera-streamer, the other models ustreamer (a ribbon camera: camera-streamer, or spyglass on a Pi 5), editable per camera in `crowsnest.conf`.
- **`crowsnest.conf` is rewritten for crowsnest v5** (the old template had v4 options that v5 ignores) and starts with an explanation of every option and a link to the crowsnest manual. An existing `crowsnest.conf` is never overwritten: the new explained copy is saved as `crowsnest.conf.new`.
- **Fluidd lists the cameras** as Camera, Camera 2, Camera 3 (and 4): the `[webcam ...]` sections are added to `moonraker.conf`, above anything else, and ones you made yourself are left alone.
- **`./installer.sh --webcam-setup`** repeats the camera questions later (copy of the old file kept, service restarted).

## 2.0.12

- **Update: the screen's version is the version of the screen's files, not of the installer folder.** After a `git pull` the installer folder is already new, so `--update` compared GitHub with the folder, said "Already up to date" and then stamped the version marks as new while the panel files were still the old ones. Now `Installed` comes from `zr_version.txt` next to the panels (then `~/wm-screen-backup/version`), and when the numbers match but the panel files differ from the newest ones, the update refreshes them anyway. `--post-update` no longer stamps the version marks unless the panel files really are that version's.

## 2.0.11

- **Update never goes back to an older version.** Right after a new version is published, GitHub's raw file cache can still serve the previous small screen bundle for about 5 minutes, while the version file already says the new number. The menu then offered "Update now" with "Newest: 2.0.9" while 2.0.10 was installed, which would have been a downgrade. `--update` now stops with "the download is OLDER than the one installed" and changes nothing, and every GitHub read of the updater and of the screen's Update button carries a cache buster so it fetches the current copy.

## 2.0.10

- **`--update` on an up-to-date board now repairs what is missing.** A board that already had the newest files could still lack the Update and Factory mode permissions, the passwordless sudo rule or the version marks (an update started by an older script never added them), and `--update` only said "Already up to date" and asked for the password again later. Now it runs `--post-update` in that case. If you decline the sudo rule once, an up-to-date `--update` does not ask again (`--post-update` does).

## 2.0.9

- **Update button: it showed "new version" when the screen already had the latest.** The screen read its version from a file that only a 2.0.8 install wrote, so an update run by an older script left it "unknown" and every check offered an update. Now every install and update writes the version next to the panels (`zr_version.txt`) and to `~/wm-screen-backup/version`, and the screen reads its own panel version first. The dialog shows **Installed** and **Latest** in every case (up to date, new version, GitHub unreachable).
- **Update button: it did nothing when the sudoers rule was missing**, and said nothing. It now reports why it could not start, with the command to fix it. An update started by an older script used to leave the old sudoers line, so the new button could not run; an update now runs the new script's `--post-update` at its end, which refreshes the root copy of the script, the sudoers lines and the version marks.
- **New `--post-update`**: (re)applies the permissions the Update and Factory mode buttons need. Run it once over SSH on a board whose Update button says the permission is missing.

## 2.0.8

- **Screen board install: the board user gets sudo without a password.** The install asks once (default yes, `--yes` accepts) and writes `/etc/sudoers.d/wm-user-nopasswd` (checked with `visudo`). After that the install, the Update button and later updates never stop at a password prompt. Anyone who can log in as that user then has full control of the board, so Factory mode and `--factory-restore` remove the rule again. `--no-sudo-rule` skips it.
- **KlipperScreen: Update button** (ZR Tools > More > Update, screen board only). It reads the newest version from GitHub (one small file), says "Up to date" or offers the new version, then updates the installer folder and the screen files from the small screen bundle and restarts KlipperScreen and Klipper. It refuses during a print. It runs through the root copy of the script and one extra sudoers line (`--update --yes --detach`), as a separate systemd unit with a log in `~/wm-screen-backup/update.log`, and gives the files back to the board user. The screen remembers its version in `~/wm-screen-backup/version` and the installer folder in `~/wm-screen-backup/installer_dir`, so the button works even when the script is run as a lone copy. **A board installed before 2.0.8 needs one `bash scripts/screen_board.sh --update` over SSH first**, which adds the sudoers line and the button.
- **KlipperScreen: the Light button is always on the print screen** (while printing and paused). It used to be added only when the root light helper existed, so a missing helper hid it without a word. Now tapping it says "The chamber light helper is not installed." when the helper is missing. A print screen patched by an older version is corrected on the next update.

## 2.0.7

- **Screen board: small download.** The board needs only about 90 KB (`screen_board_bundle/wm-screen-board.tar.gz`), not the whole 500 MB repository. The README has a one-line command for it, and `--update` on the board uses it too (it falls back to the full download if the small file is not available). `scripts/make_screen_bundle.sh` rebuilds it and the test suite checks that it is current.
- **Screen board: Factory mode button fixed.** The copy of `screen_board.sh` in `/usr/local/sbin/wm-factory-restore` (used by the on-screen button, the rescue window and the USB flag) stopped at once with "lib_free_space.sh is missing". The helper is now installed next to every copy, and a missing helper no longer blocks a restore. A board installed before this keeps the old copy until `--update` or a reinstall.
- **KlipperScreen: Unlock gripper has its own icon**, drawn like the Lock gripper icon in the colour of each theme (`zr_tools/make_unlock_icon.py`). KlipperScreen ships no unlock icon in any theme.

## 2.0.6

- **Full Calibration starts with the Extruder Setup** (stage 1 of 6). It picks up T0 to T3 and checks that each tool head has the CAN id of its dock. If every tool came out of its own dock it goes straight on with the other five stages; if the ids must change it asks, restarts the firmware, and you start the Full Calibration again. The window explains this and the hang-the-extruders instruction.
- **Hidden helper macros.** `_WM_CAL_STOP`, `_WM_NOZZLE_TYPE` and `_WM_NOZZLE_CHANGE_END` start with `_` now, so Fluidd's macro list no longer shows them; the windows still have their buttons (Stop heaters, Nozzle Type, Done). `WM_NOZZLE_CHANGE` no longer offers the Extruder Setup, and its windows now say that Done leads to the Nozzle Type window.
- **`WM_ZOFFSET_UP` and `WM_ZOFFSET_DOWN` are removed.** Nothing used them (no macro, no ZR Tools button).
- **`WM_CAL_HELP` lists the current macros**, including the Full Calibration stages, the Extruder Setup and the hidden helpers.

## 2.0.5

- **README: using OrcaSlicer.** A new section 4.2 says to use OrcaSlicer and to write the Machine G-code fields without a `;` in front (`START_PRINT ...`, `PRINT_END`, `TIMELAPSE_TAKE_FRAME`, `PAUSE`), with the exact lines and three screenshots, and a step in the quick start. A line that starts with `;` is a comment, so Klipper would skip it.
- **README: CAN ids of the other boards** (section 4.1): the hub, extruder board, T0 to T3 and the load cell start with placeholder ids; power-cycle the printer, then `./installer.sh --can-ids` (or `--can-ids set T0 <id>`), and FIRMWARE_RESTART if the main board kept the shutdown state.
- **First start no longer says "All checks passed" while boards still have placeholder CAN ids.** It fails that check with the commands to fix it, and the "not on the bus" hint now also mentions boards that still hold an id from an earlier Klipper session.
- **The Fluidd macro categories are only reported as set up when Moonraker's database holds them.** Fluidd creates its settings the first time it is opened, so a fresh install can have nothing to store them in yet; the installer then tells you to open Fluidd once and run `--fluidd-categories`.
- **The host MCU is built from the bundled Klipper (v0.13.0-827), not the older v0.12.0 download.** `mcu rpi` now reports the same version as the host, so Klipper no longer sees a version mismatch, and Moonraker shows the Klipper version instead of `?` (the bundle now carries `klippy/.version`). `--update` rebuilds a host MCU that was made from another version, and copies the version file to a Pi that lacks it.

## 2.0.4

- **The services are started last.** Before, Klipper was enabled and started and only then the board temperature sensors and the host MCU were added (two more Klipper restarts, and both were taken out again when Klipper was not ready yet). Now an install adds them first and starts the services at the very end, once. `./installer.sh --pi-sensors` on its own still needs a running Klipper.
- **The Fluidd macro categories are set up after Moonraker starts.** They could not be set at the ACE Pro step ("Moonraker did not answer"); the installer repeats them once Moonraker runs.
- **First start asks the CAN bus up to 3 times.** The first query right after `can0` came up could be empty and the check said "nothing answers on the CAN bus" although the main board was there.

## 2.0.3

- **Fix: the 5 compiled WonderMaker modules were missing from GitHub.** The bundled Klipper has its own `.gitignore` with `*.so`, so git left `cs1237`, `hx711`, `heater_air_core`, `heater_feng` and `xy_offset_calibrator_core` out of the commits. A fresh install stopped with "Checksum of the factory files does not match". They are now in the repository (checked against `modules.sha256`), and a test fails if a file listed in the checksum files is not tracked by git.

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
