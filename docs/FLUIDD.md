# FLUIDD.md - Fluidd on the WonderMaker Ultra Pi

Written 2026-11-18. Sources: `~/fluidd` on the Pi (`.version` = **v1.38.0**), the panel repo `wm-ultra-fluidd-acepro-panel` (fluidd/README.md and the patch `fluidd-v1.38.0-zr-ace.patch`, 8158 lines), Moonraker's database (`fluidd` namespace), Fluidd docs https://docs.fluidd.xyz/ and source https://github.com/fluidd-core/fluidd. Docs of other Fluidd versions were not used. Nothing on the printer was changed.

## Installation and connection
- Installed as static files in `~/fluidd` (served by nginx on port 80). `~/fluidd/config.json` is the stock one (blacklist fluidd.xyz/.net, theme presets Fluidd and Annex...; `hosted: false`). Our build is `fluidd-v1.38.0-zr-ace.zip` (sha256 file next to it) made from Fluidd v1.38.0 plus our patch; the installer unpacks it into `~/fluidd` (`mv ~/fluidd ~/fluidd_backup`, copies config.json back).
- nginx on port 80 serves Fluidd and forwards the Moonraker API and websocket to port 7125 and the camera stream to the webcam service (the installer doctor checks "nginx forwards the API to Moonraker"; the exact nginx location list was not read). Fluidd talks to Moonraker over HTTP and one websocket; Moonraker then talks to Klipper over the UDS socket.
- Trusted client rules and CORS are in Moonraker (see MOONRAKER.md).

## What our patch changes (files in the Fluidd source)
All changes are one `git format-patch` series on v1.38.0. Files touched: `src/App.vue`, `src/views/Dashboard.vue`, `src/store/layout/state.ts`, `src/store/printer/getters.ts`, `src/store/printer/types.ts`, `src/store/console/actions.ts`, `src/store/console/types.ts`, `src/components/widgets/filesystem/FileSystem.vue`, `src/components/widgets/status/PrinterStatusCard.vue`, `src/components/widgets/runout-sensors/RunoutSensorsCard.vue`, `src/components/common/ActionCommandPromptDialog.vue`, and new files in `src/components/widgets/zr/`: `ZrToolheadsCard.vue`, `ZrToolDialog.vue`, `ZrPrintDialog.vue`, `ZrMappingView.vue`, `zr.ts`, `zrMixin.ts`, `zrUi.ts`, `zrPrintHook.ts`, specs, and the pictures `public/img/wm/setter-compare.svg`, `setter-height.svg`, `setter-place.svg`.
What it adds for the user: the **Toolheads card** (4 toolheads, chamber target, air filter, chamber light, doors, print with colours), the **Choose toolheads** window at print start (filament mapping), the **ACE Pro** part inside the card (slot state, tangle/head sensor dots, ACE header with connection/temperature/humidity, dryer with six presets, endless spool section) and **pictures in macro windows** (`action:prompt_image name ...`, files `img/wm/<name>.svg`).
It reads from Klipper: `ace_instance_0`, `filament_switch_sensor path_N` and `filament<N>`, the saved variable `wm_endless`, the print file metadata, the macro `WM_ENDLESS_CONTINUE` (endless row only when it exists).

## Macro buttons (Fluidd macro list, namespace `fluidd`, key `macros`)
116 macros stored; 103 visible in 8 categories, 13 hidden on purpose (M104, M106, M107, M109, M141, M190, M191, M221, SET_GCODE_OFFSET, WM_BED_SOAK, Z_OFFSET_APPLY_ENDSTOP, Z_OFFSET_APPLY_PROBE, z_rise).
| Category | Visible macros |
|---|---|
| RPI Calibration | 26 |
| WM Factory Calibration | 18 |
| AcePro | 14 |
| WM Ultra Filament | 12 |
| ZR Tools | 11 |
| WM Ultra Tool Change | 10 |
| WM Ultra Print | 7 |
| Timelapse | 5 |
The categories are created by `scripts/wm_fluidd_categories.py` (installer/panel; it only sorts macros whose Fluidd entry is still the default and records what it handled in the Moonraker database namespace `wm_ultra`). Since F-144 (panel 1.16.2) the sorter writes no aliases: Fluidd shows the real macro names. The per-macro category is listed in MACROS.md (field "Fluidd"). **Note**: the category colours read back from the database are empty (`color: null`) for all 8 categories in the stored category list; the colour rule (same colour inside a category, different between categories) could not be confirmed from this data and should be checked in the Fluidd UI.

