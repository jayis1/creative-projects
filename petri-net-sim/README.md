# petri-net-sim

A Petri net (Place/Transition net) simulator and analysis toolkit, written in pure Python with zero external dependencies.

## Overview

Petri nets are a mathematical modeling language for distributed, concurrent, and asynchronous systems. They model system state as **tokens in places** and state changes as **transition firings** that consume and produce tokens according to weighted arcs.

This toolkit provides:

- **Net model**: Places (with optional capacity), Transitions (with optional guard functions), weighted Arcs.
- **Firing semantics**: Single-step firing, in-place mutation, capacity-aware enabling checks.
- **Simulation**: Random walk, fixed-sequence execution, maximal-step (concurrent firing), fire-until-target, and step-by-step iteration.
- **Reachability graph**: BFS construction of all reachable markings with deadlock detection.
- **Coverability tree**: Karp-Miller algorithm with ω-abstraction for unboundedness detection.
- **Structural analysis**:
  - **T-invariants** — transition multisets whose firing returns the net to the same marking.
  - **P-invariants** — place weightings whose token sum is conserved (computed via Gaussian elimination over the rationals).
  - **Incidence matrix** (Post − Pre).
  - **Traps** — sets of places that, once marked, stay marked.
  - **Siphons** — sets of places that, once unmarked, stay unmarked (potential deadlocks).
- **Behavioral analysis**:
  - **Boundedness** — k-boundedness detection via reachability exploration.
  - **Liveness** — L0–L4 classification (dead, L1, L4/live).
  - **Reachability checking** — can a specific marking be reached?
  - **Reversibility** — is the initial marking a home state (reachable from every reachable marking)?
- **Visualization**: ASCII net diagrams, ASCII marking display, ASCII reachability graph, Graphviz DOT export.
- **Serialization**: Full JSON round-trip (save/load nets).
- **8 preset nets**: dining philosophers, producer-consumer, mutual exclusion, workflow, state machine, free-choice, readers-writers, simple buffer.
- **CLI**: `petri` command with 10 subcommands: `simulate`, `reachability`, `invariants`, `analyze`, `show`, `fire`, `export`, `presets`, `reachable`, `cover`.

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
from petri import is_reachable, is_reversible, coverability_tree, analyze_traps_siphons

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

# Check reachability
print(f"Can reach consumed=5: {is_reachable(net, {'consumed': 5})}")

# Check reversibility
print(f"Reversible: {is_reversible(net)}")

# Coverability tree (for unbounded nets)
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

### Reversibility

A net is **reversible** if the initial marking is reachable from every reachable marking (i.e., it's a home state). This means the system can always return to its starting configuration.

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
│   ├── analysis.py      # Reachability, coverability, invariants, boundedness, liveness, traps/siphons
│   ├── presets.py       # 8 preset nets
│   ├── visualizer.py    # ASCII + DOT visualization
│   └── cli.py           # Command-line interface
├── tests/
│   ├── test_petri.py    # Core test suite (39 tests)
│   └── test_enhanced.py # Enhanced analysis tests (12 tests)
├── pyproject.toml
└── README.md
```

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

## License

MIT