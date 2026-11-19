"""F-151: KlipperScreen's Updating page closes by itself when the update is done and Klipper is ready again (stock KlipperScreen keeps
it open until Finish is pressed, and a stale dialog reference stops the next update from opening a page). Idempotent.
usage: patch_ks_update.py /path/to/KlipperScreen/panels/base_panel.py   (exit 0 patched or already patched, 1 the file does not match)"""
import sys

MARK = "WM F-151"
METHODS = '''
    def _wm_start_auto_finish(self):
        # WM F-151: the Updating page closes by itself when the update is complete and Klipper is ready again
        self._wm_tries = 0
        GLib.timeout_add_seconds(5, self._wm_auto_finish)

    def _wm_auto_finish(self):
        dialog = self.update_dialog
        if dialog is None:
            return False
        self._wm_tries += 1
        if self._screen.printer.state == "ready" or self._wm_tries > 36:   # 36 x 5 s = 3 minutes, then it closes anyway
            logging.info("WM: the Updating page closes by itself")
            self.finish_updating(dialog, Gtk.ResponseType.OK)
            return False
        return True
'''
SHOW = '''                        self.update_dialog.get_widget_for_response(Gtk.ResponseType.OK).show()
'''
EXC = '''                        self._screen.state.updating = False
'''
REM = '''        self._gtk.remove_dialog(dialog)
        self._screen._menu_go_back(home=True)
'''

p = sys.argv[1]
s = open(p).read()
if MARK in s:
    sys.exit(0)
try:
    assert s.count(SHOW) == 1 and s.count(REM) == 1 and "def finish_updating" in s
    s = s.replace(SHOW, SHOW + "                        self._wm_start_auto_finish()\n")
    i = s.index("error trying to show the updater button")
    j = s.index(EXC, i)
    s = s[:j + len(EXC)] + "                        self.update_dialog = None   # WM F-151: no stale dialog for the next update\n" + s[j + len(EXC):]
    s = s.replace(REM, '''        self._gtk.remove_dialog(dialog)
        self.update_dialog = None   # WM F-151: a finished dialog is forgotten, the next update opens a new one
        self._screen._menu_go_back(home=True)
''')
    k = s.index("self.update_dialog = None   # WM F-151: a finished")
    k = s.index("\n    def ", k) if "\n    def " in s[k:] else len(s)
    s = s[:k].rstrip("\n") + "\n" + METHODS + s[k:]
    compile(s, p, "exec")
except Exception as e:
    print("patch_ks_update: base_panel.py does not match (%s)" % e)
    sys.exit(1)
open(p, "w").write(s)
