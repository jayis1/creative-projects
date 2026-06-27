# simplex-solver

An exact-arithmetic linear and integer programming solver implemented from scratch in pure Python (stdlib only — no NumPy, no SciPy, no external solvers).

## Features

### Linear Programming
- **Two-phase primal Simplex method** with exact rational arithmetic (`fractions.Fraction`) — no floating-point roundoff during pivoting.
- **Phase I** minimises the sum of artificial variables to find a feasible starting basis; **Phase II** optimises the original objective.
- **Bland's rule** (default) for anti-cycling, or **Dantzig's rule** (most-positive reduced cost) for speed.
- **Constraint types**: `<=`, `>=`, `=`.
- **Variable bounds**: non-negative (default), lower-bounded (shifted), upper-bounded (explicit constraint), free variables (split into `x⁺ − x⁻`), and flipped variables (`x = ub − y`).
- **Dual values** (shadow prices) and **reduced costs** extracted from the optimal tableau.
- **Unbounded** and **infeasible** detection.

### Mixed-Integer Programming
- **Branch-and-bound** with best-first search and incumbent pruning.
- Supports both pure-integer and mixed-integer problems.
- Tightens bounds at each branch node (floor/ceiling branching).

### File I/O
- **MPS format** reader and writer (fixed-column and free-format compatible).
- **JSON problem specification** for programmatic use.

### Analysis Tools
- **Sensitivity analysis**: objective coefficient ranges and RHS ranges via basis-change detection with binary search.

### CLI
- `solve` — solve an LP/MILP from JSON or MPS, with optional sensitivity analysis.
- `mps-info` — inspect an MPS file.
- `version` — print version.

## How It Works

### Tableau Construction

The `Tableau` class transforms an `LPProblem` into a standard simplex tableau:

1. **Variable transformations**:
   - Free variables `(−∞, +∞)` → split `x = x⁺ − x⁻`, both `≥ 0`.
   - Lower bound only `(−∞, ub]` → substitute `x = ub − y`, `y ≥ 0`.
   - Lower bound shift `x ≥ lb` → substitute `x' = x − lb`, `x' ≥ 0`.
   - Upper bounds `x ≤ ub` → explicit `≤` constraint row added.

2. **Constraint rows**: each constraint gets a slack (for `≤`), surplus + artificial (for `≥`), or artificial (for `=`). Negative-rhs rows are normalised by negating the entire row *before* fixing the basic variable's identity coefficient to +1.

3. **Initial basis**: slack variables (for `≤` with non-negative rhs) or artificial variables (for `≥`, `=`, and `≤` with negative rhs). All basic variables have coefficient +1 in their row (identity column).

### Phase I

Minimises `Σ artificials` (equivalently maximises `−Σ artificials`). The reduced costs are computed by pricing out the artificial basic variables against each non-basic column. If the optimal artificial sum is positive, the problem is **infeasible**. Otherwise, artificials are driven out of the basis (pivoting on non-artificial columns with nonzero row coefficients), and the original objective is restored by recomputing reduced costs against the feasible basis.

### Phase II

Standard primal simplex: at each iteration, select an entering variable (positive reduced cost), perform the ratio test to find the leaving variable (minimum ratio, unbounded if none), and pivot. Bland's rule prevents cycling by always selecting the smallest-index improving variable.

### Dual Extraction

For a `≤` constraint, the dual (shadow price) is `−reduced_cost(slack)`. For a `≥` constraint, it's `reduced_cost(surplus)`. For `=`, it's `−reduced_cost(artificial)`. For `min` problems (where costs are negated internally), duals are negated to match the original sense.

### Branch-and-Bound

The `MILPSolver` solves LP relaxations at each node. When a fractional integer variable is found, two child nodes are created with tightened bounds (`x ≤ floor` and `x ≥ ceil`). Best-first search explores the most promising node first. Pruning occurs when a relaxation bound is worse than the incumbent.

## Usage

### Python API

```python
from simplex import LPProblem, SimplexSolver, MILPSolver

# Define a linear program
lp = LPProblem(
    name="diet",
    objective="min",
    variables=("bread", "milk"),
    objective_coeffs={"bread": 2, "milk": 3},
    constraints=[
        {"coeffs": {"bread": 1, "milk": 3}, "relation": ">=", "rhs": 5, "name": "calories"},
        {"coeffs": {"bread": 2, "milk": 1}, "relation": ">=", "rhs": 4, "name": "vitamins"},
    ],
)

# Solve
result = SimplexSolver().solve(lp)
print(f"Status: {result.status.value}")
print(f"Objective: {result.objective_value}")
print(f"Solution: {result.solution}")
print(f"Duals: {result.duals}")

# Mixed-integer programming
milp = LPProblem(
    name="knapsack",
    objective="max",
    variables=("i1", "i2", "i3"),
    objective_coeffs={"i1": 60, "i2": 50, "i3": 70},
    constraints=[
        {"coeffs": {"i1": 5, "i2": 3, "i3": 4}, "relation": "<=", "rhs": 10, "name": "capacity"},
    ],
    bounds={"i1": (0, 1), "i2": (0, 1), "i3": (0, 1)},
    integer={"i1", "i2", "i3"},
)
result = MILPSolver().solve(milp)
```

### CLI

```bash
# Solve from JSON
python -m simplex.cli solve examples/diet.json --pretty

# Solve with sensitivity analysis
python -m simplex.cli solve examples/diet.json --pretty --sensitivity

# Solve MILP
python -m simplex.cli solve examples/knapsack.json --pretty

# Inspect MPS file
python -m simplex.cli mps-info examples/problem.mps
```

### JSON Problem Format

```json
{
  "name": "diet",
  "objective": "min",
  "variables": ["bread", "milk"],
  "objective_coeffs": {"bread": 2, "milk": 3},
  "constraints": [
    {"coeffs": {"bread": 1, "milk": 3}, "relation": ">=", "rhs": 5, "name": "calories"},
    {"coeffs": {"bread": 2, "milk": 1}, "relation": ">=", "rhs": 4, "name": "vitamins"}
  ],
  "bounds": {},
  "integer": []
}
```

## Examples

- `examples/diet.json` — Classic diet problem (minimise cost subject to nutrient minimums).
- `examples/knapsack.json` — 0/1 knapsack problem (MILP).

## Installation

```bash
cd simplex-solver
pip install -e .
```

## Testing

```bash
pytest tests/
```

## License

MIT