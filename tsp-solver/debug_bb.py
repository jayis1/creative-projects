#!/usr/bin/env python3
"""Debug B&B seed=6."""
from tsp_solver.instance import generate_instance
from tsp_solver.exact import held_karp, branch_and_bound, _nn_upper_bound, _mst_cost
import math

inst = generate_instance(8, seed=6)
hk = held_karp(inst)
print(f"HK optimal: {hk.length}")

nn = _nn_upper_bound(inst)
print(f"NN upper bound: {nn}")

matrix = inst.matrix
n = inst.n

# Check lower bound at root (path=[0], only city 0 visited)
visited = [False] * n
visited[0] = True
path = [0]

# Reproduce the lower bound
cur = path[-1]
unvisited = [j for j in range(n) if not visited[j]]
path_cost = sum(matrix[a, b] for a, b in zip(path, path[1:]))
min_to_unvisited = min(matrix[cur, j] for j in unvisited)
min_to_start = min(matrix[j, 0] for j in unvisited)
mst = _mst_cost(matrix, unvisited)
lb = path_cost + min_to_unvisited + mst + min_to_start
print(f"Root LB: {lb}")
print(f"  path_cost={path_cost}, min_to_unvisited={min_to_unvisited}, mst={mst}, min_to_start={min_to_start}")
print(f"  Optimal={hk.length}, LB <= optimal? {lb <= hk.length + 1e-9}")

# Check if LB is valid for the optimal completion
# The optimal tour from city 0 visits all unvisited, returns to 0.
# So the LB should be <= hk.length
if lb > hk.length + 1e-9:
    print("  BUG: LB exceeds optimal! The bound is invalid.")