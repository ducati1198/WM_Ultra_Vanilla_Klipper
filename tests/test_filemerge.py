#!/usr/bin/env python3
"""Tests of scripts/wm_filemerge.py: the 3-way merge of WonderMaker's macro files and rpi_*.cfg on an update."""
import os, subprocess, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(os.path.dirname(HERE), "scripts", "wm_filemerge.py")

BASE = "".join("line %d\n" % i for i in range(1, 21))


def put(d, name, text):
    p = os.path.join(d, name)
    with open(p, "w") as f:
        f.write(text)
    return p


def run(live, new, basedir, *extra):
    r = subprocess.run([sys.executable, "-I", TOOL, live, new, basedir] + list(extra), capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


class T(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.b = os.path.join(self.d, "base")
        os.makedirs(self.b)
        put(self.b, "m.cfg", BASE)
        self.live = put(self.d, "live.cfg", BASE)
        self.new = put(self.d, "m.cfg", BASE)

    def go(self, *extra):
        return run(self.live, self.new, self.b, "--name", "m.cfg", "--write", "--stamp", "T", *extra)

    def text(self, p=None):
        with open(p or self.live) as f:
            return f.read()

    def test_a_user_never_changed_it(self):
        put(self.d, "m.cfg", BASE.replace("line 5\n", "line 5 NEW\n"))
        rc, out = self.go()
        self.assertEqual(rc, 10, out)
        self.assertIn("line 5 NEW", self.text())
        self.assertEqual(self.text(os.path.join(self.b, "m.cfg")), self.text(self.new))
        self.assertTrue(os.path.exists(os.path.join(os.path.dirname(self.live), "backup", os.path.basename(self.live) + ".wm-before-merge-T")))

    def test_b_wonder_maker_did_not_change_it(self):
        put(self.d, "live.cfg", BASE.replace("line 7\n", "line 7 MINE\n"))
        rc, out = self.go()
        self.assertEqual(rc, 0, out)
        self.assertIn("line 7 MINE", self.text())
        self.assertFalse(os.path.exists(os.path.join(os.path.dirname(self.live), "backup", os.path.basename(self.live) + ".wm-before-merge-T")))

    def test_c_different_lines_both_stay(self):
        put(self.d, "live.cfg", BASE.replace("line 3\n", "line 3 MINE\n"))
        put(self.d, "m.cfg", BASE.replace("line 15\n", "line 15 NEW\n"))
        rc, out = self.go()
        self.assertEqual(rc, 10, out)
        t = self.text()
        self.assertIn("line 3 MINE", t)
        self.assertIn("line 15 NEW", t)

    def test_d_same_line_yours_stays_and_is_reported(self):
        put(self.d, "live.cfg", BASE.replace("line 9\n", "line 9 MINE\n"))
        put(self.d, "m.cfg", BASE.replace("line 9\n", "line 9 NEW\n"))
        rc, out = self.go()
        self.assertEqual(rc, 11, out)
        t = self.text()
        self.assertIn("line 9 MINE", t)
        self.assertNotIn("line 9 NEW", t)
        self.assertNotIn("<<<<", t)
        self.assertIn("line 9 NEW", out)
        self.assertEqual(self.text(os.path.join(self.b, "m.cfg")), self.text(self.new))

    def test_e_both_add_a_macro_in_different_places(self):
        put(self.d, "live.cfg", BASE + "[gcode_macro MY_OWN]\ngcode:\n  M117 mine\n")
        put(self.d, "m.cfg", "[gcode_macro WM_NEW]\ngcode:\n  M117 new\n" + BASE)
        rc, out = self.go()
        self.assertEqual(rc, 10, out)
        t = self.text()
        self.assertIn("MY_OWN", t)
        self.assertIn("WM_NEW", t)

    def test_second_update_after_a_conflict_keeps_yours(self):
        put(self.d, "live.cfg", BASE.replace("line 9\n", "line 9 MINE\n"))
        put(self.d, "m.cfg", BASE.replace("line 9\n", "line 9 NEW\n"))
        self.go()
        rc, out = self.go()
        self.assertEqual(rc, 0, out)
        self.assertIn("line 9 MINE", self.text())

    def test_dry_run_changes_nothing(self):
        put(self.d, "m.cfg", BASE.replace("line 5\n", "line 5 NEW\n"))
        rc, out = run(self.live, self.new, self.b, "--name", "m.cfg")
        self.assertEqual(rc, 10, out)
        self.assertEqual(self.text(), BASE)
        self.assertEqual(self.text(os.path.join(self.b, "m.cfg")), BASE)

    def test_missing_file_is_added(self):
        os.remove(self.live)
        rc, out = self.go()
        self.assertEqual(rc, 10, out)
        self.assertEqual(self.text(), BASE)

    def _repo(self):
        r = os.path.join(self.d, "repo")
        os.makedirs(r)
        env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
        g = lambda *a: subprocess.run(["git", "-C", r] + list(a), check=True, capture_output=True, env=env)
        g("init", "-q")
        os.makedirs(os.path.join(r, "f"))
        v1 = BASE
        v2 = BASE.replace("line 5\n", "line 5 V2\n")
        v3 = v2.replace("line 15\n", "line 15 V3\n")
        for v in (v1, v2, v3):
            put(r, "f/m.cfg", v)
            g("add", "."); g("commit", "-q", "-m", "v")
        return r, v1, v2, v3

    def test_no_baseline_clean_old_version_is_replaced(self):
        r, v1, v2, v3 = self._repo()
        os.remove(os.path.join(self.b, "m.cfg"))
        put(self.d, "live.cfg", v2)
        put(self.d, "m.cfg", v3)
        rc, out = self.go("--git-repo", r, "--git-path", "f/m.cfg")
        self.assertEqual(rc, 10, out)
        self.assertEqual(self.text(), v3)
        self.assertIn("baseline taken from", out)

    def test_no_baseline_your_edit_survives(self):
        r, v1, v2, v3 = self._repo()
        os.remove(os.path.join(self.b, "m.cfg"))
        put(self.d, "live.cfg", v2.replace("line 2\n", "line 2 MINE\n"))
        put(self.d, "m.cfg", v3)
        rc, out = self.go("--git-repo", r, "--git-path", "f/m.cfg")
        self.assertEqual(rc, 10, out)
        t = self.text()
        self.assertIn("line 2 MINE", t)
        self.assertIn("line 15 V3", t)

    def test_no_baseline_and_no_history_leaves_the_file(self):
        os.remove(os.path.join(self.b, "m.cfg"))
        put(self.d, "live.cfg", BASE.replace("line 2\n", "line 2 MINE\n"))
        put(self.d, "m.cfg", BASE.replace("line 15\n", "line 15 NEW\n"))
        rc, out = self.go()
        self.assertEqual(rc, 11, out)
        self.assertIn("line 2 MINE", self.text())
        self.assertNotIn("line 15 NEW", self.text())
        self.assertTrue(os.path.exists(self.live + ".wm-new"))


if __name__ == "__main__":
    unittest.main()
