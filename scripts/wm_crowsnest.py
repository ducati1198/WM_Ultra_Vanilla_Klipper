#!/usr/bin/env python3
"""Webcam setup for the Crowsnest service (stdlib only, so the installer can call it on a fresh Pi).

  wm_crowsnest.py detect [--json]                      list the cameras that are plugged in (USB by-id paths, CSI libcamera paths)
  wm_crowsnest.py modes --model "<Pi model text>"      which streamer is used for a USB and for a CSI camera on this Pi
  wm_crowsnest.py conf  --model M --count N --resolution 480p|720p|1080p|WxH --fps F [--out FILE] [--keep]
                                                       the full crowsnest.conf (every option explained at the top). Without --out it prints.
                                                       --keep: an existing FILE is never touched, the new text goes to FILE.new
  wm_crowsnest.py moonraker FILE --count N [--write]   add [webcam Camera], [webcam Camera 2] ... to moonraker.conf so Fluidd lists the cameras
  wm_crowsnest.py resolution TEXT                      check a resolution and print it as WIDTHxHEIGHT
  wm_crowsnest.py count TEXT | fps TEXT                check the number of cameras (1-4) or max_fps (1-60) and print it
  wm_crowsnest.py cams FILE                            how many [cam ...] sections a crowsnest.conf has

Test hooks: WM_TEST_CAMERAS (a JSON list) replaces the hardware scan, WM_V4L_BYID_DIR replaces /dev/v4l/by-id.
Exit codes: 0 ok / nothing to change, 10 a change is needed (moonraker without --write) or was written, 2 usage or bad value.
"""
import json
import os
import re
import shutil
import subprocess
import sys

README = "https://github.com/mainsail-crew/crowsnest/blob/master/README.md"
MAX_CAMS = 4                     # nginx (config/nginx_fluidd.conf) has /webcam/ to /webcam4/, crowsnest ports 8080 to 8083
BASE_PORT = 8080
RESOLUTIONS = {"480p": (640, 480), "720p": (1280, 720), "1080p": (1920, 1080)}
DEFAULT_RES, DEFAULT_FPS = "720p", 15


# ----------------------------------------------------------------------------------------------------------------------
# values
# ----------------------------------------------------------------------------------------------------------------------
def parse_resolution(text):
    """'720p' or '1280x720' -> (1280, 720). ValueError for anything else (and for sizes no camera does)."""
    t = (text or "").strip().lower().replace(" ", "")
    t = {"1": "480p", "2": "720p", "3": "1080p"}.get(t, t)      # the menu numbers
    if t in RESOLUTIONS:
        return RESOLUTIONS[t]
    m = re.fullmatch(r"(\d{3,4})[x*](\d{3,4})", t)
    if not m:
        raise ValueError("resolution must be 480p, 720p, 1080p or WIDTHxHEIGHT like 1280x720")
    w, h = int(m.group(1)), int(m.group(2))
    if not (160 <= w <= 4096 and 120 <= h <= 4096):
        raise ValueError("resolution must be between 160x120 and 4096x4096")
    return w, h


def parse_fps(text):
    try:
        f = int(str(text).strip())
    except ValueError:
        raise ValueError("max_fps must be a whole number from 1 to 60")
    if not 1 <= f <= 60:
        raise ValueError("max_fps must be a whole number from 1 to 60")
    return f


def parse_count(text, limit=MAX_CAMS):
    try:
        n = int(str(text).strip())
    except ValueError:
        raise ValueError("the number of cameras must be a whole number from 1 to %d" % limit)
    if not 1 <= n <= limit:
        raise ValueError("the number of cameras must be a whole number from 1 to %d" % limit)
    return n


# ----------------------------------------------------------------------------------------------------------------------
# which streamer
# ----------------------------------------------------------------------------------------------------------------------
def pi_kind(model):
    """'pi5', 'pi4' (Pi 4 and Compute Module 4) or 'other' from the text of /proc/device-tree/model"""
    m = (model or "").lower()
    if "raspberry pi 5" in m or "compute module 5" in m:
        return "pi5"
    if "raspberry pi 4" in m or "compute module 4" in m:
        return "pi4"
    return "other"


