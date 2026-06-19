#!/usr/bin/env python3
"""Heap visualization example.

Shows how to render the heap as ASCII art and export the object
graph as Graphviz DOT for external visualization.
"""

from gc_sim.simulator import GCSimulator
from gc_sim.visualizer import render_heap_ascii, render_object_graph_dot


def main():
    # Create a small heap and populate it
    sim = GCSimulator(heap_size=128, collector="mark_sweep")
    sim.scenario_binary_tree(depth=2, obj_size=4)

    print("=== ASCII Heap Visualization ===")
    print(render_heap_ascii(sim.heap, use_color=False))
    print()

    # Free some objects to create fragmentation
    live = sim.heap.live_objects
    for obj in live[3:5]:
        sim.heap.free_obj(obj)

    print("=== After freeing 2 objects ===")
    print(render_heap_ascii(sim.heap, use_color=False))
    print(f"Fragmentation: {sim.fragmentation():.1%}")
    print()

    # DOT graph export
    print("=== Graphviz DOT Export ===")
    dot = render_object_graph_dot(sim.heap, sim.roots)
    print(dot[:500] + "..." if len(dot) > 500 else dot)


if __name__ == "__main__":
    main()