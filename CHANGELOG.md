# Changelog

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
