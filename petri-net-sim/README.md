# petri-net-sim

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests: 107](https://img.shields.io/badge/tests-107%20passed-brightgreen.svg)](#testing)
[![Version: 3.0.0](https://img.shields.io/badge/version-3.0.0-orange.svg)](#changelog)

> A comprehensive Petri net (Place/Transition net) simulator and analysis toolkit, written in pure Python with zero external dependencies.

Petri nets are a mathematical modeling language for distributed, concurrent, and asynchronous systems. They model system state as **tokens in places** and state changes as **transition firings** that consume and produce tokens according to weighted arcs. This toolkit provides simulation, analysis, verification, and visualization for Petri nets — plus **stochastic Petri nets**, **colored Petri nets**, and industry-standard **PNML** interchange.

---

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [CLI Reference](#cli-reference)
- [Stochastic Petri Nets](#stochastic-petri-nets)
- [Colored Petri Nets](#colored-petri-nets)
- [PNML Exchange](#pnml-exchange)
- [Batch Analysis](#batch-analysis)
- [Configuration Files](#configuration-files)
- [How It Works](#how-it-works)
- [Presets](#presets)
- [Examples](#examples)
- [Known Issues (Resolved)](#known-issues-resolved)
- [Changelog](#changelog)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

---

## Features

### Core Model
- **Places** with optional capacity constraints
- **Transitions** with optional guard functions (predicates on markings)
- **Weighted arcs** (integer multiplicity)
- **Firing semantics**: single-step, in-place mutation, capacity-aware enabling
- **JSON serialization** with full round-trip support

### Simulation
- **Random walk**: fire random enabled transitions until deadlock or step limit
- **Fixed sequence**: execute a specific transition sequence
- **Maximal step**: fire all non-conflicting enabled transitions simultaneously (step semantics)
- **Fire-until-target**: random walk until a target marking is reached
- **Iterator protocol**: step-by-step lazy simulation

### Analysis
- **Reachability graph**: BFS construction with deadlock detection
- **Coverability tree**: Karp-Miller algorithm with ω-abstraction for unboundedness detection
- **T-invariants**: transition multisets that preserve the marking (null space of incidence matrix)
- **P-invariants**: place weightings with conserved token sum
- **Boundedness**: k-boundedness detection
- **Liveness**: L0–L4 classification (dead, L1, L4/live)
- **Reachability checking**: can a specific marking be reached?
- **Reversibility**: is the initial marking a home state?
- **Traps**: place sets that stay marked once marked
- **Siphons**: place sets that stay unmarked once unmarked (structural deadlock indicator)

### Stochastic Petri Nets (SPN)
- Exponentially distributed firing delays with per-transition rates
- **CTMC** (Continuous-Time Markov Chain) generation from the reachability graph
- **Steady-state probabilities** via power iteration on the embedded DTMC
- **Expected time to reach** a target marking (Gauss-Seidel iteration)
- **Monte Carlo simulation** with deadlock probability estimation and marking distributions

### Colored Petri Nets (CPN)
- **Typed tokens** with color sets (int, string, bool, custom values)
- **Arc inscriptions**: functions that transform token values during firing
- **Variable binding**: bind input tokens to named variables, use in guards and output expressions
- **Guards**: predicates that inspect bound variables

### Batch Analysis
- **Batch simulation**: run thousands of random walks and aggregate statistics
- **Deadlock probability** with Wilson score confidence intervals
- **Transition fire frequencies** and **token count distributions**
- **Mean/std statistics** per place

### Interchange & Config
- **PNML** (ISO/IEC 15909-2) export, import, and validation
- **JSON/YAML config files** for declarative net definitions
- **Graphviz DOT** export for reachability graphs

### Visualization
- ASCII net diagrams (places, transitions, arcs with weights)
- ASCII marking display (token counts per place)
- ASCII reachability graph (adjacency list with deadlock flags)
- DOT export for Graphviz rendering

### Developer Experience
- 16 **preset nets**: dining philosophers, producer-consumer, mutual exclusion, workflow, state machine, free-choice, readers-writers, simple buffer, token ring, elevator, pipeline, database transaction
- **14 CLI subcommands** with `--help` text and flags
- **Structured logging** with configurable verbosity and file output
- **107 tests** covering core, enhanced, stochastic, colored, PNML, batch, and edge cases
- **GitHub Actions CI** across Python 3.9–3.12

## Installation

```bash
cd petri-net-sim
pip install -e .
```

Optional dependencies:
```bash
pip install -e ".[dev]"      # pytest, pytest-cov for development
pip install pyyaml           # YAML config file support
```

Or use directly without installation:
```bash
python3 -m petri.cli <command> [options]
```

## Quick Start

### Python API

```python
from petri import PetriNet, Place, Transition, Simulator, ascii_marking
from petri import reachability_graph, compute_t_invariants, compute_p_invariants
from petri import is_reachable, is_reversible, coverability_tree, analyze_traps_siphons

# Build a producer-consumer net
net = PetriNet("pc")
net.add_place(Place("free", initial=1, capacity=1))
net.add_place(Place("items", initial=0, capacity=3))
net.add_place(Place("consumed", initial=0))
net.add_transition(Transition("produce"))
net.add_transition(Transition("consume"))

net.add_arc("free", "produce")
net.add_arc("produce", "free")
net.add_arc("produce", "items")
net.add_arc("items", "consume")
net.add_arc("consume", "consumed")

# Simulate
sim = Simulator(net, seed=42)
result = sim.random_walk(max_steps=20)
print(f"Steps: {result.steps_fired}, Deadlocked: {result.deadlocked}")
print(f"Final: {ascii_marking(result.final_marking, net)}")

# Analyze
rg = reachability_graph(net)
print(f"Reachability: {rg.num_states} states, {rg.num_edges} edges")
print(f"Can reach consumed=5: {is_reachable(net, {'consumed': 5})}")
print(f"Reversible: {is_reversible(net)}")

# Coverability tree
tree = coverability_tree(net)
print(f"Unbounded: {tree.is_unbounded}")

# Traps and siphons
ts = analyze_traps_siphons(net)
print(f"Traps: {ts.traps}")
print(f"Siphons: {ts.siphons}")

# Invariants
print(f"T-invariants: {compute_t_invariants(net)}")
print(f"P-invariants: {compute_p_invariants(net)}")
```

### Using a preset

```python
from petri.presets import dining_philosophers, mutual_exclusion

net = dining_philosophers(n=3)
sim = Simulator(net, seed=0)
result = sim.random_walk(max_steps=100)
print(f"Deadlocked: {result.deadlocked}")
```

### CLI

```bash
# Show a preset net
petri --preset mutual_exclusion show

# Simulate
petri --preset dining_philosophers --seed 42 simulate --steps 100 --trace

# Build reachability graph
petri --preset mutual_exclusion reachability
petri --preset mutual_exclusion reachability --dot > reachability.dot

# Compute invariants
petri --preset producer_consumer invariants --type both

# Full analysis (boundedness, liveness, reversibility, traps/siphons)
petri --preset workflow analyze

# Check if a marking is reachable
petri --preset workflow reachable end=1

# Build coverability tree
petri --preset mutual_exclusion cover

# Fire a specific sequence
petri --preset workflow fire submit review approve

# Batch simulation with statistics
petri --preset dining_philosophers batch --runs 2000 --steps 200

# Steady-state analysis (stochastic)
petri --preset mutual_exclusion steady-state --rates p1_request=1.0 p1_enter=2.0

# Export to PNML
petri --preset workflow export --format pnml > workflow.pnml

# List presets
petri presets
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                        CLI (cli.py)                       │
│  simulate · reachability · invariants · analyze · batch │
│  steady-state · cover · pnml · config · monte-carlo ...  │
└─────────────┬───────────────────────────────────┬───────┘
              │                                   │
              ▼                                   ▼
┌─────────────────────┐            ┌───────────────────────┐
│  Core Model (net.py) │            │  Visualization        │
│  PetriNet · Place ·  │            │  ASCII · DOT · PNML   │
│  Transition · Arc    │            └───────────────────────┘
└──────────┬──────────┘
           │
    ┌──────┴──────┬──────────┬───────────┬──────────┐
    ▼             ▼          ▼           ▼          ▼
┌────────┐  ┌────────┐ ┌─────────┐ ┌───────┐ ┌──────────┐
│Simulator│  │Analysis│ │Stochastic│ │Colored│ │  Batch   │
│random   │  │reachab.│ │CTMC ·    │ │typed  │ │simulate  │
│walk ·   │  │invari. │ │steady-  │ │tokens │ │stats ·   │
│seq ·    │  │bounded.│ │state ·  │ │guards │ │CI · freq │
│maximal  │  │liveness│ │MC · exp │ │       │ │          │
└────────┘  └────────┘ └─────────┘ └───────┘ └──────────┘
                                                     │
                                              ┌──────┴──────┐
                                              │  Presets    │
                                              │  16 nets    │
                                              └─────────────┘
```

### Module Overview

| Module | Responsibility |
|--------|--------------|
| `net.py` | Core model: `PetriNet`, `Place`, `Transition`, `Arc`, firing semantics |
| `simulator.py` | Token game: random walk, sequences, maximal step, fire-until |
| `analysis.py` | Reachability, coverability, invariants, boundedness, liveness, traps/siphons |
| `stochastic.py` | SPN, CTMC generation, steady-state, Monte Carlo, expected time |
| `colored.py` | Colored Petri nets with typed tokens and arc inscriptions |
| `batch.py` | Batch simulation with statistical aggregation and confidence intervals |
| `config.py` | JSON/YAML config file loading and saving |
| `pnml.py` | PNML (ISO/IEC 15909-2) export, import, validation |
| `presets.py` | 16 pre-built example nets |
| `visualizer.py` | ASCII visualization and Graphviz DOT export |
| `logging_util.py` | Structured logging with configurable verbosity |
| `cli.py` | Command-line interface with 14 subcommands |

## CLI Reference

| Command | Description |
|---------|-------------|
| `simulate` | Run a random-walk simulation with optional trace |
| `reachability` | Build and display the reachability graph |
| `invariants` | Compute T-invariants and/or P-invariants |
| `analyze` | Full analysis: boundedness, liveness, reversibility, traps/siphons |
| `reachable` | Check if a target marking is reachable |
| `cover` | Build coverability tree (Karp-Miller) |
| `show` | Display net structure and initial marking |
| `fire` | Fire a specific sequence of transitions |
| `export` | Export as JSON, DOT, PNML, or config |
| `presets` | List all available preset nets |
| `batch` | Run batch simulations with statistics |
| `steady-state` | Compute steady-state probabilities (stochastic) |
| `expected-time` | Expected time to reach a target marking (stochastic) |
| `pnml` | PNML export/import/validate |
| `config` | Config file (JSON/YAML) export/import |
| `monte-carlo` | Monte Carlo simulation with deadlock estimation |

Global options: `--preset <name>`, `--file <path>`, `--seed <int>`, `--log-level`, `--log-file`

## Stochastic Petri Nets

Add firing rates to transitions and analyze the resulting Continuous-Time Markov Chain:

```python
from petri import PetriNet, Place, Transition
from petri.stochastic import StochasticPetriNet, build_ctmc, steady_state_probabilities

net = mutual_exclusion()
spn = StochasticPetriNet(net)
spn.set_rate("p1_request", 1.0)
spn.set_rate("p1_enter", 2.0)
spn.set_rate("p1_exit", 3.0)

ctmc = build_ctmc(spn)
probs = steady_state_probabilities(ctmc)
# Returns {state_id: probability} — the long-run distribution
```

## Colored Petri Nets

Model data-dependent concurrency with typed tokens:

```python
from petri.colored import (
    ColoredPetriNet, ColoredPlace, ColoredTransition,
    ColorSet, ArcInscription, INT,
)

cpn = ColoredPetriNet("filter")
cpn.add_place(ColoredPlace("input", color_set=INT, initial=[1, 2, 3, 4, 5]))
cpn.add_place(ColoredPlace("output", color_set=INT))
cpn.add_transition(ColoredTransition("filter_even",
    guard=lambda b: b.get("x", 0) % 2 == 0))
cpn.add_arc("input", "filter_even", ArcInscription.identity("x"), direction="in")
cpn.add_arc("output", "filter_even", ArcInscription.identity("x"), direction="out")

marking = cpn.initial_marking()
while cpn.is_enabled("filter_even", marking):
    marking = cpn.fire("filter_even", marking)
# output now contains [2, 4] (even numbers from input)
```

## PNML Exchange

Export and import nets in the ISO/IEC 15909-2 standard format:

```python
from petri.pnml import to_pnml, from_pnml, validate_pnml
from petri.presets import mutual_exclusion

net = mutual_exclusion()
pnml_xml = to_pnml(net)        # Export to PNML XML string
validate_pnml(pnml_xml)        # Returns list of issues (empty = valid)
net2 = from_pnml(pnml_xml)     # Import back to PetriNet
```

## Batch Analysis

Run thousands of simulations and aggregate statistics:

```python
from petri.presets import dining_philosophers
from petri.batch import batch_simulate

net = dining_philosophers(3)
stats = batch_simulate(net, num_runs=2000, max_steps=200, seed=42)
print(f"Deadlock probability: {stats.deadlock_probability:.4f}")
print(f"95% CI: [{stats.deadlock_ci_low:.4f}, {stats.deadlock_ci_high:.4f}]")
print(f"Mean steps: {stats.mean_steps:.1f} ± {stats.std_steps:.1f}")
```

## Configuration Files

Define nets declaratively in JSON or YAML:

```yaml
# my_net.yaml
name: my_workflow
places:
  - name: start
    initial: 1
  - name: middle
    initial: 0
  - name: end
    initial: 0
transitions:
  - name: step1
  - name: step2
arcs:
  - source: start
    target: step1
  - source: step1
    target: middle
  - source: middle
    target: step2
  - source: step2
    target: end
```

```bash
petri --file my_net.yaml show    # (requires pyyaml)
petri config import --input my_net.yaml
```

## How It Works

### Firing Rules

A transition `t` is **enabled** in marking `M` when:
1. Every input place `p` has `M(p) ≥ w(p, t)` (enough tokens for each input arc weight).
2. Firing would not exceed any output place's capacity.
3. The transition's guard function (if any) returns `True`.

Firing consumes tokens from input places and produces tokens in output places:
```
M'(p) = M(p) − w(p,t)    for each input place p
M'(p) = M(p) + w(t,p)    for each output place p
```

### Reachability Graph

Built via BFS from the initial marking. Each reachable marking becomes a node; each firing becomes an edge labeled with the transition name. Deadlock states (no enabled transitions) are flagged.

### Coverability Tree (Karp-Miller)

For unbounded nets (where the reachability graph is infinite), the coverability tree uses **ω-abstraction**: when a marking M' is reached that covers a predecessor M on the path, places that strictly increased are replaced by ω (infinity). This makes the tree finite while preserving boundedness information. If any node contains ω, the net is unbounded.

### Invariants

The **incidence matrix** `C = Post − Pre` captures the net effect of each transition on each place.

- **T-invariants** satisfy `C · x = 0` — firing the transition multiset `x` returns to the same marking.
- **P-invariants** satisfy `y^T · C = 0` — the weighted sum `y · M` is conserved.

Both are computed via Gaussian elimination over the rationals, extracting null-space basis vectors from free variables, then normalizing to coprime integers.

### Traps and Siphons

- **Trap**: A set of places S where every transition that consumes from S also produces into S. Once marked, a trap can never become empty.
- **Siphon**: A set of places S where every transition that produces into S also consumes from S. Once unmarked, a siphon can never become marked (dead).

An initially-unmarked siphon indicates a potential structural deadlock.

### Liveness

- **L0 (dead)**: The transition can never fire from any reachable marking.
- **L1**: The transition can fire from at least one reachable marking.
- **L4 (live)**: The transition can fire from every reachable marking.

### Stochastic Analysis

Stochastic Petri nets associate exponentially distributed firing delays with each transition. The reachability graph becomes a **Continuous-Time Markov Chain** (CTMC), where each transition firing contributes a rate to the infinitesimal generator matrix Q. **Steady-state probabilities** π satisfy π·Q = 0 and Σπ = 1, computed via power iteration on the embedded Discrete-Time Markov Chain. **Expected time to reach** a target marking solves a system of linear equations over the CTMC states.

## Presets

| Preset | Description |
|--------|-------------|
| `dining_philosophers` | n philosophers sharing n forks (deadlock-prone) |
| `producer_consumer` | Producer/consumer with bounded buffer |
| `mutual_exclusion` | Two processes with semaphore-protected critical section |
| `workflow` | Submit → review → approve/reject → done |
| `state_machine` | idle → running → paused → stopped |
| `free_choice` | Free-choice net example |
| `readers_writers` | Readers-writers with writer priority |
| `simple_buffer` | Minimal producer/buffer/consumer |
| `token_ring` | Token ring network (n stations) |
| `elevator` | Elevator controller (n floors) |
| `pipeline` | Multi-stage producer-consumer chain |
| `db_transaction` | Database transaction: begin → validate → commit/abort |

## Examples

The `examples/` directory contains runnable demonstrations:

| File | Description |
|------|-------------|
| `01_basic_simulation.py` | Build, simulate, and analyze a workflow net |
| `02_stochastic_net.py` | CTMC and steady-state analysis of mutual exclusion |
| `03_colored_net.py` | Data pipeline with colored Petri net (filter even numbers) |
| `04_batch_analysis.py` | Batch simulation of dining philosophers |
| `05_pnml_exchange.py` | PNML export/import round-trip |

Run with:
```bash
python3 examples/01_basic_simulation.py
```

## Project Structure

```
petri-net-sim/
├── petri/
│   ├── __init__.py       # Public API (all exports)
│   ├── net.py            # Core model: PetriNet, Place, Transition, Arc
│   ├── simulator.py      # Simulator (random walk, sequences, maximal step)
│   ├── analysis.py       # Reachability, coverability, invariants, boundedness, liveness, traps/siphons
│   ├── stochastic.py     # SPN, CTMC, steady-state, Monte Carlo, expected time
│   ├── colored.py        # Colored Petri nets (typed tokens, arc inscriptions)
│   ├── batch.py          # Batch simulation with statistics and confidence intervals
│   ├── config.py         # JSON/YAML config file support
│   ├── pnml.py           # PNML (ISO/IEC 15909-2) import/export/validate
│   ├── presets.py        # 16 preset nets
│   ├── visualizer.py     # ASCII + DOT visualization
│   ├── logging_util.py   # Structured logging
│   └── cli.py            # Command-line interface (14 subcommands)
├── tests/
│   ├── test_petri.py       # Core test suite (39 tests)
│   ├── test_enhanced.py    # Enhanced analysis tests (12 tests)
│   ├── test_bug_hunt.py   # Bug hunt verification tests (9 tests)
│   ├── test_stochastic.py # Stochastic Petri net tests (13 tests)
│   ├── test_colored.py    # Colored Petri net tests (15 tests)
│   └── test_new_features.py # PNML, config, batch, presets tests (19 tests)
├── examples/              # 5 runnable example scripts
├── .github/workflows/     # CI config (GitHub Actions)
├── pyproject.toml         # Package metadata and dependencies
├── CONTRIBUTING.md        # Contribution guidelines
├── LICENSE                # MIT License
└── README.md              # This file
```

## Testing

The project has **107 tests** across 6 test files:

```bash
# Run all tests
python -m pytest --tb=short -v

# Run with coverage
python -m pytest --cov=petri --cov-report=term-missing

# Run a specific test file
python -m pytest tests/test_stochastic.py -v
```

Test coverage:
- `test_petri.py` — core model, firing, simulation, reachability, invariants (39 tests)
- `test_enhanced.py` — reachability checking, reversibility, coverability, traps/siphons (12 tests)
- `test_bug_hunt.py` — bug fix verification and edge cases (9 tests)
- `test_stochastic.py` — SPN, CTMC, steady-state, Monte Carlo, expected time (13 tests)
- `test_colored.py` — color sets, colored places, firing, guards, arc inscriptions (15 tests)
- `test_new_features.py` — PNML, config files, batch simulation, new presets (19 tests)

## Known Issues (Resolved)

### Bug 1: Boundedness analysis failed to detect unbounded nets

**Problem**: `analyze_boundedness` used `detect_omega=False` when building the reachability graph, then checked `rg.omega_markings` — which was always empty because omega detection was disabled. Unbounded nets were incorrectly reported as bounded.

**Fix**: Use the coverability tree (Karp-Miller algorithm with ω-abstraction) to detect unboundedness before falling back to reachability graph exploration for bounded nets.

### Bug 2: `fire_until` missed target reached on the final step

**Problem**: `fire_until` checked the target marking *before* each firing but not *after*. If the target was reached on the last allowed step, it was missed and `None` was returned.

**Fix**: Check the target marking both before the loop (for the initial marking) and after each firing.

### Bug 3: `_marking_key` used dict keys instead of all place names

**Problem**: `_marking_key(marking)` iterated over `sorted(marking)` (the dict's keys), which could produce different keys for the same logical marking if some places had 0 tokens and were omitted from the dict.

**Fix**: Added an optional `place_names` parameter. `is_reversible` now passes the full list of place names to ensure consistent key generation.

### Bug 4: Coverability tree didn't re-expand updated nodes

**Problem**: When a node's marking was updated to a larger value in the coverability tree, it wasn't re-queued for expansion. This meant the ω-abstraction might not propagate correctly, potentially missing unbounded places.

**Fix**: When a node's marking is updated, re-queue it for expansion and clear its `is_terminal` flag. Also changed the comparison from `_marking_le` (≤) to `_marking_strictly_less` (<) to avoid unnecessary re-expansion when markings are equal.

## Changelog

### v3.0.0 — Comprehensive Improvement (2026-06-19)

**Major new features:**
- **Stochastic Petri nets**: `StochasticPetriNet` class with per-transition firing rates, CTMC generation (`build_ctmc`), steady-state probability computation (`steady_state_probabilities`), Monte Carlo simulation (`monte_carlo`), and expected time to target marking (`expected_time_to_target`).
- **Colored Petri nets**: `ColoredPetriNet`, `ColoredPlace`, `ColoredTransition`, `ColorSet` with typed tokens, arc inscriptions (identity, transform, constant, unit), variable binding, and guards.
- **Batch simulation**: `batch_simulate` with deadlock probability, Wilson score confidence intervals, transition fire frequencies, and token count statistics.
- **PNML support**: ISO/IEC 15909-2 export (`to_pnml`), import (`from_pnml`), and validation (`validate_pnml`).
- **Config files**: JSON/YAML declarative net definitions (`load_config`, `save_config`).
- **Structured logging**: `logging_util.py` with configurable verbosity and file output.
- **4 new presets**: `token_ring`, `elevator`, `pipeline`, `db_transaction` (16 total).
- **5 new CLI commands**: `batch`, `steady-state`, `expected-time`, `pnml`, `config`, `monte-carlo` (16 total).
- **5 runnable examples** in `examples/` directory.
- **GitHub Actions CI** across Python 3.9–3.12.
- **CONTRIBUTING.md** and **LICENSE**.

**Code quality:**
- Type hints throughout all new modules.
- Comprehensive docstrings on all public APIs.
- 47 new tests (107 total, all passing).
- Input validation on all user-facing functions.
- Error handling with specific exception types.

### v2.0.0 — Enhanced Analysis

- Coverability tree (Karp-Miller ω-abstraction)
- Reachability checking
- Reversibility (home state) analysis
- Trap & siphon detection
- Improved liveness (L0/L1/L4)
- 3 new CLI commands
- 12 new tests (60 total)

### v1.0.0 — Initial Release

- Core Petri net model with places, transitions, weighted arcs, guards
- Firing semantics (single-step, in-place, maximal-step)
- Simulator (random walk, sequence, fire-until)
- Reachability graph with deadlock detection
- T-invariants and P-invariants
- Boundedness and liveness analysis
- ASCII visualization and DOT export
- JSON serialization
- 8 preset nets
- 39 tests

## Roadmap

- [ ] Timed Petri nets (deterministic firing delays)
- [ ] High-level Petri net simulation with complex data types
- [ ] Symmetric net reductions
- [ ] Partial order reduction for reachability (stubborn sets)
- [ ] Export to PNML with extended features (hierarchical nets)
- [ ] Interactive web-based visualization
- [ ] Performance benchmarks and optimization for large nets
- [ ] Soundness checking for workflow nets
- [ ] Unfolding for boundedness verification
- [ ] Integration with SMT solvers for constraint-based analysis

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style guidelines, testing instructions, and the PR process.

## License

MIT — see [LICENSE](LICENSE).