# Planar IK Lab

A dependency-free Python toolkit for forward kinematics and damped-least-squares inverse kinematics of planar serial robot arms. Unlike a single-step geometric demo, it solves arbitrary positive link chains iteratively and reports the best-effort residual for unreachable targets.

## Table of contents

- [How it works](#how-it-works)
- [Installation](#installation)
- [Usage](#usage)
- [Python API](#python-api)
- [Architecture](#architecture)
- [Tests](#tests)
- [Limitations and roadmap](#limitations-and-roadmap)
- [Contributing](#contributing)

## How it works

Joint angles are relative revolute angles in radians; each link extends at the cumulative heading. The solver builds the 2×N end-effector Jacobian and solves the damped system `(J Jᵀ + λ²I)z = target - position`. Damping stabilizes near-singular poses, while a step bound limits each update. The base is fixed at `(0, 0)`. An optional pair of hard angular limits per joint clamps both the initial pose and each solver update.

## Installation

Requires Python 3.10 or newer. There are no third-party dependencies and no installation step; clone the repository and run the script directly:

```sh
git clone https://github.com/jayis1/creative-projects.git
cd creative-projects/planar-ik-lab
python3 ik.py --help
```

## Usage

Solve a target with defaults:

```sh
python3 ik.py --lengths 1,1,0.7 --angles 0,0,0 --target 1.5,1.2
```

Set solver tuning values and per-link hard limits (JSON pairs in radians):

```sh
python3 ik.py --lengths 1,1 --angles 0,0 --target 0,1 \\
  --damping 0.1 --max-step 0.1 --joint-limits '[[-0.5,0.5],[-1,1]]'
```

Options also include `--iterations` (0–100000) and `--tolerance`. Invalid values produce an argparse error and exit status 2. Successful runs print JSON containing `angles_radians`, every joint coordinate, residual `error`, and `iterations`. Unreachable targets return the best pose reached, with its residual, rather than raising an exception.

## Python API

```python
from ik import Arm

arm = Arm((1.0, 1.0), (0.0, 0.0))
angles, residual, steps = arm.solve(
    (0.8, 1.2), joint_limits=((-1.5, 1.5), (-2.0, 2.0))
)
points = arm.joints(angles)
```

Lengths must be finite and positive; initial angles and target coordinates must be finite. Limits require one finite ordered `(minimum, maximum)` pair per link. Solver defaults are 500 iterations, tolerance `1e-5`, damping `0.05`, and maximum step `0.2` radians.

## Architecture

`Arm` is an immutable dataclass holding link lengths and initial angles. `joints()` computes forward kinematics; `solve()` repeatedly evaluates the end-effector Jacobian, applies a damped least-squares update, and optionally clamps the update to hard stops. `main()` adapts command-line strings into validated model inputs and emits machine-readable JSON. The project intentionally uses only the Python standard library.

## Tests

Run the deterministic unit and subprocess CLI tests from this directory:

```sh
python3 -m unittest -v
```

## Limitations and roadmap

The solver is local and may return a best-effort pose rather than a global optimum. It does not model link or self-collisions. Future directions include collision-aware solving, visualization, and packaging if the project grows beyond a standalone lab. These are not implemented.

## Contributing

Keep changes dependency-free where practical, add regression tests for behavior changes, and run `python3 -m unittest -v` before submitting. Preserve radians as the API and CLI angle unit.

## Changelog

- Added CLI controls for damping and maximum step, plus JSON-configured hard joint limits.
- Expanded CLI regression coverage and usage documentation.

---

The initial project provides forward kinematics, iterative damped inverse kinematics, bounded input checks, a JSON CLI, hard joint limits, and deterministic unit tests. Collision handling remains outside scope.
