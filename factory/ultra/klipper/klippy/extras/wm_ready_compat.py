# WonderMaker add-on: lets the closed-source factory modules (cs1237 load-cell driver and friends)
# run their "klippy:ready" handler the way the factory Klipper did.
#
# Current Klipper calls all "klippy:ready" handlers with pausing forbidden. The factory cs1237
# module talks to its MCU (a blocking command) in that handler, which now stops Klipper with
# "reactor pause disabled". This module moves those handlers out of the ready loop and starts
# each one a moment later in its own callback, where blocking is allowed. No upstream file
# is edited and the factory module is not changed.
#
# [wm_ready_compat]
# modules: cs1237, hx711, heater_feng, heater_air_core, xy_offset_calibrator_core   (default)
#
# This file may be distributed under the terms of the GNU GPLv3 license.
import logging


class WMReadyCompat:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.reactor = self.printer.get_reactor()
        names = config.get('modules', 'cs1237, hx711, heater_feng, '
                           'heater_air_core, xy_offset_calibrator_core')
        self.modules = set('extras.' + n.strip() for n in names.split(',')
                           if n.strip())
        self.printer.register_event_handler("klippy:connect",
                                            self._handle_connect)

    def _make_deferred(self, orig, label):
        def deferred():
            def run(eventtime):
                try:
                    orig()
                except Exception as e:
                    logging.exception("wm_ready_compat: %s failed", label)
                    self.printer.invoke_shutdown(
                        "Internal error in %s ready handler: %s" % (label, e))
            self.reactor.register_callback(run)
        return deferred

    def _handle_connect(self):
        handlers = self.printer.event_handlers.get("klippy:ready", [])
        for i, cb in enumerate(handlers):
            owner = getattr(cb, '__self__', None)
            mod = getattr(type(owner), '__module__', '') if owner else ''
            if mod in self.modules:
                label = "%s.%s" % (mod, getattr(cb, '__name__', 'ready'))
                handlers[i] = self._make_deferred(cb, label)
                logging.info("wm_ready_compat: deferred ready handler %s",
                             label)


def load_config(config):
    return WMReadyCompat(config)
