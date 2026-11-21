# ZR Tools: logic that has no screen code in it, so it can be tested without KlipperScreen/GTK.
# Settings, ACE state, calibration list, collision settings, dryer presets, small helpers.

import configparser
import glob
import os
import subprocess

SETTINGS_FILE = os.path.expanduser("~/printer_data/config/zr_screen.conf")
DEFAULTS = {"layout": "tabs", "density": "comfortable", "theme": "dark", "style": "soft"}
LAYOUTS = ("tabs", "grid")          # C (big touch, tabs) and A (card grid)
DENSITIES = ("auto", "compact", "comfortable")
THEMES = ("dark", "light")
STYLES = ("soft", "flat", "bold", "classic")    # the look of cards, chips and colour dots
COMPACT_MAX_WIDTH = 900             # the long side: 800x480 and 480x800 are compact, 1024x600 and 600x1024 are comfortable
TINY_MAX_SHORT = 400                # the short side: 480x320 and 480x272 (3.5 and 4 inch) get the "tiny" layout
WIDE_MIN_LONG = 1200                # the long side: 1280x800 and up (9 to 10 inch) get more columns
SCALE_MIN, SCALE_MAX = 0.75, 1.5    # buttons and text never shrink or grow more than this
REF_SHORT = {"compact": 480, "comfortable": 600}   # the short side the base sizes were made for
COMPACT_MAX_SHORT = 520             # the short side: 480 (5 inch class) is compact, 600 (7 inch 1024x600) is comfortable


def load_settings(path=None):
    """Read the layout settings; anything missing or invalid falls back to the defaults."""
    out = dict(DEFAULTS)
    cp = configparser.ConfigParser()
    try:
        cp.read(path or SETTINGS_FILE)
        sec = cp["screen"] if cp.has_section("screen") else {}
    except (configparser.Error, OSError):
        return out
    for key, allowed in (("layout", LAYOUTS), ("density", DENSITIES), ("theme", THEMES), ("style", STYLES)):
        val = str(sec.get(key, "")).strip().lower() if sec else ""
        if val in allowed:
            out[key] = val
    return out


def save_settings(settings, path=None):
    path = path or SETTINGS_FILE
    cp = configparser.ConfigParser()
    cp["screen"] = {k: settings.get(k, DEFAULTS[k]) for k in DEFAULTS}
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        f.write("# Written by ZR Tools (Settings page) and ./installer.sh --screen-layout\n")
        cp.write(f)
    os.replace(tmp, path)


def _px(value):
    """A pixel count, or 0 when the value is missing or not a number."""
    return int(value) if isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0 else 0


def screen_profile(width, height=None):
    """Orientation and size class of the screen, from its pixels.
    portrait: taller than wide (480x800, 600x1024); landscape otherwise (800x480, 1024x600).
    class: "small" = 800x480 or smaller (a 5 inch, and many 7 inch, screens), "large" = 1024x600 and up."""
    w, h = _px(width), _px(height)
    portrait = bool(w and h and h > w)
    short, long_ = (min(w, h), max(w, h)) if (w and h) else (w, w)
    small = (short <= COMPACT_MAX_SHORT) or (long_ <= COMPACT_MAX_WIDTH)
    known = bool(w and h)
    return {"portrait": portrait, "class": "small" if small else "large", "width": w, "height": h,
            "tiny": bool(known and short <= TINY_MAX_SHORT),
            "wide": bool(known and not portrait and long_ >= WIDE_MIN_LONG)}


def scale_factor(density, width, height=None):
    """How much to grow or shrink buttons and text for the real pixel size: 1.0 at 800x480 (compact) and 1024x600
    (comfortable), smaller below, larger above, within SCALE_MIN..SCALE_MAX. 1.0 when the height is unknown."""
    w, h = _px(width), _px(height)
    if not (w and h):
        return 1.0
    ref = REF_SHORT.get(density, REF_SHORT["compact"])
    return round(max(SCALE_MIN, min(SCALE_MAX, min(w, h) / float(ref))), 2)


def resolve_density(setting, width, height=None):
    if setting in ("compact", "comfortable"):
        return setting
    return "compact" if screen_profile(width, height)["class"] == "small" else "comfortable"


def sizes(density, portrait=False, width=None, height=None):
    """Pixel sizes and column counts used by the views for a density and an orientation."""
    if density == "compact":
        out = {"btn_h": 40, "tile_h": 44, "nav_h": 52, "cols": 2}
    else:
        out = {"btn_h": 54, "tile_h": 60, "nav_h": 64, "cols": 3}
    prof = screen_profile(width, height)
    k = scale_factor(density, width, height)
    for key in ("btn_h", "tile_h", "nav_h"):
        out[key] = int(round(out[key] * k))
    out["scale"] = k
    out["tiny"] = prof["tiny"]
    out["portrait"] = bool(portrait)
    out["tool_cols"] = 2 if portrait else 4        # toolhead cards per row: 2x2 on a tall screen
    out["util_cols"] = 2 if portrait else 3        # calibration tiles per row
    if portrait:
        out["cols"] = 2                            # hub and More tiles
    if prof["wide"] and density == "comfortable":
        out["cols"] = out["util_cols"] = 4        # a 9 to 10 inch screen has room for more tiles per row
    out["dot"] = int(round((56 if (portrait and density == "compact") else 64) * k))   # round colour swatches in the editor
    return out


def short_label(label, portrait, density):
    """Tab and button labels shortened on a narrow (5 inch, tall) screen, where six tabs share 480 px."""
    if portrait and density == "compact":
        return {"Toolheads": "Heads", "Calibrate": "Calib."}.get(label, label)
    return label


# --------------------------------------------------------------------------------------
# ACE Pro (same data model as the Fluidd panel: wm-ultra-fluidd-acepro-panel)
# --------------------------------------------------------------------------------------
DRY_PRESETS = [("PLA", 45, 4), ("PETG", 55, 6), ("ABS/ASA", 65, 6), ("TPU", 50, 6), ("Nylon/PA", 65, 8), ("PVA", 45, 6)]
DRY_MAX_TEMP = 65


def has_ace(objects):
    return objects.get("gcode_macro _WM_ACE") is not None or objects.get("ace") is not None \
        or isinstance(objects.get("ace_instance_0"), dict)


