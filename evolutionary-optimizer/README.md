# EvOpt — Evolutionary Optimization Toolkit

A from-scratch evolutionary optimization toolkit implementing seven algorithms with a clean, modular architecture. Pure Python, no external dependencies.

## Features

### Algorithms (7)
1. **Genetic Algorithm (GA)** — Classic GA with elitism, tournament selection, auto-detection of genome type (continuous/binary/permutation), and appropriate crossover/mutation operators for each.
2. **Evolution Strategy (ES)** — (µ+λ)-ES and (µ,λ)-ES with self-adaptive step sizes using the standard log-normal update rule.
3. **Differential Evolution (DE)** — Storn & Price's DE with 5 mutation strategies (rand/1, best/1, rand/2, best/2, current-to-best/1) and binomial/exponential crossover.
4. **Particle Swarm Optimization (PSO)** — Kennedy & Eberhart's PSO with inertia weight, cognitive/social coefficients, and velocity clamping.
5. **NSGA-II** — Deb et al.'s multi-objective optimizer with fast non-dominated sorting, crowding distance, and Pareto front extraction.
6. **Island Model GA** — Parallel subpopulations with periodic migration (ring/random/fully-connected topologies) for enhanced diversity.
7. **Memetic Algorithm** — GA with local search (hill climbing) refinement of offspring for combined global exploration + local exploitation.

### Problems (11)
- **Sphere** — Unimodal benchmark: f(x) = Σxᵢ²
- **Rastrigin** — Highly multimodal: f(x) = 10n + Σ(xᵢ² - 10cos(2πxᵢ))
- **Rosenbrock** — The "banana" function: f(x) = Σ100(xᵢ₊₁ - xᵢ²)² + (1 - xᵢ)²
- **Ackley** — Multimodal with deep global minimum
- **Griewank** — Many local minima, single global minimum
- **Schwefel** — Deceptive landscape with global minimum far from origin
- **Michalewicz** — Steep valleys and ridges
- **Zakharov** — Unimodal with a narrow valley
- **TSP** — Euclidean Traveling Salesman Problem with precomputed distance matrix
- **Knapsack** — 0/1 Knapsack with capacity constraints and repair operator
- **ZDT1/ZDT2** — Multi-objective benchmarks with known Pareto fronts

### Operators
- **Selection (4)**: Tournament, Roulette wheel, Rank-based (linear), Stochastic Universal Sampling (SUS)
- **Crossover (8)**: Uniform, One-point, Two-point, BLX-α, SBX (Simulated Binary), Order (OX), Cycle (CX), PMX
- **Mutation (8)**: Gaussian, Polynomial, Bit-flip, Swap, Random-reset, Inversion, Insert, Scramble

### Callbacks & Termination Criteria
- **MaxGenerations** — Stop after N generations
- **FitnessThreshold** — Stop when fitness reaches a target
- **Stagnation** — Stop if no improvement for N generations
- **TimeLimit** — Wall-clock time limit
- **Convergence** — Stop when population variance drops below threshold
- **AdaptiveMutationRate** — Dynamically adjust mutation rate based on diversity
- **AdaptiveInertia** — Linearly decrease PSO inertia weight over time

### Visualization
- **ASCII Convergence Plot** — Best/avg fitness over generations
- **ASCII Pareto Front** — 2-objective scatter plot
- **ASCII Diversity Plot** — Population diversity over time

## Architecture

```
evopt/
├── core.py              # Individual, Population, random_population
├── algorithms/          # 7 algorithm implementations + base class
│   ├── base.py           # BaseAlgorithm: run loop, statistics, callbacks
│   ├── ga.py             # GeneticAlgorithm
│   ├── es.py             # EvolutionStrategy (self-adaptive)
│   ├── de.py             # DifferentialEvolution (5 strategies)
│   ├── pso.py            # ParticleSwarmOptimizer
│   ├── nsga2.py          # NSGA2 + MultiObjectiveProblem
│   ├── island_model.py   # IslandModelGA (parallel subpopulations)
│   └── memetic.py        # MemeticAlgorithm (GA + local search)
├── problems/             # Problem definitions
│   ├── base.py           # Problem, ContinuousProblem, CombinatorialProblem
│   ├── sphere.py         # Sphere function
│   ├── rastrigin.py      # Rastrigin function
│   ├── rosenbrock.py     # Rosenbrock function
│   ├── benchmarks.py     # Ackley, Griewank, Schwefel, Michalewicz, Zakharov
│   ├── tsp.py            # Traveling Salesman Problem
│   ├── knapsack.py       # 0/1 Knapsack
│   └── multi_objective.py # ZDT1, ZDT2
├── operators/            # Selection, crossover, mutation operators
│   ├── selection.py      # tournament, roulette, rank, SUS
│   ├── crossover.py      # uniform, 1-point, 2-point, BLX, SBX, OX, CX, PMX
│   └── mutation.py       # Gaussian, polynomial, bit-flip, swap, etc.
├── utils/                # Statistics, visualization, callbacks, logging
│   ├── statistics.py     # Per-generation statistics tracking
│   ├── visualization.py  # ASCII convergence/Pareto/diversity plots
│   ├── callbacks.py       # Termination criteria & adaptive operators
│   └── logging_utils.py  # Configurable logging
├── cli.py                # Command-line interface (solve/benchmark/plot/list)
└── __main__.py           # Module entry point
```

