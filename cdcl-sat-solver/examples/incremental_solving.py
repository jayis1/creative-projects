#!/usr/bin/env python3
"""
Example: Incremental SAT solving with assumptions.

Demonstrates using assumptions to solve the same formula
under different constraints, enabling incremental solving.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from cdcl_sat import Solver

# Formula: (x1 ∨ x2) — this is satisfiable on its own
dimacs = "p cnf 2 1\n1 2 0\n"

# Solve without assumptions — should be SAT
solver = Solver.from_dimacs(dimacs)
result = solver.solve()
print(f"Without assumptions: {result}")
if result:
    print(f"  Model: {solver.get_model()}")

# Solve assuming both x1=False and x2=False — should be UNSAT
solver2 = Solver.from_dimacs(dimacs)
result2 = solver2.solve(assumptions=[-1, -2])
print(f"With assumptions [-1, -2]: {result2}")
if not result2:
    print(f"  Failed assumptions: {solver2.get_failed_assumptions()}")

# Solve assuming x1=True — should be SAT
solver3 = Solver.from_dimacs(dimacs)
result3 = solver3.solve(assumptions=[1])
print(f"With assumptions [1]: {result3}")
if result3:
    print(f"  Model: {solver3.get_model()}")