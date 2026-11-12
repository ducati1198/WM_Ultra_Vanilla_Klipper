# WonderMaker add-on: three behaviours of the factory Klipper, done on top of upstream Klipper
# without editing any upstream file.
#
#  1. grip_check: a G0/G1 move with a positive E value is refused when the active tool is not
#     the gripped one (saved variable current_extruder) or the hall sensor reading (custom_hall)
#     is outside 3000..4700. Outside a print it is an error. During a print or pause it only
#     prints a message (at most every 5 s) and the move continues, as the factory does.
#     Saved variable if_check_extruder_status = 0 switches the check off (tool change macros).
#  2. cold_extrude_switch: with if_check_extruder_status = 0 the "Extrude below minimum temp"
#     check is skipped (used by the extruderN.cfg insert_gcode).
#  3. restore_keeps_offsets: RESTORE_GCODE_STATE does not restore the G-code offsets
#     (SET_GCODE_OFFSET / G92 base position). A tool change saves the state, changes the
#     offsets for the new tool, then restores the state; the new offsets must stay.
#
# This file may be distributed under the terms of the GNU GPLv3 license.
import logging

HALL_MIN = 3000
HALL_MAX = 4700
MSG = "Current nozzle not gripped, unable to extrude."
MSG_INTERVAL = 5.


class WMGcodeCompat:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.reactor = self.printer.get_reactor()
        self.grip_check = config.getboolean('grip_check', True)
        self.cold_extrude_switch = config.getboolean('cold_extrude_switch', True)
        self.restore_keeps_offsets = config.getboolean('restore_keeps_offsets', True)
        self.gm = self.printer.load_object(config, 'gcode_move')
        self.hall = None
        if self.grip_check:
            self.hall = self.printer.load_object(config, 'custom_hall')
        self.save_vars = None
        self.last_msg = -MSG_INTERVAL
        gcode = self.printer.lookup_object('gcode')
        if self.grip_check:
            for cmd in ('G1', 'G0'):
                gcode.register_command(cmd, None)
                gcode.register_command(cmd, self.cmd_G1)
        if self.restore_keeps_offsets:
            gcode.register_command('RESTORE_GCODE_STATE', None)
            gcode.register_command(
                'RESTORE_GCODE_STATE', self.cmd_RESTORE_GCODE_STATE,
                desc=self.gm.cmd_RESTORE_GCODE_STATE_help)
        if self.cold_extrude_switch:
            self.printer.register_event_handler("klippy:connect",
                                                self._handle_connect)

    def _vars(self):
        if self.save_vars is None:
            sv = self.printer.lookup_object('save_variables', None)
            if sv is None:
                return {}
            self.save_vars = sv
        return self.save_vars.allVariables

    # -- grip check
    def cmd_G1(self, gcmd):
        self._check_grip(gcmd)
        self.gm.cmd_G1(gcmd)

    def _check_grip(self, gcmd):
        e = gcmd.get_command_parameters().get('E')
        if e is None:
            return
        try:
            v = float(e) * self.gm.extrude_factor
        except ValueError:
            return
        if v <= 0.:
            return
        svars = self._vars()
        if svars.get('if_check_extruder_status', 1) != 1:
            return
        toolhead = self.printer.lookup_object('toolhead')
        name = toolhead.get_extruder().get_name()
        idx = 0
        if name.startswith('extruder') and name[8:].isdigit():
            idx = int(name[8:])
        raw = self.hall.last_adc_value_raw
        if (idx == int(svars.get('current_extruder', 0))
                and HALL_MIN <= raw <= HALL_MAX):
            return
        eventtime = self.reactor.monotonic()
        ps = self.printer.lookup_object('print_stats', None)
        state = ps.get_status(eventtime)['state'] if ps is not None else ''
        if state in ('printing', 'paused'):
            if eventtime - self.last_msg >= MSG_INTERVAL:
                self.last_msg = eventtime
                gcmd.respond_info(MSG)
            return
        raise gcmd.error(MSG)

    # -- RESTORE_GCODE_STATE without the offsets
    def cmd_RESTORE_GCODE_STATE(self, gcmd):
        gm = self.gm
        name = gcmd.get('NAME', 'default')
        state = gm.saved_states.get(name)
        if state is None:
            gm.cmd_RESTORE_GCODE_STATE(gcmd)    # raises the usual error
            return
        tmp = dict(state)
        tmp['base_position'] = list(gm.base_position)
        tmp['homing_position'] = list(gm.homing_position)
        gm.saved_states[name] = tmp
        try:
            gm.cmd_RESTORE_GCODE_STATE(gcmd)
        finally:
            gm.saved_states[name] = state

    # -- cold extrude switch
    def _handle_connect(self):
        for name, ext in self.printer.lookup_objects('extruder'):
            if hasattr(ext, 'check_move') and hasattr(ext, 'heater'):
                self._wrap_extruder(ext)

    def _wrap_extruder(self, ext):
        orig = ext.check_move
        def check_move(move, *args):
            if self._vars().get('if_check_extruder_status', 1) == 0:
                heater = ext.heater
                saved = heater.can_extrude
                heater.can_extrude = True
                try:
                    return orig(move, *args)
                finally:
                    heater.can_extrude = saved
            return orig(move, *args)
        ext.check_move = check_move


def load_config(config):
    return WMGcodeCompat(config)
