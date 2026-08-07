"""
Example 3: Sensitivity analysis and unate classification.

Demonstrates boolean difference, sensitivity computation, and unate
classification for a 4-variable function.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from logicmin import (
    BooleanFunction, all_sensitivities, boolean_difference,
    unate_profile, is_unate, on_set_size, off_set_size,
    minterm_adjacency, var_names,
)

# F(A,B,C,D) = AB + CD
f = BooleanFunction(n_vars=4, minterms=[12, 13, 14, 15, 3, 7, 11])
print(f"Function: F = AB + CD")
print(f"  Minterms: {sorted(f.minterms)}")
print(f"  On-set size: {on_set_size(f)}")
print(f"  Off-set size: {off_set_size(f)}")
print()

# Sensitivity analysis
names = var_names(4)
print("Sensitivity analysis:")
sens = all_sensitivities(f)
for i, name in enumerate(names):
    bar = "█" * int(sens[i] * 20)
    print(f"  {name}: {sens[i]:.4f}  {bar}")
print()

# Boolean difference
print("Boolean differences:")
for i, name in enumerate(names):
    diff = boolean_difference(f, i)
    print(f"  ∂f/∂{name}: minterms={sorted(diff.minterms)} (in {diff.n_vars} vars)")
print()

# Unate classification
print("Unate classification:")
profile = unate_profile(f)
for i, name in enumerate(names):
    cls = profile[i]
    symbol = "↑" if cls == "positive" else "↓" if cls == "negative" else "⇅"
    print(f"  {name}: {cls} {symbol}")
print()

# Minterm adjacency
edges = minterm_adjacency(f)
print(f"Minterm adjacency graph ({len(edges)} edges):")
for a, b in edges:
    print(f"  {a:04b} ({a}) ↔ {b:04b} ({b})")