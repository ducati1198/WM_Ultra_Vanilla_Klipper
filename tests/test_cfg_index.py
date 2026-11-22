#!/usr/bin/env python3
"""Tests of scripts/wm_cfg_index.py and its use in wm_rpi_pi.py (F-158). Throwaway folders only."""
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = os.path.join(ROOT, "scripts")
spec = importlib.util.spec_from_file_location("ci", os.path.join(S, "wm_cfg_index.py"))
CI = importlib.util.module_from_spec(spec); spec.loader.exec_module(CI)

SAMPLE = """# rpi_x.cfg  -  test file
# second header line

# ===== part_a.cfg
[gcode_macro WM_SHOW]
description: Shows things
gcode:
    RESPOND MSG="hi"

[gcode_macro _WM_HIDDEN]
gcode:
    M400

[delayed_gcode WM_TICK]
gcode:
    M400
"""


def macro_text(t):
    return [l for l in t.split("\n") if not l.startswith("#") and l.strip()]


class Idx(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_index_lists_visible_hidden_and_keeps_the_macro_text(self):
        new = CI.build(SAMPLE, "rpi_x.cfg")
        self.assertIn("3 macros (2 visible in Fluidd, 1 hidden", new)
        self.assertIn("WM_SHOW", new); self.assertIn("Shows things", new); self.assertIn("[delayed]", new)
        self.assertEqual(macro_text(new), macro_text(SAMPLE))
        self.assertTrue(new.startswith("# rpi_x.cfg  -  test file\n# second header line\n\n" + CI.BEGIN))

    def test_second_run_changes_nothing_and_a_changed_file_gets_one_index(self):
        once = CI.build(SAMPLE, "rpi_x.cfg")
        self.assertEqual(CI.build(once, "rpi_x.cfg"), once)
        more = once + "\n[gcode_macro NEW_ONE]\ngcode:\n    M400\n"
        twice = CI.build(more, "rpi_x.cfg")
        self.assertEqual(twice.count(CI.BEGIN), 1); self.assertIn("NEW_ONE", twice)

    def test_write_backs_up_the_file_that_changes_and_leaves_other_files(self):
        p = os.path.join(self.d, "rpi_x.cfg"); open(p, "w").write(SAMPLE)
        open(os.path.join(self.d, "printer.cfg"), "w").write("[mcu]\n")
        self.assertEqual(CI.main(["x", "write", self.d]), 10)
        self.assertTrue(any(n.startswith("rpi_x.cfg.wm-before-index-") for n in os.listdir(os.path.join(self.d, "backup"))))
        self.assertEqual(open(os.path.join(self.d, "printer.cfg")).read(), "[mcu]\n")
        self.assertEqual(CI.main(["x", "write", self.d]), 0)

    def test_rpi_pi_cfg_keeps_its_index_when_the_installer_rewrites_it(self):
        env = dict(os.environ)
        def run(*a):
            return subprocess.run([sys.executable, "-I", os.path.join(S, "wm_rpi_pi.py")] + list(a), capture_output=True, text=True)
        part = os.path.join(self.d, "light.txt"); open(part, "w").write("[gcode_macro WM_CHAMBER_LIGHT]\ndescription: Chamber light\ngcode:\n    M400\n")
        self.assertEqual(run("set", self.d, "light", part).returncode, 0)
        self.assertEqual(run("set", self.d, "light", part).returncode, 0)     # the rewrite that used to remove the index
        t = open(os.path.join(self.d, "rpi_pi.cfg")).read()
        self.assertEqual(t.count(CI.BEGIN), 1); self.assertIn("WM_CHAMBER_LIGHT", t)
        self.assertEqual(run("has", self.d, "light").returncode, 0)
        self.assertIn("light", run("parts", self.d).stdout)
        self.assertEqual(run("del", self.d, "light").returncode, 0)
        self.assertNotIn("WM_CHAMBER_LIGHT", open(os.path.join(self.d, "rpi_pi.cfg")).read())


if __name__ == "__main__":
    unittest.main(verbosity=1)