def mode_for(model, kind):
    """The streamer for a camera of kind 'usb' or 'csi'.
    Pi 4 / CM4: camera-streamer. Every other Pi (Pi 5, Pi 3, Zero 2): ustreamer.
    A CSI ribbon camera needs libcamera, which ustreamer cannot use, so a CSI camera gets camera-streamer
    (not available on a Pi 5) or spyglass (Pi 5)."""
    p = pi_kind(model)
    if kind == "csi":
        return "spyglass" if p == "pi5" else "camera-streamer"
    return "camera-streamer" if p == "pi4" else "ustreamer"


# ----------------------------------------------------------------------------------------------------------------------
# cameras
# ----------------------------------------------------------------------------------------------------------------------
def detect():
    """[{'kind': 'usb'|'csi', 'path': ..., 'name': ...}] in a stable order (USB by name, then CSI)."""
    fake = os.environ.get("WM_TEST_CAMERAS")
    if fake is not None:
        try:
            return [c for c in json.loads(fake) if c.get("kind") in ("usb", "csi") and c.get("path")]
        except ValueError:
            return []
    cams = []
    byid = os.environ.get("WM_V4L_BYID_DIR", "/dev/v4l/by-id")
    try:
        names = sorted(os.listdir(byid))
    except OSError:
        names = []
    for n in names:
        if n.endswith("-video-index0"):             # index0 is the picture, index1 is metadata
            cams.append({"kind": "usb", "path": os.path.join(byid, n), "name": n[:-len("-video-index0")].replace("usb-", "", 1)})
    for cmd in ("rpicam-hello", "libcamera-hello"):
        exe = shutil.which(cmd)
        if not exe:
            continue
        try:
            out = subprocess.run([exe, "--list-cameras"], capture_output=True, text=True, timeout=15).stdout
        except (OSError, subprocess.SubprocessError):
            out = ""
        for m in re.finditer(r"^\s*\d+\s*:\s*(\S+).*?\((/base[^)]*)\)", out, re.M):
            cams.append({"kind": "csi", "path": m.group(2), "name": m.group(1)})
        break
    return cams


