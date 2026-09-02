# finite-element-solver

[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![CI](https://img.shields.io/badge/ci-github%20actions-black.svg)](../../actions)

2D truss finite element analysis toolkit built around the direct stiffness method. It solves pin-jointed planar trusses, supports reusable materials and sections, named load cases, linear load combinations, self-weight, and envelope reporting for fast design checks.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Model Format](#model-format)
- [CLI Reference](#cli-reference)
- [Architecture](#architecture)
- [Examples and Demos](#examples-and-demos)
- [Recent Improvements](#recent-improvements)
- [Known Issues (Resolved)](#known-issues-resolved)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

## Features

- Direct stiffness assembly for 2D truss elements
- Partial-pivot Gaussian elimination with singularity detection
- JSON, TOML, and YAML model input/output
- Reusable material and section libraries
- Named load cases with nodal loads and optional gravity/self-weight
- Linear load combinations for code-style strength and service checks
- Envelope reporting across cases and combinations
- Model validation command for CI and preflight checks
- CLI logging with selectable log levels and file output
- Installable package with pytest suite and GitHub Actions workflow

## Installation

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e .[dev]
```

## Quick Start

Solve a basic load case:

```bash
python3 -m finite_element_solver solve examples/cantilever-triangle.json --case service
```

Solve a load combination from YAML:

```bash
python3 -m finite_element_solver solve examples/roof-truss.yaml --combination ultimate-down
```

Compute an envelope across all defined cases and combinations:

```bash
python3 -m finite_element_solver envelope examples/roof-truss.yaml --json
```

Validate a model in automation:

```bash
python3 -m finite_element_solver validate examples/roof-truss.yaml
```

Write starter examples in any supported format:

```bash
python3 -m finite_element_solver write-example scratch.yaml --preset roof
python3 -m finite_element_solver write-example scratch.toml --preset triangle
```

Run tests:

```bash
python3 -m pytest
```

## Model Format

A model may define reusable `materials` and `sections`, then reference them from each element. Load combinations reference named load cases by factor.

```yaml
metadata:
  title: Roof truss
materials:
  - id: steel
    E: 200000000000.0
    density: 7850.0
    yield_strength: 250000000.0
sections:
  - id: chord
    A: 0.004
nodes:
  - {id: A, x: 0.0, y: 0.0}
  - {id: B, x: 2.0, y: 0.0}
  - {id: C, x: 4.0, y: 0.0}
  - {id: D, x: 1.0, y: 1.0}
  - {id: E, x: 3.0, y: 1.0}
elements:
  - {id: AB, start: A, end: B, material: steel, section: chord}
  - {id: BC, start: B, end: C, material: steel, section: chord}
  - {id: AD, start: A, end: D, material: steel, section: chord}
  - {id: DB, start: D, end: B, material: steel, section: chord}
  - {id: BE, start: B, end: E, material: steel, section: chord}
  - {id: EC, start: E, end: C, material: steel, section: chord}
  - {id: DE, start: D, end: E, material: steel, section: chord}
supports:
  - {node: A, fix: [true, true]}
  - {node: C, fix: [false, true]}
load_cases:
  - name: snow
    node_loads:
      - {node: D, load: [0.0, -6000.0]}
      - {node: E, load: [0.0, -6000.0]}
  - name: self-weight
    gravity: [0.0, -9.81]
    include_self_weight: true
load_combinations:
  - name: ultimate-down
    cases:
      self-weight: 1.2
      snow: 1.6
```

## CLI Reference

```text
solve                  Solve one load case or load combination
summary                Print aggregate model statistics
list-load-cases        List defined load cases
list-load-combinations List defined load combinations
envelope               Build governing displacement/stress/utilization envelopes
validate               Validate input without solving
write-example          Emit a starter model in JSON/TOML/YAML
```

Use logging when integrating with scripts:

```bash
python3 -m finite_element_solver --log-level INFO --log-file run.log summary examples/roof-truss.yaml
```

## Architecture

```text
finite_element_solver/
├── model.py      # data classes, parsing, validation
├── solver.py     # stiffness assembly and linear solve
├── io.py         # JSON/TOML/YAML readers and writers
├── reporting.py  # summaries, result serialization, envelopes
├── examples.py   # built-in starter models
└── cli.py        # argparse entrypoint and command dispatch
```

The solver assembles each bar's 4×4 stiffness contribution into the global matrix, removes constrained degrees of freedom, solves the reduced linear system, reconstructs displacements, then computes reactions from `K u - f`. Because the model is linear elastic, load combinations are solved by scaling and summing case load vectors once, instead of re-deriving special-case logic.

## Examples and Demos

- `examples/cantilever-triangle.json`
- `examples/roof-truss.json`
- `examples/roof-truss.yaml`
- `docs/usage-demo.md`

Example text output:

```text
Load combination: ultimate-down
Displacements:
  A: dx=0.000000e+00 m, dy=0.000000e+00 m
  B: dx=0.000000e+00 m, dy=-2.007758e-05 m
  C: dx=1.240195e-05 m, dy=0.000000e+00 m
```

## Recent Improvements

- Split the original monolithic implementation into focused modules
- Added YAML input/output support
- Added linear load combinations and envelope analysis
- Added validation and load-combination listing commands
- Added structured logging and file-based logs
- Added install metadata, CONTRIBUTING guide, LICENSE, docs, and CI config
- Expanded tests to cover new CLI flows and envelope logic

## Known Issues (Resolved)

- Fixed silent overwriting of duplicate material definitions; models now fail fast.
- Fixed silent overwriting of duplicate section definitions; models now fail fast.
- Fixed duplicate load entries within one load case being overwritten; they are now summed.
- Fixed `write-example` rejecting TOML destinations; it now writes valid TOML as well as JSON.
- Fixed load-combination assembly from double-counting node base loads.

## Roadmap

- Beam/frame elements with rotational degrees of freedom
- Sparse matrix backend for larger models
- Plotting and SVG result export
- Material nonlinearity and iterative solve modes
- Basic optimization for section sizing under utilization constraints

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup and development workflow.

## License

MIT. See [LICENSE](LICENSE).
