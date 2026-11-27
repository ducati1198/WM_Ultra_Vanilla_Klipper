#!/usr/bin/env python3
"""Fixes and new sections for the machine files of a Pi that is already installed (2.37.0).

Machine files: printer.cfg, saved_variables.cfg, rpi_pi.cfg, moonraker.conf, KlipperScreen.conf (and the CAN ids, which are
never touched). A new version can ADD a missing section or key, FIX a line that has a bug, or REMOVE an old line or section.
Everything else in the file stays as it is. The list of changes is wm_machine_fixes.json (entries, one change each).

  op            what it does
  add_section   [section] with "lines" is added when the section is not there
  add_key       key = value is added when the key is not there (the section is created when it is missing)
  set_key       the key gets this value (the old value is reported); added when it is not there
  remove_key    the key (and its continuation lines) is removed
  remove_section the whole section is removed

Each entry has: id (unique), version, file, op, section, key, value / lines, reason (one line, shown in the report).
Rules:
  - every entry is applied once on a machine; its id goes into the record file. A later change of the user is not undone at the
    next update.
  - printer.cfg: new sections go above the SAVE_CONFIG block; the SAVE_CONFIG block itself is never changed.
  - saved_variables.cfg: only add_key (calibration values are never changed or removed). A missing, empty or damaged file is
    reported (exit 12): the installer asks the user whether to replace it.
  - wm_my_overrides.cfg is the user's own file and is refused. canbus_uuid and serial of an [mcu] section are refused.
  - a file that cannot be read is skipped and reported; a file that is not there is skipped without a word.

  wm_machine_fixes.py CONFIG_DIR [--list FILE] [--record FILE] [--backup-dir DIR] [--stamp S] [--write]

Without --write nothing is changed (a list of what would happen). With --write every changed file is first copied to
BACKUP_DIR/NAME.wm-before-machine-fixes-S.
Exit code: 0 nothing to do, 10 changes made / needed, 11 something was skipped or refused, 12 saved_variables.cfg is missing or
damaged, 2 usage."""
import json, os, re, shutil, sys, time

MARK = re.compile(r"^#\*# <-+ SAVE_CONFIG -+>", re.M)   # Klipper writes: #*# <---------------------- SAVE_CONFIG ---------------------->
SEC = re.compile(r"^\[([^\]]+)\]\s*(?:[#;].*)?$")
OPS = ("add_section", "add_key", "set_key", "remove_key", "remove_section")
USER_FILE = "wm_my_overrides.cfg"
MACHINE = ("printer.cfg", "saved_variables.cfg", "rpi_pi.cfg", "moonraker.conf", "KlipperScreen.conf")


def split_tail(text):
    m = MARK.search(text)
    return (text[:m.start()], text[m.start():]) if m else (text, "")


def find_section(lines, name):
    start = None
    for i, l in enumerate(lines):
        m = SEC.match(l)
        if m and m.group(1).strip() == name:
            start = i
            break
    if start is None:
        return None
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if SEC.match(lines[j]):
            end = j
            break
    return start, end


def key_span(lines, s, e, key):
    rx = re.compile(r"^(" + re.escape(key) + r"\s*[:=]\s*)(.*)$")
    for i in range(s + 1, e):
        m = rx.match(lines[i])
        if m:
            j = i + 1
            while j < e and (lines[j].startswith((" ", "\t")) or lines[j] == ""):
                j += 1
            while j > i + 1 and lines[j - 1] == "":
                j -= 1
            return i, j, m
    return None


def body_end(lines, s, e):
    """index to insert a new line at the end of the section: after the last line that is not a blank or a trailing comment"""
    k = e
    while k > s + 1 and (lines[k - 1].strip() == "" or lines[k - 1].lstrip().startswith(("#", ";"))):
        k -= 1
    return k


def norm(v):
    return " ".join(x.strip() for x in v.split("\n") if x.strip())


def sep_of(lines, s, e):
    """the way the other keys of the section are written: "key: value" or "key = value" """
    for i in range(s + 1, e):
        m = re.match(r"^[A-Za-z_][^\s:=#;]*(\s*[:=]\s*)", lines[i])
        if m:
            return ": " if ":" in m.group(1) else " = "
    return " = "


def kv_line(key, value, sep=" = "):
    parts = str(value).split("\n")
    return ["%s%s%s" % (key, sep, parts[0])] + parts[1:]


def new_block(sec, items):
    return ["[%s]" % sec] + list(items)


def append_block(lines, block):
    while lines and lines[-1] == "":
        lines.pop()
    if lines:
        lines.append("")
    lines.extend(block)
    lines.append("")


