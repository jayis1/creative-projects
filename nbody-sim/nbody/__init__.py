"""nbody-sim: a 2D Barnes–Hut N-body gravity simulator.

Subpackages
-----------
- :mod:`nbody.vec`         – lightweight 2-D vector helpers
- :mod:`nbody.barnes_hut`  – quadtree + θ-opening force evaluator
- :mod:`nbody.integrator`  – kick–drift–kick (leapfrog) integrator (legacy)
- :mod:`nbody.integrators` – multiple integrators (leapfrog, RK4, Forest–Ruth)
- :mod:`nbody.simulation`  – orchestrating :class:`Simulation`
- :mod:`nbody.renderer`   – PPM frame rendering
- :mod:`nbody.cli`         – command-line front-end
- :mod:`nbody.config`      – YAML/JSON/TOML config files
- :mod:`nbody.numpy_force` – NumPy-accelerated force evaluation
- :mod:`nbody.logging_utils` – structured logging
"""

from .simulation import Simulation, SimulationResult, Snapshot
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
from .integrators import (
    LeapfrogIntegrator,
    RK4Integrator,
    ForestRuthIntegrator,
    make_integrator,
    INTEGRATORS,
)
from .config import SimConfig, load_config, save_config

__all__ = [
    "Simulation",
    "Body",
    "Snapshot",
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
    "LeapfrogIntegrator",
    "RK4Integrator",
    "ForestRuthIntegrator",
    "make_integrator",
    "INTEGRATORS",
    "SimConfig",
    "load_config",
    "save_config",
    "__version__",
]

__version__ = "3.0.0"