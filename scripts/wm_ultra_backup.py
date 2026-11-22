#!/usr/bin/env python3
"""wm_ultra_backup.py - one folder for every backup the Pi keeps (item 36).

  wm_ultra_backup.py sweep   [--home DIR] [--dry-run]   move the old backups into ~/ultra-backup, then enforce the size limits
  wm_ultra_backup.py add FILE_OR_DIR CATEGORY [--home DIR] copy something into ~/ultra-backup/CATEGORY/<date>/
  wm_ultra_backup.py prune   [--home DIR] [--dry-run]   enforce the size limits only
  wm_ultra_backup.py status  [--home DIR]               sizes per type and the limits

Folders under ~/ultra-backup (by type, the date inside):
  printer_data/config/backup/   F-157: EVERY copy of a config file (*.wm-before-*, *.wm-*, .bak, .orig, Klipper's printer-<date>_<time>.cfg,
                 crowsnest.conf.<date>) goes here, flat, so the config folder only holds the live files; newest 8 per file, 60 MB
  config/        copies that older versions of the installer moved here (kept; no new ones are added)
  fluidd-page/   copies of the Fluidd web page
  fluidd-macros/ Fluidd macro lists (.json)
  settings/      "Back up my settings" archives (.tgz)
  installer/     old installer safety folders
  drivers/       copies of Klipper driver files and ACE driver edits
  other/         anything else, and test leftovers

Never touched: installer/acepro-panel (the panel installer's undo folders and the saved original Fluidd: it prunes them itself, and --undo and
--uninstall need them), saved_variables.cfg.wm-good (the safeguard copy), printer.cfg.wm-model-bak and other copies the installer reads again,
crowsnest.conf.new, any git repository folder, the records in ~/wm-rpi-backup (install.conf, installed.manifest, panel.version), and the NEWEST
folder of each undo store (~/wm-rpi-backup old-*/fluidd-*, ~/acepro-backup wm-*, ~/fluidd_backup_*): ./installer.sh --undo restores from those.
Nothing is deleted by a move. Only the size limits delete, the oldest first. Not enough free disk space (under 2 GB): nothing is written.
"""
import os, re, shutil, sys, time

MB = 1024 * 1024
TOTAL_LIMIT = 400 * MB
LIMITS = {   # category: (max bytes, max copies per name or 0 for no count limit)
    "config": (60 * MB, 8), "fluidd-page": (120 * MB, 6), "fluidd-macros": (20 * MB, 0),
    "settings": (150 * MB, 5), "installer": (20 * MB, 0), "drivers": (20 * MB, 0), "other": (20 * MB, 0),
}
MIN_FREE = 2048 * MB
INDEX_MAX = 1 * MB
COPY_RE = re.compile(r"^(?P<base>.+?)\.(?:wm-[A-Za-z0-9_-]*|bak|orig)(?:[-.]?\d{8}[-_]\d{6})?$")
KLIPPER_COPY_RE = re.compile(r"^printer-\d{8}_\d{6}\.cfg$")               # Klipper's own copy before SAVE_CONFIG
DATED_COPY_RE = re.compile(r"^(?P<base>.+?)\.20\d\d-\d\d-\d\d-\d{4}$")   # e.g. crowsnest.conf.2026-11-18-1616
ZRBAK_RE = re.compile(r"^(?P<base>.+?)\.zrbak[-_]?(?:\d{8}[-_]\d{6})?$")          # e.g. printer.cfg.zrbak_20261119_092137 (copy made by the factory/ZR tools)
CONFIG_BACKUP_DIR = "backup"                                                 # printer_data/config/backup (F-157)
CONFIG_BACKUP_COPIES = 8
CONFIG_BACKUP_CAP = 60 * MB


def copy_base(name):
    """The file a backup copy belongs to (rpi_base.cfg for rpi_base.cfg.wm-before-x-2026...), or None when it is not a copy."""
    if name.endswith(".new"):
        return None
    m = COPY_RE.match(name)
    if m:
        return m.group("base")
    if KLIPPER_COPY_RE.match(name):
        return "printer.cfg"
    m = DATED_COPY_RE.match(name)
    if m:
        return m.group("base")
    m = ZRBAK_RE.match(name)
    return m.group("base") if m else None