## Fluidd features our macros depend on
- **Macro prompts**: `RESPOND TYPE=command MSG="action:prompt_begin|prompt_text|prompt_button|prompt_show|prompt_end|prompt_image"` (windows of calibration, endless spool, unload slot-ready question, tool setter helper). `prompt_image` is our own addition.
- **Macro parameters**: Fluidd's macro buttons with parameter fields for macros that read `params.*` (the first comment lines of a macro describe the parameters).
- **Console**: `RESPOND` messages (echo prefix `echo:` from `[respond]`), `M118`, errors from `action_raise_error`.
- **Outputs card**: `output_pin ACE_Pro`, `ACE_Auto_Load` (virtual pins), `WM_BED_SOAK` pin switch.
- **Runout sensors card**: patched (path_N tangle sensors, filament sensors per head).
- **Update manager**: Fluidd's software-update Update buttons for the installer and the panel run the services `wm-pi-update` / `wm-panel-update`.
- **Camera**: webcam `Camera` (screen board USB camera through crowsnest).

## Patch read line by line (2026-11-19)
Checked against: Fluidd v1.38.0 source (clone of the tag, the 31 patches applied with `git am`, so I read the final files), the installer repo macros and the panel repo `config/`. Files read in full: `zr.ts` (316 lines), `zrMixin.ts` (406), `zrUi.ts` (79), `zrPrintHook.ts` (15), `ZrToolheadsCard.vue` (1695: template, script and the start of the style), `ZrToolDialog.vue` (450: script), `ZrPrintDialog.vue` (889: script), `ZrMappingView.vue` (237: script), and the diffs of `App.vue`, `Dashboard.vue`, `layout/state.ts`, `printer/getters.ts`, `printer/types.ts`, `console/actions.ts`, `console/types.ts`, `ActionCommandPromptDialog.vue`, `RunoutSensorsCard.vue`, `FileSystem.vue`, `PrinterStatusCard.vue`. Not read: the SCSS blocks of the three big components, the two spec files (`zr.spec.ts`, `zrPromptImage.spec.ts`) and the three SVG pictures. 24 files changed, 4320 lines added, 6 removed against v1.38.0.