# ----------------------------------------------------------------------------------------------------------------------
# crowsnest.conf
# ----------------------------------------------------------------------------------------------------------------------
HEADER = """#### crowsnest.conf  -  webcam streaming (Crowsnest)
####
#### Written by the WM_Ultra_Vanilla_Klipper installer. Edit it freely: the installer never overwrites it once it exists
#### (a newer explained copy is saved next to it as crowsnest.conf.new). To start over: ./installer.sh --webcam-setup
####
#### Full manual of every option: %(readme)s
####
#### After a change:  sudo systemctl restart crowsnest        Log:  ~/printer_data/logs/crowsnest.log
####
#####################################################################################################
####  OPTIONS OF THE [crowsnest] SECTION (one section for the whole service)
#####################################################################################################
####  log_level           quiet | verbose | debug
####                      How much crowsnest writes to its log. verbose is a good everyday value, debug is for finding problems.
####  rollover_on_start   true | false        (default false)
####                      true: at every start the old log is kept as a backup and a fresh log is started.
####  no_proxy            true | false        (default false)
####                      false: the streams listen on 127.0.0.1 only and nginx (the Fluidd web page) hands them out under /webcam/.
####                      true: the streams listen on 0.0.0.0 and can be opened directly as http://<ip>:<port>/?action=stream.
####                      Only change this if you know why. It can also be set inside one [cam ...] section.
####
#####################################################################################################
####  OPTIONS OF A [cam NAME] SECTION (one section per camera, NAME is any text and shows up in the log)
#####################################################################################################
####  mode                ustreamer | camera-streamer | spyglass
####                      ustreamer        MJPEG streamer for USB cameras. The choice for a Pi 5 and for older Pis (Pi 3, Zero 2).
####                      camera-streamer  uses the Pi's hardware where it can: USB cameras and the CSI ribbon camera. The choice
####                                       for a Pi 4 / Compute Module 4. Not available on a Pi 5.
####                      spyglass         for the CSI ribbon camera on a Pi 5 (libcamera).
####  port                8080 to 8083        HTTP port of this camera's stream, one port per camera. With the nginx proxy:
####                        8080 = /webcam/   8081 = /webcam2/   8082 = /webcam3/   8083 = /webcam4/    (add  ?action=stream  or  ?action=snapshot)
####  device              Which camera. USB: the stable name under /dev/v4l/by-id/ that ends in -video-index0 (it does not change when
####                      you plug the camera into another port). CSI ribbon camera: the libcamera path that starts with /base/
####                      (rpicam-hello --list-cameras). To list what is plugged in:  python3 ~/wm_ultra_vanilla_klipper/scripts/wm_crowsnest.py detect
####  resolution          WIDTHxHEIGHT, for example 640x480 (480p), 1280x720 (720p), 1920x1080 (1080p). A bigger picture needs more
####                      CPU and network speed. The camera must support it, otherwise it is ignored or the closest size is used.
####  max_fps             Pictures per second (1 to 60). Used if the camera can do it, otherwise it is ignored or lowered. Fewer is lighter.
####  no_proxy            true | false, same meaning as in [crowsnest] but for this one camera.
####  custom_flags        Extra command-line flags for the streamer program, for example   --quality=80   (see the manual for the
####                      flags of ustreamer / camera-streamer / spyglass). Leave it out unless you need it.
####  v4l2ctl             Camera controls to set at start, separated by commas, for example   focus_auto=0, focus_absolute=30
####                      The controls your camera offers are listed in the log.
####
#####################################################################################################
####  FLUIDD: the cameras are listed in Fluidd as  Camera, Camera 2, Camera 3  through the [webcam ...] sections in
####  ~/printer_data/config/moonraker.conf (the installer adds them). Rename or remove them there if you like.
#####################################################################################################
""" % {"readme": README}


def conf_text(model, cams, resolution, fps):
    """The whole crowsnest.conf. cams: list of {'kind','path','name'} (may be shorter than the number wanted: see conf_for)."""
    w, h = parse_resolution(resolution)
    parts = [HEADER, "\n[crowsnest]\nlog_level: verbose\nrollover_on_start: false\nno_proxy: false\n"]
    for i, c in enumerate(cams, start=1):
        kind = c.get("kind", "usb")
        parts.append("\n[cam %d]\n" % i)
        if c.get("placeholder"):
            parts.append("# No camera was found for this one when the file was written. Plug it in, then set the device (see the notes at the top).\n")
        elif c.get("name"):
            parts.append("# %s\n" % c["name"])
        parts.append("mode: %s\nport: %d\ndevice: %s\nresolution: %dx%d\nmax_fps: %d\n#custom_flags:\n#v4l2ctl:\n"
                     % (mode_for(model, kind), BASE_PORT + i - 1, c["path"], w, h, fps))
    return "".join(parts)


def conf_for(model, found, count, resolution, fps):
    """Fill up to `count` cameras: the ones found first, then placeholders (/dev/video0, /dev/video2 ...) for those not plugged in."""
    cams = [dict(c) for c in found[:count]]
    n = 0
    while len(cams) < count:
        cams.append({"kind": "usb", "path": "/dev/video%d" % n, "name": "", "placeholder": True})
        n += 2
    return conf_text(model, cams, resolution, fps)


# ----------------------------------------------------------------------------------------------------------------------
# moonraker.conf: the cameras Fluidd lists
# ----------------------------------------------------------------------------------------------------------------------
def webcam_sections(count):
    out = []
    for i in range(1, count + 1):
        name = "Camera" if i == 1 else "Camera %d" % i
        prefix = "/webcam/" if i == 1 else "/webcam%d/" % i
        out.append((name, prefix, "[webcam %s]\nlocation: printer\nservice: mjpegstreamer\nstream_url: %s?action=stream\nsnapshot_url: %s?action=snapshot\n"
                    % (name, prefix, prefix)))
    return out


