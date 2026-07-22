#!/usr/bin/env python3
from tsp_solver.instance import generate_instance
from tsp_solver.heuristics import nearest_neighbor

inst = generate_instance(12, seed=42)
nn = nearest_neighbor(inst)
matrix = inst.matrix

# Original edges and their costs
orig_edges = [(0,9),(9,3),(3,4),(4,11),(11,1),(1,6),(6,5),(5,8),(8,7),(7,2),(2,10),(10,0)]
orig_cost = sum(matrix[a,b] for a,b in orig_edges)
print(f"Original cost: {orig_cost}")

# Final edges
final_edges = [(0,9),(9,11),(11,1),(1,6),(6,5),(5,8),(8,7),(7,2),(2,10),(10,3),(3,4),(4,0)]
final_cost = sum(matrix[a,b] for a,b in final_edges)
print(f"Final cost: {final_cost}")

# Removed edges: 9-3, 4-11, 10-0
# Added edges: 9-11, 10-3, 4-0
removed = matrix[9,3] + matrix[4,11] + matrix[10,0]
added = matrix[9,11] + matrix[10,3] + matrix[4,0]
print(f"Removed: {removed}, Added: {added}")
print(f"Delta: {added - removed}")

# Now check our formula
removed_cost = matrix[9,3] + matrix[4,11] - matrix[9,11]
insert_cost = matrix[10,3] + matrix[4,0] - matrix[10,0]
print(f"removed_cost: {removed_cost}, insert_cost: {insert_cost}")
print(f"Formula delta: {removed_cost + insert_cost}")

# These should be the same...
# removed_cost = 9-3 + 4-11 - 9-11  (the net of removing segment and reconnecting)
# insert_cost = 10-3 + 4-0 - 10-0  (the net of inserting segment)
# But the ACTUAL delta is:
# (9-11 + 10-3 + 4-0) - (9-3 + 4-11 + 10-0)
# = 9-11 + 10-3 + 4-0 - 9-3 - 4-11 - 10-0
# = (9-3 + 4-11 - 9-11) negated + (10-3 + 4-0 - 10-0)
# Wait no:
# = -(9-3) - (4-11) + (9-11) + (10-3) + (4-0) - (10-0)
# = -(9-3 + 4-11 - 9-11) + (10-3 + 4-0 - 10-0)
# = -removed_cost + insert_cost
# NOT removed_cost + insert_cost!

print(f"\n-removed_cost + insert_cost = {-removed_cost + insert_cost}")
print(f"This matches actual delta: {final_cost - orig_cost}")

# The bug is in the sign of removed_cost!
# removed_cost should be the SAVINGS from removing (negative means it costs more to remove)
# But delta = -removed_cost + insert_cost when removed_cost is defined as
# (edges removed) - (edge added to close gap)
# Because: removing the segment means we GAIN -removed_cost (we save removed_cost)
# Actually no:
# removed_cost = matrix[a_prev,a] + matrix[b,b_next] - matrix[a_prev,b_next]
# This is the COST CHANGE of removing: we remove (a_prev,a) and (b,b_next),
# add (a_prev,b_next). If this is negative, removal is beneficial.
# insert_cost = matrix[c,a] + matrix[b,d] - matrix[c,d]
# This is the COST CHANGE of inserting: we add (c,a) and (b,d), remove (c,d).
# Total delta = removed_cost + insert_cost
# But the actual change is:
# added - removed = (9-11 + 10-3 + 4-0) - (9-3 + 4-11 + 10-0)
# removed_cost = (9-3 + 4-11) - (9-11) = 9-3 + 4-11 - 9-11
# insert_cost = (10-3 + 4-0) - (10-0) = 10-3 + 4-0 - 10-0
# removed_cost + insert_cost = 9-3 + 4-11 - 9-11 + 10-3 + 4-0 - 10-0
# = -(9-11) + (9-3) + (4-11) + (10-3) + (4-0) - (10-0)
# But actual delta = (9-11) - (9-3) - (4-11) + (10-3) + (4-0) - (10-0)
# = -(9-3 + 4-11 - 9-11) + (10-3 + 4-0 - 10-0)
# = -removed_cost + insert_cost

# So the bug is: delta should be -removed_cost + insert_cost, NOT removed_cost + insert_cost!
# Wait, let me recheck. When we "remove" the segment, we:
#   - Remove edges (a_prev, a) and (b, b_next)  → cost decreases by their sum
#   - Add edge (a_prev, b_next)  → cost increases by that
# So the net change from removal = -(a_prev,a) - (b,b_next) + (a_prev,b_next)
#                                = -[(a_prev,a) + (b,b_next) - (a_prev,b_next)]
#                                = -removed_cost
# Then when we "insert" the segment between c and d:
#   - Remove edge (c, d)  → cost decreases by (c,d)
#   - Add edges (c, a) and (b, d)  → cost increases by (c,a) + (b,d)
# So the net change from insertion = (c,a) + (b,d) - (c,d) = insert_cost
# Total delta = -removed_cost + insert_cost

print(f"\nCORRECT delta = -removed_cost + insert_cost = {-removed_cost + insert_cost}")
print(f"Actual delta = {final_cost - orig_cost}")