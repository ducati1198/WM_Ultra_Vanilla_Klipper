# Changelog

## 2.26.0

- **Check of the ZR changes inside KlipperScreen (screen board doctor).** `scripts/screen_board.sh --doctor` now checks every change the installer makes in KlipperScreen's own files (`zr_tools/ks_wm_patches.json`: sensor strip, live Z adjust, popup windows and pictures, the Choose toolheads page, and so on). It says "all ZR changes inside KlipperScreen are in", or names the file and key that is missing (a KlipperScreen update removed it) or different (another KlipperScreen version or your own edit), and offers to put the missing ones back and restart KlipperScreen. It only looks; nothing changes unless you accept the fix. New `patch_ks_wm.py --check KEY FILE` (exit 0 in, 10 missing, 11 different).
- **Tests:** the E-step render test now reads the config the way Klipper does (a line is cut at the first `#`), has old=0 cases for CONFIRM, STEP and SET, and the suite check fails on any render error. New `tests/test_ks_patch_check.py`.

## 2.25.2

- **E-step (F-221):** `_WM_ESTEP_CONFIRM` (the Save and restart question) no longer divides by zero when it is opened outside a calibration (same guard as `_WM_ESTEP_S3`).

## 2.25.1

- **Fix (B-2.25.0 E-step window did not load):** the 2.25.0 guard in `_WM_ESTEP_S3` carried a Jinja comment `{# ... #}`; Klipper cuts a config line at the first `#`, so Klipper stopped with "Error loading template _WM_ESTEP_S3". The comment is gone from `rpi_nozzle.cfg`, and a suite check now refuses any `{#` in `rpi-cfg/`. If your Klipper shows that error after the 2.25.0 Update, run the Update again.

## 2.25.0

- **Your own values are protected during an update (F-222).** The update remembers your saved variables, `rotation_distance` lines, the SAVE_CONFIG block and `crowsnest.conf` before it starts and checks them again before Klipper restarts. A value an update step changed is put back and listed; otherwise it prints "Your settings: untouched". New helper `scripts/wm_protect.py`, test `tests/test_protect.py`.
- **E-step fixes (F-222b):** `_WM_ESTEP_S3` no longer divides by zero when it is opened outside a calibration (it shows "does not fit"); `wm_estep.py` keeps its `printer.cfg` backups in `config/backup/`, not next to `printer.cfg`.
- **`--rollback`:** goes back to how your settings were before the last update (restores the newest "before-update" backup, safety copy first).

## 2.24.0

- **New: `WM_ESTEP_CAL`, e-step (rotation_distance) calibration of one tool (F-221).** Windows in Fluidd and KlipperScreen: pick the tool, heat, insert 100 mm (head sensor checked), mark at 120 mm, slow 100 mm extrusion, measure with step buttons, save into `printer.cfg` (old value kept as a comment, backup first) and restart. New: macros at the end of `rpi-cfg/rpi_nozzle.cfg`, helper `scripts/wm_estep.py` (installed to `~/printer_data/wm-tools/`, checked by `--doctor`), four pictures `zr_tools/wm_images/estep-*.png`, an "E-step calibration" button under Tool offsets in the KlipperScreen Calibration panel, tests `tests/test_wm_estep.py` and `tests/estep_render.py`. Fluidd pictures and the Fluidd notes are in `docs/estep/`.
- **KlipperScreen shows one picture big.** A popup with exactly one picture shows it as wide as the screen allows (at most 60 percent of the screen height); two to four pictures stay small as before (the three setter pictures do not change).
- **Head sensor watcher stays out of the e-step calibration** (`WM_HEAD_SENSOR_WATCH` in `rpi_base.cfg` counts it as busy), so pushing filament in by hand does not start the automatic load.

## 2.23.2

- **One standard writing for every KlipperScreen popup (F-219, F-220).** Every popup text is Large and bold (warnings yellow). It is a stock-KlipperScreen patch (`prompts2` in `zr_tools/ks_wm_patches.json`) applied by the Pi install and by the screen board installer, so the Pi and the screen board match.
- **Offsets "stopped again" window (F-219).** When the same wrong result comes twice at a tool, the window shows old, new and moved values and the buttons "Use the new value" (recommended: run Offsets rapid again), "Keep the old value" and Cancel (`rpi_calibration.cfg`, `rpi_nozzle.cfg`).
- **Rapid offsets (F-211, F-217, F-218):** manual nozzle clean first, no nozzle heating, every nozzle waits until it is under 80 C before it is measured; the first-run and Z-calibration flows clean first (F-212, F-213); purge without an extra swap (F-216); Nozzle PID screen button moved to the nozzle page (F-214).
- **`WM_LIVE_Z_ZERO` is now the hidden macro `_WM_LIVE_Z_ZERO`.** The KlipperScreen fine tune patch renames it on a board that has the old name (`from`/`to` entries in the patch list).
- **Backup folder (F-157, F-158, F-159):** the installer and `wm_ultra_backup.py` keep config backups in `printer_data/config/backup`.
- **Streamer question (F-191):** new option `--cam-mode` (and a question at install) to choose camera-streamer or ustreamer for the Pi webcam (`wm_crowsnest.py`).
- Tests: new `tests/test_f220.py`, `tests/test_cfg_index.py`; calibration render tests follow the new rapid flow; the popup text of "no longer valid" no longer holds a `;`.

## 2.23.1

