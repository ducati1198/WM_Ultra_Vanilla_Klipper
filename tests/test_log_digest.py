#!/usr/bin/env python3
"""Tests of scripts/wm_log_digest.py (the troubleshooting logs). No Klipper, no Moonraker, no network."""
import importlib.util
import os
import shutil
import sys
import tempfile
import time
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("digest", os.path.join(ROOT, "scripts", "wm_log_digest.py"))
D = importlib.util.module_from_spec(spec)
spec.loader.exec_module(D)
D.API = "http://127.0.0.1:9"          # nothing listens there: the Moonraker calls fail fast


def feed(lines):
    D.SINK = []
    D._LAST.clear()
    D._RATE.update({"minute": 0, "n": 0, "dropped": 0})
    D._ACE_RATE.update({"minute": 0, "n": 0, "dropped": 0})
    r = D.KlippyRules()
    for l in lines:
        r.feed(l)
    out, D.SINK = D.SINK, None
    return out


class KlippyRules(unittest.TestCase):
    def test_config_copy_lines_are_ignored(self):
        out = feed(["\tRESPOND MSG=\"Error evaluating 'x': y\"", "\t{% endif %}", "Stats 1.0: gcodein=0"])
        self.assertEqual(out, [])

    def test_start_shutdown_mcu_macro_error(self):
        out = feed(["Start printer at Tue Nov 17 08:52:58 2026 (1794923578.5 97582.2)",
                    "Transition to shutdown state: Lost communication with MCU 'mcu'",
                    "MCU 'mcu' shutdown: Command request", "MCU 'HUB' shutdown: Timer too close",
                    "Error evaluating 'gcode_macro ZR_LOAD:gcode': gcode.CommandError: ZR_LOAD: T must be 0-3",
                    "Error evaluating 'gcode_macro ZR_LOAD:gcode': gcode.CommandError: ZR_LOAD: T must be 0-3"])
        txt = "\n".join(out)
        self.assertIn("START", txt)
        self.assertIn("SHUTDOWN  Lost communication with MCU 'mcu'", txt)
        self.assertNotIn("mcu shutdown: Command request", txt)          # a normal restart is not an event
        self.assertIn("HUB shutdown: Timer too close", txt)
        self.assertEqual(txt.count("T must be 0-3"), 1)                 # Klipper logs it twice
    def test_config_error_carries_the_reason(self):
        out = feed(["klippy.configfile.error: Unable to open config file x.cfg", "Config error", "Error configuring printer"])
        self.assertEqual(len([x for x in out if "CONFIG" in x]), 1)
        self.assertIn("Unable to open config file x.cfg", out[0])

    def test_ace_lines_go_to_the_ace_log_without_rfid_noise(self):
        out = feed(["ACE[0]: Slot 1 - No RFID tag (rfid=0), skipping inventory update", "ACE[0]: Reconnect - querying RFID data for slot 2",
                    "ACE[0]: Sending request: {'method': 'feed_filament'}", "ACE[0]: Disconnected - all timers stopped"])
        ace = [x for x in out if x.startswith("ACELOG")]
        self.assertEqual(len(ace), 2)
        self.assertTrue(any("feed_filament" in x for x in ace))
        self.assertTrue(any("ACE       ACE[0] Disconnected" in x for x in out))


class ConsoleRules(unittest.TestCase):
    def run_items(self, items, printing=False):
        D.SINK = []
        D._LAST.clear()
        D._RATE.update({"minute": 0, "n": 0, "dropped": 0})
        c = D.ConsoleRules()
        c.printing = printing
        for typ, m in items:
            c.item({"time": time.time(), "type": typ, "message": m})
        out, D.SINK = D.SINK, None
        return out, c

    def test_commands_errors_and_noise(self):
        out, _ = self.run_items([("command", "ZR_LOAD T=3"), ("command", "G1 X10 F3000"), ("command", "M105"),
                                 ("response", "!! ACE: toolhead sensor never triggered"), ("response", "!! Error evaluating 'x': y"),
                                 ("response", "B:22.2 /0.0 T0:23.3 /0.0"), ("response", "// Lock fail"), ("response", "// LOCK fail retry 2")])
        txt = "\n".join(out)
        self.assertIn("COMMAND   ZR_LOAD T=3", txt)
        self.assertNotIn("G1 X10", txt)
        self.assertNotIn("M105", txt)
        self.assertIn("ERROR     ACE: toolhead sensor never triggered", txt)
        self.assertNotIn("Error evaluating", txt)
        self.assertNotIn("B:22.2", txt)
        self.assertEqual(txt.count("tool pickup failed"), 1)

    def test_steps_are_quiet_while_printing_and_tool_changes_are_counted(self):
        out, c = self.run_items([("response", "echo: T3 heats to 210 C at the wipe area"), ("response", "echo: start change tool T0"),
                                 ("response", "echo: Print start purge: T0 20 mm at the wipe area")], printing=True)
        txt = "\n".join(out)
        self.assertNotIn("T3 heats", txt)
        self.assertIn("Print start purge", txt)
        self.assertEqual(c.changes, 1)

    def test_ace_console_lines_and_commands_go_to_the_ace_log(self):
        out, _ = self.run_items([("response", "// ACE: feeding slot 4"), ("command", "ACE_WM_ASSIST T=1 STATE=on"), ("response", "echo: hello")])
        ace = [x for x in out if x.startswith("ACELOG")]
        self.assertEqual(len(ace), 2)


