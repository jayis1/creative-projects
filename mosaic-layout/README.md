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

Use `name:width:height:quantity` to request repeated parts. Add `--no-rotate` to prohibit rotation, or `--json` for a machine-readable report containing sheet dimensions, placements, free rectangles, and area statistics. The CLI rejects malformed dimensions and parts with a concise usage error.

Example JSON invocation:

```sh
python3 main.py 5 3 panel:5:3 --json
```

The JSON summary reports `used`, `waste`, and `utilization`; the output is deterministic for identical inputs.

## Testing

```sh
python3 -m unittest discover -s . -p 'test_*.py'
```

## Known Issues (Resolved)

- `waste_summary` raised an unhandled `ZeroDivisionError` for a zero-width sheet (and accepted negative dimensions). It now validates positive integer dimensions and raises the documented `LayoutError`; the regression test was observed failing before the fix and passes afterward.

## Verification

The final test suite covers placement non-overlap and area accounting, rotation policy, invalid and unfit parts, JSON CLI output, and invalid summary dimensions. The CLI examples above were executed against the shipped implementation.
