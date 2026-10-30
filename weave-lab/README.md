# Weave Lab

A dependency-free weaving-draft explorer for small binary interlacement patterns. Its twist: the draft is treated as a measurable structure, reporting the longest uninterrupted float on both warp and weft rather than only drawing a pattern.

Run the demo from this directory:

```sh
python3 main.py --size 8 --step 1
```

The terminal displays an eight-by-eight twill draft (`█` = warp over weft; `·` = weft over warp), followed by float measurements. Save a reusable pattern with `python3 main.py --size 6 --step 2 --json out.json`.

## How it works

The cyclic twill rule assigns a cell according to `(row + step * column) modulo size`. For each warp column and weft row, the analyzer finds the longest run of identical face-up cells; these runs are the float lengths. Long floats are a useful warning because they can snag more easily. This educational model measures a periodic repeat, not physical yarn tension, fiber, or loom setup.

## Usage

- `--size N`: repeat width and height, from 2 to 64 (default 8).
- `--step N`: twill progression, from 1 to `size - 1` (default 1).
- `--json PATH`: additionally serialize the matrix as JSON.
- `python3 -m unittest -v`: run unit tests.

Invalid parameters produce a clear CLI error. The library also validates rectangular binary drafts up to 256 by 256 before analysis/rendering. Stdlib only; Python 3.9+.
