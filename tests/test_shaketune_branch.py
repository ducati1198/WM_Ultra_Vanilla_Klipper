#!/usr/bin/env python3
"""Shake&Tune: a detached copy is put on branch main at the same commit, files unchanged (Moonraker showed a detached copy as INVALID)."""
import os, re, subprocess, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(ROOT, "installer.sh")).read()
m = re.search(r"^shaketune_on_branch\(\) \{.*?^\}", src, re.M | re.S)
assert m, "shaketune_on_branch is missing from installer.sh"
def git(d, *a): return subprocess.run(["git", "-C", d, "-c", "user.email=a@b", "-c", "user.name=a"] + list(a), capture_output=True, text=True).stdout.strip()
bad = 0
with tempfile.TemporaryDirectory() as t:
    r = os.path.join(t, "r"); subprocess.run(["git", "init", "-q", r], check=True)
    open(os.path.join(r, "f"), "w").write("1\n"); git(r, "add", "f"); git(r, "commit", "-qm", "one"); git(r, "checkout", "-q", "--detach")
    head = git(r, "rev-parse", "HEAD")
    subprocess.run(["bash", "-c", m.group(0) + '\nshaketune_on_branch "$1"', "x", r], check=True)
    ok1 = git(r, "symbolic-ref", "-q", "HEAD") == "refs/heads/main"; ok2 = git(r, "rev-parse", "HEAD") == head; ok3 = git(r, "status", "--porcelain") == ""
    subprocess.run(["bash", "-c", m.group(0) + '\nshaketune_on_branch "$1"', "x", r], check=True)   # second run changes nothing
    ok4 = git(r, "rev-parse", "HEAD") == head and git(r, "symbolic-ref", "-q", "HEAD") == "refs/heads/main"
    for n, ok in (("on branch main", ok1), ("same commit", ok2), ("files unchanged", ok3), ("second run changes nothing", ok4)):
        print(("ok   " if ok else "FAIL ") + n); bad += (not ok)
sys.exit(1 if bad else 0)
