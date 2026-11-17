# WonderMaker: Z trim page (WM_Z_TRIM_MENU). One screen in place of the two windows: pick the tool head, Closer /
# Further with a step size, set to 0. It opens in place of the windows (ks_includes/widgets/prompts.py sends the
# values shown on their buttons here) and calls the same macros: _WM_Z_TRIM_STEP, _WM_Z_TRIM_RESET.
# The limit (0.30 mm) and the saving are in the macros, not here.
import logging

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk

from ks_includes.screen_panel import ScreenPanel


class Panel(ScreenPanel):
    steps = ["0.01", "0.02", "0.05", "0.1"]
    step = "0.02"

    def __init__(self, screen, title):
        title = title or "Z trim"
        super().__init__(screen, title)
        self.values = {}
        self.was = {}
        self.target = 0
        self.note = ""
        self.tool = {}
        toolgrid = Gtk.Grid(column_homogeneous=True)
        for t in range(4):
            w = self._gtk.Button(None, "T%d" % t, "color4")
            w.connect("clicked", self.pick, t)
            self.tool[t] = w
            toolgrid.attach(w, t, 0, 1, 1)

        sc = self._gtk.button_image_scale * 0.9
        closer = self._gtk.Button("z-closer", "Closer to the bed", "color1", sc)
        further = self._gtk.Button("z-farther", "Further from the bed", "color3", sc)
        closer.connect("clicked", self.do_step, "-")
        further.connect("clicked", self.do_step, "")
        self.info = Gtk.Label(halign=Gtk.Align.START, valign=Gtk.Align.START)
        self.info.set_line_wrap(True)
        self.info.set_max_width_chars(20)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.set_margin_start(10)
        box.set_margin_end(4)
        box.set_margin_top(6)
        box.add(self.info)
        mid = Gtk.Grid(column_homogeneous=True)
        mid.attach(closer, 0, 0, 3, 1)
        mid.attach(further, 3, 0, 3, 1)
        mid.attach(box, 6, 0, 3, 1)

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
            if s == self.step:
                ctx.add_class("horizontal_togglebuttons_active")
            self.stepbtn[s] = w
            stepgrid.attach(w, j + 1, 0, 1, 1)

        bottom = Gtk.Grid(column_homogeneous=True)
        self.zero = self._gtk.Button(None, "Set T0 to 0", "color2")
        self.zero.connect("clicked", self.do_zero)
        allzero = self._gtk.Button(None, "Set all to 0", "color2")
        allzero.connect("clicked", self.send, "_WM_Z_TRIM_RESET")
        close = self._gtk.Button(None, "Close", "color4")
        close.connect("clicked", self.close)
        bottom.attach(self.zero, 0, 0, 1, 1)
        bottom.attach(allzero, 1, 0, 1, 1)
        bottom.attach(close, 2, 0, 1, 1)

        # the two big buttons take what is left of the height; the other rows keep a fixed height (no scrolling)
        h = max(40, int(self._screen.height * 0.105))
        for w in list(self.stepbtn.values()) + [lab]:
            w.set_vexpand(False)
        stepgrid.set_size_request(-1, h)
        for grid in (toolgrid, bottom):
            for w in grid.get_children():
                w.set_vexpand(False)
                w.set_size_request(-1, int(h * 1.4))
        main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        main.pack_start(toolgrid, False, False, 0)
        main.pack_start(mid, True, True, 0)
        main.pack_start(stepgrid, False, False, 0)
        main.pack_start(bottom, False, False, 0)
        self.content.add(main)
        self.wm_refresh(getattr(self._screen, "wm_ztrim_data", None))

    # ---- data: {"values": {tool: mm}, "target": tool or None} read from the buttons of the windows
    def wm_refresh(self, data):
        if isinstance(data, dict):
            for t, v in (data.get("values") or {}).items():
                if t in self.tool:
                    self.values[t] = v
                    self.was.setdefault(t, v)
            if data.get("target") in self.tool:
                self.target = data["target"]
        self.show_all_values()

    def show_all_values(self):
        def f(v):
            return "-" if v is None else "%+.2f" % v
        for t, w in self.tool.items():
            w.set_label("%sT%d   %s" % ("\u25cf " if t == self.target else "", t, f(self.values.get(t))))
            ctx = w.get_style_context()
            # the chosen tool head: active look and another colour bar
            for cls, on in (("button_active", t == self.target), ("color1", t == self.target), ("color4", t != self.target)):
                if on:
                    ctx.add_class(cls)
                else:
                    ctx.remove_class(cls)
        self.zero.set_label("Set T%d to 0" % self.target)
        lines = ["<small><b>T%d TRIM NOW</b></small>" % self.target,
                 "<big><b>%s mm</b></big>" % f(self.values.get(self.target)),
                 "<small><b>WAS</b>  %s mm</small>" % f(self.was.get(self.target)),
                 "<small>Lines pressed flat or rough: Further. Lines that do not touch: Closer. "
                 "Limit 0.30 mm.</small>"]
        if self.note:
            lines.append("<small>%s</small>" % GLib.markup_escape_text(self.note))
        self.info.set_markup("\n".join(lines))

    # ---- actions
    def pick(self, widget, t):
        self.target = t
        self.note = ""
        self.show_all_values()

    def set_step(self, widget, s):
        self.stepbtn[self.step].get_style_context().remove_class("horizontal_togglebuttons_active")
        self.stepbtn[s].get_style_context().add_class("horizontal_togglebuttons_active")
        self.step = s

    def do_step(self, widget, sign):
        self.note = ""
        self.send(widget, "_WM_Z_TRIM_STEP TARGET=%d D=%s%s" % (self.target, sign, self.step))

    def do_zero(self, widget):
        self.note = ""
        self.send(widget, "_WM_Z_TRIM_STEP TARGET=%d ZERO=1" % self.target)

    def send(self, widget, gcode):
        self._screen._send_action(widget, "printer.gcode.script", {"script": gcode})

    def close(self, widget):
        if self._screen._cur_panels and self._screen._cur_panels[-1] == "wm_ztrim":
            self._screen._menu_go_back()

    def activate(self):
        self.was = {}
        self.wm_refresh(getattr(self._screen, "wm_ztrim_data", None))

    def process_update(self, action, data):
        try:
            if action == "notify_gcode_response" and isinstance(data, str) and "Z trim: the limit is" in data:
                self.note = "The limit is 0.30 mm either way."
                self.show_all_values()
        except Exception:
            logging.exception("WM Z trim page")
