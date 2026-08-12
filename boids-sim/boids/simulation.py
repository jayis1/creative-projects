"""Boids simulation engine — ties boids, spatial hashing, and behaviors together."""

from __future__ import annotations
import math
import random
from dataclasses import dataclass, field
from typing import Optional

from boids.boid import Boid
from boids.vector import Vector2
from boids.spatial_hash import SpatialHashGrid


@dataclass
class SimulationConfig:
    """Configuration for the boids simulation."""

    width: float = 800.0
    height: float = 600.0
    num_boids: int = 150
    max_speed: float = 4.0
    max_force: float = 0.2

    # perception radii
    sep_perception: float = 30.0
    ali_perception: float = 60.0
    coh_perception: float = 60.0

    # behavior weights
    w_sep: float = 1.5
    w_ali: float = 1.0
    w_coh: float = 1.0
    w_boundary: float = 1.0
    w_avoid: float = 2.0
    w_flee: float = 3.0
    w_seek: float = 0.5

    # simulation
    dt: float = 1.0
    boundary_margin: float = 50.0
    use_wrap: bool = False  # toroidal world if True

    # spatial hash
    cell_size: float = 60.0


@dataclass
class Obstacle:
    """A circular obstacle boids should avoid."""

    pos: Vector2
    radius: float


