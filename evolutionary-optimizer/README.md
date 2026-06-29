<div align="center">

# EvOpt — Evolutionary Optimization Toolkit

**A from-scratch evolutionary optimization toolkit implementing 9 algorithms
with multi-objective support, configuration files, performance indicators,
and batch experiments. Pure Python with optional NumPy support.**

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Tests](https://img.shields.io/badge/tests-82%20passing-brightgreen.svg)
![Algorithms](https://img.shields.io/badge/algorithms-9-orange.svg)
![Problems](https://img.shields.io/badge/problems-12-purple.svg)
![No Dependencies](https://img.shields.io/badge/dependencies-minimal-yellow.svg)

</div>

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Python API](#python-api)
- [CLI Reference](#cli-reference)
- [Configuration Files](#configuration-files)
- [Multi-Objective Optimization](#multi-objective-optimization)
- [Performance Indicators](#performance-indicators)
- [Batch Experiments](#batch-experiments)
- [Architecture](#architecture)
- [Examples](#examples)
- [Testing](#testing)
- [Known Issues (Resolved)](#known-issues-resolved)
- [Changelog](#changelog)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

EvOpt is a comprehensive evolutionary optimization toolkit built entirely from
scratch in pure Python. It provides 9 optimization algorithms, 12 benchmark
problems, 20+ genetic operators, multi-objective optimization with NSGA-II,
performance indicators (hypervolume, IGD, GD, spacing, spread), configuration
file support (YAML/JSON), batch experiments, parameter sweeps, and an ASCII
visualization system — all with zero required external dependencies.

Whether you're researching metaheuristics, solving engineering optimization
problems, or learning about evolutionary algorithms, EvOpt provides a clean,
well-documented, and extensible platform.

## Features

### Algorithms (9)

| # | Algorithm | Type | Key Features |
|---|-----------|------|-------------|
| 1 | **Genetic Algorithm (GA)** | Single-objective | Elitism, tournament selection, auto-detects genome type (continuous/binary/permutation) |
| 2 | **Evolution Strategy (ES)** | Single-objective | (µ+λ) and (µ,λ) with self-adaptive step sizes (log-normal update) |
| 3 | **Differential Evolution (DE)** | Single-objective | 5 mutation strategies, binomial/exponential crossover |
| 4 | **Particle Swarm Optimization (PSO)** | Single-objective | Inertia weight, cognitive/social coefficients, velocity clamping |
| 5 | **NSGA-II** | Multi-objective | Fast non-dominated sorting, crowding distance, Pareto front extraction |
| 6 | **Island Model GA** | Single-objective | Parallel subpopulations with migration (ring/random/fully-connected) |
| 7 | **Memetic Algorithm** | Single-objective | GA + local search (hill climbing) refinement |
| 8 | **CMA-ES** | Single-objective | Covariance Matrix Adaptation ES — state-of-the-art for ill-conditioned problems |
| 9 | **Simulated Annealing** | Single-objective | 3 cooling schedules, custom move functions, reheat on stagnation |

### Problems (12)

- **Continuous (8):** Sphere, Rastrigin, Rosenbrock, Ackley, Griewank, Schwefel,
  Michalewicz, Zakharov
- **Combinatorial (2):** TSP (Euclidean, precomputed distances), Knapsack (0/1 with repair)
- **Multi-objective (2):** ZDT1, ZDT2 (with known Pareto fronts)

### Operators (20+)

- **Selection (4):** Tournament, Roulette wheel, Rank-based (linear), SUS
- **Crossover (8):** Uniform, One-point, Two-point, BLX-α, SBX, Order (OX),
  Cycle (CX), PMX
- **Mutation (8):** Gaussian, Polynomial, Bit-flip, Swap, Random-reset,
  Inversion, Insert, Scramble

### Callbacks & Termination (7)

- `MaxGenerations`, `FitnessThreshold`, `Stagnation`, `TimeLimit`,
  `Convergence`, `AdaptiveMutationRate`, `AdaptiveInertia`

### Performance Indicators (5)

- **Hypervolume (HV)** — dominated objective space volume
- **IGD** — Inverted Generational Distance (convergence + diversity)
- **GD** — Generational Distance (convergence)
- **Spacing** — distribution uniformity
- **Spread (Δ)** — diversity metric

### Visualization

- ASCII convergence plot (best/avg fitness over generations)
- ASCII Pareto front scatter plot (2 objectives)
- ASCII diversity plot (population diversity over time)

## Installation

### From source (recommended)

```bash
cd evolutionary-optimizer
pip install -e .
```

### With optional dependencies

```bash
# For CMA-ES and multi-objective indicators (NumPy):
pip install -e . numpy

# For YAML config file support:
pip install -e . pyyaml

# For development:
pip install -e . numpy pyyaml pytest
```

### No installation (add to path)

```bash
export PYTHONPATH=/path/to/evolutionary-optimizer:$PYTHONPATH
```

**Requirements:** Python 3.8+. No mandatory dependencies. NumPy and PyYAML
are optional (required for CMA-ES, hypervolume computation, and YAML configs).

## Quick Start

### Python API (30 seconds)

```python
from evopt import GeneticAlgorithm, Sphere

# Solve the Sphere function with a Genetic Algorithm
problem = Sphere(dims=5)
ga = GeneticAlgorithm(problem, population_size=50, max_generations=100, seed=42)
best = ga.run()

print(f"Best fitness: {best.fitness}")  # ~0.001
print(f"Best solution: {best.genome}")
```

### CLI (30 seconds)

```bash
# Solve a problem
python -m evopt.cli solve --algorithm cmaes --problem sphere --dims 3 --generations 50

# Benchmark all algorithms on the same problem
python -m evopt.cli benchmark --problem rastrigin --dims 3 --generations 50

# Multi-objective with Pareto front plot
python -m evopt.cli plot --algorithm nsga2 --problem zdt1 --dims 5 --generations 50

# Run from a config file
python -m evopt.cli config run config.yaml

# List available algorithms and problems
python -m evopt.cli list
```

## Python API

### Single-Objective Optimization

```python
from evopt import (
    GeneticAlgorithm, DifferentialEvolution, EvolutionStrategy,
    ParticleSwarmOptimizer, CMAES, SimulatedAnnealing,
    Sphere, Rastrigin, Rosenbrock, Ackley,
)

# --- Genetic Algorithm ---
ga = GeneticAlgorithm(
    Rastrigin(dims=5), population_size=50, max_generations=200,
    crossover_rate=0.9, mutation_rate=0.05, elite_size=2,
    seed=42,
)
best = ga.run()

# --- Differential Evolution (5 strategies) ---
de = DifferentialEvolution(
    Rastrigin(dims=5), population_size=50, max_generations=200,
    F=0.8, CR=0.9, strategy='best/1',  # or 'rand/1', 'rand/2', 'best/2', 'current-to-best/1'
    seed=42,
)
best = de.run()

# --- CMA-ES (best for ill-conditioned problems) ---
cma = CMAES(
    Ackley(dims=5), max_generations=100, seed=42,
)
best = cma.run()

# --- Simulated Annealing ---
sa = SimulatedAnnealing(
    Rastrigin(dims=2), max_generations=500,
    initial_temperature=5.0, cooling_schedule='geometric',
    cooling_rate=0.995, seed=42,
)
best = sa.run()
print(f"Acceptance rate: {sa.acceptance_rate:.1%}")
```

### Using Callbacks

```python
from evopt import GeneticAlgorithm, Sphere, Stagnation, AdaptiveMutationRate, TimeLimit

ga = GeneticAlgorithm(
    Sphere(dims=3), population_size=50, max_generations=500, seed=42,
    callbacks=[
        Stagnation(patience=30),
        AdaptiveMutationRate(low_diversity=0.1, high_diversity=0.5),
        TimeLimit(seconds=10),
    ],
)
best = ga.run()
print(f"Terminated: {ga.termination_reason}")
```

### Visualization

```python
from evopt import GeneticAlgorithm, Sphere
from evopt.utils.visualization import ascii_convergence_plot, diversity_plot

ga = GeneticAlgorithm(Sphere(dims=2), population_size=50, max_generations=100, seed=42)
ga.run()

print(ascii_convergence_plot(ga.history, title="Convergence"))
print(diversity_plot(ga.history, title="Diversity"))
```

Output:
```
Convergence
   17.4938 │·
   14.9947 │
   12.4955 │  ·
    9.9964 │
    7.4973 │   ·
    4.9982 │
    2.4991 │●●● ··
    1.2496 │   ●●●●●●●●●●●●●●●●●●●●●
    0.0000 │                         ●
           └────────────────────────────────────────────────────────────
            Gen 0                                                Gen 100
```

## CLI Reference

### `solve` — Solve a problem

```bash
python -m evopt.cli solve \
    --algorithm ga \          # Algorithm: ga, es, de, pso, nsga2, island, memetic, cmaes, sa
    --problem sphere \        # Problem: sphere, rastrigin, rosenbrock, ackley, ...
    --dims 3 \                # Problem dimensions
    --population 50 \         # Population size
    --generations 100 \       # Max generations
    --seed 42 \               # Random seed
    --verbose \               # Verbose output
    --json \                  # Output as JSON
    --plot \                  # Show ASCII convergence plot
    --output result.json      # Save result to file (.json or .csv)
```

### `benchmark` — Compare all algorithms

```bash
python -m evopt.cli benchmark --problem rastrigin --dims 3 --generations 50
```

Output:
```
        GA: fitness=  12.345678  time=0.012s
        DE: fitness=   5.678901  time=0.023s
       PSO: fitness=  23.456789  time=0.015s
    CMAES: fitness=   0.000123  time=0.045s
       SA: fitness=   8.765432  time=0.008s

Ranking (best fitness):
  1. CMAES:   0.000123 (0.045s)
  2.    DE:   5.678901 (0.023s)
  ...
```

### `plot` — Display ASCII plots

```bash
python -m evopt.cli plot --algorithm ga --problem sphere --dims 3 --generations 50
python -m evopt.cli plot --algorithm nsga2 --problem zdt1 --dims 5 --generations 50
```

### `config` — Run from / generate config files

```bash
# Generate a template config
python -m evopt.cli config template --algorithm de --problem rastrigin --dims 5 --output config.yaml

# Run from a config file
python -m evopt.cli config run --config-file config.yaml --json

# List config-compatible algorithms/problems/callbacks
python -m evopt.cli config list
```

### `batch` — Batch experiment

```bash
python -m evopt.cli batch \
    --problem rastrigin \
    --algorithms ga,de,pso,cmaes \
    --dims 3 \
    --generations 50 \
    --repeats 5 \
    --output results/
```

### `list` — List available resources

```bash
python -m evopt.cli list
```

## Configuration Files

EvOpt supports YAML and JSON configuration files for reproducible experiments.

### YAML Example

```yaml
algorithm:
  name: ga
  params:
    population_size: 100
    max_generations: 200
    crossover_rate: 0.9
    mutation_rate: 0.05
    elite_size: 2
    tournament_k: 5

problem:
  name: rastrigin
  params:
    dims: 5

seed: 42
verbose: false

callbacks:
  - type: stagnation
    params: {patience: 30}
  - type: adaptive_mutation_rate
    params: {low_diversity: 0.1, high_diversity: 0.5}
```

### Python API for configs

```python
from evopt.config import default_config, save_config, load_config, build_from_config

# Create a config programmatically
cfg = default_config("cmaes", "sphere", dims=3, max_generations=100)

# Save to file
save_config(cfg, "my_config.yaml")

# Load and run
problem, algorithm = build_from_config(load_config("my_config.yaml"))
best = algorithm.run()
```

## Multi-Objective Optimization

```python
from evopt import NSGA2
from evopt.problems.multi_objective import ZDT1
from evopt.indicators import hypervolume, inverted_generational_distance, spacing
from evopt.utils.visualization import ascii_pareto_front

# Solve ZDT1
nsga = NSGA2(ZDT1(dims=10), population_size=100, max_generations=100, seed=42)
nsga.run()

pareto = nsga.pareto_front
print(f"Pareto front size: {len(pareto)}")

# Evaluate quality
objs = [ind.metadata['objectives'] for ind in pareto]
ref = [max(o[0] for o in objs) + 0.1, max(o[1] for o in objs) + 0.1]
print(f"Hypervolume: {hypervolume(objs, ref):.6f}")
print(f"Spacing:     {spacing(objs):.6f}")

# Visualize
print(ascii_pareto_front(pareto, title="ZDT1 Pareto Front"))
```

## Performance Indicators

| Indicator | Measures | Better When |
|-----------|----------|-------------|
| **Hypervolume** | Convergence + diversity | Higher |
| **IGD** | Convergence + diversity | Lower |
| **GD** | Convergence | Lower |
| **Spacing** | Distribution uniformity | Lower |
| **Spread** | Diversity | Lower |

```python
from evopt.indicators import hypervolume, generational_distance,
    inverted_generational_distance, spacing, spread

front = [[0.1, 1.0], [0.3, 0.7], [0.5, 0.5], [0.8, 0.3], [1.0, 0.1]]
ref_point = [1.5, 1.5]

hv = hypervolume(front, ref_point)        # 1.50
sp = spacing(front)                        # ~0.045
```

## Batch Experiments

### Comparing Algorithms

```python
from evopt.results import Experiment

exp = Experiment(name="algo_comparison")
for alg in ["ga", "de", "pso", "cmaes", "sa"]:
    exp.add(alg, "rastrigin", {
        "dims": 5, "population_size": 50, "max_generations": 100,
    }, seed=42)

results = exp.run(repeats=5)
exp.report()
exp.save_results("results/")
```

### Parameter Sweep (Grid Search)

```python
from evopt.results import parameter_sweep

exp = parameter_sweep(
    "ga", "rastrigin",
    param_grid={
        "mutation_rate": [0.01, 0.05, 0.1, 0.2],
        "crossover_rate": [0.7, 0.85, 0.95],
    },
    fixed_params={"dims": 3, "population_size": 50, "max_generations": 50},
    repeats=3, seed=42,
)
exp.report()
```

### Result Objects

```python
from evopt.results import Result

ga = GeneticAlgorithm(Sphere(dims=2), population_size=50, max_generations=100, seed=42)
ga.run()

result = Result.from_algorithm(ga, problem_name="sphere", algorithm_name="ga",
                                time_seconds=0.5)
result.to_json("result.json")   # Full result with history
result.to_csv("history.csv")    # Per-generation history as CSV
print(result.summary())         # One-line summary
```

## Architecture

```
evopt/
├── __init__.py              # Public API exports
├── __main__.py              # python -m evopt entry point
├── cli.py                   # CLI: solve, benchmark, plot, config, batch, list
├── config.py                # YAML/JSON config loading, building, templates
├── core.py                  # Individual, Population, random_population
├── results.py               # Result, Experiment, parameter_sweep
├── indicators.py            # Hypervolume, IGD, GD, Spacing, Spread
├── algorithms/
│   ├── __init__.py
│   ├── base.py              # BaseAlgorithm: run loop, statistics, callbacks
│   ├── ga.py                # GeneticAlgorithm
│   ├── es.py                # EvolutionStrategy (self-adaptive)
│   ├── de.py                # DifferentialEvolution (5 strategies)
│   ├── pso.py               # ParticleSwarmOptimizer
│   ├── nsga2.py             # NSGA2 + MultiObjectiveProblem
│   ├── island_model.py      # IslandModelGA (parallel subpopulations)
│   ├── memetic.py           # MemeticAlgorithm (GA + local search)
│   ├── cmaes.py             # CMAES (Covariance Matrix Adaptation ES)
│   └── simulated_annealing.py # SimulatedAnnealing
├── problems/
│   ├── __init__.py
│   ├── base.py              # Problem, ContinuousProblem, CombinatorialProblem
│   ├── sphere.py            # Sphere function
│   ├── rastrigin.py         # Rastrigin function
│   ├── rosenbrock.py        # Rosenbrock function
│   ├── benchmarks.py        # Ackley, Griewank, Schwefel, Michalewicz, Zakharov
│   ├── tsp.py               # Traveling Salesman Problem
│   ├── knapsack.py          # 0/1 Knapsack
│   └── multi_objective.py   # ZDT1, ZDT2
├── operators/
│   ├── __init__.py
│   ├── selection.py         # Tournament, Roulette, Rank, SUS
│   ├── crossover.py         # Uniform, 1-point, 2-point, BLX, SBX, OX, CX, PMX
│   └── mutation.py          # Gaussian, Polynomial, Bit-flip, Swap, etc.
└── utils/
    ├── __init__.py
    ├── statistics.py        # Per-generation statistics tracking
    ├── visualization.py     # ASCII convergence/Pareto/diversity plots
    ├── callbacks.py         # Termination criteria & adaptive operators
    └── logging_utils.py     # Configurable logging with file/JSON support
```

### Design Principles

1. **No mandatory dependencies** — Pure Python; NumPy/PyYAML are optional.
2. **Clean abstractions** — `BaseAlgorithm` provides the run loop; subclasses
   implement `initialize()` and `evolve_one_generation()`.
3. **Composability** — Problems, operators, callbacks, and algorithms are all
   independent and interchangeable.
4. **Reproducibility** — Random seeds control both Python and NumPy RNGs.
5. **Extensibility** — New algorithms/problems/operators follow clear patterns.

## Examples

The `examples/` directory contains 7 detailed examples:

| File | Description |
|------|-------------|
| `01_basic_usage.py` | Solve benchmarks with GA, DE, PSO, CMA-ES, SA |
| `02_multi_objective.py` | NSGA-II with hypervolume/IGD indicators |
| `03_config_files.py` | Run experiments from YAML/JSON config files |
| `04_batch_experiments.py` | Compare algorithms and parameter sweeps |
| `05_custom_problem.py` | Define custom problems (continuous, constrained, multi-obj) |
| `06_cmaes_advanced.py` | CMA-ES on ill-conditioned problems (cigar, tablet) |
| `07_simulated_annealing.py` | SA with custom cooling schedules and move functions |

```bash
cd evolutionary-optimizer
python examples/01_basic_usage.py
```

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test class
python -m pytest tests/test_new_features.py::TestCMAES -v

# Run with coverage (requires pytest-cov)
python -m pytest tests/ --cov=evopt --cov-report=term-missing
```

The test suite includes **82 tests** covering:
- All algorithms (convergence, reproducibility, edge cases)
- All operators (permutation validity, parameter validation)
- Config loading/saving (YAML, JSON, error handling)
- Result objects (JSON/CSV export)
- Performance indicators (known-answer tests)
- CLI integration
- Callbacks (termination, adaptive operators)
- Integration tests (algorithms + indicators + results)

## Known Issues (Resolved)

The following bugs were identified during systematic bug hunting and have been fixed:

1. **PMX crossover produced invalid permutations** — mapping direction was inverted,
   causing duplicates. Fixed with correct mapping and cycle detection. Verified
   with 500-iteration stress test.

2. **Individual ID counter never reset** — unbounded memory growth in NSGA2 cache.
   Fixed with `reset_id_counter()` and automatic cache cleanup.

3. **Stagnation callback didn't reset between runs** — internal state persisted
   across runs. Fixed with generation-0 reset.

4. **Verbose logging crashed on None fitness** — `:.6g` format on None. Fixed
   with None-safe formatting.

5. **Knapsack infeasible fitness was ambiguous** — negative fitness preferred by
   minimizers. Fixed with direction-aware penalties.

6. **DE mutation could pick duplicate indices** — infinite loop in uniqueness
   check. Fixed with `pick_distinct()` using `random.sample()`.

7. **DE best/1 strategy re-evaluated entire population** — extreme performance
   regression. Fixed by using cached fitness values.

8. **Polynomial mutation produced complex numbers** — when `xy` went negative
   (out-of-bounds genomes). Fixed with clamping and `abs()` guards.

9. **SBX crossover produced complex numbers** — from numerical edge cases in
   beta calculation. Fixed with `.real` extraction guards.

10. **Base run() overwrote termination reasons** — callbacks/should_terminate()
    set termination reasons that were unconditionally overwritten. Fixed to
    respect pre-set reasons.

## Changelog

### v3.0.0 (Major Improvement)

**New Algorithms (2):**
- **CMA-ES** — Covariance Matrix Adaptation Evolution Strategy with full
  path updates, step-size adaptation, and covariance matrix learning.
- **Simulated Annealing** — with 3 cooling schedules (geometric, linear,
  logarithmic), custom move functions, and reheat-on-stagnation.

**New Modules (4):**
- `config.py` — YAML/JSON configuration file support with algorithm/problem/
  callback building and template generation.
- `results.py` — `Result` dataclass (JSON/CSV export), `Experiment` runner
  (batch comparisons), `parameter_sweep` (grid search).
- `indicators.py` — Hypervolume, IGD, GD, Spacing, Spread for multi-objective
  evaluation.
- Enhanced `logging_utils.py` — file logging, JSON-line format, level control.

**CLI Improvements:**
- New commands: `config` (run/template/list), `batch` (batch experiments)
- New algorithms: `cmaes`, `sa` in solve/benchmark/plot
- `--output` flag on solve for result file export
- Hypervolume computation in NSGA-II solve output

**Code Quality:**
- Fixed broken `pyproject.toml` build backend
- Type hints throughout new code
- Comprehensive docstrings on all public APIs
- 61 new tests (82 total, all passing)
- Numpy RNG seeded alongside Python RNG for reproducibility
- Complex number guards in SBX and polynomial mutation
- Termination reason preservation in base run() loop

**Infrastructure:**
- GitHub Actions CI config (Python 3.9-3.12)
- CONTRIBUTING.md with development guidelines
- LICENSE (MIT)
- 7 detailed example scripts

### v2.0.0 (Enhanced)

- Added Island Model GA and Memetic Algorithm
- Added 5 new benchmark problems (Ackley, Griewank, Schwefel, Michalewicz, Zakharov)
- Added 7 termination/adaptive callbacks
- Added ASCII visualization (convergence, Pareto front, diversity)
- Added CLI with solve/benchmark/plot/list commands

### v1.0.0 (Initial)

- GA, ES, DE, PSO, NSGA-II
- Sphere, Rastrigin, Rosenbrock, TSP, Knapsack, ZDT1, ZDT2
- 20 operators (selection, crossover, mutation)
- Statistics tracking and history

## Roadmap

- [ ] **SPEA2** — Strength Pareto Evolutionary Algorithm 2
- [ ] **MOEA/D** — Multi-Objective Evolutionary Algorithm based on Decomposition
- [ ] **Bayesian Optimization** — For expensive black-box optimization
- [ ] **CMA-ES with restarts** — IPOP-CMA-ES / BIPOP-CMA-ES
- [ ] **Parallel evaluation** — Multiprocessing for expensive objective functions
- [ ] **Constraint handling** — Constraint-domination in NSGA-II
- [ ] **Real plotting** — Matplotlib backend (optional) for publication-quality plots
- [ ] **Web dashboard** — Real-time monitoring of optimization runs
- [ ] **Problem suite** — BBOB/COCO benchmark suite integration
- [ ] **Auto-tuning** — Automatic algorithm selection and parameter tuning

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on adding algorithms,
problems, operators, and tests.

### Quick Start for Contributors

```bash
git clone https://github.com/<your-fork>/creative-projects.git
cd creative-projects/evolutionary-optimizer
python -m venv .venv
source .venv/bin/activate
pip install -e . pytest numpy pyyaml
python -m pytest tests/ -v
```

## License

MIT License — see [LICENSE](LICENSE) for details.

Copyright (c) 2024-2026 EvOpt Contributors

---

<div align="center">

*Built with care for the evolutionary optimization community.*

</div>