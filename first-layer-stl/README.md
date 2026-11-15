# First layer test files

Flat test squares for the first layer check that follows `WM_FULL_OFFSET_CAL`. Bed size 300 x 270 mm.

| File | What it is |
|---|---|
| `wm_first_layer_T0.stl` to `wm_first_layer_T3.stl` | One square per tool head, 50 x 50 mm, 0.2 mm high. The tool number is cut out of the square. |
| `Trim_Test_80x80.3mf` | Ready-made OrcaSlicer project (Orca 2.5.1) for the tool test: four squares of 80 x 80 mm, 0.2 mm high, numbered 1 to 4, already placed on the bed and each given its own tool (1 = T0, 2 = T1, 3 = T2, 4 = T3). PLA, nozzle 220 C, bed 55 C, layer 0.2 mm, slicer Z offset 0. Open it, pick your own printer and filament presets if they differ, slice and print. |
| `wm_first_layer_bed_5patch.stl` | Five squares for one tool: four corners and the centre, numbered 1 to 5. Shows if the first layer is even over the whole bed. |

The quick way: open `Trim_Test_80x80.3mf` in OrcaSlicer, slice, print, then correct with `WM_Z_TRIM_MENU`.

How to use the tool test with the STL files:

1. Load the four T files in the slicer together. If it asks to load them as one object with several parts, say yes: that keeps the 2 x 2 layout.
2. Give each square its own tool (the T0 file to the first tool, and so on).
3. Layer height and first layer height 0.2 mm. Leave the Z offset of the slicer at 0.
4. Print, look at each square, and correct with `WM_Z_TRIM_MENU`.

How to read a square: good is a closed smooth surface where the lines just touch. Too close is rough, see-through or with ridges between the lines: use a plus trim. Too far is lines that do not touch each other and lift easily: use a minus trim.
