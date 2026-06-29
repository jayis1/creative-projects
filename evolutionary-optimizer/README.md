# EvOpt — Evolutionary Optimization Toolkit

A from-scratch evolutionary optimization toolkit implementing five major algorithms with a clean, modular architecture. Pure Python, no external dependencies.

## Features

### Algorithms
1. **Genetic Algorithm (GA)** — Classic GA with elitism, tournament selection, auto-detection of genome type (continuous/binary/permutation), and appropriate crossover/mutation operators for each.
2. **Evolution Strategy (ES)** — (µ+λ)-ES and (µ,λ)-ES with self-adaptive step sizes using the standard log-normal update rule.
3. **Differential Evolution (DE)** — Storn & Price's DE with 5 mutation strategies (rand/1, best/1, rand/2, best/2, current-to-best/1) and binomial/exponential crossover.
4. **Particle Swarm Optimization (PSO)** — Kennedy & Eberhart's PSO with inertia weight, cognitive/social coefficients, and velocity clamping.
5. **NSGA-II** — Deb et al.'s multi-objective optimizer with fast non-dominated sorting, crowding distance, and Pareto front extraction.

### Problems
- **Sphere** — Unimodal benchmark: f(x) = Σxᵢ²
- **Rastrigin** — Highly multimodal: f(x) = 10n + Σ(xᵢ² - 10cos(2πxᵢ))
- **Rosenbrock** — The "banana" function: f(x) = Σ100(xᵢ₊₁ - xᵢ²)² + (1 - xᵢ)²
- **TSP** — Euclidean Traveling Salesman Problem with precomputed distance matrix
- **Knapsack** — 0/1 Knapsack with capacity constraints
- **ZDT1/ZDT2** — Multi-objective benchmarks with known Pareto fronts

### Operators
- **Selection**: Tournament, Roulette wheel, Rank-based (linear), Stochastic Universal Sampling (SUS)
- **Crossover**: Uniform, One-point, Two-point, BLX-α, SBX (Simulated Binary), Order (OX), Cycle (CX), PMX
- **Mutation**: Gaussian, Polynomial, Bit-flip, Swap, Random-reset, Inversion, Insert, Scramble

## Architecture

```
evopt/
├── core.py              # Individual, Population, random_population
├── algorithms/          # 5 algorithm implementations + base class
│   ├── base.py           # BaseAlgorithm: run loop, statistics, callbacks
│   ├── ga.py             # GeneticAlgorithm
│   ├── es.py             # EvolutionStrategy (self-adaptive)
│   ├── de.py             # DifferentialEvolution (5 strategies)
│   ├── pso.py            # ParticleSwarmOptimizer
│   └── nsga2.py          # NSGA2 + MultiObjectiveProblem
├── problems/             # Problem definitions
│   ├── base.py           # Problem, ContinuousProblem, CombinatorialProblem
│   ├── sphere.py         # Sphere function
│   ├── rastrigin.py      # Rastrigin function
│   ├── rosenbrock.py     # Rosenbrock function
│   ├── tsp.py            # Traveling Salesman Problem
│   ├── knapsack.py       # 0/1 Knapsack
│   └── multi_objective.py # ZDT1, ZDT2
├── operators/            # Selection, crossover, mutation operators
│   ├── selection.py      # tournament, roulette, rank, SUS
│   ├── crossover.py      # uniform, 1-point, 2-point, BLX, SBX, OX, CX, PMX
│   └── mutation.py       # Gaussian, polynomial, bit-flip, swap, etc.
├── utils/                # Statistics tracking, logging
├── cli.py                # Command-line interface
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
from evopt.algorithms.nsga2 import NSGA2
from evopt.problems.multi_objective import ZDT1

# Multi-objective optimization
nsga = NSGA2(ZDT1(dims=10), population_size=100, max_generations=100, seed=42)
nsga.run()
print(f"Pareto front size: {len(nsga.pareto_front)}")
for ind in nsga.pareto_front[:5]:
    print(f"  Objectives: {ind.metadata['objectives']}")
```

```python
from evopt import TSP, GeneticAlgorithm

# Solve TSP
tsp = TSP.random_cities(n=20, seed=42)
ga = GeneticAlgorithm(tsp, population_size=100, max_generations=200, seed=42)
best = ga.run()
print(f"Best tour length: {best.fitness:.2f}")
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

# Benchmark all algorithms on the same problem
python -m evopt.cli benchmark --problem rastrigin --dims 3 --generations 50

# List available problems and algorithms
python -m evopt.cli list
```

### Custom Problems

```python
from evopt.problems.base import ContinuousProblem

class Ackley(ContinuousProblem):
    """Ackley function — another classic benchmark."""
    def __init__(self, dims=2):
        super().__init__(dims=dims, bounds=(-32.768, 32.768))

    def evaluate(self, genome):
        import math
        n = len(genome)
        sum_sq = sum(x**2 for x in genome)
        sum_cos = sum(math.cos(2 * math.pi * x) for x in genome)
        return -20 * math.exp(-0.2 * math.sqrt(sum_sq / n)) \
               - math.exp(sum_cos / n) + 20 + math.e

# Use with any algorithm
from evopt import GeneticAlgorithm
ga = GeneticAlgorithm(Ackley(dims=3), population_size=50, max_generations=100, seed=42)
best = ga.run()
```

### Callbacks

```python
def early_stop(algo):
    """Stop if fitness hasn't improved in 10 generations."""
    if len(algo.history) > 10:
        recent = [h['best_fitness'] for h in algo.history[-10:]]
        if max(recent) - min(recent) < 1e-8:
            algo.max_generations = algo.generation  # force termination

ga = GeneticAlgorithm(Sphere(dims=3), callbacks=[early_stop], seed=42)
best = ga.run()
```

## Installation

```bash
cd evolutionary-optimizer
pip install -e .
```

Or simply add the directory to your Python path — no dependencies required.