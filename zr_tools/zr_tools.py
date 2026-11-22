# ZR Tools - KlipperScreen panel for the WonderMaker ZR Ultra-S (4 toolheads)
# Version 1
#
# Install:  copy to ~/KlipperScreen/panels/zr_tools.py
# Needs:    zr_tools.cfg included in printer.cfg
# Menu:     see KlipperScreen.conf snippet in INSTALL.md
#
# Data comes from Klipper/Moonraker (printer.objects.query, polled every 2 s
# while the panel is visible). Filament info is stored in save_variables:
#   zr_t<N>_color (int 0xRRGGBB), zr_t<N>_mat (index in MATERIALS),
#   zr_t<N>_temp (C), t<N>_pressure_advance (WonderMaker's own variable)
# Tool mapping uses WonderMaker's own box_modify_t<N> variables.

import colorsys
import cairo
import json
import logging
import math
import threading
import time
import urllib.request
import uuid

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib, Pango  # noqa: E402

from ks_includes.screen_panel import ScreenPanel  # noqa: E402

try:                                   # KlipperScreen loads panels as "panels.<name>"
    from panels import zr_logic as L  # noqa: E402
    from panels.zr_views import ViewsMixin  # noqa: E402
except ImportError:                    # tests import the files from this folder
    import zr_logic as L  # noqa: E402
    from zr_views import ViewsMixin  # noqa: E402

NTOOLS = 4
POLL_SECONDS = 2

# (name, default nozzle temperature)
MATERIALS = [
    ("Empty", 0),
    ("PLA", 210),
    ("PLA+", 215),
    ("PLA Silk", 215),
    ("PLA Matte", 210),
    ("PLA-CF", 220),
    ("PETG", 240),
    ("PETG-CF", 245),
    ("ABS", 250),
    ("ASA", 255),
    ("TPU", 220),
    ("PA / Nylon", 270),
    ("PC", 270),
    ("PVA", 195),
    ("HIPS", 235),
    ("Other", 220),
]

COLOR_PRESETS_TOUCH = L.TOUCH_PALETTE        # same swatches, same order as the Fluidd panel and the touchscreen
# F-201: three more swatches fill the empty places of the last row of the editor (the 21 touchscreen swatches above keep their
# order and indexes, tmt1.ini snaps these three to the closest touchscreen swatch; the exact colour is kept in zr_tN_color)
EXTRA_PRESETS = [("Purple", 0x7B3FCE), ("Teal", 0x1A9C9C), ("Maroon", 0x8B1A1A)]
COLOR_PRESETS = list(COLOR_PRESETS_TOUCH) + EXTRA_PRESETS

CHAMBER_MAX = 65


def _rgb(color_int):
    color_int = int(color_int or 0) & 0xFFFFFF
    return (color_int >> 16) & 0xFF, (color_int >> 8) & 0xFF, color_int & 0xFF


def _color_name(color_int):
    """Name of the colour (exact match in the Orca lists), else the closest preset name, else the hex code."""
    want = int(color_int or 0) & 0xFFFFFF
    for _lname, _items in L.COLOR_LISTS:
        for _n, _c in _items:
            if _c == want:
                return _n
    best, dist = None, 10 ** 9
    r, g, b = _rgb(color_int)
    for name, col in COLOR_PRESETS:
        cr, cg, cb = _rgb(col)
        d = (r - cr) ** 2 + (g - cg) ** 2 + (b - cb) ** 2
        if d < dist:
            best, dist = name, d
    return best if dist < 3000 else "#%06X" % (color_int & 0xFFFFFF)


def _hex_to_int(v):
    try:
        return int(str(v).strip().lstrip("#")[:6], 16)
    except (TypeError, ValueError):
        return None


def _meta_list(v):
    if isinstance(v, (list, tuple)):
        return list(v)
    if not isinstance(v, str):
        return []
    t = v.strip()
    if t.startswith("["):
        try:
            x = json.loads(t)
            if isinstance(x, list):
                return x
        except ValueError:
            pass
    return t.replace(";", ",").split(",")


def file_colours(meta):
    """F-208: the colours of a G-code file from the Moonraker metadata (the same keys the Fluidd Choose toolheads window reads).
    [{'tool': 0, 'color': 0xRRGGBB, 'mat': 'PLA'}, ...] for the tools the file really uses; [] when the file has no colour data."""
    meta = meta or {}
    cols = [_hex_to_int(x) for x in _meta_list(meta.get("preset_colours") or meta.get("filament_colors"))]
    if not cols:
        return []
    types = [str(x).strip() for x in _meta_list(meta.get("filament_type"))]
    used = []
    for x in _meta_list(meta.get("filament_used_g")):
        try:
            used.append(float(x))
        except (TypeError, ValueError):
            used.append(None)
    ref = meta.get("referenced_tools")
    ref = ref if isinstance(ref, list) and ref else None
    out = []
    for t, c in enumerate(cols):
        if c is None or t >= NTOOLS:
            continue
        if ref is not None:
            ok = t in ref
        elif t < len(used) and used[t] is not None:
            ok = used[t] > 0
        else:
            ok = True
        if ok:
            out.append({"tool": t, "color": c, "mat": types[t] if t < len(types) else ""})
    return out


def _ext_name(tool):
    return "extruder" if tool == 0 else f"extruder{tool}"


def _tool_from_ext(name):
    if not name or not str(name).startswith("extruder"):
        return -1
    suffix = str(name)[len("extruder"):]
    if suffix == "":
        return 0
    try:
        return int(suffix)
    except ValueError:
        return -1


BIG_H = 78       # height of the Yes / Cancel and the big tiles = the buttons of the Bed PID window


