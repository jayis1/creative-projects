# tsp-solver

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests: 130](https://img.shields.io/badge/tests-130%20passing-brightgreen.svg)](#testing)
[![Algorithms: 18](https://img.shields.io/badge/algorithms-18-orange.svg)](#algorithms)

A comprehensive **Traveling Salesman Problem (TSP)** solver implementing **18
algorithms** across five categories: exact, approximation, construction
heuristics, local search, and metaheuristics. Pure Python with NumPy for
vectorized distance computation. No heavy external dependencies.

---

## Table of Contents

- [Overview](#overview)
- [Algorithms](#algorithms)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
  - [Python API](#python-api)
  - [Command Line](#command-line)
  - [Configuration Files](#configuration-files)
- [Architecture](#architecture)
- [Examples](#examples)
- [Example Output](#example-output)
- [Testing](#testing)
- [Contributing](#contributing)
- [Roadmap](#roadmap)
- [Changelog](#changelog)
- [License](#license)

---

## Overview

The Traveling Salesman Problem (TSP) is the classic NP-hard combinatorial
optimization problem: given a set of cities and distances between them, find
the shortest tour that visits every city exactly once and returns to the
starting city.

`tsp-solver` provides a unified interface to **18 algorithms** — from exact
dynamic programming (guaranteed optimal) to fast metaheuristics (near-optimal
in milliseconds). It is designed for education, experimentation, and practical
use.

### Key Features

- **18 algorithms** in 5 categories
- **Refinement chaining**: apply 2-opt/3-opt/or-opt after any algorithm
- **BenchmarkSuite**: run all algorithms, compute quality ratios, export CSV/JSON
- **ASCII visualization**: render tours as ASCII art
- **Config files**: YAML/JSON configuration for CLI and API
- **Logging**: configurable logging via environment or config
- **TSPLIB I/O**: load and save `.tsp` files (coordinates and edge weights)
- **Cluster instances**: generate clustered city distributions for harder tests
- **Comprehensive tests**: 130 pytest tests covering all algorithms and edge cases
- **CI**: GitHub Actions workflow for multi-version Python testing
- **pip-installable**: `pip install -e .`

---

## Algorithms

### Exact (guarantee optimal solution)

| Algorithm | Complexity | Feasible n |
|---|---|---|
| **Held-Karp** (dynamic programming) | O(n²·2ⁿ) time, O(n·2ⁿ) space | n ≤ ~22 |
| **Branch & Bound** (DFS with MST lower bound) | O(n!) worst case, much better with good bounds | n ≤ ~18 |

### Approximation (guaranteed ratio for metric TSP)

| Algorithm | Ratio |
|---|---|
| **MST 2-approximation** | ≤ 2·OPT |
| **Christofides' 1.5-approximation** | ≤ 1.5·OPT |

### Construction Heuristics (fast, no guarantee)

| Algorithm | Description |
|---|---|
| **Nearest Neighbor** | Greedily go to closest unvisited city |
| **Nearest Neighbor Multi-start** | Try multiple starting cities, keep best |
| **Nearest Insertion** | Insert city nearest to current subtour |
| **Farthest Insertion** | Insert city farthest from subtour |
| **Greedy (Multi-fragment)** | Sort edges, add shortest non-cycle-forming edges |
| **Savings (Clarke-Wright)** | Merge subtours by decreasing savings |

### Local Search (improve an existing tour)

| Algorithm | Description |
|---|---|
| **2-opt** | Reverse segments to remove crossing edges |
| **3-opt** | Try all 7 reconnections of 3 broken edges |
| **Or-opt** | Move segments of length 1-3 to better positions |

### Metaheuristics (stochastic search)

| Algorithm | Description |
|---|---|
| **Simulated Annealing** | Geometric cooling with 2-opt moves |
| **Genetic Algorithm** | Order crossover (OX), inversion mutation, elitism |
| **Ant Colony Optimization** | Pheromone-based colony search |
| **Iterated Local Search** | Double-bridge kicks + 2-opt/3-opt |
| **Lin-Kernighan** | Variable-depth sequential edge exchange |

---

## Installation

### From source (recommended)

```bash
cd tsp-solver
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

### With optional YAML config support

```bash
pip install -e ".[yaml]"
```

### With test dependencies

```bash
pip install -e ".[test]"
pytest test_suite.py -v
```

### Requirements

- Python ≥ 3.9
- NumPy ≥ 1.20
- PyYAML (optional, for YAML config files)
- pytest (optional, for running tests)

---

## Quick Start

```python
from tsp_solver.instance import generate_instance
from tsp_solver.solver import solve

# Generate a 50-city instance
inst = generate_instance(50, seed=42)

# Solve with Christofides + 2-opt refinement
tour = solve(inst, 'christofides', refine='two_opt')
print(f"Length: {tour.length:.2f}")
print(f"Tour: {tour.order}")
```

From the command line:

```bash
tsp-solver --algo christofides --refine two_opt -n 50 --seed 42 --json
```

---

## Usage

### Python API

```python
from tsp_solver.instance import generate_instance
from tsp_solver.solver import solve, list_algorithms, list_algorithms_by_category
from tsp_solver.benchmark import BenchmarkSuite
from tsp_solver.viz import ascii_plot, tour_to_json
from tsp_solver.config import SolverConfig

# List algorithms by category
for cat, algos in list_algorithms_by_category().items():
    print(f"{cat}: {', '.join(algos)}")

# Generate a random 50-city instance
inst = generate_instance(50, seed=42)

# Solve with Christofides + 2-opt refinement
tour = solve(inst, 'christofides', refine='two_opt')
print(f"Length: {tour.length:.2f}")

# Multi-start nearest neighbor
tour = solve(inst, 'nearest_neighbor_multistart', seed=42)

# Iterated Local Search (advanced metaheuristic)
tour = solve(inst, 'iterated_local_search', seed=42, max_iter=500)

# Lin-Kernighan (near-optimal heuristic)
tour = solve(inst, 'lin_kernighan', seed=42)

# Benchmark all algorithms with quality ratios
suite = BenchmarkSuite()
suite.run(inst, seed=42)
print(suite.summary())
print(f"Best: {suite.best()}")

# Export results
suite.to_csv("results.csv")
suite.to_json("results.json")

# ASCII visualization
tour = solve(inst, 'christofides', refine='two_opt')
print(ascii_plot(inst, tour))

# JSON export
data = tour_to_json(inst, tour)
```

### Command Line

```bash
# Solve a 30-city instance with GA
tsp-solver --algo genetic_algorithm -n 30 --seed 42 --json

# Compare all algorithms on a 20-city instance
tsp-solver --compare -n 20 --seed 1

# Benchmark with quality ratios and export CSV
tsp-solver --benchmark -n 15 --seed 42 --csv results.csv

# Visualize the tour
tsp-solver --algo christofides -n 15 --seed 1 --plot

# Load a TSPLIB file
tsp-solver --load instance.tsp --algo christofides --refine two_opt

# Save a generated instance to TSPLIB format
tsp-solver --algo nearest_neighbor -n 50 --save my_instance.tsp

# Use clustered distribution (harder instances)
tsp-solver --algo iterated_local_search -n 30 --distribution cluster --seed 42

# List algorithms by category
tsp-solver --list-categories

# Use a config file
tsp-solver --config config.yaml --json

# Verbose logging
tsp-solver --algo lin_kernighan -n 40 --seed 42 -v
```

### Configuration Files

The CLI and API support loading configuration from YAML or JSON files.

**YAML config (`config.yaml`):**

```yaml
algorithm: christofides
refine: two_opt
seed: 42
n: 100
grid: 1000
output: json
log_level: INFO
algorithm_params:
  genetic_algorithm:
    population_size: 200
    generations: 1000
  simulated_annealing:
    initial_temp: 200.0
    cooling_rate: 0.999
```

**JSON config (`config.json`):**

```json
{
  "algorithm": "held_karp",
  "n": 15,
  "seed": 1
}
```

**Auto-discovery:** The CLI automatically looks for `tsp-solver.yaml`,
`tsp-solver.yml`, `tsp-solver.json`, `~/.tsp-solver.yaml`, or
`~/.tsp-solver.json` if no `--config` flag is given.

**Python API:**

```python
from tsp_solver.config import SolverConfig

# Load from file
cfg = SolverConfig.from_file("config.yaml")

# Use config to solve
from tsp_solver.instance import generate_instance
from tsp_solver.solver import solve

inst = generate_instance(cfg.n, seed=cfg.seed)
tour = solve(inst, cfg.algorithm, refine=cfg.refine, seed=cfg.seed)
```

---

## Architecture

```
                        ┌─────────────────────────────────────────────┐
                        │                  CLI / API                   │
                        │         (tsp_solver/cli.py, config.py)       │
                        └───────────────────┬─────────────────────────┘
                                           │
                          ┌────────────────▼────────────────┐
                          │         solve() dispatcher       │
                          │       (tsp_solver/solver.py)     │
                          └────────────────┬────────────────┘
                                           │
          ┌────────────────┬───────────────┼───────────────┬────────────────┐
          ▼                ▼               ▼               ▼                ▼
   ┌─────────────┐ ┌──────────────┐ ┌────────────┐ ┌──────────────┐ ┌──────────────┐
   │   Exact      │ │ Approximation│ │Construction│ │  Local Search│ │Metaheuristic │
   │  exact.py    │ │approximation │ │heuristics  │ │ local_search │ │metaheuristics│
   │              │ │    .py       │ │   .py      │ │     .py      │ │   .py +      │
   │ Held-Karp    │ │ MST 2-approx │ │ NN, Insert │ │ 2/3-opt,or-opt│ │ SA, GA, ACO  │
   │ B&B          │ │ Christofides  │ │ Greedy,Sav │ │              │ │ ILS, LK      │
   └─────────────┘ └──────────────┘ └────────────┘ └──────────────┘ └──────────────┘
          │                │               │               │                │
          └────────────────┴───────────────┼───────────────┴────────────────┘
                                           │
                          ┌────────────────▼────────────────┐
                          │     TSPInstance + Tour           │
                          │  (instance.py, tour.py)          │
                          │  Distance matrix, coordinates,   │
                          │  immutable tour with cached len  │
                          └─────────────────────────────────┘
```

### Module Overview

| Module | Responsibility |
|---|---|
| `instance.py` | `TSPInstance` class, generation, TSPLIB I/O, validation |
| `tour.py` | Immutable `Tour` with cached length, edge iteration |
| `exact.py` | Held-Karp DP, Branch & Bound with MST lower bound |
| `approximation.py` | MST 2-approx, Christofides 1.5-approx |
| `heuristics.py` | NN, NN multi-start, nearest/farthest insertion, greedy |
| `local_search.py` | 2-opt, 3-opt, or-opt (first-improvement) |
| `metaheuristics.py` | Simulated Annealing, Genetic Algorithm, Ant Colony |
| `advanced.py` | Savings (Clarke-Wright), ILS, Lin-Kernighan, double-bridge |
| `solver.py` | Unified `solve()` dispatcher, algorithm registry |
| `benchmark.py` | `BenchmarkSuite` with quality ratios, CSV/JSON export |
| `viz.py` | ASCII visualization, JSON serialization |
| `config.py` | `SolverConfig` — typed config from YAML/JSON |
| `logging_util.py` | Centralized logging |
| `cli.py` | Command-line interface with config file support |

### Pipeline

```
Instance → [Construction Heuristic] → [Local Search] → [Metaheuristic] → Tour
```

The `solve()` dispatcher ties everything together, allowing any algorithm to
be followed by a local-search refinement step. The `BenchmarkSuite` runs all
algorithms on an instance, computes quality ratios against the optimal
solution, and reports timing.

---

## Examples

The `examples/` directory contains ready-to-run demo scripts:

| Script | Description |
|---|---|
| `basic_usage.py` | Getting started: generate, solve, visualize, benchmark |
| `advanced_algorithms.py` | ILS, Lin-Kernighan, Savings vs optimal |
| `config_demo.py` | Config file creation, loading, and usage |
| `benchmark_demo.py` | Multi-instance benchmarking with CSV/JSON export |

Run them with:

```bash
python3 examples/basic_usage.py
python3 examples/advanced_algorithms.py
python3 examples/config_demo.py
python3 examples/benchmark_demo.py
```

---

## Example Output

### Benchmark

```
Algorithm                       Length    Ratio     Gap%    Time(s)
-------------------------------------------------------------------
ant_colony                     2851.00   1.0000    0.00%     1.1311
branch_and_bound               2851.00   1.0000    0.00%     1.2715
christofides                   2945.00   1.0330    3.30%     0.0002
farthest_insertion             2851.00   1.0000    0.00%     0.0003
genetic_algorithm              2851.00   1.0000    0.00%     1.1570
greedy                         2851.00   1.0000    0.00%     0.0001
held_karp                      2851.00   1.0000    0.00%     0.3449
iterated_local_search          2851.00   1.0000    0.00%     0.0312
lin_kernighan                  2851.00   1.0000    0.00%     0.0187
mst_approx                     3467.00   1.2161   21.61%     0.0002
nearest_insertion              2965.00   1.0400    4.00%     0.0002
nearest_neighbor               3310.00   1.1610   16.10%     0.0000
nearest_neighbor_multistart    2851.00   1.0000    0.00%     0.0003
or_opt                         2851.00   1.0000    0.00%     0.0004
savings                        2851.00   1.0000    0.00%     0.0001
simulated_annealing            2851.00   1.0000    0.00%     0.0726
three_opt                      2851.00   1.0000    0.00%     0.0024
two_opt                        2851.00   1.0000    0.00%     0.0004
```

### ASCII Visualization

```
Tour (len=2851.00, n=15)  @=start #=city .=edge
                                     #...#.
                                   ..      #
          #...........           ..         .
          #           ..........#            .
        ..                                    .
       .                                       .
      .                                         .
    ..                                           #
   .                                            .
 ..         .#.                                .
#       ....   .#                              .
 ..  ...         .                            .
   #.             ..                        .#
                    #...........@....     ..
                                     ....#
```

### Advanced Algorithms Comparison (n=20)

```
Optimal (Held-Karp):    3524.00
Savings:                3848.00  (ratio=1.092)
Iterated Local Search:  3524.00  (ratio=1.000)
Lin-Kernighan:          3536.00  (ratio=1.003)
Nearest Neighbor:       4605.00  (ratio=1.307)
ILS (3-opt):            3524.00  (ratio=1.000)
```

---

## Testing

The project includes a comprehensive pytest test suite with **130 tests**:

```bash
# Run all tests
pytest test_suite.py -v

# Run a specific test class
pytest test_suite.py -v -k "TestExactAlgorithms"

# Run algorithm validity tests
pytest test_suite.py -v -k "TestAlgorithmValidity"

# Run edge case tests
pytest test_suite.py -v -k "TestEdgeCases"
```

### Test Coverage

| Category | Tests | Description |
|---|---|---|
| `TestInstance` | 12 | Instance creation, validation, matrix, TSPLIB I/O |
| `TestGenerateInstance` | 6 | Random generation, seeds, distributions |
| `TestTSPLIB` | 4 | Save/load TSPLIB files |
| `TestTour` | 9 | Tour operations, immutability, edges |
| `TestAlgorithmValidity` | 36 | All 18 algorithms produce valid permutations |
| `TestExactAlgorithms` | 5 | Optimality of Held-Karp and B&B |
| `TestLocalSearchNonWorsening` | 13 | Local search never worsens tours |
| `TestAdvancedAlgorithms` | 9 | Savings, ILS, LK, double-bridge |
| `TestSolver` | 7 | Dispatcher, categories, refinement |
| `TestBenchmark` | 12 | Benchmark, CSV/JSON export, multi-instance |
| `TestVisualization` | 3 | ASCII plot, JSON export |
| `TestConfig` | 8 | Config loading, saving, YAML/JSON |
| `TestEdgeCases` | 4 | n=2, n=3 edge cases |
| `TestRefinementChains` | 6 | Refinement chains improve tours |

Plus the original 72 bug hunt tests in `test_bughunt.py`.

---

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for
guidelines on adding algorithms, running tests, and submitting pull requests.

### Adding a New Algorithm

1. Implement with signature: `def my_algo(instance: TSPInstance, **kwargs) -> Tour`
2. Register in `tsp_solver/solver.py`
3. Add to the appropriate category
4. Export in `tsp_solver/__init__.py`
5. Add tests in `test_suite.py`
6. Update this README

---

## Roadmap

### Planned Features

- **Or-opt with variable segment length** (currently fixed at 1-3)
- **Candidate list / nearest-neighbor lists** for faster local search on large instances
- **LKH (Lin-Kernighan-Helsgaun)** — the state-of-the-art LK variant
- **2d matplotlib visualization** backend (optional dependency)
- **ASYM TSP support** — asymmetric distance matrices
- **ATSP (Asymmetric TSP)** algorithms (e.g., transformed to symmetric)
- **Concorde interface** — optional wrapper for the Concorde exact solver
- **Parallel metaheuristics** — multi-start with multiprocessing
- **Tour comparison** — visualize differences between two tours
- **Progress bars** — tqdm integration for long-running algorithms
- **Web interface** — Flask/Streamlit dashboard for interactive solving

### Performance Optimizations

- Vectorized nearest-neighbor using NumPy argmin
- Don't-look bits for 2-opt/3-opt
- Granular neighborhood for large instances
- Cython/Numba JIT compilation for hot loops

---

## Changelog

### v2.0.0 (2026-07-20) — Comprehensive Improvement

**New Algorithms (+3):**
- **Savings (Clarke-Wright)** construction heuristic
- **Iterated Local Search (ILS)** with double-bridge perturbation
- **Lin-Kernighan** simplified variable-depth heuristic

**New Features:**
- YAML/JSON configuration file support (`tsp_solver/config.py`)
- Centralized logging system (`tsp_solver/logging_util.py`)
- CSV export for benchmark results
- Multi-instance benchmarking (`BenchmarkSuite.run_instances`)
- TSPLIB EDGE_WEIGHT_SECTION loading (explicit matrices)
- `save_tsplib` for writing instances to TSPLIB format
- Clustered distribution for random instances
- Algorithm category system (`list_algorithms_by_category`)
- Enhanced CLI with `--config`, `--csv`, `--list-categories`, `--save`, `--distribution`
- Auto-discovery of config files

**Architecture:**
- Split monolithic code into cleaner modules
- Added comprehensive type hints throughout
- Input validation on `tour_length` (permutation check)
- `TSPInstance.__eq__` and `__hash__` for instance comparison
- Better error messages with context

**Testing:**
- New comprehensive pytest suite: **130 tests** (`test_suite.py`)
- All 18 algorithms tested for validity and non-worsening
- Edge case coverage (n=2, n=3)
- Config file I/O tests

**Documentation & Infrastructure:**
- Dramatically improved README with TOC, badges, architecture diagram
- `CONTRIBUTING.md` with development workflow
- `LICENSE` (MIT)
- GitHub Actions CI workflow (Python 3.9-3.12)
- `examples/` directory with 4 demo scripts
- PyPI metadata with classifiers and optional dependencies

### v1.0.0 — Initial Release

- 15 algorithms: Held-Karp, B&B, MST approx, Christofides, NN, NN multi-start,
  nearest/farthest insertion, greedy, 2-opt, 3-opt, or-opt, SA, GA, ACO
- BenchmarkSuite with quality ratios
- ASCII visualization
- JSON export
- TSPLIB loader
- pip-installable
- 72 bug hunt tests

---

## Known Issues (Resolved)

All bugs found during the bug hunt phase (v1.0.0) have been fixed and verified
with automated tests.

### Bug 1: 2-opt wrap-around edge handling (Critical)
**Symptom:** 2-opt could *worsen* a tour due to incorrect handling of the
wrap-around edge.

**Fix:** Rewrote 2-opt to use modular indexing for all edge lookups, naturally
handling the wrap-around edge. Uses first-improvement strategy.

### Bug 2: or-opt delta sign error (Critical)
**Symptom:** or-opt could *worsen* a tour despite the delta calculation
indicating improvement.

**Fix:** Changed `delta = insert_cost + removed_cost` to
`delta = -removed_cost + insert_cost`.

### Bug 3: Branch & Bound returning suboptimal tours (Critical)
**Symptom:** B&B returned the identity permutation when NN was already optimal.

**Fix:** Initialize `best_order` with the actual nearest-neighbor tour.

### Bug 4: Branch & Bound lower bound was incorrect (Major)
**Symptom:** B&B found suboptimal solutions for several instances.

**Fix:** Replaced with a valid lower bound: path cost + min edge to unvisited +
MST of unvisited + min edge back to start.

### Bug 5: 3-opt case application was incorrect (Major)
**Symptom:** 3-opt could produce invalid results due to incorrect segment
reordering.

**Fix:** Rewrote 3-opt with correct, verified reconnection cases and
first-improvement strategy.

---

## License

[MIT](LICENSE) — see the LICENSE file for details.