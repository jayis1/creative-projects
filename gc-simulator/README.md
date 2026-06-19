<div align="center">

# gc-simulator

**A from-scratch, pure-Python heap & garbage-collector simulator**

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests: 116](https://img.shields.io/badge/tests-116%20passing-brightgreen.svg)]()
[![Version: 2.0](https://img.shields.io/badge/version-2.0-blue.svg)]()

*Model memory allocation and automatic memory management with five classic
GC algorithms, tracing, replay, and detailed performance analysis.*

</div>

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
  - [Python API](#python-api)
  - [CLI](#cli)
  - [Configuration Files](#configuration-files)
  - [Event Tracing & Replay](#event-tracing--replay)
  - [Reporting & Analysis](#reporting--analysis)
- [Architecture](#architecture)
- [Collectors](#collectors)
- [Allocators](#allocators)
- [Scenarios](#scenarios)
- [Examples](#examples)
- [Testing](#testing)
- [Known Issues (Resolved)](#known-issues-resolved)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [Changelog](#changelog)
- [License](#license)

---

## Overview

gc-simulator models a fixed-size "machine heap" populated with objects that
reference each other, and provides **five classic garbage-collection
algorithms** that run over that heap, exposing detailed statistics, traces,
and visualizations so that the trade-offs between collectors can be studied
empirically.

It is designed for:

- **Education** — understand how mark-sweep, copying, reference counting, and
  generational GC actually work, with visible heap layouts and pause-time data.
- **Benchmarking** — compare all five collectors on identical workloads and
  see which has the lowest pause, best survival ratio, or least fragmentation.
- **Experimentation** — record an allocation trace, then replay it on a
  different collector or with a different heap size to see how behaviour
  changes.

## Features

### Collectors (5 algorithms)

| Collector | Description |
|-----------|-------------|
| **Mark-Sweep** | Trace from roots (DFS/BFS), then free unmarked objects. Non-moving. |
| **Mark-Compact** | Mark-Sweep + Lisp-2 sliding compaction. Eliminates fragmentation. |
| **Copying** | Cheney-style semispace copying collector. O(live) pause, no fragmentation. |
| **Reference Counting** | Immediate reclamation on zero refcount, with cycle collection. |
| **Generational** | Young (copying) + Old (mark-sweep) generations with promotion, remembered sets, minor/major collections. |

### Allocators (2 strategies)

- **Bump allocator** — O(1) pointer-bump, no reuse until compaction
- **Free-list allocator** — reuses freed space with first-fit / best-fit / worst-fit policies

### Scenarios (5 built-in)

- **Linked list** — singly-linked chain of N nodes
- **Binary tree** — complete binary tree of depth D
- **Random graph** — N objects with configurable edge probability and root count
- **Churn** — many short-lived objects plus a few long-lived roots (generational hypothesis)
- **Cycle heavy** — many cyclic structures (challenging for ref counting)

### Tools

- **Object graph tracer** — iterative DFS/BFS marking, reachable-set computation, Tarjan SCC cycle detection
- **Statistics tracker** — per-collection stats with summary reporting and JSON export
- **Heap visualizer** — ASCII heap layout with ANSI colour, Graphviz DOT graph export, stats table renderer
- **Benchmark harness** — cross-collector comparison with predefined scenarios, wall-time measurement, formatted comparison tables
- **Event tracing** — record every allocation, root, link, and collection as a JSON-serialisable event stream
- **Trace replay** — replay a recorded trace on any collector to compare behaviour on the exact same workload
- **Pause-time analysis** — histogram with percentile breakdowns (p90, p95, p99), ASCII bar charts
- **Comparison reports** — formatted cross-collector reports with winner analysis
- **Heap snapshots** — JSON-serialisable heap state for debugging and reproducibility
- **Weak references** — `ObjectRef` handles that don't prevent collection; automatically cleared when target is freed
- **Finalizers** — callbacks invoked when an object is freed by the GC (with exception safety)
- **Config system** — JSON/YAML/TOML configuration loading and saving
- **Structured logging** — configurable log levels with stderr/file output
- **CLI** — 12 subcommands: `run`, `viz`, `compare`, `benchmark`, `snapshot`, `list`, `config-save`, `config-load`, `trace`, `replay`, `report`, `histogram`

## Installation

```bash
cd gc-simulator
pip install -e .
```

For development:
```bash
pip install -e ".[dev]"
```

## Quick Start

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

## Usage

### Python API

#### Basic simulation

```python
from gc_sim.simulator import GCSimulator

sim = GCSimulator(heap_size=256, collector="mark_sweep")
sim.scenario_linked_list(n=10, obj_size=8)
stats = sim.collect()
print(f"Collected {stats.collected} objects, freed {stats.bytes_freed} cells")
print(sim.summary())
```

#### Comparing collectors

```python
from gc_sim.simulator import GCSimulator

for collector in ["mark_sweep", "mark_compact", "copying", "ref_count", "generational"]:
    sim = GCSimulator(heap_size=512, collector=collector)
    sim.scenario_random_graph(n=50, edge_prob=0.05, n_roots=5, seed=42)
    sim.collect()
    print(f"{collector:20s} pause={sim.stats.max_pause:4d}  "
          f"freed={sim.stats.total_freed:4d}  frag={sim.fragmentation():.1%}")
```

#### Event tracing

```python
from gc_sim.simulator import GCSimulator

sim = GCSimulator(heap_size=512, collector="mark_sweep", trace=True)
sim.scenario_random_graph(n=30, edge_prob=0.1, n_roots=5, seed=42)
sim.collect()

# Export trace as JSON
sim.tracer.export_json("trace.json")
print(f"Recorded {len(sim.tracer)} events")
```

#### Trace replay

```python
from gc_sim.replay import TraceReplayer

# Replay the trace on a different collector
replayer = TraceReplayer("trace.json", collector="copying", heap_size=512)
sim2 = replayer.replay()
print(f"Allocations: {sim2._alloc_count}, Live: {sim2.heap.num_live}")

# Or replay on ALL collectors
results = replayer.replay_all_collectors()
for name, s in results.items():
    print(f"{name}: live={s.heap.num_live}, pause={s.stats.total_pause}")
```

#### Pause-time analysis

```python
from gc_sim.simulator import GCSimulator
from gc_sim.reporting import PauseHistogram

sim = GCSimulator(heap_size=512, collector="generational")
sim.scenario_churn(n_short=100, n_long=5, obj_size=4)
for _ in range(5):
    sim.collect()

hist = PauseHistogram.from_records(sim.stats.records)
print(hist.render_ascii())
print(f"p90={hist.p90}, p95={hist.p95}, p99={hist.p99}")
```

#### Detailed comparison report

```python
from gc_sim.simulator import GCSimulator
from gc_sim.reporting import analyse_from_sims, format_comparison_report

sims = {}
for collector in ["mark_sweep", "copying", "generational"]:
    sim = GCSimulator(heap_size=512, collector=collector)
    sim.scenario_churn(n_short=80, n_long=5, obj_size=4)
    for _ in range(5):
        sim.collect()
    sims[collector] = sim

reports = analyse_from_sims(sims)
print(format_comparison_report(reports, include_histogram=True))
```

### CLI

```bash
# List available collectors, allocators, and scenarios
gc-sim list

# Run a simulation
gc-sim run --collector mark_sweep --scenario linked_list \
    --scenario-params '{"n": 20, "obj_size": 8}'

# Visualise the heap (ASCII or DOT)
gc-sim viz --heap-size 128 --collector copying --scenario binary_tree \
    --scenario-params '{"depth": 3, "obj_size": 4}'
gc-sim viz --heap-size 128 --scenario linked_list --dot

# Compare all collectors (with histogram)
gc-sim compare --heap-size 512 --scenario random_graph \
    --scenario-params '{"n": 50, "edge_prob": 0.05}' --histogram

# Generate a detailed report with winner analysis
gc-sim report --heap-size 1024 --scenario churn \
    --scenario-params '{"n_short": 100, "n_long": 5, "obj_size": 4}' \
    --num-collections 5 --histogram

# Show pause-time histogram for a single collector
gc-sim histogram --collector generational --scenario churn \
    --num-collections 10 --heap-size 1024

# Benchmark collectors (with timing)
gc-sim benchmark --heap-size 512 --scenario random_graph \
    --scenario-params '{"n": 50, "edge_prob": 0.05}'

# Trace a simulation and export the trace
gc-sim trace --scenario linked_list --output trace.json --summary

# Replay a trace on a different collector
gc-sim replay trace.json --collector copying --heap-size 512

# Snapshot the heap state as JSON
gc-sim snapshot --heap-size 128 --scenario linked_list --after-collect

# Save/load configuration
gc-sim config-save my_run.json --collector generational
gc-sim config-load my_run.json

# With logging
gc-sim --log-level DEBUG run --collector mark_sweep --scenario churn
```

### Configuration Files

Configuration files support JSON, YAML, and TOML formats:

**JSON** (`config.json`):
```json
{
  "heap_size": 512,
  "collector": "generational",
  "allocator": "bump",
  "scenario": "churn",
  "scenario_params": {"n_short": 100, "n_long": 5, "obj_size": 4},
  "num_collections": 5,
  "seed": 42
}
```

**YAML** (`config.yaml`):
```yaml
heap_size: 1024
collector: mark_compact
allocator: free_list
allocator_policy: best_fit
scenario: random_graph
scenario_params:
  n: 50
  edge_prob: 0.08
  n_roots: 5
num_collections: 3
seed: 42
```

Load and run:
```bash
gc-sim config-load config.json
```

### Event Tracing & Replay

Event tracing records every operation as a JSON-serialisable event:

```bash
# Record a trace
gc-sim trace --scenario churn --output trace.json --summary

# Replay on a different collector
gc-sim replay trace.json --collector copying --heap-size 1024

# Replay without running collections (just allocation pattern)
gc-sim replay trace.json --collector generational --no-collect
```

### Reporting & Analysis

```bash
# Full comparison report with histograms
gc-sim report --scenario churn --num-collections 10 --histogram

# JSON output for programmatic use
gc-sim report --json --scenario random_graph

# Single-collector histogram
gc-sim histogram --collector mark_compact --scenario churn --json
```

## Architecture

```
gc-simulator/
├── gc_sim/
│   ├── __init__.py        # Package exports & version
│   ├── __main__.py        # python -m gc_sim entry point
│   ├── heap.py            # Heap, Object, ObjectRef, RootSet, weak refs, finalizers
│   ├── allocators.py      # BumpAllocator, FreeListAllocator (first/best/worst-fit)
│   ├── tracer.py          # DFS/BFS marking, reachable set, Tarjan cycle detection
│   ├── collectors.py       # 5 GC algorithms (mark-sweep, mark-compact, copying, ref-count, generational)
│   ├── simulator.py       # GCSimulator high-level driver + scenario generators
│   ├── stats.py           # CollectionStats, StatsTracker
│   ├── visualizer.py      # ASCII heap rendering, DOT export, stats tables
│   ├── benchmark.py       # Cross-collector benchmarking harness + predefined scenarios
│   ├── config.py          # JSON/YAML/TOML config loading & saving
│   ├── logging_utils.py   # Structured logging
│   ├── events.py          # Event-sourcing trace recording (NEW)
│   ├── replay.py          # Trace replay engine (NEW)
│   ├── reporting.py       # Pause histograms, comparison reports (NEW)
│   └── cli.py             # argparse CLI (12 subcommands)
├── tests/
│   ├── test_gc_sim.py     # 57 core tests
│   ├── test_bug_hunt.py   # 11 bug-fix verification tests
│   └── test_enhancements.py  # 59 tests for new features (NEW)
├── examples/
│   ├── basic_simulation.py      # Getting started
│   ├── compare_collectors.py    # Cross-collector comparison
│   ├── trace_and_replay.py      # Tracing & replay demo
│   ├── pause_analysis.py       # Pause-time histogram demo
│   ├── heap_visualization.py    # ASCII & DOT visualization
│   ├── generational_config.json # Example config
│   └── mark_compact_config.yaml # Example config
├── pyproject.toml
├── CONTRIBUTING.md
├── LICENSE
└── README.md
```

### How It Works

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
Objects that survive `promote_threshold` minor collections are promoted to the
old generation. A *remembered set* tracks old-to-young references so minor
collections don't need to scan the entire old generation.

## Collectors

| Collector | Pros | Cons | Best For |
|-----------|------|------|----------|
| **Mark-Sweep** | Non-moving, simple | Fragmentation grows | General purpose |
| **Mark-Compact** | No fragmentation | Long pause (move phase) | Memory-constrained |
| **Copying** | No fragmentation, O(live) pause | 50% heap overhead | Short-lived objects |
| **Reference Counting** | Immediate reclamation, deterministic | Cycles not collected | Cycles rare |
| **Generational** | Cheap minor collections | Complexity, write barriers | Most real workloads |

## Allocators

| Allocator | Speed | Fragmentation | Reuse |
|-----------|-------|-------------|-------|
| **Bump** | O(1) | None (while space remains) | No (until compaction) |
| **Free-List (first-fit)** | O(n) scan | Moderate | Yes |
| **Free-List (best-fit)** | O(n) scan | Low waste | Yes |
| **Free-List (worst-fit)** | O(n) scan | Large blocks preserved | Yes |

## Scenarios

| Scenario | Description | Models |
|----------|-------------|--------|
| **linked_list** | N-node singly-linked chain | Sequential allocation |
| **binary_tree** | Complete binary tree, depth D | Hierarchical allocation |
| **random_graph** | N objects, random edges | General workload |
| **churn** | Many short-lived + few long-lived | Generational hypothesis |
| **cycle_heavy** | Many 2-node cycles | Ref-counting weakness |

## Examples

Run the included examples:

```bash
# Basic simulation
python examples/basic_simulation.py

# Compare all collectors
python examples/compare_collectors.py

# Trace and replay
python examples/trace_and_replay.py

# Pause-time analysis
python examples/pause_analysis.py

# Heap visualization
python examples/heap_visualization.py
```

### ASCII Heap Visualization

```
Heap: 128 cells, used=28, free=100, frag=0.0%
high water mark = 28 cells
1111222233334444555566667777....................................
................................................................
```

After freeing 2 objects:
```
Heap: 128 cells, used=20, free=108, frag=7.4%
high water mark = 28 cells
111122223333........66667777....................................
................................................................
```

### Pause-time Histogram

```
Pause-time histogram (5 collections)
  min=0  mean=21.8  median=0.0  p90=84  p95=84  p99=84  max=84

  <=     1: ████████████████████████████████████████    3 ( 60.0%)
      2-    4:     0 (  0.0%)
      5-   16:     0 (  0.0%)
     17-   64: █████████████    1 ( 20.0%)
     65-  256: █████████████    1 ( 20.0%)
    257- 1024:     0 (  0.0%)
  >  1024:     0 (  0.0%)
```

### Comparison Report

```
====================================================================================
GC Collector Comparison Report
====================================================================================
collector        #coll   alloc  freed  coll t_pause  avg_p  max_p  surv% frag%  peak
------------------------------------------------------------------------------------
mark_sweep           5     340    320    80     105   21.0     85  81.2%    0%   340
mark_compact         5     340    320    80     105   21.0     85  81.2%    0%   340
copying              5     340    320    80     205   41.0    105  81.2%   48%   340
ref_count            5     340    288    72      97   19.4     77  81.3%    0%   308
generational         5     340    256    59     109   21.8     84  86.1%   40%   340
====================================================================================

Winner Analysis:
  Lowest avg pause : ref_count (19.4 cells)
  Lowest total pause: ref_count (97 cells)
  Highest survival  : generational (86.12%)
  Least fragmentation: mark_sweep (0.0%)
```

## Testing

```bash
cd gc-simulator
pip install -e ".[dev]"

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=gc_sim

# Run only enhancement tests
pytest tests/test_enhancements.py -v

# Run a specific test class
pytest tests/test_gc_sim.py::TestMarkSweep -v

# Run with parallel execution
pytest tests/ -v -n auto
```

**116 tests** covering:
- Heap operations, allocators, and object graph management
- All 5 collectors (mark-sweep, mark-compact, copying, ref-count, generational)
- Tracing (DFS/BFS marking, reachable set, cycle detection)
- All 5 scenarios (linked list, binary tree, random graph, churn, cycle heavy)
- Weak references, finalizers, heap snapshots
- Event tracing, trace replay, and cross-collector determinism
- Pause-time histograms, comparison reports, JSON export
- CLI (12 subcommands)
- Input validation and error handling
- 4 bug-fix verifications

## Known Issues (Resolved)

The following bugs were identified during the Phase 3 bug hunt and have been
fixed with targeted patches. Each fix is covered by a dedicated test in
`tests/test_bug_hunt.py`.

1. **Generational `_major_collect` TypeError (Bug A/G)**: `mark_dfs()` returns
   a `Set[int]`, but `_major_collect` assigned it directly to `stats.marked`
   (typed `int`) and used it in `marked + collected` arithmetic, causing a
   `TypeError` at runtime. **Fix**: use `len(marked)` to convert the set to
   an integer count.

2. **Copying collector skips finalizers and weak-ref cleanup (Bug B)**: The
   copying collector freed dead objects by directly setting `alive = False`
   and `address = -1`, bypassing `Heap.free_obj()`. This meant finalizers
   were never called and weak references to dead objects were never cleared.
   **Fix**: call `self.heap.free_obj(o)` instead, which runs finalizers and
   clears weak refs.

3. **`_is_young` returns True for dead objects (Bug C)**:
   `GenerationalCollector._is_young()` checked only `obj.address <
   young_size`, which is `True` for dead objects (address = -1). This could
   cause freed objects to be mistaken for young-gen objects, leading to
   incorrect sweep behaviour. **Fix**: check `obj.alive` and `obj.address >=
   0` first.

4. **Dead code in CopyingCollector (Bug H)**: The variable `scan_ptr =
   to_start` was assigned but never used (the actual working variable is
   `scan_ptr_current`). Removed to avoid confusion.

## Roadmap

- **Incremental/concurrent GC** — simulate concurrent marking with write barriers
- **Large object space** — separate allocation region for large objects
- **Pin/unpin** — support for pinning objects (preventing movement)
- **GC pressure analysis** — automatic detection of allocation hotspots
- **Interactive mode** — step-through debugger for GC cycles
- **Web UI** — browser-based heap visualization with D3.js
- **More collectors** — Shenandoah-style concurrent compaction, ZGC-style colored pointers
- **Object aging policies** — configurable promotion thresholds per-object
- **Memory pressure callbacks** — simulate OOM handlers and backpressure

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines on development
setup, code style, adding new collectors/allocators/scenarios, and the pull
request process.

## Changelog

### v2.0.0 (2026-06-19) — Comprehensive Improvement

**New Features:**
- Event tracing system (`gc_sim.events`) — record every allocation, root,
  link, and collection as a JSON-serialisable event stream
- Trace replay engine (`gc_sim.replay`) — replay recorded traces on any
  collector or all collectors simultaneously
- Pause-time analysis (`gc_sim.reporting`) — histogram with configurable bins,
  percentile breakdowns (p90/p95/p99), ASCII bar charts
- Cross-collector comparison reports (`gc_sim.reporting`) — formatted tables
  with winner analysis, JSON export
- Two new scenarios: `churn` (generational hypothesis) and `cycle_heavy`
  (ref-counting stress test)
- Input validation on all simulator methods (allocate, scenarios, link)

**CLI Enhancements:**
- 4 new subcommands: `trace`, `replay`, `report`, `histogram`
- Global `--log-level` and `--log-file` flags
- `--histogram` flag on `compare` and `report`
- `--json` output on `compare`, `report`, `histogram`
- `--summary` flag on `trace`

**Architecture:**
- Version bumped to 2.0.0
- 3 new modules: `events.py`, `replay.py`, `reporting.py`
- Updated `pyproject.toml` with expanded classifiers and keywords
- Updated `__init__.py` with all new exports
- Cleaned up `benchmark.py` (removed dead code in `benchmark_all`)
- Added CONTRIBUTING.md and LICENSE
- Added GitHub Actions CI (Python 3.10-3.13 matrix)
- Added examples/ directory with 5 example scripts and 2 config files
- 59 new tests (116 total, all passing)

### v1.1.0 — Phase 2 & 3 (Bug Hunt)

- Benchmark harness, weak references, finalizers, heap snapshots
- Structured logging, `__main__.py` entry point
- Input validation on link/root operations
- 4 bugs fixed (TypeError in generational, finalizer/weak-ref bypass,
  dead-object _is_young, dead code removal)
- 12 additional tests (57 total)

### v1.0.0 — Initial Release

- 5 GC algorithms, 2 allocators, 3 scenarios
- Object graph tracer with Tarjan SCC
- ASCII heap visualizer, Graphviz DOT export
- Statistics tracker, JSON/YAML/TOML config
- argparse CLI (8 subcommands)
- 46 tests

## License

MIT — see [LICENSE](LICENSE).