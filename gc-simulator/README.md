# gc-simulator

A from-scratch, pure-Python **heap & garbage-collector simulator** that models
memory allocation and automatic memory management. It simulates a fixed-size
"machine heap" populated with objects that reference each other, and provides
**five classic garbage-collection algorithms** that run over that heap,
exposing detailed statistics, traces and visualisations so that the trade-offs
between collectors can be studied empirically.

## Features

### Collectors (5 algorithms)
| Collector | Description |
|-----------|-------------|
| **Mark-Sweep** | Trace from roots (DFS/BFS), then free unmarked objects. Non-moving. |
| **Mark-Compact** | Mark-Sweep + Lisp-2 sliding compaction. Eliminates fragmentation. |
| **Copying** | Cheney-style semispace copying collector. O(live) pause, no fragmentation. |
| **Reference Counting** | Immediate reclamation on zero refcount, with cycle collection. |
| **Generational** | Young (copying) + Old (mark-sweep) generations with promotion, remembered sets, minor/major collections. |

### Allocators (3 strategies)
- **Bump allocator** — O(1) pointer-bump, no reuse until compaction
- **Free-list allocator** — reuses freed space with first-fit / best-fit / worst-fit policies

### Scenarios
- **Linked list** — singly-linked chain of N nodes
- **Binary tree** — complete binary tree of depth D
- **Random graph** — N objects with configurable edge probability and root count

### Tools
- **Object graph tracer** — iterative DFS/BFS marking, reachable-set computation, Tarjan SCC cycle detection
- **Statistics tracker** — per-collection stats (live before/after, collected, freed, moved, pause cost, fragmentation, survival ratio) with summary reporting
- **Heap visualizer** — ASCII heap layout with ANSI colour, Graphviz DOT graph export, stats table renderer
- **Config system** — JSON/YAML/TOML configuration loading and saving
- **CLI** — `run`, `viz`, `compare`, `list`, `config-save`, `config-load` subcommands

## How It Works

The simulator models a heap as a fixed-size array of *cells*. Each `Object`
occupies a contiguous run of cells and carries metadata: size, address, mark
bit, age, forwarding pointer, and a list of outgoing `ObjectRef` handles. A
`RootSet` holds the GC roots (global variables, stack slots).

When `collect()` is called:
1. **Mark phase** — the collector traverses the object graph from the roots,
   marking every reachable object.
2. **Sweep/copy/compact phase** — depending on the algorithm, dead objects are
   freed (mark-sweep), live objects are slid to the bottom (mark-compact), or
   live objects are copied to a semispace (copying).
3. **Statistics** — every collection records detailed metrics for analysis.

The generational collector splits the heap into a young generation (lower
half, copying collection) and an old generation (upper half, mark-sweep).
Objects that survive `promote_threshold` minor collections are promoted to
the old generation. A *remembered set* tracks old-to-young references so
minor collections don't need to scan the entire old generation.

## Installation

```bash
cd gc-simulator
pip install -e .
```

## Usage

### Python API

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

### Comparing collectors

```python
from gc_sim.simulator import GCSimulator

for collector in ["mark_sweep", "mark_compact", "copying", "ref_count", "generational"]:
    sim = GCSimulator(heap_size=512, collector=collector)
    sim.scenario_random_graph(n=50, edge_prob=0.05, n_roots=5, seed=42)
    sim.collect()
    print(f"{collector:20s} pause={sim.stats.max_pause:4d}  freed={sim.stats.total_freed:4d}  frag={sim.fragmentation():.1%}")
```

### CLI

```bash
# List available collectors
gc-sim list

# Run a simulation
gc-sim run --collector mark_sweep --scenario linked_list \
    --scenario-params '{"n": 20, "obj_size": 8}'

# Visualise the heap
gc-sim viz --heap-size 128 --collector copying --scenario binary_tree \
    --scenario-params '{"depth": 3, "obj_size": 4}'

# Compare all collectors
gc-sim compare --heap-size 512 --scenario random_graph \
    --scenario-params '{"n": 50, "edge_prob": 0.05}'

# Save/load configuration
gc-sim config-save my_run.json --collector generational
gc-sim config-load my_run.json
```

## Project Structure

```
gc-simulator/
├── gc_sim/
│   ├── __init__.py      # Package exports
│   ├── heap.py          # Heap, Object, ObjectRef, RootSet
│   ├── allocators.py    # BumpAllocator, FreeListAllocator
│   ├── tracer.py        # DFS/BFS marking, reachable set, cycle detection
│   ├── collectors.py     # 5 GC algorithms
│   ├── simulator.py     # GCSimulator high-level driver
│   ├── stats.py         # CollectionStats, StatsTracker
│   ├── visualizer.py    # ASCII heap rendering, DOT export, stats tables
│   ├── config.py        # JSON/YAML/TOML config loading
│   └── cli.py           # argparse CLI
├── tests/
│   └── test_gc_sim.py   # 34 tests
├── pyproject.toml
└── README.md
```

## Testing

```bash
cd gc-simulator
pip install -e ".[dev]"
pytest tests/ -v
```

## License

MIT