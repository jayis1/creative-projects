# finite-element-solver

2D truss finite element analysis toolkit built from the direct stiffness method. It solves pin-jointed planar trusses, supports named load cases, handles self-weight, and reports nodal displacements, reactions, element stress/strain/force, utilization, and mass.

## Features

- Direct stiffness assembly for 2D truss elements
- Partial-pivot Gaussian elimination with singularity detection
- JSON and TOML model input
- Materials and sections with reusable references
- Named load cases with nodal loads and optional gravity/self-weight
- Aggregate model summaries: counts, mass, total length, bounding box
- CLI for solving, listing load cases, printing summaries, and writing starter examples
- Example trusses for a cantilever triangle and a roof truss
- Pytest suite covering solve paths, summaries, TOML parsing, CLI commands, and invalid models

## Model format

A model may define reusable `materials` and `sections`, then reference them from each element.

```json
{
  "metadata": {"title": "Cantilever triangle"},
  "materials": [
    {"id": "steel", "E": 210000000000.0, "density": 7850.0, "yield_strength": 250000000.0}
  ],
  "sections": [
    {"id": "rod", "A": 0.003}
  ],
  "nodes": [
    {"id": "A", "x": 0.0, "y": 0.0},
    {"id": "B", "x": 1.0, "y": 0.0},
    {"id": "C", "x": 1.0, "y": 1.0}
  ],
  "elements": [
    {"id": "AB", "start": "A", "end": "B", "material": "steel", "section": "rod"},
    {"id": "BC", "start": "B", "end": "C", "material": "steel", "section": "rod"},
    {"id": "AC", "start": "A", "end": "C", "material": "steel", "section": "rod"}
  ],
  "supports": [
    {"node": "A", "fix": [true, true]},
    {"node": "B", "fix": [false, true]}
  ],
  "load_cases": [
    {"name": "service", "node_loads": [{"node": "C", "load": [0.0, -1000.0]}]},
    {"name": "gravity", "gravity": [0.0, -9.81], "include_self_weight": true}
  ]
}
```

## How it works

Each truss bar contributes a 4×4 global stiffness block derived from its direction cosines. The solver assembles those contributions into a full global matrix, removes constrained degrees of freedom, solves the reduced system, reconstructs nodal displacements, then computes support reactions from `K u - f`. Element strain comes from projected axial extension; stress follows from Hooke's law, and axial force follows from stress times area. When density and gravity are present, self-weight is lumped equally to each element endpoint.

## Usage

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
```

Solve the default example load case:

```bash
python3 -m finite_element_solver solve examples/cantilever-triangle.json --case service
```

Solve the roof truss with JSON output:

```bash
python3 -m finite_element_solver solve examples/roof-truss.json --case snow --json
```

List load cases:

```bash
python3 -m finite_element_solver list-load-cases examples/roof-truss.json
```

Print a summary:

```bash
python3 -m finite_element_solver summary examples/roof-truss.json
```

Write a starter example:

```bash
python3 -m finite_element_solver write-example scratch.json --preset triangle
```

Run tests:

```bash
python3 -m pytest
```

## Example output

```text
Load case: service
Displacements:
  A: dx=0.000000e+00 m, dy=0.000000e+00 m
  B: dx=0.000000e+00 m, dy=0.000000e+00 m
  C: dx=1.587302e-06 m, dy=-1.587302e-06 m
Reactions:
  A: Rx=0.000 N, Ry=0.000 N
  B: Rx=0.000 N, Ry=1000.000 N
Element forces:
  AB: axial=0.000 N, stress=0.000 Pa, strain=0.000000e+00, utilization=0.000%, mass=23.550 kg
  BC: axial=-1000.000 N, stress=-333333.333 Pa, strain=-1.587302e-06, utilization=0.133%, mass=23.550 kg
  AC: axial=0.000 N, stress=0.000 Pa, strain=0.000000e+00, utilization=0.000%, mass=33.305 kg
Total length: 3.414 m
Total mass: 80.405 kg
Max displacement magnitude: 2.244783e-06 m
```

## Enhancements in phase 2

- Added reusable material and section libraries
- Added named load cases
- Added gravity and self-weight loading
- Added utilization and mass reporting per member
- Added model summary and load-case listing commands
- Added TOML parsing and broader test coverage
