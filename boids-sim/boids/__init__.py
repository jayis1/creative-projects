"""Boids Flocking Simulation — Enhanced v2.0

A Reynolds boids flocking simulator with spatial hashing, multiple behaviors,
obstacle avoidance, predators, goal seeking, trail rendering, config files,
presets, serialization, and multiple visualization backends.

Implements Craig Reynolds' classic boids algorithm (1987) with:
  - Separation: avoid crowding neighbors
  - Alignment: steer toward average heading of neighbors
  - Cohesion: steer toward average position of neighbors

Additional behaviors:
  - Obstacle avoidance
  - Predator evasion
  - Goal seeking
  - Bounding/wall avoidance
  - Trail rendering with fading
  - Config presets
  - Save/load state
"""

from boids.simulation import BoidSimulation, SimulationConfig
from boids.boid import Boid
from boids.vector import Vector2
from boids.spatial_hash import SpatialHashGrid
from boids.renderer import ASCIIRenderer, SVGRenderer, PPMRenderer, TrailSVGRenderer
from boids.config import load_config, save_config, PRESETS
from boids.boid import BoidState  # re-export for convenience

__version__ = "2.0.0"
__all__ = [
    "BoidSimulation",
    "SimulationConfig",
    "Boid",
    "Vector2",
    "SpatialHashGrid",
    "ASCIIRenderer",
    "SVGRenderer",
    "PPMRenderer",
    "TrailSVGRenderer",
    "load_config",
    "save_config",
    "PRESETS",
]