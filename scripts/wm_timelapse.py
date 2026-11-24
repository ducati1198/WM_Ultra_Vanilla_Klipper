#!/usr/bin/env python3
# wm_timelapse.py: change the moonraker-timelapse settings for the WM_TIMELAPSE window.
# Runs in the background so the Klipper macro that started it can finish first.
import sys, os, json, time, subprocess, urllib.request, urllib.parse
B = "http://127.0.0.1:7125"
CRF = {"fast": 26, "better": 20, "best": 17}

def call(method, path, params=None):
    url = B + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, data=(b"" if method == "POST" else None), method=method)
    with urllib.request.urlopen(req, timeout=8) as r:
        return json.loads(r.read().decode())

def gcode(s):
    call("POST", "/printer/gcode/script", {"script": s})

def show(msg=None):
    s = call("GET", "/machine/timelapse/settings")["result"]
    g = "_WM_TL_MAIN EN=%d MODE=%s CRF=%s PARK=%d FPS=%s CYC=%s" % (
        1 if s.get("enabled") else 0, s.get("mode", "layermacro"),
        s.get("constant_rate_factor", 23), 1 if s.get("parkhead") else 0,
        s.get("output_framerate", 30), s.get("hyperlapse_cycle", 30))
    if msg:
        g = "M118 " + msg + "\n" + g
    gcode(g)

def work(a):
    time.sleep(0.8)
    try:
        if not a or a[0] == "show":
            show()
        elif a[0] == "set" and len(a) >= 3:
            k, v = a[1], a[2]
            if k == "quality" and v in CRF:
                call("POST", "/machine/timelapse/settings", {"constant_rate_factor": CRF[v]})
                msg = "Timelapse video quality set to " + v + " (CRF " + str(CRF[v]) + "). It applies to the next video."
            elif k == "mode" and v in ("layer", "time"):
                call("POST", "/machine/timelapse/settings", {"mode": "layermacro" if v == "layer" else "hyperlapse"})
                msg = "Timelapse mode set to " + ("every layer" if v == "layer" else "by time") + ". It applies to the next print."
            elif k == "park" and v in ("on", "off"):
                call("POST", "/machine/timelapse/settings", {"parkhead": "true" if v == "on" else "false"})
                msg = "Timelapse head parking " + v + ". It applies to the next print."
            else:
                raise ValueError("unknown setting " + k + " " + v)
            show(msg)
    except Exception as e:
        try:
            gcode("M118 Timelapse settings failed: " + str(e)[:90])
        except Exception:
            pass

def main():
    a = sys.argv[1:]
    if a and a[0] == "--bg":
        work(a[1:])
        return
    subprocess.Popen([sys.executable, os.path.abspath(__file__), "--bg"] + a, start_new_session=True,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

main()
