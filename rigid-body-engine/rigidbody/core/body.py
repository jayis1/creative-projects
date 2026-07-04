"""Rigid body: a shape plus dynamic state (position, velocity, forces)."""

from __future__ import annotations

import math
from typing import Optional

from .shapes import AABB, Shape
from .vec2 import Vec2

__all__ = ["RigidBody"]


class RigidBody:
    """A 2D rigid body.

    A body is either *dynamic* (affected by forces and collisions), *static*
    (infinite mass, immovable), or *kinematic* (infinite mass but moves with
    a set velocity; useful for moving platforms).

    Public attributes are intentionally plain so the integrator and solver can
    read/write them directly without going through accessors.
    """

    DYNAMIC = "dynamic"
    STATIC = "static"
    KINEMATIC = "kinematic"

    def __init__(
        self,
        shape: Shape,
        position: Vec2,
        angle: float = 0.0,
        body_type: str = DYNAMIC,
        density: float = 1.0,
        restitution: float = 0.2,
        friction: float = 0.3,
        linear_damping: float = 0.01,
        angular_damping: float = 0.01,
        gravity_scale: float = 1.0,
    ) -> None:
        if density <= 0.0 and body_type == self.DYNAMIC:
            raise ValueError("dynamic bodies need positive density")
        self.shape = shape
        self.position = Vec2(position.x, position.y)
        self.angle = float(angle)
        self.body_type = body_type

        self.linear_velocity = Vec2.zero()
        self.angular_velocity = 0.0
        self.force = Vec2.zero()
        self.torque = 0.0

        if body_type == self.DYNAMIC:
            mass, inertia = shape.compute_mass(density)
            self.mass = mass
            self.inv_mass = 1.0 / mass if mass > 0.0 else 0.0
            self.inertia = inertia
            self.inv_inertia = 1.0 / inertia if inertia > 0.0 else 0.0
        else:
            self.mass = 0.0
            self.inv_mass = 0.0
            self.inertia = 0.0
            self.inv_inertia = 0.0

        self.restitution = max(0.0, min(1.0, float(restitution)))
        self.friction = max(0.0, float(friction))
        self.linear_damping = float(linear_damping)
        self.angular_damping = float(angular_damping)
        self.gravity_scale = float(gravity_scale)

        # Sleeping bookkeeping — bodies at rest can skip integration.
        self.sleeping = False
        self.sleep_time = 0.0
        self._sleep_threshold = 0.2
        self._sleep_time_limit = 0.6
        self.allow_sleep = True

        # Optional user data / tag for external bookkeeping.
        self.user_data: object = None
        # Collision filtering: a body only collides with another if
        # ``(a.collision_mask & b.collision_layer) != 0`` **and**
        # ``(b.collision_mask & a.collision_layer) != 0``.
        # Defaults: layer 1, mask all-bits → collide with everything.
        self.collision_layer: int = 0x0001
        self.collision_mask: int = 0xFFFF
        # If True, this body never generates collision responses (but still
        # triggers the on_collision callback).  Useful for sensors/triggers.
        self.is_sensor: bool = False

        # Cached world-space AABB, recomputed each broad phase.
        self.aabb: Optional[AABB] = None

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #
    @property
    def is_static(self) -> bool:
        return self.body_type == self.STATIC

    @property
    def is_dynamic(self) -> bool:
        return self.body_type == self.DYNAMIC

    @property
    def is_kinematic(self) -> bool:
        return self.body_type == self.KINEMATIC

    def world_centroid(self) -> Vec2:
        """World-space centre of mass (the body's position)."""
        return self.position

    def to_world(self, local_point: Vec2) -> Vec2:
        """Transform a body-local point into world space."""
        c, s = math.cos(self.angle), math.sin(self.angle)
        wx = local_point.x * c - local_point.y * s + self.position.x
        wy = local_point.x * s + local_point.y * c + self.position.y
        return Vec2(wx, wy)

    def to_local(self, world_point: Vec2) -> Vec2:
        """Transform a world-space point into body-local space."""
        c, s = math.cos(self.angle), math.sin(self.angle)
        dx = world_point.x - self.position.x
        dy = world_point.y - self.position.y
        return Vec2(dx * c + dy * s, -dx * s + dy * c)

    def velocity_at_point(self, world_point: Vec2) -> Vec2:
        """Velocity of the body at *world_point* (linear + rotational)."""
        r = world_point - self.position
        return self.linear_velocity + Vec2(-r.y, r.x) * self.angular_velocity

    # ------------------------------------------------------------------ #
    # force / impulse application
    # ------------------------------------------------------------------ #
    def apply_force(self, force: Vec2, point: Vec2 | None = None) -> None:
        """Accumulate *force*; if *point* is given apply it as a torque too."""
        if self.is_static or self.sleeping:
            return
        self.force = self.force + force
        if point is not None:
            r = point - self.position
            self.torque += r.cross(force)

    def apply_impulse(self, impulse: Vec2, point: Vec2 | None = None) -> None:
        """Instantaneously change momentum.

        Unlike :meth:`apply_force` this does **not** accumulate — it directly
        alters velocity.  Used by the contact/joint solvers.
        """
        if self.is_static or self.sleeping:
            return
        self.linear_velocity = self.linear_velocity + impulse * self.inv_mass
        if point is not None:
            r = point - self.position
            self.angular_velocity += r.cross(impulse) * self.inv_inertia

    def apply_torque(self, torque: float) -> None:
        if self.is_static or self.sleeping:
            return
        self.torque += float(torque)

    def apply_angular_impulse(self, impulse: float) -> None:
        if self.is_static or self.sleeping:
            return
        self.angular_velocity += impulse * self.inv_inertia

    def apply_linear_impulse(self, impulse: Vec2) -> None:
        if self.is_static or self.sleeping:
            return
        self.linear_velocity = self.linear_velocity + impulse * self.inv_mass

    def set_awake(self) -> None:
        self.sleeping = False
        self.sleep_time = 0.0

    def set_sleeping(self) -> None:
        if not self.allow_sleep:
            return
        self.sleeping = True
        self.linear_velocity = Vec2.zero()
        self.angular_velocity = 0.0
        self.force = Vec2.zero()
        self.torque = 0.0

    def clear_forces(self) -> None:
        self.force = Vec2.zero()
        self.torque = 0.0

    # ------------------------------------------------------------------ #
    # integration (called by the World each step)
    # ------------------------------------------------------------------ #
    def integrate(self, gravity: Vec2, dt: float) -> None:
        """Semi-implicit Euler integration of position and angle."""
        if not self.is_dynamic:
            # Kinematic bodies move with their set velocity only.
            if self.is_kinematic:
                self.position = self.position + self.linear_velocity * dt
                self.angle += self.angular_velocity * dt
            return

        # Acceleration = force/m + gravity (scaled).
        a = self.force * self.inv_mass + gravity * self.gravity_scale
        self.linear_velocity = self.linear_velocity + a * dt
        # Angular integration.
        alpha = self.torque * self.inv_inertia
        self.angular_velocity += alpha * dt

        # Damping — exponential decay, frame-rate independent.
        lin_damp = max(0.0, 1.0 - self.linear_damping * dt)
        ang_damp = max(0.0, 1.0 - self.angular_damping * dt)
        self.linear_velocity = self.linear_velocity * lin_damp
        self.angular_velocity *= ang_damp

        # Position integration (semi-implicit: velocity already updated).
        self.position = self.position + self.linear_velocity * dt
        self.angle += self.angular_velocity * dt

    def update_aabb(self) -> AABB:
        self.aabb = self.shape.compute_aabb(self.position, self.angle)
        return self.aabb

    def __repr__(self) -> str:
        return (
            f"RigidBody(type={self.body_type}, pos={self.position}, "
            f"angle={self.angle:.3f})"
        )