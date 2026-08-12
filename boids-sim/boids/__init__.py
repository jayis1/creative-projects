"""Boids Flocking Simulation — Enhanced v3.0

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
  - Arrival (decelerating seek)
  - Wander (Reynolds-style constrained random walk)
  - Path following (waypoint navigation)
  - Boundary/wall avoidance
  - Multi-species flocking

Features:
  - Pluggable spatial index (uniform grid or quadtree)
  - Event/callback system
  - Stats time-series tracking
  - Config presets and files (JSON/YAML/TOML)
  - Save/load state
  - Animated SVG export
  - Multiple renderers (ASCII/SVG/TrailSVG/PPM/AnimatedSVG/JSON)
"""

from boids.simulation import BoidSimulation, Obstacle
from boids.boid import Boid, BoidState
from boids.vector import Vector2
from boids.spatial_hash import SpatialHashGrid
from boids.spatial_index import SpatialIndex
from boids.quadtree import QuadTree
from boids.renderer import (
    ASCIIRenderer,
    SVGRenderer,
    PPMRenderer,
    TrailSVGRenderer,
    AnimatedSVGRenderer,
    JSONRenderer,
)
from boids.config import load_config, save_config, get_preset, list_presets, PRESETS, SimulationConfig
from boids.events import EventBus
from boids.stats_tracker import StatsTracker

__version__ = "3.0.0"
__all__ = [
    "BoidSimulation",
    "Obstacle",
    "SimulationConfig",
    "Boid",
    "BoidState",
    "Vector2",
    "SpatialHashGrid",
    "SpatialIndex",
    "QuadTree",
    "ASCIIRenderer",
    "SVGRenderer",
    "PPMRenderer",
    "TrailSVGRenderer",
    "AnimatedSVGRenderer",
    "JSONRenderer",
    "load_config",
    "save_config",
    "get_preset",
    "list_presets",
    "PRESETS",
    "EventBus",
    "StatsTracker",
]