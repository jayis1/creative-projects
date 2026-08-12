"""Boids simulation engine — ties boids, spatial hashing, and behaviors together.

Enhanced v2.0: uses enhanced SimulationConfig, supports save/load, wander behavior,
config presets, trail rendering, improved neighbor queries with unified perception radius.
"""

from __future__ import annotations
import json
import math
import random
from dataclasses import dataclass, field
from typing import Optional, Any

from boids.boid import Boid, BoidState
from boids.config import SimulationConfig
from boids.vector import Vector2
from boids.spatial_hash import SpatialHashGrid


@dataclass
class Obstacle:
    """A circular obstacle boids should avoid."""

    pos: Vector2
    radius: float

    def to_dict(self) -> dict:
        return {"pos": [self.pos.x, self.pos.y], "radius": self.radius}


class BoidSimulation:
    """Manages a collection of boids and steps the simulation forward.

    Usage::

        sim = BoidSimulation(SimulationConfig(num_boids=200))
        for _ in range(100):
            sim.step()

    Enhanced v2.0:
        - Config from boids.config (with presets, save/load)
        - Wander behavior
        - Save/load simulation state to JSON
        - Trail support
        - Improved stats with flock centroid and spread
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
        cfg = self.config
        for _ in range(cfg.num_boids):
            x = rng.uniform(0, cfg.width)
            y = rng.uniform(0, cfg.height)
            angle = rng.uniform(0, math.tau)
            speed = rng.uniform(1.0, cfg.max_speed)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            b = Boid(
                x, y, vx, vy,
                max_speed=cfg.max_speed,
                max_force=cfg.max_force,
                radius=cfg.radius,
                trail_length=cfg.trail_length,
            )
            self.boids.append(b)

    # ------------------------------------------------------------------ #
    #  Setup helpers
    # ------------------------------------------------------------------ #
    def add_obstacle(self, x: float, y: float, radius: float) -> None:
        self.obstacles.append(Obstacle(Vector2(x, y), radius))

    def add_predator(self, x: float, y: float) -> None:
        cfg = self.config
        angle = random.uniform(0, math.tau)
        pred = Boid(
            x, y,
            math.cos(angle) * 2.0, math.sin(angle) * 2.0,
            max_speed=cfg.predator_max_speed,
            max_force=cfg.predator_max_force,
            radius=6.0,
            kind="predator",
            trail_length=cfg.trail_length,
        )
        self.predators.append(pred)

    def set_goal(self, x: float, y: float) -> None:
        self.goal = Vector2(x, y)

    def clear_goal(self) -> None:
        self.goal = None

    def add_boid(self, x: float, y: float) -> None:
        """Add a single boid at position (x, y)."""
        angle = random.uniform(0, math.tau)
        speed = random.uniform(1.0, self.config.max_speed)
        b = Boid(
            x, y,
            math.cos(angle) * speed, math.sin(angle) * speed,
            max_speed=self.config.max_speed,
            max_force=self.config.max_force,
            radius=self.config.radius,
            trail_length=self.config.trail_length,
        )
        self.boids.append(b)

    def remove_boid(self, index: int) -> None:
        """Remove the boid at *index* from the flock."""
        if 0 <= index < len(self.boids):
            self.boids.pop(index)

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
        """Query the spatial hash for candidate neighbors within *perception*.

        Uses a distance-squared comparison to avoid sqrt calls.
        """
        candidates = self.grid.query(boid.pos.x, boid.pos.y, perception)
        # filter by actual distance
        neighbors = []
        px, py = boid.pos.x, boid.pos.y
        sq = perception * perception
        for other in candidates:
            if other is boid:
                continue
            dx = px - other.pos.x
            dy = py - other.pos.y
            if dx * dx + dy * dy <= sq:
                neighbors.append(other)
        return neighbors

    def step(self) -> None:
        """Advance the simulation by one tick.

        For each boid, computes separation, alignment, cohesion, obstacle
        avoidance, predator evasion, goal seeking, wander, and boundary
        forces, sums them with configurable weights, and integrates.
        """
        self.tick += 1
        cfg = self.config
        self._rebuild_grid()

        # Use the largest perception radius for a single neighbor query,
        # then filter within each behavior (avoids 3x grid queries per boid).
        max_perception = max(cfg.sep_perception, cfg.ali_perception, cfg.coh_perception)
        all_neighbors_cache: dict[int, list[Boid]] = {}

        for boid in self.boids:
            # Query once with the largest radius and reuse for all behaviors
            neighbors = self._get_neighbors(boid, max_perception)
            all_neighbors_cache[boid.id] = neighbors

            sep = boid.separation(neighbors, cfg.sep_perception)
            ali = boid.alignment(neighbors, cfg.ali_perception)
            coh = boid.cohesion(neighbors, cfg.coh_perception)

            boid.apply_force(sep * cfg.w_sep)
            boid.apply_force(ali * cfg.w_ali)
            boid.apply_force(coh * cfg.w_coh)

            # wander
            if cfg.w_wander > 0:
                wander = boid.wander(cfg.w_wander)
                boid.apply_force(wander)

            # obstacle avoidance
            for obs in self.obstacles:
                avoid = boid.avoid_obstacle(obs.pos, obs.radius)
                boid.apply_force(avoid * cfg.w_avoid)

            # predator evasion
            for pred in self.predators:
                flee = boid.flee(pred.pos, panic_dist=cfg.predator_panic_dist)
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

        # update predators (wander + chase nearest boid)
        for pred in self.predators:
            self._update_predator(pred)

    def _update_predator(self, pred: Boid) -> None:
        """Predators wander and chase the nearest boid within chase radius."""
        cfg = self.config
        # find nearest boid via spatial hash
        candidates = self.grid.query(pred.pos.x, pred.pos.y, cfg.predator_chase_radius)
        nearest = None
        nearest_d = float("inf")
        for b in candidates:
            if b.kind == "predator":
                continue
            d = Vector2.dist_sq(pred.pos, b.pos)
            if d < nearest_d:
                nearest_d = d
                nearest = b

        chase_sq = cfg.predator_chase_radius ** 2
        if nearest is not None and nearest_d < chase_sq:
            seek = pred.seek(nearest.pos)
            pred.apply_force(seek * 2.0)
        else:
            wander = pred.wander(0.3)
            pred.apply_force(wander)

        # boundary
        if cfg.use_wrap:
            self._wrap(pred)
        else:
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
    #  Statistics
    # ------------------------------------------------------------------ #
    def stats(self) -> dict:
        """Return aggregate statistics about the flock.

        Includes count, average speed, alignment (0-1), flock centroid,
        spatial spread (std dev of positions), and heading.
        """
        if not self.boids:
            return {
                "tick": self.tick, "count": 0, "predators": len(self.predators),
                "obstacles": len(self.obstacles), "avg_speed": 0.0,
                "avg_heading": 0.0, "alignment": 0.0,
                "centroid": [0.0, 0.0], "spread": 0.0,
            }
        n = len(self.boids)
        speeds = [b.vel.length() for b in self.boids]
        headings = [b.vel.angle for b in self.boids]
        avg_speed = sum(speeds) / n
        avg_hx = sum(math.cos(h) for h in headings) / n
        avg_hy = sum(math.sin(h) for h in headings) / n
        avg_heading = math.atan2(avg_hy, avg_hx)

        # centroid
        cx = sum(b.pos.x for b in self.boids) / n
        cy = sum(b.pos.y for b in self.boids) / n

        # spatial spread (average distance from centroid)
        spread = sum(math.sqrt((b.pos.x - cx) ** 2 + (b.pos.y - cy) ** 2) for b in self.boids) / n

        return {
            "tick": self.tick,
            "count": n,
            "predators": len(self.predators),
            "obstacles": len(self.obstacles),
            "avg_speed": avg_speed,
            "avg_heading": avg_heading,
            "alignment": math.sqrt(avg_hx * avg_hx + avg_hy * avg_hy),
            "centroid": [cx, cy],
            "spread": spread,
        }

    # ------------------------------------------------------------------ #
    #  Serialization (save/load full simulation state)
    # ------------------------------------------------------------------ #
    def to_dict(self) -> dict:
        """Serialize the entire simulation state to a dictionary."""
        return {
            "config": self.config.to_dict(),
            "tick": self.tick,
            "boids": [b.to_dict() for b in self.boids],
            "obstacles": [o.to_dict() for o in self.obstacles],
            "predators": [p.to_dict() for p in self.predators],
            "goal": [self.goal.x, self.goal.y] if self.goal else None,
        }

    def save(self, path: str) -> None:
        """Save simulation state to a JSON file."""
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: str) -> "BoidSimulation":
        """Load a simulation state from a JSON file.

        Restores all boids, predators, obstacles, goal, and config.
        """
        with open(path) as f:
            data = json.load(f)
        cfg = SimulationConfig.from_dict(data["config"])
        sim = cls.__new__(cls)
        sim.config = cfg
        sim.boids = []
        sim.predators = []
        sim.obstacles = []
        sim.goal = None
        sim.grid = SpatialHashGrid(cfg.cell_size)
        sim.tick = data.get("tick", 0)

        for bdata in data.get("boids", []):
            state = BoidState(
                id=bdata["id"],
                x=bdata["pos"][0], y=bdata["pos"][1],
                vx=bdata["vel"][0], vy=bdata["vel"][1],
                max_speed=bdata["max_speed"],
                max_force=bdata["max_force"],
                radius=bdata["radius"],
                kind=bdata["kind"],
            )
            sim.boids.append(Boid.restore(state, trail_length=cfg.trail_length))

        for pdata in data.get("predators", []):
            state = BoidState(
                id=pdata["id"],
                x=pdata["pos"][0], y=pdata["pos"][1],
                vx=pdata["vel"][0], vy=pdata["vel"][1],
                max_speed=pdata["max_speed"],
                max_force=pdata["max_force"],
                radius=pdata["radius"],
                kind=pdata["kind"],
            )
            sim.predators.append(Boid.restore(state, trail_length=cfg.trail_length))

        for odata in data.get("obstacles", []):
            sim.obstacles.append(Obstacle(Vector2(odata["pos"][0], odata["pos"][1]), odata["radius"]))

        if data.get("goal"):
            sim.goal = Vector2(data["goal"][0], data["goal"][1])

        return sim