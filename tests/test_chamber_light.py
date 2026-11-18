"""Chamber light: the board's network service (wm-chamber-light-http) with a fake helper, the registration upload
against a fake Moonraker, and the root helper script against a fake sysfs folder."""
import http.client
import importlib.machinery
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
passed = failed = 0


def check(name, cond):
    global passed, failed
    if cond:
        passed += 1
        print("  ok   ", name)
    else:
        failed += 1
        print("  FAIL ", name)


tmp = tempfile.mkdtemp()
fake = os.path.join(tmp, "helper.sh")
state = os.path.join(tmp, "state")
open(fake, "w").write('#!/bin/sh\nf=%s; [ -f $f ] || echo off > $f\ncase $1 in on|off) echo $1 > $f;; toggle) [ "$(cat $f)" = on ] && echo off > $f || echo on > $f;; esac\ncat $f\n' % state)
os.chmod(fake, 0o755)

src = open(os.path.join(ROOT, "zr_tools", "wm-chamber-light-http")).read().replace('HELPER = "/usr/local/sbin/wm-chamber-light"', 'HELPER = "%s"' % fake)
svc_path = os.path.join(tmp, "svc.py")
open(svc_path, "w").write(src)
loader = importlib.machinery.SourceFileLoader("svc", svc_path)
spec = importlib.util.spec_from_loader("svc", loader)
svc = importlib.util.module_from_spec(spec)
loader.exec_module(svc)

srv = ThreadingHTTPServer(("127.0.0.1", 0), svc.Handler)
port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()


def call(method, path, body=None):
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    c.request(method, path, body=body)
    r = c.getresponse()
    data = r.read()
    return r.status, dict(r.getheaders()), (json.loads(data) if data else None)


print("network service")
st, h, d = call("GET", "/light")
check("GET /light says off at first", st == 200 and d == {"on": False})
check("answers carry the CORS header the Fluidd page needs", h.get("Access-Control-Allow-Origin") == "*")
st, _, d = call("POST", "/light/toggle")
check("POST /light/toggle turns it on", st == 200 and d == {"on": True})
st, _, d = call("POST", "/light", json.dumps({"on": False}))
check("POST /light {on:false} turns it off", st == 200 and d == {"on": False})
st, _, d = call("POST", "/light", json.dumps({"on": "yes"}))
check("a body that is not true/false is refused", st == 400)
st, _, _ = call("GET", "/nothing")
check("other paths are 404", st == 404)
st, _, _ = call("OPTIONS", "/light")
check("OPTIONS (browser preflight) is answered", st == 204)

print("registration upload")
got = {}


