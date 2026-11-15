#!/usr/bin/env python3
"""The chamber light as a Moonraker power device, so the Fluidd Toolheads card, the touchscreen buttons and the macro
WM_CHAMBER_LIGHT all switch the same thing and always show the same state.

The light hangs on the screen board. Its service wm-chamber-light-http (port 8765) tells the Pi where it is by uploading
rpi_chamber_light.json ({"url": "http://<board>:8765"}) into Moonraker's config folder. This script writes the section
[power chamber_light] for that address into moonraker.conf, or corrects the address when the board got a new one.

  wm_light_conf.py url  JSON_FILE                  prints the address in rpi_chamber_light.json (nothing when missing, not an address,
                                                   or the placeholder 127.0.0.1 the factory files ship)
  wm_light_conf.py conf MOONRAKER_CONF URL [--write]

A [power chamber_light] section that this script did not write (no marker line) is never touched.
Exit code: 0 nothing to change, 10 a change is needed / was written, 12 a section of your own is there (left alone), 2 usage."""
import json, re, sys

MARK = "# wm-chamber-light: written by the installer (scripts/wm_light_conf.py). The light is on the screen board, its service answers {\"on\": true|false}"
URL_RE = re.compile(r"^https?://[\w.-]+(?::\d+)?$")


def block(url):
    return "\n".join([
        "[power chamber_light]",
        MARK,
        "type: http",
        "on_url: %s/light" % url,
        "off_url: %s/light" % url,
        "status_url: %s/light" % url,
        "request_template:",
        '  {% if command == "on" %}',
        '    {% do http_request.set_method("POST") %}',
        '    {% do http_request.set_body({"on": true}) %}',
        '  {% elif command == "off" %}',
        '    {% do http_request.set_method("POST") %}',
        '    {% do http_request.set_body({"on": false}) %}',
        "  {% endif %}",
        "  {% do http_request.send() %}",
        "response_template:",
        "  {% set resp = http_request.last_response().json() %}",
        '  {"on" if resp["on"] else "off"}',
        "poll_interval: 3",
    ])


def fix(text, url):
    """-> (new text, code)"""
    lines = text.split("\n")
    start = next((i for i, l in enumerate(lines) if re.match(r"^\[power\s+chamber_light\]\s*$", l)), None)
    want = block(url).split("\n")
    if start is None:
        body = text.rstrip("\n")
        return (body + "\n\n" if body else "") + "\n".join(want) + "\n", 10
    end = next((i for i in range(start + 1, len(lines)) if re.match(r"^\[[^\]]+\]\s*$", lines[i])), len(lines))
    cur = lines[start:end]
    while cur and not cur[-1].strip():
        cur.pop()
    ours = any(l.startswith("# wm-chamber-light:") or l.startswith("# The chamber light is on the screen board") for l in cur)
    if not ours:
        return text, 12
    if cur == want:
        return text, 0
    tail = lines[end:]
    return "\n".join(lines[:start] + want + ([""] if tail else []) + tail) + ("" if text.endswith("\n") and tail else "\n" if not tail else ""), 10


def main():
    a = sys.argv[1:]
    if len(a) >= 2 and a[0] == "url":
        try:
            u = str(json.load(open(a[1])).get("url", ""))
        except (OSError, ValueError, AttributeError):
            u = ""
        # the factory files ship this file with the address of the Pi itself (a placeholder): that is not a screen board
        host = re.sub(r"^https?://", "", u).split(":")[0]
        if URL_RE.match(u) and host != "localhost" and not host.startswith("127."):
            print(u)
        return 0
    if len(a) >= 3 and a[0] == "conf" and URL_RE.match(a[2]):
        text = open(a[1]).read()
        new, code = fix(text, a[2])
        if code == 10 and "--write" in a:
            open(a[1], "w").write(new)
        return code
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