- **B-081: a tool change to a head that another slicer tool also uses no longer waits for a cooldown.** With the tool map (Resume with T*, endless spool swap) two slicer tools can print with the same head. The slicer cools the tool it leaves (`M104 S140 Tx`), and that cooled the head the next tool change was about to use: it then waited for the head to cool and heated it again. The `M104` macro (`macros.cfg`, both models) now skips a standby temperature (1 to 169 C, below the target) while a print runs when more than one slicer tool maps to that head, and says "Cooldown of slicer tool Tx skipped: head y also prints another slicer tool". `M104 S0`, print temperatures, a paused print and a head used by one tool only work as before. `./installer.sh --update` adds it to an installed Pi (macro patch list: 1 entry for 2.23.1). Tested on a real print by the user.

## 2.23.0

- **Start purge (F-190, F-206).** At the start of a print every toolhead the print uses draws its own purge line. New Fluidd switch `Purge_Line_Every_Toolhead` (ON = every used head, OFF = only the first tool). The old F-160 purge block is dropped; F-190 replaces it.
- **Purge while paused (F-203) and a confirmation page before "Resume with T*" (F-204).** `rpi_base.cfg` (`WM_PURGE_MENU`, `_WM_PURGE`, `_WM_PURGE_DONE`, `_WM_RTOOL_CONFIRM`) and `zr_tools.py`.
- **Hot Z offset calibration waits for the bed (F-205).** `WM_OFFSETS_Z_HOT` waits after the bed is hot, before touching it, with the same bed warp wait as a print start (switch `Bed_Warp_Stabilisation`).
- **KlipperScreen Tools page (F-195, F-197).** The bottom tab is now "Tools" (category buttons); Filament layout and Climate page with ACE off; centred banner.
- **Choose toolheads page (F-208, B-080).** Starting a print from the file list or the job page opens the toolhead choice page first, with a remembered tool map and "More" labels. New stock KlipperScreen patches in `zr_tools/ks_wm_patches.json` (`gcodes` key, a 7th `job_status` hunk), applied by the screen board script.
- **Z trim window (F-162).** The trim window shows a plain-text top line `TRIM IS x.xx MM` (`rpi_calibration.cfg`).
- **More logs for troubleshooting (F-210).** Everything is in Fluidd > Configuration > Other Files and in `./installer.sh --support-bundle`.
  - New `wm-system.log`: when Klipper, Moonraker, KlipperScreen, crowsnest, nginx and the network services started, stopped, failed or restarted, with their journal warnings.
  - `wm-events.log` gets a `STATE` line at every pause, resume and cancel: tool, G-code position, head position, offsets, heaters, print state. A print that is misplaced after a resume can now be checked in numbers.
  - `wm-ace.log` now rotates at 1 MB and keeps two old files (`.1`, `.2`).
  - The support bundle also holds `wm-system.log`, `wm-ace.log.2` and the last 800 lines of `moonraker.log`, `KlipperScreen.log` and `crowsnest.log`.
- **New hidden macro `_WM_LOG_STATE`** (macros.cfg, both models) writes the `STATE` line. `PAUSE`, `RESUME` and `CANCEL_PRINT` call it at their start and end; nothing else in them changed. It only reads values (guarded for a missing heater), so it cannot stop a pause. `./installer.sh --update` adds it to an installed Pi (macro patch list: 7 entries for 2.23.0).
- The Fluidd console shows the new lines (`WMLOG ...`) after each pause, resume and cancel.

## 2.22.1

- **Update: no more "changed" lines for fixes that a later version takes back.** `scripts/wm_macro_patches.py`. The heat-at-wipe lines added to `change_macros.cfg`/`macros.cfg` in 2.13.0 were removed again in 2.22.0; on a Pi already at 2.22.0 the update applied the first and then the second, reported "changed macros.cfg #1 (2.13.0)" and "#8 (2.22.0)" and exited with 10 every time, though the file did not change. A file that ends up the same is now reported as unchanged.
- **Tests:** the installer test mode no longer looks at the machine's real `klipper`/`klipper-mcu` services (`--remove` and `--doctor`), so the suite also passes on a Pi that runs Klipper; the macro patch list test uses the 2.22.0 base commit; tests updated to the 2.22.0 macros (purge length from `_WM_RTOOL`, start purge macro in `rpi_base.cfg`); the panel test is skipped when the panel repository is not on the machine (`WM_PANEL_REPO`).
- No change for a real Pi apart from the update message above.

## 2.22.0

- **KlipperScreen ACE page redone (F-193, F-194).** Bigger spools, four big buttons, and three page buttons (Dryer, Endless spool, Feed/Retract) that each open their own page: a larger endless circle with larger tool numbers, a Feed/Retract page with Stop, a dryer page with bigger temperature and time. Nothing scrolls on the 800x480 screen. The Filament page has a Load menu and a coloured Feed assist button. `zr_tools.py`, `zr_views.py`, `zr_logic.py` and the screen board bundle are updated.
- **Hidden secondary macros (F-167).** `_WM_ENDLESS_SET/_FIXED/_PLAN/_CONTINUE`, `_WM_STATS_RESET`, `_WM_LOAD_STOP`, `_WM_UNLOAD_STOP`, `_ACE_WM_RETRACT`, `_ACE_WM_ASSIST` and `_WM_Z_TRIM` start with an underscore. The Fluidd build and KlipperScreen call them by these names.
- **Macro fixes and tests from the F-187 to F-192 series** in `rpi_base.cfg`, `rpi_calibration.cfg`, `rpi_nozzle.cfg`, `zr_tools.cfg` and the factory `macros.cfg`, `change_macros.cfg`, `extruder0-3.cfg`, `fz-wipe-nozzle.cfg` of Ultra and Ultra S. `scripts/wm_macro_patches.json` has 28 new entries for 2.22.0.
- **Docs:** `docs/MACROS.md` and `docs/FLUIDD.md` follow the renames.
- Goes with the panel repository 1.17.0 (Fluidd build with the new macro names).

## 2.21.1