def moonraker_text(text, count):
    """Adds the missing [webcam ...] sections. A section with the same name, or one that already streams from the same /webcam/
    address, is left alone. Returns (new_text, [names added])."""
    have_names = {m.group(1).strip().lower() for m in re.finditer(r"^\[webcam\s+([^\]]+)\]", text, re.M | re.I)}
    added, add = [], ""
    for name, prefix, block in webcam_sections(count):
        if name.lower() in have_names:
            continue
        if re.search(r"^stream_url\s*[:=]\s*%s\?action=stream" % re.escape(prefix), text, re.M):
            continue
        add += "\n" + block
        added.append(name)
    if not added:
        return text, []
    if text and not text.endswith("\n"):
        text += "\n"
    return text + add, added


# ----------------------------------------------------------------------------------------------------------------------
def die(msg):
    sys.stderr.write("wm_crowsnest: %s\n" % msg)
    sys.exit(2)


def arg(argv, name, default=None):
    if name in argv:
        i = argv.index(name)
        if i + 1 >= len(argv):
            die("%s needs a value" % name)
        return argv[i + 1]
    return default


def main(argv):
    if len(argv) < 2 or argv[1] in ("-h", "--help"):
        print(__doc__)
        return 0 if len(argv) >= 2 else 2
    cmd = argv[1]
    try:
        if cmd == "detect":
            cams = detect()
            if "--count" in argv:
                print(len(cams))
            elif "--json" in argv:
                print(json.dumps(cams))
            elif not cams:
                print("no camera found")
            else:
                for i, c in enumerate(cams, 1):
                    print("%d  %s  %s  (%s)" % (i, c["kind"].upper(), c["path"], c.get("name") or "-"))
            return 0
        if cmd == "modes":
            m = arg(argv, "--model", "")
            print("usb: %s\ncsi: %s" % (mode_for(m, "usb"), mode_for(m, "csi")))
            return 0
        if cmd == "resolution":
            w, h = parse_resolution(argv[2] if len(argv) > 2 else "")
            print("%dx%d" % (w, h))
            return 0
        if cmd == "count":
            print(parse_count(argv[2] if len(argv) > 2 else ""))
            return 0
        if cmd == "fps":
            print(parse_fps(argv[2] if len(argv) > 2 else ""))
            return 0
        if cmd == "cams":
            try:
                with open(argv[2]) as f:
                    print(min(MAX_CAMS, len(re.findall(r"^\[cam\s+[^\]]+\]", f.read(), re.M))))
            except (OSError, IndexError):
                print(0)
            return 0
        if cmd == "conf":
            model = arg(argv, "--model", "")
            count = parse_count(arg(argv, "--count", "1"))
            text = conf_for(model, detect(), count, arg(argv, "--resolution", DEFAULT_RES), parse_fps(arg(argv, "--fps", DEFAULT_FPS)))
            out = arg(argv, "--out")
            if not out:
                sys.stdout.write(text)
                return 0
            if "--keep" in argv and os.path.exists(out):
                out += ".new"
            with open(out, "w") as f:
                f.write(text)
            print(out)
            return 10
        if cmd == "moonraker":
            if len(argv) < 3:
                die("moonraker needs the moonraker.conf path")
            path = argv[2]
            count = parse_count(arg(argv, "--count", "1"))
            try:
                with open(path) as f:
                    text = f.read()
            except OSError as e:
                die("cannot read %s: %s" % (path, e))
            new, added = moonraker_text(text, count)
            if not added:
                print("nothing to change")
                return 0
            if "--write" in argv:
                with open(path, "w") as f:
                    f.write(new)
                print("added: " + ", ".join(added))
            else:
                print("would add: " + ", ".join(added))
            return 10
    except ValueError as e:
        die(str(e))
    die("unknown command %s" % cmd)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
