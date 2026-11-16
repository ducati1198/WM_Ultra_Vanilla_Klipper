# WonderMaker: Sensors page. Every filament_switch_sensor of the printer with a friendly label, the real Klipper
# name under it, and its state. On a ZR Ultra the sensors of the tool changer get friendly labels (the same as in Fluidd).
import json
import logging
import re
import threading
import urllib.parse
import urllib.request

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk, Pango

from ks_includes.screen_panel import ScreenPanel


def wm_sensor_label(name, is_zr):
    """(friendly label, sort order) of a sensor name, or (None, 200) when it has no friendly label."""
    if is_zr:
        m = re.match(r"^filament([0-3])$", name)
        if m:
            return f"T{m.group(1)} head filament", int(m.group(1)) * 10
        m = re.match(r"^path_([0-3])$", name)
        if m:
            return f"T{m.group(1)} hub filament", int(m.group(1)) * 10 + 1
        m = re.match(r"^docked([0-3])$", name)
        if m:
            return f"T{m.group(1)} in dock", int(m.group(1)) * 10 + 2
        if name == "sensor_b":
            return "Tool lock", 100
        if name == "sensor_a":
            return "Lock motor home", 101
    return None, 200


def wm_is_zr(sensors):
    return "filament_switch_sensor docked0" in sensors and "filament_switch_sensor filament0" in sensors


def wm_sensors_sync(panel, done=None):
    """Read the real state of every filament sensor from Moonraker and put it into KlipperScreen's data.
    KlipperScreen can miss the first state after a Klipper restart: it asks once while the sensors still report
    nothing, and a sensor that does not change afterwards never sends an update."""
    sensors = list(panel._printer.get_filament_sensors())
    ws = getattr(panel._screen, "_ws", None)
    host, port = getattr(ws, "host", None), getattr(ws, "port", None)
    if not sensors or not isinstance(host, str) or not host or not port:
        return
    url = "%s://%s:%s/printer/objects/query?%s" % (
        "https" if getattr(ws, "ssl", False) else "http", host, port,
        "&".join(urllib.parse.quote(x) for x in sensors))

    def work():
        status = None
        try:
            with urllib.request.urlopen(url, timeout=4) as r:
                status = json.loads(r.read().decode("utf-8", "replace"))["result"]["status"]
        except Exception as e:
            logging.debug(f"WM sensors: not read: {e}")
        GLib.idle_add(finish, status)

    def finish(status):
        try:
            if isinstance(status, dict):
                panel._printer.process_update(status)
                if done is not None:
                    done()
        except Exception:
            logging.exception("WM sensors: sync")
        return False

    threading.Thread(target=work, daemon=True).start()


class Panel(ScreenPanel):
    def __init__(self, screen, title):
        title = title or "Sensors"
        super().__init__(screen, title)
        sensors = list(self._printer.get_filament_sensors())
        is_zr = wm_is_zr(sensors)
        rows = []
        for x in sensors:
            name = x.split(" ", 1)[1].strip()
            label, order = wm_sensor_label(name, is_zr)
            rows.append((order, label or self.prettify(name), name, x, label is not None))
        rows.sort(key=lambda r: (r[0], r[2]))
        self.rows = {}
        grid = Gtk.Grid(column_homogeneous=True, row_spacing=6, column_spacing=10)
        grid.set_margin_start(8)
        grid.set_margin_end(8)
        grid.set_margin_top(6)
        cols = 1 if self._screen.vertical_mode else 2
        per_col = (len(rows) + cols - 1) // cols
        for i, (_order, label, name, x, friendly) in enumerate(rows):
            title_l = Gtk.Label(halign=Gtk.Align.START, ellipsize=Pango.EllipsizeMode.END)
            title_l.set_markup(f"<b>{label}</b>")
            text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, valign=Gtk.Align.CENTER)
            text.add(title_l)
            if friendly:
                real = Gtk.Label(halign=Gtk.Align.START)
                real.set_markup(f"<small>{name}</small>")
                text.add(real)
            state = Gtk.Label(label="-", width_chars=9)
            pill = Gtk.Box(valign=Gtk.Align.CENTER)
            pill.pack_start(state, True, True, 8)
            pill.get_style_context().add_class("filament_sensor")
            row = Gtk.Box(spacing=8)
            row.pack_start(text, True, True, 0)
            row.pack_start(pill, False, False, 0)
            self.rows[x] = {"state": state, "pill": pill}
            grid.attach(row, i // per_col if per_col else 0, i % per_col if per_col else i, 1, 1)
        scroll = self._gtk.ScrolledWindow()
        scroll.add(grid)
        self.content.add(scroll)
        self.refresh_all()

    def refresh_all(self):
        for x in self.rows:
            self.set_row(x)

    def set_row(self, x):
        row = self.rows.get(x)
        if row is None:
            return
        enabled = self._printer.get_stat(x, "enabled")
        detected = self._printer.get_stat(x, "filament_detected")
        shown = (enabled is False, bool(detected))
        if row.get("shown") == shown:
            return
        row["shown"] = shown
        ctx = row["pill"].get_style_context()
        ctx.remove_class("filament_sensor_detected")
        ctx.remove_class("filament_sensor_empty")
        if enabled is False:
            row["state"].set_markup(f"<small>{'on' if detected else 'off'} (disabled)</small>")
        elif detected:
            row["state"].set_label("on")
            ctx.add_class("filament_sensor_detected")
        else:
            row["state"].set_label("off")
            ctx.add_class("filament_sensor_empty")

    def activate(self):
        self.refresh_all()
        wm_sensors_sync(self, self.refresh_all)

    def process_update(self, action, data):
        if action != "notify_status_update":
            return
        for x in self.rows:
            if x in data:
                self.set_row(x)
