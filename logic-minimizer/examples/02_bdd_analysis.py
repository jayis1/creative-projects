"""
Example 2: BDD construction and analysis.

Shows how to build a Reduced Ordered Binary Decision Diagram (ROBDD) from
a boolean function, count satisfying assignments, and extract SOP covers.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from logicmin import BooleanFunction, BDDManager, build_bdd, bdd_sop, var_names, cube_covers

# f(A,B,C) = Σm(1,3,5,7) = C
f = BooleanFunction(n_vars=3, minterms=[1, 3, 5, 7])
print(f"Function: f = C (minterms 1,3,5,7)")
print(f"  n_vars={f.n_vars}, minterms={sorted(f.minterms)}")
print()

# Build BDD
mgr, root = build_bdd(f)
print(f"BDD node count: {mgr.node_count(root)}")
print(f"Satisfying assignments: {mgr.count_satisfying(root)}")
print()

# Extract SOP from BDD
cubes = mgr.to_sop(root)
names = var_names(3)
from logicmin import Implicant
sop_str = " + ".join(Implicant(c).sop_term(names) for c in cubes)
print(f"SOP from BDD: {sop_str}")
print(f"  Cubes: {cubes}")
print()

# Compare with a more complex function
f2 = BooleanFunction(n_vars=4, minterms=[0, 1, 2, 5, 7, 8, 9, 10, 14])
mgr2 = BDDManager(4)
root2 = mgr2.from_function(f2)
print(f"Complex function: minterms={sorted(f2.minterms)}")
print(f"  BDD nodes: {mgr2.node_count(root2)}")
print(f"  Satisfying: {mgr2.count_satisfying(root2)}")
cubes2 = mgr2.to_sop(root2)
sop2 = " + ".join(Implicant(c).sop_term(var_names(4)) for c in cubes2)
print(f"  SOP: {sop2}")
print()

# Boolean operations via BDD
f_or = BooleanFunction(n_vars=3, minterms=[3, 7])
r1 = mgr.from_function(f)
r2 = mgr.from_function(f_or)
r_or = mgr.or_(r1, r2)
r_and = mgr.and_(r1, r2)
r_xor = mgr.xor(r1, r2)
print(f"f = C, g = AB")
print(f"  f OR g  = {mgr.count_satisfying(r_or)} satisfying")
print(f"  f AND g = {mgr.count_satisfying(r_and)} satisfying")
print(f"  f XOR g = {mgr.count_satisfying(r_xor)} satisfying")