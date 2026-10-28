# Stitch Planner

Turn tiny monochrome raster designs into travel-aware running-stitch SVG paths. This is a practical bridge between pixel art and hand embroidery: each marked horizontal run becomes a stitch segment, alternating rows reverse scan direction to reduce travel.

## Quick start

```sh
python3 stitch_planner.py examples/leaf.mask -o leaf.svg --spacing 2
```

Output is a self-contained SVG preview; the path vertices represent stitch locations. The mask is plain UTF-8 text (`#` ink, `.` blank), so no imaging libraries are required.

## How it works

The planner samples every `spacing`th row, detects maximal contiguous ink runs, and traverses runs in alternating directions. An optional maximum stitch length inserts evenly spaced intermediate points, making long runs more suitable for actual thread. SVG coordinates use the source raster's pixel coordinate system. This is a running-stitch planner, not a machine-specific embroidery file exporter.

## CLI

```sh
python3 stitch_planner.py --help
python3 stitch_planner.py examples/leaf.mask -o leaf.svg --spacing 1
```

Run tests from this folder with `python3 -m unittest discover -s tests`.
