# WonderMaker add-on: an adaptive (per-print) bed mesh is used from memory and is not saved as a
# profile, so Klipper does not mark the config as changed (no "Save & Restart" in Fluidd).
# This is how the K1 Cartographer plugin behaves for adaptive meshes.
#
# BED_MESH_CALIBRATE does not save a profile when ADAPTIVE=1 is given or PROFILE=adaptive_mesh
# is given, unless SAVE=1 is also given. A plain BED_MESH_CALIBRATE (full mesh) still saves
# the "default" profile exactly like upstream.
#
# This file may be distributed under the terms of the GNU GPLv3 license.
import logging

SKIP_PROFILES = ("adaptive_mesh",)


class WMAdaptiveMesh:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.bedmesh = self.printer.load_object(config, 'bed_mesh')
        self.gcode = self.printer.lookup_object('gcode')
        self.orig_calibrate = self.bedmesh.bmc.cmd_BED_MESH_CALIBRATE
        self.gcode.register_command('BED_MESH_CALIBRATE', None)
        self.gcode.register_command(
            'BED_MESH_CALIBRATE', self.cmd_BED_MESH_CALIBRATE,
            desc=self.bedmesh.bmc.cmd_BED_MESH_CALIBRATE_help)

    def cmd_BED_MESH_CALIBRATE(self, gcmd):
        skip = False
        if gcmd.get_int('SAVE', 0) == 0:
            if gcmd.get_int('ADAPTIVE', 0) > 0:
                skip = True
            elif gcmd.get('PROFILE', '') in SKIP_PROFILES:
                skip = True
        if not skip:
            self.orig_calibrate(gcmd)
            return
        bedmesh = self.bedmesh
        orig_save = bedmesh.save_profile
        def no_save(prof_name):
            logging.info("wm_adaptive_mesh: not saving profile '%s'", prof_name)
        bedmesh.save_profile = no_save
        try:
            self.orig_calibrate(gcmd)
        finally:
            bedmesh.save_profile = orig_save


def load_config(config):
    return WMAdaptiveMesh(config)
