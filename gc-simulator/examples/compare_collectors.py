#!/usr/bin/env python3
"""Compare all collectors on the same workload.

Shows how to benchmark all five GC algorithms on the same scenario
and print a detailed comparison table.
"""

from gc_sim.simulator import GCSimulator
from gc_sim.collectors import available_collectors
from gc_sim.visualizer import render_stats_table


def main():
    print("=" * 72)
    print("GC Collector Comparison")
    print("=" * 72)

    for collector in available_collectors():
        sim = GCSimulator(heap_size=512, collector=collector)
        sim.scenario_random_graph(n=50, edge_prob=0.05, n_roots=5, seed=42)
        sim.collect()

        print(f"\n--- {collector} ---")
        print(f"  Live objects : {sim.heap.num_live}")
        print(f"  Total pause  : {sim.stats.total_pause} cells")
        print(f"  Max pause    : {sim.stats.max_pause} cells")
        print(f"  Avg pause    : {sim.stats.avg_pause:.1f} cells")
        print(f"  Survival     : {sim.stats.avg_survival:.1%}")
        print(f"  Fragmentation: {sim.fragmentation():.1%}")
        print(f"  Peak heap    : {sim.heap.high_water_mark} cells")


if __name__ == "__main__":
    main()