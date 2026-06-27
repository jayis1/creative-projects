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

## Known Issues (Resolved)

The following bugs were identified during the Phase 3 bug hunt and fixed:

1. **Artificial variables re-entering basis in Phase II** — After Phase I drove artificials out of the basis, they could re-enter during Phase II (their reduced cost was positive under the restored objective), undoing Phase I's work and returning a trivially zero solution. **Fix**: Artificials are permanently barred from re-entering the basis in `_select_entering`.

2. **Dual sign error** — The shadow price for `<=` constraints was reported with the wrong sign (negative instead of positive). **Fix**: Dual is now correctly extracted as `-reduced_cost(slack)` for `<=`, `+reduced_cost(surplus)` for `>=`, and `-reduced_cost(artificial)` for `=`.

3. **Negative-rhs constraint handling** — Constraints with negative rhs after variable shifts would have their slack/surplus coefficient negated by a blanket "multiply row by -1" step, breaking the identity column and causing the solver to return infeasible solutions as optimal. **Fix**: Negative-rhs rows now use an artificial variable with the correct sign, and the entire row is negated *before* the identity coefficient is established, ensuring the basic variable always has coefficient +1.

4. **MILP `_apply_bounds` convoluted logic** — The bound-tightening code had dead, unreachable branches and a duplicate `return p` statement. **Fix**: Simplified to a clean max/min tightening.

5. **MILP `floor_v` computation** — The floor of fractional values used an ad-hoc expression that was incorrect for negative values. **Fix**: Replaced with `math.floor()`.

6. **MILP node_id mismatch in priority key** — The heap priority tuple used `self._node_counter + 1` which didn't match the actual node_id assigned by `_new_node`. **Fix**: Create nodes first, then push, so the priority key matches.

7. **Phase I obj_const not restored** — After Phase I, the objective constant was reset to `sum c_B * rhs[i]` without re-adding the construction-time variable-shift constant (`c·lb` for shifted vars, `c·ub` for flipped vars). This didn't affect the reported objective (which is recomputed from scratch) but made `obj_const` inconsistent. **Fix**: The shift constant is now saved before Phase I and re-added during restoration.

8. **MPS INTEND marker malformed** — When the last variable in the COLUMNS section was integer, the INTEND marker line was `MARKER 'INTEND'` without a column name field, which strict MPS parsers reject. **Fix**: The marker now includes the last variable's name in the column field.

9. **MPS RANGES L-row handling** — For L (≤) rows with RANGES, the code appended a `<=` constraint with `b + |r|` and then overwrote it with a `>=` constraint, resulting in only one constraint instead of two. **Fix**: Correctly generates both `a.x <= b` and `a.x >= b - |r|`.

10. **Dead code: `_frac_part`** — The `_frac_part` helper function in `integer.py` was unused and had incorrect behaviour for negative integers. **Fix**: Removed.

11. **Unused imports** — `Iterable`, `Sequence` in `simplex.py` and `Iterable` in `integer.py` were imported but never used. **Fix**: Removed.

## License

MIT