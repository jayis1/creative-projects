## Enhancements

- Added selectable 4- or 8-neighbor routing; diagonal drainage is available for terrain where cardinal-only routing traps cells on stair-step slopes.
- Added a minimum stream-contributing-area filter to the ASCII map, so channel networks can be isolated from hillslope cells.
- Made tie-breaking and downhill ordering deterministic, including equal-elevation cells.

Run `python3 main.py --demo --connectivity 8 --stream-threshold 4` to inspect the extracted channels. Existing 4-neighbor behavior remains the default.
