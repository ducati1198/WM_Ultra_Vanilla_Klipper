# WonderMaker STEPPER_DIAG_ENABLE / STEPPER_DIAG_DISABLE as a stand-alone module for upstream Klipper.
# The factory added these two commands to tmc.py: they switch a TMC2209 into the sensorless (StallGuard)
# state before a homing move and restore the normal settings afterwards.
#   STEPPER_DIAG_ENABLE  CHIP=stepper_z
#   STEPPER_DIAG_DISABLE CHIP=stepper_z
# Config: add an empty section   [wm_stepper_diag]
# Supports tmc2209 drivers (the only type the printer uses).
#
# This file may be distributed under the terms of the GNU GPLv3 license.
import logging

FORCED_TPWMTHRS = 0x0003f
FORCED_TCOOLTHRS = 0xfffff


class _Diag:
    def __init__(self, name, drv):
        self.name = name
        self.fields = drv.fields
        self.mcu_tmc = drv.mcu_tmc
        self.pwmthrs = self.coolthrs = self.thigh = 0
        self.en_pwm = False
        self.active = False

    def enable(self, gcmd):
        f, m = self.fields, self.mcu_tmc
        if self.active:
            # already enabled: do not overwrite the saved normal values
            return
        logging.info("wm_stepper_diag enable %s", self.name)
        self.pwmthrs = f.get_field("tpwmthrs")
        self.en_pwm = not f.get_field("en_spreadcycle")
        self.coolthrs = f.get_field("tcoolthrs")
        f.set_field("tpwmthrs", 0)
        m.set_register("TPWMTHRS", f.set_field("tpwmthrs", 0))
        m.set_register("GCONF", f.set_field("en_spreadcycle", 0))
        if f.lookup_register("thigh", None) is not None:
            self.thigh = f.get_field("thigh")
            m.set_register("THIGH", f.set_field("thigh", 0))
        # factory values for sensorless homing
        m.set_register("TPWMTHRS", f.set_field("tpwmthrs", FORCED_TPWMTHRS))
        m.set_register("TCOOLTHRS", f.set_field("tcoolthrs", FORCED_TCOOLTHRS))
        self.active = True

    def disable(self, gcmd):
        f, m = self.fields, self.mcu_tmc
        logging.info("wm_stepper_diag disable %s", self.name)
        if not self.active:
            return
        m.set_register("TPWMTHRS", f.set_field("tpwmthrs", self.pwmthrs))
        m.set_register("GCONF",
                       f.set_field("en_spreadcycle", not self.en_pwm))
        m.set_register("TCOOLTHRS", f.set_field("tcoolthrs", self.coolthrs))
        if f.lookup_register("thigh", None) is not None:
            m.set_register("THIGH", f.set_field("thigh", self.thigh))
        self.active = False


class WMStepperDiag:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.printer.register_event_handler("klippy:connect",
                                            self._handle_connect)

    def _handle_connect(self):
        gcode = self.printer.lookup_object('gcode')
        for objname, drv in self.printer.lookup_objects(module='tmc2209'):
            name = objname.split()[-1]
            d = _Diag(name, drv)
            gcode.register_mux_command("STEPPER_DIAG_ENABLE", "CHIP", name,
                                       d.enable, desc="Sensorless homing on")
            gcode.register_mux_command("STEPPER_DIAG_DISABLE", "CHIP", name,
                                       d.disable, desc="Sensorless homing off")


def load_config(config):
    return WMStepperDiag(config)
