#!/usr/bin/env python3
"""Brings a config file of WonderMaker's (a macro file or an rpi_*.cfg) up to the new version and keeps your own edits.

A 3-way merge of three files: the version WonderMaker gave you last time (the baseline, kept in ~/printer_data/wm-baseline),
the new version of this repository, and the file on the Pi. Line by line:

  - you never changed the file                 -> it becomes the new version
  - WonderMaker did not change the file        -> yours stays
  - both changed different lines               -> both changes are in the result
  - both changed the same lines                -> YOUR lines stay, WonderMaker's lines are listed in the output
  - both only ADDED lines at the same place    -> both additions are in (yours first), nothing is lost
  - your file has Windows line endings (CRLF)  -> compared without them and written back the same way
  - no baseline yet (first update with this)   -> the baseline is found in the history of the repository: the older version
                                                  your file is closest to

  wm_filemerge.py LIVE NEW BASEDIR [--name N] [--git-repo R --git-path REL] [--write] [--stamp S]

Without --write nothing is changed. With --write the old file is first copied to backup/NAME.wm-before-merge-S (a backup folder next to LIVE), and the new version
becomes the baseline (BASEDIR/N).
Exit code: 0 nothing to change, 10 the file was changed (or would be), 11 changed, but some lines of yours kept instead of
WonderMaker's (listed), 2 usage or error."""
import os, shutil, subprocess, sys, tempfile


def merge3(live, base, new):
    """-> (merged text, conflicts). On a conflict the lines of the live file are kept, except where both sides only ADDED lines at the
    same place (nothing of the old file changed): then both additions are kept, yours first. conflicts: [(your lines, WonderMaker's lines)]"""
    with tempfile.TemporaryDirectory() as d:
        ps = []
        for n, t in (("yours", live), ("base", base), ("wm", new)):
            p = os.path.join(d, n)
            with open(p, "w", newline="") as f:
                f.write(t)
            ps.append(p)
        cmd = ["git", "merge-file", "-p", "--diff3", "-L", "yours", "-L", "base", "-L", "wm"]
        raw = subprocess.run(cmd + ps, capture_output=True)
        if raw.returncode < 0 or raw.returncode > 127:
            raise RuntimeError("git merge-file failed: " + raw.stderr.decode("utf-8", "replace"))
    conflicts, out, mode, a, o, b = [], [], 0, [], [], []
    for line in raw.stdout.decode("utf-8", "replace").split("\n"):
        if mode == 0 and line.startswith("<<<<<<< yours"):
            mode, a, o, b = 1, [], [], []
        elif mode == 1 and line.startswith("||||||| base"):
            mode = 2
        elif mode == 2 and line == "=======":
            mode = 3
        elif mode == 3 and line.startswith(">>>>>>> wm"):
            if o:
                conflicts.append((a, b))
                out.extend(a)
            else:
                out.extend(a + b)
            mode = 0
        elif mode == 1:
            a.append(line)
        elif mode == 2:
            o.append(line)
        elif mode == 3:
            b.append(line)
        else:
            out.append(line)
    return "\n".join(out), conflicts


def distance(a, b):
    """number of lines that differ between two texts"""
    with tempfile.TemporaryDirectory() as d:
        pa, pb = os.path.join(d, "a"), os.path.join(d, "b")
        for p, t in ((pa, a), (pb, b)):
            with open(p, "w", newline="") as f:
                f.write(t)
        r = subprocess.run(["git", "diff", "--no-index", "--numstat", pa, pb], capture_output=True, text=True)
    n = 0
    for l in r.stdout.splitlines():
        p = l.split("\t")
        if len(p) >= 2 and p[0].isdigit() and p[1].isdigit():
            n += int(p[0]) + int(p[1])
    return n


def guess_base(live, repo, rel, limit=80):
    """-> (text, short commit, differing lines) of the older version in the history that the live file is closest to, or None"""
    r = subprocess.run(["git", "-C", repo, "log", "--format=%H", "-n", str(limit), "--", rel], capture_output=True, text=True)
    best = None
    for h in r.stdout.split():
        s = subprocess.run(["git", "-C", repo, "show", "%s:%s" % (h, rel)], capture_output=True)
        if s.returncode != 0:
            continue
        t = s.stdout.decode("utf-8", "replace")
        dist = 0 if t == live else distance(t, live)
        if best is None or dist < best[2]:
            best = (t, h[:7], dist)
        if dist == 0:
            break
    return best


