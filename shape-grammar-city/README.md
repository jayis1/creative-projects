# shape-grammar-city

A procedural city generator that grows road networks and paints land-use zones with shape-grammar-inspired heuristics. The project produces ASCII maps, SVG renders, JSON snapshots, and layout statistics.

## Features

- Two road-growth modes: `grid` and `organic`
- Land-use zoning for residential, commercial, industrial, parks, and water
- Reproducible generation with deterministic seeds
- ASCII, SVG, JSON, and stats output modes
- JSON snapshot loading for repeatable renders and analysis

## How it works

1. Start with a seed intersection near the center of the map.
2. Grow roads by repeatedly extending short orthogonal segments.
3. Paint non-road cells according to distance from the core, road adjacency, edge bias, and random variation.
4. Render the result as text or vector art, or export structured JSON.

## Usage

Generate an ASCII city:

```bash
python3 -m citygen --width 41 --height 25 --seed 7 --mode grid --format ascii
```

Render an SVG file:

```bash
python3 -m citygen --width 51 --height 31 --seed 21 --mode organic --format svg --output city.svg
```

Export JSON and stats:

```bash
python3 -m citygen --seed 12 --format json --output city.json
python3 -m citygen --input city.json --format stats
```

## Example legend

- `#` road
- `r` residential
- `c` commercial
- `i` industrial
- `.` park
- `~` water
