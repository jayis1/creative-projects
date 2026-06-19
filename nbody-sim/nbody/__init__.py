"""nbody-sim: a 2D Barnes–Hut N-body gravity simulator.

Subpackages
-----------
- :mod:`nbody.vec`      – lightweight 2-D vector helpers
- :mod:`nbody.barnes_hut` – quadtree + θ-opening force evaluator
- :mod:`nbody.integrator` – kick–drift–kick (leapfrog) integrator
- :mod:`nbody.simulation` – orchestrating :class:`Simulation`
- :mod:`nbody.renderer`  – PPM frame rendering
- :mod:`nbody.cli`       – command-line front-end
"""

from .simulation import Simulation, SimulationResult
from .barnes_hut import BHTree
from .body import Body
from .brute_force import benchmark, brute_force_accelerations
from .diagnostics import (
    total_angular_momentum,
    com_velocity,
    virial_ratio,
    min_separation,
    max_acceleration,
    adaptive_dt,
)

__all__ = [
    "Simulation",
    "Body",
    "SimulationResult",
    "BHTree",
    "benchmark",
    "brute_force_accelerations",
    "total_angular_momentum",
    "com_velocity",
    "virial_ratio",
    "min_separation",
    "max_acceleration",
    "adaptive_dt",
    "__version__",
]

__version__ = "2.0.0"