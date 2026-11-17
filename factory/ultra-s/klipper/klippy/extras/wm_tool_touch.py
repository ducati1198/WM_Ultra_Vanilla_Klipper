# wm_tool_touch.py  -  one touch of the tool setter with a travel limit (WonderMaker ZR Ultra, Pi installer)
#
# [wm_tool_touch]   (no options; needs WonderMaker's [tools_calibrate])
#
# TOOL_CALIBRATE_TOUCH DIRECTION=x+|x-|y+|y-|z- [MAX=5] [NAME=<key>] [OPTIONAL=1] [SAMPLES=n] [SAMPLES_TOLERANCE=mm]
#                      [SAMPLES_TOLERANCE_RETRIES=n] [ACCEL=14] [SETTLE=0.6]
#   One touch from where the nozzle stands, MAX mm of travel at most (40 at most), z- at half speed. The nozzle goes back to
#   where it started. The result is printer.wm_tool_touch.touch[NAME] = {found, x, y, z, direction}. Nothing is saved.
#   OPTIONAL=1: "no touch within MAX" and "the touches did not agree" are a result (found False), not an error.
#   Every touch runs with a low acceleration (ACCEL) after a short rest (SETTLE), and the old acceleration is put back
#   afterwards. A result less than 0.3 mm from the start is a false touch and is repeated (5 times at most): the load cell
#   of the tool setter sometimes trips without contact.
#
# Used by the tool setter position helper (rpi-cfg/rpi_calibration.cfg, WM_SETTER_PROBE_POSITION). WonderMaker's own
# tools_calibrate driver is not changed: this module only calls its run_probe.
#
# This file may be distributed under the terms of the GNU GPLv3 license.

DIRECTIONS = {'x+': 0, 'x-': 0, 'y+': 1, 'y-': 1, 'z-': 2}


class WmToolTouch:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.gcode = self.printer.lookup_object('gcode')
        self.touch = {}
        self.gcode.register_command('TOOL_CALIBRATE_TOUCH', self.cmd_TOOL_CALIBRATE_TOUCH,
                                    desc=self.cmd_TOOL_CALIBRATE_TOUCH_help)

    def _note(self, name, direction, pos=None):
        touch = dict(self.touch)   # a new dict every time, so the status readers see the change
        if pos is None:
            touch[name] = {'found': False, 'x': 0., 'y': 0., 'z': 0., 'direction': direction}
        else:
            touch[name] = {'found': True, 'x': pos[0], 'y': pos[1], 'z': pos[2], 'direction': direction}
        self.touch = touch

    def _accel(self, value):
        self.gcode.run_script_from_command("SET_VELOCITY_LIMIT ACCEL=%.1f" % (value,))

    def _collision_off(self):
        coll = self.printer.lookup_object('collision_detect', None)
        if coll is not None:
            try:
                coll.cmd_disable()
            except Exception:
                pass

    cmd_TOOL_CALIBRATE_TOUCH_help = ("WonderMaker: one touch from where the nozzle stands. DIRECTION=x+ x- y+ y- or z-, "
                                     "MAX=mm of travel at most (40 at most), NAME=key of the result, OPTIONAL=1: no touch "
                                     "is not an error. The nozzle goes back to where it started. Nothing is saved.")

    def cmd_TOOL_CALIBRATE_TOUCH(self, gcmd):
        direction = gcmd.get("DIRECTION", "").lower()
        if direction not in DIRECTIONS:
            raise gcmd.error("TOOL_CALIBRATE_TOUCH: DIRECTION must be x+, x-, y+, y- or z-")
        calibrate = self.printer.lookup_object('tools_calibrate', None)
        if calibrate is None or not hasattr(calibrate, 'probe_multi_axis'):
            raise gcmd.error("TOOL_CALIBRATE_TOUCH needs WonderMaker's [tools_calibrate]")
        probe = calibrate.probe_multi_axis
        max_distance = gcmd.get_float("MAX", 5., above=0., maxval=40.)
        name = gcmd.get("NAME", direction)
        optional = gcmd.get_int("OPTIONAL", 0)
        accel = gcmd.get_float("ACCEL", 14., above=0.)
        settle = gcmd.get_float("SETTLE", 0.6, minval=0., maxval=5.)
        axis = DIRECTIONS[direction]
        toolhead = self.printer.lookup_object('toolhead')
        lift_speed = calibrate.lift_speed
        start = list(toolhead.get_position())[:3]
        self._note(name, direction)
        prev_accel = toolhead.max_accel
        self._accel(accel)
        try:
            pos = None
            for _ in range(5):
                toolhead.dwell(settle)
                pos = probe.run_probe(direction, gcmd, speed_ratio=(0.5 if direction == 'z-' else 1.0),
                                      samples=1, max_distance=max_distance)
                if abs(pos[axis] - start[axis]) >= 0.3:
                    break
                gcmd.respond_info("Touch %s (%s): the sensor tripped before the nozzle moved, again" % (name, direction))
                toolhead.manual_move(start, lift_speed)
                toolhead.dwell(1.0)
                pos = None
            if pos is None:
                raise self.printer.command_error("Probe samples exceed samples_tolerance (the sensor trips without a touch)")
        except self.printer.command_error as e:
            self._accel(prev_accel)
            try:
                probe.mcu_probe[axis].multi_probe_end()
            except Exception:
                pass
            reason = str(e)
            if optional and not self.printer.is_shutdown() and ("No trigger" in reason or "samples_tolerance" in reason):
                toolhead.manual_move(start, lift_speed)
                if "No trigger" in reason:
                    gcmd.respond_info("Touch %s (%s): no touch within %.2f mm" % (name, direction, max_distance))
                else:
                    gcmd.respond_info("Touch %s (%s): the touches did not agree, not used" % (name, direction))
                return
            self._collision_off()
            raise
        except Exception:
            self._accel(prev_accel)
            self._collision_off()
            raise
        toolhead.manual_move(start, lift_speed)
        self._accel(prev_accel)
        self._note(name, direction, pos)
        gcmd.respond_info("Touch %s (%s) at %.4f, %.4f, %.4f" % (name, direction, pos[0], pos[1], pos[2]))

    def get_status(self, eventtime):
        return {'touch': self.touch}


def load_config(config):
    return WmToolTouch(config)
