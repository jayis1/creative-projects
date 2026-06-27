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
- **Iteration counting**: the solver reports the total number of simplex pivots performed.
- **Problem validation**: `LPProblem.validate()` checks for unknown variables, inconsistent bounds, duplicate names, and missing fields.

### Mixed-Integer Programming
- **Branch-and-bound** with best-first search and incumbent pruning.
- Supports both pure-integer and mixed-integer problems.
- Tightens bounds at each branch node (floor/ceiling branching).
- Correctly handles infeasible subproblems (negative-rhs normalisation ensures Phase I detects infeasibility).

### File I/O
- **MPS format** reader and writer (fixed-column and free-format compatible).
- **JSON problem specification** for programmatic use.
- **Round-trip** support: write to MPS and read back produces an equivalent problem.

### Analysis Tools
- **Sensitivity analysis**: objective coefficient ranges and RHS ranges via basis-change detection with binary search.

### CLI
- `solve` — solve an LP/MILP from JSON or MPS, with optional sensitivity analysis.
- `validate` — validate a problem file and report issues.
- `mps-info` — inspect an MPS file.
- `version` — print version.
- Supports `python -m simplex` as an entry point.

## How It Works

### Tableau Construction

The `Tableau` class transforms an `LPProblem` into a standard simplex tableau:

1. **Variable transformations**:
   - Free variables `(−∞, +∞)` → split `x = x⁺ − x⁻`, both `≥ 0`.
   - Lower bound only `(−∞, ub]` → substitute `x = ub − y`, `y ≥ 0`.
   - Lower bound shift `x ≥ lb` → substitute `x' = x − lb`, `x' ≥ 0`.
   - Upper bounds `x ≤ ub` → explicit `≤` constraint row added.

2. **Constraint rows**: each constraint gets a slack (for `≤`), surplus + artificial (for `≥`), or artificial (for `=`). **Negative-rhs rows** are normalised by negating the entire row *before* fixing the basic variable's identity coefficient to +1, ensuring the initial basis is always feasible and the identity column property holds.

3. **Initial basis**: slack variables (for `≤` with non-negative rhs) or artificial variables (for `≥`, `=`, and `≤` with negative rhs). All basic variables have coefficient +1 in their row (identity column), and all rhs values are non-negative.

### Phase I

Minimises `Σ artificials` (equivalently maximises `−Σ artificials`). The reduced costs are computed by pricing out the artificial basic variables against each non-basic column. If the optimal artificial sum is positive, the problem is **infeasible**. Otherwise, artificials are driven out of the basis (pivoting on non-artificial columns with nonzero row coefficients), and the original objective is restored by recomputing reduced costs against the feasible basis. Artificial variables are permanently barred from re-entering the basis in Phase II.

### Phase II

Standard primal simplex: at each iteration, select an entering variable (positive reduced cost), perform the ratio test to find the leaving variable (minimum ratio, unbounded if none), and pivot. Bland's rule prevents cycling by always selecting the smallest-index improving variable. The pivot count is tracked and reported in the result.

### Dual Extraction

For a `≤` constraint, the dual (shadow price) is `−reduced_cost(slack)`. For a `≥` constraint, it's `reduced_cost(surplus)`. For `=`, it's `−reduced_cost(artificial)`. For `min` problems (where costs are negated internally), duals are negated to match the original sense.

### Branch-and-Bound

The `MILPSolver` solves LP relaxations at each node. When a fractional integer variable is found, two child nodes are created with tightened bounds (`x ≤ floor` and `x ≥ ceil`). Best-first search explores the most promising node first (priority queue keyed by relaxation objective). Pruning occurs when a relaxation bound is worse than the incumbent. The solver correctly detects infeasible subproblems via Phase I.

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

# Validate before solving
errors = lp.validate()
assert not errors

# Solve
result = SimplexSolver().solve(lp)
print(f"Status: {result.status.value}")
print(f"Objective: {result.objective_value}")
print(f"Solution: {result.solution}")
print(f"Duals: {result.duals}")
print(f"Pivots: {result.iterations}")

# Mixed-integer programming (0/1 knapsack)
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
# Solve from JSON with pretty output
python -m simplex solve examples/diet.json --pretty

# Solve with sensitivity analysis
python -m simplex solve examples/diet.json --pretty --sensitivity

# Solve MILP
python -m simplex solve examples/knapsack.json --pretty

# Validate a problem file
python -m simplex validate examples/production.json

# Inspect MPS file
python -m simplex mps-info examples/problem.mps

# Use Dantzig's rule
python -m simplex solve examples/production.json --pretty --dantzig
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
- `examples/knapsack.json` — 0/1 knapsack problem (MILP, 5 items).
- `examples/production.json` — Production planning (3 products, 3 resources).
- `examples/transport.json` — Transportation problem (2 suppliers, 3 customers).

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