# WonderMaker "echelon" transfer stepper, ported to the upstream Klipper motion system
# (motion_queuing, stepper.LookupRail). Based on upstream manual_stepper.py plus the WonderMaker
# commands. The ECHELON_* commands used by the printer configs are kept:
#   ECHELON_STEPPER, ECHELON_STEPPER_HOMING, ECHELON_STEPPER_DISABLE, ECHELON_SP, ECHELON_QUERY,
#   ECHELON_INVERT, ECH_SYNC_EXTRUDER_MOTION
# Dropped (not used by any config, they depended on factory-only stepper.py additions):
#   ECHELON_STEPPER_INVERT_DIR, ECHELON_PRINT_DIR
#
# This file may be distributed under the terms of the GNU GPLv3 license.
import logging
import stepper
from . import force_move
from kinematics import extruder


class EchelonStepper:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.name = config.get_name()
        stepper_name = self.name.split()[-1]
        self.reactor = self.printer.get_reactor()
        self.can_home = True
        self.rail = stepper.LookupRail(
            config, need_position_minmax=False, default_position_endstop=0.)
        self.steppers = self.rail.get_steppers()
        self.velocity = config.getfloat('velocity', 5., above=0.)
        self.accel = self.homing_accel = config.getfloat('accel', 0., minval=0.)
        self.next_cmd_time = 0.
        self.commanded_pos = 0.
        self.motion_queue = None
        # Setup iterative solver
        self.motion_queuing = self.printer.load_object(config, 'motion_queuing')
        self.trapq = self.motion_queuing.allocate_trapq()
        self.trapq_append = self.motion_queuing.lookup_trapq_append()
        self.rail.setup_itersolve('cartesian_stepper_alloc', b'x')
        self.rail.set_trapq(self.trapq)
        # Register commands
        self.gcode = gcode = self.printer.lookup_object('gcode')
        for cmd, func in (
                ('ECHELON_SP', self.cmd_ECHELON_SP),
                ('ECHELON_QUERY', self.cmd_ECHELON_STEPPER_QUERY),
                ('ECHELON_STEPPER', self.cmd_ECHELON_STEPPER),
                ('ECHELON_STEPPER_HOMING', self.cmd_ECHELON_STEPPER_HOMING),
                ('ECHELON_INVERT', self.cmd_ECHELON_ENDSTOP_INVERT),
                ('ECHELON_STEPPER_DISABLE', self.cmd_ECHELON_STEPPER_DISABLE)):
            gcode.register_mux_command(cmd, "STEPPER", stepper_name, func)
        gcode.register_mux_command(
            "ECH_SYNC_EXTRUDER_MOTION", "STEPPER", stepper_name,
            self.cmd_ECH_SYNC_EXTRUDER_MOTION,
            desc=self.cmd_ECH_SYNC_EXTRUDER_MOTION_help)

    def get_name(self):
        return self.name

    def sync_print_time(self):
        toolhead = self.printer.lookup_object('toolhead')
        print_time = toolhead.get_last_move_time()
        if self.next_cmd_time > print_time:
            toolhead.dwell(self.next_cmd_time - print_time)
        else:
            self.next_cmd_time = print_time

    def do_enable(self, enable):
        stepper_names = [s.get_name() for s in self.steppers]
        stepper_enable = self.printer.lookup_object('stepper_enable')
        stepper_enable.set_motors_enable(stepper_names, enable)

    def do_set_position(self, setpos):
        toolhead = self.printer.lookup_object('toolhead')
        toolhead.flush_step_generation()
        self.commanded_pos = setpos
        self.rail.set_position([self.commanded_pos, 0., 0.])

    def _submit_move(self, movetime, movepos, speed, accel):
        cp = self.commanded_pos
        dist = movepos - cp
        axis_r, accel_t, cruise_t, cruise_v = force_move.calc_move_time(
            dist, speed, accel)
        self.trapq_append(self.trapq, movetime,
                          accel_t, cruise_t, accel_t,
                          cp, 0., 0., axis_r, 0., 0.,
                          0., cruise_v, accel)
        self.commanded_pos = movepos
        return movetime + accel_t + cruise_t + accel_t

    def do_move(self, movepos, speed, accel, sync=True):
        self.sync_print_time()
        self.next_cmd_time = self._submit_move(self.next_cmd_time, movepos,
                                               speed, accel)
        self.motion_queuing.note_mcu_movequeue_activity(self.next_cmd_time)
        if sync:
            self.sync_print_time()

    def _query_endstop(self):
        toolhead = self.printer.lookup_object('toolhead')
        print_time = toolhead.get_last_move_time()
        return self.rail.get_endstops()[0][0].query_endstop(print_time)

    def do_homing_move(self, movepos, speed, accel, triggered, check_trigger):
        self.homing_accel = accel
        pos = [movepos, 0., 0., 0.]
        endstops = self.rail.get_endstops()
        phoming = self.printer.lookup_object('homing')
        phoming.manual_home(self, endstops, pos, speed,
                            False, triggered, check_trigger)
        self.sync_print_time()

    def cmd_ECHELON_ENDSTOP_INVERT(self, gcmd):
        mcu_endstop = self.rail.get_endstops()[0][0]
        mcu_endstop._invert = not mcu_endstop._invert

    def cmd_ECHELON_STEPPER_DISABLE(self, gcmd):
        self.sync_print_time()
        self.do_enable(False)

    def cmd_ECHELON_SP(self, gcmd):
        self.do_set_position(0.)

    def cmd_ECHELON_STEPPER_QUERY(self, gcmd):
        gcmd.respond_info("ENDSTOP: %s" % (self._query_endstop(),))

    def cmd_ECHELON_STEPPER(self, gcmd):
        speed = gcmd.get_float('SPEED', self.velocity, above=0.)
        accel = gcmd.get_float('ACCEL', self.accel, minval=0.)
        movepos = gcmd.get_float('MOVE')
        sync = gcmd.get_int('SYNC', 1)
        self.do_move(movepos, speed, accel, bool(sync))

    def cmd_ECHELON_STEPPER_HOMING(self, gcmd):
        speed = gcmd.get_float('SPEED', self.velocity, above=0.)
        accel = gcmd.get_float('ACCEL', self.accel, minval=0.)
        movepos = gcmd.get_float('MOVE')
        post_dist = gcmd.get_float('PDI', 0.0)
        sync = gcmd.get_int('SYNC', 1)
        try:
            self.do_homing_move(movepos, speed, accel, True, True)
        except Exception:
            # Same as the factory: a failed unlock is logged, not fatal
            logging.exception("WARNING: UNLOCK TOOL FAILED")
        self.do_set_position(0.)
        self.do_move(post_dist, speed, accel, bool(sync))

    cmd_ECH_SYNC_EXTRUDER_MOTION_help = "Set extruder stepper motion queue"
    def cmd_ECH_SYNC_EXTRUDER_MOTION(self, gcmd):
        ename = gcmd.get('MOTION_QUEUE')
        self.sync_to_extruder(ename)
        gcmd.respond_info("ECHELON_STEP '%s' now syncing with '%s'"
                          % (self.name, ename))

    def sync_to_extruder(self, extruder_name):
        toolhead = self.printer.lookup_object('toolhead')
        toolhead.flush_step_generation()
        if not extruder_name:
            self.rail.set_trapq(None)
            self.motion_queue = None
            self.motion_queuing.check_step_generation_scan_windows()
            return
        extruder_obj = self.printer.lookup_object(extruder_name, None)
        if extruder_obj is None or not isinstance(
                extruder_obj, extruder.PrinterExtruder):
            raise self.printer.command_error("'%s' is not a valid extruder."
                                             % (extruder_name,))
        self.rail.set_position([extruder_obj.last_position, 0., 0.])
        self.rail.set_trapq(extruder_obj.get_trapq())
        self.motion_queue = extruder_name
        self.motion_queuing.check_step_generation_scan_windows()

    # Toolhead wrappers to support homing
    def flush_step_generation(self):
        toolhead = self.printer.lookup_object('toolhead')
        toolhead.flush_step_generation()

    def get_position(self):
        return [self.commanded_pos, 0., 0., 0.]

    def set_position(self, newpos, homing_axes=""):
        self.do_set_position(newpos[0])

    def get_last_move_time(self):
        self.sync_print_time()
        return self.next_cmd_time

    def dwell(self, delay):
        self.next_cmd_time += max(0., delay)

    def drip_move(self, newpos, speed, drip_completion):
        # Submit move to trapq
        self.sync_print_time()
        start_time = self.next_cmd_time
        end_time = self._submit_move(start_time, newpos[0],
                                     speed, self.homing_accel)
        # Drip updates to motors
        self.motion_queuing.drip_update_time(start_time, end_time,
                                             drip_completion)
        # Clear trapq of any remaining parts of movement
        self.motion_queuing.wipe_trapq(self.trapq)

    def get_kinematics(self):
        return self

    def get_steppers(self):
        return self.steppers

    def calc_position(self, stepper_positions):
        return [stepper_positions[self.rail.get_name()], 0., 0.]


def load_config_prefix(config):
    return EchelonStepper(config)
