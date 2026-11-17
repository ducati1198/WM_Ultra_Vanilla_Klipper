#!/usr/bin/env python3
"""WonderMaker changes to KlipperScreen's own files (2.9.0). The changes are listed in ks_wm_patches.json next to this script.

  patch_ks_wm.py KEY FILE        KEY = extrude | job_status | fine_tune | prompts | screen | main_menu | temperature

  extrude     panels/extrude.py           the sensor strip shows T<n> head, T<n> hub and Tool lock of the tool on the carriage,
                                          and a button "All sensors" opens the Sensors page (panels/wm_sensors.py)
  job_status  panels/job_status.py        the Z offset of the print screen is the live Z adjust of the tool on the carriage, and
                                          after a print one button "Save Z Trim" opens the Save all / Do not save window
                                          (instead of Klipper's Save Z to probe / endstop, which would bake the tool offsets in)
  fine_tune   panels/fine_tune.py         Fine Tuning shows and changes the live Z adjust of the tool on the carriage
  prompts     ks_includes/widgets/prompts.py   every text line of a window is shown (not only the last one), and a window
                                          closes at once when a button or X is pressed (before, it waited for a busy Klipper);
                                          a window can show pictures, "action:prompt_image name [name ...]" (2.14.0, files
                                          KlipperScreen/wm_images/<name>.png)
  screen      screen.py                   the filament sensors are read again 8 s after the start (they showed off after a
                                          Klipper restart); and 30 s after KlipperScreen stopped retrying to reach
                                          the Pi it starts a new round of tries by itself (2.13.0)
  main_menu   panels/main_menu.py         no temperature graph on the main menu (2.11.0: the graph drew up to 1200 points per line
  temperature panels/temperature.py       and no graph on the Temperature page   in Python without a GPU and took a whole core of
                                          the screen board; the temperatures stay as numbers)

Each change is "old lines -> new lines": old lines found once -> replaced; new lines already there -> nothing to do; else the
file is left as it was (KlipperScreen of another version, or your own edit) and the exit code is 11.
Exit codes: 0 nothing to do, 10 changed, 11 not changed (lines different), 2 usage."""
import json
import os
import sys


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    key, path = sys.argv[1], sys.argv[2]
    data = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "ks_wm_patches.json")))
    if key not in data or not os.path.isfile(path):
        print(__doc__)
        return 2
    text = open(path).read()
    new = text
    for h in data[key]:
        if new.count(h["old"]) == 1:
            new = new.replace(h["old"], h["new"])
        elif h["new"] in new:
            continue
        else:
            print("not changed %s: these lines are different (KlipperScreen of another version, or an own edit)" % path)
            return 11
    if new == text:
        return 0
    tmp = path + ".wm-tmp"
    with open(tmp, "w") as f:
        f.write(new)
    os.replace(tmp, path)
    return 10


if __name__ == "__main__":
    sys.exit(main())
