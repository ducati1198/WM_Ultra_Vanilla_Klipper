#!/usr/bin/env python3
"""Builds scripts/wm_macro_patches.json: the changes this version makes to WonderMaker's macro files (factory/<model>/config),
so that ./installer.sh --update can make the same changes on a Pi that is already installed (scripts/wm_macro_patches.py).

  python3 tools/make_macro_patches.py OLD_GIT_REV VERSION [--check]

OLD_GIT_REV is the commit of the version before (its factory files are the "old" side). Every change becomes one entry
{file, old, new}: "old" is the changed lines plus as many lines around them as it takes to be found exactly once in the old file.
Entries of earlier versions stay in the list (a Pi that skipped versions gets all of them, oldest first). --check writes nothing
and exits 1 when the list is out of date."""
import difflib, json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "scripts", "wm_macro_patches.json")
FILES = ["macros.cfg", "change_macros.cfg", "offset_calibrate.cfg", "extruder0.cfg", "extruder1.cfg", "extruder2.cfg", "extruder3.cfg", "hub.cfg"]


def _expand(a, b, old, i1, i2, j1, j2):
    """The patch for the lines a[i1:i2] -> b[j1:j2] with as much context as it needs to be found exactly once in the old file."""
    ctx = 1
    while True:
        lo, hi = max(0, i1 - ctx), min(len(a), i2 + ctx)
        o = "\n".join(a[lo:hi])
        n = "\n".join(a[lo:i1] + b[j1:j2] + a[i2:hi])
        # "new inside old" is fine (a block removed at the end of the file has nothing after it); "old inside new" is not
        # (the patch would apply again on every update)
        if (old.count(o) == 1 and o and o not in n and (n not in o or hi == len(a))) or (lo == 0 and hi == len(a)):
            return lo, hi, o, n
        ctx += 1


def hunks(old, new):
    a, b = old.split("\n"), new.split("\n")
    ops = [op[1:] for op in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes() if op[0] != "equal"]
    # two changes that lie close together must be one patch: the context of the first would contain lines the second one
    # changes, so the second could not be found any more after the first was applied (F-150, LOAD_FILAMENT / UNLOAD_FILAMENT)
    groups = []
    for op in ops:
        if groups:
            g = groups[-1]
            lo_g, hi_g, _, _ = _expand(a, b, old, g[0], g[1], g[2], g[3])
            lo_o, hi_o, _, _ = _expand(a, b, old, *op)
            if lo_o <= hi_g or lo_g >= hi_o:
                groups[-1] = [g[0], op[1], g[2], op[3]]
                continue
        groups.append(list(op))
    out = []
    for i1, i2, j1, j2 in groups:
        out.append(_expand(a, b, old, i1, i2, j1, j2)[2:])
    return out


def main():
    rev, version = sys.argv[1], sys.argv[2]
    check = "--check" in sys.argv
    cur = json.load(open(OUT)) if os.path.exists(OUT) else []
    keep = [e for e in cur if e["version"] != version]
    new = []
    for f in FILES:
        both = []
        for model in ("ultra", "ultra-s"):
            path = "factory/%s/config/%s" % (model, f)
            old = subprocess.run(["git", "-C", ROOT, "show", "%s:%s" % (rev, path)], capture_output=True, text=True, check=True).stdout
            both.append(hunks(old, open(os.path.join(ROOT, path)).read()))
        if both[0] != both[1]:
            sys.exit("%s: the two models changed differently, this tool keeps one list for both" % f)
        for i, (o, n) in enumerate(both[0]):
            new.append({"version": version, "file": f, "n": i + 1, "old": o, "new": n})
    data = keep + new
    text = json.dumps(data, indent=1, sort_keys=True) + "\n"
    if check:
        ok = os.path.exists(OUT) and open(OUT).read() == text
        print("macro patch list is up to date" if ok else "macro patch list is OUT OF DATE: run python3 tools/make_macro_patches.py %s %s" % (rev, version))
        sys.exit(0 if ok else 1)
    open(OUT, "w").write(text)
    print("wrote %s: %d entries (%d for %s)" % (OUT, len(data), len(new), version))


if __name__ == "__main__":
    main()
