#!/usr/bin/env python3
"""
Example 3: Bipartite Matching and Assignment

Demonstrates:
  - Maximum bipartite matching (Hopcroft-Karp)
  - Minimum vertex cover (Kőnig's theorem)
  - Maximum independent set
  - Minimum-cost assignment (Hungarian algorithm)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from networkflow import BipartiteMatcher, AssignmentSolver

# === Bipartite Matching ===
# Job assignment: 4 workers, 4 jobs
# Worker 0 can do jobs 0, 1
# Worker 1 can do jobs 0, 2
# Worker 2 can do jobs 1, 3
# Worker 3 can do jobs 2, 3
print("=== Bipartite Matching ===")
matcher = BipartiteMatcher(4, 4)
for u, v in [(0,0),(0,1),(1,0),(1,2),(2,1),(2,3),(3,2),(3,3)]:
    matcher.add_edge(u, v)

size = matcher.match()
print(f"Maximum matching size: {size}")
print(f"Matching: {matcher.get_matching()}")

# Kőnig's theorem: min vertex cover
lc, rc = matcher.minimum_vertex_cover()
print(f"Minimum vertex cover: left={lc}, right={rc}")
print(f"Vertex cover size: {len(lc) + len(rc)} (should equal matching size)")

# Maximum independent set
li, ri = matcher.maximum_independent_set()
print(f"Maximum independent set: left={li}, right={ri}")

# === Assignment Problem ===
print("\n=== Assignment Problem (Hungarian Algorithm) ===")
# Cost matrix: 3 workers, 3 tasks
cost_matrix = [
    [4, 1, 3],  # Worker 0: task costs
    [2, 0, 5],  # Worker 1: task costs
    [3, 2, 2],  # Worker 2: task costs
]
solver = AssignmentSolver()
min_cost = solver.solve(cost_matrix)
print(f"Cost matrix: {cost_matrix}")
print(f"Minimum assignment cost: {min_cost}")
print(f"Assignment (worker → task): {solver.get_assignment()}")

# Maximum weight assignment
max_cost = AssignmentSolver.max_assignment(cost_matrix)
print(f"Maximum assignment cost: {max_cost}")