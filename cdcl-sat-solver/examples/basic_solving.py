#!/usr/bin/env python3
"""
Example: Basic SAT solving with the CDCL SAT Solver.

Demonstrates creating a solver from a DIMACS string,
solving, and extracting the model.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from cdcl_sat import Solver

# A simple SAT instance: (x1 ∨ x2) ∧ (¬x1 ∨ x2) ∧ (¬x2 ∨ x3)
dimacs = """p cnf 3 3
1 2 0
-1 2 0
-2 3 0
"""

solver = Solver.from_dimacs(dimacs)
result = solver.solve()

if result is True:
    model = solver.get_model()
    print(f"Result: SAT")
    print(f"Model: {model}")
    print(f"Verified: {solver.verify_model(model)}")
    print(f"Stats: {solver.get_stats()}")
elif result is False:
    print("Result: UNSAT")
else:
    print("Result: UNKNOWN (timeout)")