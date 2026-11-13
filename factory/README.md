# Files in this repository

For installing without a copy of the files from your own printer. The installer uses the folder of your model.

## Two folders, one per model

| Folder | Printer | Difference |
|---|---|---|
| [`ultra/`](ultra) | WonderMaker ZR Ultra | `printer.cfg` has `# [include zru-s.cfg]` (off) |
| [`ultra-s/`](ultra-s) | WonderMaker ZR Ultra-S | `printer.cfg` includes `zru-s.cfg` (chamber heater, air filter fan, door buttons) |

Both use the same Klipper, Moonraker and MCU files. The settings in `config/` come from a Raspberry Pi that runs this setup on a ZR Ultra-S. The `ultra/` copy has the `zru-s.cfg` include commented out and the Ultra's `tmt1.ini` (`model=1`, no camera, timelapse, air filter or auxiliary fan). The installer asks which printer you have and uses the matching folder.

## What is in each folder

| Item | Files |
|---|---|
| Klipper (upstream, Klipper3d, **v0.13.0-827-g29d4ec2d6**) | [`klipper/`](ultra-s/klipper): browsable source folder with `lib/`, GPL v3 (`COPYING`), plus WonderMaker's modules in `klippy/extras/` (below) and the Pi-side modules `wm_adaptive_mesh`, `wm_mcu_tweaks`, `wm_pin_pulse`, `wm_stepper_diag`, `wm_gcode_compat`, `wm_ready_compat` |
| Moonraker (upstream, Arksine, **v0.11.0-4-gb559b9a**) | [`moonraker/`](ultra-s/moonraker): browsable source folder, GPL v3 (`LICENSE`) |
| Settings | `config/`: `printer.cfg`, macros, extruders, hub, load cell, offset calibration, Moonraker config, `tmt1.ini`, `saved_variables.cfg`, `zru-s.cfg`, `rpi_fan_guard.cfg`, `rpi_chamber_light.json` |
| `printer.cfg` per toolhead count | `config-variants/printer1.cfg` ... `printer4.cfg` (1 to 4 toolheads) |
| WonderMaker's helper scripts | `scripts/` (CAN id tools, restore factory settings, `set_zru_include.sh`, ...) |
| MCU update scripts and firmware | `mcu/*.sh`, `mcu/mcu_info.ini`, the `klipper*.bin` files (never run by the installer) |
| Python environments | not stored (machine-built folders): rebuilt from `config/klippy-requirements.txt` and `config/moonraker-requirements.txt` |
| Checksums | `SHA256SUMS` (klipper and moonraker folders), `modules.sha256` (compiled modules), `mcu/binaries.sha256` (MCU firmware and flasher) |

The Klipper and Moonraker folders are source copies without git history. They are not git clones on the Pi, so Fluidd's update button does not update them: a new version arrives with a new version of this repository (`./installer.sh --get-latest && ./installer.sh --update`).

## What is not shipped

No bed mesh, PID results, input shaper, probe offset or tool offsets: a new install starts clean (`z_offset:0`, tool offsets 0, an empty `SAVE_CONFIG` block). CAN ids: main board, hub and extruder board have placeholders (`000000000000`, `000000000001`, `000000000002`); T0 to T3 and the load cell are empty and filled by the installer. The ACE Pro driver and its configs come from the `wm-ultra-fluidd-acepro-panel` project when you ask for it.

## Binary files from WonderMaker (included at the repository owner's request)

| Item | Where | Note |
|---|---|---|
| The 5 compiled Python modules: `cs1237`, `hx711`, `heater_air_core`, `heater_feng`, `xy_offset_calibrator_core` | `<model>/klipper/klippy/extras/` | WonderMaker's binaries, copied unchanged from a ZR Ultra-S. **No source and no license to redistribute are published by WonderMaker.** They stay WonderMaker's property |
| MCU firmware `klipper*.bin` and the `hid-flash` tool | `<model>/mcu/` | Never used or run by the installer, which never flashes anything. Upstream Klipper prints "deprecated code" warnings for this firmware; they are harmless |

Not included: WonderMaker's touchscreen app and its encrypted update package, and your own calibration, saved variables and logs.

**Takedown:** if WonderMaker or any rights holder asks, these binaries will be removed. Their checksums stay in `modules.sha256` and `mcu/binaries.sha256`, so you can still verify files taken from your own printer.

WonderMaker's official firmware download: https://wondermaker3d.gitbook.io/wondermaker3d/printer-series/zr-ultra/documentation-package/firmware-file-download

## Verify

```
cd factory/<model> && sha256sum -c SHA256SUMS
cd factory/<model>/klipper && sha256sum -c ../modules.sha256
```