def dry_remaining_text(dryer):
    """ACE Pro reports minutes, ACE 2 seconds (as the Fluidd panel does)."""
    remain = max(0, dryer.get("remain_time") or 0)
    duration = dryer.get("duration") or 0
    if duration > 0:
        total = remain if remain > duration + 1 else remain * 60
    else:
        total = remain * 60 if remain < 1000 else remain
    h, m = int(total // 3600), int((total % 3600) // 60)
    return "%dh %02dm" % (h, m) if h > 0 else "%dm" % m


def ace_state(objects, ntools=4):
    inst = objects.get("ace_instance_0")
    inst = inst if isinstance(inst, dict) else {}
    wm = objects.get("gcode_macro _WM_ACE") or {}
    conn = inst.get("connection_state")
    connected = bool(inst) and (conn is None or conn == "connected")
    dryer = inst.get("dryer_status") or inst.get("dryer") or {"status": "stop"}
    drying = str(dryer.get("status", "stop")) not in ("stop", "stopped", "idle", "unknown")
    slots_raw = inst.get("slots") if isinstance(inst.get("slots"), list) else []
    feed_assist = inst.get("feed_assist_slot")
    slots = []
    for i in range(ntools):
        slot = next((s for s in slots_raw if isinstance(s, dict) and s.get("index") == i), None)
        mode = str(wm.get("mode", "idle"))
        if str(wm.get("tool")) == str(i) and mode.startswith("load"):
            text = "loading"
        elif str(wm.get("tool")) == str(i) and mode.startswith("unload"):
            text = "unloading"
        elif feed_assist == i:
            text = "assist"
        elif slot is None:
            text = "no data"
        elif slot.get("status") == "empty":
            text = "empty"
        elif slot.get("status") == "ready":
            text = "ready"
        else:
            text = str(slot.get("status", "unknown"))
        sw = objects.get("filament_switch_sensor path_%d" % i)
        slots.append({"index": i, "text": text, "empty": slot is not None and slot.get("status") == "empty",
                      "assist": feed_assist == i,
                      "hub": None if sw is None else sw.get("filament_detected") is True})
    return {"connected": connected, "state": conn or ("ACE" if inst else "no data"),
            "model": inst.get("model", "ACE"), "firmware": inst.get("firmware", ""),
            "temp": inst.get("temp"), "humidity": inst.get("humidity"),
            "drying": drying, "dryer": dryer, "dry_left": dry_remaining_text(dryer) if drying else "",
            "max_temp": inst.get("max_dryer_temperature") or DRY_MAX_TEMP, "slots": slots,
            "endless_available": objects.get("gcode_macro _WM_ENDLESS_CONTINUE") is not None}


def ace_tool_lines(objects, tool):
    """Up to two short lines about the ACE slot that feeds this tool (tool N = slot N), for the Filament page."""
    if not has_ace(objects):
        return []
    a = ace_state(objects)
    if not a["connected"]:
        return ["ACE: not connected"]
    slot = a["slots"][tool] if 0 <= tool < len(a["slots"]) else None
    first = "ACE slot %d: %s" % (tool + 1, slot["text"] if slot else "no data")
    if slot and slot["assist"]:
        first += " \u00b7 feed assist on"
    elif slot:
        first += " \u00b7 feed assist off"
    second = "ACE %s\u00b0" % ("%.0f" % a["temp"] if isinstance(a["temp"], (int, float)) else "--")
    second += (" \u00b7 drying, %s left" % a["dry_left"]) if a["drying"] else " \u00b7 dryer off"
    return [first, second]


def ace_card_text(objects, tool):
    """Short ACE line for a tool card on the Toolheads page ('' when there is no ACE)."""
    if not has_ace(objects):
        return ""
    a = ace_state(objects)
    if not a["connected"]:
        return "ACE offline"
    slot = a["slots"][tool] if 0 <= tool < len(a["slots"]) else None
    return "ACE %d: %s" % (tool + 1, slot["text"] if slot else "no data")


def ace_bar_text(objects):
    """One line for the top of the Toolheads page ('' when there is no ACE)."""
    if not has_ace(objects):
        return ""
    a = ace_state(objects)
    if not a["connected"]:
        return "ACE: not connected"
    temp = "%.0f\u00b0" % a["temp"] if isinstance(a["temp"], (int, float)) else "--"
    return "ACE %s \u00b7 %s" % (temp, ("drying, %s left" % a["dry_left"]) if a["drying"] else "dryer off")


def endless_sets(keys):
    """Endless spool: the sets of two or more toolheads with the same material and colour, each in number order
    (the same rule as the Fluidd panel). keys[i] is "mat/color" or None."""
    sets = []
    for i, key in enumerate(keys):
        if key is None or any(i in s for s in sets):
            continue
        s = [j for j, k in enumerate(keys) if k == key]
        if len(s) > 1:
            sets.append(s)
    return sets


def endless_next(frm, keys, loaded):
    """Toolheads that can take over for toolhead frm, in the order the printer tries them."""
    out = []
    key = keys[frm] if 0 <= frm < len(keys) else None
    if key is None:
        return out
    for k in range(1, len(keys)):
        c = (frm + k) % len(keys)
        if keys[c] == key and (loaded is None or loaded[c] is True):
            out.append(c)
    return out


def endless_auto(variables):
    try:
        return int(float(variables.get("wm_endless_auto", 1))) == 1
    except (TypeError, ValueError):
        return True


def endless_enabled(variables):
    try:
        return int(float(variables.get("wm_endless", 0))) == 1
    except (TypeError, ValueError):
        return False


def clamp_dry(temp, hours, max_temp=DRY_MAX_TEMP):
    return max(30, min(int(temp), int(max_temp))), max(1, min(int(hours), 24))


# --------------------------------------------------------------------------------------
# Calibration list: only macros that exist on this printer are offered
# --------------------------------------------------------------------------------------
# (icon, label, gcode, question, requires)  requires: macro name, "klipper:<cmd>" or "object:<name>"
CALIBRATION = [
    ("z-farther", "Z offset (active tool)", "CALIBRATE_TOOL_Z_OFFSET T={tool}", "Calibrate the Z offset of toolhead T{tool}?", "CALIBRATE_TOOL_Z_OFFSET"),
    ("move", "XY offset (active tool)", "CALIBRATE_TOOL_OFFSET T={tool}", "Calibrate the XY offset of toolhead T{tool}?\nThis heats the nozzle.", "CALIBRATE_TOOL_OFFSET"),
    ("fine-tune", "Offsets, all: fine", "CALIBRATE_OFFSET_ALL_FINE_MODE", "Calibrate the offsets of all toolheads (fine mode)?\nThis heats the nozzles.", "CALIBRATE_OFFSET_ALL_FINE_MODE"),
    ("fine-tune", "Offsets, all: rapid", "CALIBRATE_OFFSET_ALL_RAPID_MODE", "Calibrate the offsets of all toolheads (rapid mode)?", "CALIBRATE_OFFSET_ALL_RAPID_MODE"),
    ("move", "Tool position", "CALIBRATE_TOOL_POSITION", "Calibrate the dock position of the active toolhead?", "CALIBRATE_TOOL_POSITION"),
    ("move", "Wipe position", "CALIBRATE_WIPE_POSITION", "Calibrate the wipe position?", "CALIBRATE_WIPE_POSITION"),
    ("bed-mesh", "Bed mesh", "BED_MESH_CALIBRATE", "Run a full bed mesh?", "BED_MESH_CALIBRATE"),
    ("heat-up", "PID: bed (60 C)", "PID_CALIBRATE HEATER=heater_bed TARGET=60", "Tune the bed heater (PID)?\nThe bed heats to 60 C and stays on for several minutes.", "object:heater_bed"),
    ("heat-up", "PID: chamber (45 C)", "PID_CALIBRATE HEATER=chamber TARGET=45", "Tune the chamber heater (PID)?\nIt heats to 45 C and stays on for several minutes.", "object:heater_generic chamber"),
    ("heat-up", "PID: extruder T{tool} (200 C)", "PID_CALIBRATE HEATER={ext} TARGET=200", "Tune the heater of toolhead T{tool} (PID)?\nThe nozzle heats to 200 C.", "object:{ext}"),
    ("settings", "Save config", "SAVE_CONFIG", "Save the pending changes?\nKlipper restarts.", "klipper:SAVE_CONFIG"),
]


def ext_name(tool):
    return "extruder" if tool == 0 else "extruder%d" % tool


def calibration_items(sections, active_tool):
    """Items whose macro or object exists. `sections` = section names of printer.cfg
    (for example "gcode_macro BED_MESH_CALIBRATE", "heater_bed", "heater_generic chamber")."""
    tool = active_tool if active_tool is not None and active_tool >= 0 else 0
    ext = ext_name(tool)
    have = {str(x).strip().upper() for x in sections}
    out = []
    for icon, label, script, question, req in CALIBRATION:
        req = req.format(tool=tool, ext=ext)
        if req.startswith("object:"):
            ok = req[7:].upper() in have
        elif req.startswith("klipper:"):
            ok = True
        else:
            ok = ("GCODE_MACRO " + req).upper() in have
        if ok:
            out.append((icon, label.format(tool=tool), script.format(tool=tool, ext=ext), question.format(tool=tool), req))
    return out


def shaper_available(sections):
    """Input shaper needs the accelerometer (LIS2DW on the tool-changer MCU EX_T) and [resonance_tester]."""
    have = {str(x).strip().lower() for x in sections}
    return "lis2dw" in have and "resonance_tester" in have


def collision_settings(section):
    """Read-only values from the printer config ([collision_detect] has no live status object)."""
    if not section:
        return None
    try:
        get = section.get
    except AttributeError:
        return None
    return {"threshold": get("threshold", None), "action": get("action", "shutdown"),
            "window": get("window_size", None), "sensor": get("sensor", "lis2dw")}


# --------------------------------------------------------------------------------------
# System page helpers
# --------------------------------------------------------------------------------------
def throttled_text(flags):
    """vcgencmd get_throttled value (hex string) -> readable text."""
    try:
        v = int(str(flags).strip(), 16)
    except ValueError:
        return "unknown"
    if v & 0x1:
        return "under-voltage now"
    if v & 0x50000:
        return "had power or heat problems"
    return "ok"


def read_pi_temp(path="/sys/class/thermal/thermal_zone0/temp"):
    try:
        with open(path) as f:
            return int(f.read().strip()) / 1000.0
    except (OSError, ValueError):
        return None


def web_url(hostname, ip):
    return "http://%s.local/" % hostname if hostname else ("http://%s/" % ip if ip else "")


# --------------------------------------------------------------------------------------
# Factory screen board mode (KlipperScreen installed on the WonderMaker screen board)
# --------------------------------------------------------------------------------------
BOARD_DIR = os.path.expanduser("~/wm-screen-backup")
BOARD_MARKER = os.path.join(BOARD_DIR, "board_mode")          # written by scripts/screen_board.sh
BOARD_SCRIPT = "/usr/local/sbin/wm-factory-restore"           # root-owned copy of the script; sudoers allows only this one command


def board_mode(marker=None):
    """True when this KlipperScreen runs on the WonderMaker screen board (the restore button is shown then)."""
    return os.path.exists(marker or BOARD_MARKER)


RESCUE_SCRIPT = "/usr/local/sbin/wm-screen-rescue"             # root-owned; sudoers allows only "wm-screen-rescue open"
RESCUE_UNITS = ("/etc/systemd/system/wm-screen-rescue.service",)


def rescue_available(unit_files=None):
    """True when the rescue tool is installed on this board (the Rescue tile is shown then)."""
    return all(os.path.exists(f) for f in (unit_files or RESCUE_UNITS))


def rescue_command(script=None):
    """Opens the rescue window. KlipperScreen is stopped while it is open (the window has its own screen server)."""
    return ["sudo", "-n", script or RESCUE_SCRIPT, "open"]


def factory_restore_command(script=None):
    """The script re-starts itself under systemd (--detach), because stopping KlipperScreen would otherwise kill it."""
    return ["sudo", "-n", script or BOARD_SCRIPT, "--factory-restore", "--yes", "--detach"]


UPDATE_VERSION_URL = "https://raw.githubusercontent.com/ducati1198/WM_Ultra_Vanilla_Klipper/main/VERSION"
BOARD_VERSION_FILE = os.path.join(BOARD_DIR, "version")        # written by scripts/screen_board.sh at install and after every update


def update_command(script=None):
    """The Update button: the root copy of the script updates the installer folder and the screen files, and re-starts itself under
    systemd (--detach), because it restarts KlipperScreen. sudoers allows exactly this command."""
    return ["sudo", "-n", script or BOARD_SCRIPT, "--update", "--yes", "--detach"]


def version_tuple(text):
    """'2.0.7' -> (2, 0, 7); anything that is not numbers like that gives None."""
    parts = (text or "").strip().split(".")
    if not parts or not all(p.isdigit() for p in parts):
        return None
    return tuple(int(p) for p in parts)


def version_newer(latest, installed):
    """True when latest is a higher version than installed. An unknown installed version counts as older (an update is offered),
    an unreadable latest version never does."""
    new = version_tuple(latest)
    if new is None:
        return False
    old = version_tuple(installed)
    return True if old is None else new > old


def installed_version(path=None):
    """The version of the files on this screen. Every install and update writes it next to the panels (zr_version.txt) and to
    ~/wm-screen-backup/version; the installer folder's VERSION is the last resort. '' when none can be read."""
    here = os.path.dirname(os.path.abspath(__file__))
    files = [path] if path else [os.path.join(here, "zr_version.txt"), BOARD_VERSION_FILE] + sorted(glob.glob(os.path.expanduser("~/WM_Ultra_Vanilla_Klipper*/VERSION")))
    for f in files:
        try:
            with open(f) as fh:
                v = fh.readline().strip()
            if version_tuple(v):
                return v
        except OSError:
            pass
    return ""


def start_update(cmd=None, timeout=25):
    """Runs the Update command (sudo, root copy of the script, --detach: it hands over to systemd and returns at once).
    Returns (ok, message). A refused sudo (missing rule) gives ok=False and the reason, instead of silently doing nothing."""
    try:
        r = subprocess.run(cmd or update_command(), capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return True, ""             # still running after the hand-over: it is working
    except OSError as e:
        return False, str(e)
    if r.returncode == 0:
        return True, ""
    lines = (r.stderr or r.stdout or "").strip().splitlines()
    return False, lines[-1] if lines else "exit code %d" % r.returncode


def latest_version(url=None, timeout=10):
    """The newest version on GitHub (one small text file). '' when it cannot be read."""
    import urllib.request
    try:
        import time
        u = url or UPDATE_VERSION_URL
        if url is None:             # GitHub's raw files are cached for a few minutes: a changing query makes it fetch the current one
            u += "?nocache=%d" % int(time.time())
        with urllib.request.urlopen(u, timeout=timeout) as r:
            return r.read(64).decode("ascii", "ignore").splitlines()[0].strip()
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Update Pi button: the same update Fluidd's Update button does (Moonraker's update manager downloads the new installer
# files, wm-pi-update.path then runs scripts/pi_update.sh = installer.sh --update --yes on the Pi)
# ---------------------------------------------------------------------------
PI_UPDATE_NAME = "WM_Ultra_Vanilla_Klipper"
PANEL_UPDATE_NAME = "wm-ultra-fluidd-acepro-panel"     # the Fluidd panel (ACE Pro) project: its Update button is applied by wm-panel-update.service


def _moonraker(base, method, path, timeout):
    import urllib.request, json
    req = urllib.request.Request(base + path, data=b"" if method == "POST" else None, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace") or "{}")


def pi_update_parse(status, name=PI_UPDATE_NAME):
    """Moonraker's /machine/update/status answer -> {known, behind, version, remote, dirty, detached, problem}.
    known=False: this installer is not in the update manager (run ./installer.sh --update once in SSH)."""
    info = ((status or {}).get("result") or {}).get("version_info", {}).get(name)
    if not isinstance(info, dict):
        return {"known": False, "behind": False, "version": "", "remote": "", "dirty": False, "detached": False, "problem": ""}
    behind = bool(info.get("commits_behind")) or (bool(info.get("remote_hash")) and info.get("remote_hash") != info.get("current_hash"))
    problem = ""
    if info.get("is_dirty"):
        problem = "The installer folder on the Pi has changed files. Update it in SSH: cd ~/WM_Ultra_Vanilla_Klipper && git status"
    elif info.get("detached"):
        problem = "The installer folder on the Pi is not on the main branch. Update it in SSH."
    elif info.get("anomalies"):
        problem = "The update manager reports: %s" % "; ".join(str(a) for a in info["anomalies"][:2])
    return {"known": True, "behind": behind, "version": str(info.get("version", "")), "remote": str(info.get("remote_version", "")),
            "dirty": bool(info.get("is_dirty")), "detached": bool(info.get("detached")), "problem": problem}


def pi_update_check(base, timeout=40):
    """Asks Moonraker to look at GitHub, then reads the result. Returns the pi_update_parse dict of the installer with the Fluidd panel
    under "panel" (same keys; known=False when the panel is not in the update list), or None when Moonraker cannot be reached."""
    try:
        for name in (PI_UPDATE_NAME, PANEL_UPDATE_NAME):
            try:
                _moonraker(base, "POST", "/machine/update/refresh?name=%s" % name, timeout)
            except Exception:
                pass                # an older Moonraker may refuse a single-name refresh: the status still shows the last check
        status = _moonraker(base, "GET", "/machine/update/status", timeout)
        info = pi_update_parse(status)
        info["panel"] = pi_update_parse(status, PANEL_UPDATE_NAME)
        return info
    except Exception:
        return None


def pi_update_names(info):
    """Which update-manager entries 'Update now' downloads. The installer's own update also brings the Fluidd panel along (it pulls it),
    so the panel is asked for only when it is behind on its own."""
    if info.get("behind") and info.get("known"):
        return [PI_UPDATE_NAME]
    panel = info.get("panel") or {}
    if panel.get("known") and panel.get("behind") and not panel.get("problem"):
        return [PANEL_UPDATE_NAME]
    return []


def pi_update_start(base, timeout=60, names=None):
    """Starts the download (one POST per name; default: the installer). Returns (ok, message)."""
    try:
        for name in (names or [PI_UPDATE_NAME]):
            _moonraker(base, "POST", "/machine/update/client?name=%s" % name, timeout)
        return True, ""
    except Exception as e:
        body = ""
        try:
            body = e.read().decode("utf-8", "replace")[:200]        # urllib's HTTPError carries Moonraker's reason
        except Exception:
            pass
        return False, body or str(e)


# ---------------------------------------------------------------------------
# Wi-Fi on the screen board (wpa_supplicant + wpa_cli; no NetworkManager)
# ---------------------------------------------------------------------------
def wifi_parse_scan(text):
    """wpa_cli scan_results -> [{ssid, signal, secured}] strongest first, one entry per name, hidden names dropped."""
    best = {}
    for line in (text or "").splitlines():
        parts = line.split("\t")
        if len(parts) < 5 or parts[0] == "bssid / frequency / signal level / flags / ssid":
            continue
        ssid = parts[4].strip()
        if not ssid or "\\x00" in ssid:
            continue
        try:
            sig = int(parts[2])
        except ValueError:
            continue
        flags = parts[3]
        secured = any(k in flags for k in ("WPA", "WEP", "RSN", "SAE"))
        if ssid not in best or sig > best[ssid]["signal"]:
            best[ssid] = {"ssid": ssid, "signal": sig, "secured": secured}
    return sorted(best.values(), key=lambda n: -n["signal"])


def wifi_signal_bars(dbm):
    return 4 if dbm >= -55 else 3 if dbm >= -65 else 2 if dbm >= -75 else 1


def wifi_parse_status(text):
    """wpa_cli status -> dict (key=value lines)."""
    d = {}
    for line in (text or "").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            d[k.strip()] = v.strip()
    return d


def wifi_parse_networks(text):
    """wpa_cli list_networks -> {ssid: id}"""
    out = {}
    for line in (text or "").splitlines()[1:]:
        p = line.split("\t")
        if len(p) >= 2 and p[0].isdigit():
            out[p[1]] = int(p[0])
    return out


def wifi_password_ok(pw):
    return 8 <= len(pw) <= 63


# ---------------------------------------------------------------------------
# Pi address on the screen board (KlipperScreen.conf: moonraker_host)
# ---------------------------------------------------------------------------
import re as _re


def valid_host(host):
    return bool(_re.match(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,252}$", host or ""))


def replace_moonraker_host(text, host):
    """Return the config text with every moonraker_host line set to host (None if there is none)."""
    new, n = _re.subn(r"(?m)^(moonraker_host\s*[:=]).*$", lambda m: "%s %s" % (m.group(1), host), text)
    return new if n else None


def read_moonraker_host(text):
    m = _re.search(r"(?m)^moonraker_host\s*[:=]\s*(\S+)", text or "")
    return m.group(1) if m else ""


KS_CONF = os.path.expanduser("~/printer_data/config/KlipperScreen.conf")
LOCAL_HOSTS = ("", "localhost", "127.0.0.1", "::1")


def fluidd_url(hostname="", ip="", conf=None):
    """Where Fluidd is: the Pi address entered in KlipperScreen.conf (moonraker_host) when it is a real address,
    otherwise this machine's own name or address (KlipperScreen running on the Pi itself)."""
    try:
        with open(conf or KS_CONF) as f:
            host = read_moonraker_host(f.read())
    except OSError:
        host = ""
    if host not in LOCAL_HOSTS:
        return "http://%s/" % host
    return web_url(hostname, ip)


# ---------------------------------------------------------------------------
# Looks (style x theme): plain GTK3 CSS, built here so it can be tested
# ---------------------------------------------------------------------------
_STYLE_TOKENS = {
    # radius, border width, accent, accent text, font scale
    "soft": {"radius": 14, "bw": 1, "accent": "#2f7bf6", "on_text": "#ffffff", "font": "100%"},
    "flat": {"radius": 6, "bw": 0, "accent": "#14b8a6", "on_text": "#ffffff", "font": "100%"},
    "bold": {"radius": 10, "bw": 3, "accent": "#ff9800", "on_text": "#000000", "font": "110%"},
    "classic": {"radius": 10, "bw": 2, "accent": "#2e7d32", "on_text": "#ffffff", "font": "100%"},
}


def build_css(theme, style, density="compact", scale=1.0):
    """Design A: tall rounded cards, status chips, a rounded tab bar, big action buttons. Plain GTK3 CSS."""
    t = _STYLE_TOKENS.get(style) or _STYLE_TOKENS["soft"]
    big = density == "comfortable"
    k = scale if isinstance(scale, (int, float)) and scale > 0 else 1.0
    light = theme == "light"
    if light:
        bg, card, card_on, edge, small, hint = "#eef1f4", "#ffffff", "#e4eefc", "#cfd6de", "#44505c", "#66727e"
        text = "#14181c"
        ready = ("#d6f3e0", "#17703d"); active = ("#d9e6fd", "#1b4fb3"); empty = ("#fdebd0", "#a15c00")
        dot_edge = "#44505c"
    else:
        bg, card, card_on, edge, small, hint = "#11161b", "#1b232b", "#18222f", "#2a343e", "#b4bec8", "#8a96a2"
        text = "#e8edf2"
        ready = ("#173b25", "#6fe39a"); active = ("#16325f", "#8db8ff"); empty = ("#4a3212", "#ffb74d")
        dot_edge = "#ffffff"
    acc = t["accent"]
    r = t["radius"] if style != "soft" else 14
    return """
    .zr_card { border: 2px solid %(edge)s; border-radius: %(r)dpx; background-image: none; background-color: %(card)s; color: %(text)s; }
    .zr_active { border: 2px solid %(acc)s; background-color: %(card_on)s; }
    .zr_card_empty { background-color: #0e1114; border: 2px solid #232a30; }
    .zr_card_empty label { color: #5f666c; }
    .zr_card_sel { border: 3px solid #8ab4ff; background-color: #141c2e; }
    .zr_swatch { border: 2px solid %(dot_edge)s; border-radius: %(sr)dpx; }
    .zr_dot { border: 2px solid %(edge)s; border-radius: 32px; }
    .zr_dot_on { border: 5px solid %(acc)s; }
    .zr_chip { border-radius: %(r)dpx; background-image: none; background-color: %(card)s; color: %(text)s; border: 2px solid %(edge)s; }
    .zr_chip_on { background-color: %(acc)s; color: #ffffff; border-color: %(acc)s; }
    .zr_pill { border-radius: 14px; padding: 2px 10px; font-weight: bold; font-size: %(pill)s; background-color: %(card)s; color: %(small)s; }
    .zr_pill_ready { background-color: %(ready_bg)s; color: %(ready_fg)s; }
    .zr_pill_active { background-color: %(active_bg)s; color: %(active_fg)s; }
    .zr_pill_empty { background-color: %(empty_bg)s; color: %(empty_fg)s; }
    .zr_pill_info { background-color: %(card)s; color: %(text)s; border: 1px solid %(edge)s; }
    .zr_title { font-weight: bold; font-size: %(title)s; }
    .zr_mat { font-weight: bold; font-size: %(mat)s; }
    .zr_btn, .zr_tab { border-radius: %(r)dpx; background-image: none; background-color: %(card)s; color: %(text)s; border: 1px solid %(edge)s; box-shadow: none; text-shadow: none; }
    .zr_btn_primary { background-color: %(acc)s; border-color: %(acc)s; color: #ffffff; }
    .zr_btn_navy { background-color: #1e3a8a; border-color: #1e3a8a; color: #ffffff; }
    .zr_btn_go { background-image: none; background-color: #0b57d0; border: 2px solid #8ab4ff; color: #ffffff; font-weight: bold; text-shadow: none; }
    .zr_btn_big { font-size: 20px; font-weight: bold; }
    .zr_btn_green { background-color: #2e9d57; border-color: #2e9d57; color: #ffffff; }
    .zr_btn_orange { background-color: #d9822b; border-color: #d9822b; color: #ffffff; }
    .zr_btn_purple { background-color: #7b4fd0; border-color: #7b4fd0; color: #ffffff; }
    .zr_btn_pink { background-color: #c2477f; border-color: #c2477f; color: #ffffff; }
    .zr_arrow { background-color: #27323c; border-color: #3b4955; color: #ffffff; font-weight: bold; padding: 0; }
    .zr_arrow label { font-size: 125%%; font-weight: bold; }
    .zr_btn_off { background-color: #262a3a; border-color: #3b4955; color: #aab0c0; }
    .zr_pill_on { background-color: #33d06b; color: #06280f; }
    .zr_pill_off { background-color: #e04545; color: #ffffff; }
    .zr_btn_cyan { background-color: #17a2b8; border-color: #17a2b8; color: #ffffff; }
    .zr_btn_red { background-color: #c0392b; border-color: #c0392b; color: #ffffff; }
    .zr_btn_blue { background-color: #1f6feb; border-color: #1f6feb; color: #ffffff; }
    .zr_selected { background-image: none; background-color: %(acc)s; border-color: %(acc)s; color: #ffffff; }
    .zr_section { font-weight: bold; padding-top: 6px; }
    .zr_small { font-size: %(small_pct)s; color: %(small)s; }
    .zr_value { font-weight: bold; font-size: %(value)s; }
    .zr_value_dim { font-weight: bold; font-size: %(value_dim)s; color: %(small)s; }
    .zr_value_xl { font-weight: bold; font-size: %(value_xl)s; }
    .zr_value_xl_dim { font-weight: bold; font-size: %(value_xl)s; color: %(small)s; }
    .zr_hint { font-size: %(small_pct)s; color: %(hint)s; }
    scrollbar.vertical { min-width: 18px; }
    scrollbar slider { min-width: 14px; min-height: 40px; border-radius: 8px; background-color: %(edge)s; }
    """ % {"edge": edge, "r": r, "sr": max(r // 2, 4), "card": card, "card_on": card_on, "acc": acc, "text": text,
           "small": small, "hint": hint, "dot_edge": dot_edge,
           "ready_bg": ready[0], "ready_fg": ready[1], "active_bg": active[0], "active_fg": active[1],
           "empty_bg": empty[0], "empty_fg": empty[1],
           "pill": "%d%%" % round((100 if big else 85) * k), "title": "%d%%" % round((120 if big else 100) * k),
           "mat": "%d%%" % round((130 if big else 110) * k),
           "value": "%d%%" % round((330 if big else 290) * k), "value_dim": "%d%%" % round((230 if big else 200) * k), "value_xl": "%d%%" % round((380 if big else 330) * k), "small_pct": "%d%%" % round(85 * k)}


# ---------------------------------------------------------------------
# Filament colour / material shared with the Fluidd panel and the factory touchscreen.
# All three read and write the [slot] section of tmt1.ini (colourN / materialN are list indices).
# The lists below are the touchscreen's own, same order as the Fluidd panel.
# ---------------------------------------------------------------------
TOUCH_PALETTE = [
    ("White", 0xFFFFFF), ("Beige", 0xF3E8C8), ("Brown", 0x9A6738), ("Grey", 0xC7D5DF), ("Black", 0x000000),
    ("Cyan", 0x00DDE3), ("Light blue", 0x13A7E8), ("Dark blue", 0x0B4BD8), ("Light green", 0x16E900),
    ("Dark green", 0x00A84F), ("Yellow", 0xFFF200), ("Orange", 0xFF5A1F), ("Light pink", 0xDDBFDE),
    ("Magenta", 0xE72DBE), ("Red", 0xFF1C2E), ("Bright blue", 0x006EFF), ("Gold", 0xD9A520),
    ("Copper", 0xB86B44), ("Silver", 0xAFC0CC), ("Multicolour", 0xC060C0), ("Clear", 0xD5E8EE),
]
# ---------------------------------------------------------------------
# More filament colours: the same four lists as OrcaSlicer's colour picker (names and values read from the Orca app, palettes.js).
# (list name, [(colour name, 0xRRGGBB), ...]). Used by the colour page of the filament editor; the 21 touchscreen swatches above stay.
# ---------------------------------------------------------------------
COLOR_LISTS = [
    ('Orca', [
        ('Coral fire', 0xED1C24), ('Sea anemone', 0xC41E3A), ('Deep abyss', 0x800000), ('Lobster red', 0xB22222), ('Sandy clay', 0xA0522D),
        ('Driftwood', 0x8B4513), ('Sea buckthorn', 0xD2691E), ('Sunset reef', 0xF26722), ('Tiger coral', 0xFF8C00), ('Pink coral', 0xFA8173),
        ('Seashell glow', 0xFFA07A), ('Sand', 0xF4E2C1), ('Golden kelp', 0xFFD700), ('Sunlit dune', 0xF7B763), ('Amber nautilus', 0xFFAA33),
        ('Sea lemon', 0xFFEB31), ('Pale starfish', 0xD4ED91), ('Spring tide', 0x00FF7F), ('Lime algae', 0x32CD32), ('Sea grass', 0xA4C41E),
        ('Neon plankton', 0x7CFC00), ('Kelp forest', 0x228B22), ('Emerald wave', 0x008000), ('Whale shadow', 0x345B2F), ('Sea turtle', 0x2E8B57),
        ('Lagoon', 0x00C1AE), ('Tropical current', 0x20B2AA), ('Midnight trench', 0x115877), ('Dark kelp', 0x008B8B), ('Crystal surf', 0x00FFFF),
        ('Turquoise bay', 0x40E0D0), ('Sky over reef', 0x2EBDEF), ('Shallow sky', 0x87CEEB), ('Electric blue', 0x1E90FF), ('Dolphin', 0x4169E1),
        ('Ocean depths', 0x0000CD), ('Whale', 0x191970), ('Indigo abyss', 0x4B0082), ('Sea urchin', 0x7841CE), ('Lavender coral', 0x9370DB),
        ('Violet tide', 0x800080), ('Deep sea orchid', 0x8B008B), ('Neon jelly', 0xFF00FF), ('Fuchsia coral', 0xED1E79),
        ('Pink jellyfish', 0xFF69B4), ("White", 0xFFFFFF), ('Seashell white', 0xD3D3D3), ('Pebble gray', 0x808080), ('Storm cloud', 0x696969),
        ('Black', 0x000000),
    ]),
    ('Basic', [
        ('Red', 0xFF0000), ('Orange', 0xFF8000), ('Yellow', 0xFFFF00), ('Lime', 0x80FF00), ('Green', 0x00FF00), ('Cyan', 0x00FFFF),
        ('Blue', 0x0000FF), ('Purple', 0x8000FF), ('Magenta', 0xFF00FF), ('Pink', 0xFF8080), ('Brown', 0x804000), ('Black', 0x000000),
        ('Black 90%', 0x191919), ('%80', 0x333333), ('%70', 0x4C4C4C), ('%60', 0x666666), ('%50', 0x808080), ('%40', 0x999999), ('%30', 0xB3B3B3),
        ('Black 20%', 0xCCCCCC), ('%10', 0xE6E6E6), ('White', 0xFFFFFF),
    ]),
    ('Web', [
        ('Red', 0xFF0000), ('Crimson', 0xDC143C), ('Orange red', 0xFF4500), ('Tomato', 0xFF6347), ('Orange', 0xFFA500), ('Dark orange', 0xFF8C00),
        ('Gold', 0xFFD700), ('Burly wood', 0xDEB887), ('Bisque', 0xFFE4C4), ('Misty rose', 0xFFE4E1), ('Yellow', 0xFFFF00),
        ('Light yellow', 0xFFFFE0), ('Lemon chiffon', 0xFFFACD), ('Beige', 0xF5F5DC), ('Light golden rod yellow', 0xFAFAD2),
        ('Pale golden rod', 0xEEE8AA), ('Khaki', 0xF0E68C), ('Dark khaki', 0xBDB76B), ('Peach puff', 0xFFDAB9), ('Moccasin', 0xFFE4B5),
        ('Papaya whip', 0xFFEFD5), ('Blanched almond', 0xFFEBCD), ('Antique white', 0xFAEBD7), ('Navajo white', 0xFFDEAD), ('Wheat', 0xF5DEB3),
        ('Golden rod', 0xDAA520), ('Chocolate', 0xD2691E), ('Peru', 0xCD853F), ('Fire brick', 0xB22222), ('Sienna', 0xA0522D),
        ('Saddle brown', 0x8B4513), ('Brown', 0xA52A2A), ('Rosy brown', 0xBC8F8F), ('Salmon', 0xFA8072), ('Light salmon', 0xFFA07A),
        ('Dark salmon', 0xE9967A), ('Sandy brown', 0xF4A460), ('Coral', 0xFF7F50), ('Light coral', 0xF08080), ('Indian red', 0xCD5C5C),
        ('Dark red', 0x8B0000), ('Maroon', 0x800000), ('Green yellow', 0xADFF2F), ('Yellow green', 0x9ACD32), ('Chartreuse', 0x7FFF00),
        ('Lawn green', 0x7CFC00), ('Lime green', 0x32CD32), ('Spring green', 0x00FF7F), ('Medium spring green', 0x00FA9A), ('Lime', 0x00FF00),
        ('Green', 0x008000), ('Forest green', 0x228B22), ('Dark green', 0x006400), ('Olive drab', 0x6B8E23), ('Olive', 0x808000),
        ('Dark olive green', 0x556B2F), ('Pale green', 0x98FB98), ('Light green', 0x90EE90), ('Medium sea green', 0x3CB371), ('Sea green', 0x2E8B57),
        ('Dark sea green', 0x8FBC8F), ('Cadet blue', 0x5F9EA0), ('Medium aqua marine', 0x66CDAA), ('Turquoise', 0x40E0D0),
        ('Medium turquoise', 0x48D1CC), ('Dark turquoise', 0x00CED1), ('Pale turquoise', 0xAFEEEE), ('Aqua', 0x00FFFF), ('Cyan', 0x00FFFF),
        ('Light cyan', 0xE0FFFF), ('Mint cream', 0xF5FFFA), ('Honey dew', 0xF0FFF0), ('Aquamarine', 0x7FFFD4), ('Light sea green', 0x20B2AA),
        ('Dark cyan', 0x008B8B), ('Teal', 0x008080), ('Dark slate gray', 0x2F4F4F), ('Light slate gray', 0x778899), ('Slate gray', 0x708090),
        ('Deep sky blue', 0x00BFFF), ('Dodger Blue', 0x1E90FF), ('Sky blue', 0x87CEEB), ('Light sky blue', 0x87CEFA), ('Light blue', 0xADD8E6),
        ('Powder blue', 0xB0E0E6), ('Light steel blue', 0xB0C4DE), ('Steel blue', 0x4682B4), ('Cornflower blue', 0x6495ED), ('Royal blue', 0x4169E1),
        ('Blue', 0x0000FF), ('Medium blue', 0x0000CD), ('Midnight blue', 0x191970), ('Dark blue', 0x00008B), ('Navy', 0x000080),
        ('Slate blue', 0x6A5ACD), ('Dark slate blue', 0x483D8B), ('Medium slate blue', 0x7B68EE), ('Blue violet', 0x8A2BE2), ('Indigo', 0x4B0082),
        ('Dark violet', 0x9400D3), ('Dark orchid', 0x9932CC), ('Medium orchid', 0xBA55D3), ('Orchid', 0xDA70D6), ('Violet', 0xEE82EE),
        ('Medium purple', 0x9370DB), ('Purple', 0x800080), ('Rebecca purple', 0x663399), ('Medium violet red', 0xC71585),
        ('Pale violet red', 0xDB7093), ('Deep pink', 0xFF1493), ('Hot pink', 0xFF69B4), ('Light pink', 0xFFB6C1), ('Pink', 0xFFC0CB),
        ('Plum', 0xDDA0DD), ('Thistle', 0xD8BFD8), ('Magenta', 0xFF00FF), ('Fuchsia', 0xFF00FF), ('Dark magenta', 0x8B008B), ('Linen', 0xFAF0E6),
        ('Old lace', 0xFDF5E6), ('Sea shell', 0xFFF5EE), ('Ivory', 0xFFFFF0), ('Floral white', 0xFFFAF0), ('Lavender blush', 0xFFF0F5),
        ('Ghost white', 0xF8F8FF), ('Alice blue', 0xF0F8FF), ('Lavender', 0xE6E6FA), ('White smoke', 0xF5F5F5), ('Gainsboro', 0xDCDCDC),
    ]),
    ('RAL', [
        ('1000 Green beige', 0x716F52), ('1001 Beige', 0x9B8E79), ('1002 Sand yellow', 0xD4BB87), ('1003 Signal yellow', 0xF4A460),
        ('1004 Golden yellow', 0xEFBF04), ('1005 Honey yellow', 0xD7A500), ('1006 Maize yellow', 0xF2D185), ('1007 Daffodil yellow', 0xFDD185),
        ('1011 Brown beige', 0x8B7D6B), ('1012 Lemon yellow', 0xF5DB50), ('1013 Oyster white', 0xF3E5AB), ('1014 Ivory', 0xF8E4BC),
        ('1015 Light ivory', 0xFAE6D3), ('1018 Zinc yellow', 0xE4B922), ('1019 Grey beige', 0xA19D94), ('1020 Olive yellow', 0xB9975B),
        ('1021 Rape yellow', 0xB8860B), ('1023 Traffic yellow', 0xFF8C00), ('1024 Ochre yellow', 0xCC7722), ('1026 Traffic orange yellow', 0xFDBA37),
        ('1027 Curry', 0xF3A55C), ('1028 Melon yellow', 0xE87C33), ('1032 Broom yellow', 0xF2A641), ('1033 Dahlia yellow', 0xE09F39),
        ('1034 Pastel yellow', 0xF0B76E), ('1035 Pearl beige', 0xD1BCA0), ('1036 Pearl gold', 0xD4AF37), ('1037 Sun yellow', 0xF7C64F),
        ('2000 Yellow orange', 0xF28C38), ('2001 Deep orange', 0xE55B2B), ('2002 Vermilion', 0xE34234), ('2003 Pearl orange', 0xF27B33),
        ('2004 Pure orange', 0xF37322), ('2005 Luminous orange', 0xF75C03), ('2007 Luminous bright orange', 0xF46C1F),
        ('2008 Bright red orange', 0xE14423), ('2009 Traffic orange', 0xF28500), ('2010 Signal orange', 0xF46A0A), ('2011 Deep orange', 0xE0490C),
        ('2012 Salmon orange', 0xF46F42), ('2013 Pearl orange', 0xE6761C), ('2015 Pearl pink', 0xE8A18B), ('2016 Copper orange', 0xB8612C),
        ('2017 Signal brown', 0x8B4513), ('2018 Fir orange', 0xC14A0F), ('2020 Signal red', 0xBC2E1F), ('2021 Luminous red', 0xD52713),
        ('2022 Carmine red', 0x9F261E), ('2023 Pearl carmine red', 0xD53832), ('2024 Pure red', 0xC2341C), ('2025 Luminous deep red', 0xB32D1C),
        ('2027 Currant red', 0xA62320), ('2028 Pearl ruby red', 0xB9301E), ('3000 Fire red', 0xA91D2E), ('3001 Signal red', 0xA1262A),
        ('3002 Carmine red', 0x8F2626), ('3003 Ruby red', 0x9B2428), ('3004 Purple red', 0x872241), ('3005 Wine red', 0x722F37),
        ('3007 Black red', 0x3D1818), ('3009 Oxide red', 0x8A3324), ('3011 Brown red', 0xA22C29), ('3012 Pine red', 0xB22D20),
        ('3013 Tomato red', 0xD23741), ('3014 Antique pink', 0xA8282E), ('3015 Light pink', 0xC8283C), ('3016 Coral red', 0xD23F39),
        ('3017 Rose', 0xD1425E), ('3018 Strawberry red', 0xC4232F), ('3020 Traffic red', 0xC8102E), ('3022 Salmon pink', 0xE36A5A),
        ('3024 Luminous rose', 0xE63E62), ('3026 Luminous bright red', 0xE02A27), ('3027 Raspberry red', 0xB8315F), ('3028 Pure red', 0xC61C23),
        ('3031 Orient red', 0xAD2932), ('3032 Pearl ruby', 0xD32F2F), ('3033 Pearl pink', 0xD13C6F), ('4001 Red purple', 0x7B2B5F),
        ('4002 Red violet', 0x912E8C), ('4003 Heather violet', 0x9C366F), ('4004 Bordeaux violet', 0x6A1F49), ('4005 Blue violet', 0x4B2663),
        ('4006 Mahogany', 0x5C2D3C), ('4007 Grey purple', 0x5E3559), ('4008 Signal violet', 0x9C3568), ('4009 Fir green', 0x5E6E3A),
        ('4010 Sabine grey', 0x5B5B8A), ('4011 Pearl violet', 0x8F3A70), ('4012 Pearl blackberry', 0x5E3252), ('5001 Green blue', 0x1B4F72),
        ('5002 Ultramarine blue', 0x18669E), ('5003 Sapphire blue', 0x0F4C8A), ('5004 Black blue', 0x0D324A), ('5005 Signal blue', 0x1B5583),
        ('5007 Brilliant blue', 0x2C5F9D), ('5008 Grey blue', 0x3B5AA9), ('5009 Azure blue', 0x0077A3), ('5010 Gentian blue', 0x0A558C),
        ('5011 Steel blue', 0x2B547E), ('5012 Light blue', 0x0066A1), ('5013 Cobalt blue', 0x124780), ('5014 Pigeon blue', 0x1F4E79),
        ('5015 Sky blue', 0x0384A7), ('5017 Traffic blue', 0x006A9E), ('5018 Turquoise blue', 0x005F87), ('5019 Capri blue', 0x1B5583),
        ('5020 Ocean blue', 0x04749F), ('5021 Water blue', 0x009AAA), ('5022 Night blue', 0x1A3D5F), ('5023 Distant blue', 0x047AA6),
        ('5024 Pastel blue', 0x5B9BB8), ('5025 Pearl gentian blue', 0x3C6A98), ('5026 Pearl midnight blue', 0x1C3F5F),
        ('6000 Patina green', 0x36673A), ('6001 Emerald green', 0x0E5C34), ('6002 Leaf green', 0x437034), ('6003 Olive green', 0x3F3F2A),
        ('6004 Blue green', 0x2B4E52), ('6005 Moss green', 0x3B5F3F), ('6006 Grey olive', 0x4A563C), ('6007 Pine green', 0x2B4638),
        ('6008 Pine brown', 0x4A4139), ('6009 Fir green', 0x3B3A2E), ('6010 Grass green', 0x3E7A5F), ('6011 Reseda green', 0x5E716A),
        ('6012 Brown green', 0x3A4E48), ('6013 Reed green', 0x6B8E23), ('6014 Yellow green', 0x6B8E23), ('6015 Black green', 0x1E3E2F),
        ('6016 Turquoise green', 0x1E4D4B), ('6017 May green', 0x4C7C47), ('6018 Yellow green', 0x9CBF60), ('6019 Pine green', 0x2E5A3A),
        ('6020 Chrome oxide green', 0x2E5A3A), ('6021 Pale green', 0x9DC0A5), ('6022 Brown green', 0x4A563C), ('6024 Traffic green', 0x009E60),
        ('6025 Fern green', 0x3F7044), ('6026 Opal green', 0x4F7942), ('6027 Pine green', 0x3B5F3F), ('6028 Pine green', 0x3B5F3F),
        ('6029 Mint green', 0x00A550), ('6031 Bronze green', 0x3E5A40), ('6032 Pearl green', 0x3D7E5A), ('6033 Sax turquoise', 0x007D6E),
        ('6034 Pearl turquoise', 0x3D7E5A), ('6035 Pearl green', 0x3D7E5A), ('6036 Pearl jade', 0x3D7E5A), ('6037 Pure green', 0x00A550),
        ('6038 Luminous green', 0x00A550), ('6039 Mint green', 0x00A550), ('7000 Squirrel grey', 0x7D7D7D), ('7001 Silver grey', 0xA8A9AD),
        ('7002 Olive grey', 0x6F7368), ('7003 Moss grey', 0x8F9080), ('7004 Signal grey', 0x8E9291), ('7005 Mouse grey', 0x8B8788),
        ('7006 Beige grey', 0x9A8373), ('7008 Khaki grey', 0x828C6A), ('7009 Green grey', 0x6F7368), ('7010 Tarpaulin grey', 0x5F6563),
        ('7011 Iron grey', 0x4A5656), ('7012 Basalt grey', 0x4D5656), ('7013 Brown grey', 0x635147), ('7015 Slate grey', 0x6B6B83),
        ('7016 Anthracite grey', 0x32373D), ('7021 Light grey', 0x8B8B83), ('7022 Umber grey', 0x716347), ('7023 Concrete grey', 0x76787A),
        ('7024 Graphite grey', 0x5E6565), ('7026 Granite grey', 0x5E6565), ('7030 Stone grey', 0x8F9494), ('7031 Iron grey', 0x4A5656),
        ('7032 Pebble grey', 0xB2BFC0), ('7033 Cement grey', 0x9B9B9B), ('7034 Yellow grey', 0x8F9D9B), ('7035 Light grey', 0xCBD0CC),
        ('7036 Platinum grey', 0x6D7A80), ('7037 Dusty grey', 0x8A9191), ('7038 Agate grey', 0x7E8181), ('7039 Quartz grey', 0x6E7D7E),
        ('7040 Window grey', 0x8A9191), ('7042 Traffic grey A', 0x8A9191), ('7043 Traffic grey B', 0x6E7D7E), ('7044 Silk grey', 0x9B9B9B),
        ('7045 Telegrey 1', 0xA1A7B0), ('7046 Telegrey 2', 0x7E848C), ('7047 Telegrey 4', 0x7E848C), ('7048 Pearl mouse grey', 0x6D7A80),
        ('8000 Green brown', 0x786D5F), ('8001 Ochre brown', 0x8B7355), ('8003 Clay brown', 0x8B6F47), ('8004 Copper brown', 0x8B6F47),
        ('8007 Chocolate brown', 0x5C4033), ('8008 Olive brown', 0x6E5C4A), ('8011 Nut brown', 0x8B4513), ('8012 Red brown', 0x8B4513),
        ('8014 Sepia brown', 0x5C3317), ('8015 Chestnut brown', 0x854636), ('8016 Mahogany brown', 0x8B4513), ('8017 Chocolate brown', 0x5C3317),
        ('8019 Grey brown', 0x786D5F), ('8022 Chestnut brown', 0x854636), ('8023 Pearl copper', 0x8B6F47), ('8024 Beige brown', 0x8B7355),
        ('8025 Pearl mocha brown', 0x8B6F47), ('8027 Clay brown', 0x8B6F47), ('8028 Earth brown', 0x8B6F47), ('8029 Pearl brown', 0x8B6F47),
        ('9001 Cream', 0xFAF0E6), ('9002 Grey white', 0xEDECE6), ('9003 Signal white', 0xFFFFFF), ('9004 Signal black', 0x000000),
        ('9005 Jet black', 0x1D1D1D), ('9006 White aluminium', 0xC0C0C0), ('9007 Grey aluminium', 0x8C7853), ('9010 Pure white', 0xFFFFFF),
        ('9011 Graphite black', 0x1D1D1D), ('9016 Traffic white', 0xFFFFFF), ('9017 Traffic black', 0x000000), ('9018 Papyrus white', 0xFAF0E6),
        ('9022 Pearl light grey', 0xB2BFC0),
    ]),
]

# touchscreen material list: (name, temperature, index in the ZR Tools material list)
TOUCH_MATERIALS = [
    ("PLA", 210, 1), ("PLA Silk", 215, 3), ("ABS", 250, 8), ("PETG", 240, 6), ("PLA Matte", 210, 4),
    ("PLA Metal", 215, 15), ("ABS Matte", 250, 8), ("PETG Matte", 240, 6), ("PVA", 200, 13), ("TPE", 225, 10),
    ("Marble", 210, 15), ("HIPS", 235, 14), ("TPU", 225, 10), ("PET", 240, 15), ("Wood", 200, 15), ("ASA", 255, 9),
    # added at the END (no index moves); the factory touchscreen may not know them
    ("PLA+", 215, 2), ("PLA-CF", 220, 5), ("PETG-CF", 250, 7), ("PA", 270, 11), ("PA-CF", 280, 11),
    ("PC", 270, 12), ("ABS-CF", 260, 8), ("PA-GF", 280, 11), ("PC-ABS", 260, 12), ("PP", 230, 15), ("BVOH", 210, 15),
]


def nearest_palette(color_int):
    """Index of the touchscreen swatch closest to an 0xRRGGBB colour."""
    r, g, b = (color_int >> 16) & 255, (color_int >> 8) & 255, color_int & 255
    best, dist = 0, None
    for i, (_n, c) in enumerate(TOUCH_PALETTE):
        cr, cg, cb = (c >> 16) & 255, (c >> 8) & 255, c & 255
        rm = (r + cr) / 2.0
        d = (2 + rm / 256) * (r - cr) ** 2 + 4 * (g - cg) ** 2 + (2 + (255 - rm) / 256) * (b - cb) ** 2
        if dist is None or d < dist:
            best, dist = i, d
    return best


def parse_tmt1_slots(text, ntools=4):
    """[{'color': palette index or None, 'material': index or None}] from the [slot] section of tmt1.ini."""
    slots = [{"color": None, "material": None} for _ in range(ntools)]
    section = ""
    for raw in (text or "").splitlines():
        line = raw.strip()
        m = _re.match(r"^\[(.+)\]$", line)
        if m:
            section = m.group(1).strip().lower()
            continue
        if section != "slot":
            continue
        m = _re.match(r"^(color|material)(\d+)\s*=\s*(-?\d+)\s*$", line, _re.I)
        if not m or int(m.group(2)) >= ntools:
            continue
        key, idx, val = m.group(1).lower(), int(m.group(2)), int(m.group(3))
        limit = len(TOUCH_PALETTE) if key == "color" else len(TOUCH_MATERIALS)
        slots[idx][key] = val if 0 <= val < limit else None
    return slots


def update_tmt1_slot(text, index, color, material):
    """tmt1.ini text with one slot changed; every other line stays as it was."""
    eol = "\r\n" if "\r\n" in text else "\n"
    lines = text.splitlines()
    section, slot_end, done_c, done_m = "", -1, False, False
    for i, raw in enumerate(lines):
        line = raw.strip()
        m = _re.match(r"^\[(.+)\]$", line)
        if m:
            if section == "slot":
                slot_end = i
            section = m.group(1).strip().lower()
            continue
        if section != "slot":
            continue
        if _re.match(r"^color%d\s*=" % index, line, _re.I):
            lines[i], done_c = "color%d=%d" % (index, color), True
        elif _re.match(r"^material%d\s*=" % index, line, _re.I):
            lines[i], done_m = "material%d=%d" % (index, material), True
    if not (done_c and done_m):
        extra = []
        if not done_c:
            extra.append("color%d=%d" % (index, color))
        if not done_m:
            extra.append("material%d=%d" % (index, material))
        if section == "slot" and slot_end < 0:
            at = len(lines)
        elif slot_end >= 0:
            at = slot_end
        else:
            lines += ["", "[slot]"]
            at = len(lines)
        while at > 0 and lines[at - 1].strip() == "":
            at -= 1
        lines[at:at] = extra
    return eol.join(lines) + (eol if text.endswith(("\n", "\r")) else "")