What the code does, in plain words:
- Everything switches on only when the printer has `filament_switch_sensor docked0` and `filament0` (the Ultra-S sensors). On other printers the card is hidden and the print button works as stock Fluidd.
- Print button (file list and status card) always opens the Choose toolheads window (`zrInterceptPrint`). The window reads the metadata from Moonraker (`preset_colours`, `filament_colors`, `filament_type`, `filament_used_g`, `referenced_tools`), falls back to the last 60000 bytes of the file, suggests the closest loaded toolhead per file colour, and on Print writes `box_modify_t0..t3` and `box_modify_tN_backup` with `SAVE_VARIABLE` (the same variables the T0..T3 macros in change_macros.cfg read), plus `wm_map_file` (file name, quotes and backslashes removed), then starts the print. A mapping per file and named presets are kept in the browser (localStorage, wrapped in try/catch).
- Toolhead card reads: `save_variables` (`current_extruder`, `current_extruder_backup`, `changing_tool`, `box_modify_tN`, `zr_tN_temp/_color/_mat`, `wm_endless*`, `wm_stat_*`, `ace_global_enabled`), `ace_instance_0` (`connection_state`, `slots[].status`, `feed_assist_slot`, `dryer_status`, `temp`, `humidity`, `model`, `firmware`, `usb_port`), `gcode_macro _WM_ACE` (`mode`, `tool`), `gcode_macro _WM_ENDLESS` (`out0..3`, `from`, `to`, `swap_file`), `heater_generic chamber`, `fan_generic air_fan`, `gcode_button Door_button1/2`, `output_pin ACE_Pro / ACE_Auto_Load / Bed_Warp_Stabilisation / Nozzle_Heat_Growth`, the Moonraker power device `chamber_light`, and the file `config/tmt1.ini` and `config/wm_screen_status.json` over the Moonraker file API. It writes `tmt1.ini` (colour and material per slot) with an upload to the `config` root.
- Commands it sends: `_CHANGE_TOOL T=`, `PARK_CURRENT_TOOL` (preceded by `SET_GCODE_OFFSET X=0 Y=0 Z=0`; and `G28` after a "Home first" question), `SET_HEATER_TEMPERATURE`, `ZR_LOAD`/`ZR_UNLOAD` (or `LOAD_FILAMENT`/`UNLOAD_FILAMENT`) without an ACE, `ACE_START_DRYING INSTANCE=0 TEMP= DURATION=`, `ACE_STOP_DRYING INSTANCE=0`, `ACE_WM_AUTO ENABLE=`, `SET_PIN PIN=ACE_Pro|Nozzle_Heat_Growth`, `WM_BED_SOAK ENABLE=`, `WM_ENDLESS_SET ENABLE=|AUTO=|TANGLE=`, `WM_ENDLESS_CONTINUE FROM= TO=`, `WM_ENDLESS_FIXED T=`, `WM_STATS_RESET`, `WM_UNLOAD_MENU`, `ZR_CHAMBER S=`, `SET_FAN_SPEED FAN=air_fan`, and the service restart of `makerbase-client`. Macro and pin existence checked 2026-11-19: all exist (rpi_endless.cfg, rpi_stats.cfg, rpi_ace.cfg, rpi_ace_driver.cfg, rpi_base.cfg, rpi_calibration.cfg, zr_tools.cfg, factory macros.cfg / change_macros.cfg), and `ACE_START_DRYING` / `ACE_STOP_DRYING` are commands registered by `extras/ace/commands.py`.
- Pictures in macro windows: `action:prompt_image name [name ...]` (names must match `[a-z0-9-]`, at most 4) shows `img/wm/<name>.svg`; a missing picture is hidden.

Findings (reported, not fixed):
1. **Wrong text**: `ZrPrintDialog.vue` L396 shows "panel 1.6.0" in the window subtitle, hard-coded. The panel is 1.16.2 (1.16.3 not pushed). Cosmetic, but it tells the user the wrong version.
2. **Dead code**: `ZrToolDialog.vue` still offers a Purge button when a macro `ZR_PURGE` exists. That macro was removed in F-104 (CHANGELOG installer), so the button never shows. No harm. The old `CALIBRATE_TOOL_Z_OFFSET` button is gone from the final file.
3. **Park sends `SET_GCODE_OFFSET X=0 Y=0 Z=0`**: this goes through our SET_GCODE_OFFSET wrapper (rpi_base.cfg) and the live-Z logic (`_WM_LIVEZ_SGO`); whether a Z=0 from the card is counted as a live Z change was not checked in a test.
4. **Print mapping writes 8 `SAVE_VARIABLE` lines per print** (box_modify_t0..3 and the backups) plus `wm_map_file`: nine writes of saved_variables.cfg in one script. Works, a little slow; an interrupted script could leave a half-written map (not seen).
5. **Mapping uses tool numbers 0..3 only**: a file colour with tool number 4 or more is ignored (`c.tool < ZR_HEADS`). Files with more than 4 colours print the extra ones unmapped.
6. **Mapping exposure** (same as the `T0` remark in MACROS.md): the card changes `box_modify_tN` freely, so any macro that calls `T0` instead of `_CHANGE_TOOL T=0` can pick another head after a print with a changed map; the saved values at the last check were the identity.
7. **Dry presets are in the browser code** (PLA 45 C 4 h, PETG 55 C 6 h, ABS/ASA 65 C 6 h, TPU 50 C 6 h, PA 65 C 8 h, PVA 45 C 6 h); the ACE driver limits them itself (heater max 65 C per the comment); `ZrPrintDialog` uses a second list (`zrUi.ts`) with different hours for PETG and others (card: PETG 6 h; zrUi: 360 min = 6 h, equal) - the two lists agree today, but they are two copies.
8. **Comment names differ from the files**: `zrMixin.ts` and `zr.ts` mention `wm_endless.cfg`, `rpi_bed_soak.cfg`, `rpi_zoffset.cfg`; the real files are `rpi_endless.cfg`, `rpi_base.cfg`, `rpi_calibration.cfg`. Comments only.
9. **Fluidd 1.38.0 only**: I did not check for a newer Fluidd release or for removed or deprecated Fluidd APIs in this pass (the patch applies cleanly to the v1.38.0 tag, which is the only check done, 2026-11-19).
10. **Not run here**: the spec tests (`zr.spec.ts`, `zrPromptImage.spec.ts`) and a build were not run in this pass; the zip in the panel repo was not rebuilt.

