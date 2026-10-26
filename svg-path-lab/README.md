# SVG Path Lab

A small, dependency-free geometry inspector for SVG path strings. It parses the common line and Bézier commands and reports sampled bounds and approximate length.

## Try it

From this directory, run `python3 main.py --demo`. It prints deterministic JSON for a closed cubic path, including four segments and its bounds.

## How it works

The tokenizer consumes SVG path syntax strictly, then the parser expands relative and repeated parameter groups into absolute line, quadratic, and cubic segments. Smooth `S` and `T` commands reflect the preceding compatible control point. Curves are sampled uniformly in parameter space for approximate length and bounds.

## Usage

`python3 main.py --help`

`python3 main.py 'M0 0 C0 10 10 10 10 0 Z' --steps 64`

`python3 main.py --file path.txt`

`python3 main.py --svg drawing.svg --steps 64` reports every path element, preserving its `id` where present. SVG input is read-only and limited to 5 MB; XML is parsed locally without fetching resources.

Supported commands: M, L, H, V, C, S, Q, T, Z (upper or lowercase). Arc commands are not supported. Curve bounds/length are sampled approximations, not exact extrema/integrals. Multiple move-to subpaths are measured independently, without counting imaginary connector lines. Input files are read only; no output file is written.

## What makes this different

A typical SVG viewer renders paths; this tool exposes their geometry as inspectable JSON using only Python's standard library, so path parsing and numerical approximation can be experimented with independently of a graphics stack.

## Known Issues (Resolved)

- Relative coordinate addition could overflow finite operands into infinity, later emitting non-standard JSON numbers. `test_relative_coordinate_overflow_rejected` reproduced this before the fix; parsed segment coordinates are now checked after transformation.
- Multiple `M` commands were incorrectly treated as drawn line segments, inflating length and connecting separate contours. A reproduced test (`test_move_to_starts_new_subpath_without_connector`) failed at 142.716 instead of 2.0 before the fix; move commands now start independent contours, and regression coverage passes.

## Tests

Run `python3 -m unittest -v` from this directory.