class Limits(unittest.TestCase):
    def test_rate_limit_events_and_ace(self):
        D.SINK = []
        D._LAST.clear()
        D._RATE.update({"minute": 0, "n": 0, "dropped": 0})
        D._ACE_RATE.update({"minute": 0, "n": 0, "dropped": 0})
        for i in range(500):
            D.ev("TEST", "line %d" % i)
            D.ace("ace line %d" % i)
        ev = [x for x in D.SINK if not x.startswith("ACELOG")]
        ac = [x for x in D.SINK if x.startswith("ACELOG")]
        D.SINK = None
        self.assertEqual(len(ev), 120)
        self.assertEqual(len(ac), 200)

    def test_files_rotate(self):
        tmp = tempfile.mkdtemp()
        try:
            D.EVENTS, D.ACELOG = os.path.join(tmp, "e.log"), os.path.join(tmp, "a.log")
            D.MAX_BYTES, D.ACE_MAX = 300, 300
            D._LAST.clear()
            D._RATE.update({"minute": 0, "n": 0, "dropped": 0})
            D._ACE_RATE.update({"minute": 0, "n": 0, "dropped": 0})
            for i in range(40):
                D.ev("TEST", "event number %d" % i)
                D.ace("ace number %d" % i)
            names = sorted(os.listdir(tmp))
            self.assertIn("e.log.1", names)
            self.assertIn("a.log.1", names)
            self.assertLess(os.path.getsize(D.EVENTS), 600)
        finally:
            shutil.rmtree(tmp)
            D.EVENTS = os.path.join(D.LOGS, "wm-events.log")
            D.ACELOG = os.path.join(D.LOGS, "wm-ace.log")
            D.MAX_BYTES, D.ACE_MAX = 1000000, 500000


class ConfigCheck(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        D.CFG = self.tmp
        D.SINK = []

    def tearDown(self):
        D.CFG = os.path.join(D.DATA, "config")
        D.SINK = None
        shutil.rmtree(self.tmp)

    def w(self, name, text):
        with open(os.path.join(self.tmp, name), "w") as f:
            f.write(text)

    def check(self):
        return D.config_check("test")[0]

    def test_clean_config(self):
        self.w("printer.cfg", "[include rpi_a.cfg]\n[mcu]\n\n#*# <---------------------- SAVE_CONFIG ---------------------->\n#*# DO NOT EDIT\n")
        self.w("rpi_a.cfg", "[gcode_macro A]\ngcode:\n    RESPOND MSG=\"all fine {1 * 2}\"\n")
        txt = self.check()
        self.assertIn("0 problems, 1 warnings", txt)                      # the only one: nothing answers on the test Moonraker port
        self.assertIn("Moonraker did not answer", txt)
        self.assertNotIn("RESPOND text", txt)

    def test_missing_include_and_below_save_config(self):
        self.w("printer.cfg", "[include gone.cfg]\n[mcu]\n#*# <---------------------- SAVE_CONFIG ---------------------->\n#*# x\n[include late.cfg]\n")
        txt = self.check()
        self.assertIn("include not found: [include gone.cfg]", txt)
        self.assertIn("below SAVE_CONFIG", txt)

    def test_do_tag_semicolon_and_digit_letters(self):
        self.w("printer.cfg", "[include rpi_b.cfg]\n")
        self.w("rpi_b.cfg", "[gcode_macro T0A]\ngcode:\n    {% do x.append(1) %}\n    RESPOND MSG=\"one; two\"\n    RESPOND MSG=\"star * and {a * b}\"\n    # {% do ignored %}\n")
        txt = self.check()
        self.assertIn("uses the Jinja tag", txt)
        self.assertIn("RESPOND text contains ;", txt)
        self.assertIn("RESPOND text contains *", txt)
        self.assertEqual(txt.count("RESPOND text contains"), 2)         # the {a * b} is a Jinja expression
        self.assertIn("digit followed by letters", txt)
        self.assertEqual(txt.count("uses the Jinja tag"), 1)             # the comment line is ignored

    def test_section_twice_and_unincluded_file(self):
        self.w("printer.cfg", "[include a.cfg]\n[include b.cfg]\n")
        self.w("a.cfg", "[gcode_macro X]\ngcode:\n    M117 a\n")
        self.w("b.cfg", "[gcode_macro X]\ngcode:\n    M117 b\n")
        self.w("lonely.cfg", "[gcode_macro Y]\ngcode:\n    M117 y\n")
        txt = self.check()
        self.assertIn("[gcode_macro X] is defined 2 times", txt)
        self.assertIn("lonely.cfg is in the config folder but no file includes it", txt)


if __name__ == "__main__":
    unittest.main(verbosity=1)
