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

from .simulation import Simulation, Body, SimulationResult
from .barnes_hut import BHTree

__all__ = [
    "Simulation",
    "Body",
    "SimulationResult",
    "BHTree",
    "__version__",
]

__version__ = "1.0.0"