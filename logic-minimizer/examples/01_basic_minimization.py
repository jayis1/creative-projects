"""
Example 1: Basic Quine-McCluskey minimization.

Demonstrates exact two-level SOP minimization with prime implicant
identification and Petrick's method.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from logicmin import QuineMcCluskey, BooleanFunction, var_names

# F(A,B,C,D) = Σm(4,8,10,11,12,15) + d(9,14)
f = BooleanFunction(n_vars=4, minterms=[4, 8, 10, 11, 12, 15], dontcare=[9, 14])
print(f"Function: {f}")
print(f"Minterms: {sorted(f.minterms)}")
print(f"Don't-cares: {sorted(f.dontcare)}")
print()

# Exact minimization
qm = QuineMcCluskey(n_vars=4)
result = qm.minimize(f)
print(f"Minimized SOP: {result.sop}")
print(f"  Terms:       {result.n_terms}")
print(f"  Literals:    {result.n_literals}")
print(f"  Primes:      {len(result.prime_implicants)}")
print(f"  Essentials:  {len(result.essential_implicants)}")
print()

# Show all prime implicants
names = var_names(4)
print("Prime implicants:")
for p in result.prime_implicants:
    tag = " (essential)" if p in result.essential_implicants else ""
    print(f"  {p.cube} = {p.sop_term(names)}{tag}")
print()

# Show the truth table
tt = f.truth_table()
print("Truth table:")
print(tt.render_ascii())