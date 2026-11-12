# WonderMaker add-on: raises the trsync timeout from 0.025 s to 0.05 s as the factory firmware
# does (the factory comment recommends 0.05 for the multi-MCU homing on this printer).
# It also gives the STM32F4-type main board the factory's fixed chip-temperature curve: the board
# has no factory calibration data in its chip, so upstream temperature_mcu divides by zero.
# It also switches off upstream's "probe triggered prior to movement" check for WonderMaker's
# nozzle-sensor probes (the factory Klipper had that check commented out; its X/Y probing moves
# never move every stepper, so the check always fails there).
# All are set at runtime, so no upstream file is edited.
#
# This file may be distributed under the terms of the GNU GPLv3 license.
import logging
import mcu
from . import temperature_mcu, homing

TRSYNC_TIMEOUT = 0.05
NOMOVE_CHECK_CLASSES = ('WeighEndstopWrapper', 'ProbeEndstopWrapper')


def _config_stm32f4_fixed(self, addr1=None, addr2=None):
    # Same numbers as the factory's temperature_mcu.py (typical STM32 internal sensor curve).
    self.slope = 3.3 / -.004400
    self.base_temperature = self.calc_base(25., 1.4 / 3.3)


_seen = set()


def _patch_probing_move():
    orig = homing.PrinterHoming.probing_move
    if getattr(orig, '_wm_patched', False):
        return

    def probing_move(self, mcu_probe, pos, speed, check_movement=True):
        # The factory Klipper never ran this check. Right after a fast move the probe can read
        # triggered for a moment, which upstream turns into a stopped print. Switch it off for
        # every probe (the class name is logged once so it is visible which probes run).
        name = type(mcu_probe).__name__
        if name not in _seen:
            _seen.add(name)
            logging.info("wm_mcu_tweaks: probing_move with %s, no-movement check off", name)
        check_movement = False
        return orig(self, mcu_probe, pos, speed, check_movement)
    probing_move._wm_patched = True
    homing.PrinterHoming.probing_move = probing_move


class WMMcuTweaks:
    def __init__(self, config):
        self.trsync_timeout = config.getfloat('trsync_timeout', TRSYNC_TIMEOUT,
                                              minval=0.025, maxval=0.25)
        mcu.TRSYNC_TIMEOUT = self.trsync_timeout
        if config.getboolean('fix_mcu_temp', True):
            temperature_mcu.PrinterTemperatureMCU.config_stm32f4 = \
                _config_stm32f4_fixed
        if config.getboolean('fix_probe_nomove_check', True):
            _patch_probing_move()
        logging.info("wm_mcu_tweaks: TRSYNC_TIMEOUT set to %.3f",
                     self.trsync_timeout)


def load_config(config):
    return WMMcuTweaks(config)