def apply_entry(head, e):
    """-> (new head, status, detail); status: applied, already, refused"""
    lines = head.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    op, sec, key = e["op"], e.get("section", ""), e.get("key", "")
    val = e.get("value", "")
    s = find_section(lines, sec) if sec else None
    if op == "add_section":
        if s:
            return head, "already", ""
        append_block(lines, new_block(sec, e.get("lines", [])))
        return "\n".join(lines).rstrip("\n") + "\n", "applied", "added section [%s]" % sec
    if op in ("add_key", "set_key"):
        if not s:
            if op == "add_key" and e.get("create_section") is False:
                return head, "refused", "section [%s] is not in the file" % sec
            append_block(lines, new_block(sec, kv_line(key, val)))
            return "\n".join(lines).rstrip("\n") + "\n", "applied", "added [%s] %s = %s (new section)" % (sec, key, norm(str(val)))
        ks = key_span(lines, s[0], s[1], key)
        if not ks:
            at = body_end(lines, s[0], s[1])
            lines[at:at] = kv_line(key, val, sep_of(lines, s[0], s[1]))
            return "\n".join(lines) + "\n", "applied", "added [%s] %s = %s" % (sec, key, norm(str(val)))
        if op == "add_key":
            return head, "already", ""
        i, j, m = ks
        old = norm(m.group(2) + "\n" + "\n".join(lines[i + 1:j]))
        if old == norm(str(val)):
            return head, "already", ""
        lines[i:j] = [m.group(1) + str(val).split("\n")[0]] + str(val).split("\n")[1:]
        return "\n".join(lines) + "\n", "applied", "fixed [%s] %s: %s -> %s" % (sec, key, old or "(empty)", norm(str(val)))
    if op == "remove_key":
        if not s:
            return head, "already", ""
        ks = key_span(lines, s[0], s[1], key)
        if not ks:
            return head, "already", ""
        i, j, m = ks
        old = norm(m.group(2))
        del lines[i:j]
        return "\n".join(lines) + "\n", "applied", "removed [%s] %s = %s" % (sec, key, old)
    if op == "remove_section":
        if not s:
            return head, "already", ""
        a, b = s
        del lines[a:b]
        while a < len(lines) and a > 0 and lines[a - 1] == "" and lines[a] == "":
            del lines[a]
        return "\n".join(lines) + "\n", "applied", "removed section [%s]" % sec
    return head, "refused", "unknown op %s" % op


def check_entry(e):
    name = os.path.basename(e.get("file", ""))
    if e.get("op") not in OPS:
        return "unknown op"
    if name == USER_FILE:
        return "this is the user's own file"
    if name not in MACHINE:
        return "not a machine file"
    if name == "saved_variables.cfg" and e["op"] != "add_key":
        return "calibration values are never changed or removed"
    if e.get("key") in ("canbus_uuid", "serial") and str(e.get("section", "")).startswith("mcu"):
        return "CAN ids and serial paths belong to this machine"
    return ""


def read(p):
    with open(p, "rb") as f:
        b = f.read()
    return b.decode("utf-8")


def sv_problem(path):
    if not os.path.isfile(path):
        return "the file is missing"
    try:
        t = read(path)
    except Exception:
        return "the file cannot be read (damaged)"
    if not t.strip():
        return "the file is empty"
    if not re.search(r"^\[Variables\]", t, re.M | re.I):
        return "the file has no [Variables] section"
    return ""


def main(argv):
    a = list(argv)
    write = "--write" in a
    if write:
        a.remove("--write")
    opts = {}
    for o in ("--list", "--record", "--backup-dir", "--stamp"):
        if o in a:
            i = a.index(o)
            if i + 1 >= len(a):
                print(__doc__); return 2
            opts[o] = a[i + 1]
            del a[i:i + 2]
    if len(a) != 1:
        print(__doc__); return 2
    cd = a[0]
    lst = opts.get("--list") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "wm_machine_fixes.json")
    stamp = opts.get("--stamp") or time.strftime("%Y%m%d-%H%M%S")
    bdir = opts.get("--backup-dir") or os.path.join(cd, "backup")
    rec = opts.get("--record")
    try:
        entries = json.load(open(lst, encoding="utf-8")).get("entries", [])
    except Exception as ex:
        print("could not read the list %s: %s" % (lst, ex)); return 2
    done = set()
    if rec and os.path.isfile(rec):
        try:
            done = set(json.load(open(rec)).get("ids", []))
        except Exception:
            done = set()
    code = 0
    sv = os.path.join(cd, "saved_variables.cfg")
    why = sv_problem(sv)
    if why:
        print("PROBLEM  saved_variables.cfg: %s" % why)
        code = 12
    by_file = {}
    for e in entries:
        by_file.setdefault(os.path.basename(e.get("file", "")), []).append(e)
    new_ids = set()
    skipped = False
    changed = False
    for name, es in by_file.items():
        path = os.path.join(cd, name)
        todo = [e for e in es if e.get("id") not in done]
        if not todo:
            continue
        if name == "saved_variables.cfg" and sv_problem(path):
            continue      # reported above
        if not os.path.isfile(path):
            continue
        try:
            text = read(path)
        except Exception:
            print("skipped  %s: the file cannot be read" % name); skipped = True
            continue
        if not text.strip():
            print("skipped  %s: the file is empty" % name); skipped = True
            continue
        head, tail = split_tail(text)
        cur = head
        file_changed = False
        for e in todo:
            bad = check_entry(e)
            if bad:
                print("refused  %s: %s (%s)" % (name, e.get("id"), bad)); skipped = True
                continue
            cur2, st, detail = apply_entry(cur, e)
            if st == "applied":
                cur = cur2
                file_changed = True
                print("%s  %s  %s   - %s" % ("fixed  " if detail.startswith("fixed") else ("removed" if detail.startswith("removed") else "added  "), name, detail, e.get("reason", "")))
                new_ids.add(e["id"])
            elif st == "already":
                new_ids.add(e["id"])
            else:
                print("skipped  %s: %s (%s)" % (name, e.get("id"), detail)); skipped = True
        if file_changed:
            changed = True
            if write:
                os.makedirs(bdir, exist_ok=True)
                shutil.copy2(path, os.path.join(bdir, "%s.wm-before-machine-fixes-%s" % (name, stamp)))
                tmp = path + ".wm-tmp"
                with open(tmp, "w", encoding="utf-8", newline="") as f:
                    f.write(cur + (("" if cur.endswith("\n\n") else "\n") if tail else "") + tail)
                os.replace(tmp, path)
    if write and rec and new_ids:
        os.makedirs(os.path.dirname(rec), exist_ok=True)
        json.dump({"ids": sorted(done | new_ids)}, open(rec, "w"))
    if code == 12:
        return 12
    if skipped:
        return 11
    return 10 if changed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
