# Runoff Lab

A dependency-free, deterministic rainfall-runoff flow-routing model over seeded synthetic terrain. Its twist: it exposes a single-receiver drainage network and per-cell contributing area as both a JSON graph and an ASCII flow map.

## Quickstart

From this directory run `python3 main.py --demo`.

Example (small map):

```text
  ..   .
 .:-:  .
:-+*=-:
 =#%@#=
```

(The exact pattern is deterministic for a given seed and dimensions.)

## How it works

The terrain generator creates a gently sloped, seeded basin. Each cell routes to the cardinal neighbor with the greatest strictly positive elevation drop; cells without a lower neighbor are sinks. Because every edge decreases elevation, routing is acyclic. Starting with one unit of rainfall per cell, cells are visited in descending elevation order and pass their accumulated contribution downstream. The output is a discrete contributing-area estimate, not a calibrated hydrology model.

## Usage

- `python3 main.py --demo --width 24 --height 14 --seed 7` prints an ASCII accumulation map.
- `python3 main.py --width 16 --height 10 --rain 2 --output flow.json` writes a JSON grid and downstream-index map.
- `python3 -m unittest -v` runs the tests.

Dimensions are limited to 512 per side and 262,144 cells total. JSON output uses exclusive creation and refuses to overwrite an existing file.

## Testing

Uses only Python 3 standard library. No installation required.