## Problems / things to re-check
1. When Fluidd is updated upstream, the patch (8158 lines, 11 core files) has to be rebased; the build is pinned to v1.38.0.
2. `config.json` `blacklist` is stock (fluidd.xyz); nothing custom there.
3. Category colours not confirmed (see above).
4. The KlipperScreen "Updating" page closes by itself since F-151 (installer 2.21.1, built; not pushed, not tested after the Fluidd Update).

## Change log
- 2026-11-19: patch read line by line (final files of the 31 patches); section "Patch read line by line" added; backup FLUIDD.md.bak-2026-11-19-before-patch-read.
- 2026-11-18: document created (read-only).

## Purge dialog (F-156, 2026-11-19, dev Pi only, not in the patch yet)
New ZrPurgeDialog.vue and an orange PURGE button next to UNLOAD MENU in the Toolheads card (needs the macro _WM_PURGE). Dialog: toolhead, temperature, speed, amount; Start purge keeps the tool hot at the wipe position, Cancel wipes, cools with the part fan and parks (_WM_PURGE_DONE). The macro list also has WM_PURGE_MENU (prompt window). Checked against the live card, 2026-11-19.

- 2026-11-19 (F-161, pi400 only): ZrToolheadsCard.vue watches _WM_PURGE_SEL.show; WM_PURGE_MENU from the macro list opens ZrPurgeDialog (build v11). Works only while the Dashboard is open, else the macro shows the prompt window after 2 s. Backups FLUIDD.md.bak-2026-11-19-purgemenu.
- 2026-11-19 (F-166, pi400 only): ZrToolheadsCard.vue: Unload Menu enabled while paused, new Load Menu and Resume tool buttons (build v12, zrMixin.ts zrPrinting/zrPaused). Backups FLUIDD.md.bak-2026-11-19-f166.
- 2026-11-19 F-167: ZrToolheadsCard.vue/zrMixin.ts call _WM_ENDLESS_*, _WM_STATS_RESET (build v13).
- 2026-11-19 F-167 part 2: Fluidd build v14 calls the renamed _ZR_*, _ACE_WM_* macros; AcePro category created on pi400.
- 2026-11-19 F-168: ActionCommandPromptDialog.vue window width 640, button text wraps (build v15).
- 2026-11-19 T-001: Fluidd folder on main RPi4 replaced by the pi400 build (new macro names).
- 2026-11-19 F-180: Fluidd macro categories database (fluidd/macros) on main RPi4 replaced by the pi400 list (ids mapped by name). Checked against the live database, 2026-11-19.
- 2026-11-20 F-203 (pi400 only, not tested): Dashboard-Bl-QdHqC.js: purge dialog (`blocked`, `blockedText`) and the Purge button in the Toolheads card use print_stats.state === "printing" instead of zrBusy (printing or paused), text "Pause the print first, then purge". Edited in the built file (no source rebuild), backup printer_data/config/backup/Dashboard-Bl-QdHqC.js.*-before-pausepurge on pi400, md5 328f05ec. Checked against the live file, 2026-11-20.
- 2026-11-20 F-204 (pi400 only): the Resume tool window in Fluidd is a prompt window made by macros (_WM_RTOOL_SHOW1/2); a third window _WM_RTOOL_CONFIRM now asks for the confirmation. No Fluidd file changed. See MACROS.md F-204.
