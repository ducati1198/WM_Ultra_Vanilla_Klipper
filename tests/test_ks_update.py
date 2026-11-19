"""F-151: patch_ks_update.py on a stock KlipperScreen base_panel.py (fixture)."""
import os, shutil, subprocess, sys, tempfile
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
d = tempfile.mkdtemp(); f = os.path.join(d, "base_panel.py")
shutil.copy(os.path.join(R, "tests/fixtures/ks_base_panel_stock.py"), f)
run = lambda: subprocess.run([sys.executable, "-I", os.path.join(R, "zr_tools/patch_ks_update.py"), f]).returncode
ok = run() == 0; s = open(f).read()
ok &= s.count("WM F-151") == 3 and "_wm_auto_finish" in s and "self._wm_start_auto_finish()" in s
compile(s, f, "exec")
ok &= run() == 0 and open(f).read() == s            # idempotent
open(f, "w").write("nothing here"); ok &= run() == 1  # a file that does not match is refused
print("ks_update:", "ok" if ok else "FAILED"); sys.exit(0 if ok else 1)
