#!/usr/bin/env python3
"""Tests of scripts/wm_ultra_backup.py (one folder for every backup, item 36). Throwaway folders only."""
import importlib.util
import os
import shutil
import sys
import tempfile
import time
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("ub", os.path.join(ROOT, "scripts", "wm_ultra_backup.py"))
U = importlib.util.module_from_spec(spec)
spec.loader.exec_module(U)


def put(path, text="x", when=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)
    if when:
        os.utime(path, (when, when))


class Home(unittest.TestCase):
    def setUp(self):
        self.h = tempfile.mkdtemp()
        self.c = os.path.join(self.h, "printer_data", "config")
        os.makedirs(self.c)
        self.u = os.path.join(self.h, "ultra-backup")
        self._limits = dict(U.LIMITS); self._total = U.TOTAL_LIMIT; self._free = U.free_bytes

    def tearDown(self):
        U.LIMITS.clear(); U.LIMITS.update(self._limits); U.TOTAL_LIMIT = self._total; U.free_bytes = self._free
        shutil.rmtree(self.h, ignore_errors=True)

    def run_cli(self, *a):
        sys.stdout = open(os.devnull, "w")
        try:
            return U.main(["x"] + list(a) + ["--home", self.h])
        finally:
            sys.stdout.close(); sys.stdout = sys.__stdout__

    def files(self):
        out = []
        for r, _d, fs in os.walk(self.h):
            out += [os.path.relpath(os.path.join(r, f), self.h) for f in fs]
        return sorted(out)

    def test_config_keeps_newest_copy_and_never_touches_the_safeguard(self):
        for i, n in enumerate(["rpi_base.cfg.wm-before-a-20261110-100000", "rpi_base.cfg.wm-before-b-20261111-100000", "rpi_base.cfg.wm-before-c-20261112-100000"]):
            put(os.path.join(self.c, n), when=time.time() - 1000 + i)
        put(os.path.join(self.c, "saved_variables.cfg.wm-good"))
        put(os.path.join(self.c, "crowsnest.conf.new"))
        put(os.path.join(self.c, "printer.cfg"))
        put(os.path.join(self.c, "printer-20261118_172301.cfg")); put(os.path.join(self.c, "crowsnest.conf.2026-11-18-1616")); put(os.path.join(self.c, "printer.cfg.zrbak_20261119_092137"))
        self.run_cli("sweep")
        f = self.files()
        for n in ("rpi_base.cfg.wm-before-a-20261110-100000", "rpi_base.cfg.wm-before-b-20261111-100000", "rpi_base.cfg.wm-before-c-20261112-100000",
                  "printer-20261118_172301.cfg", "crowsnest.conf.2026-11-18-1616", "printer.cfg.zrbak_20261119_092137"):
            self.assertIn("printer_data/config/backup/" + n, f)      # F-157: every copy, also the newest, goes to config/backup
            self.assertNotIn("printer_data/config/" + n, f)
        for keep in ("saved_variables.cfg.wm-good", "crowsnest.conf.new", "printer.cfg"):
            self.assertIn("printer_data/config/" + keep, f)

    def test_config_backup_keeps_8_copies_per_file(self):
        for i in range(11):
            put(os.path.join(self.c, "backup", "rpi_base.cfg.wm-before-x-202611%02d-100000" % (i + 1)), when=1700000000 + i * 100)
        put(os.path.join(self.c, "backup", "printer.cfg.wm-before-x-20261101-100000"), when=1700000000)
        self.run_cli("prune")
        left = [n for n in self.files() if "backup/rpi_base" in n]
        self.assertEqual(len(left), 8)
        self.assertIn("printer_data/config/backup/rpi_base.cfg.wm-before-x-20261111-100000", left)
        self.assertTrue(any("backup/printer.cfg" in n for n in self.files()))

    def test_second_run_changes_nothing_and_dry_run_changes_nothing(self):
        put(os.path.join(self.h, "wm-backups", "a.tgz")); put(os.path.join(self.h, "fluidd_backup_x", "config.json"))
        before = self.files()
        self.assertEqual(self.run_cli("sweep", "--dry-run"), 10)
        self.assertEqual(self.files(), before)
        self.assertEqual(self.run_cli("sweep"), 10)
        after = self.files()
        self.assertEqual(self.run_cli("sweep"), 0)
        self.assertEqual(self.files(), after)

    def test_old_places_go_to_the_right_type_records_repos_and_the_newest_undo_copy_stay(self):
        old, new = 1700000000, 1700100000
        put(os.path.join(self.h, "wm-backups", "wm-backup-x.tgz")); put(os.path.join(self.h, "wm-backups", "m.json"))
        put(os.path.join(self.h, "wm-backups", "rename-20261113-130537", "a.cfg"))
        put(os.path.join(self.h, "acepro-backup", "fluidd-macros-before-1.json"))
        for n, w in (("wm-20261112_000001", old), ("wm-20261114_000002", new)):
            put(os.path.join(self.h, "acepro-backup", n, "manifest.txt"), when=w); os.utime(os.path.join(self.h, "acepro-backup", n), (w, w))
        put(os.path.join(self.h, "printer_data", "backups", "ace-descriptions-1", "f")); put(os.path.join(self.h, "printer_data", "backups", "x.json"))
        for n, w in (("fluidd_backup_20261112_081041", old), ("fluidd_backup_ui_20261114_112536", new)):
            put(os.path.join(self.h, n, "config.json"), when=w); os.utime(os.path.join(self.h, n), (w, w))
        for n, w in (("old-20261112-000001", old), ("old-20261114-000002", new)):
            put(os.path.join(self.h, "wm-rpi-backup", n, "printer_data", "config", "mine.cfg"), when=w); os.utime(os.path.join(self.h, "wm-rpi-backup", n), (w, w))
        put(os.path.join(self.h, "wm-rpi-backup", "install.conf")); put(os.path.join(self.h, "wm-rpi-backup", "installed.manifest"))
        put(os.path.join(self.h, "repo", ".git", "HEAD")); put(os.path.join(self.h, "fluidd_backup_in_repo", ".git", "HEAD"))
        put(os.path.join(self.c, "printer.cfg.wm-model-bak")); put(os.path.join(self.c, "printer.cfg.wm-before-a-20261110-100000"), when=old); put(os.path.join(self.c, "printer.cfg.wm-before-b-20261111-100000"), when=new)
        self.run_cli("sweep")
        f = " ".join(self.files())
        for want in ("ultra-backup/settings/wm-backup-x.tgz", "ultra-backup/fluidd-macros/", "ultra-backup/config/2026-11-13/rename-20261113-130537/a.cfg",
                     "ultra-backup/installer/2026-11-12/wm-20261112_000001", "ultra-backup/drivers/", "ultra-backup/fluidd-page/2026-11-12/fluidd_backup_20261112_081041/config.json",
                     "ultra-backup/installer/2026-11-12/old-20261112-000001", "ultra-backup/INDEX.txt", "printer_data/config/backup/printer.cfg.wm-before-a-20261110-100000"):
            self.assertIn(want, f, want)
        for stay in ("wm-rpi-backup/install.conf", "wm-rpi-backup/installed.manifest", "wm-rpi-backup/old-20261114-000002/printer_data/config/mine.cfg",
                     "acepro-backup/wm-20261114_000002/manifest.txt", "fluidd_backup_ui_20261114_112536/config.json", "repo/.git/HEAD", "fluidd_backup_in_repo/.git/HEAD",
                     "printer_data/config/printer.cfg.wm-model-bak", "printer_data/config/backup/printer.cfg.wm-before-b-20261111-100000"):
            self.assertIn(stay, f, stay)
        self.assertFalse(os.path.exists(os.path.join(self.h, "wm-backups")))
        self.assertEqual(self.run_cli("sweep"), 0)

    def test_index_says_where_each_backup_came_from(self):
        put(os.path.join(self.h, "wm-backups", "a.tgz"))
        self.run_cli("sweep")
        idx = open(os.path.join(self.u, "INDEX.txt")).read()
        self.assertIn("moved ~/wm-backups/a.tgz -> ~/ultra-backup/settings/a.tgz", idx)

    def test_copies_per_file_limit(self):
        U.LIMITS["config"] = (60 * U.MB, 3)
        for i in range(6):
            put(os.path.join(self.u, "config", "2026-11-1%d" % i, "rpi_base.cfg.wm-before-f%d-2026111%d-100000" % (i, i)), when=1700000000 + i * 100)
        self.run_cli("prune")
        left = [n for n in self.files() if "rpi_base" in n]
        self.assertEqual(len(left), 3)
        self.assertTrue(all(("f3" in n or "f4" in n or "f5" in n) for n in left))   # the newest 3 stay

    def test_size_limit_deletes_the_oldest_first_and_keeps_the_newest(self):
        U.LIMITS["fluidd-page"] = (3 * U.MB, 0)
        for i in range(4):
            d = os.path.join(self.u, "fluidd-page", "2026-11-1%d" % i, "page%d" % i)
            put(os.path.join(d, "big.bin"), "x" * (2 * U.MB), when=1700000000 + i * 100); os.utime(d, (1700000000 + i * 100,) * 2)
        self.run_cli("prune")
        left = sorted(n for n in self.files() if "big.bin" in n)
        self.assertEqual(len(left), 1)
        self.assertIn("page3", left[0])

    def test_whole_folder_limit(self):
        U.TOTAL_LIMIT = 3 * U.MB
        for cat in ("fluidd-page", "installer"):
            for i in range(2):
                d = os.path.join(self.u, cat, "2026-11-1%d" % i, "it%d" % i)
                put(os.path.join(d, "b.bin"), "x" * (2 * U.MB)); os.utime(d, (1700000000 + i * 100 + (50 if cat == "installer" else 0),) * 2)
        self.run_cli("prune")
        total = sum(os.path.getsize(os.path.join(r, f)) for r, _d, fs in os.walk(self.u) for f in fs if f.endswith(".bin"))
        self.assertLessEqual(total, 4 * U.MB)
        self.assertGreaterEqual(total, 2 * U.MB)

    def test_nothing_is_written_when_the_disk_is_nearly_full(self):
        put(os.path.join(self.h, "wm-backups", "a.tgz"))
        U.free_bytes = lambda home: 100 * U.MB
        self.assertEqual(self.run_cli("sweep"), 2)
        self.assertTrue(os.path.exists(os.path.join(self.h, "wm-backups", "a.tgz")))

    def test_add_copies_into_the_type_folder(self):
        src = os.path.join(self.h, "f.cfg"); put(src, "hello")
        self.assertEqual(self.run_cli("add", src, "config"), 0)
        got = [n for n in self.files() if n.startswith("ultra-backup/config/") and "f.cfg" in n]
        self.assertEqual(len(got), 1)
        self.assertEqual(self.run_cli("add", src, "nonsense"), 2)

    def test_settings_archives_stay_flat_for_the_restore_page(self):
        put(os.path.join(self.u, "settings", "2026-11-14", "old.tgz")); put(os.path.join(self.h, "wm-backups", "new.tgz"))
        self.run_cli("sweep")
        f = self.files()
        self.assertIn("ultra-backup/settings/old.tgz", f); self.assertIn("ultra-backup/settings/new.tgz", f)

    def test_panel_installer_folder_is_never_pruned(self):
        # installer/acepro-panel holds the panel installer's undo folders and the saved original Fluidd: the size limits must not touch it
        big = os.path.join(self.u, "installer", "acepro-panel", "original-fluidd", "assets", "app.js")
        put(big, "x" * 2000); put(os.path.join(self.u, "installer", "acepro-panel", "wm-20261110_101010", "manifest.txt"))
        put(os.path.join(self.u, "installer", "2026-11-10", "old-safety", "a.txt"), "y" * 2000, when=1)
        U.LIMITS["installer"] = (1000, 0); U.TOTAL_LIMIT = 1000
        self.run_cli("prune")
        f = self.files()
        self.assertIn("ultra-backup/installer/acepro-panel/original-fluidd/assets/app.js", f)
        self.assertIn("ultra-backup/installer/acepro-panel/wm-20261110_101010/manifest.txt", f)

    def test_status_runs(self):
        self.assertEqual(self.run_cli("status"), 0)


if __name__ == "__main__":
    unittest.main(verbosity=1)
