# shape-grammar-city

A procedural city generator that grows road networks and paints land-use zones with shape-grammar-inspired heuristics. It now supports multiple street grammars, weighted zoning, civic landmarks, routing, validation, and export-friendly outputs.

## Features

- Three road-growth modes: `grid`, `organic`, and `radial`
- Weighted land-use zoning for residential, commercial, industrial, park, water, and civic tiles
- Deterministic generation with reproducible seeds
- Civic landmark placement near major intersections
- ASCII and SVG rendering, JSON snapshots, route overlays, and statistics reports
- Validation of road-network connectivity and fill completeness
- Shortest-path routing across the generated road network
- Pure-stdlib Python package with unit tests

## How it works

1. Start with a seed intersection near the center of the map.
2. Grow streets using one of several grammars:
   - `grid`: extends orthogonal avenues from a rolling frontier
   - `organic`: uses branching walkers for more irregular neighborhoods
   - `radial`: creates spokes and rings before blending in a secondary grid
3. Carve a river or canal corridor to break symmetry.
4. Fill remaining cells with land uses using weighted random selection adjusted by downtown distance, road adjacency, edge bias, and waterfront proximity.
5. Convert selected lots near large intersections into civic landmarks.
6. Render, validate, analyze, or route across the resulting city.

## Usage

Generate an ASCII city:

```bash
python3 -m citygen generate --width 41 --height 25 --seed 7 --mode grid --format ascii
```

Render an SVG file:

```bash
python3 -m citygen generate --width 51 --height 31 --seed 21 --mode radial --format svg --output city.svg
```

Bias the generator toward commerce and parks:

```bash
python3 -m citygen generate \
  --seed 12 \
  --mode organic \
  --zone-weight commercial=0.35 \
  --zone-weight park=0.2 \
  --format stats
```

Validate a saved city:

```bash
python3 -m citygen validate --input city.json
```

Route through the road network:

```bash
python3 -m citygen route --input city.json --start 10,12 --goal 30,12 --format ascii
```

## Output legend

- `#` road
- `r` residential
- `c` commercial
- `i` industrial
- `.` park
- `~` water
- `@` civic landmark
- `*` highlighted path segment

## Enhancements added in Phase 2

- Added `radial` street grammar with ring roads and spokes
- Added weighted zoning overrides via CLI
- Added civic landmark placement and visualization
- Added route-finding and path overlays
- Added city validation and richer statistics
- Refactored CLI into subcommands and improved input validation
- Added docstrings and broader test coverage
