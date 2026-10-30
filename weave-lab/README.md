# Weave Lab

A dependency-free weaving-draft explorer for small binary interlacement patterns. Its twist: the draft is treated as a measurable structure, reporting uninterrupted float lengths on warp and weft rather than only drawing a pattern.

Run an eight-by-eight twill (`█` = warp over weft; `·` = weft over warp):

```sh
python3 main.py --size 8 --step 1
```

A satin repeat spreads single warp-over points across each row and column: `python3 main.py --pattern satin --size 5 --step 2`.

```text
█····
··█··
····█
·█···
···█·
Float lengths: {"warp": 4, "weft": 4, "worst": 4}
```

Satin progressions must be coprime to the repeat size; for example, size 6 with step 2 is rejected because it cannot visit every position. Export a matrix: `python3 main.py --pattern plain --size 6 --json out.json`.

## How it works

Twill assigns a cell according to `(row + step * column) modulo size`; plain weave alternates over-under like a checkerboard. Satin places one warp-over point in each row and column using a coprime progression. For each warp column and weft row, the analyzer finds the longest run of identical face-up cells. Long floats can snag more readily. This educational model measures periodic repeats, not physical yarn tension, fiber, or loom setup.

## Usage

- `--size N`: repeat width and height from 2 to 64 (default 8).
- `--step N`: twill progression from 1 to `size - 1` (default 1; ignored for `plain`).
- `--pattern {twill,plain}`: select the cyclic twill (default) or checkerboard plain weave.
- `--json PATH`: additionally serialize the matrix as JSON.
- `python3 -m unittest -v`: run unit tests.

Invalid parameters produce a clear CLI error. Library validation supports rectangular binary drafts up to 256 by 256. Stdlib only; Python 3.9+.

## Known Issues (Resolved)

- `floats()` originally stopped at the edge of a stored row/column, under-reporting a continuous float that crossed into the next periodic repeat. Regression test: `test_float_wraps_across_periodic_repeat_boundary` failed with 2 where the correct run is 3; circular doubled scanning now reports 3 and caps measurements at one repeat.
