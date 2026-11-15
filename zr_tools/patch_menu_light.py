"""Make the main-menu button "method: wm_chamber_light" toggle the chamber light (no page). The button switches Moonraker's
power device chamber_light. Idempotent; a file patched by an older version (root helper through sudo) is brought up to date.
usage: patch_menu_light.py /path/to/KlipperScreen/panels/menu.py"""
import re
import sys

MARK = "wm_chamber_light"
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
if NEW_MARK in s:
    sys.exit(0)
if MARK in s:
    open(p, "w").write(upgrade(s))
    sys.exit(0)
a = '            elif item["method"] == "ks_confirm_save":\n'
if a not in s:
    sys.exit(1)
s = s.replace(a, '            elif item["method"] == "wm_chamber_light":\n                b.connect("clicked", self.wm_chamber_light)\n' + a, 1)
m = re.search(r"\n    def create_menu_items\(self\):", s)
s = s[:m.start()] + METHOD + s[m.start():]
open(p, "w").write(s)
