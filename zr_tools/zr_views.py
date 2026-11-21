# ZR Tools: the extra views (hub, ACE Pro, calibration, collision, system, settings, extras).
# Mixed into the ZR Tools Panel (zr_tools.py). Uses only helpers the Panel already has:
#   _clear, _label, _button, _header, _scrolled, _confirm, _gcode, _require_idle, _vars, _active_tool, _busy
# KlipperScreen panels are loaded as "panels.<name>", so the logic module is imported from there.

import logging
import math
import os
import socket
import subprocess
import threading
import time

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib  # noqa: E402

try:
    from panels import zr_logic as L
except ImportError:                      # tests import it from the same folder
    import zr_logic as L

NTOOLS = 4


class ViewsMixin:
    dry_temp = 55      # ACE dryer settings (the Climate page edits them)
    dry_hours = 6

    # ------------------------------------------------------------------
    # small helpers
    # ------------------------------------------------------------------
    def _sections(self):
        try:
            return list(self._screen.printer.get_config_section_list(""))
        except Exception:
            return []

    def _tile_grid(self, items, cols=None, scale=1.0, height=None):
        """items: (icon, label, callback). A homogeneous grid of buttons."""
        cols = cols or self.sz["cols"]
        grid = Gtk.Grid()
        grid.set_row_spacing(6)
        grid.set_column_spacing(6)
        grid.set_column_homogeneous(True)
        for n, (icon, label, cb) in enumerate(items):
            b = self._button(icon, label, "color%d" % (1 + n % 4), cb)
            b.set_size_request(-1, height or int(self.sz["tile_h"] * scale))
            grid.attach(b, n % cols, n // cols, 1, 1)
        return grid

    def _open_stock(self, panel, title):
        try:
            self._screen.show_panel(panel, title)
        except Exception as e:
            logging.error(f"ZR: could not open panel {panel}: {e}")
            self._screen.show_popup_message("Could not open %s." % title)

    def _row(self, *widgets, spacing=6):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=spacing)
        row.set_homogeneous(True)
        for w in widgets:
            row.pack_start(w, True, True, 0)
        return row

    def _seg(self, options, current, callback):
        """A row of buttons where `current` is highlighted."""
        buttons = {}

        def _pick(value):
            callback(value)

        for value, text in options:
            b = self._button(None, text, "color3", _pick, value)
            b.set_size_request(-1, self.sz["btn_h"])
            if value == current:
                b.get_style_context().add_class("zr_selected")
            buttons[value] = b
        return self._row(*buttons.values()), buttons

    # ------------------------------------------------------------------
    # HUB: every entry in one place (grid layout home, and the "More" tab)
    # ------------------------------------------------------------------
    def _hub_items(self, include_main=True):
        st = self.st
        items = []
        if include_main:
            items += [("toolchanger", "Toolheads", self.show_main),
                      ("filament", "Filament", self.show_filament),
                      ("heat-up", "Chamber / air", self.show_chamber),
                      ("settings", "Calibration", self.show_utilities)]
        if L.has_ace(st):
            items.append(("spool", "ACE Pro", self.show_ace))
        if not include_main and getattr(self, "tiny", False):     # the Calibrate tab is hidden on a tiny screen
            items.append(("settings", "Calibration", self.show_utilities))
        items += [("shuffle", "Tool map", self.show_mapping),
                  ("fan", "Fans", lambda: self._open_stock("fan", "Fan")),
                  ("retract", "Pressure", lambda: self._open_stock("pressure_advance", "Pressure advance"))]
        items.append(("filament", "Sensors", lambda: self._open_stock("wm_sensors", "Sensors")))   # all sensors, friendly label and real name
        have = {str(x).strip().upper() for x in (self._sections() or [])}
        if not have or "GCODE_MACRO WM_UNLOAD_MENU" in have:      # the unload window of the Pi (one tool or all tools), hidden when the Pi lacks it
            items.append(("retract", "Unload menu", self._unload_open))
        if not have or "GCODE_MACRO WM_LOAD_MENU" in have:         # F-166: Load window (also while paused)
            items.append(("filament", "Load menu", self._load_open))
        if not have or "GCODE_MACRO WM_RESUME_TOOL" in have:       # F-166: choose the tool that continues a paused print
            items.append(("extruder", "Resume tool", self._resume_tool_open))
        if L.collision_settings(self._collision_section()):
            items.append(("warning", "Collision", self.show_collision))
        items += [("camera", "Camera", lambda: self._open_stock("camera", "Camera")),
                  ("clock", "Timelapse", self.show_extras)]
        if L.board_mode():          # KlipperScreen runs on the WonderMaker screen board: it can update itself from GitHub
            items.append(("refresh", "Update screen", self._sys_update))
        items.append(("refresh", "Update Pi", self._pi_update))     # the same update as Fluidd's Update button
        items += [("info", "System", self.show_system),
                  ("settings", "Screen", self.show_settings)]
        return items

    def show_hub(self, title="ZR Tools", include_main=True):
        self.view = "hub" if include_main else "more"
        self._clear()
        self.root.pack_start(self._header(title), False, False, 0)
        self.root.pack_start(self._scrolled(self._tile_grid(self._hub_items(include_main), scale=1.0, height=None if include_main else 78)), True, True, 0)
        self.root.show_all()

    def show_more(self):
        self.show_hub("More", include_main=False)
        self.view = "more"

    # ------------------------------------------------------------------
    # FILAMENT (the existing tool view: heat, load, unload, purge, colour/material/PA editor)
    # ------------------------------------------------------------------
    def show_filament(self):
        self.show_tool(max(self._active_tool(), 0))
        self.view = "tool"

    # ------------------------------------------------------------------
    # ACE PRO (only reachable when an ACE exists; same macros as the Fluidd panel)
    # ------------------------------------------------------------------
    def show_ace(self):
        self.view = "ace"
        self.ace_slot = getattr(self, "ace_slot", 0)
        self.ace_len = getattr(self, "ace_len", 50)
        self.ace_speed = getattr(self, "ace_speed", 5)
        self._clear()
        hdr = self._header("ACE Pro")
        small_screen = bool(self.sz.get("tiny") or self.density == "compact" or (getattr(self._screen, "height", 1200) or 1200) <= 600)    # 800x480 board: no scrolling
        if self._pin_value("ACE_Pro") is not None:     # F-137: the ACE Pro on/off switch (output_pin ACE_Pro, the same as Fluidd)
            sbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            self.w["ace_pro_lbl"] = self._label("", "zr_small")
            sbox.pack_start(self.w["ace_pro_lbl"], False, False, 0)
            sbox.pack_start(self._switch("sw_ace", self._ace_pro_set), False, False, 0)
            hdr.pack_end(sbox, False, False, 0)
        self.root.pack_start(hdr, False, False, 0)
        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4 if small_screen else 6)
        self.w["ace_info"] = self._label("", "zr_small")

        # Four slot cards like the Toolheads page (spool in the filament colour, status chip) ...
        cards = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        cards.set_homogeneous(True)
        self.w["ace_cards"] = []
        small = small_screen
        for i in range(NTOOLS):      # F-194: spools a hair bigger
            ev = Gtk.EventBox()
            ev.get_style_context().add_class("zr_card")
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            for m in ("top", "bottom", "start", "end"):
                getattr(box, "set_margin_" + m)(3 if small else 5)
            c = {"ev": ev, "title": self._label("T%d" % (i + 1), "zr_title"),
                 "spool": self._spool(58 if small else 64), "chip": self._pill("", "empty"),
                 "hub": self._label("", "zr_small")}
            for key in ("title", "spool", "chip", "hub"):
                box.pack_start(c[key], False, False, 0)
            ev.add(box)
            ev.connect("button-release-event", lambda *_a, n=i: self._ace_select(n))
            cards.pack_start(ev, True, True, 0)
            self.w["ace_cards"].append(c)
        body.pack_start(cards, False, False, 0)

        # ... and a grid of big coloured actions like the Filament page.
        bh = int(self.sz["btn_h"] * 1.0)
        acts = [("load", "Load from ACE", "zr_btn_green", self._ace_load),
                ("retract", "Unload to ACE", "zr_btn_orange", self._ace_unload),
                ("fan", "Feed assist", "zr_btn_blue", self._ace_assist),
                ("stop", "Stop motor", "zr_btn_red", self._ace_stop)]
        grid = Gtk.Grid()
        grid.set_row_spacing(6)
        grid.set_column_spacing(6)
        grid.set_column_homogeneous(True)
        for n, (icon, text, cls, cb) in enumerate(acts):
            if text == "Feed assist":       # F-193: blue when feed assist is on, red when off, with a small ON / OFF tag
                b = Gtk.Button()
                b.get_style_context().add_class("zr_btn")
                bx = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)      # label and tag side by side = same height as the other buttons
                bx.set_halign(Gtk.Align.CENTER)
                bx.set_valign(Gtk.Align.CENTER)
                bx.pack_start(Gtk.Label(label="Feed assist"), False, False, 0)
                self.w["ace_assist_pill"] = self._pill("OFF", "off")
                bx.pack_start(self.w["ace_assist_pill"], False, False, 0)
                b.add(bx)
                b.connect("clicked", lambda _w, f=cb: f())
                self.w["ace_assist_btn"] = b
            else:
                b = self._button(icon, text, "color3", cb)
            if cls:
                b.get_style_context().add_class(cls)
            b.set_size_request(-1, bh)
            grid.attach(b, n % 2, n // 2, 1, 1)
        body.pack_start(grid, False, False, 0)
        pages = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)      # F-194: one page per rare job
        pages.set_homogeneous(True)
        for icon, text, cls, cb in (("heat-up", "Dryer", "zr_btn_cyan", self.show_ace_dryer),
                                    ("spool", "Endless spool", "zr_btn_purple", self.show_ace_endless),
                                    ("arrow-down", "Feed / Retract", "zr_btn_navy", self.show_ace_feed)):
            pb = self._button(icon, text, "color3", cb)
            pb.get_style_context().add_class(cls)
            pb.set_size_request(-1, bh)
            pages.pack_start(pb, True, True, 0)
        body.pack_start(pages, False, False, 0)

        self.root.pack_start(self._scrolled(body), True, True, 0)
        self.root.show_all()
        self._refresh_ace()

    # ------------------------------------------------------------------
    # F-194: the three ACE sub pages (each fits one screen, no scrolling)
    # ------------------------------------------------------------------
    def show_ace_feed(self):
        self.view = "ace_feed"
        self.ace_slot = getattr(self, "ace_slot", 0)
        self.ace_len = getattr(self, "ace_len", 50)
        self.ace_speed = getattr(self, "ace_speed", 5)
        self._clear()
        self.root.pack_start(self._header("Feed / Retract"), False, False, 0)
        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        body.set_valign(Gtk.Align.CENTER)
        self.w["feed_slot"] = self._label("", "zr_small")
        body.pack_start(self.w["feed_slot"], False, False, 0)
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row.set_homogeneous(True)
        for icon, text, cls, cb in (("arrow-down", "Feed", "", self._ace_feed),
                                    ("arrow-up", "Retract", "", self._ace_retract),
                                    ("stop", "Stop", "zr_btn_red", self._ace_stop)):
            b = self._button(icon, text, "color3", cb)
            if cls:
                b.get_style_context().add_class(cls)
            b.set_size_request(-1, int(self.sz["btn_h"] * 1.6))
            row.pack_start(b, True, True, 0)
        body.pack_start(row, False, False, 0)
        cols = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        cols.set_homogeneous(True)
        for title, key, wkey, steps in (("Length", "ace_len", "feed_len", (-10, 10)), ("Speed", "ace_speed", "feed_spd", (-1, 1))):
            card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            card.get_style_context().add_class("zr_card")
            card.set_border_width(8)
            card.pack_start(self._label(title, "zr_small"), False, False, 0)
            self.w[wkey] = self._label("", "zr_value")
            card.pack_start(self.w[wkey], False, False, 0)
            br = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            br.set_homogeneous(True)
            for st in steps:
                b = self._button(None, ("%+d" % st), "color3", self._ace_step, key, st)
                b.set_size_request(-1, self.sz["btn_h"])
                br.pack_start(b, True, True, 0)
            card.pack_start(br, False, False, 0)
            cols.pack_start(card, True, True, 0)
        body.pack_start(cols, False, False, 0)
        self.root.pack_start(body, True, True, 0)
        self.root.show_all()
        self._refresh_feed()

    def _refresh_feed(self):
        if "feed_len" not in self.w:
            return
        self.w["feed_slot"].set_text("Toolhead T%d" % (self.ace_slot + 1))
        self.w["feed_len"].set_text("%d mm" % self.ace_len)
        self.w["feed_spd"].set_text("%d mm/s" % self.ace_speed)

    def show_ace_endless(self):
        self.view = "ace_endless"
        self._clear()
        self.root.pack_start(self._header("Endless spool"), False, False, 0)
        h = getattr(getattr(self, "_screen", None), "height", 480) or 480
        self.RING = int(max(150, min(h * 0.42, h - 270)))       # a bigger circle, tool numbers scale with it
        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        body.set_valign(Gtk.Align.CENTER)
        self._build_endless(body)
        self.root.pack_start(body, True, True, 0)
        self.root.show_all()
        self._refresh_endless()

    def show_ace_dryer(self):
        self.view = "ace_dryer"
        self._clear()
        self.root.pack_start(self._header("ACE Dryer"), False, False, 0)
        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        body.set_valign(Gtk.Align.CENTER)
        self._build_dryer(body, big=True)
        self.root.pack_start(body, True, True, 0)
        self.root.show_all()
        self._refresh_dryer()

    def _build_dryer(self, body, big=False):
        """The ACE dryer card: big temperature and hours, presets, Temp / Hours steps, start and stop. big=True: the full ACE Dryer page (F-194)."""
        self.dry_temp = getattr(self, "dry_temp", 55)
        self.dry_hours = getattr(self, "dry_hours", 6)
        bh = int(self.sz["btn_h"] * 1.2) if big else min(self.sz["btn_h"], 42)      # F-194: the ACE Dryer page has bigger buttons
        if not big:
            body.pack_start(self._label("ACE DRYER", "zr_small"), False, False, 0)
        vals = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14 if not big else 70)
        vals.set_halign(Gtk.Align.CENTER)
        self.w["dry_lbl"] = self._label("", "zr_value_xl" if big else "zr_value")
        self.w["dry_hrs"] = self._label("", "zr_value_xl_dim" if big else "zr_value_dim")
        vals.pack_start(self.w["dry_lbl"], False, False, 0)
        vals.pack_start(self.w["dry_hrs"], False, False, 0)
        body.pack_start(vals, False, False, 0)
        self.w["dry_info"] = self._label("", "zr_small")
        body.pack_start(self.w["dry_info"], False, False, 0)
        pres = Gtk.Grid()
        pres.set_column_spacing(6)
        pres.set_row_spacing(6)
        pres.set_column_homogeneous(True)
        for n, (name, temp, hours) in enumerate(L.DRY_PRESETS):
            b = self._button(None, name, "color3", self._ace_preset, temp, hours)
            b.set_size_request(-1, bh - 4)
            pres.attach(b, n % 3, n // 3, 1, 1)
        body.pack_start(pres, False, False, 0)
        drow = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        drow.set_homogeneous(True)
        for text, key, step in (("-5\u00b0", "dry_temp", -5), ("+5\u00b0", "dry_temp", 5),
                                ("-1 h", "dry_hours", -1), ("+1 h", "dry_hours", 1)):
            b = self._button(None, text, "color3", self._ace_step, key, step)
            b.set_size_request(-1, bh)
            drow.pack_start(b, True, True, 0)
        body.pack_start(drow, False, False, 0)
        start = self._button("heat-up", "Start drying", "color1", self._ace_dry_start)
        stop = self._button("stop", "Stop", "color3", self._ace_dry_stop)
        for btn in (start, stop):
            btn.set_size_request(-1, bh + 4)
        body.pack_start(self._row(start, stop), False, False, 0)
        self._refresh_dryer()

    def _refresh_dryer(self):
        if "dry_lbl" not in self.w:
            return
        a = L.ace_state(self.st)
        t = []
        if a["temp"] is not None:
            t.append("ACE %s C" % a["temp"])
        if a["humidity"] is not None:
            t.append("%s %% RH" % a["humidity"])
        t.append(("drying, %s left" % a["dry_left"]) if a["drying"] else "dryer off")
        t.append("max %s C" % a["max_temp"])
        self.w["dry_info"].set_text("  -  ".join(t))
        self.w["dry_lbl"].set_text("%d\u00b0C" % self.dry_temp)
        self.w["dry_hrs"].set_text("%d h" % self.dry_hours)

    def _refresh_ace(self):
        if "ace_info" not in self.w:
            return
        a = L.ace_state(self.st)
        t = []
        t.append("%s %s: %s" % (a["model"], a["firmware"], a["state"]))
        if a["temp"] is not None:
            t.append("%s C" % a["temp"])
        if a["humidity"] is not None:
            t.append("%s %% RH" % a["humidity"])
        if a["drying"]:
            t.append("drying, %s left" % a["dry_left"])
        self.w["ace_info"].set_text("   ".join(t))
        ab = self.w.get("ace_assist_btn")
        if ab is not None and 0 <= self.ace_slot < len(a["slots"]):      # F-193: Feed assist button blue when on, red when off
            on = bool(a["slots"][self.ace_slot]["assist"])
            ctx = ab.get_style_context()
            for c in ("zr_btn_primary", "zr_btn_blue", "zr_btn_red"):
                ctx.remove_class(c)
            ctx.add_class("zr_btn_blue" if on else "zr_btn_red")
            self._set_pill(self.w["ace_assist_pill"], "ON" if on else "OFF", "on" if on else "off")
        for i, c in enumerate(self.w["ace_cards"]):
            sl = a["slots"][i]
            info = self._tool_info(i)
            has = not sl["empty"] and sl["text"] != "no data"
            self._mark_empty(c["ev"], c["spool"], not has)   # F-172: empty ACE slot = whole box + spool grey
            self._set_swatch(c["spool"], info["color"] if has else 0x303030)
            kind = "empty" if not has else ("active" if sl["text"] in ("loading", "unloading", "assist") else "ready")
            self._set_pill(c["chip"], sl["text"].capitalize(), kind)
            c["hub"].set_text("-" if sl["hub"] is None else ("hub on" if sl["hub"] else "hub off"))
            ctx = c["ev"].get_style_context()
            if i == self.ace_slot:
                ctx.add_class("zr_active")
            else:
                ctx.remove_class("zr_active")
        pin = self._pin_value("ACE_Pro")
        if pin is not None and "sw_ace" in self.w:
            self._set_switch("sw_ace", pin)
            self.w["ace_pro_lbl"].set_text("ON" if pin else "off")
        self._refresh_endless()

    def _ace_select(self, i):
        self.ace_slot = i
        self._refresh_ace()

    def _ace_idle_gate(self):
        return self._require_idle()

    def _ace_load(self):
        if self._ace_idle_gate():
            self._confirm("Load from ACE", "Feed slot T%d to the toolhead and load it?" % (self.ace_slot + 1),
                          "ACE_WM_LOAD T=%d" % self.ace_slot, "ACE loading T%d" % (self.ace_slot + 1))

    def _ace_unload(self):
        if self._ace_idle_gate():
            self._confirm("Unload to ACE", "Unload toolhead T%d and pull the filament back into the ACE?" % (self.ace_slot + 1),
                          "ACE_WM_UNLOAD T=%d" % self.ace_slot, "ACE unloading T%d" % (self.ace_slot + 1))

    def _ace_assist(self):
        a = L.ace_state(self.st)["slots"][self.ace_slot]["assist"]
        cmd = "ACE_DISABLE_FEED_ASSIST" if a else "ACE_ENABLE_FEED_ASSIST"
        self._gcode("%s T=%d" % (cmd, self.ace_slot), "Feed assist %s" % ("off" if a else "on"))

    def _ace_stop(self):
        self._gcode("ACE_WM_STOP", "ACE stopped")

    def _ace_feed(self):
        if self._ace_idle_gate():
            self._gcode("ACE_FEED T=%d LENGTH=%d SPEED=%d" % (self.ace_slot, self.ace_len, self.ace_speed), "ACE feeding")

    def _ace_retract(self):
        if self._ace_idle_gate():
            self._gcode("ACE_RETRACT T=%d LENGTH=%d SPEED=%d" % (self.ace_slot, self.ace_len, self.ace_speed), "ACE retracting")

    def _ace_step(self, key, step):
        if key == "ace_len":
            self.ace_len = max(10, min(500, self.ace_len + step))
            return self._refresh_feed() if self.view == "ace_feed" else self._refresh_ace()
        elif key == "ace_speed":
            self.ace_speed = max(1, min(30, self.ace_speed + step))
            return self._refresh_feed() if self.view == "ace_feed" else self._refresh_ace()
        elif key == "dry_temp":
            self.dry_temp, self.dry_hours = L.clamp_dry(self.dry_temp + step, self.dry_hours, L.ace_state(self.st)["max_temp"])
            return self._refresh_dryer()
        elif key == "dry_hours":
            self.dry_temp, self.dry_hours = L.clamp_dry(self.dry_temp, self.dry_hours + step, L.ace_state(self.st)["max_temp"])
            return self._refresh_dryer()
        self._refresh_ace()

    def _ace_preset(self, temp, hours):
        self.dry_temp, self.dry_hours = L.clamp_dry(temp, hours, L.ace_state(self.st)["max_temp"])
        self._refresh_dryer()

    def _ace_dry_start(self):
        self._gcode("_ACE_WM_DRY_START TEMP=%d DURATION=%d" % (self.dry_temp, self.dry_hours * 60), "Drying started")

    def _ace_dry_stop(self):
        self._gcode("_ACE_WM_DRY_STOP", "Drying stopped")

    def _ace_endless_toggle(self):
        on = L.endless_enabled(self._vars())
        self._gcode("_WM_ENDLESS_SET ENABLE=%d" % (0 if on else 1), "Endless spool %s" % ("off" if on else "on"))

    # ------------------------------------------------------------------
    # CALIBRATION (only macros that exist on this printer)
    # ------------------------------------------------------------------
    def show_utilities(self):
        self.view = "utilities"
        self._clear()
        self.root.pack_start(self._header("Calibration"), False, False, 0)
        a = self._active_tool()
        items = [("home", "Home all", "G28", "Home all axes?")]
        items += [(i, l, s, q) for (i, l, s, q, _r) in L.calibration_items(self._sections(), a)]
        items += [("extruder", "Park tool", "PARK_CURRENT_TOOL", "Return the active toolhead to its dock?"),
                  ("motor-off", "Motors off", "M84", "Disable all motors?"),
                  ("unlock", "Unlock gripper", "UNLOCK", "HOLD THE TOOL HEAD with your hand first. Opening the gripper lets go of it, and it falls onto the bed if nobody holds it. Open the toolhead gripper?"),
                  ("lock", "Lock gripper", "LOCK", "Close the toolhead gripper?")]
        tiles = []
        for icon, text, script, question in items:
            tiles.append((icon, text, (lambda t=text, s=script, q=question: self._utility(t, s, q))))
        if L.shaper_available(self._sections()):
            tiles.append(("speed+", "Input shaper", lambda: self._open_stock("input_shaper", "Input shaper")))
        else:
            tiles.append(("speed+", "Input shaper (not available)", lambda: self._screen.show_popup_message(
                "Needs the LIS2DW sensor on the tool-changer board (EX_T) and [resonance_tester].")))
        self.root.pack_start(self._scrolled(self._tile_grid(tiles)), True, True, 0)
        self.root.show_all()

    # ------------------------------------------------------------------
    # COLLISION (read-only on purpose)
    # ------------------------------------------------------------------
    def _collision_section(self):
        try:
            return self._screen.printer.get_config_section("collision_detect")
        except Exception:
            return None

    def show_collision(self):
        self.view = "collision"
        self._clear()
        self.root.pack_start(self._header("Collision detection"), False, False, 0)
        c = L.collision_settings(self._collision_section())
        if not c:
            text = "No [collision_detect] section in the printer config."
        else:
            text = ("Sensor: %s\nThreshold: %s m/s^2\nWindow: %s samples\nAction on impact: %s\n\n"
                    "Read-only on purpose. To change the threshold edit change_extruder.cfg "
                    "([collision_detect]) and restart Klipper. WonderMaker's tool-offset macros switch "
                    "the detection on and off by themselves."
                    % (c["sensor"], c["threshold"], c["window"], c["action"]))
        self.root.pack_start(self._label(text, wrap=True), True, True, 0)
        self.root.show_all()

    # ------------------------------------------------------------------
    # TIMELAPSE / RESTART / TEST TOOL CHANGE
    # ------------------------------------------------------------------
    def show_extras(self):
        self.view = "extras"
        self._clear()
        self.root.pack_start(self._header("Timelapse and restart"), False, False, 0)
        have = {s.upper() for s in self._sections()}
        a = self._active_tool()
        nxt = (a + 1) % NTOOLS if a >= 0 else 0
        entries = [("camera", "Take frame", "TIMELAPSE_TAKE_FRAME", "Take one timelapse frame now?", "GCODE_MACRO TIMELAPSE_TAKE_FRAME"),
                   ("complete", "Render video", "TIMELAPSE_RENDER", "Render the timelapse video now?", "GCODE_MACRO TIMELAPSE_RENDER"),
                   ("refresh", "Restart Klipper", "RESTART", "Restart Klipper (reload the config)?", None),
                   ("refresh", "Firmware restart", "FIRMWARE_RESTART", "Firmware restart? This resets the MCUs.", None),
                   ("toolchanger", "Test change to T%d" % nxt, "T%d" % nxt, "Change to toolhead T%d now?\nThe printer must be homed." % nxt, "GCODE_MACRO T%d" % nxt)]
        tiles = []
        for icon, text, script, q, need in entries:
            if need is None or need in have:
                tiles.append((icon, text, (lambda t=text, s=script, qq=q: self._utility(t, s, qq))))
        self.root.pack_start(self._scrolled(self._tile_grid(tiles, height=78)), True, True, 0)
        self.root.show_all()

    # ------------------------------------------------------------------
    # SYSTEM
    # ------------------------------------------------------------------
    def show_system(self):
        self.view = "system"
        self._clear()
        self.root.pack_start(self._header("System"), False, False, 0)
        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.w["sys"] = self._label("", wrap=True)
        body.pack_start(self.w["sys"], False, False, 0)
        if L.board_mode():     # KlipperScreen runs on the WonderMaker screen board
            tiles = [("home", "Factory mode", self._sys_factory),
                     ("refresh", "Reboot the Pi", self._sys_reboot),
                     ("shutdown", "Shut down the Pi", self._sys_shutdown)]
            if L.rescue_available():
                tiles.insert(1, ("settings", "Rescue", self._sys_rescue))
        else:
            tiles = [("sd", "Backup settings", self._sys_backup),
                     ("refresh", "Reboot", self._sys_reboot),
                     ("shutdown", "Shut down", self._sys_shutdown)]
        body.pack_start(self._tile_grid(tiles, height=78), False, False, 0)
        self.root.pack_start(self._scrolled(body), True, True, 0)
        self.root.show_all()
        self._refresh_system()

    def _read_flags(self):
        try:
            out = subprocess.run(["vcgencmd", "get_throttled"], capture_output=True, text=True, timeout=2).stdout
            return out.split("=")[-1].strip()
        except Exception:
            return ""

    def _refresh_system(self):
        if "sys" not in self.w:
            return
        temp = L.read_pi_temp()
        flags = self._read_flags()
        try:
            host = socket.gethostname()
            ip = socket.gethostbyname(host)
        except OSError:
            host, ip = "", ""
        can = "down or missing"
        try:
            with open("/sys/class/net/can0/operstate") as f:
                can = "up" if f.read().strip() in ("up", "unknown") else "down"
        except OSError:
            pass
        try:
            kstate = self._screen.printer.state
        except Exception:
            kstate = "unknown"
        lines = ["Pi temperature: %s" % ("%.0f C" % temp if temp is not None else "unknown"),
                 "Power: %s" % (L.throttled_text(flags) if flags else "unknown"),
                 "can0: %s" % can, "Klipper: %s" % kstate,
                 "Fluidd: %s" % (L.fluidd_url(host, ip) or "unknown")]
        self.w["sys"].set_text("\n".join(lines))

    def _install_dir(self):
        try:
            with open(os.path.expanduser("~/wm-rpi-backup/install.conf")) as f:
                for line in f:
                    if line.startswith("REPO_DIR="):
                        return line.split("=", 1)[1].strip()
        except OSError:
            pass
        return ""

    def _sys_backup(self):
        repo = self._install_dir()
        if not repo or not os.path.exists(os.path.join(repo, "installer.sh")):
            self._screen.show_popup_message("Installer folder not found. Run ./installer.sh --backup in a terminal.")
            return

        def _go():
            try:
                subprocess.Popen(["bash", os.path.join(repo, "installer.sh"), "--backup"],
                                 stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                self._screen.show_popup_message("Backup started. It is saved in ~/wm-backups.", 1)
            except OSError as e:
                self._screen.show_popup_message("Backup failed: %s" % e)
        self._confirm_call("Backup", "Save your config, calibration and database to ~/wm-backups?", _go)

    def _confirm_call(self, title, text, func, no="Cancel", yes="OK"):
        self._ask_page(title, text, func, "Yes" if yes == "OK" else yes, no)

    def _sys_factory(self):
        if not self._require_idle():
            return
        self._confirm_call("Factory mode",
                           "Switch this screen back to the WonderMaker factory software?\n"
                           "KlipperScreen is removed, the factory services are turned back on and the board reboots.\n"
                           "The screen turns black: wait about 5 minutes for the WonderMaker app to appear.",
                           self._run_factory_restore)

    def _sys_rescue(self):
        self._confirm_call("Rescue window",
                           "Open the rescue window? KlipperScreen stops while it is open. In the window, 'Restart KlipperScreen' brings it back.",
                           self._run_rescue)

    def _run_rescue(self):
        try:
            subprocess.Popen(L.rescue_command(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        except OSError as e:
            self._screen.show_popup_message("Could not open the rescue window: %s" % e)

    def _sys_update(self):
        """Update button (More): looks up the newest version on GitHub, asks, then the root copy of screen_board.sh updates
        the installer folder and the screen files and restarts KlipperScreen."""
        if not self._require_idle():
            return
        self._screen.show_popup_message("Checking for a new version ...", 1)

        def _check():
            latest = L.latest_version()
            GLib.idle_add(self._update_answer, latest, L.installed_version())
        threading.Thread(target=_check, daemon=True).start()

    def _update_answer(self, latest, installed):
        versions = "Installed: %s    Latest: %s" % (installed or "unknown", latest or "unknown")
        try:
            if not latest:
                self._screen.show_popup_message("Could not check for a new version. Is the screen board online?\n" + versions)
            elif not L.version_newer(latest, installed):
                self._screen.show_popup_message("Up to date.\n" + versions, 1)
            else:
                self._confirm_call("Update",
                                   "A new version is available.\n%s\n"
                                   "It updates the installer files and the screen, then restarts KlipperScreen and Klipper.\n"
                                   "The screen goes dark for about a minute. Do not power off. Update now?" % versions,
                                   self._run_update)
        except Exception:
            logging.exception("ZR Tools: update check")
        return False

    def _run_update(self):
        if not self._require_idle():
            return

        def _go():
            ok, msg = L.start_update()
            GLib.idle_add(self._update_started, ok, msg)
        self._screen.show_popup_message("Starting the update ...", 1)
        threading.Thread(target=_go, daemon=True).start()

    def _update_started(self, ok, msg):
        try:
            if ok:
                self._screen.show_popup_message("Updating. The screen restarts by itself in about a minute.", 1)
            else:
                logging.error("ZR Tools: update did not start: %s", msg)
                hint = ""
                if "password" in msg.lower() or "not allowed" in msg.lower():
                    hint = "\nThe update permission is missing. In a terminal on the board run once:\nbash ~/WM_Ultra_Vanilla_Klipper/scripts/screen_board.sh --post-update"
                self._screen.show_popup_message("Could not start the update: %s%s" % (msg, hint))
        except Exception:
            logging.exception("ZR Tools: update start")
        return False

    def _pi_update(self):
        """Update Pi button (More): asks Moonraker whether the installer on the Pi has a newer version, asks, then Moonraker downloads it
        and wm-pi-update.service applies it (backup, configs, add-ons, restart of Klipper and Moonraker) exactly as Fluidd's Update does."""
        if not self._require_idle():
            return
        base = self._http_base()
        if base is None:
            self._screen.show_popup_message("Not connected to the Pi.")
            return
        self._screen.show_popup_message("Checking the Pi for a new version ...", 1)

        def _check():
            GLib.idle_add(self._pi_update_answer, base, L.pi_update_check(base))
        threading.Thread(target=_check, daemon=True).start()

    def _pi_update_answer(self, base, info):
        try:
            panel = (info or {}).get("panel") or {}
            names = L.pi_update_names(info) if info else []
            if info is None:
                self._screen.show_popup_message("Could not check for a new version. Is the Pi online?")
            elif not info["known"]:
                self._screen.show_popup_message("This installer is not in the Pi's update list yet.\nIn SSH run once: cd ~/WM_Ultra_Vanilla_Klipper && ./installer.sh --update")
            elif info["problem"]:
                self._screen.show_popup_message(info["problem"])
            elif not names:
                text = "The Pi is up to date.\nInstaller: %s" % (info["version"] or "unknown")
                if panel.get("known"):
                    text += "    Fluidd panel: %s" % (panel.get("version") or "unknown")
                if panel.get("problem"):
                    text += "\n" + panel["problem"]
                self._screen.show_popup_message(text, 1)
            else:
                lines = []
                if names[0] == L.PI_UPDATE_NAME:
                    lines.append("Installer: %s -> %s" % (info["version"] or "unknown", info["remote"] or "unknown"))
                if panel.get("known") and panel.get("behind"):
                    lines.append("Fluidd panel: %s -> %s" % (panel.get("version") or "unknown", panel.get("remote") or "unknown"))
                self._confirm_call("Update Pi",
                                   "New versions are available:\n%s\n"
                                   "Update now makes a backup, updates the configs, the Fluidd panel and the screen boards added on the Pi, then restarts Klipper and Moonraker.\n"
                                   "The screen shows 'Disconnected' for about a minute. Do not power off."
                                   % "\n".join(lines),
                                   lambda: self._pi_update_run(base, names), no="Not now", yes="Update now")
        except Exception:
            logging.exception("ZR Tools: Pi update check")
        return False

    def _pi_update_run(self, base, names=None):
        if not self._require_idle():
            return

        def _go():
            GLib.idle_add(self._pi_update_started, *L.pi_update_start(base, names=names))
        self._screen.show_popup_message("Starting the Pi update ...", 1)
        threading.Thread(target=_go, daemon=True).start()

    def _pi_update_started(self, ok, msg):
        try:
            if ok:
                self._screen.show_popup_message("Downloaded. The Pi applies it now and restarts Klipper in about a minute. Log: ~/wm-pi-update.log", 1)
            else:
                logging.error("ZR Tools: Pi update did not start: %s", msg)
                self._screen.show_popup_message("Could not start the Pi update: %s" % msg)
        except Exception:
            logging.exception("ZR Tools: Pi update start")
        return False

    def _run_factory_restore(self):
        try:
            subprocess.Popen(L.factory_restore_command(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        except OSError as e:
            self._screen.show_popup_message("Could not start the restore: %s" % e)

    def _sys_reboot(self):
        if self._require_idle():
            self._confirm_call("Reboot", "Reboot the Pi?", lambda: self._screen._ws.send_method("machine.reboot"))

    def _sys_shutdown(self):
        if self._require_idle():
            self._confirm_call("Shut down", "Shut the Pi down?", lambda: self._screen._ws.send_method("machine.shutdown"))

    # ------------------------------------------------------------------
    # SCREEN SETTINGS (layout, density, theme)
    # ------------------------------------------------------------------
    def show_settings(self):
        self.view = "settings"
        self._clear()
        self.root.pack_start(self._header("Screen settings"), False, False, 0)
        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        for key, title, options in (
                ("layout", "Layout", [("tabs", "Big touch + tabs"), ("grid", "Card grid")]),
                ("density", "Size", [("auto", "Auto (%s)" % self.density), ("compact", "Compact"), ("comfortable", "Comfortable")]),
                ("theme", "Colours of these pages", [("dark", "Dark"), ("light", "Light")]),
                ("style", "Look", [("soft", "Soft"), ("flat", "Flat"), ("bold", "Bold"), ("classic", "Classic")])):
            body.pack_start(self._label(title, "zr_small"), False, False, 0)
            row, _btns = self._seg(options, self.settings[key], (lambda v, k=key: self._set_setting(k, v)))
            body.pack_start(row, False, False, 0)
        body.pack_start(self._label("For a fully light screen also choose the material-light icon theme in KlipperScreen's "
                                    "own Configuration page. Saved in ~/printer_data/config/zr_screen.conf.", "zr_hint", wrap=True),
                        False, False, 0)
        self.root.pack_start(self._scrolled(body), True, True, 0)
        self.root.show_all()

    def _set_setting(self, key, value):
        self.settings[key] = value
        try:
            L.save_settings(self.settings)
        except OSError as e:
            self._screen.show_popup_message("Could not save the settings: %s" % e)
        self._apply_settings()
        self.show_settings()

    # ------------------------------------------------------------------
    # live refresh hook (called from the Panel's _refresh_view)
    # ------------------------------------------------------------------
    def refresh_extra_views(self):
        if self.view == "ace":
            self._refresh_ace()
        elif self.view == "ace_feed":
            self._refresh_feed()
        elif self.view == "ace_endless":
            self._refresh_endless()
        elif self.view == "ace_dryer":
            self._refresh_dryer()
        elif self.view == "system":
            self._refresh_system()
        elif self.view == "growth":
            self._refresh_growth()
        elif self.view in ("hub", "more"):
            pass

    # ------------------------------------------------------------------
    # F-137: switches (ACE Pro, endless spool, nozzle heat growth)
    # ------------------------------------------------------------------
    def _switch(self, key, cb):
        sw = Gtk.Switch()
        sw.set_valign(Gtk.Align.CENTER)
        sw.set_size_request(int(70 * self.scale), int(34 * self.scale))
        def _toggled(w, _p):
            if getattr(self, "_sw_lock", False):
                return
            self.__dict__.setdefault("_sw_hold", {})[key] = (w.get_active(), time.monotonic() + 5.0)    # keep what was tapped until Klipper reports it (no flicker)
            cb(w.get_active())
        sw.connect("notify::active", _toggled)
        self.w[key] = sw
        return sw

    def _set_switch(self, key, value):
        sw = self.w.get(key)
        if sw is None:
            return
        hold = self.__dict__.setdefault("_sw_hold", {}).get(key)
        if hold is not None:
            if time.monotonic() < hold[1] and bool(value) != hold[0]:
                return            # Klipper still reports the old value: ignore it, the new one is on its way
            self._sw_hold.pop(key, None)
        if sw.get_active() == bool(value):
            return
        self._sw_lock = True
        try:
            sw.set_active(bool(value))
        finally:
            self._sw_lock = False

    def _pin_value(self, name):
        p = self.st.get("output_pin " + name)
        if not isinstance(p, dict) or "value" not in p:
            return None
        try:
            return float(p["value"]) >= 0.5
        except (TypeError, ValueError):
            return None

    def _ace_pro_set(self, on):
        self._gcode("SET_PIN PIN=ACE_Pro VALUE=%d" % (1 if on else 0), "ACE Pro %s" % ("on" if on else "off"))

    def _endless_set(self, on):
        self._gcode("_WM_ENDLESS_SET ENABLE=%d" % (1 if on else 0), "Endless spool %s" % ("on" if on else "off"))

    def _auto_set(self, on):
        self._gcode("_WM_ENDLESS_SET AUTO=%d" % (1 if on else 0), "Swap automatically %s" % ("on" if on else "off"))

    # ------------------------------------------------------------------
    # F-137: endless spool section = the same ring and chips as the Fluidd Toolheads card
    # ------------------------------------------------------------------
    RING = 120

    def _endless_keys(self):
        v = self._vars()
        keys = []
        for i in range(NTOOLS):
            m, c = v.get("zr_t%d_mat" % i), v.get("zr_t%d_color" % i)
            keys.append(None if m is None or c is None else "%s/%s" % (m, c))
        return keys

    def _endless_loaded(self):
        out = []
        for i in range(NTOOLS):
            head = self._sensor("filament%d" % i)
            out.append(False if head is True and self._sensor("path_%d" % i) is False else head)
        return out

    def _build_endless(self, body):
        avail = L.ace_state(self.st)["endless_available"]
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        card.get_style_context().add_class("zr_card")
        card.set_border_width(8)
        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        title = self._label()
        title.set_markup("<b>Endless spool</b>")
        top.pack_start(title, True, True, 0)
        if avail:
            top.pack_end(self._switch("sw_endless", self._endless_set), False, False, 0)
            auto = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            auto.pack_start(self._label("Swap automatically", "zr_small"), False, False, 0)
            auto.pack_start(self._switch("sw_auto", self._auto_set), False, False, 0)
            self.w["auto_box"] = auto
            top.pack_end(auto, False, False, 12)
        card.pack_start(top, False, False, 0)
        if not avail:
            card.pack_start(self._label("The endless spool macros (rpi_endless.cfg) are not installed on this printer.",
                                        "zr_hint", wrap=True), False, False, 0)
        else:
            self.w["endless_off"] = self._label("Off. Switch it on to see which toolheads take over for each other.",
                                                "zr_hint", wrap=True)
            card.pack_start(self.w["endless_off"], False, False, 0)
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
            row.set_halign(Gtk.Align.CENTER)
            ring = Gtk.DrawingArea()
            ring.set_size_request(self.RING, self.RING)
            ring.set_valign(Gtk.Align.CENTER)
            ring.connect("draw", self._draw_ring)
            self.w["ring"] = ring
            row.pack_start(ring, False, False, 0)
            self.w["chips"] = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            self.w["chips"].set_valign(Gtk.Align.CENTER)
            row.pack_start(self.w["chips"], True, True, 0)
            self.w["endless_row"] = row
            card.pack_start(row, False, False, 0)
        body.pack_start(card, False, False, 0)

    def _draw_ring(self, widget, cr):
        size = float(self.RING)
        c = size / 2.0
        R = c - 2
        r = R * 0.62
        n = NTOOLS
        keys, loaded = self._endless_keys(), self._endless_loaded()
        sets = L.endless_sets(keys)
        active = self._active_tool() if self._busy() else -1
        shift = -math.pi / 2          # the circle starts at the top, clockwise (as the Fluidd graph)
        cr.select_font_face("Sans", 0, 1)
        cr.set_font_size(max(14, int(self.RING * 0.14)))      # F-194: bigger tool numbers
        for i in range(n):
            a0 = i * 2 * math.pi / n + 0.04
            a1 = (i + 1) * 2 * math.pi / n - 0.04
            col = self._tool_info(i)["color"]
            red, green, blue = (col >> 16 & 255) / 255.0, (col >> 8 & 255) / 255.0, (col & 255) / 255.0
            cr.new_path()
            cr.arc(c, c, R, a0 + shift, a1 + shift)
            cr.arc_negative(c, c, r, a1 + shift, a0 + shift)
            cr.close_path()
            cr.set_source_rgba(red, green, blue, 0.28 if loaded[i] is False else 1.0)
            if i == active:
                cr.fill_preserve()
                cr.set_source_rgb(1, 1, 1)
                cr.set_line_width(2)
                cr.stroke()
            else:
                cr.fill()
            mid = (a0 + a1) / 2.0
            tx, ty = c + (R + r) / 2.0 * math.sin(mid), c - (R + r) / 2.0 * math.cos(mid)
            label = "T%d" % (i + 1)
            ext = cr.text_extents(label)
            cr.move_to(tx - ext[2] / 2.0 - ext[0], ty + 4.5)
            cr.text_path(label)
            cr.set_source_rgb(0, 0, 0)
            cr.set_line_width(3)
            cr.stroke_preserve()
            cr.set_source_rgb(1, 1, 1)
            cr.fill()
        rr = r - 7
        cr.set_line_width(3)
        cr.set_line_cap(1)
        for s in sets:
            for k in range(len(s) - 1):
                m0 = (s[k] + 0.5) * 2 * math.pi / n
                m1 = (s[k + 1] + 0.5) * 2 * math.pi / n
                cr.set_source_rgb(0.208, 0.769, 0.416)
                cr.new_path()
                cr.arc(c, c, rr, m0 + shift, m1 + shift)
                cr.stroke()
                for m in (m0, m1):
                    cr.new_path()
                    cr.arc(c + rr * math.sin(m), c - rr * math.cos(m), 4, 0, 2 * math.pi)
                    cr.fill()
        return False

    def _endless_chips(self):
        """(heads, material, note, kind, colour, faded) like the chips of the Fluidd card."""
        keys, loaded = self._endless_keys(), self._endless_loaded()
        sets = L.endless_sets(keys)
        if not sets:
            return []
        t = lambda i: "T%d" % (i + 1)
        busy = self._busy()
        active = self._active_tool() if busy else -1
        w = self.st.get("gcode_macro _WM_ENDLESS") or {}
        try:
            wfrom, wto = int(w.get("from", -1)), int(w.get("to", -1))
        except (TypeError, ValueError):
            wfrom, wto = -1, -1
        fname = str((self.st.get("print_stats") or {}).get("filename", ""))
        swapped = busy and wfrom >= 0 and wto == active and str(w.get("swap_file", "")) == fname
        chips = []
        color = lambda i: "#%06X" % (self._tool_info(i)["color"] & 0xFFFFFF)
        for s in sets:
            col = color(s[0])
            mat = self._mat_name(s[0])
            empty = [i for i in s if loaded[i] is False]
            if active in s:
                nxt = L.endless_next(active, keys, loaded)
                if loaded[active] is False and not nxt:
                    chips.append((", ".join(t(i) for i in s), "", "all empty, print paused", "warn", col, True))
                    continue
                lead = "%s \u2192 %s" % (t(wfrom), t(active)) if swapped else t(active)
                note = "printing, next: " + ", then ".join(t(i) for i in nxt) if nxt else "printing, no spare left"
                chips.append((lead, "", note, "ok" if nxt else "warn", col, False))
            else:
                ready = [i for i in s if loaded[i] is not False]
                if len(ready) > 1:
                    chips.append((("  \u21C4  " if len(ready) == 2 else "  \u2192  ").join(t(i) for i in ready), mat, "identical", "plain", col, False))
                elif len(ready) == 1:
                    chips.append((t(ready[0]), mat, "no spare left", "warn", col, False))
            others = [i for i in empty if i != active]
            if others:
                chips.append((", ".join(t(i) for i in others), "", "empty, refill", "warn", col, True))
        for i in range(NTOOLS):
            if not any(i in s for s in sets):
                chips.append((t(i), "", "no spare", "plain", color(i), False))
        return chips

    def _refresh_endless(self):
        if "endless_row" not in self.w:
            return
        v = self._vars()
        on = L.endless_enabled(v)
        self._set_switch("sw_endless", on)
        self._set_switch("sw_auto", L.endless_auto(v))
        self.w["auto_box"].set_visible(on)
        self.w["endless_row"].set_visible(on)
        self.w["endless_off"].set_visible(not on)
        if not on:
            return
        self.w["ring"].queue_draw()
        box = self.w["chips"]
        for ch in box.get_children():
            box.remove(ch)
        chips = self._endless_chips()
        if not chips:
            lbl = self._label("No two toolheads have the same material and colour. A runout pauses the print.", "zr_hint", wrap=True)
            box.pack_start(lbl, False, False, 0)
        kind_col = {"ok": "#35c46a", "warn": "#f0a030", "plain": "#aab4be"}
        for heads, mat, note, kind, col, faded in chips:
            lbl = Gtk.Label()
            lbl.set_xalign(0)
            lbl.set_markup('<span foreground="%s" alpha="%s" size="x-large">\u25CF</span> <span size="x-large"><b>%s</b></span> %s <span foreground="%s">%s</span>' % (
                col, "35%" if faded else "100%", GLib.markup_escape_text(heads), GLib.markup_escape_text(mat),
                kind_col[kind], GLib.markup_escape_text(note)))
            box.pack_start(lbl, False, False, 0)
        box.show_all()

    # ------------------------------------------------------------------
    # F-137: nozzle heat growth page (on/off switch; the measurement is started from here)
    # ------------------------------------------------------------------
    def show_growth(self):
        self.view = "growth"
        self._clear()
        self.root.pack_start(self._header("Nozzle heat growth"), False, False, 0)
        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        card.get_style_context().add_class("zr_card")
        card.set_border_width(10)
        texts = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        title = self._label()
        title.set_markup("<b>Heat growth correction</b>")
        texts.pack_start(title, False, False, 0)
        self.w["gr_sub"] = self._label("", "zr_small", wrap=True)
        texts.pack_start(self.w["gr_sub"], False, False, 0)
        card.pack_start(texts, True, True, 0)
        card.pack_end(self._switch("sw_growth", self._growth_set), False, False, 0)
        body.pack_start(card, False, False, 0)
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row.set_homogeneous(True)
        b1 = self._button("heat-up", "Measure again", "color1", self._utility, "Measure heat growth", "WM_NOZZLE_GROWTH_CAL", None)
        b2 = self._button("info", "Show value", "color3", self._gcode, "WM_NOZZLE_GROWTH", None)
        for b in (b1, b2):
            b.set_size_request(-1, self.sz["tile_h"])
            row.pack_start(b, True, True, 0)
        body.pack_start(row, False, False, 0)
        body.pack_start(self._label("Corrects the first layer height of every tool for the nozzle growing with heat. "
                                    "It can only be switched on after a measurement, and not while printing.",
                                    "zr_hint", wrap=True), False, False, 0)
        self.root.pack_start(self._scrolled(body), True, True, 0)
        self.root.show_all()
        self._refresh_growth()

    def _growth_set(self, on):
        if not self._require_idle():
            self.__dict__.setdefault("_sw_hold", {}).pop("sw_growth", None)
            self._refresh_growth()
            return
        self._gcode("SET_PIN PIN=Nozzle_Heat_Growth VALUE=%d" % (1 if on else 0), "Nozzle heat growth %s" % ("on" if on else "off"))

    def _refresh_growth(self):
        if "sw_growth" not in self.w:
            return
        pin = self._pin_value("Nozzle_Heat_Growth")
        self.w["sw_growth"].set_sensitive(pin is not None)
        if pin is not None:
            self._set_switch("sw_growth", pin)
        try:
            sv = self._vars()
            g = float(sv.get("wm_nozzle_growth_meas", 0) or 0) or float(sv.get("wm_nozzle_growth", 0) or 0)     # the measured value stays when the switch is off
        except (TypeError, ValueError):
            g = 0.0
        if pin is None:
            txt = "Not on this printer (rpi_zoffset.cfg)."
        elif g:
            txt = "Measured %.4f mm per degree. The value is kept when the switch is off." % g
        else:
            txt = "Not measured yet. Use Measure again first."
        self.w["gr_sub"].set_text(txt)

    # ------------------------------------------------------------------
    # F-137: Klipper offline: banner, greyed page, restart buttons and the system menu of KlipperScreen
    # ------------------------------------------------------------------
    def _offline(self):
        st = getattr(self._screen, "state", None)
        if st is None:
            return False
        return (not getattr(st, "initialized", True)) or (not getattr(st, "connected", True))

    def _update_offline(self):
        off = self._offline()
        if off == getattr(self, "_off_shown", False):
            if off and self.nav is not None and self.nav.get_visible():
                self.nav.hide()
            return
        self._off_shown = off
        if off:
            self._build_offline_ui()
        else:
            self._remove_offline_ui()

    def _build_offline_ui(self):
        st = self._screen.state
        txt = "Moonraker not connected: retrying" if not getattr(st, "connected", True) else "Klipper is not ready (restarting or in error)"
        banner = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        banner.pack_start(self._pill(txt, "off"), True, True, 0)
        banner.pack_end(self._button("refresh", "Retry now", "color1", self._retry_now), False, False, 0)
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        bar.set_homogeneous(True)
        for icon, text, style, cb in (("refresh", "Klipper Restart", "color1", self._klipper_restart),
                                      ("refresh", "Firmware Restart", "color2", self._firmware_restart),
                                      ("settings", "System menu", "color3", self._open_system_menu)):
            b = self._button(icon, text, style, cb)
            b.set_size_request(-1, self.sz["nav_h"])
            bar.pack_start(b, True, True, 0)
        self.outer.pack_start(banner, False, False, 0)
        self.outer.reorder_child(banner, 0)
        self.outer.pack_end(bar, False, False, 0)
        self._off_widgets = [banner, bar]
        self.root.set_sensitive(False)
        if self.nav is not None:
            self.nav.hide()
        banner.show_all()
        bar.show_all()

    def _remove_offline_ui(self):
        for wdg in getattr(self, "_off_widgets", []):
            self.outer.remove(wdg)
            wdg.destroy()
        self._off_widgets = []
        self.root.set_sensitive(True)
        if self.nav is not None:
            self.nav.show_all()

    def _retry_now(self):
        try:
            s = self._screen
            s.state.reinit_count = 0
            s.state.klippy_retry_count = 0
            s._init_printer("Connecting to %s" % s.state.printer_name)
        except Exception as e:
            logging.error("ZR: retry failed: %s" % e)

    def _klipper_restart(self):
        try:
            self._screen._ws.api.restart()
        except Exception as e:
            logging.error("ZR: klipper restart failed: %s" % e)
            self._screen.show_popup_message("Cannot reach Moonraker")

    def _firmware_restart(self):
        try:
            self._screen._ws.api.restart_firmware()
        except Exception as e:
            logging.error("ZR: firmware restart failed: %s" % e)
            self._screen.show_popup_message("Cannot reach Moonraker")

    def _open_system_menu(self):
        try:
            items = self._screen._config.get_menu_items("__splashscreen", "")
            self._screen.show_panel("menu", "System", panel_name="", items=items)
        except Exception as e:
            logging.error("ZR: system menu failed: %s" % e)
            self._screen.show_popup_message("System menu not available")
