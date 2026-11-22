# Fluidd: put WM_ESTEP_CAL in the "RPI Calibration" macro category (same colour)

Fluidd keeps the macro list in the Moonraker database, namespace `fluidd`, key `macros` (backup first:
`curl "http://localhost:7125/server/database/item?namespace=fluidd&key=macros" > fluidd-macros-db.backup.json`).

Entry added to `value.stored` (the category id is the id of the existing "RPI Calibration" category on that printer;
on wmultra it is 1795037710131, look it up in `value.categories`, it is different on another printer):

    {"name": "WM_ESTEP_CAL", "alias": "", "visible": true, "disabledWhilePrinting": false,
     "color": "#e91e63", "categoryId": "1795037710131"}

Write the whole changed `macros` value back with `POST /server/database/item` (namespace `fluidd`, key `macros`, value = the full
changed object). Do not write only the entry. Reload the Fluidd page. Fluidd macros that start with "_" are hidden by default,
so only WM_ESTEP_CAL shows.
