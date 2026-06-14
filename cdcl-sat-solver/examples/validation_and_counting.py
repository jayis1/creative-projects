#!/usr/bin/env python3
"""
Example: DIMACS validation and solution counting.

Demonstrates validating DIMACS input and counting
satisfying assignments for small instances.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from cdcl_sat import Solver
from cdcl_sat.utils import validate_dimacs, count_satisfying_assignments

# Validate a DIMACS string
valid_dimacs = """p cnf 3 2
1 2 0
-1 3 0
"""

print("Validating DIMACS string:")
issues = validate_dimacs(valid_dimacs)
if issues:
    print(f"  Issues found: {issues}")
else:
    print("  No issues found. DIMACS is valid.")

# Validate an invalid DIMACS string
invalid_dimacs = """p cnf 3 5
1 -1 0
1 2 0
"""

print("\nValidating invalid DIMACS string:")
issues = validate_dimacs(invalid_dimacs)
for issue in issues:
    print(f"  - {issue}")

# Count satisfying assignments for a small formula
# (x1 ∨ x2) has 3 satisfying assignments: {T,F}, {F,T}, {T,T}
print("\nCounting satisfying assignments:")
clauses = [[1, 2]]
count = count_satisfying_assignments(2, clauses)
print(f"  (x1 ∨ x2): {count} satisfying assignments")

# (x1) ∧ (-x1) has 0 satisfying assignments
clauses_unsat = [[1], [-1]]
count_unsat = count_satisfying_assignments(1, clauses_unsat)
print(f"  (x1) ∧ (¬x1): {count_unsat} satisfying assignments")