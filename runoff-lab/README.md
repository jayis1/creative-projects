# Runoff Lab

A dependency-free, deterministic rainfall-runoff flow-routing model over seeded synthetic terrain. Its twist: it exposes a single-receiver drainage network and per-cell contributing area as both a JSON graph and an ASCII flow map.

## Contents

- [Quickstart](#quickstart)
- [How it works](#how-it-works)
- [Usage](#usage)
- [Architecture](#architecture)
- [Testing](#testing)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [Recent improvements](#recent-improvements)

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

A seeded synthetic basin is routed to its steepest lower cardinal neighbor, accumulating one rainfall unit per cell. The graph is acyclic because every edge descends in elevation. Choose 4-neighbor or 8-neighbor routing; the latter connects diagonal channels. Stream thresholding renders only cells whose contributing area reaches a chosen value. The model is illustrative rather than calibrated hydrology.

## Usage

- `python3 main.py --demo --width 24 --height 14 --seed 7` prints an ASCII accumulation map.
- `python3 main.py --demo --connectivity 8 --stream-threshold 4` extracts high-contributing-area channels.
- `python3 main.py --width 16 --height 10 --rain 2 --output flow.json` writes a JSON grid and downstream-index map.
- `python3 main.py --terrain elevations.json --connectivity 8 --demo` routes a user-supplied elevation grid. The JSON file must contain a rectangular array of finite numbers, for example `[[4, 3], [2, 0]]`.
- `python3 main.py --terrain elevations.json --output result.json` exports the resulting map; its dimensions come from the input and its seed is `null`.
- `python3 -m unittest -v` runs the tests.

- `--connectivity 4|8` chooses cardinal or diagonal flow routing (default 4).
- `--stream-threshold N` prints only cells with at least N contributing rainfall units.
Dimensions are limited to 512 per side and 262,144 cells total. JSON output uses exclusive creation and refuses to overwrite an existing file.

## Testing

Uses only Python 3 standard library. Run `python3 -m unittest -v`; no installation required.

## Architecture

`main.py` contains three layers: bounded input validation and JSON loading, deterministic single-receiver flow routing/accumulation, and the `argparse` CLI with ASCII/JSON output. `test_main.py` exercises reproducibility, conservation, routing modes, rendering, and terrain-file validation. `examples/stepped-basin.json` is a small hand-authored elevation grid for the input workflow.

## Roadmap

- Add optional per-cell rainfall input.
- Offer a raster export format for GIS tooling.
- Compare single-receiver routing with a multiple-flow-direction model.

## Contributing

Keep the model dependency-free and deterministic. Add focused `unittest` coverage for behavior and invalid inputs; run `python3 -m unittest -v` from this directory before submitting changes.

## Recent improvements

- Added validated JSON elevation-grid input via `--terrain`, enabling runs on hand-authored or externally prepared terrain while preserving the seeded generator as the default.
- Added a reproducible stepped-basin input example and documented the input/export workflow.
- CI was not added because repository policy for this run limits changes to the project subtree; no build-status badge is claimed.

## Known Issues (Resolved)

- A Python integer too large to convert to a finite float raised `OverflowError` during grid validation instead of the documented validation error. `_validate_grid` now catches overflow from `math.isfinite` and rejects the value with `ValueError`; `test_rejects_unrepresentably_large_integer_elevation` reproduced the failure before the fix and passes afterward.
