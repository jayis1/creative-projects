#!/usr/bin/env python3
"""Debug or_opt delta calculation."""
from tsp_solver.instance import generate_instance
from tsp_solver.heuristics import nearest_neighbor

inst = generate_instance(12, seed=42)
nn = nearest_neighbor(inst)
order = list(nn.order)
n = len(order)
matrix = inst.matrix

print(f"NN: {order}, len={inst.tour_length(order)}")

# Try to find a valid or-opt move manually
# Try seg_len=1, i=0 (move city 0)
seg_len = 1
i = 0
a_prev = order[(i - 1) % n]  # order[11] = 10
a = order[i]  # 0
b = order[i + seg_len - 1]  # 0
b_next = order[(i + seg_len) % n]  # order[1] = 9
removed_cost = matrix[a_prev, a] + matrix[b, b_next] - matrix[a_prev, b_next]
seg = order[i : i + seg_len]  # [0]
print(f"\nseg_len=1, i=0: seg={seg}, a_prev={a_prev}, a={a}, b={b}, b_next={b_next}")
print(f"  removed_cost = {matrix[a_prev, a]} + {matrix[b, b_next]} - {matrix[a_prev, b_next]} = {removed_cost}")

# Try inserting at j=5
j = 5
c = order[j]  # order[5] = 1
d = order[(j + 1) % n]  # order[6] = 6
insert_cost = matrix[c, a] + matrix[b, d] - matrix[c, d]
delta = insert_cost + removed_cost
print(f"  j=5: c={c}, d={d}, insert_cost={matrix[c, a]}+{matrix[b, d]}-{matrix[c, d]}={insert_cost}, delta={delta}")

# Verify: what would the actual new tour look like?
new_order = order[:i] + order[i + seg_len:]  # remove seg
print(f"  After removal: {new_order}")
if j >= i + seg_len:
    insert_j = j - seg_len
else:
    insert_j = j
print(f"  insert_j={insert_j}")
new_order2 = new_order[:insert_j + 1] + seg + new_order[insert_j + 1:]
print(f"  After insert: {new_order2}")
actual_len = inst.tour_length(new_order2)
expected_len = inst.tour_length(order) + delta
print(f"  Actual len: {actual_len}, Expected: {expected_len}, Match: {abs(actual_len - expected_len) < 1e-6}")

# Now let's find all valid improving moves
print("\n=== All improving moves ===")
for seg_len in (1, 2, 3):
    for i in range(n):
        if i + seg_len > n:
            continue
        a_prev = order[(i - 1) % n]
        a = order[i]
        b = order[i + seg_len - 1]
        b_next = order[(i + seg_len) % n]
        removed_cost = matrix[a_prev, a] + matrix[b, b_next] - matrix[a_prev, b_next]
        seg = order[i : i + seg_len]
        seg_set = set(seg)
        for j in range(n):
            if j == i or j == (i - 1) % n:
                continue
            c = order[j]
            d = order[(j + 1) % n]
            if c in seg_set or d in seg_set:
                continue
            insert_cost = matrix[c, a] + matrix[b, d] - matrix[c, d]
            delta = insert_cost + removed_cost
            if delta < -1e-12:
                # Verify
                new_order = order[:i] + order[i + seg_len:]
                if j >= i + seg_len:
                    insert_j = j - seg_len
                else:
                    insert_j = j
                new_order = new_order[:insert_j + 1] + seg + new_order[insert_j + 1:]
                actual_len = inst.tour_length(new_order)
                expected_len = inst.tour_length(order) + delta
                valid = abs(actual_len - expected_len) < 1e-6
                improves = actual_len < inst.tour_length(order)
                print(f"  seg_len={seg_len}, i={i}, j={j}: delta={delta:.0f}, actual={actual_len:.0f}, expected={expected_len:.0f}, valid={valid}, improves={improves}")