#!/usr/bin/env python3
"""Debug 2-opt wrap-around bug."""
from tsp_solver.instance import generate_instance
from tsp_solver.heuristics import nearest_neighbor
from tsp_solver.local_search import two_opt

inst = generate_instance(12, seed=42)
nn = nearest_neighbor(inst)
print(f"NN: {list(nn.order)}, length={nn.length}")

# Let's manually trace 2-opt
order = list(nn.order)
n = len(order)
matrix = inst.matrix

# Check all 2-opt swaps (non-wrap)
best_delta = 0
best_swap = None
for i in range(n - 1):
    a = order[i]
    b = order[i + 1]
    for j in range(i + 2, n - 1):
        c = order[j]
        d = order[j + 1]
        delta = (matrix[a, c] + matrix[b, d]) - (matrix[a, b] + matrix[c, d])
        if delta < best_delta:
            best_delta = delta
            best_swap = (i, j)

print(f"Best non-wrap swap: {best_swap}, delta={best_delta}")

# Now check wrap-around
a = order[-1]
b = order[0]
print(f"Wrap edge: ({a},{b}) = {matrix[a, b]}")
for j in range(1, n - 2):
    c = order[j]
    d = order[j + 1]
    delta = (matrix[a, c] + matrix[b, d]) - (matrix[a, b] + matrix[c, d])
    if delta < 0:
        print(f"Wrap swap at j={j}: c={c}, d={d}, delta={delta}")
        # What does the current code do?
        # order[j + 1 :] = order[j + 1 :][::-1]
        # idx0 = order.index(order[0])
        # order = order[idx0:] + order[:idx0]
        test_order = list(order)
        test_order[j + 1 :] = test_order[j + 1 :][::-1]
        print(f"  After reverse: {test_order}")
        idx0 = test_order.index(order[0])
        test_order = test_order[idx0:] + test_order[:idx0]
        print(f"  After rotate: {test_order}")
        actual_len = inst.tour_length(test_order)
        print(f"  Actual length: {actual_len} (expected {inst.tour_length(order) + delta})")

# Run actual 2-opt
t = two_opt(inst, nn, max_iter=1)
print(f"\n2-opt (1 iter): {list(t.order)}, length={t.length}")
t = two_opt(inst, nn, max_iter=5)
print(f"2-opt (5 iter): {list(t.order)}, length={t.length}")