class BoidSimulation:
    """Manages a collection of boids and steps the simulation forward.

    Usage::

        sim = BoidSimulation(SimulationConfig(num_boids=200))
        for _ in range(100):
            sim.step()
    """

    def __init__(self, config: Optional[SimulationConfig] = None):
        self.config = config or SimulationConfig()
        self.boids: list[Boid] = []
        self.obstacles: list[Obstacle] = []
        self.predators: list[Boid] = []
        self.goal: Optional[Vector2] = None
        self.grid = SpatialHashGrid(self.config.cell_size)
        self.tick = 0
        self._populate()

    def _populate(self) -> None:
        """Initialize boids with random positions and velocities."""
        rng = random.Random()
        for _ in range(self.config.num_boids):
            x = rng.uniform(0, self.config.width)
            y = rng.uniform(0, self.config.height)
            angle = rng.uniform(0, math.tau)
            speed = rng.uniform(1.0, self.config.max_speed)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            b = Boid(
                x, y, vx, vy,
                max_speed=self.config.max_speed,
                max_force=self.config.max_force,
            )
            self.boids.append(b)

    # ------------------------------------------------------------------ #
    #  Setup helpers
    # ------------------------------------------------------------------ #
    def add_obstacle(self, x: float, y: float, radius: float) -> None:
        self.obstacles.append(Obstacle(Vector2(x, y), radius))

    def add_predator(self, x: float, y: float) -> None:
        angle = random.uniform(0, math.tau)
        pred = Boid(
            x, y,
            math.cos(angle) * 2.0, math.sin(angle) * 2.0,
            max_speed=self.config.max_speed * 1.5,
            max_force=self.config.max_force * 1.5,
            radius=6.0,
            kind="predator",
        )
        self.predators.append(pred)

    def set_goal(self, x: float, y: float) -> None:
        self.goal = Vector2(x, y)

    def clear_goal(self) -> None:
        self.goal = None

    # ------------------------------------------------------------------ #
    #  Simulation step
    # ------------------------------------------------------------------ #
    def _rebuild_grid(self) -> None:
        """Clear and re-populate the spatial hash grid with all boids and predators."""
        self.grid.clear()
        for b in self.boids:
            self.grid.insert(b, b.pos.x, b.pos.y)
        for p in self.predators:
            self.grid.insert(p, p.pos.x, p.pos.y)

    def _get_neighbors(self, boid: Boid, perception: float) -> list[Boid]:
        """Query the spatial hash for candidate neighbors within *perception*."""
        candidates = self.grid.query(boid.pos.x, boid.pos.y, perception)
        # filter by actual distance
        neighbors = []
        for other in candidates:
            if other is boid:
                continue
            if Vector2.dist_sq(boid.pos, other.pos) <= perception * perception:
                neighbors.append(other)
        return neighbors

    def step(self) -> None:
        """Advance the simulation by one tick."""
        self.tick += 1
        cfg = self.config
        self._rebuild_grid()

        for boid in self.boids:
            # core flocking behaviors
            sep_neighbors = self._get_neighbors(boid, cfg.sep_perception)
            ali_neighbors = self._get_neighbors(boid, cfg.ali_perception)
            coh_neighbors = self._get_neighbors(boid, cfg.coh_perception)

            sep = boid.separation(sep_neighbors, cfg.sep_perception)
            ali = boid.alignment(ali_neighbors, cfg.ali_perception)
            coh = boid.cohesion(coh_neighbors, cfg.coh_perception)

            boid.apply_force(sep * cfg.w_sep)
            boid.apply_force(ali * cfg.w_ali)
            boid.apply_force(coh * cfg.w_coh)

            # obstacle avoidance
            for obs in self.obstacles:
                avoid = boid.avoid_obstacle(obs.pos, obs.radius)
                boid.apply_force(avoid * cfg.w_avoid)

            # predator evasion
            for pred in self.predators:
                flee = boid.flee(pred.pos, panic_dist=80.0)
                boid.apply_force(flee * cfg.w_flee)

            # goal seeking
            if self.goal is not None:
                seek = boid.seek(self.goal)
                boid.apply_force(seek * cfg.w_seek)

            # boundary handling
            if cfg.use_wrap:
                self._wrap(boid)
            else:
                bf = boid.boundary_force(
                    cfg.width, cfg.height, cfg.boundary_margin
                )
                boid.apply_force(bf * cfg.w_boundary)

            boid.update(cfg.dt)

        # update predators (simple wander + chase nearest boid)
        for pred in self.predators:
            self._update_predator(pred)

    def _update_predator(self, pred: Boid) -> None:
        """Predators wander and chase the nearest boid."""
        cfg = self.config
        # find nearest boid
        nearest = None
        nearest_d = float("inf")
        for b in self.boids:
            d = Vector2.dist_sq(pred.pos, b.pos)
            if d < nearest_d:
                nearest_d = d
                nearest = b
        if nearest is not None and nearest_d < 200.0 * 200.0:
            seek = pred.seek(nearest.pos)
            pred.apply_force(seek * 2.0)
        else:
            # wander: random steering
            wander = Vector2.random_unit()
            wander.scale(pred.max_force * 0.3)
            pred.apply_force(wander)

        # boundary
        bf = pred.boundary_force(cfg.width, cfg.height, cfg.boundary_margin)
        pred.apply_force(bf * 2.0)
        pred.update(cfg.dt)

    def _wrap(self, boid: Boid) -> None:
        """Toroidal wrap: boids that exit one side re-enter the opposite."""
        if boid.pos.x < 0:
            boid.pos.x += self.config.width
        elif boid.pos.x >= self.config.width:
            boid.pos.x -= self.config.width
        if boid.pos.y < 0:
            boid.pos.y += self.config.height
        elif boid.pos.y >= self.config.height:
            boid.pos.y -= self.config.height

    # ------------------------------------------------------------------ #
    #  Utilities
    # ------------------------------------------------------------------ #
    def stats(self) -> dict:
        """Return aggregate statistics about the flock."""
        if not self.boids:
            return {"count": 0, "avg_speed": 0.0, "avg_heading": 0.0}
        speeds = [b.vel.length() for b in self.boids]
        headings = [b.vel.angle for b in self.boids]
        avg_speed = sum(speeds) / len(speeds)
        avg_hx = sum(math.cos(h) for h in headings) / len(headings)
        avg_hy = sum(math.sin(h) for h in headings) / len(headings)
        avg_heading = math.atan2(avg_hy, avg_hx)
        return {
            "tick": self.tick,
            "count": len(self.boids),
            "predators": len(self.predators),
            "obstacles": len(self.obstacles),
            "avg_speed": avg_speed,
            "avg_heading": avg_heading,
            "alignment": math.sqrt(avg_hx * avg_hx + avg_hy * avg_hy),  # 0-1, 1=perfect alignment
        }

    def to_dict(self) -> dict:
        return {
            "config": self.config.__dict__,
            "tick": self.tick,
            "boids": [b.to_dict() for b in self.boids],
            "obstacles": [
                {"pos": [o.pos.x, o.pos.y], "radius": o.radius}
                for o in self.obstacles
            ],
            "predators": [p.to_dict() for p in self.predators],
            "goal": [self.goal.x, self.goal.y] if self.goal else None,
        }