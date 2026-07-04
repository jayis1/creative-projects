"""Force fields: global forces applied to all (or filtered) dynamic bodies.

A :class:`ForceField` is called once per step with each dynamic body; it can
add a force or impulse based on the body's position, velocity, or other state.
This is how wind, drag, buoyancy, gravity wells, or custom force functions are
implemented without modifying the core integrator.
"""

from __future__ import annotations

import math
from typing import Callable, List, Optional

from .body import RigidBody
from .vec2 import Vec2

__all__ = ["ForceField", "UniformField", "RadialField", "DragField", "BuoyancyField"]


class ForceField:
    """Base class — override :meth:`apply` to implement custom fields."""

    def apply(self, body: RigidBody, dt: float) -> None:
        raise NotImplementedError


class UniformField(ForceField):
    """A constant force per unit mass (like uniform gravity or wind)."""

    def __init__(self, acceleration: Vec2) -> None:
        self.acceleration = Vec2(acceleration.x, acceleration.y)

    def apply(self, body: RigidBody, dt: float) -> None:
        if not body.is_dynamic or body.sleeping:
            return
        body.apply_force(self.acceleration * body.mass)


class RadialField(ForceField):
    """A radial force field (gravity well or repeller).

    ``strength`` > 0 attracts, < 0 repels.  ``falloff`` controls the distance
    scaling: 2.0 = inverse-square, 1.0 = linear, 0.0 = constant.
    """

    def __init__(self, center: Vec2, strength: float, falloff: float = 2.0,
                 max_radius: float = math.inf, min_radius: float = 0.1) -> None:
        self.center = Vec2(center.x, center.y)
        self.strength = float(strength)
        self.falloff = float(falloff)
        self.max_radius = float(max_radius)
        self.min_radius = float(min_radius)

    def apply(self, body: RigidBody, dt: float) -> None:
        if not body.is_dynamic or body.sleeping:
            return
        d = self.center - body.position
        dist = d.length()
        if dist > self.max_radius or dist < self.min_radius:
            return
        if dist < 1e-9:
            return
        direction = d / dist
        # Force magnitude: strength / dist^falloff, scaled by body mass.
        magnitude = self.strength * body.mass / (dist ** self.falloff)
        body.apply_force(direction * magnitude)


class DragField(ForceField):
    """Quadratic drag: ``F = -k * |v| * v`` (proportional to velocity squared)."""

    def __init__(self, coefficient: float = 0.5) -> None:
        self.coefficient = max(0.0, float(coefficient))

    def apply(self, body: RigidBody, dt: float) -> None:
        if not body.is_dynamic or body.sleeping:
            return
        v = body.linear_velocity
        speed = v.length()
        if speed < 1e-9:
            return
        drag = v * (-self.coefficient * speed * body.mass)
        body.apply_force(drag)


class BuoyancyField(ForceField):
    """Buoyancy in a fluid of a given density, filling the half-space ``y <= level``.

    Approximates the submerged volume by checking the body's AABB depth below
    the fluid surface.  Not physically exact for tilted bodies but adequate for
    visual effect.
    """

    def __init__(self, fluid_level: float, fluid_density: float = 1.0,
                 gravity: Vec2 = Vec2(0.0, -9.81), drag: float = 0.3) -> None:
        self.fluid_level = float(fluid_level)
        self.fluid_density = float(fluid_density)
        self.gravity = gravity
        self.drag = float(drag)

    def apply(self, body: RigidBody, dt: float) -> None:
        if not body.is_dynamic or body.sleeping:
            return
        aabb = body.aabb
        if aabb is None or aabb.max.y <= self.fluid_level:
            return  # entirely above fluid
        # Submerged depth: fraction of AABB below the fluid level.
        submerged_top = min(aabb.max.y, self.fluid_level)
        submerged_depth = submerged_top - aabb.min.y
        total_height = aabb.height
        if total_height <= 0:
            return
        fraction = max(0.0, min(1.0, submerged_depth / total_height))
        # Approximate submerged volume via AABB area (rough but stable).
        submerged_area = aabb.width * submerged_depth
        buoyancy_force = self.fluid_density * submerged_area * (-self.gravity)
        body.apply_force(buoyancy_force)
        # Linear drag while submerged.
        if self.drag > 0 and fraction > 0:
            drag = body.linear_velocity * (-self.drag * fraction * body.mass)
            body.apply_force(drag)