"""Add a Light button (chamber light) to KlipperScreen's print screen (job_status.py) while printing or paused.
The button switches Moonraker's power device chamber_light, so Fluidd and the screen always agree. It is always there during
a print. Idempotent; a file patched by an older version (root helper through sudo, or hidden without the helper) is brought up to date.
usage: patch_job_status_light.py /path/to/KlipperScreen/panels/job_status.py"""
import sys

NEW_MARK = "machine.device_power.post_device"
METHOD = '''
    def wm_chamber_light(self, widget):
        # WonderMaker: toggle the chamber light through Moonraker's power device chamber_light (moonraker.conf on the Pi).
        # Fluidd, the macro WM_CHAMBER_LIGHT and this button all switch that one device, so they always show the same state.
        import logging
        from gi.repository import GLib

        def done(response, method=None, params=None, *extra):
            try:
                self._gtk.Button_busy(widget, False)
                if not isinstance(response, dict) or "error" in response:
                    logging.info("chamber light: Moonraker answered %r", response)
                    self._screen.show_popup_message("Chamber light: Moonraker has no power device chamber_light.\\nRun ./installer.sh --update on the Pi.")
            except Exception:
                logging.exception("chamber light: could not reset the button")
            return False

        def watchdog():   # never leave the button spinning
            try:
                self._gtk.Button_busy(widget, False)
            except Exception:
                logging.exception("chamber light: watchdog")
            return False

        logging.info("chamber light: button pressed")
        self._gtk.Button_busy(widget, True)
        GLib.timeout_add_seconds(12, watchdog)
        if not self._screen._ws.send_method("machine.device_power.post_device", {"device": "chamber_light", "action": "toggle"}, done):
            self._gtk.Button_busy(widget, False)
            self._screen.show_popup_message("Chamber light: not connected to Moonraker.")
'''


def upgrade(s):
    """A file patched by an older version (the button ran the root helper through sudo): swap the method for the Moonraker one."""
    i = s.index("\n    def wm_chamber_light(self, widget):")
    j = s.index("\n    def ", i + 5)
    return s[:i] + METHOD.rstrip("\n") + "\n" + s[j:]


p = sys.argv[1]
s = open(p).read()
guard = '''            if os.path.exists("/usr/local/sbin/wm-chamber-light"):
                self.buttons["button_grid"].attach(self.buttons["wm_light"], 4, 0, 1, 1)
'''
plain = '''            self.buttons["button_grid"].attach(self.buttons["wm_light"], 4, 0, 1, 1)
'''
if "wm_chamber_light" in s:
    new = s.replace(guard, plain)      # patched by an older version: show the button always
    if NEW_MARK not in new:
        new = upgrade(new)
    if new != s:
        open(p, "w").write(new)
    sys.exit(0)

a = '        self.buttons["control"].connect("clicked", self._screen._go_to_submenu, "")\n'
if s.count(a) != 1:
    sys.exit(1)
s = s.replace(a, a + '''        # WonderMaker: chamber light button (always shown during a print)
        self.buttons["wm_light"] = self._gtk.Button("light", _("Light"), "color3")
        self.buttons["wm_light"].connect("clicked", self.wm_chamber_light)
''', 1)

b = '            self.buttons["button_grid"].attach(self.buttons["control"], 3, 0, 1, 1)\n'
if s.count(b) != 2:
    sys.exit(1)
s = s.replace(b, b + '''            self.buttons["button_grid"].attach(self.buttons["wm_light"], 4, 0, 1, 1)
''')

i = s.index("\n    def save_offset(self, widget, device):")
s = s[:i] + METHOD + s[i:]
if "\nimport os\n" not in s:
    s = "import os\n" + s if not s.startswith(("#", '"')) else s.replace("\nimport ", "\nimport os\nimport ", 1)
open(p, "w").write(s)