- **`rpi_auto_speed.cfg` is joined into `rpi_nozzle.cfg` (2.21.1).** One file less: the speed test (`WM_AUTO_SPEED`, `WM_AUTO_SPEED_VALIDATE`) needs the same shell command extension as the nozzle macros, so it lives in the file that has the same install condition (not in `rpi_calibration.cfg`, which every printer gets, and not in the panel's `rpi_ace.cfg`, which only an ACE printer gets). The update moves an old `rpi_auto_speed.cfg` to ~/ultra-backup/config/<date>/rpi-join-*, takes its include line out of printer.cfg and installs the new `rpi_nozzle.cfg`. The macro names do not change. The module check (`auto_speed.py`) now applies to `rpi_nozzle.cfg`. New test for the move.
- **The KlipperScreen "Updating" page closes by itself when an update is done (F-151).** After Update in Fluidd the screen showed an Updating page that stayed open until Finish was pressed, and a stale reference stopped the next update from opening a page at all. The page now closes about 5 seconds after the update is complete and Klipper is ready again (after 3 minutes at the latest). New `zr_tools/patch_ks_update.py`, called by the screen board install and update (idempotent, keeps `base_panel.py.wm-orig`). New test `tests/test_ks_update.py`.
- **The chamber light watcher no longer restarts Klipper in the middle of a macro (F-155).** `wm-light.path` runs `./installer.sh --light --yes` whenever the screen board uploads `rpi_chamber_light.json`, and that step restarted Klipper every time, also during loads and unloads with a hot nozzle: two tool boards shut down (T1 mid-load, T0 during an unload). Now Klipper restarts only when `printer.cfg`, `rpi_pi.cfg` or `rpi_light.cfg` changed, and never while a macro runs, a print is active or a heater target is above 0 (new helper `klipper_busy`; the log says so and the macro starts with the next restart). 3 new tests.
- **`scripts/wm_macro_patches.json` regenerated.** It was out of date since the F-150 edits of 2.21.0 (`tools/make_macro_patches.py`).
- **Documents of the Pi in `docs/`.** `MACROS.md` (every macro, checked against the files and the ACE driver, read line by line), `MOONRAKER.md`, `FLUIDD.md` and `DIFFERENCES.md` (what differs from upstream Klipper, Moonraker and Fluidd). Reading only; nothing in the installer reads them.

## 2.21.0

First Run Calibration in a new order, fewer homings, real macro names, the nozzle heats at the wipe position, and a clearer end window (F-143 to F-150).

- **First Run Calibration no longer contains Extruder Setup (F-142) and has a new order (F-143).** 7 stages: tool setter position (found and saved by itself), tool offsets (rapid, saved), hot Z offsets (saved), input shaper, bed PID, bed leveling, nozzle PID. The first three save as they finish (no restart); the other four are saved together by the one Save and Restart window at the very end. The setter stage is new: `_WM_SETTER_AUTO` runs the quick search and the block middle measurement of the tool setter helper without windows (mode `cal = 2`) and saves `probe_position`; a failed search, a nozzle that meets something or incomplete middles raise an error and stop the calibration (`_WM_SETTER_AUTO_CHECK`). Stage 2 runs `WM_OFFSETS_RAPID CONFIRM=1 XYLIMIT=3`: the saved offsets of a new install come from the repo (another printer), so the normal 0.20 mm check would stop the first run; only a gross error (3 mm) stops it there. Normal runs keep 0.20 mm. The CAN ids of the tool heads are set by the installer's Extruder Setup (`WM_EXTRUDER_SETUP` when you need it again). The old second stage after a firmware restart (`_WM_FIRST_RUN_CAL_REST`, `variable_full`) is gone.
- **Fewer homings in First Run Calibration (F-145).** `WM_OFFSETS_Z_HOT`, `WM_VIBRATION_COMP` and `WM_BED_LEVELING` homed all axes every time they started, so a First Run did three extra full homings. Each now homes only when X, Y and Z are not all homed (as `WM_OFFSETS_RAPID`, `WM_BED_PID` and `WM_NOZZLE_TEMP_CAL` already did). Run alone on a cold printer they still home first. 3 new tests.
- **Every `variable_` line of the `rpi_*` files has a comment (F-146).** 87 variables in `rpi_base.cfg`, `rpi_calibration.cfg` and `rpi_nozzle.cfg` and the 4 of `rpi_fan_guard.cfg` (Ultra and Ultra-S) now say what they hold and in which unit. Comments only, no value changed.
- **`WM_NOZZLE_TEMP_CAL` is now `WM_NOZZLE_FULL_PID` and tunes at the wipe position (F-147).** Each head is picked up and the PID is run at the wipe position (it was the middle of the bed). Then the nozzle heats back to the PID target, is wiped, cools to 140 C and is wiped a second time. The wait below 80 C between heads is gone (the 140 C wipe replaces it). The old name is removed everywhere (First Run Calibration stage 7, windows, Nozzle Change text, screen label, `--pid-cfg` message). 2 new tests (order of the steps, no move to X150).
- **The nozzle now heats at the wipe position (F-150).** New helper `_WM_GO_WIPE` (moves the head to the saved wipe position, does nothing when it is already there). `RESUME` (and so endless spool), `G29`, `NOZZLE_PREPARE`, `_WM_NOZZLE_PREPARE` and `POP` heat there; the three that purge on the bed go back to the purge spot after the heat. `LOAD_FILAMENT` and `UNLOAD_FILAMENT` pick the head up if it is not on the carriage, heat at the wipe position, wipe after the load or unload and park (they also home first when needed, and they now switch off the stepper of the head they used). `_WM_ACE_GRAB` heats at the wipe position when its head is on the carriage, and `ACE_WM_LOAD` (panel repo) moves the head there before the filament starts to feed. Every macro falls back to the old behaviour when the helper is missing. New render checks for all of them.
- **Nozzle heat growth measurement (`WM_NOZZLE_GROWTH_CAL`) homes only if the printer is not homed (F-149).** It was the one macro of the Full Offset Calibration that always ran `G28`. New render checks for both cases.
- **First Run Calibration: the end window shows the result of every test, and a queued start call can no longer replace it (F-148).** First found on a real run: a second `WM_FIRST_RUN_CAL` (clicked while the calibration ran) was queued and ran right after the end, so the start window took the place of Save and Restart. Now `WM_FIRST_RUN_CAL` ignores a call that arrives within 10 s of the end window, and `_WM_FIRST_RUN_CAL_DONE` lists: setter position, tool offsets, hot Z offsets (already saved), then input shaper (type and Hz for X and Y), bed PID (old to new Kp Ki Kd), bed mesh (just "Bed mesh") and nozzle PID per head (old to new), which are saved by Save and Restart. The start window text for stage 7 now says wipe position. 4 new tests.

- Tests: 25 new checks.

## 2.20.1

Found by the first fresh-SD install test (F-141): the end of the install told the truth too early, the Fluidd categories were not set up, and the doctor did not check them.

- **Extruder Setup in the installer now writes the ids it found (F-141).** The ids were read from Fluidd's button line, which ends in `|primary`, so the last id was `ac...|primary`; the writer refused it, the installer restarted the firmware anyway and said "in dock order now" while nothing was written. Now only 12-digit ids are read, and after the apply the files are read back: when they do not hold the new ids it says so, warns and keeps Extruder Setup pending. 2 new tests use the real button line.
- **The Fluidd macro categories are set up after Klipper is ready** (new place at the very end of the install). Before, they ran while Klipper was still stopped, so the macro names were unknown ("Moonraker did not answer (Not Found)") and the install said "open Fluidd once". Fluidd does not have to be opened first: the sorter creates Fluidd's macro settings itself. The panel's `--fluidd-categories` now waits up to 60 s for Klipper (panel 1.16.1).
- **The doctor checks the Fluidd categories** and offers to sort the macros. New doctor checks: saved_variables safeguard (timer and current script), ModemManager rule, `wm_canmatch.py` present, Klipper state, ACE Pro on USB, load cell on firmware V2 (offers the load cell menu).
- **Klipper's first state is no longer reported as an error.** The throw-away connections of the board matching leave the main board in a shutdown state; the start now does one firmware restart before it reports, and the last warning is dropped when Klipper is ready at the end (it said "error" although the printer was fine).
- **`wm_sv_guard.sh` uses a temp file of its own and runs one at a time** (a lock). The install and the 10-minute timer both wrote `saved_variables.cfg.wm-good.tmp` and one failed with "File exists".
- **New udev rule `99-wm-no-modemmanager.rules`:** ModemManager probed the ACE Pro (USB 28e9:018a) every 3.5 s while no Klipper held its port (258 reconnects in 10 minutes on the test Pi). The rule tells it to leave the ACE Pro, the MKS CAN adapter and Klipper boards (1d50) alone.
- **The backup folder is swept a second time at the very end** of the install: the board matching and the Wi-Fi step write backups after the first sweep, and the doctor then reported "some backups are outside ~/ultra-backup" right after a fresh install.
- **The chamber light is set up by itself (no doctor needed).** The screen board announces its light (`rpi_chamber_light.json`) some minutes after the install, when its own service has started, so the install found nothing. The installer now adds `wm-light.path`: it watches that file and runs `./installer.sh --light --yes` when it appears or changes (log `~/wm-light.log`). The doctor checks that it runs; the uninstall removes it.
- **First Run Calibration no longer contains Extruder Setup (F-142).** It has 6 stages (bed leveling, rapid offsets, hot Z offsets, vibration compensation, bed and hotend PID, nozzle temperature) and asks for Save and Restart once, at the very end. The CAN ids of the tool heads are set by the installer's Extruder Setup (`WM_EXTRUDER_SETUP` when you need it again). The old second stage after a firmware restart (`_WM_FIRST_RUN_CAL_REST`, `variable_full`) is gone.
- Tests: 16 new checks.

## 2.20.0

The installer finds the CAN ids of every board by itself, and Extruder Setup is required after it.

- **CAN boards are matched by the firmware name each board reports (F-140).** `scripts/wm_canmatch.py` (new) asks the bus which ids answer (five scans, because the load cell answers only now and then), connects to each id with a throw-away Klipper and reads the firmware name from its log: `KLP_MCU_` main board, `KLP_HUB_` hub, `KLP_EXT_` extruder board, `KLP_CELL_` load cell (factory firmware and V2 both), `KLP_THR_` tool head. The first start (when an id in the config is not on the bus, placeholders always are) and `--can-ids` now write the main board, hub, extruder board and load cell ids and the four tool head ids in id order, with no stored id and no factory screen. If a board is missing, two look the same, or a board answers only from its bootloader, nothing is written and the problem board is named. A copy of every changed file goes to `~/wm-rpi-backup/uuid-<time>/`.
- **Extruder Setup is required after that, and cannot be skipped (new `--extruder-setup`).** The four tool heads report the same firmware name, so their order is not known. Right after Klipper starts the installer shows a warning (look at the printer, all four tool heads in their docks, heaters off and cold, nothing in the way) and you can only press Enter; then it runs the screen's Extruder Setup (`_WM_MATCH_RUN`), waits for the result, and writes the dock order itself (`_WM_MATCH_APPLY`) when the tools did not come out in id order. It also restarts the firmware once when the main board is "shutdown" from the throw-away connections. A run that stops writes nothing and says why. Until it is done, `--doctor` and the end of the install say so (marker file `~/printer_data/.wm-extruder-setup-pending`). Unattended runs (`--yes`, Fluidd's Update) never move the printer: they say it is still to do.
- **The load cell lookup (`cell_uuid`) reads only real `*.cfg` files**, not the copies named `*.cfg.wm-before-...` next to them (a copy with the old placeholder was found first on the dev Pi and the CELL scripts used the wrong id).
- Tests: 20 new checks (matching, missing/duplicate/bootloader-only boards, copies outside the config folder, first start, forced Extruder Setup, doctor).

