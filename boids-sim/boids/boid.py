"""Individual boid entity with steering behaviors."""

from __future__ import annotations
import math
from boids.vector import Vector2


class Boid:
    """A single boid agent with position, velocity, and acceleration.

    The boid accumulates steering forces each tick and integrates them
    with simple Euler integration. Each behavior method returns a desired
    steering force (acceleration) which the Simulation sums with weights.
    """

    __slots__ = ("id", "pos", "vel", "acc", "max_speed", "max_force", "radius", "kind")

    _next_id = 0

    def __init__(
        self,
        x: float,
        y: float,
        vx: float = 0.0,
        vy: float = 0.0,
        max_speed: float = 4.0,
        max_force: float = 0.2,
        radius: float = 3.0,
        kind: str = "boid",
    ):
        self.id = Boid._next_id
        Boid._next_id += 1
        self.pos = Vector2(x, y)
        self.vel = Vector2(vx, vy)
        self.acc = Vector2(0.0, 0.0)
        self.max_speed = max_speed
        self.max_force = max_force
        self.radius = radius
        self.kind = kind  # "boid", "predator"

    # ------------------------------------------------------------------ #
    #  Steering behaviors
    # ------------------------------------------------------------------ #
    def separation(self, neighbors: list["Boid"], perception: float) -> Vector2:
        """Steer away from nearby neighbors within *perception* radius."""
        steer = Vector2(0.0, 0.0)
        count = 0
        for other in neighbors:
            if other is self or other.kind == "predator":
                continue
            d = Vector2.dist(self.pos, other.pos)
            if 0.0 < d < perception:
                # inversely proportional to distance
                diff = self.pos - other.pos
                diff.scale(1.0 / d)
                steer.add(diff)
                count += 1
        if count > 0:
            steer.scale(1.0 / count)
            if steer.length_sq() > 0:
                steer.set_length(self.max_speed)
                steer.sub(self.vel)
                steer.limit(self.max_force)
        return steer

    def alignment(self, neighbors: list["Boid"], perception: float) -> Vector2:
        """Steer toward the average heading of nearby neighbors."""
        avg = Vector2(0.0, 0.0)
        count = 0
        for other in neighbors:
            if other is self or other.kind == "predator":
                continue
            if Vector2.dist(self.pos, other.pos) < perception:
                avg.add(other.vel)
                count += 1
        if count > 0:
            avg.scale(1.0 / count)
            avg.set_length(self.max_speed)
            avg.sub(self.vel)
            avg.limit(self.max_force)
        return avg

    def cohesion(self, neighbors: list["Boid"], perception: float) -> Vector2:
        """Steer toward the average position of nearby neighbors."""
        center = Vector2(0.0, 0.0)
        count = 0
        for other in neighbors:
            if other is self or other.kind == "predator":
                continue
            if Vector2.dist(self.pos, other.pos) < perception:
                center.add(other.pos)
                count += 1
        if count > 0:
            center.scale(1.0 / count)
            return self._seek(center)
        return Vector2(0.0, 0.0)

    def _seek(self, target: Vector2) -> Vector2:
        """Steer toward a target position at max speed."""
        desired = target - self.pos
        if desired.length_sq() < 1e-10:
            return Vector2(0.0, 0.0)
        desired.set_length(self.max_speed)
        steer = desired - self.vel
        steer.limit(self.max_force)
        return steer

    def seek(self, target: Vector2) -> Vector2:
        """Public seek behavior."""
        return self._seek(target)

    def flee(self, target: Vector2, panic_dist: float = 80.0) -> Vector2:
        """Steer away from a target if within panic_dist."""
        d = Vector2.dist(self.pos, target)
        if d < panic_dist and d > 1e-6:
            desired = self.pos - target
            desired.set_length(self.max_speed)
            steer = desired - self.vel
            steer.limit(self.max_force * 2.0)  # stronger when fleeing
            return steer
        return Vector2(0.0, 0.0)

    def avoid_obstacle(self, obstacle_pos: Vector2, obstacle_radius: float) -> Vector2:
        """Steer away from a circular obstacle."""
        d = Vector2.dist(self.pos, obstacle_pos)
        safe = obstacle_radius + self.radius + 20.0
        if d < safe and d > 1e-6:
            # stronger as we get closer
            urgency = 1.0 - (d / safe)
            away = self.pos - obstacle_pos
            away.normalize()
            away.set_length(self.max_speed * (0.5 + urgency))
            steer = away - self.vel
            steer.limit(self.max_force * 3.0)
            return steer
        return Vector2(0.0, 0.0)

    def boundary_force(
        self, width: float, height: float, margin: float = 50.0
    ) -> Vector2:
        """Soft steering force to keep boids inside the simulation area."""
        force = Vector2(0.0, 0.0)
        if self.pos.x < margin:
            force.x = (margin - self.pos.x) / margin * self.max_force * 5
        elif self.pos.x > width - margin:
            force.x = -((self.pos.x - (width - margin)) / margin) * self.max_force * 5
        if self.pos.y < margin:
            force.y = (margin - self.pos.y) / margin * self.max_force * 5
        elif self.pos.y > height - margin:
            force.y = -((self.pos.y - (height - margin)) / margin) * self.max_force * 5
        return force

    # ------------------------------------------------------------------ #
    #  Integration
    # ------------------------------------------------------------------ #
    def apply_force(self, force: Vector2) -> None:
        """Accumulate a steering force."""
        self.acc.add(force)

    def update(self, dt: float = 1.0) -> None:
        """Integrate acceleration -> velocity -> position (Euler)."""
        self.vel.add(self.acc)
        self.vel.limit(self.max_speed)
        self.pos.x += self.vel.x * dt
        self.pos.y += self.vel.y * dt
        self.acc.x = 0.0
        self.acc.y = 0.0

    def __repr__(self) -> str:
        return f"Boid(id={self.id}, pos={self.pos}, vel={self.vel})"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "pos": [self.pos.x, self.pos.y],
            "vel": [self.vel.x, self.vel.y],
            "max_speed": self.max_speed,
            "max_force": self.max_force,
            "radius": self.radius,
            "kind": self.kind,
        }