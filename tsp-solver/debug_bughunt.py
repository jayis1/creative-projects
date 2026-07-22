#!/usr/bin/env python3
"""Debug or_opt and B&B."""
from tsp_solver.instance import generate_instance
from tsp_solver.heuristics import nearest_neighbor
from tsp_solver.local_search import or_opt, two_opt
from tsp_solver.exact import held_karp, branch_and_bound
from tsp_solver.tour import Tour

# Debug or_opt
print("=== or_opt debug ===")
inst = generate_instance(12, seed=42)
nn = nearest_neighbor(inst)
print(f"NN tour: {list(nn.order)}, length={nn.length}")

# Try 2-opt first to see what optimal looks like
t2 = two_opt(inst, nn)
print(f"2-opt: {list(t2.order)}, length={t2.length}")

# Now try or_opt on the NN tour
to = or_opt(inst, nn, max_iter=100)
print(f"or_opt: {list(to.order)}, length={to.length}")

# Verify the or_opt result is a valid permutation
print(f"Valid perm: {sorted(to.order) == list(range(inst.n))}")

# Let's try or_opt on an already-good tour
to2 = or_opt(inst, t2, max_iter=100)
print(f"or_opt on 2-opt: {list(to2.order)}, length={to2.length}")
print(f"Valid perm: {sorted(to2.order) == list(range(inst.n))}")

# Debug B&B seed=6
print("\n=== B&B debug seed=6 ===")
inst6 = generate_instance(8, seed=6)
hk = held_karp(inst6)
bb = branch_and_bound(inst6)
print(f"HK: {list(hk.order)}, length={hk.length}")
print(f"B&B: {list(bb.order)}, length={bb.length}")

# Check if the HK tour is valid
print(f"HK valid: {sorted(hk.order) == list(range(inst6.n))}")
print(f"B&B valid: {sorted(bb.order) == list(range(inst6.n))}")

# Verify HK length
print(f"HK verified: {inst6.tour_length(list(hk.order))}")
print(f"B&B verified: {inst6.tour_length(list(bb.order))}")