def read(p):
    with open(p, newline="") as f:
        return f.read()


def decide(live, new, base):
    """-> (kind, result text, conflicts); kind: same, kept, updated, merged, conflicts.
    A file with Windows line endings (CRLF) is compared without the CR and written back with CRLF."""
    crlf = live.count("\r\n") > live.count("\n") / 2
    orig = live
    if crlf:
        live, new, base = (t.replace("\r\n", "\n") for t in (live, new, base))
    if live == new:
        kind, out, conf = "same", new, []
    elif base == new:
        kind, out, conf = "kept", live, []
    elif base == live:
        kind, out, conf = "updated", new, []
    else:
        merged, conf = merge3(live, base, new)
        kind, out = ("conflicts" if conf else "merged"), merged
    if crlf:
        out = out.replace("\n", "\r\n")
        if kind in ("same", "kept"):
            out = orig
    return kind, out, conf


def main(argv):
    args, opt, i = [], {}, 0
    while i < len(argv):
        a = argv[i]
        if a in ("--name", "--git-repo", "--git-path", "--stamp"):
            if i + 1 >= len(argv):
                print(__doc__); return 2
            opt[a], i = argv[i + 1], i + 2
        elif a == "--write":
            opt[a], i = True, i + 1
        else:
            args.append(a); i += 1
    if len(args) != 3:
        print(__doc__); return 2
    live_p, new_p, basedir = args
    name = opt.get("--name") or os.path.basename(new_p)
    stamp = opt.get("--stamp") or "now"
    write = bool(opt.get("--write"))
    base_p = os.path.join(basedir, name)
    if not os.path.isfile(new_p):
        print("%s: the new version is missing (%s)" % (name, new_p)); return 2
    new = read(new_p)
    if not os.path.isfile(live_p):
        print("%s: not on this Pi yet, the new version is copied" % name)
        if write:
            shutil.copyfile(new_p, live_p); os.makedirs(basedir, exist_ok=True); shutil.copyfile(new_p, base_p)
        return 10
    live = read(live_p)
    note = ""
    if os.path.isfile(base_p):
        base = read(base_p)
    elif live == new:
        base = new
    else:
        g = guess_base(live, opt["--git-repo"], opt["--git-path"]) if opt.get("--git-repo") and opt.get("--git-path") else None
        if g is None:
            print("%s: no baseline and no history to find one: the file is left as it is (WonderMaker's version: %s.wm-new)" % (name, live_p))
            if write:
                shutil.copyfile(new_p, live_p + ".wm-new")
            return 11
        base, h, dist = g
        note = "baseline taken from the version of commit %s (your file differs from it in %d lines)" % (h, dist)
    kind, out, conf = decide(live, new, base)
    msg = {"same": "already the new version", "kept": "WonderMaker did not change it, yours stays", "updated": "you never changed it: replaced by the new version",
           "merged": "your edits and WonderMaker's changes are both in", "conflicts": "merged, but %d place(s) kept as you have them" % len(conf)}[kind]
    print("%s: %s" % (name, msg))
    if note:
        print("    " + note)
    for k, (mine, theirs) in enumerate(conf, 1):
        print("    place %d, your lines (kept):" % k)
        for l in mine[:6]:
            print("        " + l)
        print("    place %d, WonderMaker's lines (not used):" % k)
        for l in theirs[:6]:
            print("        " + l)
    changed = out != live
    if write:
        if changed:
            bdir = os.path.join(os.path.dirname(os.path.abspath(live_p)), "backup")
            os.makedirs(bdir, exist_ok=True)
            shutil.copy2(live_p, os.path.join(bdir, os.path.basename(live_p) + ".wm-before-merge-" + stamp))
            with open(live_p, "w", newline="") as f:
                f.write(out)
        os.makedirs(basedir, exist_ok=True)
        shutil.copyfile(new_p, base_p)
    if conf:
        return 11
    return 10 if changed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
