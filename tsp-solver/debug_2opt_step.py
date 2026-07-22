#!/usr/bin/env python3
"""Debug 2-opt step by step."""
from tsp_solver.instance import generate_instance
from tsp_solver.heuristics import nearest_neighbor

inst = generate_instance(12, seed=42)
nn = nearest_neighbor(inst)
order = list(nn.order)
n = len(order)
matrix = inst.matrix

print(f"Start: {order}, len={inst.tour_length(order)}")

# Reproduce the 2-opt loop exactly
improved = True
iters = 0
while improved and iters < 100:
    improved = False
    iters += 1
    for i in range(n - 1):
        a = order[i]
        b = order[i + 1]
        for j in range(i + 2, n - 1):
            c = order[j]
            d = order[j + 1]
            delta = (matrix[a, c] + matrix[b, d]) - (matrix[a, b] + matrix[c, d])
            if delta < -1e-12:
                order[i + 1 : j + 1] = order[i + 1 : j + 1][::-1]
                improved = True
                print(f"  Swap i={i},j={j}: delta={delta:.0f}, new_len={inst.tour_length(order):.0f}, order={order}")
    # wrap-around
    a = order[-1]
    b = order[0]
    for j in range(1, n - 2):
        c = order[j]
        d = order[j + 1]
        delta = (matrix[a, c] + matrix[b, d]) - (matrix[a, b] + matrix[c, d])
        if delta < -1e-12:
            order[j + 1 :] = order[j + 1 :][::-1]
            idx0 = order.index(order[0])
            order = order[idx0:] + order[:idx0]
            improved = True
            print(f"  Wrap swap j={j}: delta={delta:.0f}, new_len={inst.tour_length(order):.0f}, order={order}")

print(f"Final: {order}, len={inst.tour_length(order)}")