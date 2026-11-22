# Planar IK Lab

A dependency-free Python toolkit for forward kinematics and damped-least-squares inverse kinematics of planar serial robot arms. Unlike a single-step geometric demo, it solves arbitrary positive link chains iteratively and reports the best-effort residual for unreachable targets.

## How it works

Joint angles are relative revolute angles in radians; each link extends at the cumulative heading. The solver builds the 2×N end-effector Jacobian, solves the damped 2×2 system `(J Jᵀ + λ²I)z = target - position`, and applies bounded joint updates. Damping stabilizes near-singular poses, while the step limit prevents large jumps. The base is fixed at `(0, 0)`.

## Usage

Requires Python 3.10+; no third-party packages.

```sh
python3 ik.py --lengths 1,1,0.7 --angles 0,0,0 --target 1.5,1.2
python3 -m unittest -v
```

The CLI prints JSON with solved angles, all joint coordinates, residual error, and iterations used. Unreachable targets return the closest solution found (not an exception). Library users can call `Arm(lengths, initial_angles).solve((x, y))`; the returned angles can be passed to `joints()`.

## Phase 1 scope

The initial implementation provides forward kinematics, iterative damped inverse kinematics, bounded input checks, a JSON CLI, and deterministic unit tests. Joint limits and collision handling are outside the initial scope.
