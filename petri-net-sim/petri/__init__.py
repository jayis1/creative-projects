"""
petri-net-sim: A Petri net (place/transition net) simulator and analysis toolkit.

Features
--------
- Place/Transition (P/T) net model with weighted arcs.
- Transition firing with guard functions.
- Multiple firing semantics: single-step, step-bounded, maximal-step.
- Reachability graph generation with cycle/deadlock detection.
- Place & transition invariants (T-invariants, P-invariants) via linear algebra.
- Boundedness analysis (k-bounded places).
- Liveness classification (dead, L1-L4).
- Token game simulation: random walk, step-by-step, batch runs.
- Net serialization (JSON) and deserialization.
- ASCII visualization of net structure and marking.
- Dot (Graphviz) export for reachability graphs.
- Preset nets: dining philosophers, producer-consumer, mutual exclusion,
  simple workflow, state machine, free-choice workflow, etc.
- argparse CLI.
"""

from .net import PetriNet, Place, Transition, Arc
from .simulator import Simulator
from .analysis import (
    compute_t_invariants,
    compute_p_invariants,
    reachability_graph,
    analyze_boundedness,
    analyze_liveness,
    BoundednessResult,
    LivenessResult,
)
from .presets import (
    dining_philosophers,
    producer_consumer,
    mutual_exclusion,
    workflow_net,
    state_machine,
    free_choice_net,
    readers_writers,
    simple_buffer,
)
from .visualizer import (
    ascii_net,
    ascii_marking,
    reachability_dot,
    reachability_ascii,
)

__version__ = "1.0.0"

__all__ = [
    "PetriNet", "Place", "Transition", "Arc",
    "Simulator",
    "compute_t_invariants", "compute_p_invariants", "reachability_graph",
    "analyze_boundedness", "analyze_liveness",
    "BoundednessResult", "LivenessResult",
    "dining_philosophers", "producer_consumer", "mutual_exclusion",
    "workflow_net", "state_machine", "free_choice_net", "readers_writers",
    "simple_buffer",
    "ascii_net", "ascii_marking", "reachability_dot", "reachability_ascii",
]