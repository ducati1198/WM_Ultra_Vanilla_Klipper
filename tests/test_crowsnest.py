#!/usr/bin/env python3
"""scripts/wm_crowsnest.py: streamer choice, resolutions, camera detection, crowsnest.conf text, Moonraker webcam sections."""
import json, os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import wm_crowsnest as C

def raises(fn, *a):
    try: fn(*a)
    except ValueError: return True
    return False

# streamer per model
P4, P5, P3, Z2 = "Raspberry Pi 4 Model B Rev 1.4", "Raspberry Pi 5 Model B Rev 1.0", "Raspberry Pi 3 Model B Plus Rev 1.3", "Raspberry Pi Zero 2 W Rev 1.0"
assert C.mode_for(P4, "usb") == "camera-streamer" and C.mode_for("Raspberry Pi Compute Module 4 Rev 1.0", "usb") == "camera-streamer"
for m in (P5, P3, Z2, ""): assert C.mode_for(m, "usb") == "ustreamer", m
assert C.mode_for(P5, "csi") == "spyglass" and C.mode_for(P4, "csi") == "camera-streamer" and C.mode_for(P3, "csi") == "camera-streamer"

# values
assert C.parse_resolution("480p") == (640, 480) and C.parse_resolution("720p") == (1280, 720) and C.parse_resolution("1080P") == (1920, 1080)
assert C.parse_resolution("2") == (1280, 720) and C.parse_resolution("800x600") == (800, 600) and C.parse_resolution("800 x 600") == (800, 600)
assert all(raises(C.parse_resolution, x) for x in ("", "abc", "10x10", "99999x99999", "720"))
assert C.parse_fps("15") == 15 and all(raises(C.parse_fps, x) for x in ("0", "61", "x", ""))
assert C.parse_count("4") == 4 and all(raises(C.parse_count, x) for x in ("0", "5", "two"))

# detection: USB by-id (index0 only), test hook
d = tempfile.mkdtemp()
for n in ("usb-Logi_C920-video-index0", "usb-Logi_C920-video-index1", "usb-Other_Cam-video-index0"): open(os.path.join(d, n), "w").close()
os.environ["WM_V4L_BYID_DIR"] = d
cams = [c for c in C.detect() if c["kind"] == "usb"]
assert [os.path.basename(c["path"]) for c in cams] == ["usb-Logi_C920-video-index0", "usb-Other_Cam-video-index0"], cams
os.environ["WM_TEST_CAMERAS"] = json.dumps([{"kind": "csi", "path": "/base/soc/i2c0mux/i2c@1/imx708@1a", "name": "imx708"}])
assert C.detect()[0]["kind"] == "csi"
os.environ["WM_TEST_CAMERAS"] = "not json"; assert C.detect() == []

# conf text
found = [{"kind": "usb", "path": "/dev/v4l/by-id/usb-A-video-index0", "name": "A"}]
t = C.conf_for(P4, found, 3, "1080p", 25)
assert C.README in t
for opt in ("log_level", "rollover_on_start", "no_proxy", "mode", "port", "device", "resolution", "max_fps", "custom_flags", "v4l2ctl"):
    assert "####  " + opt in t, opt
assert t.count("\n[cam ") == 3 and "[cam 1]" in t and "[cam 3]" in t and "[cam 4]" not in t
assert "port: 8080" in t and "port: 8081" in t and "port: 8082" in t
assert "resolution: 1920x1080" in t and "max_fps: 25" in t and "device: /dev/v4l/by-id/usb-A-video-index0" in t
assert "No camera was found for this one" in t and "device: /dev/video0" in t
# the v4 leftovers are not written
for old in ("log_path", "delete_log", "enable_rtsp", "rtsp_port"): assert old not in t, old
assert "mode: ustreamer" in C.conf_for(P5, found, 1, "720p", 15)

# moonraker sections
base = "[server]\nhost: 0.0.0.0\n"
new, added = C.moonraker_text(base, 3)
assert added == ["Camera", "Camera 2", "Camera 3"]
for s in ("[webcam Camera]", "[webcam Camera 2]", "[webcam Camera 3]", "stream_url: /webcam2/?action=stream", "snapshot_url: /webcam3/?action=snapshot"): assert s in new, s
assert C.moonraker_text(new, 3) == (new, [])                       # twice changes nothing
mine = base + "\n[webcam printer cam]\nservice: mjpegstreamer\nstream_url: /webcam/?action=stream\nsnapshot_url: /webcam/?action=snapshot\n"
new2, added2 = C.moonraker_text(mine, 2)
assert added2 == ["Camera 2"] and "[webcam printer cam]" in new2 and "[webcam Camera]" not in new2   # the user's own section for /webcam/ is kept, no duplicate
assert C.moonraker_text("", 1)[0].startswith("\n[webcam Camera]")

# the camera on the screen board: Camera = the board, this Pi's cameras start at [cam 2] (port 8081)
assert C.parse_count("0", 3, 0) == 0 and C.parse_count("3", 3, 0) == 3 and raises(C.parse_count, "4", 3, 0) and raises(C.parse_count, "0")
t2 = C.conf_for(P3, found, 2, "720p", 30, 2)
assert "[cam 2]" in t2 and "[cam 3]" in t2 and "[cam 1]" not in t2 and "port: 8081" in t2 and "port: 8082" in t2 and "port: 8080\n" not in t2.split("\n[crowsnest]\n")[1]
assert "[cam " not in C.conf_for(P3, found, 0, "720p", 30, 2).split("\n[crowsnest]\n")[1]
sd = tempfile.mkdtemp(); sj = os.path.join(sd, "rpi_screen_camera.json")
assert C.screen_cam_url(sj) == ""                                          # no file
open(sj, "w").write('{"url": "http://board-1.local:8080"}'); assert C.screen_cam_url(sj) == "http://board-1.local:8080"
open(sj, "w").write('{"url": ""}'); assert C.screen_cam_url(sj) == ""      # no camera plugged in
open(sj, "w").write('{"url": "javascript:alert(1)"}'); assert C.screen_cam_url(sj) == ""
open(sj, "w").write("not json"); assert C.screen_cam_url(sj) == ""
ups = "upstream apiserver {\n    server 127.0.0.1:7125;\n}\nupstream mjpgstreamer1 { server 127.0.0.1:8080; }\nupstream mjpgstreamer2 { server 127.0.0.1:8081; }\n"
u1, ch = C.upstream_text(ups, "http://board-1.local:8080")
assert ch and "upstream mjpgstreamer1 { server board-1.local:8080; }" in u1 and "mjpgstreamer2 { server 127.0.0.1:8081; }" in u1 and "127.0.0.1:7125" in u1
assert C.upstream_text(u1, "http://board-1.local:8080") == (u1, False)      # twice changes nothing
assert C.upstream_text(u1, "default") == (ups, True)                        # and back
print("crowsnest helper tests passed")
