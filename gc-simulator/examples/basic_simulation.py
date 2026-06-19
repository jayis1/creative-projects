#!/usr/bin/env python3
"""Basic GC simulation example.

Demonstrates creating a simulator, building an object graph, running
a collection, and inspecting results.
"""

from gc_sim.simulator import GCSimulator


def main():
    # Create a mark-sweep simulator with a 256-cell heap
    sim = GCSimulator(heap_size=256, collector="mark_sweep")

    # Allocate a 10-node linked list
    sim.scenario_linked_list(n=10, obj_size=8)
    print(f"Objects allocated: {sim.heap.num_live}")
    print(f"Heap used: {sim.used}/{sim.heap.size} cells")

    # Collect garbage (nothing should be collected — list is rooted)
    stats = sim.collect()
    print(f"\nCollection 1: collected={stats.collected}, freed={stats.bytes_freed}")
    print(f"Survival ratio: {stats.survival_ratio:.0%}")

    # Unroot the list — all nodes become unreachable
    sim.clear_root("list_head")

    # Collect again — all 10 nodes should be collected
    stats = sim.collect()
    print(f"\nCollection 2: collected={stats.collected}, freed={stats.bytes_freed}")
    print(f"Live objects: {sim.heap.num_live}")

    # Print full summary
    print()
    print(sim.summary())


if __name__ == "__main__":
    main()