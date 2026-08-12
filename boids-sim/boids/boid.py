"""Individual boid entity with steering behaviors.

Enhanced v3.0: trail tracking, BoidState snapshot/restore, wander behavior,
path following, species support, arrival behavior, queue/flow-field helpers.

The Boid class implements Craig Reynolds' steering model where each agent
accumulates steering forces (accelerations) each tick and integrates them
via simple Euler integration.

Behaviors implemented:
    - Separation: steer away from crowding neighbors
    - Alignment: match average heading of neighbors
    - Cohesion: steer toward average position of neighbors
    - Seek: steer toward a target position
    - Flee: steer away from a threat (with urgency scaling)
    - Arrive: like seek but decelerates near target (Reynolds arrival)
    - Wander: Reynolds-style constrained random walk
    - Path following: follow a sequence of waypoints with arrival radius
    - Obstacle avoidance: steer away from circular obstacles
    - Boundary force: soft steering to stay inside the simulation area
"""

from __future__ import annotations
import math
import random
from collections import deque
from dataclasses import dataclass
from typing import Optional
from boids.vector import Vector2


@dataclass
class BoidState:
    """Serializable snapshot of a boid's state for save/load."""

    id: int
    x: float
    y: float
    vx: float
    vy: float
    max_speed: float
    max_force: float
    radius: float
    kind: str
    species: int = 0
    path_index: int = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "pos": [self.x, self.y],
            "vel": [self.vx, self.vy],
            "max_speed": self.max_speed,
            "max_force": self.max_force,
            "radius": self.radius,
            "kind": self.kind,
            "species": self.species,
            "path_index": self.path_index,
        }


