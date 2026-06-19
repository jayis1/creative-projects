# Example: Basic GC Simulation

This example shows how to create a simulator, build an object graph,
run a collection, and inspect the results.

```python
from gc_sim.simulator import GCSimulator

# Create a mark-sweep simulator with a 256-cell heap
sim = GCSimulator(heap_size=256, collector="mark_sweep")

# Allocate a 10-node linked list
sim.scenario_linked_list(n=10, obj_size=8)

# Collect garbage
stats = sim.collect()
print(f"Collected {stats.collected} objects, freed {stats.bytes_freed} cells")

# Print summary
print(sim.summary())
```

## Running

```bash
cd gc-simulator
pip install -e .
python examples/basic_simulation.py
```