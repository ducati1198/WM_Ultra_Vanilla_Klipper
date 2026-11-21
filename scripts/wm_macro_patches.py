#!/usr/bin/env python3
"""Brings WonderMaker's macro files on a Pi that is already installed up to this version (./installer.sh --update).

A new install gets the macro files of this repository (factory/<model>/config). An update never replaced them, because they may
hold your own edits, so fixes inside macros.cfg, change_macros.cfg, offset_calibrate.cfg and extruder0-3.cfg stayed behind.
This applies each fix as a small text change, listed in wm_macro_patches.json (built by tools/make_macro_patches.py):

  - the new text is already there                   -> nothing to do
  - the old text is there exactly once              -> it is replaced by the new text
  - anything else (you changed these lines)         -> left alone and reported

  wm_macro_patches.py CONFIG_DIR [--write] [--stamp S] [--list FILE]

Without --write nothing is changed. With --write every changed file is first copied to NAME.wm-before-macro-patches-S.
Exit code: 0 nothing to change, 10 changes are needed / were written, 11 some changes could not be applied, 2 usage."""
import json, os, shutil, sys, time


def plan(text, entries):
    """-> (new text, applied, already, skipped) for the entries of one file, in list order"""
    applied, already, skipped = [], [], []
    orig = text
    ok_by_version, bad, proven = {}, [], set()
    for e in entries:
        tag = "%s #%d (%s)" % (e["file"], e["n"], e["version"])
        if text.count(e["old"]) == 1:      # the old lines never contain the new ones (the list is built that way)
            text = text.replace(e["old"], e["new"])
            applied.append(tag)
        elif e["new"] in text:
            already.append(tag)
        else:
            bad.append((e, tag))
            ok_by_version.setdefault(e["version"], []).append(False)
            continue
        ok_by_version.setdefault(e["version"], []).append(True)
        proven.add(id(e))                  # this fix is really in the file (applied now, or its new lines are there)
    key = lambda v: [int(x) for x in v.split(".") if x.isdigit()]
    lines = lambda t: {l.strip() for l in t.split("\n") if l.strip()}
    # a fix whose lines a later fix changed again (its old and new lines are gone): when a later fix that replaced lines this fix
    # wrote is really in the file, this fix is in too. Newest first, so a chain over three versions works (the touch tolerance:
    # 0.5 to 0.1 in 2.14.0, 0.1 to 0.05 in the next one, and the 2.8.0 fix around those lines)
    bad.sort(key=lambda b: key(b[0]["version"]), reverse=True)
    rest = []
    for e, tag in bad:
        wrote = lines(e["new"]) - lines(e["old"])
        later = [l for l in entries if key(l["version"]) > key(e["version"]) and wrote & lines(l["old"])]
        if wrote and later and all(id(l) in proven for l in later):
            already.append(tag + " (changed again by a later fix)")
            proven.add(id(e))
            ok_by_version[e["version"]][ok_by_version[e["version"]].index(False)] = True
        else:
            rest.append((e, tag))
    # the rule of earlier versions: when every fix of every later version of this file is in, the file is at that later state,
    # so the older one is in too (its old and new lines are simply gone)
    for e, tag in rest:
        later = [v for v in ok_by_version if key(v) > key(e["version"])]
        if later and all(all(ok_by_version[v]) for v in later):
            already.append(tag + " (changed again by a later fix)")
        else:
            skipped.append(tag)
    if text == orig:                       # a fix that a later fix takes back (2.13.0 adds, 2.22.0 removes the heat-at-wipe lines) changes nothing
        applied = []
    return text, applied, already, skipped


def main():
    args = sys.argv[1:]
    if not args or args[0].startswith("-"):
        print(__doc__)
        return 2
    cfg = args[0]
    write = "--write" in args
    stamp = args[args.index("--stamp") + 1] if "--stamp" in args else time.strftime("%Y%m%d-%H%M%S")
    lst = args[args.index("--list") + 1] if "--list" in args else os.path.join(os.path.dirname(os.path.abspath(__file__)), "wm_macro_patches.json")
    entries = json.load(open(lst))
    files = []
    for e in entries:
        if e["file"] not in files:
            files.append(e["file"])
    n_applied = n_skipped = 0
    for f in files:
        path = os.path.join(cfg, f)
        if not os.path.isfile(path):
            continue
        text = open(path, errors="replace").read()
        new, applied, already, skipped = plan(text, [e for e in entries if e["file"] == f])
        for tag in applied:
            print("%s %s" % ("changed" if write else "would change", tag))
        for tag in skipped:
            print("not changed %s: these lines are different on this Pi" % tag)
        n_applied += len(applied)
        n_skipped += len(skipped)
        if write and new != text:
            shutil.copy2(path, "%s.wm-before-macro-patches-%s" % (path, stamp))
            open(path, "w").write(new)
    if n_skipped:
        return 11
    return 10 if n_applied else 0


if __name__ == "__main__":
    sys.exit(main())