class Boid:
    """A single boid agent with position, velocity, and acceleration.

    The boid accumulates steering forces each tick and integrates them
    with simple Euler integration. Each behavior method returns a desired
    steering force (acceleration) which the Simulation sums with weights.

    Enhanced v2.0:
        - Trail tracking via deque for rendering fading paths
        - BoidState snapshot/restore for serialization
        - Wander behavior (Reynolds-style constrained random walk)
    """

    __slots__ = ("id", "pos", "vel", "acc", "max_speed", "max_force", "radius",
                  "kind", "species", "trail", "_wander_angle", "path", "path_index")

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
        species: int = 0,
        trail_length: int = 0,
        path: Optional[list[Vector2]] = None,
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
        self.species = species
        self.trail: deque[tuple[float, float]] = deque(maxlen=trail_length) if trail_length > 0 else None
        self._wander_angle: float = random.uniform(0, math.tau)
        self.path = path
        self.path_index = 0

    # ------------------------------------------------------------------ #
    #  Steering behaviors
    # ------------------------------------------------------------------ #
    def separation(self, neighbors: list["Boid"], perception: float) -> Vector2:
        """Steer away from nearby neighbors within *perception* radius.

        The force is inversely proportional to distance — closer neighbors
        exert a stronger repulsion.

        If the boid has a non-zero ``species``, only same-species boids are
        considered for separation.
        """
        steer = Vector2(0.0, 0.0)
        count = 0
        for other in neighbors:
            if other is self or other.kind == "predator":
                continue
            if self.species != 0 and other.species != self.species:
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
        """Steer toward the average heading of nearby neighbors.

        Respects species boundaries if ``species`` is non-zero.
        """
        avg = Vector2(0.0, 0.0)
        count = 0
        for other in neighbors:
            if other is self or other.kind == "predator":
                continue
            if self.species != 0 and other.species != self.species:
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
        """Steer toward the average position of nearby neighbors.

        Respects species boundaries if ``species`` is non-zero.
        """
        center = Vector2(0.0, 0.0)
        count = 0
        for other in neighbors:
            if other is self or other.kind == "predator":
                continue
            if self.species != 0 and other.species != self.species:
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

    def arrive(self, target: Vector2, slow_radius: float = 100.0) -> Vector2:
        """Steer toward a target, decelerating as it approaches.

        Like ``seek()`` but reduces speed when within *slow_radius* of the
        target. The desired speed is scaled linearly from 0 (at target) to
        max_speed (at slow_radius).

        Reynolds' arrival behavior (1999).
        """
        desired = target - self.pos
        d = desired.length()
        if d < 1e-10:
            return Vector2(0.0, 0.0)
        if d < slow_radius:
            # Map speed from 0 at d=0 to max_speed at d=slow_radius
            speed = self.max_speed * (d / slow_radius)
        else:
            speed = self.max_speed
        desired.set_length(speed)
        steer = desired - self.vel
        steer.limit(self.max_force)
        return steer

    def follow_path(self, loop: bool = False, arrival_radius: float = 20.0) -> Vector2:
        """Follow a predefined path of waypoints.

        The boid seeks the current waypoint and advances to the next when
        within *arrival_radius*. If *loop* is True, the path wraps around;
        otherwise the boid arrives at the final waypoint.

        Returns a zero vector if no path is set.
        """
        if self.path is None or len(self.path) == 0:
            return Vector2(0.0, 0.0)
        # Clamp path_index to valid range
        if self.path_index >= len(self.path):
            self.path_index = len(self.path) - 1
        target = self.path[self.path_index]
        d = Vector2.dist(self.pos, target)
        if d < arrival_radius:
            # Advance to next waypoint
            if self.path_index < len(self.path) - 1:
                self.path_index += 1
            elif loop:
                self.path_index = 0
            else:
                # Arrived at final waypoint — decelerate
                return self.arrive(target, slow_radius=arrival_radius * 2)
            target = self.path[self.path_index]
        return self._seek(target)

    def flee(self, target: Vector2, panic_dist: float = 80.0) -> Vector2:
        """Steer away from a target if within panic_dist.

        The steering force is amplified when the threat is closer.
        """
        d = Vector2.dist(self.pos, target)
        if d < panic_dist and d > 1e-6:
            desired = self.pos - target
            desired.set_length(self.max_speed)
            steer = desired - self.vel
            # stronger when closer
            urgency = 1.0 + (1.0 - d / panic_dist) * 2.0
            steer.limit(self.max_force * urgency)
            return steer
        return Vector2(0.0, 0.0)

    def avoid_obstacle(self, obstacle_pos: Vector2, obstacle_radius: float) -> Vector2:
        """Steer away from a circular obstacle.

        Returns a steering force that grows stronger as the boid approaches
        the obstacle's safe perimeter (obstacle_radius + boid_radius + margin).
        """
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
        """Soft steering force to keep boids inside the simulation area.

        The force is zero when the boid is more than *margin* away from any
        edge, and ramps up linearly as the boid approaches the boundary.

        FIX: guards against ZeroDivisionError when margin=0 by returning
        a zero vector (no boundary force with zero margin).
        """
        force = Vector2(0.0, 0.0)
        # FIX: avoid division by zero when margin is 0
        if margin <= 0:
            return force
        if self.pos.x < margin:
            force.x = (margin - self.pos.x) / margin * self.max_force * 5
        elif self.pos.x > width - margin:
            force.x = -((self.pos.x - (width - margin)) / margin) * self.max_force * 5
        if self.pos.y < margin:
            force.y = (margin - self.pos.y) / margin * self.max_force * 5
        elif self.pos.y > height - margin:
            force.y = -((self.pos.y - (height - margin)) / margin) * self.max_force * 5
        return force

    def wander(self, strength: float = 0.1) -> Vector2:
        """Reynolds-style wander: project a circle ahead and randomly shift target.

        Uses a wandering angle that changes slightly each call, producing
        smooth constrained random steering.
        """
        wander_radius = 25.0
        wander_distance = 55.0
        # randomly shift wander angle
        self._wander_angle += random.uniform(-0.3, 0.3)
        # circle center ahead of the boid
        circle_center = self.vel.copy()
        if circle_center.length_sq() > 1e-10:
            circle_center.normalize()
            circle_center.scale(wander_distance)
        # displacement offset on the circle
        offset = Vector2(
            math.cos(self._wander_angle) * wander_radius,
            math.sin(self._wander_angle) * wander_radius,
        )
        desired = circle_center + offset
        if desired.length_sq() < 1e-10:
            return Vector2(0.0, 0.0)
        desired.set_length(self.max_speed)
        steer = desired - self.vel
        steer.limit(self.max_force * strength)
        return steer

    # ------------------------------------------------------------------ #
    #  Integration
    # ------------------------------------------------------------------ #
    def apply_force(self, force: Vector2) -> None:
        """Accumulate a steering force (F = ma, mass = 1)."""
        self.acc.add(force)

    def update(self, dt: float = 1.0) -> None:
        """Integrate acceleration -> velocity -> position (Euler).

        Records trail point before integration so the trail reflects
        the position history.
        """
        if self.trail is not None:
            self.trail.append((self.pos.x, self.pos.y))
        self.vel.add(self.acc)
        self.vel.limit(self.max_speed)
        self.pos.x += self.vel.x * dt
        self.pos.y += self.vel.y * dt
        self.acc.x = 0.0
        self.acc.y = 0.0

    # ------------------------------------------------------------------ #
    #  Serialization
    # ------------------------------------------------------------------ #
    def snapshot(self) -> BoidState:
        """Capture current state as a serializable BoidState."""
        return BoidState(
            id=self.id,
            x=self.pos.x, y=self.pos.y,
            vx=self.vel.x, vy=self.vel.y,
            max_speed=self.max_speed,
            max_force=self.max_force,
            radius=self.radius,
            kind=self.kind,
            species=self.species,
            path_index=self.path_index,
        )

    @classmethod
    def restore(cls, state: BoidState, trail_length: int = 0) -> "Boid":
        """Reconstruct a Boid from a BoidState snapshot."""
        # Use the state's id rather than auto-incrementing
        b = cls.__new__(cls)
        b.id = state.id
        b.pos = Vector2(state.x, state.y)
        b.vel = Vector2(state.vx, state.vy)
        b.acc = Vector2(0.0, 0.0)
        b.max_speed = state.max_speed
        b.max_force = state.max_force
        b.radius = state.radius
        b.kind = state.kind
        b.species = getattr(state, "species", 0)
        b.trail = deque(maxlen=trail_length) if trail_length > 0 else None
        b._wander_angle = random.uniform(0, math.tau)
        b.path = None
        b.path_index = getattr(state, "path_index", 0)
        # Ensure _next_id stays ahead of restored ids
        if state.id >= Boid._next_id:
            Boid._next_id = state.id + 1
        return b

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
            "species": self.species,
            "path_index": self.path_index,
        }