KEEP_NAMES = {"saved_variables.cfg.wm-good"}
MANAGED = {"acepro-panel"}   # folders under installer/ that the panel installer manages itself (undo folders + the original Fluidd, never pruned here)
KEEP_SUFFIX = (".wm-good", ".wm-model-bak", ".wm-keep")   # files the installer reads again: never moved


def home_dir(args):
    if "--home" in args:
        return args[args.index("--home") + 1]
    return os.environ.get("WM_HOME") or os.path.expanduser("~")


def size_of(path):
    if os.path.isfile(path) or os.path.islink(path):
        try:
            return os.lstat(path).st_size
        except OSError:
            return 0
    total = 0
    for r, _d, files in os.walk(path):
        for f in files:
            try:
                total += os.lstat(os.path.join(r, f)).st_size
            except OSError:
                pass
    return total


def is_git(path):
    return os.path.isdir(os.path.join(path, ".git"))


def free_bytes(home):
    try:
        st = os.statvfs(home)
        return st.f_bavail * st.f_frsize
    except OSError:
        return MIN_FREE * 10


def log_index(ult, line):
    os.makedirs(ult, exist_ok=True)
    idx = os.path.join(ult, "INDEX.txt")
    try:
        if os.path.exists(idx) and os.path.getsize(idx) > INDEX_MAX:
            os.replace(idx, idx + ".1")
    except OSError:
        pass
    with open(idx, "a") as f:
        f.write("%s  %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), line))


def dated_dir(ult, cat, when=None):
    day = time.strftime("%Y-%m-%d", time.localtime(when or time.time()))
    d = os.path.join(ult, cat, day)
    os.makedirs(d, exist_ok=True)
    return d


def unique(dst):
    if not os.path.exists(dst):
        return dst
    n = 1
    while os.path.exists("%s.%d" % (dst, n)):
        n += 1
    return "%s.%d" % (dst, n)


def move(src, ult, cat, home, dry, note=""):
    """Move src into ult/cat/<date of its last change>/ and write the index line. Returns the new path (or planned path)."""
    try:
        when = os.path.getmtime(src)
    except OSError:
        return None
    day = time.strftime("%Y-%m-%d", time.localtime(when))
    flat = (cat == "settings")   # the installer lists and restores ~/ultra-backup/settings/*.tgz, so these stay in one flat folder
    m = re.search(r"(20\d\d)(\d\d)(\d\d)", os.path.basename(src))   # the date in the name wins (cp -p keeps the old file date)
    if m and 1 <= int(m.group(2)) <= 12 and 1 <= int(m.group(3)) <= 31:
        day = "%s-%s-%s" % m.groups()
    dst = unique(os.path.join(ult, cat, os.path.basename(src)) if flat else os.path.join(ult, cat, day, os.path.basename(src)))
    if dry:
        print("would move  %s  ->  %s" % (src, dst))
        return dst
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.move(src, dst)
    log_index(ult, "moved %s -> %s%s" % (src.replace(home, "~"), dst.replace(home, "~"), (" " + note) if note else ""))
    return dst


def sweep_config(home, ult, dry):
    """printer_data/config: every backup copy moves to printer_data/config/backup (F-157), so the config folder holds the live files only.
    Never moved: saved_variables.cfg.wm-good and the other files the installer reads again (KEEP_NAMES, KEEP_SUFFIX), *.new."""
    cdir = os.path.join(home, "printer_data", "config")
    if not os.path.isdir(cdir):
        return 0
    bdir = os.path.join(cdir, CONFIG_BACKUP_DIR)
    n = 0
    for name in sorted(os.listdir(cdir)):
        p = os.path.join(cdir, name)
        if not os.path.isfile(p) or name in KEEP_NAMES or name.endswith(KEEP_SUFFIX) or copy_base(name) is None:
            continue
        dst = unique(os.path.join(bdir, name))
        if dry:
            print("would move  %s  ->  %s" % (p, dst)); n += 1; continue
        os.makedirs(bdir, exist_ok=True)
        shutil.move(p, dst)
        log_index(ult, "moved %s -> %s" % (p.replace(home, "~"), dst.replace(home, "~")))
        n += 1
    return n


def prune_config_backup(home, ult, dry):
    """printer_data/config/backup: the newest CONFIG_BACKUP_COPIES of each file stay, and the folder stays under CONFIG_BACKUP_CAP (oldest go first)."""
    bdir = os.path.join(home, "printer_data", "config", CONFIG_BACKUP_DIR)
    if not os.path.isdir(bdir):
        return 0
    items = []
    for name in os.listdir(bdir):
        p = os.path.join(bdir, name)
        if os.path.isfile(p):
            items.append((os.path.getmtime(p), p, size_of(p), copy_base(name) or name))
    items.sort()   # oldest first
    removed = 0
    by_base = {}
    for it in items:
        by_base.setdefault(it[3], []).append(it)
    for lst in by_base.values():
        for it in lst[:-CONFIG_BACKUP_COPIES]:
            if dry:
                print("would delete (more than %d copies)  %s" % (CONFIG_BACKUP_COPIES, it[1]))
            else:
                remove(it[1]); log_index(ult, "deleted %s (more than %d copies)" % (it[1].replace(home, "~"), CONFIG_BACKUP_COPIES))
            items = [x for x in items if x[1] != it[1]]; removed += 1
    total = sum(i[2] for i in items)
    while total > CONFIG_BACKUP_CAP and len(items) > 1:
        it = items.pop(0)
        if dry:
            print("would delete (config/backup over %d MB)  %s" % (CONFIG_BACKUP_CAP // MB, it[1]))
        else:
            remove(it[1]); log_index(ult, "deleted %s (config/backup over %d MB)" % (it[1].replace(home, "~"), CONFIG_BACKUP_CAP // MB))
        total -= it[2]; removed += 1
    return removed


def flatten_settings(ult, dry):
    """Settings archives that an earlier version put in date folders go up one level, where the installer's restore page looks."""
    n = 0
    sd = os.path.join(ult, "settings")
    if not os.path.isdir(sd):
        return 0
    for day in sorted(os.listdir(sd)):
        dd = os.path.join(sd, day)
        if not (os.path.isdir(dd) and DAY_RE.match(day)):
            continue
        for name in sorted(os.listdir(dd)):
            if dry:
                print("would move  %s  ->  %s" % (os.path.join(dd, name), os.path.join(sd, name))); n += 1; continue
            shutil.move(os.path.join(dd, name), unique(os.path.join(sd, name))); n += 1
        if not dry:
            try:
                os.rmdir(dd)
            except OSError:
                pass
    return n


def move_older(folder, match, cat, ult, home, dry, keep=1):
    """Folders in `folder` that match: the newest `keep` stay, the older ones move."""
    items = []
    for name in os.listdir(folder):
        p = os.path.join(folder, name)
        if os.path.isdir(p) and not os.path.islink(p) and not is_git(p) and match(name):
            items.append((os.path.getmtime(p), p))
    items.sort(reverse=True)
    n = 0
    for _t, p in items[keep:]:
        if move(p, ult, cat, home, dry):
            n += 1
    return n


def sweep_home(home, ult, dry):
    n = flatten_settings(ult, dry)
    # Settings backups folder from the installer (~/wm-backups): archives, macro lists, migration copies
    wb = os.path.join(home, "wm-backups")
    if os.path.isdir(wb) and not is_git(wb):
        for name in sorted(os.listdir(wb)):
            p = os.path.join(wb, name)
            if name.endswith(".tgz"):
                cat = "settings"
            elif name.endswith(".json"):
                cat = "fluidd-macros"
            else:
                cat = "config"
            if move(p, ult, cat, home, dry):
                n += 1
        if not dry:
            try:
                os.rmdir(wb)
            except OSError:
                pass
    # other known old places
    d = os.path.join(home, "wm-test-backup-stage1")
    if os.path.isdir(d) and not is_git(d) and move(d, ult, "other", home, dry):
        n += 1
    # ~/acepro-backup: the macro lists go; the wm-<time> folders are the panel installer's undo store, its newest one stays
    d = os.path.join(home, "acepro-backup")
    if os.path.isdir(d) and not is_git(d):
        for name in sorted(os.listdir(d)):
            if name.endswith(".json") and move(os.path.join(d, name), ult, "fluidd-macros", home, dry):
                n += 1
        n += move_older(d, lambda x: x.startswith("wm-"), "installer", ult, home, dry)
        if not dry:
            try:
                os.rmdir(d)
            except OSError:
                pass
    # printer_data/backups
    pb = os.path.join(home, "printer_data", "backups")
    if os.path.isdir(pb):
        for name in sorted(os.listdir(pb)):
            cat = "fluidd-macros" if name.endswith(".json") else ("drivers" if name.startswith("ace-") else "other")
            if move(os.path.join(pb, name), ult, cat, home, dry):
                n += 1
        if not dry:
            try:
                os.rmdir(pb)
            except OSError:
                pass
    # Fluidd web page copies in the home folder: the panel installer's --undo restores the newest, so the newest stays
    n += move_older(home, lambda x: x.startswith("fluidd_backup"), "fluidd-page", ult, home, dry)
    # ~/wm-rpi-backup is the installer's own undo store and record (old-*, fluidd-*, install.conf, installed.manifest): the files stay,
    # and of each family of folders the newest stays (./installer.sh --undo restores from it); older ones move
    ib = os.path.join(home, "wm-rpi-backup")
    if os.path.isdir(ib):
        for prefix, cat in (("old-", "installer"), ("undone-", "installer"), ("uuid-", "installer"), ("wifi-", "installer"), ("fluidd-", "fluidd-page")):
            n += move_older(ib, lambda x, pr=prefix: x.startswith(pr), cat, ult, home, dry)
    return n


DAY_RE = re.compile(r"^\d{4}-\d\d-\d\d$")


def entries(cat_dir):
    """(mtime, path, size) for each saved item: inside the date folders, or loose in the type folder."""
    out = []
    if not os.path.isdir(cat_dir):
        return out
    for name in sorted(os.listdir(cat_dir)):
        p = os.path.join(cat_dir, name)
        if os.path.isdir(p) and DAY_RE.match(name):
            for sub in os.listdir(p):
                q = os.path.join(p, sub)
                try:
                    out.append((os.path.getmtime(q), q, size_of(q)))
                except OSError:
                    pass
        else:
            try:
                out.append((os.path.getmtime(p), p, size_of(p)))
            except OSError:
                pass
    return out


def remove(path):
    if os.path.isdir(path) and not os.path.islink(path):
        shutil.rmtree(path, ignore_errors=True)
    else:
        try:
            os.remove(path)
        except OSError:
            pass
    parent = os.path.dirname(path)
    if DAY_RE.match(os.path.basename(parent)):
        try:
            os.rmdir(parent)   # an empty date folder goes away
        except OSError:
            pass


def prune(home, ult, dry):
    removed = 0
    allitems = []
    for cat, (cap, copies) in LIMITS.items():
        items = sorted(i for i in entries(os.path.join(ult, cat)) if os.path.basename(i[1]) not in MANAGED)   # oldest first
        if copies:   # newest N per base name
            by_base = {}
            for it in items:
                nm = os.path.basename(it[1])
                m = COPY_RE.match(nm)
                by_base.setdefault(m.group("base") if m else re.sub(r"[-_.]?\d{8}[-_]?\d{6}.*$", "", nm), []).append(it)
            for lst in by_base.values():
                for it in lst[:-copies]:
                    if dry:
                        print("would delete (more than %d copies)  %s" % (copies, it[1]))
                    else:
                        remove(it[1])
                        log_index(ult, "deleted %s (more than %d copies)" % (it[1].replace(home, "~"), copies))
                    removed += 1
                    items = [x for x in items if x[1] != it[1]]
        total = sum(i[2] for i in items)
        while total > cap and len(items) > 1:
            it = items.pop(0)
            if dry:
                print("would delete (%s over %d MB)  %s" % (cat, cap // MB, it[1]))
            else:
                remove(it[1]); log_index(ult, "deleted %s (%s over %d MB)" % (it[1].replace(home, "~"), cat, cap // MB))
            total -= it[2]; removed += 1
        allitems += items
    removed += prune_config_backup(home, ult, dry)
    allitems.sort()
    total = sum(i[2] for i in allitems)
    while total > TOTAL_LIMIT and len(allitems) > 1:
        it = allitems.pop(0)
        if dry:
            print("would delete (folder over %d MB)  %s" % (TOTAL_LIMIT // MB, it[1]))
        else:
            remove(it[1]); log_index(ult, "deleted %s (folder over %d MB)" % (it[1].replace(home, "~"), TOTAL_LIMIT // MB))
        total -= it[2]; removed += 1
    return removed


def status(home, ult):
    print("ultra backup folder: %s" % ult.replace(home, "~"))
    tot = 0
    for cat, (cap, copies) in LIMITS.items():
        items = entries(os.path.join(ult, cat)); s = sum(i[2] for i in items); tot += s
        print("  %-14s %4d items  %7.1f MB  (limit %d MB%s)" % (cat, len(items), s / MB, cap // MB, (", %d copies per file" % copies) if copies else ""))
    bd = os.path.join(home, "printer_data", "config", CONFIG_BACKUP_DIR)
    bi = [f for f in os.listdir(bd) if os.path.isfile(os.path.join(bd, f))] if os.path.isdir(bd) else []
    print("  %-14s %4d items  %7.1f MB  (printer_data/config/backup, limit %d MB, %d copies per file)" % ("config/backup", len(bi), sum(size_of(os.path.join(bd, f)) for f in bi) / MB, CONFIG_BACKUP_CAP // MB, CONFIG_BACKUP_COPIES))
    print("  %-14s %4s        %7.1f MB  (limit %d MB)" % ("total", "", tot / MB, TOTAL_LIMIT // MB))
    print("  free disk: %.1f GB" % (free_bytes(home) / 1024 / MB))
    return tot


def main(argv):
    if len(argv) < 2 or argv[1] in ("-h", "--help"):
        print(__doc__); return 0
    cmd, args = argv[1], argv[2:]
    home = home_dir(args); ult = os.path.join(home, "ultra-backup"); dry = "--dry-run" in args
    if cmd == "status":
        status(home, ult); return 0
    if cmd in ("sweep", "add") and not dry and free_bytes(home) < MIN_FREE:
        print("wm_ultra_backup: less than 2 GB free on the Pi, nothing was written", file=sys.stderr); return 2
    if cmd == "sweep":
        n = sweep_config(home, ult, dry) + sweep_home(home, ult, dry)
        r = prune(home, ult, dry)
        print("%s %d backup item(s), %s %d over the size limit" % ("would move" if dry else "moved", n, "would delete" if dry else "deleted", r))
        return 10 if n or r else 0
    if cmd == "prune":
        r = prune(home, ult, dry)
        print("%s %d item(s)" % ("would delete" if dry else "deleted", r)); return 10 if r else 0
    if cmd == "add":
        pos = [a for a in args if not a.startswith("--") and a != home]
        if len(pos) < 2 or pos[1] not in LIMITS:
            print("usage: add FILE_OR_DIR CATEGORY (%s)" % ", ".join(LIMITS), file=sys.stderr); return 2
        src, cat = pos[0], pos[1]
        if not os.path.exists(src):
            print("wm_ultra_backup: %s does not exist" % src, file=sys.stderr); return 2
        dst = unique(os.path.join(dated_dir(ult, cat), os.path.basename(src) + "." + time.strftime("%Y%m%d-%H%M%S")))
        (shutil.copytree if os.path.isdir(src) else shutil.copy2)(src, dst)
        log_index(ult, "saved %s -> %s" % (src.replace(home, "~"), dst.replace(home, "~")))
        prune(home, ult, False)
        print(dst); return 0
    print("unknown command: %s" % cmd, file=sys.stderr); return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
