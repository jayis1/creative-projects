# tsp-solver

A comprehensive Traveling Salesman Problem (TSP) solver implementing **15 algorithms** spanning exact, approximation, construction-heuristic, local-search, and metaheuristic categories. Pure Python with NumPy for vectorized distance computation.

## Algorithms

### Exact (guarantee optimal solution)
| Algorithm | Complexity | Feasible n |
|---|---|---|
| **Held-Karp** (dynamic programming) | O(n²·2ⁿ) time, O(n·2ⁿ) space | n ≤ ~22 |
| **Branch & Bound** (DFS with pruning) | O(n!) worst case, much better with good bounds | n ≤ ~18 |

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

## How It Works

Each algorithm operates on a `TSPInstance` (holding either coordinates or an explicit distance matrix) and produces a `Tour` (an immutable, length-cached permutation).

**Pipeline:** `Instance → [Construction Heuristic] → [Local Search] → [Metaheuristic] → Tour`

The `solve()` dispatcher ties everything together, allowing any algorithm to be followed by a local-search refinement step. The `BenchmarkSuite` runs all algorithms on an instance, computes quality ratios against the optimal solution, and reports timing.

## Installation

```bash
cd tsp-solver
python3 -m venv venv && source venv/bin/activate
pip install -e .
```

## Usage

### Python API

```python
from tsp_solver.instance import generate_instance
from tsp_solver.solver import solve, list_algorithms
from tsp_solver.benchmark import BenchmarkSuite
from tsp_solver.viz import ascii_plot

# Generate a random 50-city instance
inst = generate_instance(50, seed=42)

# Solve with Christofides + 2-opt refinement
tour = solve(inst, 'christofides', refine='two_opt')
print(f"Length: {tour.length:.2f}")

# Multi-start nearest neighbor
tour = solve(inst, 'nearest_neighbor_multistart', seed=42)
print(f"Length: {tour.length:.2f}")

# Benchmark all algorithms with quality ratios
suite = BenchmarkSuite()
suite.run(inst, seed=42)
print(suite.summary())
print(f"Best: {suite.best()}")

# ASCII visualization
print(ascii_plot(inst, tour))
```

### Command Line

```bash
# Solve a 30-city instance with GA
tsp-solver --algo genetic_algorithm --n 30 --seed 42 --json

# Compare all algorithms on a 20-city instance
tsp-solver --compare --n 20 --seed 1

# Benchmark with quality ratios
tsp-solver --benchmark --n 15 --seed 42

# Visualize the tour
tsp-solver --algo christofides --n 15 --seed 1 --plot

# Load a TSPLIB file
tsp-solver --load instance.tsp --algo christofides --refine two_opt

# List available algorithms
tsp-solver --list
```

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
mst_approx                     3467.00   1.2161   21.61%     0.0002
nearest_insertion              2965.00   1.0400    4.00%     0.0002
nearest_neighbor               3310.00   1.1610   16.10%     0.0000
nearest_neighbor_multistart    2851.00   1.0000    0.00%     0.0003
simulated_annealing            2851.00   1.0000    0.00%     0.0726
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

## Features

- **15 algorithms** across 5 categories (exact, approximation, heuristic, local search, metaheuristic)
- **Refinement chaining**: apply 2-opt/3-opt/or-opt after any algorithm
- **BenchmarkSuite**: run all algorithms, compute quality ratios and timing
- **ASCII visualization**: render tours as ASCII art
- **JSON export**: serialize tours and instances
- **TSPLIB loader**: load `.tsp` files with `NODE_COORD_SECTION`
- **NumPy-backed**: vectorized distance matrix computation
- **pip-installable**: `pyproject.toml` with entry point `tsp-solver`

## File Structure

```
tsp-solver/
├── tsp_solver/
│   ├── __init__.py          # Package API
│   ├── instance.py          # TSPInstance, generate_instance, load_tsplib
│   ├── tour.py              # Immutable Tour with cached length
│   ├── exact.py             # Held-Karp, Branch & Bound
│   ├── heuristics.py        # NN, NN multistart, nearest/farthest insertion, greedy
│   ├── local_search.py     # 2-opt, 3-opt, or-opt
│   ├── metaheuristics.py   # SA, GA, ACO
│   ├── approximation.py    # MST 2-approx, Christofides
│   ├── solver.py           # Unified solve() dispatcher
│   ├── benchmark.py        # BenchmarkSuite with quality ratios
│   ├── viz.py              # ASCII plot + JSON export
│   └── cli.py              # Command-line interface
├── pyproject.toml          # pip-installable package
├── test_smoke.py           # Smoke test
├── test_enhanced.py        # Enhanced feature test
└── README.md
```