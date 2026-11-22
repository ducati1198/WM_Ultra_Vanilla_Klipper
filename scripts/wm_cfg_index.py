#!/usr/bin/env python3
"""Header index for the Klipper config files of this project (F-158): a comment block after each file's header that lists the macros
(visible and hidden, with their description:) and the parts of joined files. Comments only, no macro text is touched.

  wm_cfg_index.py write CONFIG_DIR     index rpi_*.cfg and zr_tools.cfg in CONFIG_DIR; a file that changes is copied to
                                       CONFIG_DIR/backup/NAME.wm-before-index-STAMP first. Prints one line per changed file.
                                       Exit 0 nothing to do, 10 something changed.
  wm_cfg_index.py file FILE...         the same for the named files, no backup (used on repo sources)
  wm_cfg_index.py show FILE            print the indexed text, change nothing
Idempotent: the block between the BEGIN and END lines is replaced, never doubled."""
import glob
import os
import re
import shutil
import sys
import time

BEGIN = "# ---- INDEX (auto, wm_cfg_index.py) ----"
END = "# ---- END INDEX ----"
OLD_BEGIN = "# ---- INDEX (auto, mkindex.py) ----"


def build(text, name):
    lines = text.split("\n")
    for b in (BEGIN, OLD_BEGIN):
        if b in lines and END in lines:
            i, j = lines.index(b), lines.index(END)
            del lines[i:j + 1]
            if i < len(lines) and lines[i] == "":
                del lines[i]                     # the blank line build() put after the block
            if 0 < i <= len(lines) and lines[i - 1] == "":
                del lines[i - 1]                 # and the one before it (when the file has a header)
            break
    items, cur = [], None
    for ln in lines:
        m = re.match(r"^\[(gcode_macro|delayed_gcode)\s+(\S+)\]", ln)
        if m:
            cur = [m.group(1), m.group(2), ""]
            items.append(cur)
            continue
        if re.match(r"^\[", ln):
            cur = None
            continue
        if cur and not cur[2]:
            d = re.match(r"^description\s*[:=]\s*(.*)$", ln)
            if d:
                cur[2] = d.group(1).strip()
    vis = [x for x in items if not x[1].startswith("_")]
    hid = [x for x in items if x[1].startswith("_")]
    out = [BEGIN, "# %s: %d macros (%d visible in Fluidd, %d hidden with a leading underscore)" % (name, len(items), len(vis), len(hid))]
    for title, grp in (("Visible", vis), ("Hidden helpers", hid)):
        if grp:
            out.append("# %s:" % title)
            for t, n, d in grp:
                out.append("#   %-34s%s%s" % (n, "[delayed] " if t == "delayed_gcode" else "", (" - " + d[:90]) if d else ""))
    parts = [re.match(r"^# ===== (\S+\.cfg)", ln).group(1) for ln in lines if re.match(r"^# ===== \S+\.cfg", ln)]
    if parts:
        out.append("# Parts of this file (each starts with a banner line): " + ", ".join(parts))
    out.append(END)
    k = 0
    while k < len(lines) and lines[k].startswith("#"):
        k += 1                                    # header = the leading comment lines up to the first blank or code line
    head = lines[:k]
    while head and not head[-1].strip():
        head.pop()
    return "\n".join(head + ([""] if head else []) + out + [""] + lines[k:])


def index_text(text, name):
    """Used by wm_rpi_pi.py: the text with its index (nothing to index = unchanged)."""
    return build(text, name)


def do_file(p, backup_dir=None):
    old = open(p).read()
    new = build(old, os.path.basename(p))
    if new == old:
        return False
    if backup_dir:
        os.makedirs(backup_dir, exist_ok=True)
        shutil.copy2(p, os.path.join(backup_dir, "%s.wm-before-index-%s" % (os.path.basename(p), time.strftime("%Y%m%d-%H%M%S"))))
    tmp = p + ".wm-tmp"
    with open(tmp, "w") as f:
        f.write(new)
    os.replace(tmp, p)
    return True


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    cmd = argv[1]
    if cmd == "show":
        sys.stdout.write(build(open(argv[2]).read(), os.path.basename(argv[2])))
        return 0
    if cmd == "write":
        cd = argv[2]
        files = sorted(glob.glob(os.path.join(cd, "rpi_*.cfg")) + glob.glob(os.path.join(cd, "zr_tools.cfg")))
        bk = os.path.join(cd, "backup")
    elif cmd == "file":
        files, bk = argv[2:], None
    else:
        print(__doc__)
        return 2
    changed = 0
    for p in files:
        if os.path.isfile(p) and do_file(p, bk):
            print("indexed %s" % os.path.basename(p))
            changed += 1
    return 10 if changed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
