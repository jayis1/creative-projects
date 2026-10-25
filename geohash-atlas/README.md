# Geohash Atlas

A small geographic indexing toolkit for converting latitude/longitude into geohash cells and inspecting their bounding rectangles. Useful for learning spatial indexing and for quick offline coordinate bucketing; unlike a lookup demo, it exposes the cell geometry at arbitrary precision so callers can reason about spatial resolution.

## How it works

Geohash alternates binary subdivision of longitude and latitude intervals. Five bits are packed per character into the conventional base-32 alphabet. Decoding reverses each bit subdivision to give the cell's south/west/north/east limits. Precision is bounded to 1–12 characters.

## Usage

From the repository root:

```sh
python3 -m geohash_atlas encode 42.6 -5.6 --precision 5
python3 -m geohash_atlas decode ezs42
python3 -m unittest discover -s geohash-atlas/tests -v
```

`python3 -m geohash_atlas neighbors ezs42` lists the eight adjacent cells and the cell's height/width in degrees. Neighbor cells are not wrapped across globe edges; unavailable neighbors appear as `null`.

## Limitations

This implementation reports rectangular geohash cells; it does not calculate geodesic distances or handle polygons crossing the antimeridian as a single region.
