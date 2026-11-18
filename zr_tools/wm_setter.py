# WonderMaker: step page of the tool setter position helper (WM_SETTER_PROBE_POSITION), built like the Move page.
# It opens in place of the long adjust window (ks_includes/widgets/prompts.py sends the window's text here) and
# calls the same macros as the window: _WM_SETTER_STEP, _WM_SETTER_FIND, _WM_SETTER_SAVE, _WM_SETTER_MOVE,
# _WM_SETTER_CLOSE. The limits are in _WM_SETTER_STEP, not here.
import logging
import re

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk

from ks_includes.screen_panel import ScreenPanel

WM_SETTER_NUM = r"X\s*([-+]?[\d.]+)\s+Y\s*([-+]?[\d.]+)\s+Z\s*([-+]?[\d.]+)"


def wm_setter_parse(text):
    """(now, saved) as two lists of 3 floats, or None for a part that is not in the first line of the window."""
    out = []
    for key in ("NOZZLE NOW:", "SAVED:"):
        m = re.search(re.escape(key) + r"\s*" + WM_SETTER_NUM, text or "")
        out.append([float(m.group(i)) for i in (1, 2, 3)] if m else None)
    return out[0], out[1]


class Panel(ScreenPanel):
    steps = ["0.05", "0.1", "0.5", "1"]
    step = "0.1"

    def __init__(self, screen, title):
        title = title or "Tool setter position"
        super().__init__(screen, title)
        self.now = None
        self.saved = None
        self.note = ""
        b = self._gtk.Button
        left = Gtk.PositionType.LEFT
        sc = self._gtk.button_image_scale * 0.7
        self.btn = {
            "x-": b("arrow-left", "X left", "color1", sc, left, 1),
            "x+": b("arrow-right", "X right", "color1", sc, left, 1),
            "y+": b("arrow-up", "Y back", "color2", sc, left, 1),
            "y-": b("arrow-down", "Y front", "color2", sc, left, 1),
            "z+": b("z-farther", "Z up", "color3", sc, left, 1),
            "z-": b("z-closer", "Z down", "color3", sc, left, 1),
        }
        for key, w in self.btn.items():
            w.get_style_context().add_class("zr_btn")
            w.connect("clicked", self.do_step, key[0].upper(), key[1])

        pad = Gtk.Grid(row_homogeneous=True, column_homogeneous=True)
        pad.attach(self.btn["y+"], 1, 0, 1, 1)
        pad.attach(self.btn["x-"], 0, 1, 1, 1)
        pad.attach(self.btn["x+"], 2, 1, 1, 1)
        pad.attach(self.btn["y-"], 1, 2, 1, 1)
        mid = Gtk.Label()
        mid.set_markup("<small>X and Y\nfrom above</small>")
        mid.set_justify(Gtk.Justification.CENTER)
        pad.attach(mid, 1, 1, 1, 1)
        pad.attach(self.btn["z+"], 3, 0, 1, 1)
        pad.attach(self.btn["z-"], 3, 2, 1, 1)
        zl = Gtk.Label()
        zl.set_markup("<small>Z, up is\naway from bed</small>")
        zl.set_justify(Gtk.Justification.CENTER)
        pad.attach(zl, 3, 1, 1, 1)

        self.info = Gtk.Label(halign=Gtk.Align.START, valign=Gtk.Align.START)
        self.info.set_line_wrap(True)
        self.info.set_max_width_chars(16)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.get_style_context().add_class("zr_card")
        box.set_border_width(6)
        box.set_margin_start(8)
        box.set_margin_end(4)
        box.set_margin_top(6)
        box.add(self.info)

        stepgrid = Gtk.Grid(column_homogeneous=True)
        lab = Gtk.Label(label="Step, mm")
        stepgrid.attach(lab, 0, 0, 1, 1)
        self.stepbtn = {}
        for j, s in enumerate(self.steps):
            w = self._gtk.Button(label=s)
            w.set_direction(Gtk.TextDirection.LTR)
            w.connect("clicked", self.set_step, s)
            ctx = w.get_style_context()
            ctx.add_class("horizontal_togglebuttons")
            ctx.add_class("zr_btn")
            if s == self.step:
                ctx.add_class("horizontal_togglebuttons_active")
                ctx.add_class("zr_btn_primary")
            self.stepbtn[s] = w
            stepgrid.attach(w, j + 1, 0, 1, 1)

        bottom = Gtk.Grid(column_homogeneous=True)
        for text, gcode, style, col, span in (
                ("Find automatically", "_WM_SETTER_FIND", "color1", 0, 3),
                ("Save", "_WM_SETTER_SAVE", "color3", 3, 2),
                ("Back to saved", "_WM_SETTER_MOVE", "color2", 5, 3),
                ("Close, no save", "_WM_SETTER_CLOSE", "color4", 8, 3)):
            w = self._gtk.Button(None, text, style)
            w.get_style_context().add_class("zr_btn")
            if gcode == "_WM_SETTER_SAVE":
                w.get_style_context().add_class("zr_btn_primary")
            w.connect("clicked", self.send, gcode)
            bottom.attach(w, col, 0, span, 1)

        top = Gtk.Grid(column_homogeneous=True)
        top.attach(pad, 0, 0, 7, 1)
        top.attach(box, 7, 0, 3, 1)

        # the pad takes what is left of the height; step row and bottom row keep a fixed height (no scrolling)
        h = max(40, int(self._screen.height * 0.105))
        for w in list(self.stepbtn.values()) + [lab]:
            w.set_vexpand(False)
        stepgrid.set_size_request(-1, h)
        for w in bottom.get_children():
            w.set_vexpand(False)
            w.set_size_request(-1, int(h * 1.5))
        main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        main.pack_start(top, True, True, 0)
        main.pack_start(stepgrid, False, False, 0)
        main.pack_start(bottom, False, False, 0)
        self.content.add(main)
        self.wm_refresh(getattr(self._screen, "wm_setter_data", ""))

    # ---- data
    def wm_refresh(self, text):
        now, saved = wm_setter_parse(text)
        if now:
            self.now = now
        if saved:
            self.saved = saved
        self.show_info()

    def show_info(self):
        def f(v, sign=False):
            return "-" if v is None else (("%+.2f" if sign else "%.2f") % v)
        n = self.now or [None] * 3
        s = self.saved or [None] * 3
        m = [None if (a is None or c is None) else a - c for a, c in zip(n, s)]
        lines = ["<small><b>NOZZLE NOW</b></small>"]
        lines += ["%s %s" % (a, f(v)) for a, v in zip("XYZ", n)]
        lines += ["<small><b>SAVED</b></small>", "<small>%s  %s  %s</small>" % tuple(f(v) for v in s)]
        lines += ["<small><b>MOVED</b></small>"]
        lines += ["<b>%s %s</b>" % (a, f(v, True)) for a, v in zip("XYZ", m)]
        if self.note:
            lines.append("<small>%s</small>" % GLib.markup_escape_text(self.note))
        self.info.set_markup("\n".join(lines))

    # ---- actions
    def set_step(self, widget, s):
        self.stepbtn[self.step].get_style_context().remove_class("horizontal_togglebuttons_active")
        self.stepbtn[self.step].get_style_context().remove_class("zr_btn_primary")
        self.stepbtn[s].get_style_context().add_class("horizontal_togglebuttons_active")
        self.stepbtn[s].get_style_context().add_class("zr_btn_primary")
        self.step = s

    def do_step(self, widget, axis, sign):
        self.note = ""
        self.send(widget, "_WM_SETTER_STEP AXIS=%s D=%s%s" % (axis, "-" if sign == "-" else "", self.step))

    def send(self, widget, gcode):
        self._screen._send_action(widget, "printer.gcode.script", {"script": gcode})

    # ---- KlipperScreen shows every macro message ("echo:") as a green bar over the top of the screen, and the first
    # tap there only closes the bar (B-051). While this page is open a green message goes into the page's own info
    # text instead; red error messages stay as they are.
    def wm_echo(self, text):
        self.note = text if len(text) <= 110 else text[:107] + "..."
        GLib.timeout_add(40, self.wm_close_echo)

    def wm_close_echo(self):
        scr = self._screen
        try:
            pop = getattr(scr, "popup_message", None)
            if pop is not None and scr._cur_panels and scr._cur_panels[-1] == "wm_setter":
                child = pop.get_child()
                if child is not None and child.get_style_context().has_class("message_popup_echo"):
                    scr.close_popup_message()
        except Exception:
            logging.exception("WM page: message bar")
        return False

    def activate(self):
        self.wm_refresh(getattr(self._screen, "wm_setter_data", ""))
        GLib.timeout_add(40, self.wm_close_echo)

    def process_update(self, action, data):
        try:
            if action == "notify_gcode_response" and isinstance(data, str):
                if "Tool setter position helper closed" in data or "helper is not running" in data:
                    if self._screen._cur_panels and self._screen._cur_panels[-1] == "wm_setter":
                        self._screen._menu_go_back()
                elif "refused" in data and "Tool setter position" in data:
                    self.note = "Step refused: outside the limits (10 mm from saved X and Y, 3 mm under saved Z)"
                    self.show_info()
                elif data.startswith("echo: "):
                    self.wm_echo(data[6:])
                    self.show_info()
            elif action == "notify_status_update" and "gcode_move" in data:
                p = data["gcode_move"].get("gcode_position")
                if p and len(p) >= 3:
                    self.now = [float(p[0]), float(p[1]), float(p[2])]
                    self.show_info()
        except Exception:
            logging.exception("WM setter page")
