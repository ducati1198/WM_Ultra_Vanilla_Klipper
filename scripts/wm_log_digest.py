#!/usr/bin/env python3
"""WonderMaker log digest (item 30).

Writes small files into ~/printer_data/logs, where Fluidd shows them under Configuration > Other Files:
  wm-events.log        one line per important event (Klipper start, config / macro / MCU errors, failed tool changes,
                       ACE drops, load / unload / purge steps, print start / end, commands typed by hand)
  wm-config-check.log  config check after every Klipper start (missing includes, a section defined twice,
                       config below SAVE_CONFIG, unsupported Jinja tag, RESPOND text with ; # *, ...)
  wm-blackbox.log      the last 3000 lines of /var/log/wm-blackbox/blackbox.log (Pi power / load / temperature)
  wm-ace.log           everything about the ACE Pro: its driver lines from klippy.log (without the RFID noise), the ACE
                       messages of the console, and when the USB serial port (/dev/ttyACM*) appears or disappears
  wm-system.log        when Klipper, Moonraker, KlipperScreen, crowsnest, nginx and the network services started,
                       stopped, failed or restarted, plus their journal warnings and errors
  (wm-events.log also gets one STATE line from PAUSE, RESUME and CANCEL_PRINT: tool, position, offsets, heaters)

It only READS klippy.log, Moonraker, the config files and the black box. It changes nothing in Klipper.
  python3 wm_log_digest.py              run as the service
  python3 wm_log_digest.py --check      run the config check once and print the report
  python3 wm_log_digest.py --selftest   feed sample lines through the rules and print what would be logged
"""
import glob
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

HOME = os.path.expanduser("~")
DATA = os.path.join(HOME, "printer_data")
CFG = os.path.join(DATA, "config")
LOGS = os.path.join(DATA, "logs")
KLIPPY = os.path.join(LOGS, "klippy.log")
EVENTS = os.path.join(LOGS, "wm-events.log")
CHECK = os.path.join(LOGS, "wm-config-check.log")
BB_SRC = "/var/log/wm-blackbox/blackbox.log"
BB_DST = os.path.join(LOGS, "wm-blackbox.log")
ACELOG = os.path.join(LOGS, "wm-ace.log")
ACE_MAX = 1000000            # wm-ace.log is rotated at 1 MB (.1 and .2 kept)
SYSLOG = os.path.join(LOGS, "wm-system.log")
SYS_MAX = 500000             # wm-system.log is rotated at 500 KB (.1 kept)
SYS_CURSOR = os.path.join(DATA, ".wm-system.cursor")
API = "http://localhost:7125"
MAX_BYTES = 1000000          # wm-events.log is rotated at 1 MB (.1 and .2 kept)
BB_BYTES = 400000            # about 3000 black box lines
MARK = "#*# <---------------------- SAVE_CONFIG ---------------------->"
SINK = None                  # --selftest collects the events here instead of writing the file


def ts_text(t=None):
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t or time.time()))


_LAST = {}
_RATE = {"minute": 0, "n": 0, "dropped": 0}


