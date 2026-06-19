# petri-net-sim

A Petri net (Place/Transition net) simulator and analysis toolkit, written in pure Python with zero external dependencies.

## Overview

Petri nets are a mathematical modeling language for distributed, concurrent, and asynchronous systems. They model system state as **tokens in places** and state changes as **transition firings** that consume and produce tokens according to weighted arcs.

This toolkit provides:

- **Net model**: Places (with optional capacity), Transitions (with optional guard functions), weighted Arcs.
- **Firing semantics**: Single-step firing, in-place mutation, capacity-aware enabling checks.
- **Simulation**: Random walk, fixed-sequence execution, maximal-step (concurrent firing), fire-until-target, and step-by-step iteration.
- **Reachability graph**: BFS construction of all reachable markings with deadlock detection and ω-abstraction hooks for unboundedness.
- **Structural analysis**:
  - **T-invariants** — transition multisets whose firing returns the net to the same marking.
  - **P-invariants** — place weightings whose token sum is conserved (computed via Gaussian elimination over the rationals).
  - **Incidence matrix** (Post − Pre).
- **Behavioral analysis**:
  - **Boundedness** — k-boundedness detection via reachability exploration.
  - **Liveness** — L0–L4 classification (dead, L1, L2, L3, L4/live).
- **Visualization**: ASCII net diagrams, ASCII marking display, ASCII reachability graph, Graphviz DOT export.
- **Serialization**: Full JSON round-trip (save/load nets).
- **8 preset nets**: dining philosophers, producer-consumer, mutual exclusion, workflow, state machine, free-choice, readers-writers, simple buffer.
- **CLI**: `petri` command with `simulate`, `reachability`, `invariants`, `analyze`, `show`, `fire`, `export`, and `presets` subcommands.

## Installation

```bash
cd petri-net-sim
pip install -e .
```

Or use directly without installation by running `python3 -m petri.cli`.

## Quick Start

### Python API

```python
from petri import PetriNet, Place, Transition, Simulator, ascii_marking
from petri import reachability_graph, compute_t_invariants, compute_p_invariants

# Build a simple producer-consumer net
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

# Full analysis (boundedness + liveness)
petri --preset workflow analyze

# Fire a specific sequence
petri --preset workflow fire submit review approve

# List presets
petri presets

# Export as JSON
petri --preset workflow export --format json > workflow.json

# Load from file
petri --file workflow.json show
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

Built via BFS from the initial marking. Each reachable marking becomes a node; each firing becomes an edge labeled with the transition name. Deadlock states (no enabled transitions) are flagged. The `detect_omega` flag enables ω-abstraction for unboundedness detection.

### Invariants

The **incidence matrix** `C = Post − Pre` captures the net effect of each transition on each place. 

- **T-invariants** satisfy `C · x = 0` — firing the transition multiset `x` returns to the same marking.
- **P-invariants** satisfy `y^T · C = 0` — the weighted sum `y · M` is conserved.

Both are computed via Gaussian elimination over the rationals, extracting null-space basis vectors from free variables, then normalizing to coprime integers.

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

## Project Structure

```
petri-net-sim/
├── petri/
│   ├── __init__.py      # Public API
│   ├── net.py           # PetriNet, Place, Transition, Arc
│   ├── simulator.py     # Simulator (random walk, sequences, maximal step)
│   ├── analysis.py      # Reachability, invariants, boundedness, liveness
│   ├── presets.py       # 8 preset nets
│   ├── visualizer.py    # ASCII + DOT visualization
│   └── cli.py           # Command-line interface
├── tests/
│   └── test_petri.py    # Test suite
├── pyproject.toml
└── README.md
```

## License

MIT