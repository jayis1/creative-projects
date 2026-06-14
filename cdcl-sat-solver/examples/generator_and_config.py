#!/usr/bin/env python3
"""
Example: Using the CNF generator and solver configuration.

Demonstrates generating benchmark instances, configuring the solver,
and solving with preprocessing.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from cdcl_sat import Solver, SolverConfig
from cdcl_sat.generator import generate_php, generate_random_cnf

# Generate a pigeonhole instance
num_vars, clauses = generate_php(4, 3)
print(f"Generated PHP(4,3): {num_vars} variables, {len(clauses)} clauses")

# Convert to DIMACS and solve
dimacs_lines = [f"p cnf {num_vars} {len(clauses)}"]
for clause in clauses:
    dimacs_lines.append(" ".join(str(l) for l in clause) + " 0")
dimacs = "\n".join(dimacs_lines)

# Use configuration
config = SolverConfig(
    restart_strategy="luby",
    verbose=1,
    var_decay=0.95,
)

solver = Solver.from_dimacs(dimacs)
config.apply_to_solver(solver)

print(f"Solving with config: restart={config.restart_strategy}, verbose={config.verbose}")
result = solver.solve(time_limit=30)
print(f"Result: {'SAT' if result else 'UNSAT' if result is False else 'UNKNOWN'}")
print(f"Stats: {solver.get_stats()}")

# Now generate a random 3-SAT instance and solve with preprocessing
print("\n--- Random 3-SAT ---")
num_vars, clauses = generate_random_cnf(30, 120, k=3, seed=42)
dimacs_lines = [f"p cnf {num_vars} {len(clauses)}"]
for clause in clauses:
    dimacs_lines.append(" ".join(str(l) for l in clause) + " 0")
dimacs = "\n".join(dimacs_lines)

solver2 = Solver.from_dimacs(dimacs)
solver2.verbose = 1
print(f"Before preprocessing: {solver2.num_vars} vars, {len(solver2.clauses)} clauses")

preprocess_ok = solver2.preprocess()
print(f"After preprocessing: ok={preprocess_ok}")

result2 = solver2.solve(time_limit=10)
print(f"Result: {'SAT' if result2 else 'UNSAT' if result2 is False else 'UNKNOWN'}")
print(f"Stats: {solver2.get_stats()}")