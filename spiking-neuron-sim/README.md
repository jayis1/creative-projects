# Spiking Neuron Simulator

A dependency-free, event-driven leaky integrate-and-fire (LIF) network for exploring computational neuroscience. It models membrane leakage, thresholds, resets, refractory periods, delayed synapses, deterministic stimuli, and optional pair-based spike-timing-dependent plasticity (STDP).

## How it works

Each neuron exponentially decays toward its resting potential. Input events add current; crossing threshold emits a spike, resets the membrane, and schedules weighted events on outgoing connections. A heap makes event delivery ordered and efficient even when synaptic delays differ. The simulator keeps spike histories so experiments can inspect timing and plasticity.

## Usage

Requires Python 3.10+ and has no third-party runtime dependencies.

```bash
cd spiking-neuron-sim
PYTHONPATH=. python3 -m spiking_neuron_sim.cli --until 20
```

Proof-of-life output:

```text
spikes:
    0.0 ms  input
    5.0 ms  input
    6.0 ms  output
   10.0 ms  input
total=4
```

Library example:

```python
from spiking_neuron_sim import LIFNetwork, Stimulus

net = LIFNetwork(seed=7)
net.add_neuron("pre")
net.add_neuron("post", threshold=0.5)
net.connect("pre", "post", weight=0.6, delay=1.5)
spikes = net.stimulate([Stimulus(0, "pre", 1.0)], until=10)
```

## Development

```bash
python3 -m pytest -q
```

## Phase 1 scope

The initial release provides validated neuron and connection parameters, deterministic priority-queue delivery, delayed synapses, reset support, a small CLI, and tests. Enhancement and bug-hunt phases add richer network construction and regression coverage.

## Enhancements (Phase 2)

- `add_population` creates named neuron groups with validation.
- `connect_all_to_all` builds dense or bipartite topologies without self-edges.
- `SimulationReport` exposes spike counts and firing rates (spikes/second).
- `export_state` and `from_state` provide validated, JSON-compatible topology snapshots.
- The public API now has docstrings and deterministic seeded construction for repeatable experiments.