class Panel(ViewsMixin, ScreenPanel):

    # F-137: page history, so the Back button of KlipperScreen goes to the page you came from
    @property
    def view(self):
        return self.__dict__.get("_view_v", "main")

    @view.setter
    def view(self, value):
        old = self.__dict__.get("_view_v")
        if old is not None and old != value and not self.__dict__.get("_navback"):
            h = self.__dict__.setdefault("_hist", [])
            h.append((old, self.__dict__.get("view_tool", 0)))
            del h[:-12]
        self.__dict__["_view_v"] = value

    def __init__(self, screen, title):
        super().__init__(screen, title)
        self._install_banner_fix()      # F-197
        self.view = "main"
        self.view_tool = 0
        self._timer = None
        self.st = {}          # last status received from Klipper
        self.w = {}           # widgets of the current view
        self.edit = None      # tool being edited: dict(color, mat, temp, pa)
        self._tmt1 = []       # [slot] colours and materials from tmt1.ini (shared with Fluidd)
        self._tmt1_text = ''
        self._tmt1_busy = False
        self.settings = L.load_settings()
        self.nav_btns = {}
        self.outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.nav = None
        self.outer.set_vexpand(True)
        self.outer.set_valign(Gtk.Align.FILL)
        self.content.set_vexpand(True)
        if hasattr(self.content, "pack_start"):
            self.content.pack_start(self.outer, True, True, 0)
        else:
            self.content.add(self.outer)
        self.outer.pack_start(self.root, True, True, 0)
        self._apply_settings()
        self.show_home()

    # ------------------------------------------------------------------
    # layout shell: A = card grid hub, C = big touch with a bottom tab bar
    # ------------------------------------------------------------------
    def _apply_settings(self):
        width, height = getattr(self._screen, "width", 0), getattr(self._screen, "height", 0)
        self.portrait = self._is_portrait(width, height)
        self.density = L.resolve_density(self.settings["density"], width, height)
        self.sz = L.sizes(self.density, self.portrait, width, height)
        self.scale, self.tiny = self.sz["scale"], self.sz["tiny"]
        self._add_css()
        if self.nav is not None:
            self.outer.remove(self.nav)
            self.nav = None
        if self.settings["layout"] == "tabs":
            self.nav = self._make_nav()
            self.outer.pack_end(self.nav, False, False, 0)
            self.nav.show_all()

    @staticmethod
    def _is_portrait(width, height):
        """Tall screen (480x800, 600x1024)?"""
        return bool(L.screen_profile(width, height)["portrait"])

    def _nav_entries(self):
        e = [("toolchanger", "Toolheads", self.show_main, ("main",)),
             ("filament", "Filament", self.show_filament, ("tool", "tool_edit", "color_pick", "hsv_pick")),
             ("heat-up", "Climate", self.show_chamber, ("chamber",))]
        if not self.tiny:            # on a 3 to 4 inch screen Calibrate moves into More to keep the tabs big enough to hit
            e.append(("settings", "Tools", self.show_utilities, ("utilities", "cal_cat", "growth")))
        if L.has_ace(self.st):
            e.append(("spool", "ACE", self.show_ace, ("ace", "ace_feed", "ace_endless", "ace_dryer")))
        more = ("more", "hub", "collision", "extras", "system", "settings", "mapping")
        e.append(("main", "More", self.show_more, more + (("utilities", "cal_cat") if self.tiny else ())))
        return e

    def _make_nav(self):
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        bar.set_homogeneous(True)
        self.nav_btns = {}
        for icon, label, cb, views in self._nav_entries():
            b = self._tab_button(icon, L.short_label(label, self.portrait, self.density), cb)
            b.set_size_request(-1, self.sz["nav_h"])
            bar.pack_start(b, True, True, 0)
            self.nav_btns[label] = (b, views)
        return bar

    def _mark_nav(self):
        for label, (b, views) in self.nav_btns.items():
            ctx = b.get_style_context()
            if self.view in views:
                ctx.add_class("zr_selected")
            else:
                ctx.remove_class("zr_selected")

    def _rebuild_nav_if_needed(self):
        """The ACE tab appears as soon as an ACE shows up in the printer data."""
        if self.nav is not None and ("ACE" in self.nav_btns) != L.has_ace(self.st):
            self._apply_settings()

    def _home_view(self):
        return "main" if self.settings["layout"] == "tabs" else "hub"

    def show_home(self):
        if self.settings["layout"] == "tabs":
            self.show_main()
        else:
            self.show_hub()

    # ------------------------------------------------------------------
    # lifecycle
    # ------------------------------------------------------------------
    def activate(self):
        self._update_offline()
        self._query()
        if self._timer is None:
            self._timer = GLib.timeout_add_seconds(POLL_SECONDS, self._poll)
        pend = getattr(self._screen, "zr_pending_print", None)
        if pend:                                  # F-208: a print was started from the screen: choose the toolheads first
            self._screen.zr_pending_print = None
            self._map_begin(pend)
        elif self.view == "map_start":            # the page was left with Back
            self.show_home()

    def deactivate(self):
        if self._timer is not None:
            GLib.source_remove(self._timer)
            self._timer = None

    def _view_fn(self, v):
        m = {"main": self.show_main, "hub": self.show_hub, "more": self.show_more, "chamber": self.show_chamber,
             "ace": self.show_ace, "ace_feed": self.show_ace_feed, "ace_endless": self.show_ace_endless, "ace_dryer": self.show_ace_dryer, "utilities": self.show_utilities, "cal_cat": self.show_cal_cat, "collision": self.show_collision,
             "extras": self.show_extras, "system": self.show_system, "settings": self.show_settings,
             "mapping": self.show_mapping, "map_start": self.show_map_start, "growth": self.show_growth, "unload": self.show_unload, "load": self.show_load, "resume_tool": self.show_resume_tool, "resume_tool2": self.show_resume_tool2, "resume_confirm": self.show_resume_confirm,
             "purge": lambda: self.show_purge(self.view_tool),
             "tool": lambda: self.show_tool(self.view_tool), "tool_edit": lambda: self.show_tool_edit(self.view_tool), "color_pick": lambda: self.show_color_pick(), "hsv_pick": lambda: self.show_hsv_pick()}
        return m.get(v)

    def back(self, widget=None):
        """KlipperScreen calls back() on the Back button: True = handled here, False = KlipperScreen goes to its own previous page."""
        if self._offline():
            return False
        if self.view == "map_start":         # F-208: Back on the Choose toolheads page = cancel, back to the page it was opened from
            self.__dict__["_hist"] = []
            self.__dict__["map_file"] = None
            return False
        if self.view == "purge" and not self.__dict__.pop("_purge_quiet", False):
            self._purge_finish()
        h = self.__dict__.setdefault("_hist", [])
        self.__dict__["_navback"] = True
        try:
            while h:
                v, tool = h.pop()
                fn = self._view_fn(v)
                if fn is None:
                    continue
                if v in ("tool", "tool_edit", "color_pick", "hsv_pick"):
                    self.view_tool = tool
                fn()
                return True
            if self.view != self._home_view():
                self.show_home()
                return True
        finally:
            self.__dict__["_navback"] = False
        return False

    on_back = back

    def process_update(self, action, data):
        # Global KlipperScreen subscription (temperatures, toolhead ...).
        if action != "notify_status_update" or not isinstance(data, dict):
            return
        payload = data.get("status") if isinstance(data.get("status"), dict) else data
        changed = False
        for key, val in payload.items():
            if isinstance(val, dict) and key in self._objects():
                self.st.setdefault(key, {}).update(val)
                changed = True
        if changed:
            self._refresh_view()

    # ------------------------------------------------------------------
    # Klipper communication
    # ------------------------------------------------------------------
    def _objects(self):
        objs = {
            "toolhead": ["extruder", "homed_axes"],
            "print_stats": ["state", "filename"],
            "output_pin ACE_Pro": ["value"],
            "output_pin Nozzle_Heat_Growth": ["value"],
            "gcode_macro _WM_ENDLESS": None,
            "gcode_macro _WM_UNLOAD": None,
            "gcode_macro _WM_PURGE_SEL": None,
            "gcode_macro _WM_ENDLESS_CONTINUE": None,
            "gcode_macro RESUME": None,           # F-166: the print's resume temperatures (Resume tool screen)
            "gcode_macro _WM_LOAD": None,
            "save_variables": ["variables"],
            "heater_generic chamber": ["temperature", "target"],
            "fan_generic air_fan": ["speed"],
            "gcode_button Door_button1": ["state"],
            "gcode_button Door_button2": ["state"],
            "ace_instance_0": None,
            "gcode_macro _WM_ACE": None,
        }
        for i in range(NTOOLS):
            objs[_ext_name(i)] = ["temperature", "target", "pressure_advance"]
            objs[f"filament_switch_sensor filament{i}"] = ["filament_detected"]
            objs[f"filament_switch_sensor docked{i}"] = ["filament_detected"]
            objs[f"filament_switch_sensor path_{i}"] = ["filament_detected"]
        return objs

    def _ws(self):
        ws = getattr(self._screen, "_ws", None)
        if callable(getattr(ws, "send_method", None)):
            return ws
        inner = getattr(getattr(ws, "klippy", None), "_ws", None)
        if callable(getattr(inner, "send_method", None)):
            return inner
        return None

    def _poll(self):
        self._query()
        self._update_offline()
        return True

    def _http_base(self):
        ws = getattr(self._screen, "_ws", None)
        host, port = getattr(ws, "host", None), getattr(ws, "port", None)
        if not isinstance(host, str) or not host or not port:
            return None
        return "%s://%s:%s" % ("https" if getattr(ws, "ssl", False) else "http", host, port)

    def _fetch_tmt1(self):
        """Read tmt1.ini from Moonraker (in a thread, the screen must not wait for it)."""
        base = self._http_base()
        if base is None or self._tmt1_busy:
            return
        self._tmt1_busy = True

        def work():
            try:
                with urllib.request.urlopen(base + "/server/files/config/tmt1.ini", timeout=4) as r:
                    text = r.read().decode("utf-8", "replace")
                GLib.idle_add(self._set_tmt1, text)
            except Exception as e:
                logging.debug(f"ZR: tmt1.ini not read: {e}")
            finally:
                self._tmt1_busy = False
        threading.Thread(target=work, daemon=True).start()

    def _set_tmt1(self, text):
        self._tmt1_text = text
        self._tmt1 = L.parse_tmt1_slots(text, NTOOLS)
        self._refresh_view()
        return False

    def _write_tmt1(self, index, color_idx, mat_idx):
        """Change one slot in tmt1.ini so Fluidd and the touchscreen see it. Re-reads first, keeps every other line."""
        base = self._http_base()
        if base is None:
            return

        def work():
            try:
                with urllib.request.urlopen(base + "/server/files/config/tmt1.ini", timeout=4) as r:
                    cur = r.read().decode("utf-8", "replace")
                new = L.update_tmt1_slot(cur, index, color_idx, mat_idx)
                if new != cur:
                    b = uuid.uuid4().hex
                    body = (f'--{b}\r\nContent-Disposition: form-data; name="root"\r\n\r\nconfig\r\n'
                            f'--{b}\r\nContent-Disposition: form-data; name="file"; filename="tmt1.ini"\r\n'
                            f'Content-Type: text/plain\r\n\r\n').encode() + new.encode() + f"\r\n--{b}--\r\n".encode()
                    req = urllib.request.Request(base + "/server/files/upload", body,
                                                 {"Content-Type": "multipart/form-data; boundary=" + b})
                    urllib.request.urlopen(req, timeout=6).read()
                GLib.idle_add(self._set_tmt1, new)
            except Exception as e:
                logging.error(f"ZR: could not write tmt1.ini: {e}")
                GLib.idle_add(self._screen.show_popup_message, "Could not share the colour with Fluidd (tmt1.ini).")
        threading.Thread(target=work, daemon=True).start()

    def _query(self):
        self._fetch_tmt1()
        ws = self._ws()
        if ws is None:
            return
        try:
            ws.send_method("printer.objects.query",
                           {"objects": self._objects()}, self._on_query)
        except Exception as e:
            logging.debug(f"ZR: query failed: {e}")

    def _on_query(self, response, *_):
        try:
            result = response or {}
            if isinstance(result, dict) and "result" in result:
                result = result["result"] or {}
            status = result.get("status", {}) if isinstance(result, dict) else {}
            if isinstance(status, dict) and status:
                GLib.idle_add(self._apply_status, status)
        except Exception as e:
            logging.debug(f"ZR: bad query response: {e}")

    def _apply_status(self, status):
        self.__dict__["_status_seq"] = self.__dict__.get("_status_seq", 0) + 1       # F-208: lets the Choose toolheads page know the data is fresh
        for key, val in status.items():
            if isinstance(val, dict):
                self.st.setdefault(key, {}).update(val)
        if "gcode_macro _WM_PURGE_SEL" in status:
            self._purge_sync()               # the purge window was closed in Fluidd: close this page too
        self._refresh_view()
        return False

    def _gcode(self, script, message=None):
        try:
            ws = self._screen._ws
            api = getattr(ws, "api", None)           # current KlipperScreen
            if api is None or not callable(getattr(api, "gcode_script", None)):
                api = getattr(ws, "klippy", None)    # older KlipperScreen
            if api is not None and callable(getattr(api, "gcode_script", None)):
                api.gcode_script(script)
            elif ws.send_method("printer.gcode.script", {"script": script}) is False:
                raise RuntimeError("not connected to Moonraker")
            if message:
                self._screen.show_popup_message(message, 1)
            GLib.timeout_add(800, self._query_once)
            return True
        except Exception as e:
            logging.error(f"ZR: gcode '{script}' failed: {e}")
            self._screen.show_popup_message("Connection error. Check Klipper.")
            return False

    def _query_once(self):
        self._query()
        return False

    # ------------------------------------------------------------------
    # state helpers
    # ------------------------------------------------------------------
    def _vars(self):
        return (self.st.get("save_variables") or {}).get("variables") or {}

    def _print_state(self):
        return (self.st.get("print_stats") or {}).get("state", "")

    def _busy(self):
        return self._print_state() in ("printing", "paused")

    def _active_tool(self):
        # WonderMaker keeps the tool on the carriage in current_extruder
        # (99 = no toolhead on the carriage). Fall back to Klipper's
        # active extruder if the variable is missing.
        cur = self._vars().get("current_extruder")
        try:
            cur = int(cur)
            if 0 <= cur < NTOOLS:
                return cur
            if cur == 99:
                return -1
        except (TypeError, ValueError):
            pass
        return _tool_from_ext((self.st.get("toolhead") or {}).get("extruder"))

    def _mat_name(self, i):
        m = self._tool_info(i)["mat"]
        return MATERIALS[m][0] if 0 <= m < len(MATERIALS) else ""

    def _tool_info(self, i):
        v = self._vars()
        slot = self._tmt1[i] if i < len(self._tmt1) else {}
        if f"zr_t{i}_mat" in v:
            mat = int(v.get(f"zr_t{i}_mat", 0) or 0)
        elif slot.get("material") is not None:
            mat = L.TOUCH_MATERIALS[slot["material"]][2]
        else:
            mat = 0
        if mat < 0 or mat >= len(MATERIALS):
            mat = 0
        if slot.get("color") is not None:      # tmt1.ini is shared with Fluidd and the touchscreen
            color = L.TOUCH_PALETTE[slot["color"]][1]
        else:
            color = int(v.get(f"zr_t{i}_color", 0x404040) or 0)
        return {
            "color": color,
            "mat": mat,
            "temp": int(v.get(f"zr_t{i}_temp", MATERIALS[mat][1] or 220) or 0),
            "pa": float(v.get(f"t{i}_pressure_advance", 0.04) or 0.0),
        }

    def _temps(self, i):
        e = self.st.get(_ext_name(i)) or {}
        return e.get("temperature"), e.get("target")

    def _sensor(self, name):
        s = self.st.get(f"filament_switch_sensor {name}")
        if not isinstance(s, dict) or "filament_detected" not in s:
            return None
        return bool(s["filament_detected"])

    def _mapping(self):
        v = self._vars()
        out = []
        for t in range(NTOOLS):
            try:
                out.append(int(v.get(f"box_modify_t{t}", t)))
            except (TypeError, ValueError):
                out.append(t)
        return out

    # ------------------------------------------------------------------
    # F-137: Unload menu in the ZR Tools design (replaces the Fluidd style popup of WM_UNLOAD_MENU on this screen)
    # ------------------------------------------------------------------
    def _unload_open(self):
        if not self._require_not_printing():
            return
        u = (self.st.get("gcode_macro _WM_UNLOAD") or {})
        if u.get("active"):
            self._screen.show_popup_message("An unload is already running. Stop it with _WM_UNLOAD_STOP.")
            return
        self.show_unload()

    def _unload_label(self, i):
        info = self._tool_info(i)
        mat = self._mat_name(i)
        col = _color_name(info["color"])
        return ("T%d" % (i + 1)), (" ".join(x for x in (mat, col) if x) or "no data")

    def show_unload(self):
        self.view = "unload"
        self._clear()
        self.root.pack_start(self._header("Unload filament"), False, False, 0)
        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        body.pack_start(self._label("Choose the tool to unload, or all tools one after the other.", "zr_hint", wrap=True), False, False, 0)
        grid = Gtk.Grid()
        grid.set_row_spacing(8)
        grid.set_column_spacing(8)
        grid.set_column_homogeneous(True)
        for i in range(NTOOLS):
            ev = Gtk.EventBox()
            ev.get_style_context().add_class("zr_card")
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            for m in ("top", "bottom", "start", "end"):
                getattr(row, "set_margin_" + m)(8)
            sp = self._spool(88)
            self._set_swatch(sp, self._tool_info(i)["color"])
            self._mark_empty(ev, sp, self._sensor("filament%d" % i) is False)
            row.pack_start(sp, False, False, 0)
            t1, t2 = self._unload_label(i)
            txt = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            txt.set_valign(Gtk.Align.CENTER)
            a = self._label(t1, "zr_title")
            a.set_halign(Gtk.Align.START)
            b = self._label(t2, "zr_small")
            b.set_halign(Gtk.Align.START)
            txt.pack_start(a, False, False, 0)
            txt.pack_start(b, False, False, 0)
            c = self._label("In head" if self._sensor("filament%d" % i) else "No filament", "zr_small")
            c.set_halign(Gtk.Align.START)
            txt.pack_start(c, False, False, 0)
            self._card_text(a, b, c)
            row.pack_start(txt, True, True, 0)
            ev.add(row)
            ev.connect("button-release-event", lambda _w, _e, n=i: self.show_unload_ask(str(n)))
            grid.attach(ev, i % 2, i // 2, 1, 1)
        body.pack_start(grid, False, False, 0)
        all_btn = self._button(None, "All tools", "color3", self.show_unload_ask, "ALL")
        all_btn.get_style_context().add_class("zr_btn_primary")
        all_btn.set_size_request(-1, BIG_H)
        body.pack_start(all_btn, False, False, 0)
        self.root.pack_start(self._scrolled(body), True, True, 0)
        self.root.show_all()

    def show_unload_ask(self, which):
        self.view = "unload_ask"
        self._clear()
        allt = which == "ALL"
        self.root.pack_start(self._header("Unload all tools?" if allt else "Unload T%d?" % (int(which) + 1)), False, False, 0)
        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        card.get_style_context().add_class("zr_card")
        card.set_border_width(12)
        if allt:
            txt = ("T1, T2, T3 and T4 are unloaded one after the other. A tool with nothing to unload is skipped. "
                   "Each nozzle heats to its saved temperature and the tools go back to their docks at the end.")
        else:
            txt = ("The nozzle of T%d heats to its saved temperature and the filament is pulled out. "
                   "The tool goes back to its dock at the end." % (int(which) + 1))
        card.pack_start(self._label(txt, None, wrap=True), False, False, 0)
        body.pack_start(card, False, False, 0)
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row.set_homogeneous(True)
        yes = self._button(None, "Yes, unload", "color3", self._unload_go, which)
        yes.get_style_context().add_class("zr_btn_primary")
        no = self._button(None, "Cancel", "color3", self.back)
        for b in (yes, no):
            b.set_size_request(-1, BIG_H)
            row.pack_start(b, True, True, 0)
        body.pack_start(row, False, False, 0)
        self.root.pack_start(self._scrolled(body), True, True, 0)
        self.root.show_all()

    # F-156 (restored 2026-11-19, F-179): the Purge page of a toolhead
    PURGE_TEMPS = (0, 200, 220, 240, 260)      # 0 = the temperature saved for the filament
    PURGE_SPEEDS = (2, 5, 10, 20)              # mm/s
    PURGE_LENS = (10, 20, 50, 100)             # mm

    def _purge_open(self, i):
        if not self._require_not_printing():
            return
        u = (self.st.get("gcode_macro _WM_UNLOAD") or {})
        if u.get("active"):
            self._screen.show_popup_message("An unload is running. Stop it with _WM_UNLOAD_STOP.")
            return
        self.view_tool = i
        # the page is closed when another window finishes the purge (open goes 1 -> 0). When the other window is open already
        # (open is 1) no change arrives for our own "open = 1", so that window counts as seen now.
        self._purge_seen = int((self.st.get("gcode_macro _WM_PURGE_SEL") or {}).get("open", 0) or 0) == 1
        self._gcode("SET_GCODE_VARIABLE MACRO=_WM_PURGE_SEL VARIABLE=open VALUE=1")
        self.show_purge(i)

    def _purge_pick(self, key, value):
        self.purge[key] = value
        self.show_purge(self.view_tool)

    def show_purge(self, i):
        self.view = "purge"
        self.view_tool = i
        if not hasattr(self, "purge"):
            self.purge = {"temp": 0, "speed": 5, "len": 20}
        own = int(self._tool_info(i)["temp"]) or 210
        self._clear()
        self.root.pack_start(self._header("Purge T%d" % (i + 1)), False, False, 0)
        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)

        def chips(label, key, values, text):
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            lab = self._label(label, "zr_hint")
            lab.set_size_request(80, -1)
            lab.set_halign(Gtk.Align.START)
            row.pack_start(lab, False, False, 0)
            for v in values:
                b = self._button(None, text(v), "color3", self._purge_pick, key, v)
                if self.purge[key] == v:
                    b.get_style_context().add_class("zr_btn_primary")
                b.set_hexpand(True)
                b.set_size_request(-1, 50)
                row.pack_start(b, True, True, 0)
            body.pack_start(row, False, False, 0)

        chips("Temp", "temp", self.PURGE_TEMPS, lambda v: ("Filament %d" % own) if v == 0 else "%d" % v)
        chips("Speed", "speed", self.PURGE_SPEEDS, lambda v: "%d mm/s" % v)
        chips("Amount", "len", self.PURGE_LENS, lambda v: "%d mm" % v)
        note = ("ACE feed assist is automatic. " if self._ace_connected() else "") + "Start purges and stays hot, purge again if you want. Cancel wipes, cools and parks."
        if self.__dict__.get("_purge_hot") is not None:
            note = "T%d is hot at the purge location. " % (self._purge_hot + 1) + note
        body.pack_start(self._label(note, "zr_hint", wrap=True), False, False, 0)
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row.set_homogeneous(True)
        go = self._button(None, "Start purge", "color3", self._purge_go, i)
        go.get_style_context().add_class("zr_btn_green")
        no = self._button(None, "Cancel", "color3", self._purge_cancel)
        for b in (go, no):
            b.set_size_request(-1, 84)
            row.pack_start(b, True, True, 0)
        body.pack_start(row, False, False, 0)
        self.root.pack_start(self._scrolled(body), True, True, 0)
        self.root.show_all()

    def _purge_go(self, i):
        if not self._require_not_printing():
            return
        p = self.purge
        # FINISH=2: the tool stays hot at the purge location and this page stays open; Cancel (or Back) wipes, cools and parks it
        self._gcode("_WM_PURGE T=%d S=%d SPEED=%d LEN=%d FINISH=2" % (i, p["temp"], p["speed"], p["len"]),
                    "Purging T%d: %d mm at %d mm/s..." % (i + 1, p["len"], p["speed"]))
        self._purge_hot = i
        self.show_purge(i)

    def _purge_finish(self):
        """Wipe, cool with the part fan and park the tool the purge page left hot (_WM_PURGE_DONE). Always sent: it also closes the Fluidd window."""
        hot = self.__dict__.get("_purge_hot") is not None
        self._purge_hot = None
        self._purge_seen = False
        self._gcode("_WM_PURGE_DONE", "Wiping, cooling and parking..." if hot else None)

    def _purge_sync(self):
        """The purge window was closed on the other side (Fluidd): close this page too, without sending anything."""
        if self.view != "purge":
            return
        o = int((self.st.get("gcode_macro _WM_PURGE_SEL") or {}).get("open", 0) or 0)
        if o == 1:
            self._purge_seen = True
        elif self.__dict__.get("_purge_seen"):
            self._purge_seen = False
            self._purge_hot = None
            self._purge_quiet = True         # the other window already sent _WM_PURGE_DONE: send nothing again
            self.back()

    def _purge_cancel(self):
        self._purge_finish()
        self.back()

    def _unload_go(self, which):
        if not self._require_not_printing():
            return
        t = "ALL" if which == "ALL" else str(int(which))
        self._gcode("_WM_UNLOAD_GO T=%s" % t, "Unloading %s..." % ("all tools" if t == "ALL" else "T%d" % (int(t) + 1)))
        self.back()      # ask page -> tool list
        self.back()      # tool list -> the page the Unload menu was opened from

    # ------------------------------------------------------------------
    # F-166: Load window (paused or idle) and Resume tool window (paused)
    # ------------------------------------------------------------------
    def _tool_card_row(self, i, extra, on_tap, selected=False, spool=88):
        ev = Gtk.EventBox()
        ev.get_style_context().add_class("zr_card")
        if selected:
            ev.get_style_context().add_class("zr_card_sel")
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        for m in ("top", "bottom", "start", "end"):
            getattr(row, "set_margin_" + m)(8)
        sp = self._spool(spool)
        self._set_swatch(sp, self._tool_info(i)["color"])
        self._mark_empty(ev, sp, self._sensor("filament%d" % i) is False)
        row.pack_start(sp, False, False, 0)
        t1, t2 = self._unload_label(i)
        txt = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        txt.set_valign(Gtk.Align.CENTER)
        a = self._label(t1, "zr_title")
        a.set_halign(Gtk.Align.START)
        b = self._label(t2, "zr_small")
        b.set_halign(Gtk.Align.START)
        txt.pack_start(a, False, False, 0)
        txt.pack_start(b, False, False, 0)
        if extra:                     # the status on its own short line: a long line made the page wider than the screen
            c = self._label(extra, "zr_small")
            c.set_halign(Gtk.Align.START)
            txt.pack_start(c, False, False, 0)
            self._card_text(a, b, c)
        else:
            self._card_text(a, b)
        row.pack_start(txt, True, True, 0)
        ev.add(row)
        ev.connect("button-release-event", lambda _w, _e, n=i: on_tap(n))
        return ev

    def _hint(self, text, css="zr_hint"):
        # F-166: a wrapping label with a maximum width, so a long text cannot make the whole page wider than the screen
        lbl = self._label(text, css, wrap=True)
        lbl.set_max_width_chars(34)
        lbl.set_width_chars(20)
        return lbl

    def _load_open(self):
        if not self._require_not_printing():
            return
        l = (self.st.get("gcode_macro _WM_LOAD") or {})
        if l.get("active"):
            self._screen.show_popup_message("A load is already running. Stop it with _WM_LOAD_STOP.")
            return
        self.__dict__["load_sel"] = set()
        self.show_load()

    def show_load(self):
        self.view = "load"
        self._clear()
        sel = self.__dict__.setdefault("load_sel", set())
        paused = self._print_state() == "paused"
        pt = self._pause_tool()
        self.root.pack_start(self._header("Load filament"), False, False, 0)
        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        hint = "Tap the tools to load, then press Load selected tools."
        if paused:
            pass
        body.pack_start(self._hint(hint), False, False, 0)
        grid = Gtk.Grid()
        grid.set_row_spacing(8)
        grid.set_column_spacing(8)
        grid.set_column_homogeneous(True)
        for i in range(NTOOLS):
            fil = self._sensor("filament%d" % i)
            extra = ("In head" if fil else "No filament")
            if paused and pt == i:
                extra += " \u00b7 print tool"
            if i in sel:
                extra = "Selected \u00b7 " + extra
            grid.attach(self._tool_card_row(i, extra, self._load_toggle, i in sel, 78), i % 2, i // 2, 1, 1)
        body.pack_start(grid, False, False, 0)
        go = self._button(None, "Load selected tools", "color3", self._load_go)
        go.get_style_context().add_class("zr_btn_primary")
        go.set_size_request(-1, BIG_H)
        body.pack_start(go, False, False, 0)
        self.root.pack_start(self._scrolled(body), True, True, 0)
        self.root.show_all()

    def _load_toggle(self, i):
        sel = self.__dict__.setdefault("load_sel", set())
        if i in sel:
            sel.discard(i)
        else:
            sel.add(i)
        self.show_load()

    def _load_go(self, *_):
        if not self._require_not_printing():
            return
        sel = sorted(self.__dict__.get("load_sel") or [])
        if not sel:
            self._screen.show_popup_message("Tap at least one tool first.")
            return
        names = ", ".join("T%d" % (i + 1) for i in sel)
        self._gcode('SET_GCODE_VARIABLE MACRO=_WM_LOAD VARIABLE=sel VALUE=\'"%s"\'\n_WM_LOAD_GO' % ",".join(str(i) for i in sel),
                    "Loading %s..." % names)
        self.back()

    def _pause_tool(self):
        try:
            v = int(self._vars().get("wm_pause_tool", 99))
        except (TypeError, ValueError):
            v = 99
        return v if 0 <= v < NTOOLS else -1

    def _resume_tool_open(self):
        if self._print_state() != "paused":
            self._screen.show_popup_message("Resume tool works while the print is paused.")
            return
        pt = self._pause_tool()
        if pt < 0:
            self._screen.show_popup_message("The print was paused with no tool on the carriage. Load and pick a tool first, or press Resume.")
            return
        self.__dict__["rt"] = {"rep": -1, "dtemp": 0, "purge": 20}
        self.show_resume_tool()

    def _rt_base_temp(self):
        pt = self._pause_tool()
        r = self.st.get("gcode_macro RESUME") or {}
        try:
            return float(r.get("resume_temperature%d" % pt, 0) or 0)
        except (TypeError, ValueError):
            return 0.0

    def show_resume_tool(self):
        # F-168: step 1 = choose the tool; step 2 (show_resume_tool2) = temperature, purge and the Resume button.
        # Two short pages fit the small screen board without scrolling.
        self.view = "resume_tool"
        self._clear()
        rt = self.__dict__.setdefault("rt", {"rep": -1, "dtemp": 0, "purge": 20})
        pt = self._pause_tool()
        self.root.pack_start(self._header("Resume tool"), False, False, 0)
        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        red = self._label("", "zr_title")      # F-173: the pause tool on its own line, big and red
        red.set_markup("<span foreground='#ff4d4d' font='20' weight='bold'>The print was paused with T%d</span>" % (pt + 1))
        red.set_halign(Gtk.Align.START)
        body.pack_start(red, False, False, 0)
        body.pack_start(self._hint("Pick the tool that finishes the print. A grey tool has no filament: tap it to load it."), False, False, 0)
        grid = Gtk.Grid()
        grid.set_row_spacing(8)
        grid.set_column_spacing(8)
        grid.set_column_homogeneous(True)
        for i in range(NTOOLS):
            fil = self._sensor("filament%d" % i)
            extra = ("Print tool" if i == pt else "Ready") if fil else "No filament"
            grid.attach(self._tool_card_row(i, extra, self._rt_pick, False), i % 2, i // 2, 1, 1)
        body.pack_start(grid, False, False, 0)
        self.root.pack_start(self._scrolled(body), True, True, 0)
        self.root.show_all()

    def show_resume_tool2(self):
        rt = self.__dict__.get("rt")
        if not rt or rt["rep"] < 0:
            self.show_resume_tool()
            return
        self.view = "resume_tool2"
        self._clear()
        pt = self._pause_tool()
        rep = rt["rep"]
        self.root.pack_start(self._header("Resume with T%d" % (rep + 1)), False, False, 0)
        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        if rep == pt:
            title = "T%d continues the print" % (pt + 1)
            lines = ["T%d is the tool the print was paused with." % (pt + 1),
                     "It stays on the carriage, heats, purges and wipes, then the print continues with it."]
        else:
            title = "T%d takes over from T%d" % (rep + 1, pt + 1)
            lines = ["T%d goes back to its dock and is not used again in this print." % (pt + 1),
                     "T%d heats, purges and wipes, then continues where T%d stopped." % (rep + 1, pt + 1),
                     "T%d finishes the print, including the parts meant for T%d." % (rep + 1, pt + 1)]
        body.pack_start(self._label(title, "zr_title"), False, False, 0)
        for ln in lines:
            dl = self._label("", None, wrap=True)
            dl.set_markup("<span font='14'>%s</span>" % ln)
            body.pack_start(dl, False, False, 0)
        self._rt_tl = self._label("", "zr_title")
        self._rt_sm = self._hint("", "zr_small")
        body.pack_start(self._rt_tl, False, False, 0)
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row.set_homogeneous(True)
        for lab, dd in (("Temp -5", -5), ("Temp +5", 5)):
            b = self._button(None, lab, "color3", self._rt_temp, dd)
            b.set_size_request(-1, 46)
            row.pack_start(b, True, True, 0)
        body.pack_start(row, False, False, 0)
        row2 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row2.set_homogeneous(True)
        self._rt_pb = {}
        for l in (20, 40, 60, 100):
            b = self._button(None, "%d mm" % l, "color3", self._rt_purge, l)
            b.set_size_request(-1, 46)
            self._rt_pb[l] = b
            row2.pack_start(b, True, True, 0)
        body.pack_start(row2, False, False, 0)
        go = self._button(None, "Resume with T%d" % (rep + 1), "color3", self._rt_confirm)
        go.get_style_context().add_class("zr_btn_go")
        go.set_size_request(-1, 54)
        body.pack_start(go, False, False, 0)
        self._rt_refresh()
        self.root.pack_start(self._scrolled(body), True, True, 0)
        self.root.show_all()

    def _rt_refresh(self):
        # update the texts and the chosen purge button in place: no page rebuild, so nothing is drawn twice
        rt = self.__dict__["rt"]
        base = self._rt_base_temp()
        self._rt_tl.set_text("Temperature %d C  (the print had %d C)" % (int(base + rt["dtemp"]), int(base)))
        for l, b in self.__dict__.get("_rt_pb", {}).items():
            ctx = b.get_style_context()
            if rt["purge"] == l:
                ctx.add_class("zr_btn_go")
            else:
                ctx.remove_class("zr_btn_go")

    def _rt_pick(self, i):
        if not self._sensor("filament%d" % i):      # F-174: an empty tool opens the Load page for it (no dead end)
            if not self._require_not_printing():
                return
            self.__dict__["load_sel"] = {i}
            self.show_load()
            return
        rt = self.__dict__["rt"]
        rt["rep"] = i
        rt["dtemp"] = 0
        self.show_resume_tool2()

    def _rt_temp(self, d):
        rt = self.__dict__["rt"]
        t = self._rt_base_temp() + rt["dtemp"] + d
        if t < 170 or t > 300:
            self._screen.show_popup_message("The temperature must stay between 170 and 300 C.")
            return
        rt["dtemp"] += d
        self._rt_refresh()

    def _rt_purge(self, l):
        self.__dict__["rt"]["purge"] = l
        self._rt_refresh()

    def _rt_confirm(self, *_):
        # F-204: "Resume with T*" first shows what will happen and asks for a confirmation
        rt = self.__dict__["rt"]
        if self._print_state() != "paused" or rt["rep"] < 0:
            self._screen.show_popup_message("The print must be paused and a tool chosen.")
            return
        self.show_resume_confirm()

    def show_resume_confirm(self):
        rt = self.__dict__.get("rt")
        if not rt or rt["rep"] < 0:
            self.show_resume_tool()
            return
        self.view = "resume_confirm"
        self._clear()
        pt = self._pause_tool()
        rep = rt["rep"]
        n = rep + 1
        base = int(self._rt_base_temp())
        temp = int(self._rt_base_temp() + rt["dtemp"])
        self.root.pack_start(self._header("Resume with T%d" % n), False, False, 0)
        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        card.get_style_context().add_class("zr_card")
        card.set_border_width(12)
        card.pack_start(self._label("Resume the print with T%d?" % n, "zr_title"), False, False, 0)
        if rep == pt:
            lines = ["1. T%d stays on the carriage and heats to %d C (the print had %d C)." % (n, temp, base),
                     "2. T%d purges and the nozzle is wiped." % n,
                     "3. The print continues with T%d." % n]
        else:
            lines = ["1. T%d goes back to its dock, T%d is picked up and heats to %d C (the print had %d C)." % (pt + 1, n, temp, base),
                     "2. T%d purges and the nozzle is wiped." % n,
                     "3. The print continues with T%d where T%d stopped, including the parts of T%d." % (n, pt + 1, pt + 1)]
        card.pack_start(self._label("What will happen:", None), False, False, 0)
        for ln in lines:
            dl = self._label("", None, wrap=True)
            dl.set_markup("<span font='13'>%s</span>" % ln)
            card.pack_start(dl, False, False, 0)
        rl = self._label("", None, wrap=True)
        rl.set_markup("<span font='13' foreground='#f2c744'>Check that the filament in T%d is the one you want.</span>" % n)
        card.pack_start(rl, False, False, 0)
        body.pack_start(card, False, False, 0)
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row.set_homogeneous(True)
        yb = self._button(None, "Resume", "color3", self._rt_go)
        yb.get_style_context().add_class("zr_btn_go")
        nb = self._button(None, "Back", "color3", self.back)
        for b_ in (yb, nb):
            b_.set_size_request(-1, BIG_H)
            row.pack_start(b_, True, True, 0)
        # no scrolling: the text on top, the two big buttons at the bottom
        body.set_vexpand(True)
        body.pack_end(row, False, False, 0)
        self.root.pack_start(body, True, True, 0)
        self.root.show_all()

    def _rt_go(self, *_):
        rt = self.__dict__["rt"]
        if self._print_state() != "paused" or rt["rep"] < 0:
            self._screen.show_popup_message("The print must be paused and a tool chosen.")
            return
        temp = int(self._rt_base_temp() + rt["dtemp"])
        self._gcode("_WM_RESUME_TOOL_GO REP=%d TEMP=%d PURGE=%d" % (rt["rep"], temp, rt["purge"]),
                    "Resuming with T%d..." % (rt["rep"] + 1))
        self.show_home()

    def _require_not_printing(self):
        # F-166: load, unload and Resume tool are allowed while the print is PAUSED, not while it prints
        if self._print_state() == "printing":
            self._screen.show_popup_message("Not available while printing. Pause the print first.")
            return False
        return True

    def _require_idle(self):
        if self._busy():
            self._screen.show_popup_message("Not available during a print.")
            return False
        return True

    def _confirm(self, title, text, script, message=None):
        # F-137: a page in the ZR Tools design (same as the Unload confirm page) instead of the KlipperScreen dialog
        self._ask_page(title, text, lambda: self._gcode(script, message))

    def _ask_page(self, title, text, func, yes="Yes", no="Cancel"):
        self.view = "ask"
        self._clear()
        self.root.pack_start(self._header(title), False, False, 0)
        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        card.get_style_context().add_class("zr_card")
        card.set_border_width(12)
        card.pack_start(self._label(text, None, wrap=True), False, False, 0)
        body.pack_start(card, False, False, 0)
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row.set_homogeneous(True)
        yb = self._button(None, yes, "color3", lambda: (self.back(), func()))
        yb.get_style_context().add_class("zr_btn_primary")
        nb = self._button(None, no, "color3", self.back)
        for b_ in (yb, nb):
            b_.set_size_request(-1, BIG_H)
            row.pack_start(b_, True, True, 0)
        body.pack_start(row, False, False, 0)
        self.root.pack_start(self._scrolled(body), True, True, 0)
        self.root.show_all()

    # ------------------------------------------------------------------
    # small widget helpers
    # ------------------------------------------------------------------
    def _clear(self):
        for child in self.root.get_children():
            self.root.remove(child)
        self.w = {}
        self._mark_nav()

    def _label(self, text="", css=None, wrap=False):
        lbl = Gtk.Label(label=text)
        lbl.set_line_wrap(wrap)
        lbl.set_justify(Gtk.Justification.CENTER)
        if css:
            lbl.get_style_context().add_class(css)
        return lbl

    def _swatch(self, w, h):
        box = Gtk.EventBox()
        box.set_size_request(w, h)
        box.get_style_context().add_class("zr_swatch")
        return box

    def _card_text(self, a, b, c=None):
        # F-171: card texts as in the approved picture: big tool name, material line, status line
        esc = GLib.markup_escape_text
        a.set_markup("<b><span font='18'>%s</span></b>" % esc(a.get_text()))
        b.set_markup("<span font='12'>%s</span>" % esc(b.get_text()))
        if c is not None:
            c.set_markup("<span font='11'>%s</span>" % esc(c.get_text()))

    def _mark_empty(self, ev, sp, empty):
        # F-171: a tool with no filament in its head: the whole box and the spool are greyed out
        sp.zr_empty = bool(empty)
        sp.queue_draw()
        ctx = ev.get_style_context()
        if empty:
            ctx.add_class("zr_card_empty")
        else:
            ctx.remove_class("zr_card_empty")

    def _set_swatch(self, box, color_int):
        if hasattr(box, "zr_color"):       # spool (drawn)
            box.zr_color = color_int
            box.queue_draw()
            return
        r, g, b = _rgb(color_int)
        box.override_background_color(
            Gtk.StateFlags.NORMAL, Gdk.RGBA(r / 255.0, g / 255.0, b / 255.0, 1.0))

    def _spool(self, size):
        """A round spool in the filament colour: centre hole and ring; dashed outline when empty."""
        da = Gtk.DrawingArea()
        da.set_size_request(size, size)
        da.zr_color = 0x303030
        da.zr_empty = False
        da.set_halign(Gtk.Align.CENTER)

        def draw(widget, cr):
            w, h = widget.get_allocated_width(), widget.get_allocated_height()
            d = min(w, h)
            cx, cy, rad = w / 2.0, h / 2.0, d / 2.0 - 3
            r_, g_, b_ = _rgb(widget.zr_color)
            if widget.zr_empty:          # F-171: no filament = the whole spool grey
                cr.set_source_rgb(0.24, 0.27, 0.30)
                cr.arc(cx, cy, rad, 0, 6.2832)
                cr.fill()
                cr.set_source_rgba(1, 1, 1, 0.18)
                cr.set_line_width(max(2, rad * 0.06))
                cr.arc(cx, cy, rad * 0.62, 0, 6.2832)
                cr.stroke()
                cr.set_source_rgb(0.07, 0.09, 0.11)
                cr.arc(cx, cy, rad * 0.26, 0, 6.2832)
                cr.fill()
                return False
            cr.set_source_rgb(r_ / 255.0, g_ / 255.0, b_ / 255.0)
            cr.arc(cx, cy, rad, 0, 6.2832)
            cr.fill()
            lum = (0.299 * r_ + 0.587 * g_ + 0.114 * b_) / 255.0       # light ring on dark colours
            ring = (1, 1, 1, 0.35) if lum < 0.35 else (0, 0, 0, 0.25)
            cr.set_source_rgba(*ring)
            cr.set_line_width(max(2, rad * 0.06))
            cr.arc(cx, cy, rad * 0.62, 0, 6.2832)
            cr.stroke()
            cr.set_source_rgb(0.105, 0.137, 0.168)                      # centre hole
            cr.arc(cx, cy, rad * 0.26, 0, 6.2832)
            cr.fill()
            cr.set_source_rgba(*ring)
            cr.set_line_width(max(1.5, rad * 0.04))
            cr.arc(cx, cy, rad - 1, 0, 6.2832)
            cr.stroke()
            return False
        da.connect("draw", draw)
        return da

    def _tempbar(self):
        """Thin bar: how close the nozzle is to its target."""
        da = Gtk.DrawingArea()
        da.set_size_request(-1, 6)
        da.zr_frac = 0.0

        def draw(widget, cr):
            w, h = widget.get_allocated_width(), widget.get_allocated_height()
            cr.set_source_rgba(0.5, 0.55, 0.6, 0.35)
            cr.rectangle(0, 0, w, h)
            cr.fill()
            cr.set_source_rgb(0.18, 0.48, 0.96)
            cr.rectangle(0, 0, w * max(0.0, min(1.0, widget.zr_frac)), h)
            cr.fill()
            return False
        da.connect("draw", draw)
        return da

    def _pill(self, text="", kind=None):
        lbl = Gtk.Label(label=text)
        ctx = lbl.get_style_context()
        ctx.add_class("zr_pill")
        if kind:
            ctx.add_class("zr_pill_" + kind)
        lbl.set_halign(Gtk.Align.CENTER)
        return lbl

    def _set_pill(self, lbl, text, kind):
        ctx = lbl.get_style_context()
        for k in ("ready", "active", "empty", "info", "on", "off"):
            ctx.remove_class("zr_pill_" + k)
        if kind:
            ctx.add_class("zr_pill_" + kind)
        lbl.set_text(text)

    _PRIMARY_LABELS = ("Print", "Save", "Use colour", "Color Picker", "More colours", "Start drying", "Load from ACE", "Apply", "Confirm")
    _STYLE_CLASS = {"color1": "zr_btn_primary", "color2": "zr_btn_green", "color4": "zr_btn_orange"}

    def _button(self, icon, label, style, callback, *args):
        """Icon beside the label and no vertical stretching: a slim, uniform rounded button."""
        try:
            btn = self._gtk.Button(icon, label, style, scale=self._gtk.bsidescale, position=Gtk.PositionType.LEFT, lines=1)
        except (TypeError, AttributeError):
            btn = self._gtk.Button(icon, label, style)
        btn.set_vexpand(False)
        ctx = btn.get_style_context()
        ctx.add_class("zr_btn")
        if style == "color1" and label in self._PRIMARY_LABELS:      # one clear primary action; the rest stay calm
            ctx.add_class("zr_btn_primary")
        btn.connect("clicked", lambda _w: callback(*args))
        return btn

    def _tab_button(self, icon, label, callback):
        """Bottom tab bar: icon above the label."""
        btn = self._gtk.Button(icon, label, "color3", lines=1)
        btn.set_vexpand(False)
        btn.get_style_context().add_class("zr_tab")
        btn.connect("clicked", lambda _w: (callback(), self.__dict__.__setitem__("_hist", [])))
        return btn

    def _header(self, title, back=None, action=None):
        # F-137: no Back button of our own: KlipperScreen's back button (left side) goes back, see on_back()
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        lbl = self._label()
        lbl.set_markup(f"<b>{title}</b>")
        row.pack_start(lbl, True, True, 0)
        if action is not None:
            icon, text, style, cb = action
            ab = self._button(icon, text, style, cb)
            ab.set_size_request(110, self.sz["btn_h"])
            row.pack_end(ab, False, False, 0)
        return row

    def _scrolled(self, child):
        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sw.set_vexpand(True)
        sw.set_kinetic_scrolling(True)       # drag with a finger
        sw.set_overlay_scrolling(False)      # a visible scrollbar, so you can see there is more
        sw.add(child)
        return sw

    # ------------------------------------------------------------------
    # MAIN VIEW: 4 tool cards
    # ------------------------------------------------------------------
    def show_main(self):
        self.view = "main"
        self._clear()

        self.w["p_car"] = self._pill("On carriage: --", "info")
        self.w["p_state"] = self._pill("Printer: --", "info")
        self.w["p_ch"] = self._pill("", "info")
        self.w["p_ace"] = self._pill("", "info")
        if self.portrait:
            # Tall screen: the three pills would not fit in one row, so the chamber pill gets its own row.
            top = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            row1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            row1.pack_start(self.w["p_car"], False, False, 0)
            row1.pack_start(self.w["p_state"], False, False, 0)
            top.pack_start(row1, False, False, 0)
            top.pack_start(self.w["p_ch"], False, False, 0)
            top.pack_start(self.w["p_ace"], False, False, 0)
        else:
            top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            top.pack_start(self.w["p_car"], False, False, 0)
            top.pack_start(self.w["p_state"], False, False, 0)
            top.pack_start(self.w["p_ace"], False, False, 0)
            top.pack_end(self.w["p_ch"], False, False, 0)
        self.root.pack_start(top, False, False, 0)

        self.w["cards"] = []
        if self.portrait:
            # Tall screen: the cards sit 2 x 2.
            cards = Gtk.Grid()
            cards.set_row_spacing(8)
            cards.set_column_spacing(8)
            cards.set_column_homogeneous(True)
            cards.set_row_homogeneous(True)
            for i in range(NTOOLS):
                card = self._make_card(i)
                card.set_hexpand(True)
                card.set_vexpand(True)
                cards.attach(card, i % self.sz["tool_cols"], i // self.sz["tool_cols"], 1, 1)
        else:
            # Wide screen: four cards in a row (unchanged).
            cards = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            cards.set_homogeneous(True)
            for i in range(NTOOLS):
                cards.pack_start(self._make_card(i), True, True, 0)
        self.root.pack_start(cards, True, True, 0)
        # F-166: while the print is PAUSED: Load, Unload and Resume tool (hidden otherwise)
        pb = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        pb.set_homogeneous(True)
        for lab, fn in (("Resume tool", self._resume_tool_open), ("Load", self._load_open), ("Unload", self._unload_open)):
            b = self._button(None, lab, "color3", fn)
            b.get_style_context().add_class("zr_btn_primary")
            b.set_size_request(-1, 62)
            b.get_style_context().add_class("zr_btn_big")
            pb.pack_start(b, True, True, 0)
        self.w["pausebar"] = pb
        self.root.pack_start(pb, False, False, 0)
        self.root.show_all()
        self._refresh_view()

    def _make_card(self, i):
        ev = Gtk.EventBox()
        ev.get_style_context().add_class("zr_card")
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        for m in ("top", "bottom", "start", "end"):
            getattr(box, "set_margin_" + m)(7)
        big = self.density == "comfortable"
        c = {
            "ev": ev,
            "title": self._label("Toolhead %d" % (i + 1), "zr_title"),
            "chip": self._pill("", "empty"),
            "spool": self._spool(100 if big else 78),
            "mat": self._label("", "zr_mat"),
            "color": self._label("", "zr_small"),
            "temp": self._label("", "zr_small"),
            "bar": self._tempbar(),
            "fil": self._label("", "zr_small"),
            "dock": self._label("", "zr_small"),
            "ace": self._label("", "zr_small"),
        }
        for key in ("title", "chip", "spool", "mat", "color", "temp"):
            box.pack_start(c[key], False, False, 0)
        box.pack_start(c["bar"], False, False, 2)
        box.pack_start(c["fil"], False, False, 0)
        if big:                      # compact sizes keep the cards' touch area, so no ACE line there
            box.pack_start(c["ace"], False, False, 0)
        box.pack_end(c["dock"], False, False, 0)
        ev.add(box)
        ev.connect("button-release-event", lambda *_a, t=i: self.show_tool(t))
        self.w["cards"].append(c)
        return ev

    def _chamber_text(self):
        for key in ("heater_generic chamber", "temperature_sensor chamber", "temperature_sensor chamber_temp"):
            o = self.st.get(key)
            if isinstance(o, dict) and o.get("temperature") is not None:
                return "Chamber %.0f\u00b0C" % float(o["temperature"])
        return ""

    def _refresh_main(self):
        active = self._active_tool()
        state = self._print_state() or "unknown"
        if "pausebar" in self.w:
            self.w["pausebar"].set_visible(self._print_state() == "paused")
        self.w["p_car"].set_text("On carriage: %s" % ("T%d" % active if active >= 0 else "none"))
        self.w["p_state"].set_text("Printer: %s" % state)
        self.w["p_ch"].set_text(self._chamber_text())
        self.w["p_ch"].set_visible(bool(self._chamber_text()))
        bar = L.ace_bar_text(self.st)
        self.w["p_ace"].set_text(bar)
        self.w["p_ace"].set_visible(bool(bar))
        paused_now = self._print_state() == "paused"
        for i, c in enumerate(self.w.get("cards", [])):
            info = self._tool_info(i)
            name, _ = MATERIALS[info["mat"]]
            has = bool(info["mat"])
            ctx = c["ev"].get_style_context()
            if i == active:
                ctx.add_class("zr_active")
            else:
                ctx.remove_class("zr_active")
            if i == active:
                self._set_pill(c["chip"], "Active", "active")
            elif has and self._sensor("filament%d" % i) is not False:
                self._set_pill(c["chip"], "Ready", "ready")
            else:
                self._set_pill(c["chip"], "Empty", "empty")
            fil = self._sensor("filament%d" % i)
            self._mark_empty(c["ev"], c["spool"], (not has) or (fil is False))
            self._set_swatch(c["spool"], info["color"] if has else 0x303030)
            sz = 46 if paused_now else (100 if self.density == "comfortable" else 78)
            c["spool"].set_size_request(sz, sz)
            c["mat"].set_text(name if has else "Empty")
            c["color"].set_text(_color_name(info["color"]) if has else " ")
            cur, tgt = self._temps(i)
            if cur is None:
                c["temp"].set_text("--")
                c["bar"].zr_frac = 0.0
            else:
                goal = tgt or info.get("temp") or 0
                c["temp"].set_text("%.0f\u00b0 / %.0f\u00b0" % (cur, tgt or info.get("temp") or 0))
                c["bar"].zr_frac = (cur / goal) if goal else 0.0
            c["bar"].queue_draw()
            dock = self._sensor("docked%d" % i)
            c["fil"].set_markup(self._dot(fil, "Filament" if fil else "No filament"))
            c["dock"].set_text(("In dock" if dock else "On carriage") if dock is not None else " ")
            c["ace"].set_text(L.ace_card_text(self.st, i))

    @staticmethod
    def _dot(on, text):
        if on is None:
            return " "
        col = "#6fe39a" if on else "#8a96a2"
        return "<span foreground='%s'>\u25cf</span> %s" % (col, text)

    # ------------------------------------------------------------------
    # TOOL VIEW: actions + filament editor
    # ------------------------------------------------------------------
    def show_tool(self, i):
        """Left: hero card with the spool (tap it to edit the filament). Right: 3x3 grid of big actions."""
        self.view = "tool"
        self.view_tool = i
        self.edit = dict(self._tool_info(i))
        self._clear()
        head = self._header("Toolhead %d" % (i + 1))
        kids = head.get_children()
        lbl = kids[-1]
        head.remove(lbl)
        mid = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        for text, n in (("\u25c0", (i - 1) % NTOOLS), (None, None), ("\u25b6", (i + 1) % NTOOLS)):
            if text is None:
                mid.pack_start(lbl, True, True, 0)
                continue
            arrow = self._button(None, text, "color3", self.show_tool, n)
            arrow.get_style_context().add_class("zr_arrow")
            arrow.set_size_request(84, self.sz["btn_h"])
            mid.pack_start(arrow, False, False, 0)
        head.pack_start(mid, True, True, 0)
        self.root.pack_start(head, False, False, 0)

        big = self.density == "comfortable"
        # Wide screen: the spool card on the left, the actions on the right.
        # Tall screen: the spool card is a strip on top and the actions are below it.
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL if self.portrait else Gtk.Orientation.HORIZONTAL, spacing=10)

        card = Gtk.EventBox()
        card.get_style_context().add_class("zr_card")
        card.connect("button-release-event", lambda *_a, n=i: self.show_tool_edit(n))     # F-137: tap the spool to edit the filament
        self.w["h_card"] = card
        col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        for m in ("top", "bottom", "start", "end"):
            getattr(col, "set_margin_" + m)(8)
        self.w["e_swatch"] = self._spool(110 if big else 84)
        self.w["h_mat"] = self._label("", "zr_mat")
        self.w["h_col"] = self._label("", "zr_small")
        self.w["h_chip"] = self._pill("", "ready")
        self.w["h_state"] = self._label("", "zr_small")
        self.w["h_ace1"] = self._label("", "zr_small")
        self.w["h_ace2"] = self._label("", "zr_small")
        if self.portrait:
            strip = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            strip.pack_start(self.w["e_swatch"], False, False, 0)
            texts = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            for k in ("h_mat", "h_col", "h_chip", "h_state", "h_ace1", "h_ace2"):
                texts.pack_start(self.w[k], False, False, 0)
            strip.pack_start(texts, True, True, 0)
            col.pack_start(strip, True, True, 0)
        else:
            col.pack_start(self.w["e_swatch"], True, True, 0)
            for k in ("h_mat", "h_col", "h_chip", "h_state", "h_ace1", "h_ace2"):
                col.pack_start(self.w[k], False, False, 0)
            col.pack_start(self._label("tap the spool to edit", "zr_small"), False, False, 0)
            card.set_size_request(190 if big else 150, -1)
        card.add(col)
        page.pack_start(card, False, False, 0)

        actions = Gtk.Grid()
        actions.set_row_spacing(8)
        actions.set_column_spacing(8)
        actions.set_column_homogeneous(True)
        # F-197: Row 1: Select, Park tool, Heat.  Row 2: Load, Unload, Cool.  Row 3: Load menu, Purge, Unload menu.
        # Left two columns: Load and Unload; with an ACE the feed assist button goes across the bottom under them,
        # without an ACE Load and Unload are two rows tall. (The Purge button was removed with ZR_PURGE, F-104.)
        have = {str(x).strip().upper() for x in (self._sections() or [])}
        lm_ok = (not have) or ("GCODE_MACRO WM_LOAD_MENU" in have)    # F-193: Load menu replaces the Feed assist button on this page (feed assist stays on the ACE Pro page)
        tall = 1 if (lm_ok or L.has_ace(self.st)) else 2
        items = [
            ("extruder", "Select", "color3", self._act_select, "zr_btn_pink", 0, 0, 1, 1),
            ("arrow-down", "Load", "color2", self._act_load, "", 0, 1, 1, tall),
            ("arrow-up", "Unload", "color4", self._act_unload, "", 1, 1, 1, 1),
            ("heat-up", "Heat", "color3", self._act_heat, "zr_btn_red", 2, 0, 1, 1),
            ("cool-down", "Cool", "color3", self._act_cool, "zr_btn_cyan", 2, 1, 1, 1),
        ]
        for icon, text, style, cb, cls, col, row, span, height in items:
            btn = self._gtk.Button(icon, text, style, lines=1)
            btn.get_style_context().add_class("zr_btn")
            if style in self._STYLE_CLASS:
                btn.get_style_context().add_class(self._STYLE_CLASS[style])
            if cls:
                btn.get_style_context().add_class(cls)
            btn.set_hexpand(True)
            btn.set_vexpand(True)
            btn.connect("clicked", lambda _w, f=cb: f(i))
            actions.attach(btn, col, row, span, height)
        park_btn = self._button("extruder", "Park tool", "color3", self._act_park)
        park_btn.get_style_context().add_class("zr_btn_purple")
        park_btn.set_vexpand(True)
        actions.attach(park_btn, 1, 0, 1, 1)
        have = {str(x).strip().upper() for x in (self._sections() or [])}
        if not have or "GCODE_MACRO WM_UNLOAD_MENU" in have:      # F-137: Unload menu (one tool or all) where Edit filament was; hidden when the Pi lacks it
            um_btn = self._button(None, "Unload menu", "color3", self._unload_open)
            um_btn.get_style_context().add_class("zr_btn_orange")
            um_btn.set_vexpand(True)
            actions.attach(um_btn, 2, 2, 1, 1)
        if lm_ok:                       # F-193: Load menu (same window as Fluidd) under Load and Unload
            lm_btn = self._button(None, "Load menu", "color3", self._load_open)
            lm_btn.get_style_context().add_class("zr_btn_primary")
            lm_btn.set_vexpand(True)
            actions.attach(lm_btn, 0, 2, 1, 1)
        elif L.has_ace(self.st):        # old Pi without WM_LOAD_MENU: ACE feed assist of this toolhead, purple + green ON, dark grey + red OFF
            assist_btn = Gtk.Button()
            assist_btn.get_style_context().add_class("zr_btn")
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            box.set_halign(Gtk.Align.CENTER)
            box.set_valign(Gtk.Align.CENTER)
            box.pack_start(Gtk.Label(label="Feed assist"), False, False, 0)
            self.w["a_badge"] = self._pill("OFF", "off")
            box.pack_start(self.w["a_badge"], False, False, 0)
            assist_btn.add(box)
            self.w["a_btn"] = assist_btn
            assist_btn.set_hexpand(True)
            assist_btn.set_vexpand(True)
            assist_btn.connect("clicked", lambda _w, n=i: self._act_assist(n))
            actions.attach(assist_btn, 0, 2, 1, 1)
        # F-156: Purge button (dark blue) beside Feed assist, or under Unload without an ACE; it opens the purge page
        purge_btn = self._button(None, "Purge", "color3", self._purge_open, i)
        purge_btn.get_style_context().add_class("zr_btn_navy")
        purge_btn.set_vexpand(True)
        actions.attach(purge_btn, 1, 2, 1, 1)
        page.pack_start(actions, True, True, 0)

        self.root.pack_start(page, True, True, 0)
        self.root.show_all()
        self._refresh_view()

    def show_tool_edit(self, i=None):
        """Filament editor: material chips, round colour swatches (custom colour is hidden until asked for), temperature."""
        i = self.view_tool if i is None else i
        self.view = "tool_edit"
        self.view_tool = i
        self._clear()
        self.root.pack_start(self._header(f"Filament, toolhead {i + 1}", back=lambda: self.show_tool(i),
                                          action=("complete", "Save", "color1", self._save_tool)), False, False, 0)
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        page.set_margin_start(4)
        page.set_margin_end(10)

        prev_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.w["e_swatch"] = self._swatch(84, 84)
        prev_row.pack_start(self.w["e_swatch"], False, False, 0)
        self.w["e_desc"] = self._label()
        self.w["e_desc"].set_halign(Gtk.Align.START)
        prev_row.pack_start(self.w["e_desc"], True, True, 0)
        page.pack_start(prev_row, False, False, 0)

        crow = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        crow.pack_start(self._section("Colour"), True, True, 0)
        hsv = self._button("fine-tune", "Color Picker", "color1", self.show_hsv_pick)
        hsv.set_size_request(190, self.sz["btn_h"])
        more = self._button("fine-tune", "More colours", "color1", self.show_color_pick, 0, 0)
        more.set_size_request(230, self.sz["btn_h"])
        crow.set_margin_end(0)
        crow.pack_end(more, False, False, 0)
        crow.pack_end(hsv, False, False, 0)
        page.pack_start(crow, False, False, 0)
        dots = Gtk.Grid()
        dots.set_row_spacing(8)
        dots.set_column_spacing(8)
        dots.set_column_homogeneous(True)
        self.w["dots"] = {}
        for n, (name, col) in enumerate(COLOR_PRESETS):
            dot = Gtk.EventBox()
            dot.set_size_request(self.sz["dot"], self.sz["dot"])
            dot.set_halign(Gtk.Align.CENTER)
            dot.get_style_context().add_class("zr_dot")
            self._set_swatch(dot, col)
            dot.connect("button-release-event", lambda *_a, c=col: self._pick_color(c))
            dots.attach(dot, n % 6, n // 6, 1, 1)
            self.w["dots"][col] = dot
        page.pack_start(dots, False, False, 0)

        custom = self._button("fine-tune", "Custom colour", "color3", self._toggle_rgb)
        custom.set_size_request(-1, self.sz["btn_h"])
        page.pack_start(custom, False, False, 0)
        rgb_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        rgb_box.set_no_show_all(True)
        self.w["rgb_box"] = rgb_box
        self.w["sliders"] = []
        r, g, bl = _rgb(self.edit["color"])
        for name, val in (("R", r), ("G", g), ("B", bl)):
            srow = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            srow.pack_start(self._label(name), False, False, 0)
            sc = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 255, 1)
            sc.set_value(val)
            sc.set_draw_value(True)
            sc.set_value_pos(Gtk.PositionType.RIGHT)
            sc.connect("value-changed", self._slider_changed)
            srow.pack_start(sc, True, True, 0)
            self.w["sliders"].append(sc)
            rgb_box.pack_start(srow, False, False, 0)
        page.pack_start(rgb_box, False, False, 0)

        page.pack_start(self._section("Material"), False, False, 0)
        mats = Gtk.Grid()
        mats.set_row_spacing(6)
        mats.set_column_spacing(6)
        mats.set_column_homogeneous(True)
        self.w["chips"] = {}
        for n, (name, _t) in enumerate(MATERIALS):
            chip = Gtk.Button(label=name)
            chip.get_style_context().add_class("zr_chip")
            chip.set_size_request(-1, self.sz["btn_h"] - 4)
            chip.connect("clicked", lambda _w, idx=n: self._pick_material(idx))
            mats.attach(chip, n % 4, n // 4, 1, 1)
            self.w["chips"][n] = chip
        page.pack_start(mats, False, False, 0)

        page.pack_start(self._section("Nozzle temperature"), False, False, 0)
        page.pack_start(self._stepper_row("temp", "Temp", -5, 5), False, False, 0)
        page.pack_start(self._section("Pressure advance"), False, False, 0)
        page.pack_start(self._stepper_row("pa", "PA", -0.002, 0.002), False, False, 0)

        self.root.pack_start(self._scrolled(page), True, True, 0)
        self.root.show_all()
        rgb_box.hide()
        self._update_editor()

    # ------------------------------------------------------------------
    # COLOUR PAGE (F-198): the colour lists of OrcaSlicer's picker, 4 categories, paged
    # ------------------------------------------------------------------
    def show_color_pick(self, cat=None, page=None):
        if cat is not None:
            self._cp_cat = int(cat)
            self._cp_page = int(page or 0)
            if cat == 0 and page == 0 and not self.__dict__.get("_cp_open"):
                pass
        if "_cp_start" not in self.__dict__ or self.view != "color_pick":
            self._cp_start = int(self.edit["color"])          # Cancel puts this colour back
        i = self.view_tool
        self.view = "color_pick"
        cat = getattr(self, "_cp_cat", 0)
        pg = getattr(self, "_cp_page", 0)
        self._clear()
        self.root.pack_start(self._header("Colour, toolhead %d" % (i + 1), action=("complete", "Use colour", "color1", self._cp_done)), False, False, 0)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_margin_start(4)
        box.set_margin_end(10)
        chips = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        chips.set_homogeneous(True)
        for n, (lname, items) in enumerate(L.COLOR_LISTS):
            chip = Gtk.Button(label="%s (%d)" % (lname, len(items)))
            chip.get_style_context().add_class("zr_chip")
            if n == cat:
                chip.get_style_context().add_class("zr_chip_on")
            chip.set_size_request(-1, self.sz["btn_h"] - 8)
            chip.connect("clicked", lambda _w, c=n: self.show_color_pick(c, 0))
            chips.pack_start(chip, True, True, 0)
        box.pack_start(chips, False, False, 0)
        items = L.COLOR_LISTS[cat][1]
        cols = 4 if self.portrait else 6
        rows = 6 if (self.portrait or getattr(self._screen, "height", 480) >= 800) else 3
        per = cols * rows
        pages = max(1, (len(items) + per - 1) // per)
        pg = max(0, min(pg, pages - 1))
        self._cp_page = pg
        grid = Gtk.Grid()
        grid.set_row_spacing(6)
        grid.set_column_spacing(6)
        grid.set_column_homogeneous(True)
        self.w["cp_tiles"] = {}
        dsz = max(26, int(self.sz["dot"] * 0.55))
        for k, (name, col) in enumerate(items[pg * per:(pg + 1) * per]):
            tile = Gtk.EventBox()
            tile.get_style_context().add_class("zr_card")
            tb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
            tb.set_border_width(3)
            dot = Gtk.EventBox()
            dot.set_size_request(dsz, dsz)
            dot.set_halign(Gtk.Align.CENTER)
            dot.get_style_context().add_class("zr_dot")
            self._set_swatch(dot, col)
            tb.pack_start(dot, False, False, 0)
            nl = Gtk.Label()
            nl.set_markup("<span size='small'>%s</span>" % GLib.markup_escape_text(name))
            nl.set_ellipsize(Pango.EllipsizeMode.END)
            nl.set_max_width_chars(14)
            hl = Gtk.Label()
            hl.set_markup("<span size='x-small' foreground='#8a96a3'>#%06X</span>" % col)
            tb.pack_start(nl, False, False, 0)
            tb.pack_start(hl, False, False, 0)
            tile.add(tb)
            tile.connect("button-release-event", lambda *_a, c=col: self._cp_pick(c))
            grid.attach(tile, k % cols, k // cols, 1, 1)
            self.w["cp_tiles"][col] = tile
        box.pack_start(grid, True, True, 0)
        nav = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        prev = self._button("arrow-left", "Prev", "color3", self.show_color_pick, cat, pg - 1)
        nxt = self._button("arrow-right", "Next", "color3", self.show_color_pick, cat, pg + 1)
        for b in (prev, nxt):
            b.set_size_request(110, self.sz["btn_h"] - 6)
        prev.set_sensitive(pg > 0)
        nxt.set_sensitive(pg < pages - 1)
        self.w["cp_swatch"] = self._swatch(30, 30)
        self.w["cp_text"] = self._label()
        self.w["cp_text"].set_halign(Gtk.Align.START)
        nav.pack_start(prev, False, False, 0)
        nav.pack_start(self.w["cp_swatch"], False, False, 0)
        nav.pack_start(self.w["cp_text"], True, True, 0)
        pl = self._label()
        pl.set_markup("<span size='small'>%d / %d</span>" % (pg + 1, pages))
        nav.pack_start(pl, False, False, 0)
        nav.pack_start(nxt, False, False, 0)
        box.pack_start(nav, False, False, 0)
        self.root.pack_start(box, True, True, 0)
        self.root.show_all()
        self._cp_refresh()

    # ------------------------------------------------------------------
    # HSV COLOUR PICKER (F-199): hue / saturation / brightness sliders with a big preview
    # ------------------------------------------------------------------
    def show_hsv_pick(self):
        if "_cp_start" not in self.__dict__ or self.view not in ("color_pick", "hsv_pick"):
            self._cp_start = int(self.edit["color"])
        i = self.view_tool
        self.view = "hsv_pick"
        r, g, b = _rgb(int(self.edit["color"]))
        h, sat, val = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
        self._hsv = [h * 360.0, sat * 100.0, val * 100.0]
        self._clear()
        self.root.pack_start(self._header("Color picker, toolhead %d" % (i + 1), action=("complete", "Use colour", "color1", self._cp_done)), False, False, 0)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_start(4)
        box.set_margin_end(10)
        area = Gtk.DrawingArea()
        area.set_size_request(-1, 200)
        area.set_vexpand(True)
        area.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK | Gdk.EventMask.POINTER_MOTION_MASK | Gdk.EventMask.BUTTON1_MOTION_MASK)
        area.connect("draw", self._sv_draw)
        area.connect("button-press-event", self._sv_event)
        area.connect("motion-notify-event", self._sv_event)
        self.w["hs_area"] = area
        box.pack_start(area, True, True, 0)
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.w["hs_swatch"] = self._swatch(58, 58)
        row.pack_start(self.w["hs_swatch"], False, False, 0)
        self.w["hs_text"] = self._label()
        self.w["hs_text"].set_size_request(210, -1)
        row.pack_start(self.w["hs_text"], False, False, 0)
        sc = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 360, 1)
        sc.set_value(self._hsv[0])
        sc.set_draw_value(False)
        sc.set_size_request(-1, 40)
        prov = Gtk.CssProvider()
        sc.get_style_context().add_provider(prov, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 5)
        try:
            prov.load_from_data(("scale trough { background-image: linear-gradient(to right, #f00, #ff0, #0f0, #0ff, #00f, #f0f, #f00); min-height: 22px; border-radius: 11px; } "
                                 "scale highlight { background: none; } "
                                 "scale slider { min-width: 30px; min-height: 30px; border-radius: 15px; background: #ffffff; border: 3px solid #2196f3; }").encode())
        except Exception:
            pass
        sc.connect("value-changed", self._hue_changed)
        self.w["hs_hue"] = sc
        row.pack_start(sc, True, True, 0)
        box.pack_start(row, False, False, 0)
        self.root.pack_start(box, True, True, 0)
        self.root.show_all()
        self._hsv_refresh()

    def _sv_draw(self, area, cr):
        w, h = area.get_allocated_width(), area.get_allocated_height()
        hr, hg, hb = colorsys.hsv_to_rgb(self._hsv[0] / 360.0, 1.0, 1.0)
        cr.set_source_rgb(hr, hg, hb)
        cr.rectangle(0, 0, w, h)
        cr.fill()
        gw = cairo.LinearGradient(0, 0, w, 0)
        gw.add_color_stop_rgba(0, 1, 1, 1, 1)
        gw.add_color_stop_rgba(1, 1, 1, 1, 0)
        cr.set_source(gw)
        cr.rectangle(0, 0, w, h)
        cr.fill()
        gb = cairo.LinearGradient(0, 0, 0, h)
        gb.add_color_stop_rgba(0, 0, 0, 0, 0)
        gb.add_color_stop_rgba(1, 0, 0, 0, 1)
        cr.set_source(gb)
        cr.rectangle(0, 0, w, h)
        cr.fill()
        x = self._hsv[1] / 100.0 * w
        y = (1.0 - self._hsv[2] / 100.0) * h
        cr.set_line_width(3)
        cr.set_source_rgb(1, 1, 1)
        cr.arc(x, y, 11, 0, 6.2832)
        cr.stroke()
        cr.set_line_width(1.5)
        cr.set_source_rgb(0, 0, 0)
        cr.arc(x, y, 13, 0, 6.2832)
        cr.stroke()
        return False

    def _sv_event(self, area, ev):
        w, h = max(1, area.get_allocated_width()), max(1, area.get_allocated_height())
        self._hsv[1] = max(0.0, min(100.0, ev.x / w * 100.0))
        self._hsv[2] = max(0.0, min(100.0, (1.0 - ev.y / h) * 100.0))
        self._hsv_apply()
        return True

    def _hue_changed(self, sc):
        self._hsv[0] = sc.get_value()
        self._hsv_apply()

    def _hsv_apply(self):
        r, g, b = colorsys.hsv_to_rgb(self._hsv[0] / 360.0, self._hsv[1] / 100.0, self._hsv[2] / 100.0)
        self.edit["color"] = (int(round(r * 255)) << 16) | (int(round(g * 255)) << 8) | int(round(b * 255))
        self._hsv_refresh()

    def _hsv_refresh(self):
        if self.view != "hsv_pick":
            return
        col = int(self.edit["color"])
        self._set_swatch(self.w["hs_swatch"], col)
        self.w["hs_text"].set_markup("<b>%s</b>  #%06X" % (GLib.markup_escape_text(_color_name(col)), col))
        self.w["hs_area"].queue_draw()

    def _cp_pick(self, col):
        self.edit["color"] = int(col)
        self._cp_refresh()

    def _cp_refresh(self):
        col = int(self.edit["color"])
        if self.view != "color_pick":
            return
        self._set_swatch(self.w["cp_swatch"], col)
        self.w["cp_text"].set_markup("<b>%s</b>  #%06X" % (GLib.markup_escape_text(_color_name(col)), col))
        for c, tile in self.w.get("cp_tiles", {}).items():
            ctx = tile.get_style_context()
            (ctx.add_class if c == col else ctx.remove_class)("zr_card_sel")

    def _cp_done(self):
        self.__dict__.pop("_cp_start", None)
        self.show_tool_edit(self.view_tool)


    def _toggle_rgb(self):
        box = self.w.get("rgb_box")
        if box is None:
            return
        if box.get_visible():
            box.hide()
        else:
            box.show_all()

    def _section(self, text):
        lbl = self._label()
        lbl.set_markup(f"<b>{text}</b>")
        lbl.set_halign(Gtk.Align.START)
        lbl.get_style_context().add_class("zr_section")
        return lbl

    def _stepper_row(self, key, title, down, up):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        row.pack_start(self._label(title), False, False, 0)
        minus = self._button("decrease", None, "color3", self._step, key, down)
        plus = self._button("increase", None, "color3", self._step, key, up)
        for b in (minus, plus):
            b.set_size_request(80, self.sz["btn_h"])
        self.w[f"v_{key}"] = self._label()
        row.pack_start(minus, False, False, 0)
        row.pack_start(self.w[f"v_{key}"], True, True, 0)
        row.pack_start(plus, False, False, 0)
        return row

    def _step(self, key, delta):
        if key == "temp":
            self.edit["temp"] = max(0, min(320, int(self.edit["temp"] + delta)))
        else:
            self.edit["pa"] = round(max(0.0, min(1.0, self.edit["pa"] + delta)), 4)
        self._update_editor()

    def _pick_material(self, idx):
        self.edit["mat"] = idx
        if MATERIALS[idx][1]:
            self.edit["temp"] = MATERIALS[idx][1]
        self._update_editor()

    def _pick_color(self, col):
        self.edit["color"] = col
        for s, v in zip(self.w.get("sliders", []), _rgb(col)):
            s.handler_block_by_func(self._slider_changed)
            s.set_value(v)
            s.handler_unblock_by_func(self._slider_changed)
        self._update_editor()

    def _slider_changed(self, *_):
        r, g, b = (int(s.get_value()) for s in self.w["sliders"])
        self.edit["color"] = (r << 16) | (g << 8) | b
        self._update_editor()

    def _update_editor(self):
        if self.view != "tool_edit" or not self.edit:
            return
        self._set_swatch(self.w["e_swatch"], self.edit["color"])
        name = MATERIALS[self.edit["mat"]][0]
        self.w["e_desc"].set_markup(f"<big><b>{name}</b></big>\n<span size='small'>{_color_name(self.edit['color'])}  #{self.edit['color']:06X}</span>")
        self.w["v_temp"].set_text(f"{self.edit['temp']} C")
        self.w["v_pa"].set_text(f"{self.edit['pa']:.3f}")
        for idx, chip in self.w.get("chips", {}).items():
            ctx = chip.get_style_context()
            (ctx.add_class if idx == self.edit["mat"] else ctx.remove_class)("zr_chip_on")
        for col, dot in self.w.get("dots", {}).items():
            ctx = dot.get_style_context()
            (ctx.add_class if col == self.edit["color"] else ctx.remove_class)("zr_dot_on")

    def _save_tool(self):
        i = self.view_tool
        e = self.edit
        cidx = L.nearest_palette(int(e["color"]))      # tmt1.ini holds a swatch index, so a custom colour snaps to the closest swatch
        e["color"] = L.TOUCH_PALETTE[cidx][1]
        midx = next((n for n, m in enumerate(L.TOUCH_MATERIALS) if m[2] == int(e["mat"])), 0)
        if int(e["mat"]):
            self._write_tmt1(i, cidx, midx)
        script = (f"_ZR_SET_TOOL_INFO T={i} COLOR={int(e['color'])} "
                  f"MAT={int(e['mat'])} TEMP={int(e['temp'])}")
        old_pa = self._tool_info(i)["pa"]
        if abs(e["pa"] - old_pa) > 1e-6:
            script += f"\nZR_SET_TOOL_PA T={i} PA={e['pa']:.4f}"
        self._gcode(script, f"Toolhead {i + 1} saved")
        self.show_tool(i)

    def _refresh_tool(self):
        i = self.view_tool
        info = self._tool_info(i)
        cur, tgt = self._temps(i)
        fil = self._sensor("filament%d" % i)
        dock = self._sensor("docked%d" % i)
        has = bool(info["mat"])
        name = MATERIALS[info["mat"]][0] if has else "Empty"
        self._mark_empty(self.w["h_card"], self.w["e_swatch"], (not has) or (fil is False))
        self._set_swatch(self.w["e_swatch"], info["color"] if has else 0x303030)
        self.w["h_mat"].set_text(name)
        temp = ("%.0f\u00b0 / %.0f\u00b0" % (cur, tgt or info.get("temp") or 0)) if cur is not None else "--"
        self.w["h_col"].set_text(("%s \u00b7 %s" % (_color_name(info["color"]), temp)) if has else temp)
        if i == self._active_tool():
            self._set_pill(self.w["h_chip"], "Active", "active")
        elif has:
            self._set_pill(self.w["h_chip"], "Ready", "ready")
        else:
            self._set_pill(self.w["h_chip"], "Empty", "empty")
        state = []
        if fil is not None:
            state.append("Filament OK" if fil else "No filament")
        if dock is not None:
            state.append("In dock" if dock else "On carriage")
        self.w["h_state"].set_text("   ".join(state) if state else " ")
        ace = L.ace_tool_lines(self.st, i)
        for n, key in enumerate(("h_ace1", "h_ace2")):
            self.w[key].set_text(ace[n] if n < len(ace) else "")
            self.w[key].set_visible(n < len(ace))
        if self.w.get("a_btn") is not None:             # Feed assist button: purple + ON when on, dark grey + OFF when off
            slots = L.ace_state(self.st)["slots"]
            on = bool(slots[i]["assist"]) if 0 <= i < len(slots) else False
            ctx = self.w["a_btn"].get_style_context()
            ctx.remove_class("zr_btn_purple")
            ctx.remove_class("zr_btn_off")
            ctx.add_class("zr_btn_purple" if on else "zr_btn_off")
            self._set_pill(self.w["a_badge"], "ON" if on else "OFF", "on" if on else "off")

    # tool actions --------------------------------------------------------
    def _act_select(self, i):
        if self._require_idle():
            self._confirm("Select toolhead", f"Pick up toolhead {i + 1}?",
                          f"_CHANGE_TOOL T={i}", f"Changing to toolhead {i + 1}...")

    def _act_park(self):
        if self._require_idle():
            self._confirm("Park tool", "Return the active toolhead to its dock?",
                          "PARK_CURRENT_TOOL", "Parking the toolhead...")

    def _act_assist(self, i):
        """Feed assist of toolhead i, switched by hand. It works during a print and a pause too and stays until the next print starts or ends."""
        if not self._ace_connected():
            self._screen.show_popup_message("ACE is not connected.")
            return
        slots = L.ace_state(self.st)["slots"]
        on_now = bool(slots[i]["assist"]) if 0 <= i < len(slots) else False
        self._gcode(f"_ACE_WM_ASSIST T={i} STATE={'off' if on_now else 'on'}",
                    f"Feed assist {'off' if on_now else 'on'}, toolhead {i + 1}")

    def _act_heat(self, i):
        temp = int(self.edit["temp"] if self.edit and self.view_tool == i
                   else self._tool_info(i)["temp"]) or 220
        self._gcode(f"SET_HEATER_TEMPERATURE HEATER={_ext_name(i)} TARGET={temp}",
                    f"Heating toolhead {i + 1} to {temp} C")

    def _act_cool(self, i):
        self._gcode(f"SET_HEATER_TEMPERATURE HEATER={_ext_name(i)} TARGET=0",
                    f"Toolhead {i + 1} heater off")

    def _ace_connected(self):
        return L.has_ace(self.st) and bool(L.ace_state(self.st)["connected"])

    def _act_load(self, i):
        if not self._require_idle():
            return
        if self._ace_connected():           # ACE feeds the filament to this toolhead
            self._confirm("Load from ACE", f"Feed ACE slot {i + 1} to toolhead {i + 1} and load it?",
                          f"ACE_WM_LOAD T={i}", f"ACE loading T{i + 1}")
            return
        self._confirm("Load filament",
                      f"Press OK: toolhead {i + 1} is picked up and heated at the wipe area to its saved temperature.\n"
                      "Then insert the filament until you feel resistance: the printer loads it by itself.\n"
                      "Filament already in: it pushes a little, wipes and parks.",
                      f"_ZR_LOAD T={i}", "Heating for the load...")

    def _act_unload(self, i):
        if not self._require_idle():
            return
        if self._ace_connected():           # ACE pulls the filament back into its slot
            self._confirm("Unload to ACE", f"Unload toolhead {i + 1} and pull the filament back into ACE slot {i + 1}?",
                          f"ACE_WM_UNLOAD T={i}", f"ACE unloading T{i + 1}")
            return
        self._confirm("Unload filament",
                      f"Unload filament from toolhead {i + 1}?\n"
                      "It picks up the toolhead, heats it at the wipe area to the saved temperature, forms the tip and parks.\n"
                      "Then pull the filament out by hand.",
                      f"_ZR_RETRACT T={i}", "Unloading...")

    # ------------------------------------------------------------------
    # MAPPING VIEW
    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    # F-208: Choose toolheads page. Opens before a print starts from the screen (Print menu, Restart on the print status page)
    # and from ZR Tools > More > Tool mapping (then without a file: every tap is applied at once).
    # ------------------------------------------------------------------
    @staticmethod
    def _map_base(path):
        return str(path or "").split("/")[-1].replace('"', "").replace("'", "").replace("\\", "")

    @staticmethod
    def _rgb_dist(a, b):
        ar, ag, ab = _rgb(a)
        br, bg, bb = _rgb(b)
        return (ar - br) ** 2 + (ag - bg) ** 2 + (ab - bb) ** 2

    def _map_head(self, h):
        """(info, loaded) of toolhead h (0 to 3): loaded = it has a filament and its sensor does not say empty."""
        info = self._tool_info(h)
        return info, bool(info["mat"]) and self._sensor("filament%d" % h) is not False

    def _map_default_sel(self, rows):
        """The last choice for this file (kept after a cancel or a print end), else the closest loaded toolhead per file colour."""
        v = self._vars()
        base = self._map_base(self.__dict__.get("map_file"))
        parts = str(v.get("wm_last_map", "") or "").split(",")
        if base and str(v.get("wm_last_map_file", "") or "") == base and len(parts) == NTOOLS \
                and all(x.strip() in ("0", "1", "2", "3") for x in parts):
            self.map_restored = True
            return [int(x) for x in parts]
        sel = list(range(NTOOLS))
        heads = [h for h in range(NTOOLS) if self._map_head(h)[1]]
        pairs = sorted((self._rgb_dist(r["color"], self._tool_info(h)["color"]), r["tool"], h)
                       for r in rows if r["color"] is not None for h in heads)
        done, used = set(), set()
        for _d, t, h in pairs:
            if t not in done and h not in used:
                sel[t] = h
                done.add(t)
                used.add(h)
        return sel

    def _map_begin(self, filename):
        """Ask Moonraker for the colours of the file, then show the page."""
        self.map_file = filename
        self.map_rows = None
        self.map_sel = None
        self.map_restored = False
        self.map_user = False
        self.map_fresh = False
        self.map_seq = self.__dict__.get("_status_seq", 0)      # the saved data may be old: the first update after this chooses again
        self.view = "map_start"
        self._clear()
        self.root.pack_start(self._header("Choose toolheads"), False, False, 0)
        self.root.pack_start(self._label("Reading the colours of the file...", "zr_hint", wrap=True), False, False, 0)
        self.root.show_all()
        try:
            self._screen._ws.api.get_file_metadata(filename, self._map_meta_cb)
        except Exception as e:
            logging.error(f"ZR: metadata request failed: {e}")
            GLib.idle_add(self._map_meta_done, filename, {})

    def _map_meta_cb(self, result, method, params):
        meta = result if isinstance(result, dict) and "error" not in result else {}
        GLib.idle_add(self._map_meta_done, (params or {}).get("filename"), meta)

    def _map_meta_done(self, filename, meta):
        if self.__dict__.get("map_file") != filename or self.view != "map_start":
            return False
        rows = file_colours(meta)
        if not rows:                      # no colour data in the file: slicer tools T0 to T3 without colours
            rows = [{"tool": t, "color": None, "mat": ""} for t in range(NTOOLS)]
        self.map_rows = rows
        self.map_sel = None
        self.show_map_start()
        return False

    def show_mapping(self):
        self.__dict__["map_file"] = None
        self.map_rows = [{"tool": t, "color": None, "mat": ""} for t in range(NTOOLS)]
        self.map_sel = None
        self.view = "mapping"
        self._map_page(False)

    def show_map_start(self):
        if not self.__dict__.get("map_rows"):
            self._map_begin(self.__dict__.get("map_file") or "")
            return
        self.view = "map_start"
        self._map_page(True)

    def _map_page(self, file_mode):
        rows = self.map_rows
        narrow = (self.portrait and self.density == "compact") or self.tiny
        if file_mode and self.__dict__.get("_status_seq", 0) > self.__dict__.get("map_seq", 0):
            self.map_fresh = True
        if self.map_sel is None:
            self.map_restored = False
            self.map_sel = self._map_default_sel(rows) if file_mode else list(self._mapping())
        self._clear()
        self.root.pack_start(self._header("Choose toolheads" if file_mode else "Tool mapping"), False, False, 0)
        if file_mode:
            hint = self._map_base(self.map_file) + ("\nYour last choice for this file is selected." if self.map_restored else "")
        else:
            hint = "Tap the toolhead that prints each slicer tool. WonderMaker resets it to 1:1 after every print."
        self.root.pack_start(self._label(hint, "zr_hint", wrap=True), False, False, 0)
        grid = Gtk.Grid()
        grid.set_row_spacing(6)
        grid.set_column_spacing(6)
        grid.set_column_homogeneous(False)
        grid.attach(self._label(""), 0, 0, 1, 1)
        for h in range(NTOOLS):
            c = self._label(("%d" % (h + 1)) if narrow else ("Head %d" % (h + 1)), "zr_hint")
            c.set_hexpand(True)
            grid.attach(c, 1 + h, 0, 1, 1)
        rowh = 50 if narrow else 58
        self.w["mh"] = {}
        for i, r in enumerate(rows):
            t = r["tool"]
            left = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            left.get_style_context().add_class("zr_card")
            left.set_border_width(6)
            left.set_size_request(104 if narrow else 190, rowh)
            sw = self._swatch(24, 24)
            sw.set_valign(Gtk.Align.CENTER)
            self._set_swatch(sw, r["color"] if r["color"] is not None else 0x303030)
            left.pack_start(sw, False, False, 0)
            tb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            tb.set_valign(Gtk.Align.CENTER)
            l1 = self._label()
            title = ("T%d" % t) if narrow else (("Colour %d (T%d)" % (i + 1, t)) if file_mode else ("Slicer T%d" % t))
            l1.set_markup("<b><span font='12'>%s</span></b>" % GLib.markup_escape_text(title))
            l1.set_halign(Gtk.Align.START)
            tb.pack_start(l1, False, False, 0)
            if r["color"] is not None and not narrow:
                l2 = self._label(" ".join(x for x in (r["mat"], _color_name(r["color"])) if x))
                l2.set_markup("<span font='10'>%s</span>" % GLib.markup_escape_text(l2.get_text()))
                l2.set_halign(Gtk.Align.START)
                l2.set_line_wrap(True)
                l2.set_max_width_chars(16)
                tb.pack_start(l2, False, False, 0)
            left.pack_start(tb, True, True, 0)
            grid.attach(left, 0, 1 + i, 1, 1)
            for h in range(NTOOLS):
                b = Gtk.Button()
                b.set_size_request(-1, rowh)
                b.set_hexpand(True)
                box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
                box.set_halign(Gtk.Align.CENTER)
                box.set_valign(Gtk.Align.CENTER)
                hs = self._swatch(20, 20)
                hs.set_halign(Gtk.Align.CENTER)
                hl = self._label()
                box.pack_start(hs, False, False, 0)
                box.pack_start(hl, False, False, 0)
                b.add(box)
                b.connect("clicked", lambda _w, tt=t, hh=h: self._map_pick(tt, hh))
                grid.attach(b, 1 + h, 1 + i, 1, 1)
                self.w["mh"][(t, h)] = (b, hs, hl)
        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        body.pack_start(grid, False, False, 0)
        self.w["map_note"] = self._label("", "zr_hint", wrap=True)
        body.pack_start(self.w["map_note"], False, False, 0)
        self.root.pack_start(self._scrolled(body), True, True, 0)
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        bar.set_homogeneous(True)
        reset = self._button("refresh", "Reset 1:1", "color3", self._map_reset)
        bar.pack_start(reset, True, True, 0)
        if file_mode:
            cancel = self._button(None, "Cancel", "color3", self._map_cancel)
            go = self._button(None, "Print", "color1", self._map_print)
            go.get_style_context().add_class("zr_btn_primary")
            bar.pack_start(cancel, True, True, 0)
            bar.pack_start(go, True, True, 0)
        else:
            bar.pack_start(self._button(None, "Done", "color3", self.back), True, True, 0)
        for b_ in bar.get_children():
            b_.set_size_request(-1, 56)
        self.root.pack_end(bar, False, False, 0)
        self.root.show_all()
        self._refresh_map_start()

    def _map_pick(self, t, h):
        file_mode = self.view == "map_start"
        if not self._map_head(h)[1]:
            return
        if not file_mode and not self._require_idle():
            return
        sel = list(self.map_sel)
        old = sel[t]
        for r in self.map_rows:                     # a toolhead prints one colour: the colour that had it gets the old one
            if r["tool"] != t and sel[r["tool"]] == h:
                sel[r["tool"]] = old
        sel[t] = h
        self.map_sel = sel
        self.map_restored = False
        self.map_user = True
        if not file_mode:
            self.map_touch = time.time()
            self._gcode("_ZR_MAP_SET MAP=" + ",".join(str(x) for x in sel))
        self._refresh_map_start()

    def _map_reset(self):
        file_mode = self.view == "map_start"
        if not file_mode and not self._require_idle():
            return
        self.map_sel = list(range(NTOOLS))
        self.map_restored = False
        self.map_user = True
        if not file_mode:
            self.map_touch = time.time()
            self._gcode("_ZR_MAP_RESET", "Mapping reset to 1:1")
        self._refresh_map_start()

    def _map_cancel(self):
        self.__dict__["map_file"] = None
        self.__dict__["_hist"] = []
        try:
            self._screen._menu_go_back()
        except Exception as e:
            logging.error(f"ZR: could not leave the map page: {e}")
            self.show_home()

    def _map_print(self):
        fn = self.__dict__.get("map_file")
        if not fn or not self._require_idle():
            return
        sel = [int(x) for x in self.map_sel]
        for r in self.map_rows:
            if not self._map_head(sel[r["tool"]])[1]:
                self._screen.show_popup_message("Head %d has no filament. Pick another head." % (sel[r["tool"]] + 1))
                return
        m = ",".join(str(x) for x in sel)
        base = self._map_base(fn)
        lines = ["_ZR_MAP_SET MAP=" + m]
        if base:                                  # the same variable the Fluidd window writes, plus the last choice for the file (B-080)
            lines.append("SAVE_VARIABLE VARIABLE=wm_map_file VALUE=\"'%s'\"" % base)
            lines.append("SAVE_VARIABLE VARIABLE=wm_last_map_file VALUE=\"'%s'\"" % base)
            lines.append("SAVE_VARIABLE VARIABLE=wm_last_map VALUE=\"'%s'\"" % m)
        try:
            self._screen._ws.api.gcode_script("\n".join(lines), self._map_set_cb)
        except Exception as e:
            logging.error(f"ZR: could not set the map: {e}")
            self._screen.show_popup_message("Connection error. Check Klipper.")

    def _map_set_cb(self, result, method, params):
        if isinstance(result, dict) and "error" in result:
            GLib.idle_add(self._screen.show_popup_message, "Could not set the toolhead map. The print was not started.")
            return
        GLib.idle_add(self._map_do_print)

    def _map_do_print(self):
        fn = self.__dict__.get("map_file")
        self.__dict__["map_file"] = None
        if fn:
            logging.info(f"Starting print: {fn}")
            self._screen._ws.api.print_start(fn)
        return False

    def _map_notes(self, file_mode):
        out = []
        sel = self.map_sel
        for i, r in enumerate(self.map_rows):
            h = sel[r["tool"]]
            if not self._map_head(h)[1]:
                out.append("%s is set to Head %d, which has no filament." % (("Colour %d" % (i + 1)) if file_mode else ("T%d" % r["tool"]), h + 1))
        return "\n".join(out)

    def _refresh_map_start(self):
        rows = self.__dict__.get("map_rows")
        if not rows:
            return
        file_mode = self.view == "map_start"
        if file_mode and not self.__dict__.get("map_fresh") and not self.__dict__.get("map_user") \
                and self.__dict__.get("_status_seq", 0) > self.__dict__.get("map_seq", 0):
            self.map_fresh = True                 # fresh saved data arrived after the page opened: choose again, once
            self.map_sel = None
            self._map_page(True)
            return
        if not file_mode and time.time() - self.__dict__.get("map_touch", 0) > 3:
            self.map_sel = list(self._mapping())
        sel = self.map_sel
        for (t, h), (b, hs, hl) in self.w.get("mh", {}).items():
            info, has = self._map_head(h)
            self._set_swatch(hs, info["color"] if has else 0x303030)
            hl.set_markup("<span font='11'>%s</span>" % GLib.markup_escape_text((self._mat_name(h) or "Other") if has else "Empty"))
            b.set_sensitive(has)
            ctx = b.get_style_context()
            if sel[t] == h:
                ctx.add_class("zr_selected")
            else:
                ctx.remove_class("zr_selected")
        note = self.w.get("map_note")
        if note is not None:
            note.set_text(self._map_notes(file_mode))

    # ------------------------------------------------------------------
    # UTILITIES VIEW
    # ------------------------------------------------------------------
    # F-195: the Calibration & Tools page shows big category buttons; each opens a page with its macros
    _CAL_CATS = [
        ("settings", "First run & setup", ("WM_FIRST_RUN_CAL", "WM_EXTRUDER_SETUP")),
        ("fine-tune", "Tool offsets", ("WM_OFFSETS_RAPID", "WM_SETTER_PROBE_POSITION", "WM_OFFSETS_ACCURATE", "WM_FULL_OFFSET_CAL", "WM_OFFSETS_Z_HOT", "WM_Z_TRIM_MENU", "WM_LIVE_Z_MENU", "WM_NOZZLE_GROWTH_CAL", "WM_ESTEP_CAL")),
        ("bed-level", "Bed", ("WM_BED_LEVELING", "WM_PROBE_CALIBRATE", "WM_SCREWS_CAL", "WM_BED_SOAK_MENU", "WM_BED_PID")),
        ("heat-up", "Nozzle", ("WM_NOZZLE_FULL_PID", "_WM_NOZZLE_TYPE", "WM_NOZZLE_CHANGE", "WIPE_NOZZLE", "WM_NOZZLE_CLEAN")),
        ("home", "Machine", ("G28", "PARK_CURRENT_TOOL", "M84", "WM_VIBRATION_COMP")),
        ("lock", "Grippers", ("UNLOCK", "LOCK")),
    ]

    def _cal_items(self):
        """{script name: (icon, label, script, confirm question or None)} for the macros this Pi has."""
        a = self._active_tool()
        at = a if a >= 0 else 0
        have = {str(x).strip().upper() for x in (self._sections() or [])}

        def wm(name):      # WonderMaker calibration macros (rpi-cfg/rpi_calibration.cfg, rpi_nozzle.cfg): hidden when the Pi lacks them
            return not have or ("GCODE_MACRO " + name) in have

        # The WM_* macros open their own Start / Cancel window (Fluidd and here), so they are sent straight away.
        wmitems = (
            ("settings", "First run calibration", "WM_FIRST_RUN_CAL", None),
            ("bed-level", "Bed leveling", "WM_BED_LEVELING", None),
            ("z-farther", "Probe calibrate (Z height)", "WM_PROBE_CALIBRATE", None),
            ("fine-tune", "Offsets: rapid", "WM_OFFSETS_RAPID", None),
            ("fine-tune", "Tool setter position", "WM_SETTER_PROBE_POSITION", None),
            ("fine-tune", "Offsets: accurate", "WM_OFFSETS_ACCURATE", None),
            ("fine-tune", "Full offset calibration", "WM_FULL_OFFSET_CAL", None),
            ("z-farther", "Hot Z offsets", "WM_OFFSETS_Z_HOT", None),
            ("fine-tune", "Z trim", "WM_Z_TRIM_MENU", None),
            ("fine-tune", "E-step calibration", "WM_ESTEP_CAL", None),
            ("z-farther", "Live Z adjust", "WM_LIVE_Z_MENU", None),
            ("heat-up", "Nozzle heat growth", "WM_NOZZLE_GROWTH_CAL", None),
            ("bed-level", "Bed screws", "WM_SCREWS_CAL", None),
            ("bed-level", "Bed warp wait", "WM_BED_SOAK_MENU", None),
            ("speed+", "Vibration compensation", "WM_VIBRATION_COMP", None),
            ("heat-up", "Bed PID", "WM_BED_PID", None),
            ("heat-up", "Nozzle PID", "WM_NOZZLE_FULL_PID T=%d" % at, None),
            ("extruder", "Nozzle type", "_WM_NOZZLE_TYPE", None),
            ("extruder", "Nozzle change", "WM_NOZZLE_CHANGE", None),
            ("toolchanger", "Extruder setup", "WM_EXTRUDER_SETUP", None),
            ("heat-up", "Nozzle clean", "WM_NOZZLE_CLEAN", None),     # F-212: opens its own Start / Cancel window
        )
        out = {x[2].split()[0]: x for x in wmitems if wm(x[2].split()[0])}
        for x in (("home", "Home all", "G28", "Home all axes?"),
                  ("fine-tune", "Wipe nozzle", "WIPE_NOZZLE", "Wipe the active nozzle?"),
                  ("extruder", "Park tool", "PARK_CURRENT_TOOL", "Return the active toolhead to its dock?"),
                  ("motor-off", "Motors off", "M84", "Disable all motors?"),
                  ("unlock", "Unlock gripper", "UNLOCK", "HOLD THE TOOL HEAD with your hand first. Opening the gripper lets go of it, and it falls onto the bed if nobody holds it. Open the toolhead gripper?"),
                  ("lock", "Lock gripper", "LOCK", "Close the toolhead gripper?")):
            out[x[2].split()[0]] = x
        return out

    def _cal_grid(self, buttons, tall):
        cols = 2 if self.sz["util_cols"] <= 3 else 3
        grid = Gtk.Grid()
        grid.set_row_spacing(10)
        grid.set_column_spacing(10)
        grid.set_column_homogeneous(True)
        grid.set_border_width(6)
        for n, b in enumerate(buttons):
            b.set_size_request(-1, tall)
            ctx = b.get_style_context()
            ctx.add_class("zr_btn_big")
            grid.attach(b, n % cols, n // cols, 1, 1)
        return grid

    def show_utilities(self):
        self.view = "utilities"
        self._clear()
        self.root.pack_start(self._header("Calibration &amp; Tools"), False, False, 0)
        items = self._cal_items()
        buttons = []
        for n, (icon, name, scripts) in enumerate(self._CAL_CATS):
            c = [x for x in scripts if x in items]
            if not c:
                continue
            buttons.append(self._button(icon, "%s (%d)" % (name, len(c)), "color%d" % (1 + n % 4), self.show_cal_cat, n))
        self.root.pack_start(self._scrolled(self._cal_grid(buttons, max(88, int(self.sz["tile_h"] * 2)))), True, True, 0)
        self.root.show_all()

    def show_cal_cat(self, n=None):
        if n is not None:
            self.cal_cat = n
        n = getattr(self, "cal_cat", 0)
        self.view = "cal_cat"
        self._clear()
        icon, name, scripts = self._CAL_CATS[n]
        self.root.pack_start(self._header(name), False, False, 0)
        items = self._cal_items()
        buttons = []
        for k, sc in enumerate([x for x in scripts if x in items]):
            ic, text, script, question = items[sc]
            if script == "WM_NOZZLE_GROWTH_CAL":       # F-137: the page with the on/off switch; "Measure again" starts the measurement
                buttons.append(self._button(ic, text, "color%d" % (1 + n % 4), self.show_growth))
            else:
                buttons.append(self._button(ic, text, "color%d" % (1 + n % 4), self._utility, text, script, question))
        self.root.pack_start(self._scrolled(self._cal_grid(buttons, max(80, int(self.sz["tile_h"] * 1.8)))), True, True, 0)
        self.root.show_all()

    def _utility(self, title, script, question):
        if not self._require_idle():
            return
        if question is None:            # the macro shows its own Start / Cancel window
            self._gcode(script)
        else:
            self._confirm(title, question, script, f"{title}...")

    # ------------------------------------------------------------------
    # CHAMBER VIEW
    # ------------------------------------------------------------------
    def _climate_card(self):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        card.get_style_context().add_class("zr_card")
        card.set_border_width(8)
        return card

    def show_chamber(self):
        self.view = "chamber"
        self._clear()
        self.root.pack_start(self._header("Climate"), False, False, 0)
        bh = min(self.sz["btn_h"], 42)
        ch = self._climate_card()
        ch.pack_start(self._label("CHAMBER", "zr_small"), False, False, 0)
        vals = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        vals.set_halign(Gtk.Align.CENTER)
        self.w["ch_temp"] = self._label("", "zr_value")
        self.w["ch_target"] = self._label("", "zr_small")
        self.w["ch_target"].set_valign(Gtk.Align.END)
        vals.pack_start(self.w["ch_temp"], False, False, 0)
        vals.pack_start(self.w["ch_target"], False, False, 0)
        ch.pack_start(vals, False, False, 0)

        presets = Gtk.Grid()
        presets.set_column_spacing(6)
        presets.set_column_homogeneous(True)
        off = self._button(None, "Heater off", "color3", self._chamber_set, 0)
        off.get_style_context().add_class("zr_btn_red")
        off.set_size_request(-1, bh + 16)
        presets.attach(off, 0, 0, 2, 1)
        for n, t in enumerate((40, 50, 60)):
            b = self._button(None, f"{t}\u00b0C", "color2", self._chamber_set, t)
            b.set_size_request(-1, bh + 16)
            presets.attach(b, 2 + n, 0, 1, 1)
        ch.pack_start(presets, False, False, 0)

        adj = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        adj.set_homogeneous(True)
        for text, d in (("-5\u00b0C", -5), ("+5\u00b0C", 5)):
            b = self._button(None, text, "color3", self._chamber_step, d)
            b.set_size_request(-1, bh)
            adj.pack_start(b, True, True, 0)
        ch.pack_start(adj, False, False, 0)

        fan = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        fan.set_homogeneous(True)
        on = self._button("fan", "Air filter ON", "color1", self._air_filter, 1)
        off = self._button(None, "OFF", "color3", self._air_filter, 0)
        for b in (on, off):
            b.set_size_request(-1, bh + 4)
            fan.pack_start(b, True, True, 0)
        ch.pack_start(fan, False, False, 0)
        self.w["ch_fan"] = self._label("", "zr_small")
        self.w["ch_doors"] = self._label("", "zr_small", wrap=True)
        ch.pack_start(self.w["ch_fan"], False, False, 0)
        ch.pack_start(self.w["ch_doors"], False, False, 0)

        cards = [ch]
        self._ch_dryer = bool(self._ace_connected())
        if self._ch_dryer:       # F-197: no dryer card while the ACE is off
            dry = self._climate_card()
            self._build_dryer(dry)
            cards.append(dry)
        if len(cards) == 1 and not self.portrait:                       # F-197: chamber only: one big centred card, values left, buttons right
            body = self._chamber_big_card()
        elif len(cards) == 2 and not self.portrait and not self.tiny:      # side by side on a wide screen
            body = Gtk.Grid()
            body.set_column_spacing(10)
            body.set_column_homogeneous(True)
            for n, c in enumerate(cards):
                body.attach(c, n, 0, 1, 1)
        else:                                                           # stacked, scrolls
            body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
            for c in cards:
                body.pack_start(c, False, False, 0)
        self.root.pack_start(self._scrolled(body), True, True, 0)
        self.root.show_all()
        self._refresh_view()

    @staticmethod
    def _center_banner(scr):
        """F-197: KlipperScreen's message banner is a popover under the title bar, so it sat left of the screen centre."""
        try:
            pop = scr.popup_message
            tb = scr.base_panel.titlebar
            res = tb.translate_coordinates(scr, 0, 0)
            if pop is None or res is None:
                return
            x, y = res
            rect = Gdk.Rectangle()
            rect.x = int(scr.width / 2 - x)
            rect.y = 0
            rect.width = 1
            rect.height = 1
            pop.set_pointing_to(rect)
        except Exception as e:
            logging.error(f"ZR: banner centring failed: {e}")

    def _install_banner_fix(self):
        scr = self._screen
        if getattr(scr, "_zr_banner_fix", False):
            return
        orig = scr.show_popup_message

        def wrapped(*a, **k):
            r = orig(*a, **k)
            Panel._center_banner(scr)
            return r
        scr.show_popup_message = wrapped
        scr._zr_banner_fix = True

    def _chamber_big_card(self):
        """F-197: the chamber card alone and centred: big temperature on the left, large buttons on the right."""
        bh = max(56, int(self.sz["tile_h"] * 1.3))
        card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=18)
        card.get_style_context().add_class("zr_card")
        card.set_border_width(12)
        card.set_halign(Gtk.Align.FILL)
        card.set_valign(Gtk.Align.CENTER)
        left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        left.set_valign(Gtk.Align.CENTER)
        left.set_halign(Gtk.Align.CENTER)
        left.pack_start(self._label("CHAMBER", "zr_small"), False, False, 0)
        self.w["ch_temp"] = self._label("", "zr_value_xl")
        self.w["ch_target"] = self._label("", "zr_small", wrap=True)
        self.w["ch_fan"] = self._label("", "zr_small")
        self.w["ch_doors"] = self._label("", "zr_small", wrap=True)
        for k in ("ch_temp", "ch_target", "ch_fan", "ch_doors"):
            left.pack_start(self.w[k], False, False, 0)
        card.pack_start(left, True, True, 0)
        grid = Gtk.Grid()
        grid.set_row_spacing(8)
        grid.set_column_spacing(8)
        grid.set_column_homogeneous(True)
        grid.set_valign(Gtk.Align.CENTER)
        cells = [("Heater off", "color3", "zr_btn_red", self._chamber_set, 0), ("40\u00b0C", "color2", "zr_btn_green", self._chamber_set, 40),
                 ("50\u00b0C", "color2", "zr_btn_green", self._chamber_set, 50), ("60\u00b0C", "color2", "zr_btn_green", self._chamber_set, 60),
                 ("-5\u00b0C", "color3", "", self._chamber_step, -5), ("+5\u00b0C", "color3", "", self._chamber_step, 5),
                 ("Air filter ON", "color3", "zr_btn_purple", self._air_filter, 1), ("Air filter OFF", "color3", "", self._air_filter, 0)]
        for n, (text, style, cls, cb, arg) in enumerate(cells):
            b = self._button(None, text, style, cb, arg)
            if cls:
                b.get_style_context().add_class(cls)
            b.set_size_request(-1, bh)
            grid.attach(b, n % 2, n // 2, 1, 1)
        card.pack_start(grid, True, True, 0)
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        outer.set_vexpand(True)
        outer.set_valign(Gtk.Align.CENTER)
        outer.set_margin_start(6)
        outer.set_margin_end(6)
        outer.pack_start(card, False, False, 0)
        return outer

    def _chamber_target(self):
        return float((self.st.get("heater_generic chamber") or {}).get("target") or 0)

    def _chamber_set(self, t):
        self._gcode(f"_ZR_CHAMBER S={int(t)}", "Chamber off" if t == 0 else f"Chamber -> {t} C")

    def _chamber_step(self, d):
        t = max(0, min(CHAMBER_MAX, int(self._chamber_target() + d)))
        self._chamber_set(t)

    def _air_filter(self, on):
        self._gcode(f"_ZR_AIR_FILTER S={on}", "Air filter on" if on else "Air filter off")

    def _refresh_chamber(self):
        ch = self.st.get("heater_generic chamber")
        if isinstance(ch, dict) and ch.get("temperature") is not None:
            tgt = ch.get("target") or 0
            self.w["ch_temp"].set_text("%.0f\u00b0" % ch["temperature"])
            self.w["ch_target"].set_text("target %.0f\u00b0" % tgt if tgt else "heater off")
        else:
            self.w["ch_temp"].set_text("--")
            self.w["ch_target"].set_text("Chamber heater not found (is zru-s.cfg included?)")
        fan = self.st.get("fan_generic air_fan")
        if isinstance(fan, dict) and fan.get("speed") is not None:
            self.w["ch_fan"].set_text(f"Air filter {fan['speed'] * 100:.0f}%")
        else:
            self.w["ch_fan"].set_text("Air filter: --")
        doors = []
        for n in (1, 2):
            d = self.st.get(f"gcode_button Door_button{n}")
            if isinstance(d, dict) and d.get("state"):
                doors.append(f"{n}: {str(d['state']).lower()}")
        self.w["ch_doors"].set_text(("Doors  " + "   ".join(doors)) if doors else "")
        self._refresh_dryer()

    # ------------------------------------------------------------------
    def _refresh_view(self):
        try:
            if self.view == "main":
                self._refresh_main()
            elif self.view == "tool":
                self._refresh_tool()
            elif self.view == "tool_edit":
                pass
            elif self.view in ("mapping", "map_start"):
                self._refresh_map_start()
            elif self.view == "chamber":
                if bool(self._ace_connected()) != getattr(self, "_ch_dryer", None):      # F-197: the ACE came back or went away: rebuild, the dryer card appears or goes
                    self.show_chamber()
                else:
                    self._refresh_chamber()
            elif self.view == "growth":
                self._refresh_growth()
            else:
                self.refresh_extra_views()
            self._rebuild_nav_if_needed()
            self._mark_nav()
        except Exception as e:
            logging.debug(f"ZR: refresh error: {e}")

    def _add_css(self):
        css = L.build_css(self.settings.get("theme"), self.settings.get("style"), self.density, self.scale).encode()
        if getattr(self, "_css_provider", None) is None:
            self._css_provider = Gtk.CssProvider()
            Gtk.StyleContext.add_provider_for_screen(
                Gdk.Screen.get_default(), self._css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        try:
            self._css_provider.load_from_data(css)
        except Exception as e:      # a bad style must never stop the panel from opening
            logging.warning(f"ZR: could not load the style: {e}")
