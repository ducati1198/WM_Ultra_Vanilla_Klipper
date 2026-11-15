# WonderMaker add-on: virtual output pins that work with or without the ACE driver.
#
# A virtual pin is a pin that exists only in software. An [output_pin] on it shows as an on / off
# switch in Fluidd (Outputs) and KlipperScreen, and macros read it as printer["output_pin NAME"].value.
# The ACE driver has its own module for this (virtual_pins.py, chip name "virtual_pin"). This one uses
# a different chip name, "wm_pin", so both can be loaded together and neither needs the other.
#
#   [wm_virtual_pins]
#
#   [output_pin Nozzle_Heat_Growth]
#   pin: wm_pin:nozzle_heat_growth
#   pwm: False
#   value: 0
#
# Only output pins (digital and pwm) are supported. No stock Klipper file is edited.
#
# Based on "Virtual Pins support", Copyright (C) 2023 Pedro Lamas <pedrolamas@gmail.com>
# This file may be distributed under the terms of the GNU GPLv3 license.

CHIP_NAME = 'wm_pin'


class WMVirtualPins:
    def __init__(self, config):
        self._printer = config.get_printer()
        ppins = self._printer.lookup_object('pins')
        ppins.register_chip(CHIP_NAME, self)
        self._pins = {}
        self._oid_count = 0
        self._config_callbacks = []
        self._printer.register_event_handler("klippy:connect",
                                             self.handle_connect)

    def handle_connect(self):
        for cb in self._config_callbacks:
            cb()

    def setup_pin(self, pin_type, pin_params):
        ppins = self._printer.lookup_object('pins')
        name = pin_params['pin']
        if name in self._pins:
            return self._pins[name]
        if pin_type == 'digital_out':
            pin = DigitalOutVirtualPin(self, pin_params)
        elif pin_type == 'pwm':
            pin = PwmVirtualPin(self, pin_params)
        else:
            raise ppins.error(
                "%s pins can only be output pins, not %s" % (CHIP_NAME,
                                                             pin_type))
        self._pins[name] = pin
        return pin

    # The rest of this class answers the calls Klipper makes to an MCU object.
    def create_oid(self):
        self._oid_count += 1
        return self._oid_count - 1

    def register_config_callback(self, cb):
        self._config_callbacks.append(cb)

    def add_config_cmd(self, cmd, is_init=False, on_restart=False):
        pass

    def get_query_slot(self, oid):
        return 0

    def seconds_to_clock(self, time):
        return 0

    def get_printer(self):
        return self._printer

    def register_response(self, cb, msg, oid=None):
        pass

    def alloc_command_queue(self):
        pass

    def lookup_command(self, msgformat, cq=None):
        return VirtualCommand()

    def get_enumerations(self):
        return {}

    def print_time_to_clock(self, print_time):
        return 0

    def estimated_print_time(self, eventtime):
        return 0

    def register_stepqueue(self, stepqueue):
        pass

    def request_move_queue_slot(self):
        pass

    def get_status(self, eventtime):
        return {'pins': {name: pin.get_status(eventtime)
                         for name, pin in self._pins.items()}}


class VirtualCommand:
    def send(self, data=(), minclock=0, reqclock=0):
        pass

    def get_command_tag(self):
        pass


class VirtualPin:
    def __init__(self, mcu, pin_params):
        self._mcu = mcu
        self._name = pin_params['pin']
        self._value = 0.
        # output_pin asks the pin for its MCU to time the change: the main MCU does that
        self._real_mcu = self._mcu.get_printer().lookup_object('mcu')

    def get_mcu(self):
        return self._real_mcu

    def setup_max_duration(self, max_duration):
        pass

    def setup_start_value(self, start_value, shutdown_value):
        self._value = start_value


class DigitalOutVirtualPin(VirtualPin):
    def set_digital(self, print_time, value):
        self._value = value

    def get_status(self, eventtime):
        return {'value': self._value, 'type': 'digital_out'}


class PwmVirtualPin(VirtualPin):
    def setup_cycle_time(self, cycle_time, hardware_pwm=False):
        pass

    def set_pwm(self, print_time, value, cycle_time=None):
        self._value = value

    def get_status(self, eventtime):
        return {'value': self._value, 'type': 'pwm'}


def load_config(config):
    return WMVirtualPins(config)
