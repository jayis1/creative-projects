"""Example: Batch simulation with statistical analysis."""

from petri.presets import dining_philosophers
from petri.batch import batch_simulate

# Run batch simulation on dining philosophers (deadlock-prone)
net = dining_philosophers(3)

print("=== Batch Simulation: Dining Philosophers (n=3) ===")
print(f"Net: {net}")
print()

# Run 2000 simulations, 200 steps each
stats = batch_simulate(net, num_runs=2000, max_steps=200, seed=42)
print(stats)
print()

# With a larger philosopher count
net5 = dining_philosophers(5)
print("=== Dining Philosophers (n=5) ===")
stats5 = batch_simulate(net5, num_runs=1000, max_steps=200, seed=42)
print(stats5)