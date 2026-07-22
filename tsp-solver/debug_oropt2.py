#!/usr/bin/env python3
"""Debug specific or_opt case."""
from tsp_solver.instance import generate_instance
from tsp_solver.heuristics import nearest_neighbor

inst = generate_instance(12, seed=42)
nn = nearest_neighbor(inst)
order = list(nn.order)
n = len(order)
matrix = inst.matrix

print(f"order: {order}, n={n}")

# Case: seg_len=2, i=2, j=11
seg_len = 2
i = 2
j = 11
seg = order[i : i + seg_len]
print(f"seg={seg}")
a_prev = order[(i - 1) % n]
a = order[i]
b = order[i + seg_len - 1]
b_next = order[(i + seg_len) % n]
removed_cost = matrix[a_prev, a] + matrix[b, b_next] - matrix[a_prev, b_next]
print(f"a_prev={a_prev}, a={a}, b={b}, b_next={b_next}")
print(f"removed_cost = {matrix[a_prev, a]} + {matrix[b, b_next]} - {matrix[a_prev, b_next]} = {removed_cost}")

c = order[j]
d = order[(j + 1) % n]
print(f"c={c}, d={d}")
print(f"c in seg? {c in seg}, d in seg? {d in seg}")

insert_cost = matrix[c, a] + matrix[b, d] - matrix[c, d]
delta = insert_cost + removed_cost
print(f"insert_cost = {matrix[c, a]} + {matrix[b, d]} - {matrix[c, d]} = {insert_cost}")
print(f"delta = {delta}")

# Now perform the move
new_order = order[:i] + order[i + seg_len:]
print(f"After removal: {new_order} (len={len(new_order)})")

# j=11, i=2, seg_len=2, so j >= i+seg_len (11 >= 4)
insert_j = j - seg_len  # 11 - 2 = 9
print(f"insert_j = {insert_j}")
print(f"new_order[insert_j] = {new_order[insert_j]} (should be c={c})")
print(f"new_order[insert_j+1] = {new_order[insert_j+1] if insert_j+1 < len(new_order) else 'N/A'} (should be d={d})")

# But wait: d = order[(j+1) % n] = order[12 % 12] = order[0] = 0
# After removal, order[0] is still at position 0 (since i=2 > 0).
# new_order has 10 elements (12 - 2 = 10).
# insert_j = 9, so we insert after new_order[9] and before new_order[10 % 10] = new_order[0]
# new_order[9] = ?
print(f"new_order[9] = {new_order[9]}")
print(f"new_order[0] = {new_order[0]}")
# So we're inserting between new_order[9] and new_order[0] (wrap-around)
# But the delta was computed for inserting between c=order[11]=10 and d=order[0]=0
# After removal, new_order[9] should be order[11] (since positions 2,3 are removed)
# order[11] = 10 = c ✓
# new_order[0] = order[0] = 0 = d ✓
# So the insertion IS between c and d. Let's verify the length.

final = new_order[:insert_j + 1] + seg + new_order[insert_j + 1:]
print(f"Final: {final}")
actual_len = inst.tour_length(final)
print(f"Actual len: {actual_len}")
print(f"Expected: {inst.tour_length(order) + delta} = {inst.tour_length(order)} + {delta}")
print(f"Match: {abs(actual_len - (inst.tour_length(order) + delta)) < 1e-6}")

# Let's compute manually:
# Original tour: 0-9-3-4-11-1-6-5-8-7-2-10-0
# Remove seg [3,4] at positions 2,3: 0-9-11-1-6-5-8-7-2-10-0
# Insert [3,4] between 10 and 0: 0-9-11-1-6-5-8-7-2-10-3-4-0
# But wait, inserting at position 9 means after new_order[9]=10, before new_order[0]=0
# But new_order is [0,9,11,1,6,5,8,7,2,10]
# Insert at position 9+1=10: [0,9,11,1,6,5,8,7,2,10] + [3,4] = [0,9,11,1,6,5,8,7,2,10,3,4]
print(f"\nManual check:")
manual = [0,9,11,1,6,5,8,7,2,10,3,4]
print(f"Manual: {manual}, len={inst.tour_length(manual)}")
# The tour is: 0-9-11-1-6-5-8-7-2-10-3-4-0
# Edges: 0-9, 9-11, 11-1, 1-6, 6-5, 5-8, 8-7, 7-2, 2-10, 10-3, 3-4, 4-0
# But the delta assumed: remove 9-3, 4-11, add 9-11 (savings: 9-3+4-11-9-11)
# Then insert: remove 10-0, add 10-3, 4-0
# Total change: (9-3+4-11-9-11) + (10-3+4-0-10-0)
# = (matrix[9,3]+matrix[4,11]-matrix[9,11]) + (matrix[10,3]+matrix[4,0]-matrix[10,0])
# Let's check:
edge_change = (matrix[9,3] + matrix[4,11] - matrix[9,11]) + (matrix[10,3] + matrix[4,0] - matrix[10,0])
print(f"Edge change: {edge_change}")
print(f"delta was: {delta}")
# They should match... but the issue is:
# removed_cost = matrix[a_prev,a] + matrix[b,b_next] - matrix[a_prev,b_next]
#              = matrix[9,3] + matrix[4,11] - matrix[9,11]  (a_prev=9, a=3, b=4, b_next=11)
# insert_cost = matrix[c,a] + matrix[b,d] - matrix[c,d]
#             = matrix[10,3] + matrix[4,0] - matrix[10,0]  (c=10, a=3, b=4, d=0)
# delta = removed_cost + insert_cost
#       = (matrix[9,3]+matrix[4,11]-matrix[9,11]) + (matrix[10,3]+matrix[4,0]-matrix[10,0])
print(f"removed_cost = {matrix[9,3]}+{matrix[4,11]}-{matrix[9,11]} = {matrix[9,3]+matrix[4,11]-matrix[9,11]}")
print(f"insert_cost = {matrix[10,3]}+{matrix[4,0]}-{matrix[10,0]} = {matrix[10,3]+matrix[4,0]-matrix[10,0]}")
print(f"delta = {matrix[9,3]+matrix[4,11]-matrix[9,11] + matrix[10,3]+matrix[4,0]-matrix[10,0]}")
print(f"Actual delta = {inst.tour_length(manual) - inst.tour_length(order)}")