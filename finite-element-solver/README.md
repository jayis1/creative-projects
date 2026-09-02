# finite-element-solver

2D truss finite element analysis toolkit built from the direct stiffness method. It solves pin-jointed planar trusses, reports nodal displacements, support reactions, and per-member axial stress/strain/force.

## Features

- Direct stiffness assembly for 2D truss elements
- Dense linear solver with singularity detection
- JSON model format for nodes, elements, loads, and supports
- CLI for solving models and writing a starter example
- Example truss models for a cantilever triangle and a roof truss
- Pytest suite covering solving, reactions, CLI output, and invalid models

## Model format

```json
{
  "nodes": [
    {"id": "A", "x": 0.0, "y": 0.0},
    {"id": "B", "x": 1.0, "y": 0.0},
    {"id": "C", "x": 1.0, "y": 1.0, "load": [0.0, -1000.0]}
  ],
  "elements": [
    {"id": "AB", "start": "A", "end": "B", "E": 210000000000.0, "A": 0.003},
    {"id": "BC", "start": "B", "end": "C", "E": 210000000000.0, "A": 0.003},
    {"id": "AC", "start": "A", "end": "C", "E": 210000000000.0, "A": 0.003}
  ],
  "supports": [
    {"node": "A", "fix": [true, true]},
    {"node": "B", "fix": [false, true]}
  ]
}
```

## How it works

Each truss bar contributes a 4x4 global stiffness block derived from its orientation cosine and sine. The solver assembles those blocks into the global matrix, removes constrained degrees of freedom, solves the reduced linear system, reconstructs full nodal displacement vectors, and then computes support reactions and axial member responses.

## Usage

Create a virtual environment if you want an isolated install:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
```

Solve an included example:

```bash
python3 -m finite_element_solver solve examples/cantilever-triangle.json
```

Emit JSON instead of formatted text:

```bash
python3 -m finite_element_solver solve examples/roof-truss.json --json
```

Write a starter file:

```bash
python3 -m finite_element_solver write-example scratch.json
```

Run tests:

```bash
python3 -m pytest
```

## Example output

```text
Displacements:
  A: dx=0.000000e+00 m, dy=0.000000e+00 m
  B: dx=0.000000e+00 m, dy=0.000000e+00 m
  C: dx=1.587302e-06 m, dy=-1.587302e-06 m
Reactions:
  A: Rx=0.000 N, Ry=0.000 N
  B: Rx=0.000 N, Ry=1000.000 N
Element forces:
  AB: axial=0.000 N, stress=0.000 Pa, strain=0.000000e+00
  BC: axial=-1000.000 N, stress=-333333.333 Pa, strain=-1.587302e-06
  AC: axial=0.000 N, stress=0.000 Pa, strain=0.000000e+00
Max displacement magnitude: 2.244783e-06 m
```