## 2.19.1

The Wi-Fi watchdog is removed.

- **The Wi-Fi watchdog (`wm-wifi-watchdog`, 2.11.0 to 2.19.0, F-061/F-136) is gone.** On 2026-11-18 the Wi-Fi chip of the dev Raspberry Pi 4 dropped off its bus twice (07:22 and 10:23) and neither the Wi-Fi restart nor the driver reload could bring it back; only a reboot or power cycle did. `installer.sh`: `step_wifi` now only turns Wi-Fi power saving off on the NetworkManager connection (as before); at every install, update and `--wifi` an old watchdog is stopped and deleted (`wifi_wd_remove`); the doctor says so when one is still there. Deleted `scripts/wm-wifi-watchdog` and `config/wm-wifi-watchdog.service`. README: the troubleshooting row says that only a reboot or power cycle (or a network cable) helps. Tests changed.
- Docs and comments: the dev Pi is a Raspberry Pi 4 (Wi-Fi chip BCM43455), not a Pi 400.

## 2.19.0

The screen board shows the factory camera and has the new ZR Tools screens; the Wi-Fi watchdog, webcam restart and panel backups fixes are in too.

- **The factory camera on the screen board is shown in Fluidd as Camera (item 37, F-138).** The board looks for a camera in its USB (`scripts/screen_board.sh`, new `step_screen_camera`, option `--camera`, also run by the install and the update): with one it writes its `crowsnest.conf` (720p, 30 fps, port 8080, `no_proxy: true`; your own file is kept, crowsnest's default file is replaced with a copy) and enables crowsnest, without one crowsnest stays off. The board service `wm-chamber-light-http` announces the address in `rpi_screen_camera.json` next to the chamber light. On the Pi the webcam questions start with "Is the factory camera plugged into the factory screen board?" (default yes, `--screen-camera yes|no`, saved as `SCREEN_CAM`): yes points nginx `/webcam/` at the board (`scripts/wm_crowsnest.py upstream`), Fluidd lists it as **Camera**, and the Pi's own cameras start at `[cam 2]` (port 8081, Camera 2 to 4; 0 to 3 cameras, 0 builds no webcam service). README: new section "The factory camera on the screen board", the wire (USB-A to MX1.25) is only for a Pi without the factory screen board.
- **ZR Tools on the screen board (F-137).** ZR Tools opens by itself on top of the main menu at the start and after every Klipper restart; the Back button goes to the previous page (from the ZR Tools main page to the KlipperScreen main menu); an offline page with Menu/System buttons when Klipper or Moonraker is down and ZR Tools in the Menu of the Connecting screen; ACE and endless spool switches, the nozzle growth switch (no flicker: a tapped value is held up to 5 s until Klipper reports it), the spool tap to edit; the Unload menu as ZR pages; every confirm question and every macro window (`prompts.py`: Start/Yes blue 78 px, Cancel dark, no pink buttons, text on a card, the window fits the screen) in one design; the message banner sits at the very top of the screen; bigger tiles on More, Timelapse and System; the Z trim and Tool setter pages in the same style. KlipperScreen changes: `zr_tools/ks_wm_patches.json` keys `prompts` and `screen` (a `done` entry marks a file that has them), `patch_ks_wm.py` understands it.

- **Wi-Fi watchdog can now recover a hung Wi-Fi chip (F-136).** `scripts/wm-wifi-watchdog`. On 2026-11-18 the radio command timed out and the driver reload failed with `Module brcmfmac is in use` (NetworkManager and wpa_supplicant held wlan0), so the Pi stayed off the network until a power cycle. The radio commands are now time-limited; the driver reload stops NetworkManager and wpa_supplicant first, removes `brcmfmac_wcc` and `brcmfmac`, unbinds and rebinds the SDIO host, and always starts NetworkManager again. New `sudo wm-wifi-watchdog --reload-now` runs the reload once. Tested on the dev Pi, a Raspberry Pi 4 (Wi-Fi back in about 10 s); a real chip hang could not be forced.

- **Webcams: Moonraker restarts as soon as a new `[webcam Camera N]` section is written (F-135).** `installer.sh`, new `moonraker_reload_webcams`. On the dev Pi `crowsnest.conf` had two cameras and `moonraker.conf` had `[webcam Camera 2]`, but Fluidd listed one because Moonraker had started before the section was written. Moonraker is now restarted right after the write (when its service exists; not in a dry run). Test added (it also passes on the old code, so it guards the restart but does not reproduce the miss).

- **The screen board installer puts the board user into the sudo group automatically (item 35).** `scripts/screen_board.sh`, new `step_sudo_group`, called before the existing sudo-without-a-password step. Same behaviour as the load cell V2 installer: if the board user is not in the `sudo` group it is added (`usermod -aG sudo`), without a question; it takes effect at the next login. Nothing is done when the user is already in the group, on a dry run it only says what it would do. The existing question about sudo without a password (and `--no-sudo-rule`) is unchanged. New tests in `tests/run_tests.sh`; the ACE panel installer 1.16.0 does the same.

- **Panel backups (item 36b).** The ACE panel installer 1.16.0 writes its undo folders, the saved original Fluidd, its Fluidd copies and its macro lists straight into `~/ultra-backup` (`installer/acepro-panel`, `fluidd-page`, `fluidd-macros`) and moves its old folders there once. The backup helper never prunes `installer/acepro-panel` (new test), and **Remove > ACE Pro** looks for its saved copies there first (the old `~/acepro-backup` as fallback). README section "One folder for every backup" updated.

## 2.18.1

- README: the false-touch text and the `samples_tolerance` troubleshooting row now say that most false touches are a broken read of the load cell board and point to firmware V2 (section 4.1b); the tolerance in the text is now 0.05 (it said 0.1).

## 2.18.0

- **Load cell board firmware V2 in the install (item 45).** A full install now ends with a check of the load cell board (CELL): when the board is not on the newest patched firmware of the project [wm-load-cell-mcu](https://github.com/ducati1198/wm-load-cell-mcu), the installer downloads that project into `~/wm-load-cell-mcu` and runs its flash script (it shows the plan and asks once; a factory bootloader is replaced in software first). A board that already runs V2 is left alone. Never in an update, never without an answer (`--yes` and Fluidd's Update button only note it), skipped with `--no-load-cell`. New `./installer.sh --load-cell` and **Advanced → Load cell board** open the project's menu (flash V2, factory firmware, restore the original bootloader, check the bootloader, update). New functions `step_load_cell`, `do_load_cell`, `cell_get`; 9 new tests.

## 2.17.1

A better tip for the unload and a guard for its cooling. Tested on a ZR Ultra-S (T2 and T3, with and without the ACE Pro).

- **ZR Tools: the filament tip is formed with a cooling step (F-119, B-069, B-070).** `zr_tools/zr_tools.cfg`, `_WM_UNLOAD_TIP` and `_WM_LOAD_SETTINGS`. The old tip had a long string and a thick blob, and one tip stuck in the tool. After the snap the heater now goes `cool_drop` (30 C) lower and the macro waits for that temperature, then `cool_s` (4 s) more, so the tip hardens before the slow pull; the pull is 45 mm at `pull_speed` 20 mm/s (was 10), and `tip_push_mm` is 0 (was 3). The cooling target is never lower than `min_extrude_temp` of the extruder plus 5 C (180 C on this printer): below `min_extrude_temp` Klipper refuses the pull and the unload stops with the filament held. Used by `ZR_RETRACT`, `ZR_UNLOAD` and the ACE unload of panel 1.15.0. Tested: ACE unload of T2 twice, `ZR_RETRACT` and `ZR_LOAD` of T2 with the ACE off; tip judged good.
- The zr_tools.cfg of the Pi is replaced as before (an edited copy is kept as `zr_tools.cfg.zrbak_*`), so your own values of the tip settings are saved there.

## 2.17.0

Tool offset calibration made safer and faster, the zr_tools pair without the Purge button, and two installer fixes.

- **Macro patch list: a line changed in three versions no longer breaks the older entries (B-066).** `scripts/wm_macro_patches.py`. An older fix whose lines a later version changed again counted as done only when every later fix was in; the later fix of the touch tolerance (0.1 to 0.05) made the fix of 2.14.0 count as missing and its older neighbour with it, so a second update run reported lines "different on this Pi". Fixes are now checked newest first. An older fix whose lines were changed again counts as done only when a later fix that rewrote those same lines is really in the file, so lines you changed yourself are still left alone and reported (exit 11). Found by the "second run changes nothing" test.

- **Undo no longer overwrites the restored Fluidd (B-064).** `installer.sh`. `./installer.sh --undo` restored `~/fluidd` and then the Fluidd backup copied over it again; the restore now keeps what the undo brought back. Test added.

- **Offset calibration: hot Z is kept, X and Y are checked, touches are tighter (F-114, F-116, F-117; items 39, 40, 41).** `rpi-cfg/rpi_calibration.cfg`, `factory/*/config/offset_calibrate.cfg`. `WM_OFFSETS_RAPID` and `WM_OFFSETS_ACCURATE` now home only when the printer is not homed and set all extruders to 140 C at the start. The saved flag `wm_hot_z_done` (set by `WM_OFFSETS_Z_HOT` when its run passes) makes both keep the saved hot Z of T1 to T3 and save only X and Y; without the flag the Z of the run is saved as before. New hidden helper `_WM_OFFSET_CHECK` runs after each tool: when the new X or Y differs more than `xy_limit` (0.2 mm, one setting in each macro, `XYLIMIT=n` in rapid) from the saved one, it puts the old values of that tool back, turns the heaters and fan off and stops with a message. The factory touch tolerance `samples_tolerance` of `[tools_calibrate]` is 0.05 mm (was 0.1), tested with the CELL firmware V2: 240 touches, 0 retries. The tool setter helper touches the block ends 1.0 mm below the block top (`mid_drop`, `mid_wadd`, `mid_tol` in `_WM_SETTER`) so the cone of the nozzle meets the block and the nozzle cannot climb it (B-065); the block middles take one touch per end and a length check, with the right block middle from the front end and the known length when needed. Tests: `tests/rpi_cfg_render.py` (preheat, homing, flag, limit, restore) and the tolerance check in `tests/run_tests.sh`. The macro patch list is made at version time (`tools/make_macro_patches.py`).

- **ZR Tools: the Purge button and `ZR_PURGE` are gone (F-104); Load and Unload without an ACE are new (F-106, B-054).** `zr_tools/zr_tools.cfg`, `zr_tools/zr_tools.py`, `INSTALL.md`. `ZR_LOAD T=n` picks up the tool and heats it at the wipe area to its saved filament temperature; you then insert the filament and the head sensor starts WonderMaker's own load, so there is one purge, not two. Filament already in: it pushes `load_push_mm`, wipes and parks. `ZR_RETRACT` and `ZR_UNLOAD` pick up the tool, form the tip at the wipe area with the shared `_WM_UNLOAD_TIP` (also used by the ACE unload in the panel's `rpi_ace.cfg`), wipe, park. Settings in `_WM_LOAD_SETTINGS`. On the touchscreen's tool page the Purge button is removed: with an ACE the Feed assist button spans the two left columns under Load and Unload, without an ACE Load and Unload are two rows tall; the confirm texts say what happens. Tests: `tests/rpi_cfg_render.py` (ZR_LOAD render checks, no ZR_PURGE), a check in `tests/run_tests.sh`. Screen bundle rebuilt.

## 2.16.0

Troubleshooting logs and a black box, one folder for every backup, the print start purge and the files tested on the printer since 2.15.0. Tested on a ZR Ultra-S; the install from zero and the update from 2.15.0 were run on a Raspberry Pi 4 without a printer.

- **The Pi's tested files come into the repository (Pi-only work of F-096 to F-107).** `rpi-cfg/rpi_base.cfg` now also holds homing, `z_rise`, the idle timeout, the bed warp wait and the print start purge `_WM_START_PURGE`; the separate `rpi_homing.cfg` and `rpi_bed_soak.cfg` are gone. An update moves the old files and their include lines out (copies in `~/ultra-backup/config/<date>/rpi-join-*`). `rpi_calibration.cfg` and `rpi_auto_speed.cfg` are the tested versions.
- **Factory files, both models.** New Klipper driver `wm_print_info.py` (the slicer's tool list and temperatures of the file, used by the print start purge; `[wm_print_info]` in `printer.cfg`, copied into Klipper's extras by the update). Updated `air.py`, `collision_detect.py`, `feed_slot.py`, `stall_sensor.py`, `tools_calibrate_core.py`, `macros.cfg` (`START_PRINT` calls `_WM_START_PURGE` when it exists, else the old left-edge purge; the probe count message); `printer.cfg`: 9 x 9 probe points, bed mesh tension 0.2, fade 1 to 10 mm. Checksum lists regenerated. The macro patch list brings the config changes to a Pi that is already installed (only where the lines are still the factory text).
- Held back until the screen board can be read again: `zr_tools/zr_tools.cfg` and `zr_tools.py` (Purge button removed with the macro, the better Load), as one pair.
- **Troubleshooting logs in Fluidd (`scripts/wm_log_digest.py`, `config/wm-log-digest.service`, `./installer.sh --logs`).** `klippy.log` is mostly a copy of the config written at every start, so real events are buried. A small service (it only reads) now writes `wm-events.log` (one line per event), `wm-config-check.log` (config problems after every start: missing or doubled includes, config below SAVE_CONFIG, a section defined twice, the unsupported Jinja tag `do`, `;` `#` `*` in RESPOND text, files nobody includes) and `wm-ace.log` (the ACE Pro driver lines, console messages and the USB serial port appearing or disappearing) into `~/printer_data/logs`, where Fluidd shows them under Configuration > Other Files, plus a copy of the black box. Limits: events 1 MB x 3 and 120 lines a minute, ace 500 KB x 2 and 200 lines a minute. Installed in every install and update, checked by the doctor, stopped by `--uninstall`.
- **Black box (`scripts/wm-blackbox`, `config/wm-blackbox.service`, `config/50-wm-persistent.conf`).** One line every 10 seconds to `/var/log/wm-blackbox/blackbox.log` (power flags, temperature, core voltage, load, memory, USB and disk kernel messages), forced onto the disk, and a note at the next start whether the last stop was clean. `wm-blackbox report` shows the last crash. The system log is kept on the disk (200 MB) so a crash leaves a trace. Installed with the logs.
- **Support bundle (`--support-bundle`) holds more.** The new logs, `klippy-real.log` (the last 1500 klippy lines without the config copy and the Stats lines), `console-last-300.txt`, `printer-state.txt` (Klipper state, print state, config warnings, ACE status), `files-and-versions.txt` (date, size and checksum of every config file, program versions), and the new services in the system report. A `README.txt` in the bundle says where to look first. All scrubbed as before.
- **One folder for every backup: `~/ultra-backup` (`scripts/wm_ultra_backup.py`, `./installer.sh --ultra-backup`, item 36).** Sorted by type (`settings`, `config`, `fluidd-page`, `fluidd-macros`, `installer`, `drivers`, `other`) with the date inside; the newest copy of each config file stays next to it; limited to 400 MB (oldest go first) and nothing is written below 2 GB free; `INDEX.txt` records every move. `~/wm-backups` is now `~/ultra-backup/settings` (the backup, restore and clean-up pages follow); the installer's migration copies go to `~/ultra-backup/config/<date>/`. The old places are moved at the next install or update. The safeguard copy `saved_variables.cfg.wm-good` `printer.cfg.wm-model-bak`, the installer records and the newest folder of each undo store (`~/wm-rpi-backup/old-*`, `~/acepro-backup/wm-*`, `~/fluidd_backup_*`) are never moved, so `--undo` keeps working. Tests: `tests/test_ultra_backup.py` and a section in `tests/run_tests.sh`.
- **The Fluidd console keeps 1000 lines again (`[data_store] gcode_store_size`).** 2.x set 5000; the value is now 1000 (the Moonraker default, written down so it is visible). A value you set yourself is kept.
- **Webcam: "Set up the cameras again" asks again (B-060).** The answers saved by the first install (for example 1 camera) hid the questions, so a second camera was never written. The menu entry and `--webcam-setup` now ask again, and the number of cameras found is the default. Test added.
- Tests: `tests/test_log_digest.py` (rules, limits, rotation, config check) and a section in `tests/run_tests.sh` (install, second run, dry run, replace an old script, doctor, uninstall wiring, bundle contents and scrubbing).

## 2.15.0

- **Touchscreen: the steps of Tool Setter Position on their own page (`zr_tools/wm_setter.py`).** The adjust window had 24 step buttons in six rows without a label (KlipperScreen puts all text of a window on top) and jumped back up after every step. On the touchscreen it is now a page built like the Move page: X left, X right, Y back, Y front, Z up, Z down, one row to choose the step (0.05, 0.1, 0.5, 1 mm), the numbers now / saved / moved, and Find automatically, Save, Back to saved, Close. It opens by itself after Start, closes when the helper closes, and calls the same macros, so the limits are the same. The start window with the pictures, the Find result and the Save windows are unchanged. Fluidd is unchanged.
- **Touchscreen: Z trim on one page (`zr_tools/wm_ztrim.py`).** One screen in place of two windows: T0 to T3 with their saved trim (tap one to choose it), two big buttons Closer to the bed and Further from the bed, the step (0.01, 0.02, 0.05, 0.1 mm), Set this one to 0, Set all to 0 (asks first), Close. Same macros and the same 0.30 mm limit.
- **How:** three new changes to KlipperScreen's `prompts.py` in `ks_wm_patches.json`: a window whose buttons call `_WM_SETTER_STEP`, `_WM_Z_TRIM_WIN` or `_WM_Z_TRIM_STEP` is not shown, its page opens (or is refreshed) with the window's data. When the page cannot load, the window opens as before. No macro changed. `screen_board.sh` copies the two pages at install, update and repair.

## 2.14.0

- **Tool setter position helper (`WM_SETTER_PROBE_POSITION`, `rpi-cfg/rpi_calibration.cfg`; Fluidd category RPI Calibration, touchscreen Calibrate > Tool setter position).** The offset calibration starts every touch from one saved position next to the tool setter (the two small blocks at the back right of the bed): `probe_position` in `saved_variables.cfg`, X, Y, Z and two offsets. Until now it was set by eye and typed by hand. The helper puts the T0 nozzle there (the last part down with the touch sensor on, so it stops when it meets something) and opens a window with pictures of the right position.
  - **Find automatically** (T0 only, about 5 minutes) does it all: it touches the top of the back block from above and sets the height to that top minus 0.5 mm (the middle of the 1 mm straight nozzle tip), touches both blocks on both faces for X and Y, and touches the two ends of each block for the middle of their 6 mm width. One window shows what was found. **Save with middles** writes X = middle of the back block, Y = middle of the right block and the two offsets that keep the calibration touching there; **Save found** keeps the factory offsets. The line before is kept as `probe_position_backup` (**Restore old**), and **Test with T0** runs the real calibration touch from the new position.
  - When the quick search fails (no block top, a face not touched, or a touched width that is not about 2.75 mm) a window says why and asks before the **wide search**, which starts 10 mm to the left and in front of the saved position and sweeps slowly until it meets the blocks. The toolhead needs that room next to the dock.
  - Step buttons (1, 0.5, 0.1, 0.05 mm) adjust by hand, within 10 mm of the saved X and Y and not lower than 3 mm under the saved Z.
- **New module `wm_tool_touch.py` (`[wm_tool_touch]`, command `TOOL_CALIBRATE_TOUCH`)**: one touch of the tool setter in one direction with a travel limit, back to the start, result in `printer.wm_tool_touch.touch`. WonderMaker's `tools_calibrate` driver is not changed. The update copies the module before `rpi_calibration.cfg`.
- **False touches of the tool setter.** Its load cell sometimes reports a touch without contact (broken sensor reads, about 1 in 90, always the same few values; measured on a ZR Ultra-S with load cell firmware `KLP_CELL_WM_ZRU_20251223`). The helper's touches run with a low acceleration after a short rest, must agree two or three times within 0.1 to 0.3 mm and are repeated when they do not, and a touch without travel is thrown away. The block top is only taken from two spots that agree (the two touches of a spot within 0.05 mm, two of the five spots within 0.3 mm): one false touch in the air above the block is dropped instead of setting the height. The factory offset calibration (`[tools_calibrate]` in `offset_calibrate.cfg`, both models, and through the macro patches) now needs its three touches within **0.1 mm** (was 0.5) and tries **6** times (was 3), so Offsets rapid and accurate redo a false touch instead of using it.
- **Pictures in a window.** A macro can show pictures with `RESPOND TYPE=command MSG="action:prompt_image name [name ...]"`. The touchscreen shows `KlipperScreen/wm_images/<name>.png` side by side (KlipperScreen patch list, `prompts`); Fluidd shows them with the ACE Pro panel 1.13.0. A screen without the change ignores the line.

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
- **The Pi's Wi-Fi hang (`scripts/wm-wifi-watchdog`, `config/wm-wifi-watchdog.service`, `./installer.sh --wifi`).** Seen on a Raspberry Pi 4 (Wi-Fi chip BCM43455): the Wi-Fi chip (brcmfmac over SDIO) stopped answering ("CMD53 sg block write failed -110") while the Pi, Klipper and Moonraker kept running, so Fluidd, SSH and the touchscreen lost the printer until a power cycle (the black box showed the Pi alive the whole time). On a Pi whose network is Wi-Fi through NetworkManager, every install and update now turns Wi-Fi power saving off on the active connection (a copy of the connection file is kept) and installs a watchdog that pings the router every 30 s: 3 misses turn the Wi-Fi off and on, still nothing 2 minutes later reloads the Wi-Fi driver. It never reboots the Pi and never touches Klipper; its steps are in `journalctl -t wm-wifi-watchdog`. A Pi on a cable is left alone. The doctor checks it, uninstalling stops the watchdog.
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
