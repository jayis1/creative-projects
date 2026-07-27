# Solver Internals — Deep Dive

This document explains the inner workings of the KenKen solver and the
optimizations that make it efficient.

## Overview

The solver implements a **constraint satisfaction problem (CSP)** approach
with backtracking search augmented by several well-known techniques:

1. **Domain tracking** with row/column constraint propagation
2. **Minimum Remaining Values (MRV)** variable selection heuristic
3. **Naked-single propagation** (forced cell assignments)
4. **Cage feasibility pruning** (bounds checking for `+` and `*` cages)
5. **Full-domain snapshot/restore** for correct backtracking

## The CSP Formulation

The KenKen puzzle is modeled as a CSP where:

- **Variables**: Each cell `(r, c)` in the *n×n* grid.
- **Domains**: Each cell starts with the domain `D = {1, 2, ..., n}`.
- **Constraints**:
  - **Row uniqueness**: All cells in the same row must have different values.
  - **Column uniqueness**: All cells in the same column must have different values.
  - **Cage constraints**: For each cage, the values must combine via the
    cage's operator to produce the target.

## Algorithm Walkthrough

### Initialization

```
domains = { (r,c): {1, 2, ..., n} for all cells }
assignment = {}  # empty
```

### Backtracking Search

The main search loop (`_backtrack`) works as follows:

1. **Check termination**: If all cells are assigned, verify all cages are
   satisfied. If so, record the solution.

2. **MRV selection**: Find the unassigned cell with the fewest candidates.
   If any unassigned cell has zero candidates, backtrack immediately.

3. **Try each candidate**: For each value in the selected cell's domain:
   - Save a **complete snapshot** of all domains.
   - Assign the value and update domains (remove the value from the same
     row and column).
   - Run naked-single propagation.
   - Recurse. If a solution is found and we've reached `max_solutions`,
     return immediately.
   - **Restore all domains** from the snapshot.

### Naked-Single Propagation

The propagation phase (`_propagate`) runs in a loop:

**Phase 1**: For every assigned cell, remove its value from the domains of
all cells in the same row and column. If any domain becomes empty (for an
unassigned cell), return `False` (contradiction).

**Phase 2**: Find the first unassigned cell with exactly one candidate. Assign
it and loop back to Phase 1 to propagate this new assignment's constraints.

**Critical ordering**: Only ONE naked single is assigned per iteration. This
ensures its row/column constraints are fully propagated before the next
naked single is assigned, preventing incorrect domain reductions.

### Cage Feasibility Pruning

After assigning a value, the cage containing that cell is checked for
feasibility (`_cage_feasible`):

- **Sum cages (`+`)**: 
  - If `partial_sum + remaining_count > target` → infeasible (minimum
    remaining contribution is `remaining_count × 1`).
  - If `partial_sum + remaining_count × n < target` → infeasible (maximum
    remaining contribution is `remaining_count × n`).

- **Product cages (`*`)**:
  - If `partial_product > target` → infeasible.
  - If `partial_product × n^remaining < target` → infeasible.

- **Subtraction/Division cages (`-`, `/`)**: No early pruning is possible
  with partial assignments. The full permutation check is deferred until all
  cells are assigned.

### Full-Domain Snapshots

Before each branching step, a complete snapshot of all domains is saved:

```python
domain_snapshot = {k: frozenset(v) for k, v in domains.items()}
```

After the recursive call returns (or fails), all domains are restored:

```python
for k, v in domain_snapshot.items():
    domains[k] = set(v)
```

This is critical because propagation modifies domains across the entire grid
(not just the row/column of the assigned cell). A partial snapshot would
leave stale domain state after backtracking, causing missing solutions.

## Performance Characteristics

| Grid Size | Typical Nodes | Typical Backtracks | Generation Time |
|-----------|--------------|--------------------|-----------------|
| 3×3 | ~5 | ~1 | < 0.01s |
| 4×4 | ~10-30 | ~3-10 | < 0.05s |
| 5×5 | ~20-80 | ~5-20 | < 0.1s |
| 6×6 | ~50-200 | ~10-50 | < 0.5s |
| 7×7 | ~100-500 | ~20-100 | < 2s |

The MRV heuristic dramatically reduces the search space compared to naive
backtracking. For a 5×5 grid, naive backtracking might explore 5^25 ≈ 10^17
nodes, while MRV typically explores fewer than 100.

## Solution Counting

The `count_solutions()` method uses a separate backtracking function
(`_backtrack_count`) that increments a counter instead of storing solutions.
This avoids the memory cost of storing all solutions, making it practical to
count solutions even when the solution space is large.

An optional `limit` parameter stops counting once the limit is reached,
useful for uniqueness verification (limit=2).