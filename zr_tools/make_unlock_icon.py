#!/usr/bin/env python3
"""Add an "unlock" icon to every KlipperScreen theme that has a "lock" icon (the ZR Tools "Unlock gripper" button asks for the icon "unlock",
and KlipperScreen ships only lock.svg, in any of its themes). The new icon is an open padlock in the colour of that theme's lock icon;
a theme that draws its icons as thin outlines (z-bolt) gets an outline version. Existing unlock.svg files are left alone. Idempotent.
usage: make_unlock_icon.py /path/to/KlipperScreen"""
import glob
import os
import re
import sys

# filled style (material-*, colorized): 24x24, body as a frame with a keyhole, shackle open on the right
FILLED = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg version="1.1" width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
  <path fill="%(c)s" fill-rule="evenodd"
     d="M 6.75,21.1875 Q 5,21.1875 5,19.4375 V 10.6875 Q 5,8.9375 6.75,8.9375 H 17.25 Q 19,8.9375 19,10.6875 V 19.4375 Q 19,21.1875 17.25,21.1875 Z
        M 6.75,19.4375 H 17.25 V 10.6875 H 6.75 Z
        M 12,17.8125 A 1.75,1.75 0 1 0 12,14.3125 A 1.75,1.75 0 1 0 12,17.8125 Z"/>
  <path fill="none" stroke="%(c)s" stroke-width="1.75" stroke-linecap="butt" stroke-linejoin="miter"
     d="M 8.5,9.5 V 5.5 A 3.5,3.5 0 0 1 15.5,5.5 V 6.75"/>
</svg>
"""
# outline style (z-bolt): 64x64, white strokes like its lock icon
OUTLINE = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg version="1.1" width="64" height="64" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
  <ellipse style="fill:%(c)s;stroke:none" cx="31.929701" cy="41.06234" rx="4.3648357" ry="4.4511104"/>
  <rect style="fill:none;stroke:%(c)s;stroke-width:3;stroke-linecap:round;stroke-linejoin:round" width="32" height="27" x="16" y="27.5"/>
  <path style="fill:none;stroke:%(c)s;stroke-width:3;stroke-linecap:round;stroke-linejoin:miter" d="M 21,26.5 V 14 A 11,11 0 0 1 32,3 A 11,11 0 0 1 43,14 V 18"/>
</svg>
"""


def colour(lock_svg):
    """(colour, outline) of a theme's lock icon: outline themes draw it with thick strokes (z-bolt), the others as a filled shape."""
    t = open(lock_svg, errors="ignore").read()
    strokes = re.findall(r"stroke:(#[0-9a-fA-F]{6})", t)
    if strokes and "stroke-width:3" in t:
        return strokes[0], True
    fills = re.findall(r"fill:(#[0-9a-fA-F]{6})", t)
    return (fills[0] if fills else "#e2e2e2"), False


def main(ks):
    made = 0
    for lock in sorted(glob.glob(os.path.join(ks, "styles", "*", "images", "lock.svg"))):
        dst = os.path.join(os.path.dirname(lock), "unlock.svg")
        if os.path.exists(dst):
            continue
        c, outline = colour(lock)
        open(dst, "w").write((OUTLINE if outline else FILLED) % {"c": c})
        made += 1
    print("unlock icon added to %d theme(s)" % made)
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2 or not os.path.isdir(sys.argv[1]):
        sys.exit("usage: make_unlock_icon.py /path/to/KlipperScreen")
    sys.exit(main(sys.argv[1]))
