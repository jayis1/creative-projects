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

A seeded synthetic basin is routed to its steepest lower cardinal neighbor, accumulating one rainfall unit per cell. The graph is acyclic because every edge descends in elevation. Choose 4-neighbor or 8-neighbor routing; the latter connects diagonal channels. Stream thresholding renders only cells whose contributing area reaches a chosen value. The model is illustrative rather than calibrated hydrology.

## Usage

- `python3 main.py --demo --width 24 --height 14 --seed 7` prints an ASCII accumulation map.
- `python3 main.py --demo --connectivity 8 --stream-threshold 4` extracts high-contributing-area channels.
- `python3 main.py --width 16 --height 10 --rain 2 --output flow.json` writes a JSON grid and downstream-index map.
- `python3 -m unittest -v` runs the tests.

- `--connectivity 4|8` chooses cardinal or diagonal flow routing (default 4).
- `--stream-threshold N` prints only cells with at least N contributing rainfall units.
Dimensions are limited to 512 per side and 262,144 cells total. JSON output uses exclusive creation and refuses to overwrite an existing file.

## Testing

Uses only Python 3 standard library. Run `python3 -m unittest -v`; no installation required.

## Known Issues (Resolved)

- A Python integer too large to convert to a finite float raised `OverflowError` during grid validation instead of the documented validation error. `_validate_grid` now catches overflow from `math.isfinite` and rejects the value with `ValueError`; `test_rejects_unrepresentably_large_integer_elevation` reproduced the failure before the fix and passes afterward.
