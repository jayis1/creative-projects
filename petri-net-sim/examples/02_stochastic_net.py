"""Example: Stochastic Petri nets — CTMC and steady-state analysis."""

from petri import PetriNet, Place, Transition
from petri.stochastic import (
    StochasticPetriNet, build_ctmc, steady_state_probabilities,
    expected_time_to_target,
)
from petri.presets import mutual_exclusion

# Use a bounded net for steady-state analysis
net = mutual_exclusion()

# Make it stochastic
spn = StochasticPetriNet(net)
spn.set_rate("p1_request", 1.0)
spn.set_rate("p1_enter", 2.0)
spn.set_rate("p1_exit", 3.0)
spn.set_rate("p2_request", 1.5)
spn.set_rate("p2_enter", 2.5)
spn.set_rate("p2_exit", 3.5)

print("=== Mutual Exclusion (Stochastic) ===")
print(f"Rates: {spn.all_rates()}")
print()

# Build CTMC
ctmc = build_ctmc(spn)
print(f"CTMC states: {ctmc.num_states}")

# Steady-state probabilities
probs = steady_state_probabilities(ctmc)
print("\nSteady-state probabilities:")
for sid, prob in sorted(probs.items(), key=lambda x: -x[1]):
    marking = ctmc.states[sid].marking
    marking_str = ", ".join(f"{k}={v}" for k, v in sorted(marking.items()))
    print(f"  {sid}: P={prob:.6f}  [{marking_str}]")

print()
total = sum(probs.values())
print(f"Sum of probabilities: {total:.6f} (should be ~1.0)")

# Expected time to reach a state where p1 is in critical section
print()
result = expected_time_to_target(spn, {"p1_cs": 1})
print(f"Expected time to reach p1_cs=1: {result.expected_time:.4f}")
print(f"Target found: {result.found_target}")