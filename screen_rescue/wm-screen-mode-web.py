#!/usr/bin/python3
# The page you get at http://BOARD-IP:8099 while the factory software runs: one button, back to KlipperScreen.
# Started by wm-screen-mode (wm-screen-mode-web.service). Only the standard library; runs as root.
import json, subprocess, sys, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = 8099
MODE = "/usr/local/sbin/wm-screen-mode"

PAGE = """<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>WonderMaker screen board</title>
<style>body{font-family:system-ui,sans-serif;background:#f5f6f8;color:#1e2228;margin:0;padding:24px 16px;text-align:center}
h1{font-size:28px;margin:30px 0 10px}p{font-size:18px;color:#505660;margin:8px auto;max-width:560px}
button{font-size:26px;font-weight:700;color:#fff;background:#2ea05a;border:0;border-radius:16px;padding:22px 40px;margin:28px 0;cursor:pointer}
button[disabled]{background:#9aa0a8;cursor:not-allowed}.note{font-size:16px;color:#6a707a}.steps{max-width:560px;margin:24px auto;text-align:left;background:#fff;border-radius:12px;padding:12px 20px;font-size:17px;color:#3a4048}</style></head><body>
<h1>%(title)s</h1><p>%(text)s</p>%(form)s
<div class="steps"><b>How to use a USB stick instead</b><ol><li>Take a USB stick (FAT32, as most are).</li>
<li>Make an empty file named <b>WM-KLIPPERSCREEN</b> in its main folder (no .txt at the end).</li>
<li>Plug the stick into the screen board and restart the board.</li>
<li>KlipperScreen comes back by itself after about a minute. The stick is only read while the board starts.</li></ol></div>
<p class="note">%(note)s</p></body></html>"""


def local_print_state():
    try:
        with urllib.request.urlopen("http://127.0.0.1:7125/printer/objects/query?print_stats=state", timeout=2) as r:
            return json.load(r)["result"]["status"]["print_stats"]["state"]
    except Exception:
        return "unknown"


def active(unit):
    return subprocess.run(["systemctl", "is-active", "--quiet", unit]).returncode == 0


def actual_mode():
    # a plain systemd check: fast even while the factory software is still starting and the board is busy
    if active("KlipperScreen"):
        return "klipperscreen"
    return "factory" if active("makerbase-client") else "none"


def page(msg=None):
    mode, st = actual_mode(), local_print_state()
    note = "This page is on the screen board itself (its own address, not the Pi's)."
    if msg:
        return PAGE % dict(title="Switching", text=msg, form="", note="You can close this page.")
    if mode == "klipperscreen":
        return PAGE % dict(title="KlipperScreen is running", text="This board already shows KlipperScreen.", form="", note=note)
    if st in ("printing", "paused"):
        return PAGE % dict(title="A print is running", text="The factory software is printing (%s). Switching is not possible during a print." % st,
                           form='<button disabled>Back to KlipperScreen</button>', note=note)
    return PAGE % dict(title="Screen board is in factory mode", text="The factory software is running. KlipperScreen is off. No print is running, so it is safe to switch.",
                       form='<form method="post" action="/back"><button type="submit">Back to KlipperScreen</button></form>', note=note)


class H(BaseHTTPRequestHandler):
    def _send(self, body, code=200, ctype="text/html; charset=utf-8"):
        data = body.encode("utf-8"); self.send_response(code)
        self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)

    def do_GET(self):
        if self.path.startswith("/status"):
            self._send(json.dumps({"mode": actual_mode(), "print": local_print_state()}), ctype="application/json")
        else:
            self._send(page())

    def do_POST(self):
        if self.path != "/back":
            return self._send("not found", 404, "text/plain")
        if local_print_state() in ("printing", "paused"):
            return self._send(page())
        subprocess.Popen([MODE, "klipperscreen"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self._send(page("KlipperScreen is starting. The screen shows it again in about 20 seconds."))

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", PORT), H).serve_forever()
