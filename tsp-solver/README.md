# tsp-solver

A comprehensive Traveling Salesman Problem (TSP) solver implementing **14 algorithms** spanning exact, approximation, construction-heuristic, local-search, and metaheuristic categories. Pure Python with NumPy for vectorized distance computation.

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

The `solve()` dispatcher ties everything together, allowing any algorithm to be followed by a local-search refinement step.

## Installation

```bash
cd tsp-solver
python3 -m venv venv && source venv/bin/activate
pip install numpy
```

## Usage

### Python API

```python
from tsp_solver.instance import generate_instance
from tsp_solver.solver import solve, list_algorithms

# Generate a random 50-city instance
inst = generate_instance(50, seed=42)

# List all algorithms
print(list_algorithms())

# Solve with Christofides + 2-opt refinement
tour = solve(inst, 'christofides', refine='two_opt')
print(f"Length: {tour.length:.2f}")
print(f"Tour: {list(tour.order)}")

# Compare with exact (small instances only)
small = generate_instance(12, seed=1)
optimal = solve(small, 'held_karp')
approx = solve(small, 'mst_approx')
print(f"OPT={optimal.length}, MST ratio={approx.length/optimal.length:.3f}")
```

### Command Line

```bash
# Solve a 30-city instance with GA
python3 -m tsp_solver.cli --algo genetic_algorithm --n 30 --seed 42 --json

# Compare all algorithms on a 20-city instance
python3 -m tsp_solver.cli --compare --n 20 --seed 1

# Load a TSPLIB file
python3 -m tsp_solver.cli --load instance.tsp --algo christofides --refine two_opt

# List available algorithms
python3 -m tsp_solver.cli --list
```

## Example Output

```
Algorithm                Length    Ratio
ant_colony               2642.00   1.000
branch_and_bound         2642.00   1.000
christofides             2643.00   1.000
farthest_insertion       2642.00   1.000
genetic_algorithm        2642.00   1.000
greedy                   2643.00   1.000
held_karp                2642.00   1.000
mst_approx               2948.00   1.116
nearest_neighbor         2948.00   1.116
simulated_annealing      2642.00   1.000
two_opt                  2642.00   1.000
```

## File Structure

```
tsp-solver/
├── tsp_solver/
│   ├── __init__.py          # Package API
│   ├── instance.py          # TSPInstance, generate_instance, load_tsplib
│   ├── tour.py              # Immutable Tour with cached length
│   ├── exact.py             # Held-Karp, Branch & Bound
│   ├── heuristics.py        # NN, nearest/farthest insertion, greedy
│   ├── local_search.py     # 2-opt, 3-opt, or-opt
│   ├── metaheuristics.py   # SA, GA, ACO
│   ├── approximation.py    # MST 2-approx, Christofides
│   ├── solver.py           # Unified solve() dispatcher
│   └── cli.py              # Command-line interface
├── test_smoke.py           # Smoke test
└── README.md
```