## Usage

### Python API

```python
from evopt import GeneticAlgorithm, Sphere, Rastrigin

# Solve Sphere with GA
problem = Sphere(dims=5)
ga = GeneticAlgorithm(problem, population_size=50, max_generations=100, seed=42)
best = ga.run()
print(f"Best fitness: {best.fitness}")
print(f"Best solution: {best.genome}")

# View statistics
print(ga.statistics.summary())
```

```python
from evopt import DifferentialEvolution, Rastrigin

# DE with best/1 strategy
de = DifferentialEvolution(
    Rastrigin(dims=5),
    population_size=50, max_generations=200,
    F=0.8, CR=0.9, strategy='best/1',
    seed=42
)
best = de.run()
```

```python
from evopt import IslandModelGA, Rastrigin

# Island model with 4 islands, ring topology migration
island = IslandModelGA(
    Rastrigin(dims=5),
    num_islands=4, island_size=25,
    max_generations=100,
    migration_interval=10, migration_rate=0.1,
    topology='ring', seed=42
)
best = island.run()
```

```python
from evopt import MemeticAlgorithm, Ackley

# Memetic algorithm: GA + local search
memetic = MemeticAlgorithm(
    Ackley(dims=3),
    population_size=50, max_generations=100,
    local_search_rate=0.1, local_search_steps=10,
    seed=42
)
best = memetic.run()
```

```python
from evopt import NSGA2
from evopt.problems.multi_objective import ZDT1

# Multi-objective optimization
nsga = NSGA2(ZDT1(dims=10), population_size=100, max_generations=100, seed=42)
nsga.run()
print(f"Pareto front size: {len(nsga.pareto_front)}")
for ind in nsga.pareto_front[:5]:
    print(f"  Objectives: {ind.metadata['objectives']}")
```

```python
from evopt import GeneticAlgorithm, Sphere, Stagnation, AdaptiveMutationRate

# Use callbacks for early stopping and adaptive mutation
ga = GeneticAlgorithm(
    Sphere(dims=3), population_size=50, max_generations=200, seed=42,
    callbacks=[Stagnation(patience=20), AdaptiveMutationRate()]
)
best = ga.run()
print(f"Terminated: {ga.termination_reason}")
```

```python
from evopt import GeneticAlgorithm, Sphere
from evopt.utils.visualization import ascii_convergence_plot

# Visualize convergence
ga = GeneticAlgorithm(Sphere(dims=2), population_size=50, max_generations=100, seed=42)
ga.run()
print(ascii_convergence_plot(ga.history, title="My Convergence"))
```

### CLI

```bash
# Solve a problem with a specific algorithm
python -m evopt.cli solve --algorithm ga --problem sphere --dims 3 --generations 100
python -m evopt.cli solve --algorithm de --problem rastrigin --dims 5 --generations 200
python -m evopt.cli solve --algorithm pso --problem rosenbrock --dims 3
python -m evopt.cli solve --algorithm es --problem sphere --dims 2 --generations 50
python -m evopt.cli solve --algorithm nsga2 --problem zdt1 --dims 5 --generations 50
python -m evopt.cli solve --algorithm ga --problem tsp --cities 15 --generations 200
python -m evopt.cli solve --algorithm island --problem rastrigin --dims 3 --generations 100
python -m evopt.cli solve --algorithm memetic --problem ackley --dims 2 --generations 50

# Benchmark all algorithms on the same problem
python -m evopt.cli benchmark --problem rastrigin --dims 3 --generations 50

# Run and display ASCII plots
python -m evopt.cli plot --algorithm ga --problem sphere --dims 3 --generations 50
python -m evopt.cli plot --algorithm nsga2 --problem zdt1 --dims 5 --generations 50

# List available problems and algorithms
python -m evopt.cli list
```

### Custom Problems

```python
from evopt.problems.base import ContinuousProblem
import math

class Beale(ContinuousProblem):
    """Beale function — 2D unimodal benchmark."""
    def __init__(self):
        super().__init__(dims=2, bounds=(-4.5, 4.5))

    def evaluate(self, genome):
        x, y = genome
        return ((1.5 - x + x*y)**2 + (2.25 - x + x*y**2)**2
                + (2.625 - x + x*y**3)**2)

# Use with any algorithm
from evopt import GeneticAlgorithm
ga = GeneticAlgorithm(Beale(), population_size=50, max_generations=100, seed=42)
best = ga.run()
```

### Custom Multi-Objective Problems

```python
from evopt.problems.base import Problem
from evopt.algorithms.nsga2 import MultiObjectiveProblem

class MyProblem(MultiObjectiveProblem):
    def __init__(self):
        super().__init__(maximize_list=[False, True])  # min f1, max f2
        self.bounds = [(0, 1), (0, 1)]

    def evaluate_multi(self, genome):
        return [genome[0]**2, genome[1]**2]  # two objectives

    def random_genome(self):
        import random
        return [random.uniform(0, 1), random.uniform(0, 1)]

    def genome_size(self):
        return 2
```

## Installation

```bash
cd evolutionary-optimizer
pip install -e .
```

Or simply add the directory to your Python path — no dependencies required.