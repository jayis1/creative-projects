#!/usr/bin/env python3
"""Debug B&B seed=6 - trace DFS."""
from tsp_solver.instance import generate_instance
from tsp_solver.exact import held_karp, _nn_upper_bound, _mst_cost
import math

inst = generate_instance(8, seed=6)
hk = held_karp(inst)
matrix = inst.matrix
n = inst.n
upper = _nn_upper_bound(inst)
print(f"Optimal: {hk.length}, Upper: {upper}")

best_cost = [upper]
best_order = []
visited = [False] * n
visited[0] = True
path = [0]
call_count = [0]

def _lower_bound(cur_path):
    cur = cur_path[-1]
    unvisited = [j for j in range(n) if not visited[j]]
    if not unvisited:
        return sum(matrix[a, b] for a, b in zip(cur_path, cur_path[1:])) + matrix[cur, 0]
    path_cost = sum(matrix[a, b] for a, b in zip(cur_path, cur_path[1:]))
    min_to_unvisited = min(matrix[cur, j] for j in unvisited)
    min_to_start = min(matrix[j, 0] for j in unvisited)
    if len(unvisited) <= 1:
        mst_cost = 0.0
    else:
        mst_cost = _mst_cost(matrix, unvisited)
    return path_cost + min_to_unvisited + mst_cost + min_to_start

def _dfs(cur, cost, depth):
    call_count[0] += 1
    if cost >= best_cost[0]:
        return
    if depth == n:
        total = cost + matrix[cur, 0]
        if total < best_cost[0]:
            best_cost[0] = total
            best_order[:] = list(path)
            print(f"  New best: {total}, order={list(path)}")
        return
    lb = _lower_bound(path)
    if lb >= best_cost[0]:
        return
    candidates = sorted(
        ((matrix[cur, j], j) for j in range(n) if not visited[j]),
    )
    for dist, j in candidates:
        visited[j] = True
        path.append(j)
        _dfs(j, cost + dist, depth + 1)
        path.pop()
        visited[j] = False

_dfs(0, 0.0, 1)
print(f"DFS calls: {call_count[0]}")
print(f"Best: {best_cost[0]}, order={best_order}")
print(f"Match optimal: {abs(best_cost[0] - hk.length) < 1e-6}")