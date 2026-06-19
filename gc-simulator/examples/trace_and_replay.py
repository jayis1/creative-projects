#!/usr/bin/env python3
"""Trace and replay example.

Demonstrates event tracing: record all operations on one collector,
then replay the same allocation stream on a different collector to
see how the GC behaviour changes.
"""

import json
from gc_sim.simulator import GCSimulator
from gc_sim.replay import TraceReplayer


def main():
    # Phase 1: Run a simulation with tracing on mark_sweep
    print("=== Phase 1: Record trace on mark_sweep ===")
    sim1 = GCSimulator(heap_size=512, collector="mark_sweep", trace=True)
    sim1.scenario_random_graph(n=30, edge_prob=0.1, n_roots=5, seed=42)
    sim1.collect()

    events = sim1.tracer.export()
    print(f"Recorded {len(events)} events")
    counts = sim1.tracer.counts()
    for et, count in sorted(counts.items()):
        print(f"  {et:<20} {count}")

    # Phase 2: Replay the trace on copying collector
    print("\n=== Phase 2: Replay on copying collector ===")
    replayer = TraceReplayer(events, collector="copying", heap_size=512)
    sim2 = replayer.replay()
    print(f"Allocations replayed: {sim2._alloc_count}")
    print(f"Live objects: {sim2.heap.num_live}")

    # Phase 3: Replay on all collectors
    print("\n=== Phase 3: Replay on all collectors ===")
    results = replayer.replay_all_collectors()
    for cname, s in results.items():
        print(f"  {cname:<16} live={s.heap.num_live}  "
              f"pause={s.stats.total_pause:>5}  "
              f"frag={s.fragmentation():.0%}")


if __name__ == "__main__":
    main()