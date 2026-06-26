"""Larger-than-Life (LtL) — Boon rule.

Larger-than-Life rules use neighbourhoods bigger than the standard 3×3.
The Boon rule (B5678/S45678/R5) uses a 5×5 neighbourhood and produces
beautiful "blob" patterns.
"""

from cellular_automaton import (
    CellularAutomaton, LargerThanLifeRule, render_ascii,
)

rule = LargerThanLifeRule((5678,), (45678,), radius=5, name="Boon")
ca = CellularAutomaton(rule, width=30, height=20)
ca.randomize(0.3, seed=42)

print(f"Rule: {rule.rule_string()}")
print(f"Initial state ({ca.alive_count()} alive):")
print(render_ascii(ca.grid))

ca.step(10)
print(f"\nAfter 10 steps ({ca.alive_count()} alive):")
print(render_ascii(ca.grid))