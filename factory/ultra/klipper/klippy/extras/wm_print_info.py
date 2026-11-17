# WonderMaker add-on: WM_PRINT_INFO_READ reads the end of the G-code file that is printing and keeps
# which slicer tools the print uses and their first layer nozzle temperatures, so the print start can
# purge every used toolhead (_WM_START_PURGE in rpi_base.cfg).
#
#   WM_PRINT_INFO_READ [FILE=<name in the gcodes folder>]
#
# Only the last 512 KB of the file are read: OrcaSlicer, PrusaSlicer and Bambu Studio write their
# "; filament used [mm] = a, b, c, d" line and their settings there. A tool with more than 0 mm of
# filament is a used tool. Nothing found (another slicer, a file without these lines): found is False and
# the print start purges the first tool only, as before.
#
# Status (printer.wm_print_info): found (bool), tools (list of used slicer tools 0-3), temps (first layer
# nozzle temperature of every slicer tool, 0 when unknown), file (file name).
# This file may be distributed under the terms of the GNU GPLv3 license.
import logging
import os

TAIL_BYTES = 512 * 1024
MAX_TOOLS = 4
TEMP_KEYS = ("nozzle_temperature_initial_layer", "first_layer_temperature",
             "nozzle_temperature", "temperature")


def _numbers(text):
    out = []
    for part in text.replace(";", ",").split(","):
        try:
            out.append(float(part.strip()))
        except ValueError:
            out.append(0.)
    return out


def parse_tail(text):
    """(used tools, temps) from the end of a G-code file; used is None when the file has no usage line."""
    used = None
    found = {}
    for line in text.splitlines():
        if not line.startswith(";"):
            continue
        key, sep, val = line[1:].partition("=")
        if not sep:
            continue
        key = key.strip()
        if key == "filament used [mm]":
            used = _numbers(val)
        elif key in TEMP_KEYS and key not in found:
            found[key] = _numbers(val)
    temps = []
    for key in TEMP_KEYS:
        if key in found and any(t > 0 for t in found[key]):
            temps = found[key]
            break
    if used is None:
        return None, []
    tools = [i for i, mm in enumerate(used) if mm > 0. and i < MAX_TOOLS]
    temps = [int(round(t)) for t in temps[:MAX_TOOLS]]
    temps += [0] * (MAX_TOOLS - len(temps))
    return tools, temps


class WMPrintInfo:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.found = False
        self.tools = []
        self.temps = [0] * MAX_TOOLS
        self.file = ""
        gcode = self.printer.lookup_object('gcode')
        gcode.register_command('WM_PRINT_INFO_READ', self.cmd_WM_PRINT_INFO_READ,
                               desc=self.cmd_WM_PRINT_INFO_READ_help)

    cmd_WM_PRINT_INFO_READ_help = "Read which tools the printing G-code file uses and their first layer temperatures [FILE=]"

    def get_status(self, eventtime):
        return {'found': self.found, 'tools': list(self.tools),
                'temps': list(self.temps), 'file': self.file}

    def _path(self, gcmd):
        sd = self.printer.lookup_object('virtual_sdcard', None)
        name = gcmd.get('FILE', None)
        if name is None:
            return sd.file_path() if sd is not None else None
        if os.path.isabs(name) or sd is None:
            return name
        return os.path.join(sd.sdcard_dirname, name.lstrip("/"))

    def cmd_WM_PRINT_INFO_READ(self, gcmd):
        self.found, self.tools, self.temps, self.file = False, [], [0] * MAX_TOOLS, ""
        path = self._path(gcmd)
        if not path or not os.path.isfile(path):
            gcmd.respond_info("Print info: no G-code file to read")
            return
        self.file = os.path.basename(path)
        try:
            size = os.path.getsize(path)
            with open(path, 'rb') as f:
                f.seek(max(0, size - TAIL_BYTES))
                text = f.read().decode('utf-8', 'replace')
        except Exception as e:
            logging.exception("wm_print_info: read failed")
            gcmd.respond_info("Print info: could not read %s (%s)" % (self.file, e))
            return
        tools, temps = parse_tail(text)
        if tools is None:
            gcmd.respond_info("Print info: %s has no 'filament used' line, only the first tool is purged" % (self.file,))
            return
        self.found, self.tools, self.temps = True, tools, temps
        gcmd.respond_info("Print info: %s uses %s, first layer %s C" % (
            self.file, ", ".join("T%d" % t for t in tools) or "no tool",
            ", ".join("%d" % temps[t] for t in tools) or "-"))


def load_config(config):
    return WMPrintInfo(config)