class FakeMoonraker(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        body = self.rfile.read(int(self.headers["Content-Length"])).decode()
        got["path"] = self.path
        got.setdefault("all", []).append(body)
        if 'filename="rpi_chamber_light.json"' in body:
            got["body"] = body
        self.send_response(201)
        self.end_headers()
        self.wfile.write(b"{}")


try:
    mr = HTTPServer(("127.0.0.1", 7125), FakeMoonraker)
except OSError:
    mr = None
if mr:
    threading.Thread(target=mr.serve_forever, daemon=True).start()
    conf = os.path.join(tmp, "KlipperScreen.conf")
    open(conf, "w").write("[printer X]\nmoonraker_host: 127.0.0.1\n")
    ok = svc.register(conf, 8765)
    check("register uploads rpi_chamber_light.json into the config folder", ok and got.get("path") == "/server/files/upload" and 'filename="rpi_chamber_light.json"' in got["body"] and "config" in got["body"] and '"url": "http://127.0.0.1:8765"' in got["body"])
    cam_body = next((b for b in got.get("all", []) if 'filename="rpi_screen_camera.json"' in b), "")
    check("register also tells the Pi about the camera on the board (rpi_screen_camera.json, empty address when none)", '"url": ""' in cam_body or '"url": "http://127.0.0.1:8080"' in cam_body)
    check("camera_url is empty without a camera in /dev/v4l/by-id", svc.camera_url("10.0.0.2") in ("", "http://10.0.0.2:8080"))
    check("no conf file means no upload and no crash", svc.register(os.path.join(tmp, "none.conf"), 8765) is False)
    mr.shutdown()
else:
    print("  (port 7125 is busy here: registration test skipped)")

print("root helper (fake sysfs)")
helper_src = open(os.path.join(ROOT, "zr_tools", "wm-chamber-light")).read()
gpio = os.path.join(tmp, "gpio")
os.makedirs(os.path.join(gpio, "gpio76"))
open(os.path.join(gpio, "export"), "w").close()
open(os.path.join(gpio, "gpio76", "value"), "w").write("0\n")
open(os.path.join(gpio, "gpio76", "direction"), "w").write("in\n")
hp = os.path.join(tmp, "wm-chamber-light")
open(hp, "w").write(helper_src.replace("G=/sys/class/gpio", "G=%s" % gpio).replace("STATE_DIR=/var/lib/wm-chamber-light", "STATE_DIR=%s" % os.path.join(tmp, "var")))
os.chmod(hp, 0o755)


def run(arg):
    return subprocess.run([hp, arg], capture_output=True, text=True).stdout.strip()


check("status starts off", run("status") == "off")
check("on writes 1 to gpio76 and sets direction out", run("on") == "on" and open(os.path.join(gpio, "gpio76", "value")).read().strip() == "1" and open(os.path.join(gpio, "gpio76", "direction")).read().strip() == "out")
check("toggle turns it off", run("toggle") == "off" and open(os.path.join(gpio, "gpio76", "value")).read().strip() == "0")
run("on")
open(os.path.join(gpio, "gpio76", "value"), "w").write("0\n")   # a reboot clears the pin
check("restore puts it back to the saved state (on)", run("restore") == "on" and open(os.path.join(gpio, "gpio76", "value")).read().strip() == "1")
check("an unknown argument is refused", subprocess.run([hp, "bogus"], capture_output=True).returncode == 2)

print("print screen patch")
fake_js = """import logging
import os
from gi.repository import GLib, Gtk


class Panel:
    def create_buttons(self):
        self.buttons = {}
        self.buttons["control"].connect("clicked", self._screen._go_to_submenu, "")

    def save_offset(self, widget, device):
        pass

    def show_buttons_for_state(self):
        if self.state == "printing":
            self.buttons["button_grid"].attach(self.buttons["control"], 3, 0, 1, 1)
        elif self.state == "paused":
            self.buttons["button_grid"].attach(self.buttons["control"], 3, 0, 1, 1)
"""
js = os.path.join(tmp, "job_status.py")
open(js, "w").write(fake_js)
pp = os.path.join(ROOT, "zr_tools", "patch_job_status_light.py")
check("patch runs", subprocess.run([sys.executable, pp, js]).returncode == 0)
once = open(js).read()
check("patch result compiles", subprocess.run([sys.executable, "-m", "py_compile", js]).returncode == 0)
check("Light button on both printing and paused", once.count('self.buttons["wm_light"], 4, 0, 1, 1') == 2)
check("button is always on the print screen (not hidden when the helper is missing)", once.count('os.path.exists("/usr/local/sbin/wm-chamber-light")') == 0)
check("the button switches Moonraker's power device chamber_light, no sudo helper call", '"machine.device_power.post_device", {"device": "chamber_light", "action": "toggle"}' in once and "sudo" not in once and "subprocess" not in once)
# a file patched by the older version (the button ran the root helper through sudo) is brought up to date
old_method = """
    def wm_chamber_light(self, widget):
        import subprocess
        subprocess.run(["sudo", "-n", "/usr/local/sbin/wm-chamber-light", "toggle"])
"""
i1 = once.index("\n    def wm_chamber_light(self, widget):"); i2 = once.index("\n    def ", i1 + 5)
open(js, "w").write(once[:i1] + old_method.rstrip("\n") + "\n" + once[i2:])
check("an older patched print screen is upgraded", subprocess.run([sys.executable, pp, js]).returncode == 0 and open(js).read() == once)
# the main menu button
fake_menu = """class Panel:
    def arrangeMenuItems(self, items):
        return 1

    def create_menu_items(self):
        for item in self.items:
            if item["method"] == "x":
                pass
            elif item["method"] == "ks_confirm_save":
                pass
"""
mp = os.path.join(ROOT, "zr_tools", "patch_menu_light.py")
mf = os.path.join(tmp, "menu.py")
open(mf, "w").write(fake_menu)
check("menu patch runs and compiles", subprocess.run([sys.executable, mp, mf]).returncode == 0 and subprocess.run([sys.executable, "-m", "py_compile", mf]).returncode == 0)
m1 = open(mf).read()
check("menu button switches Moonraker's power device chamber_light, no sudo helper call", "machine.device_power.post_device" in m1 and 'item["method"] == "wm_chamber_light"' in m1 and "sudo" not in m1)
j1 = m1.index("\n    def wm_chamber_light(self, widget):"); j2 = m1.index("\n    def ", j1 + 5)
open(mf, "w").write(m1[:j1] + old_method.rstrip("\n") + "\n" + m1[j2:])
check("an older patched menu is upgraded, and a second run changes nothing", subprocess.run([sys.executable, mp, mf]).returncode == 0 and open(mf).read() == m1 and subprocess.run([sys.executable, mp, mf]).returncode == 0 and open(mf).read() == m1)
# moonraker.conf: the power device (scripts/wm_light_conf.py)
lc = os.path.join(ROOT, "scripts", "wm_light_conf.py")
jf = os.path.join(tmp, "rpi_chamber_light.json"); open(jf, "w").write('{"url": "http://10.0.0.9:8765"}')
check("light conf: reads the board address", subprocess.run([sys.executable, lc, "url", jf], capture_output=True, text=True).stdout.strip() == "http://10.0.0.9:8765")
open(jf, "w").write('{"url": "http://x/;rm -rf"}')
check("light conf: an address that is not an address is ignored", subprocess.run([sys.executable, lc, "url", jf], capture_output=True, text=True).stdout.strip() == "")
open(jf, "w").write('{"url": "http://127.0.0.1:8765"}')
check("light conf: the factory placeholder (the Pi itself) is not a screen board", subprocess.run([sys.executable, lc, "url", jf], capture_output=True, text=True).stdout.strip() == "")
mc = os.path.join(tmp, "moonraker.conf"); open(mc, "w").write("[server]\nhost: 0.0.0.0\n")
check("light conf: missing section is reported (10) and nothing is written without --write", subprocess.run([sys.executable, lc, "conf", mc, "http://10.0.0.9:8765"]).returncode == 10 and "power" not in open(mc).read())
subprocess.run([sys.executable, lc, "conf", mc, "http://10.0.0.9:8765", "--write"])
t1 = open(mc).read()
check("light conf: section written with the three addresses and the poll", t1.count("http://10.0.0.9:8765/light") == 3 and "[power chamber_light]" in t1 and "poll_interval: 3" in t1 and t1.startswith("[server]\nhost: 0.0.0.0\n"))
check("light conf: second run changes nothing (0)", subprocess.run([sys.executable, lc, "conf", mc, "http://10.0.0.9:8765", "--write"]).returncode == 0 and open(mc).read() == t1)
open(mc, "w").write(t1 + "\n[other]\nx: 1\n")
check("light conf: a new board address is corrected, the rest of the file stays", subprocess.run([sys.executable, lc, "conf", mc, "http://10.0.0.20:8765", "--write"]).returncode == 10 and open(mc).read().count("http://10.0.0.20:8765/light") == 3 and "10.0.0.9" not in open(mc).read() and open(mc).read().endswith("[other]\nx: 1\n"))
open(mc, "w").write("[power chamber_light]\ntype: gpio\npin: gpiochip0/gpio17\n")
check("light conf: a section of your own is left alone (12)", subprocess.run([sys.executable, lc, "conf", mc, "http://10.0.0.9:8765", "--write"]).returncode == 12 and "gpio17" in open(mc).read() and "http" not in open(mc).read())
subprocess.run([sys.executable, pp, js])
check("running the patch twice changes nothing", open(js).read() == once)
other = os.path.join(tmp, "other.py")
open(other, "w").write("print(1)\n")
check("a file it does not know is refused", subprocess.run([sys.executable, pp, other], capture_output=True).returncode == 1)

print("passed: %d   failed: %d" % (passed, failed))
sys.exit(1 if failed else 0)
