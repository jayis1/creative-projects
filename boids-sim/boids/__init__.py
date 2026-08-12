"""
Boids Flocking Simulation
==========================

A Reynolds boids flocking simulator with spatial hashing, multiple behaviors,
obstacle avoidance, predators, and multiple visualization backends.

Implements Craig Reynolds' classic boids algorithm (1987) with:
  - Separation: avoid crowding neighbors
  - Alignment: steer toward average heading of neighbors
  - Cohesion: steer toward average position of neighbors

Additional behaviors:
  - Obstacle avoidance
  - Predator evasion
  - Goal seeking
  - Bounding/wall avoidance

Performance via uniform-grid spatial hashing for O(n) neighbor queries.
"""

from boids.simulation import BoidSimulation
from boids.boid import Boid
from boids.vector import Vector2
from boids.spatial_hash import SpatialHashGrid
from boids.renderer import ASCIIRenderer, SVGRenderer, PPMRenderer

__version__ = "1.0.0"
__all__ = [
    "BoidSimulation",
    "Boid",
    "Vector2",
    "SpatialHashGrid",
    "ASCIIRenderer",
    "SVGRenderer",
    "PPMRenderer",
]