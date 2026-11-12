# WonderMaker add-on: WM_PIN_PULSE, a short pulse on an [output_pin] that is shorter than
# upstream SET_PIN can make. Upstream SET_PIN spaces two changes of the same pin at least
# 100 ms apart, so SET_PIN 0 / G4 P22 / SET_PIN 1 (the factory 22 ms LEVELING pulse)
# becomes a pulse of 100 ms or more. This command schedules both edges itself.
#
#   WM_PIN_PULSE PIN=LEVELING [WIDTH=0.022] [VALUE=0]
#
# The pin goes to VALUE for WIDTH seconds (default VALUE 0, WIDTH 0.022), then returns to the
# value it had before. This file may be distributed under the terms of the GNU GPLv3 license.
import logging


class WMPinPulse:
    def __init__(self, config):
        self.printer = config.get_printer()
        gcode = self.printer.lookup_object('gcode')
        gcode.register_command('WM_PIN_PULSE', self.cmd_WM_PIN_PULSE,
                               desc=self.cmd_WM_PIN_PULSE_help)

    cmd_WM_PIN_PULSE_help = "Pulse an output_pin for a short time: PIN= WIDTH= VALUE="

    def cmd_WM_PIN_PULSE(self, gcmd):
        name = gcmd.get('PIN')
        pin = self.printer.lookup_object('output_pin ' + name.lower(), None)
        if pin is None:
            pin = self.printer.lookup_object('output_pin ' + name, None)
        if pin is None:
            raise gcmd.error("Unknown output_pin '%s'" % (name,))
        width = gcmd.get_float('WIDTH', 0.022, minval=0.002, maxval=1.0)
        value = gcmd.get_float('VALUE', 0., minval=0., maxval=getattr(pin, 'scale', 1.))
        scale = getattr(pin, 'scale', 1.)
        pulse_value = value / scale
        toolhead = self.printer.lookup_object('toolhead')
        toolhead.register_lookahead_callback(
            lambda print_time: self._pulse(pin, print_time, pulse_value, width))
        toolhead.dwell(width)

    def _pulse(self, pin, print_time, pulse_value, width):
        rest_value = pin.last_value
        self._set(pin, print_time, pulse_value)
        self._set(pin, print_time + width, rest_value)
        pin.last_value = rest_value
        logging.info("wm_pin_pulse: %.3f for %.3f s at %.4f", pulse_value, width,
                     print_time)

    def _set(self, pin, print_time, value):
        logging.info("wm_pin_pulse: edge %.1f at print_time %.6f", value, print_time)
        if getattr(pin, 'is_pwm', False):
            pin.mcu_pin.set_pwm(print_time, value)
        else:
            pin.mcu_pin.set_digital(print_time, value)


def load_config(config):
    return WMPinPulse(config)
