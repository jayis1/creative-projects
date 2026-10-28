# Stitch Planner

Turn a small monochrome raster design into a deterministic running-stitch path and SVG preview. Mark ink with `#` and blank cells with `.`; alternating scan directions reduce unnecessary travel between rows. This creates a planning preview, not a machine-specific embroidery file.

## Contents

- [Install](#install)
- [Usage](#usage)
- [Input format](#input-format)
- [Architecture](#architecture)
- [Development and tests](#development-and-tests)
- [Roadmap](#roadmap)
- [Changelog](#changelog)
- [License](#license)

## Install

Requires Python 3.10 or newer. Install from this project directory:

```sh
python3 -m pip install .
```

This installs the `stitch-planner` command. The runtime has no third-party dependencies. For development and tests, install pytest as well:

```sh
python3 -m pip install -e . pytest
```

## Usage

Generate a preview from the included leaf sample:

```sh
stitch-planner examples/leaf.mask --output leaf.svg --spacing 1 --max-stitch-length 2.5 --max-stitches 500
```

The command reports the number of planned vertices and where the SVG was written. Use `--help` to inspect all options, or `--version` to print the installed version. The equivalent direct invocation (without installation) is:

```sh
python3 stitch_planner.py examples/leaf.mask -o leaf.svg --spacing 2
```

`--spacing` samples every Nth mask row. `--max-stitch-length` subdivides longer segments evenly; `0` disables subdivision. `--max-stitches` bounds plan vertices, and SVG subdivision has an independent 100,000-point default ceiling.

Import the planner directly when embedding it:

```python
from stitch_planner import plan, svg

points = plan(["..##..", ".####.", "..##.."], spacing=1)
preview = svg(points, width=6, height=3, stitch_length=1.5)
```

## Input format

A mask is UTF-8 text with one raster row per line. Every row must have equal nonzero width and contain only `#` and `.`. Invalid masks, nonpositive spacing or limits, inaccessible files, and invalid numeric options are reported as concise command-line errors with a nonzero exit status.

## Architecture

The project is intentionally a small, dependency-free Python module:

- `plan()` validates the rectangular mask, detects contiguous ink runs, and emits endpoint pairs in a serpentine row order.
- `svg()` optionally subdivides long spans under a point-count ceiling and emits a self-contained SVG path.
- `main()` exposes those functions through argparse, handles file/validation errors, and writes the requested output.

The data flow is mask text → validated run endpoints → optional segment subdivision → SVG document. Coordinates use the source raster's pixel space.

## Development and tests

```sh
python3 -m pytest
python3 -m stitch_planner --help
python3 -m stitch_planner examples/leaf.mask -o /tmp/leaf.svg --spacing 1 --max-stitch-length 2.5 --max-stitches 500
```

The test suite covers scan order, invalid masks and limits, subdivision safety, dimensions, and missing-input CLI behavior. See [CONTRIBUTING.md](CONTRIBUTING.md) for setup expectations. No CI workflow is configured for this project.

## Roadmap

- Add optional preview styling and coordinate scaling without changing stitch coordinates.
- Support additional simple vector or raster-mask input formats.
- Explore machine-format export with format-specific validation and explicit compatibility limits.

## Changelog

- Added installable `stitch-planner` command and version option.
- Made invalid stitch limits and file I/O failures produce clean CLI errors; added regression tests.
- Added installation, architecture, API, development, and roadmap documentation.

## License

MIT; see [LICENSE](LICENSE).
