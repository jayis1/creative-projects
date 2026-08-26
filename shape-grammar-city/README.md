# shape-grammar-city

[![CI](https://github.com/jayis1/creative-projects/actions/workflows/shape-grammar-city.yml/badge.svg)](https://github.com/jayis1/creative-projects/actions/workflows/shape-grammar-city.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)

A procedural city generator that grows road networks with shape-grammar-inspired heuristics, paints land-use zones, identifies emergent districts, computes routes, validates maps, and exports polished visual reports.

---

## Table of Contents

- [Highlights](#highlights)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Configuration Files](#configuration-files)
- [CLI Reference](#cli-reference)
- [Examples](#examples)
- [Architecture](#architecture)
- [ASCII Demo](#ascii-demo)
- [Known Issues (Resolved)](#known-issues-resolved)
- [Recent Improvements](#recent-improvements)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

## Highlights

- Three street grammars: `grid`, `organic`, and `radial`
- Deterministic seeded generation for reproducible cities
- Weighted zoning across residential, commercial, industrial, park, water, and civic tiles
- Civic landmark placement near major intersections
- District analysis via connected-component grouping of zoned regions
- Route finding over the road network
- Validation for disconnected roads, empty cells, and malformed metadata
- ASCII, SVG, JSON, Markdown, and self-contained HTML report outputs
- JSON/TOML configuration profiles
- Batch comparison mode for exploring multiple seeds
- Pure-stdlib runtime package with a pytest suite and GitHub Actions CI

## Installation

### Option 1: Run directly from the monorepo

```bash
cd shape-grammar-city
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .[dev]
```

### Option 2: Install as a local package

```bash
pip install -e .
```

After installation, you can use either:

```bash
python3 -m citygen --help
```

or:

```bash
citygen --help
```

## Quick Start

Generate an ASCII city:

```bash
python3 -m citygen generate --width 41 --height 25 --seed 7 --mode grid --format ascii
```

Render an SVG file:

```bash
python3 -m citygen generate --width 51 --height 31 --seed 21 --mode radial --format svg --output city.svg
```

Generate a full HTML report:

```bash
python3 -m citygen report --config examples/profile.toml --output city-report.html
```

Analyze districts:

```bash
python3 -m citygen districts --width 31 --height 21 --seed 13 --mode radial --format markdown
```

Compare multiple seeds:

```bash
python3 -m citygen batch --width 31 --height 21 --mode organic --seeds 3,7,11 --metric road_cells
```

## Configuration Files

`shape-grammar-city` supports both JSON and TOML profiles.

Example TOML:

```toml
title = "Waterfront Showcase"
width = 31
height = 21
seed = 13
mode = "radial"
iterations = 28
landmarks = 5
cell_size = 12
seeds = [13, 21, 34]

[zone_weights]
commercial = 0.28
park = 0.18
residential = 0.34
industrial = 0.12
water = 0.05
civic = 0.03
```

Example JSON:

```json
{
  "city": {
    "width": 25,
    "height": 19,
    "seed": 8,
    "mode": "organic",
    "iterations": 20,
    "landmarks": 3,
    "zone_weights": {
      "commercial": 0.25,
      "park": 0.2
    }
  }
}
```

CLI flags always override config file values.

## CLI Reference

### `generate`

Create a city and emit one of four output formats.

```bash
python3 -m citygen generate --config examples/profile.toml --format stats
```

Formats: `ascii`, `svg`, `json`, `stats`

### `stats`

Compute coverage, connectivity, road-degree, and landmark metrics.

```bash
python3 -m citygen stats --input city.json
```

### `validate`

Check for disconnected networks, empty cells, and malformed metadata.

```bash
python3 -m citygen validate --input city.json
```

### `route`

Find the shortest road path between two coordinates.

```bash
python3 -m citygen route --input city.json --start 10,12 --goal 30,12 --format json
```

### `districts`

Discover emergent neighborhoods from contiguous zoned cells.

```bash
python3 -m citygen districts --config examples/profile.toml --format markdown
```

Formats: `json`, `markdown`

### `report`

Create a standalone HTML report with embedded SVG and district table.

```bash
python3 -m citygen report --config examples/profile.toml --output examples/demo-report.html
```

### `batch`

Generate several cities and compare the outputs.

```bash
python3 -m citygen batch --config examples/profile.toml --metric largest_component
```

Metrics: `road_cells`, `landmark_count`, `largest_component`

## Examples

The `examples/` directory includes:

- `profile.toml` — a full featured TOML config
- `profile.json` — a nested JSON config example
- `demo-city.txt` — generated ASCII city
- `demo-districts.md` — district analysis output
- `demo-batch.json` — multi-seed comparison output
- `demo-report.html` — standalone HTML map report
- `demo-config-stats.json` — stats generated via config-driven CLI

## Architecture

The generator is split into focused modules rather than a single monolith:

- `citygen.generator` — road growth, water corridor placement, zoning, landmark placement
- `citygen.analysis` — connectivity analysis, validation, shortest-path routing
- `citygen.districts` — connected district detection and naming
- `citygen.config` — JSON/TOML config loading and validation
- `citygen.render` — ASCII and SVG renderers
- `citygen.reports` — self-contained HTML report generation
- `citygen.cli` — subcommand orchestration and file I/O flow

For a more explicit breakdown, see [`docs/architecture.md`](./docs/architecture.md).

## ASCII Demo

Legend:

- `#` road
- `r` residential
- `c` commercial
- `i` industrial
- `.` park
- `~` water
- `@` civic landmark
- `*` highlighted path segment

Sample excerpt:

```text
rrirrriiircrrr@rrrircc.rrc~icir
rc.iri.rirrrrrrrr.ir.rcirrcr.r.
rrrrrrc.@#rcr.r#.crrr.rcrr.r.i.
i.cci..rr#c.cr~#rrrr.r..@.ci.ir
.rr@cr.cr#rrr.r#..r@.crc.crrcri
```

## Known Issues (Resolved)

- Fixed malformed JSON import handling: `CityMap.from_dict()` now rejects grids whose dimensions do not match the declared width/height.
- Fixed unsafe zone-weight handling: non-finite overrides such as `NaN` are now rejected instead of silently corrupting weighted selection.
- Fixed landmark metadata validation: empty `landmarks` metadata is now correctly reported during validation instead of being skipped by a truthiness check.

## Recent Improvements

### v0.2.0 improvements

- Added JSON/TOML configuration profiles
- Added district analysis with named neighborhoods and Markdown/JSON outputs
- Added standalone HTML report generation with embedded SVG maps
- Added batch comparison mode for exploring multiple seeds at once
- Added structured logging hooks and cleaner CLI output helpers
- Added installable console script entry point: `citygen`
- Added pytest coverage for configs, reports, districts, and batch mode
- Added a ready-to-drop GitHub Actions workflow example, example assets, architecture docs, CONTRIBUTING, and MIT license

## Roadmap

- Add optional district overlays directly to SVG output
- Support additional street grammars such as cul-de-sac suburbs and boulevard cores
- Export road graphs in interoperable formats for external analysis
- Introduce pluggable naming strategies for landmarks and districts
- Add richer report sections such as zoning histograms and route heatmaps

## Contributing

Contributions are welcome. Start with [`CONTRIBUTING.md`](./CONTRIBUTING.md).

Typical workflow:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .[dev]
pytest
```

## License

Distributed under the terms of the [MIT License](./LICENSE).
