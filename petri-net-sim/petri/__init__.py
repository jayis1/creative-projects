"""
petri-net-sim: A Petri net (place/transition net) simulator and analysis toolkit.

Features
--------
- Place/Transition (P/T) net model with weighted arcs.
- Transition firing with guard functions.
- Multiple firing semantics: single-step, step-bounded, maximal-step.
- Reachability graph generation with cycle/deadlock detection.
- Coverability tree (Karp-Miller algorithm with ω-abstraction).
- Place & transition invariants (T-invariants, P-invariants) via linear algebra.
- Boundedness analysis (k-bounded places).
- Liveness classification (dead, L1-L4).
- Reachability checking and reversibility (home state) analysis.
- Trap and siphon detection (structural deadlock analysis).
- Stochastic Petri nets (SPN): CTMC generation, steady-state, Monte Carlo.
- Colored Petri nets (CPN): typed tokens with arc inscriptions.
- Token game simulation: random walk, step-by-step, batch runs.
- Batch simulation with statistical aggregation and confidence intervals.
- Net serialization: JSON, PNML (ISO/IEC 15909-2), config files (JSON/YAML).
- ASCII visualization of net structure and marking.
- Dot (Graphviz) export for reachability graphs.
- Preset nets: dining philosophers, producer-consumer, mutual exclusion,
  simple workflow, state machine, free-choice workflow, token ring,
  elevator, pipeline, database transaction, etc.
- Structured logging support.
- argparse CLI with 12 subcommands.
"""

from .net import PetriNet, Place, Transition, Arc
from .simulator import Simulator
from .analysis import (
    compute_t_invariants,
    compute_p_invariants,
    reachability_graph,
    analyze_boundedness,
    analyze_liveness,
    is_reachable,
    is_reversible,
    coverability_tree,
    analyze_traps_siphons,
    find_traps,
    find_siphons,
    BoundednessResult,
    LivenessResult,
    CoverabilityTree,
    TrapSiphonResult,
)
from .stochastic import (
    StochasticPetriNet,
    build_ctmc,
    steady_state_probabilities,
    monte_carlo,
    expected_time_to_target,
    CTMC,
    CTMCState,
    MonteCarloResult,
    ExpectedTimeResult,
)
from .colored import (
    ColoredPetriNet,
    ColoredPlace,
    ColoredTransition,
    ColorSet,
    ColoredToken,
    ArcInscription,
    INT,
    STRING,
    BOOL,
    UNIT,
)
from .batch import batch_simulate, BatchStats
from .config import load_config, save_config, from_config_dict, to_config_dict
from .pnml import to_pnml, from_pnml, validate_pnml
from .presets import (
    dining_philosophers,
    producer_consumer,
    mutual_exclusion,
    workflow_net,
    state_machine,
    free_choice_net,
    readers_writers,
    simple_buffer,
    token_ring,
    elevator_system,
    producer_consumer_chain,
    database_transaction,
)
from .visualizer import (
    ascii_net,
    ascii_marking,
    reachability_dot,
    reachability_ascii,
)

__version__ = "3.0.0"

__all__ = [
    # Core model
    "PetriNet", "Place", "Transition", "Arc",
    "Simulator",
    # Analysis
    "compute_t_invariants", "compute_p_invariants", "reachability_graph",
    "analyze_boundedness", "analyze_liveness",
    "is_reachable", "is_reversible",
    "coverability_tree", "analyze_traps_siphons",
    "find_traps", "find_siphons",
    "BoundednessResult", "LivenessResult",
    "CoverabilityTree", "TrapSiphonResult",
    # Stochastic
    "StochasticPetriNet", "build_ctmc", "steady_state_probabilities",
    "monte_carlo", "expected_time_to_target",
    "CTMC", "CTMCState", "MonteCarloResult", "ExpectedTimeResult",
    # Colored
    "ColoredPetriNet", "ColoredPlace", "ColoredTransition",
    "ColorSet", "ColoredToken", "ArcInscription",
    "INT", "STRING", "BOOL", "UNIT",
    # Batch
    "batch_simulate", "BatchStats",
    # Config / serialization
    "load_config", "save_config", "from_config_dict", "to_config_dict",
    "to_pnml", "from_pnml", "validate_pnml",
    # Presets
    "dining_philosophers", "producer_consumer", "mutual_exclusion",
    "workflow_net", "state_machine", "free_choice_net", "readers_writers",
    "simple_buffer", "token_ring", "elevator_system",
    "producer_consumer_chain", "database_transaction",
    # Visualization
    "ascii_net", "ascii_marking", "reachability_dot", "reachability_ascii",
]