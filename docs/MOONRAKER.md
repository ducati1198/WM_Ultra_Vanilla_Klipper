# MOONRAKER.md - Moonraker on the WonderMaker Ultra Pi

Written 2026-11-18 from `~/printer_data/config/moonraker.conf` (read line by line), the running service and the Moonraker docs of the installed version (`05-notes/reference/moonraker-docs-0.11.0+/docs/`, online https://moonraker.readthedocs.io/). Nothing on the printer was changed.

## Version and where it lives
- Moonraker: source in `~/moonraker` (no `.git` folder, so `git describe` is not possible); docs changelog says "after 0.11.0 (2026-08-25), Unreleased"; **API version 1.5.0** (`server.py`, `/server/info`). Virtualenv `~/moonraker-env` (tornado 6.5.8). Config `~/printer_data/config/moonraker.conf`, logs `~/printer_data/logs/moonraker.log`.
- Klippy connection: `klippy_uds_address: ~/printer_data/comms/klippy.sock`. Port 7125 (HTTP + websocket), Fluidd on port 80 (nginx forwards the Moonraker API to port 7125; the installer doctor checks it).
- Database namespaces now present: `fluidd`, `moonraker`, `update_manager`, `announcements`, `gcode_metadata`, `lane_data` (ACE slot data for Orca), `wm_ultra` (our category bookkeeping).

## Sections of moonraker.conf (checked against configuration.md of the installed docs, 2026-11-18)
| Section | Our settings | Checked |
|---|---|---|
| `[server]` | host 0.0.0.0, port 7125, klippy_uds_address | ok |
| `[authorization]` | `trusted_clients`: 10/8, 127/8, 169.254/16, 172.16/12, 192.168/16, FE80::/10, ::1; `cors_domains`: *.lan, *.local, localhost, my.mainsail.xyz, app.fluidd.xyz | ok; note: whole private ranges are trusted, so anyone on the LAN can use the printer without login |
| `[database]`, `[secrets]`, `[octoprint_compat]`, `[history]` | defaults | ok |
| `[file_manager]` | queue_gcode_uploads False, enable_object_processing True | ok |
| `[machine]` | provider systemd_dbus, validate_service False, validate_config False | ok (the two validate options exist; they hide the "services not allowed" warnings) |
| `[data_store]` | gcode_store_size 5000 (console history lines) | ok |
| `[update_manager]` | enable_auto_refresh True | ok |
| `[update_manager timelapse]` | git_repo ~/moonraker-timelapse, managed_services klipper moonraker | ok |
| `[update_manager WM_Ultra_Vanilla_Klipper]` | git_repo ~/WM_Ultra_Vanilla_Klipper (ducati1198), is_system_service False, info_tags desc=... | ok. **Custom**: the Update button also applies the update through the service `wm-pi-update` (log `~/wm-pi-update.log`) |
| `[update_manager wm-ultra-fluidd-acepro-panel]` | git_repo ~/wm-ultra-fluidd-acepro-panel, managed_services klipper | ok. **Custom**: service `wm-panel-update` applies the update |
| `[timelapse]` | output_path, frame_path, camera default, parkpos back_right, park speeds, `extraoutputparams: -preset superfast` | options belong to the third-party component moonraker-timelapse (its own docs), not to Moonraker's configuration.md: not verified here |
| `[webcam Camera]` | service mjpegstreamer, stream_url /webcam/?action=stream, snapshot_url ...action=snapshot | ok (MJPEG-Streamer is a documented service) |
| `[power chamber_light]` | type http to the screen board (http://<screen-board-ip>:8765/light), request/response templates, poll_interval 3 | ok; written by `scripts/wm_light_conf.py` of the installer |

Hidden file `.moonraker.conf.bkp` exists (Moonraker's own backup of the file).

## Moonraker APIs our code uses
| Caller | Call | Used for |
|---|---|---|
| Installer (`installer.sh`, scripts) | `GET /printer/objects/query`, `/printer/info`, `/server/info`, `/server/gcode_store`, `/machine/update/status|refresh|client`, `/machine/services/restart`, `POST /printer/gcode/script`, `/printer/firmware_restart`, `/server/files/upload` (screen board uploads), `/server/files/config/tmt...`, `/server/database/item` | state checks, update, restarts, ids of CAN boards, Extruder Setup, light announcement |
| Panel category sorter `scripts/wm_fluidd_categories.py` | `GET/POST /server/database/item` namespace `fluidd` key `macros`; own key `wm_ultra` / `fluidd_categories` | puts macros into Fluidd categories; remembers which macros it already sorted |
| ACE driver `extras/ace/moonraker_lane_sync.py` | writes Moonraker database namespace `lane_data` | slots (material, colour) for OrcaSlicer filament sync |
| Macros (Klipper side) | `action_call_remote_method("set_device_power", device="chamber_light", state=...)` in `WM_CHAMBER_LIGHT`; timelapse macros call `timelapse_newframe`, `timelapse_render` via `action_call_remote_method` | chamber light, timelapse |
| Screen board (KlipperScreen patches, `zr_tools`) | Moonraker websocket and `machine.device_power.post_device` | Light buttons, status pages |
| Fluidd patched build | Moonraker websocket subscriptions: `ace_instance_0`, `filament_switch_sensor path_N` / `filament<N>`, `save_variables`, `print_stats`, `gcode_macro *`; file metadata `/server/files/metadata` | Toolheads card, Choose toolheads window |
| OrcaSlicer plugin `orca_plugin/spool_toolhead_mapper.py` | `/server/files/list`, `/server/files/metadata`, `/printer/objects/query` | spool to toolhead mapping before print |

## Custom things
- Two extra `update_manager` entries (installer and panel) that really install on Update (services `wm-pi-update`, `wm-panel-update`).
- `wm-light.path` / `wm-light.service` (installer) set the chamber light up when the screen board announces it. **F-155 (2026-11-18)**: this service restarted Klipper every time; it now restarts only when the light macro changed and never while Klipper is busy.
- Power device `chamber_light` is an HTTP device on the screen board, not a GPIO.

## Problems / things to re-check
1. `trusted_clients` trusts all private ranges (convenient, but no login on the LAN).
2. `validate_service: False` / `validate_config: False` hide Moonraker's own warnings about unmanaged services.
3. The Moonraker folder has no `.git`: `[update_manager moonraker]` is absent, so Moonraker itself is never updated through Fluidd (how Moonraker itself is updated is not recorded in this repository).
4. The `[timelapse]` options could not be checked against Moonraker's docs (third-party component).

## Change log
- 2026-11-18: document created (read-only). No change on the printer.
