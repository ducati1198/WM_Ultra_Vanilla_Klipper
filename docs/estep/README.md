# E-step calibration: parts that live outside this repository

`WM_ESTEP_CAL` (installer 2.24.0) needs two changes in the Fluidd build and one entry in the Fluidd macro list. They are not part of the installer, so they are kept here as notes and pictures:

- `fluidd-prompt-image-size.md`: show a popup with one picture big (Fluidd source change, and the CSS/JS shortcut that was applied to the built Fluidd on the main RPi4).
- `fluidd-macro-category.md`: put `WM_ESTEP_CAL` in the "RPI Calibration" Fluidd category (colour #e91e63). The category list is written by the ACE Pro panel project (`wm_fluidd_categories.py`), so `WM_ESTEP_CAL` has to be added there too.
- `fluidd-images/estep-*.svg`: copy to `public/img/wm/` of the Fluidd source (`~/fluidd/img/wm/` on the Pi).

A Fluidd update overwrites the picture-size change on a Pi.
