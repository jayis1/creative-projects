# Mosaic Layout

Plan integer-sized parts on a sheet with deterministic guillotine cuts, rotation, and area accounting. Useful for quick workshop, tile, and panel layouts; this is a heuristic, not a globally optimal nesting solver.

## How it works

Parts are ordered by descending largest side and placed into the free rectangle with the best short-side fit. Each cut splits that rectangle into two disjoint remnants. Rotation is considered when enabled. All dimensions use the same integer unit.

## Usage

From this directory:

```sh
python3 main.py 10 8 panel:6:4 tile:4:4 strip:2:4
```

Output:

```text
panel: x=0, y=0, 4x6 rotated
tile: x=4, y=0, 4x4
strip: x=8, y=0, 2x4
Utilization: 60.0% (waste: 32)
```

Use `name:width:height:quantity` to request repeated parts. The CLI prints each placement and sheet utilization.

## Testing

```sh
python3 -m unittest discover -s . -p 'test_*.py'
```

## Known Issues (Resolved)

No confirmed defects were found during the final source review; see added regression coverage and verification notes in the final phase commit.
