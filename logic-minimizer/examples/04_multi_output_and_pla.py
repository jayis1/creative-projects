"""
Example 4: Multi-output minimization with PLA format.

Demonstrates multi-output minimization for a 2-bit adder, PLA file
generation, and don't-care optimization.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from logicmin import (
    BooleanFunction, MultiOutputMinimizer, QuineMcCluskey,
    PLAData, write_pla, assign_dontcares,
    var_names,
)

# 2-bit adder: Sum and Carry
# A, B, Cin → Sum, Carry
sum_out = BooleanFunction(3, [1, 2, 4, 7], name="sum")
carry   = BooleanFunction(3, [3, 5, 6, 7], name="carry")

print("2-bit adder:")
print(f"  Sum:   minterms = {sorted(sum_out.minterms)}")
print(f"  Carry: minterms = {sorted(carry.minterms)}")
print()

# Minimize each independently
qm = QuineMcCluskey(3)
r_sum = qm.minimize(sum_out)
r_carry = qm.minimize(carry)
print("Independent minimization:")
print(f"  Sum:   {r_sum.sop}  ({r_sum.n_literals} lits)")
print(f"  Carry: {r_carry.sop}  ({r_carry.n_literals} lits)")
print(f"  Total: {r_sum.n_literals + r_carry.n_literals} literals")
print()

# Multi-output minimization (shared implicants)
mom = MultiOutputMinimizer(3)
result = mom.minimize([sum_out, carry])
print("Multi-output minimization:")
print(f"  Total terms:    {result.total_terms}")
print(f"  Total literals: {result.total_literals}")
for i, (func, sop) in enumerate(zip([sum_out, carry], result.sop)):
    print(f"  {func.name}: {sop}")
shared = [s for s in result.shared_implicants if len(s.outputs) > 1]
if shared:
    print(f"  Shared implicants ({len(shared)}):")
    names = var_names(3)
    for s in shared:
        print(f"    {s.implicant.sop_term(names)} → outputs {sorted(s.outputs)}")
print()

# Export to PLA
pla_text = write_pla([sum_out, carry])
print("PLA format:")
print(pla_text)

# Don't-care optimization
print("Don't-care optimization example:")
f_dc = BooleanFunction(n_vars=4, minterms=[4, 8, 10, 11, 12, 15], dontcare=[9, 14])
dc_result = assign_dontcares(f_dc, "qm")
print(f"  Original:  {dc_result.original_sop}  (cost={dc_result.original_cost})")
print(f"  Optimized: {dc_result.optimized_sop} (cost={dc_result.optimized_cost})")
print(f"  Improvement: {dc_result.improvement} literals")