def ev(cat, msg, t=None):
    msg = " ".join(str(msg).split())[:300]
    now = time.time()
    if now - _LAST.get((cat, msg), 0) < 3:            # Klipper logs some errors twice
        return
    _LAST[(cat, msg)] = now
    if len(_LAST) > 500:
        _LAST.clear()
    # at most 120 lines per minute: a runaway loop (for example an endless swap) cannot flood the file or push the
    # older history out of the 1 MB rotation; the number of dropped lines is written when the minute is over
    minute = int(now // 60)
    if _RATE["minute"] != minute:
        dropped, _RATE["minute"], _RATE["n"], _RATE["dropped"] = _RATE["dropped"], minute, 0, 0
        if dropped:
            ev("DIGEST", "%d event lines were left out in the last minute (too many)" % dropped)
    _RATE["n"] += 1
    if _RATE["n"] > 120:
        _RATE["dropped"] += 1
        return
    line ="%s  %-9s %s\n" % (ts_text(t), cat, msg)
    if SINK is not None:
        SINK.append(line.rstrip())
        return
    try:
        if os.path.exists(EVENTS) and os.path.getsize(EVENTS) > MAX_BYTES:
            if os.path.exists(EVENTS + ".1"):
                os.replace(EVENTS + ".1", EVENTS + ".2")
            os.replace(EVENTS, EVENTS + ".1")
        with open(EVENTS, "a") as f:
            f.write(line)
    except OSError:
        pass


_ACE_RATE = {"minute": 0, "n": 0, "dropped": 0}


def ace(msg, t=None):
    """one line into wm-ace.log (rotated at 1 MB, .1 and .2 kept, at most 200 lines per minute)"""
    msg = " ".join(str(msg).split())[:400]
    now = time.time()
    minute = int(now // 60)
    if _ACE_RATE["minute"] != minute:
        dropped, _ACE_RATE["minute"], _ACE_RATE["n"], _ACE_RATE["dropped"] = _ACE_RATE["dropped"], minute, 0, 0
        if dropped:
            ace("%d ACE lines were left out in the last minute (too many)" % dropped)
    _ACE_RATE["n"] += 1
    if _ACE_RATE["n"] > 200:
        _ACE_RATE["dropped"] += 1
        return
    line = "%s  %s\n" % (ts_text(t), msg)
    if SINK is not None:
        SINK.append("ACELOG " + line.rstrip())
        return
    try:
        if os.path.exists(ACELOG) and os.path.getsize(ACELOG) > ACE_MAX:
            if os.path.exists(ACELOG + ".1"):
                os.replace(ACELOG + ".1", ACELOG + ".2")
            os.replace(ACELOG, ACELOG + ".1")
        with open(ACELOG, "a") as f:
            f.write(line)
    except OSError:
        pass


def api(path, timeout=5):
    with urllib.request.urlopen(API + path, timeout=timeout) as r:
        return json.load(r)["result"]


# --------------------------------------------------------------------------------------------------
# klippy.log rules (lines that start at column 0 only; the config copy in the log starts with a tab)
# --------------------------------------------------------------------------------------------------
RE_START = re.compile(r"^Start printer at (.+?) \(")
RE_SHUT = re.compile(r"^Transition to shutdown state: (.*)")
RE_MCU = re.compile(r"^MCU '([^']+)' shutdown: (.*)")
RE_MACRO = re.compile(r"^Error evaluating '([^']+)': (.*)")
RE_ACE = re.compile(r"^ACE\[(\d)\]: (Disconnected.*|Connection stabilized.*|Serial port .*|"
                    r".*(?:[Ee]rror|[Ff]ailed|[Tt]imeout|[Tt]imed out|never).*)")
RE_UNKNOWN = re.compile(r"^(Unknown command.*|Unhandled exception.*)")
RE_ACE_NOISE = re.compile(r"No RFID tag|Reconnect - querying RFID|GET_INFO raw_info")
RE_CFGERR = re.compile(r"^(Config error|Error configuring printer)")
RE_TAILERR = re.compile(r"^[\w.]*(?:Error|error|Exception): .+")


class KlippyRules:
    def __init__(self):
        self.n = 0
        self.last_err = (0, "")
        self.cfg_reported = False

    def feed(self, line):
        """returns the Klipper start time text when this line is a start, else None"""
        self.n += 1
        if not line or line[0] in " \t" or line.startswith("Stats "):
            return None
        if line.startswith("ACE") and not RE_ACE_NOISE.search(line):
            ace(line)
        m = RE_START.match(line)
        if m:
            self.cfg_reported = False
            ev("START", "Klipper started (log says %s)" % m.group(1))
            return m.group(1)
        if RE_TAILERR.match(line):
            self.last_err = (self.n, line)
        m = RE_CFGERR.match(line)
        if m:
            if not self.cfg_reported:
                self.cfg_reported = True
                detail = self.last_err[1] if self.n - self.last_err[0] < 80 else ""
                ev("CONFIG", "Klipper config error. %s" % detail)
            return None
        m = RE_SHUT.match(line)
        if m:
            ev("SHUTDOWN", m.group(1))
            return None
        m = RE_MCU.match(line)
        if m:
            if m.group(2).strip() != "Command request":
                ev("MCU", "%s shutdown: %s" % (m.group(1), m.group(2)))
            return None
        m = RE_MACRO.match(line)
        if m:
            ev("MACRO", "%s: %s" % (m.group(1), m.group(2)))
            return None
        m = RE_ACE.match(line)
        if m:
            ev("ACE", "ACE[%s] %s" % (m.group(1), m.group(2)))
            return None
        m = RE_UNKNOWN.match(line)
        if m:
            ev("ERROR", m.group(1))
        return None


class KlippyTail:
    def __init__(self, rules):
        self.rules = rules
        self.inode = None
        self.pos = 0
        self.rest = b""

    def poll(self):
        started = []
        try:
            st = os.stat(KLIPPY)
        except OSError:
            return started
        if self.inode is None:                       # first look: only new lines from now on
            self.inode, self.pos = st.st_ino, st.st_size
            return started
        if st.st_ino != self.inode or st.st_size < self.pos:   # rotated or cut: read the new file from the start
            self.inode, self.pos, self.rest = st.st_ino, 0, b""
        if st.st_size == self.pos:
            return started
        try:
            with open(KLIPPY, "rb") as f:
                f.seek(self.pos)
                data = f.read(4000000)
        except OSError:
            return started
        self.pos += len(data)
        data = self.rest + data
        lines = data.split(b"\n")
        self.rest = lines.pop()
        for raw in lines:
            r = self.rules.feed(raw.decode("utf8", "ignore"))
            if r:
                started.append(r)
        return started


# --------------------------------------------------------------------------------------------------
# console (Moonraker gcode store) rules
# --------------------------------------------------------------------------------------------------
RE_CMD_SKIP = re.compile(r"^(M105|M114|M115|M27|M20|M155|G[0-3]\b|G9[01]\b|M8[34]\b|_|TEMPERATURE_WAIT|"
                         r"SAVE_GCODE_STATE|RESTORE_GCODE_STATE|ACE_WM_ASSIST|WM_CHAMBER_LIGHT)", re.I)
RE_STEP = re.compile(r"^echo: (Load T\d|Unload T\d|T\d heats|T\d: forming|Toolhead \d|Print start purge|Purge line|"
                     r"Wipe nozzle:|ACE: |Changing tool: )")
RE_STEP_PRINT = re.compile(r"^echo: (Print start purge|Purge line|Load T\d|Unload T\d)")


class ConsoleRules:
    def __init__(self):
        self.printing = False
        self.changes = 0
        self.last_t = None

    def item(self, it):
        t = it.get("time")
        m = " ".join(str(it.get("message", "")).split())
        if not m:
            return
        if (it.get("type") == "command" and m.split(" ")[0].startswith(("ACE_", "_WM_ACE"))) or \
                re.match(r"^(echo: |// |!! )ACE", m):
            ace("console: " + m, t)
        if m.startswith(("// WMLOG ", "echo: WMLOG ")):
            # _WM_LOG_STATE (called by PAUSE, RESUME and CANCEL_PRINT): where the tool head, offsets and heaters were
            ev("STATE", m.split("WMLOG ", 1)[1], t)
            return
        if it.get("type") == "command":
            if m.startswith("SDCARD_PRINT_FILE") or RE_CMD_SKIP.match(m):
                return
            ev("COMMAND", m[:160], t)
            return
        if m.startswith("!! "):
            if m.startswith("!! Error evaluating"):
                return                                # klippy.log rule has it
            ev("ERROR", m[3:], t)
            return
        if m.startswith("echo: start change tool"):
            self.changes += 1
            return
        if "Lock fail" in m and not m.startswith("// LOCK fail retry"):
            ev("TOOLCHG", "tool pickup failed (Lock fail)", t)
            return
        if m.startswith("echo: Idle timeout"):
            ev("IDLE", m[6:], t)
            return
        if RE_STEP.match(m) and (not self.printing or RE_STEP_PRINT.match(m)):
            ev("STEP", m[6:], t)

    def poll(self):
        try:
            items = api("/server/gcode_store?count=300")["gcode_store"]
        except Exception:
            return
        if self.last_t is None:                       # first look: nothing from the past
            self.last_t = max([x.get("time", 0) for x in items] or [time.time()])
            return
        top = self.last_t
        for it in items:
            t = it.get("time", 0)
            if t > self.last_t:
                self.item(it)
                top = max(top, t)
        self.last_t = top


class PrintWatch:
    def __init__(self, console):
        self.console = console
        self.state = None
        self.start = 0

    def poll(self):
        try:
            r = api("/printer/objects/query?print_stats&wm_print_info")["status"]
        except Exception:
            return
        ps = r.get("print_stats", {})
        state = ps.get("state")
        name = ps.get("filename", "")
        self.console.printing = state in ("printing", "paused")
        if state == self.state or state is None:
            return
        old, self.state = self.state, state
        if old is None:
            return
        if state == "printing" and old != "paused":
            self.console.changes = 0
            self.start = time.time()
            wi = r.get("wm_print_info") or {}
            tools = ("tools %s" % ",".join(str(x) for x in wi.get("tools", []))) if wi.get("found") else "tools unknown"
            ev("PRINT", "start %s (%s)" % (name, tools))
        elif state == "printing":
            ev("PRINT", "resumed %s" % name)
        elif state == "paused":
            ev("PRINT", "paused %s" % name)
        elif state in ("complete", "cancelled", "error"):
            dur = ps.get("print_duration") or 0
            extra = ps.get("message") or ""
            ev("PRINT", "%s %s after %d min, %d tool changes %s" % (state, name, dur // 60, self.console.changes, extra))


class StateWatch:
    def __init__(self):
        self.state = None

    def poll(self):
        """returns True when the Klipper state changed"""
        try:
            r = api("/printer/info")
        except Exception:
            return False
        s = r.get("state")
        if s == self.state:
            return False
        old, self.state = self.state, s
        if old is None:
            return True
        msg = (r.get("state_message") or "").strip()
        if s == "ready":
            ev("STATE", "Klipper ready")
        else:
            ev("STATE", "Klipper %s: %s" % (s, " ".join(msg.split())[:240]))
        return True


class SerialWatch:
    """the ACE Pro is a USB serial device: note when it appears or disappears (a USB drop shows here first)"""

    def __init__(self):
        self.ports = None

    def poll(self):
        now = set(glob.glob("/dev/ttyACM*"))
        if self.ports is None:
            self.ports = now
            return
        for p in sorted(now - self.ports):
            ace("USB serial port %s appeared" % p)
            ev("ACE", "USB serial port %s appeared" % p)
        for p in sorted(self.ports - now):
            ace("USB serial port %s DISAPPEARED (USB drop or ACE unplugged)" % p)
            ev("ACE", "USB serial port %s DISAPPEARED (USB drop or ACE unplugged)" % p)
        self.ports = now


RE_SYS = re.compile(r"Started |Stopped |Stopping |Failed|failed|Main process exited|Scheduled restart|killed|"
                    r"Out of memory|\boom\b|code=|signal=|watchdog|Timed out|timed out", re.I)
SYS_UNITS = ("klipper", "moonraker", "KlipperScreen", "crowsnest", "wm-log-digest", "wm-blackbox", "nginx",
             "NetworkManager", "wpa_supplicant", "systemd-timesyncd", "ModemManager")


class SystemLog:
    """wm-system.log: when the printer's services started, stopped, failed or were restarted, and every warning
    or error the system journal holds for them (a service that quietly restarted shows here and nowhere else)"""

    def __init__(self):
        self.first = True

    def poll(self):
        cmd = ["journalctl", "--no-pager", "-o", "short", "--no-hostname", "--cursor-file=" + SYS_CURSOR]
        for u in SYS_UNITS:
            cmd += ["-u", u]
        if self.first:
            cmd += ["-n", "0"]                      # start from now (the first call only sets the cursor)
            self.first = False
            try:
                subprocess.run(cmd, capture_output=True, timeout=20)
            except Exception:
                pass
            return
        try:
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=20).stdout
        except Exception:
            return
        lines = []
        for l in out.splitlines():
            if l.startswith("-- ") or not l.strip():
                continue
            if RE_SYS.search(l) or re.search(r"\b(ERROR|CRITICAL|WARNING)\b", l):
                lines.append(" ".join(l.split())[:300])
        if not lines:
            return
        if len(lines) > 60:
            lines = lines[:60] + ["... %d more lines left out" % (len(lines) - 60)]
        if SINK is not None:
            SINK.extend("SYSLOG " + l for l in lines)
            return
        try:
            if os.path.exists(SYSLOG) and os.path.getsize(SYSLOG) > SYS_MAX:
                os.replace(SYSLOG, SYSLOG + ".1")
            with open(SYSLOG, "a") as f:
                f.write("\n".join(lines) + "\n")
        except OSError:
            pass


# --------------------------------------------------------------------------------------------------
# config check
# --------------------------------------------------------------------------------------------------
OURS = re.compile(r"^(rpi_|zr_)")
RE_INC = re.compile(r"^\[include\s+(.+?)\]\s*$")
RE_SEC = re.compile(r"^\[([^\]]+)\]")
RE_DO = re.compile(r"\{%-?\s*do\s")
RE_RESPOND = re.compile(r'RESPOND\b.*?MSG="(.*)"\s*$')


def walk(path, seen, order, secs, problems):
    """Klipper include order: the sections of one file and of the files it includes, in place"""
    base = os.path.dirname(path)
    try:
        lines = open(path, errors="ignore").read().split("\n")
    except OSError as e:
        problems.append("cannot read %s: %s" % (path, e))
        return
    order.append(path)
    for i, line in enumerate(lines, 1):
        if line.startswith(MARK):
            break
        m = RE_INC.match(line)
        if m:
            pat = m.group(1).strip()
            full = os.path.join(base, pat)
            hits = sorted(glob.glob(full)) if any(c in pat for c in "*?[") else ([full] if os.path.exists(full) else [])
            if not hits:
                problems.append("include not found: [include %s] in %s line %d" % (pat, os.path.basename(path), i))
            for h in hits:
                if h in seen:
                    problems.append("file included twice: %s (in %s line %d)" % (os.path.basename(h), os.path.basename(path), i))
                    continue
                seen.add(h)
                walk(h, seen, order, secs, problems)
            continue
        m = RE_SEC.match(line)
        if m:
            secs.append((m.group(1).strip(), os.path.basename(path), i))


def config_check(reason):
    t0 = time.time()
    problems, warnings, infos = [], [], []
    main = os.path.join(CFG, "printer.cfg")
    order, secs, seen = [], [], {main}
    walk(main, seen, order, secs, problems)

    # printer.cfg: anything written below SAVE_CONFIG that is not the saved data
    try:
        txt = open(main, errors="ignore").read().split("\n")
        if MARK in txt:
            for i, line in enumerate(txt[txt.index(MARK) + 1:], txt.index(MARK) + 2):
                if line.strip() and not line.startswith("#*#"):
                    problems.append("printer.cfg line %d is below SAVE_CONFIG and is not saved data: %s" % (i, line[:70]))
                    break
        else:
            infos.append("printer.cfg has no SAVE_CONFIG block")
    except OSError:
        pass

    # sections defined more than once
    by = {}
    for name, f, i in secs:
        by.setdefault(name, []).append("%s:%d" % (f, i))
    for name, where in sorted(by.items()):
        if len(where) > 1:
            infos.append("[%s] is defined %d times (%s): options of the later one win" % (name, len(where), ", ".join(where)))

    # unsupported Jinja tag, our macro names, RESPOND text
    for path in order:
        base = os.path.basename(path)
        try:
            lines = open(path, errors="ignore").read().split("\n")
        except OSError:
            continue
        for i, line in enumerate(lines, 1):
            if line.startswith(MARK):
                break
            s = line.strip()
            if s.startswith("#"):
                continue
            if RE_DO.search(line):
                problems.append("%s line %d uses the Jinja tag {%% do %%}, this Klipper does not have it (use {%% set _ = list.append(x) %%})" % (base, i))
            if not OURS.match(base):
                continue
            m = re.match(r"^\[(?:gcode_macro|delayed_gcode)\s+(\S+)\]", line)
            if m and re.search(r"\d[A-Za-z]", m.group(1)):
                warnings.append("%s line %d: macro name %s has a digit followed by letters" % (base, i, m.group(1)))
            m = RE_RESPOND.search(line)
            if m:
                lit = m.group(1)
                for _ in range(4):
                    lit = re.sub(r"\{[^{}]*\}", "", lit)
                bad = sorted(set(c for c in lit if c in ";#*"))
                if bad:
                    warnings.append("%s line %d: RESPOND text contains %s" % (base, i, " ".join(bad)))

    # cfg files nobody includes
    names = set(os.path.basename(p) for p in order)
    for p in sorted(glob.glob(os.path.join(CFG, "*.cfg"))):
        b = os.path.basename(p)
        if b in names or re.match(r"^(printer-\d|saved_variables)", b):
            continue
        infos.append("%s is in the config folder but no file includes it" % b)

    # Klipper's own view
    kstate = "unknown"
    try:
        info = api("/printer/info")
        kstate = info.get("state", "?")
        if kstate != "ready":
            problems.append("Klipper is %s: %s" % (kstate, " ".join((info.get("state_message") or "").split())[:300]))
    except Exception as e:
        warnings.append("Moonraker did not answer: %s" % e)
    try:
        w = api("/printer/objects/query?configfile")["status"]["configfile"].get("warnings") or []
        for x in w:
            warnings.append("Klipper says: %s" % (x.get("message") if isinstance(x, dict) else x))
    except Exception:
        pass

    recent = []
    for p in order:
        try:
            m = os.path.getmtime(p)
        except OSError:
            continue
        if t0 - m < 86400:
            recent.append("%s  %s" % (ts_text(m), os.path.basename(p)))

    out = ["WonderMaker config check  %s  (%s)" % (ts_text(t0), reason),
           "Klipper: %s" % kstate,
           "Result: %d problems, %d warnings, %d notes" % (len(problems), len(warnings), len(infos)), ""]
    for tag, lst in (("PROBLEM", problems), ("WARNING", warnings), ("NOTE", infos)):
        for x in lst:
            out.append("%-8s %s" % (tag, x))
    if not (problems or warnings or infos):
        out.append("Nothing found.")
    out += ["", "Files changed in the last 24 hours:"] + (["  " + x for x in sorted(recent)] or ["  none"])
    out += ["", "Include order (%d files): %s" % (len(order), ", ".join(os.path.basename(p) for p in order))]
    return "\n".join(out) + "\n", len(problems), len(warnings), len(infos)


def write_check(reason):
    text, p, w, n = config_check(reason)
    if SINK is None:
        tmp = CHECK + ".tmp"
        with open(tmp, "w") as f:
            f.write(text)
        os.replace(tmp, CHECK)
    ev("CHECK", "config check (%s): %d problems, %d warnings, %d notes. Details in wm-config-check.log" % (reason, p, w, n))
    return text


# --------------------------------------------------------------------------------------------------
# black box copy
# --------------------------------------------------------------------------------------------------
class BlackBox:
    def __init__(self):
        self.sig = None

    def poll(self):
        try:
            st = os.stat(BB_SRC)
        except OSError:
            return
        sig = (st.st_size, int(st.st_mtime))
        if sig == self.sig:
            return
        self.sig = sig
        try:
            with open(BB_SRC, "rb") as f:
                f.seek(max(0, st.st_size - BB_BYTES))
                data = f.read()
            if st.st_size > BB_BYTES:
                data = data.split(b"\n", 1)[-1]
            tmp = BB_DST + ".tmp"
            with open(tmp, "wb") as f:
                f.write(data)
            os.replace(tmp, BB_DST)
        except OSError:
            pass


# --------------------------------------------------------------------------------------------------
def selftest():
    global SINK
    SINK = []
    kr = KlippyRules()
    for l in ["\t{% endif %}", "Stats 1.0: gcodein=0", "Start printer at Tue Nov 17 08:52:58 2026 (1794923578.5 97582.2)",
              "ACE[0]: Disconnected - all timers stopped", "ACE[0]: Stop retract successful: {'id': 1842, 'result': {}, 'code': 0, 'msg': 'success'}",
              "ACE[0]: Connection stabilized (connected for 31s)", "ACE[0]: Slot 1 - No RFID tag (rfid=0), skipping inventory update",
              "ACE[0]: Sending request: {'method': 'feed_filament', 'params': {'index': 3, 'length': 2000, 'speed': 20}}",
              "Error evaluating 'gcode_macro ZR_LOAD:gcode': gcode.CommandError: ZR_LOAD: T must be 0-3",
              "Traceback (most recent call last):", "klippy.configfile.error: Unable to open config file x.cfg",
              "Config error", "Error configuring printer",
              "Transition to shutdown state: Lost communication with MCU 'mcu'",
              "MCU 'mcu' shutdown: Command request", "MCU 'HUB' shutdown: Timer too close", "Unknown command:\"FOO\""]:
        kr.feed(l)
    cr = ConsoleRules()
    for typ, m in [("command", "ZR_LOAD T=3"), ("command", "G1 X10 F3000"), ("command", "M105"),
                   ("response", "!! ACE: toolhead sensor never triggered - check tube (tool T3)"),
                   ("response", "!! Error evaluating 'gcode_macro ZR_LOAD:gcode': x"),
                   ("response", "echo: start change tool T0"), ("response", "// LOCK fail retry 2"), ("response", "// Lock fail"),
                   ("response", "echo: T3 heats to 210 C at the wipe area"), ("response", "echo: Idle timeout, all heaters and motors off"),
                   ("response", "echo: Wipe nozzle done"), ("response", "echo: WMLOG PAUSE start T0 gcode X140.5 Y110.25 Z5.6 E2.0 offset X0.35 Y-0.42 Z0.12 nozzle 220/220 bed 55/55 state printing"), ("response", "B:22.2 /0.0 T0:23.3 /0.0")]:
        cr.item({"time": time.time(), "type": typ, "message": m})
    cr.printing = True
    for m in ["echo: T3 heats to 210 C at the wipe area", "echo: Print start purge: T0 20 mm at the wipe area at 220 C"]:
        cr.item({"time": time.time(), "type": "response", "message": m})
    print("\n".join(SINK))
    SINK = None


def main():
    if "--selftest" in sys.argv:
        selftest()
        return
    if "--check" in sys.argv:
        global SINK
        SINK = []
        print(config_check("manual")[0])
        return
    ev("SERVICE", "wm-log-digest started")
    rules = KlippyRules()
    tail = KlippyTail(rules)
    con = ConsoleRules()
    pw = PrintWatch(con)
    sw = StateWatch()
    bb = BlackBox()
    sp = SerialWatch()
    sl = SystemLog()
    check_at = time.time() + 8
    reason = "service start"
    next_bb = 0
    next_sys = 0
    while True:
        try:
            started = tail.poll()
            if started and check_at is None:
                check_at, reason = time.time() + 30, "after Klipper start"
            con.poll()
            sp.poll()
            pw.poll()
            if time.time() >= next_sys:
                next_sys = time.time() + 30
                sl.poll()
            if sw.poll() and check_at is None:
                check_at, reason = time.time() + 6, "Klipper state changed"
            if check_at is not None and time.time() >= check_at:
                check_at = None
                write_check(reason)
            if time.time() >= next_bb:
                next_bb = time.time() + 60
                bb.poll()
        except Exception as e:                        # the digest must never stop
            try:
                ev("DIGEST", "internal error: %r" % (e,))
            except Exception:
                pass
            time.sleep(10)
        time.sleep(2)


if __name__ == "__main__":
    main()
