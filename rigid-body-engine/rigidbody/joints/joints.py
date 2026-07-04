"""Constraints: distance, revolute (pin), and weld joints.

A *joint* is an algebraic equality constraint between two bodies.  Each joint
type implements two methods the world calls every step:

* :meth:`pre_solve` — precompute effective-mass terms and the current
  constraint error (the "bias").
* :meth:`solve` — apply corrective impulses to drive the error to zero.

The math follows Catto's "Constraints" GDC talks adapted to 2D.
"""

from __future__ import annotations

import math
from typing import Optional

from ..core.body import RigidBody
from ..core.mat22 import solve_2x2
from ..core.vec2 import Vec2

__all__ = ["Joint", "DistanceJoint", "RevoluteJoint", "WeldJoint", "MouseJoint"]


class Joint:
    """Base class.  Subclasses implement :meth:`pre_solve` and :meth:`solve`."""

    def __init__(self, body_a: RigidBody, body_b: RigidBody) -> None:
        self.body_a = body_a
        self.body_b = body_b

    def pre_solve(self, dt: float) -> None:
        raise NotImplementedError

    def solve(self) -> None:
        raise NotImplementedError


class DistanceJoint(Joint):
    """Keeps two anchor points a fixed distance apart."""

    def __init__(self, body_a: RigidBody, local_a: Vec2, body_b: RigidBody, local_b: Vec2, length: Optional[float] = None, stiffness: float = 1.0) -> None:
        super().__init__(body_a, body_b)
        self.local_a = local_a
        self.local_b = local_b
        if length is None:
            wa = body_a.to_world(local_a)
            wb = body_b.to_world(local_b)
            length = (wb - wa).length()
        self.length = float(length)
        self.stiffness = max(0.0, min(1.0, stiffness))
        self.impulse = 0.0
        self.bias = 0.0
        self.mass = 0.0
        self.normal = Vec2(0.0, 1.0)
        self.rA = Vec2.zero()
        self.rB = Vec2.zero()

    def _anchors(self):
        self.rA = self.body_a.to_world(self.local_a) - self.body_a.position
        self.rB = self.body_b.to_world(self.local_b) - self.body_b.position
        d = (self.body_b.position + self.rB) - (self.body_a.position + self.rA)
        dist = d.length()
        if dist > 1e-9:
            self.normal = d / dist
        else:
            self.normal = Vec2(0.0, 1.0)
        return dist

    def pre_solve(self, dt: float) -> None:
        dist = self._anchors()
        # Effective mass along the normal.
        rnA = self.rA.cross(self.normal)
        rnB = self.rB.cross(self.normal)
        k = (
            self.body_a.inv_mass
            + self.body_b.inv_mass
            + rnA * rnA * self.body_a.inv_inertia
            + rnB * rnB * self.body_b.inv_inertia
        )
        self.mass = 1.0 / k if k > 0.0 else 0.0
        # Baumgarte bias to correct length error.
        C = dist - self.length
        self.bias = -0.2 * C / dt if dt > 0.0 else 0.0
        # Warm start.
        P = self.normal * self.impulse
        self.body_a.apply_impulse(-P, self.body_a.position + self.rA)
        self.body_b.apply_impulse(P, self.body_b.position + self.rB)

    def solve(self) -> None:
        va = self.body_a.velocity_at_point(self.body_a.position + self.rA)
        vb = self.body_b.velocity_at_point(self.body_b.position + self.rB)
        rel = vb - va
        vn = rel.dot(self.normal)
        dp = (-vn + self.bias) * self.mass
        # Clamp: rope can pull but never push beyond stiffness.
        old = self.impulse
        self.impulse = max(0.0, self.impulse + dp * self.stiffness)
        real_dp = self.impulse - old
        P = self.normal * real_dp
        self.body_a.apply_impulse(-P, self.body_a.position + self.rA)
        self.body_b.apply_impulse(P, self.body_b.position + self.rB)


class RevoluteJoint(Joint):
    """Pin joint: two anchor points must coincide.

    This is a 2-DOF constraint (x and y), solved with a 2x2 effective-mass
    matrix.  Optionally a motor can drive the relative angle toward a target.
    """

    def __init__(self, body_a: RigidBody, local_a: Vec2, body_b: RigidBody, local_b: Vec2,
                 motor_enabled: bool = False, motor_speed: float = 0.0, max_motor_force: float = 0.0) -> None:
        super().__init__(body_a, body_b)
        self.local_a = local_a
        self.local_b = local_b
        self.motor_enabled = motor_enabled
        self.motor_speed = float(motor_speed)
        self.max_motor_force = float(max_motor_force)
        self.motor_impulse = 0.0
        # Accumulated 2D linear impulse (x, y).
        self.impulse = Vec2.zero()
        self.mass_a = 0.0
        self.mass_b = 0.0
        self.mass_c = 0.0
        self.mass_d = 0.0
        self.bias = Vec2.zero()
        self.rA = Vec2.zero()
        self.rB = Vec2.zero()
        self._motor_mass = 0.0

    def pre_solve(self, dt: float) -> None:
        self.rA = self.body_a.to_world(self.local_a) - self.body_a.position
        self.rB = self.body_b.to_world(self.local_b) - self.body_b.position
        # 2x2 effective mass matrix K for the linear constraint.
        mA = self.body_a.inv_mass
        mB = self.body_b.inv_mass
        iA = self.body_a.inv_inertia
        iB = self.body_b.inv_inertia
        k11 = mA + mB + self.rA.y * self.rA.y * iA + self.rB.y * self.rB.y * iB
        k12 = -self.rA.x * self.rA.y * iA - self.rB.x * self.rB.y * iB
        k22 = mA + mB + self.rA.x * self.rA.x * iA + self.rB.x * self.rB.x * iB
        self.mass_a = k11
        self.mass_b = k12
        self.mass_c = k12
        self.mass_d = k22
        # Position error (bias).
        pa = self.body_a.position + self.rA
        pb = self.body_b.position + self.rB
        C = pb - pa
        self.bias = C * (-0.2 / dt) if dt > 0.0 else Vec2.zero()
        # Motor mass = I_a^-1 + I_b^-1.
        self._motor_mass = iA + iB
        # Warm start.
        P = self.impulse
        self.body_a.apply_impulse(-P, self.body_a.position + self.rA)
        self.body_b.apply_impulse(P, self.body_b.position + self.rB)
        if self.motor_enabled and self._motor_mass > 0.0:
            self.body_a.angular_velocity -= self.motor_impulse * self.body_a.inv_inertia
            self.body_b.angular_velocity += self.motor_impulse * self.body_b.inv_inertia

    def solve(self) -> None:
        # Linear constraint.
        va = self.body_a.velocity_at_point(self.body_a.position + self.rA)
        vb = self.body_b.velocity_at_point(self.body_b.position + self.rB)
        rel = vb - va
        rhs = -rel + self.bias
        try:
            ix, iy = solve_2x2(
                self.mass_a, self.mass_b,
                self.mass_c, self.mass_d,
                rhs.x, rhs.y,
            )
        except ZeroDivisionError:
            ix = iy = 0.0
        impulse = Vec2(ix, iy)
        self.impulse = self.impulse + impulse
        self.body_a.apply_impulse(-impulse, self.body_a.position + self.rA)
        self.body_b.apply_impulse(impulse, self.body_b.position + self.rB)

        # Motor constraint.
        if self.motor_enabled and self._motor_mass > 0.0:
            rel_w = self.body_b.angular_velocity - self.body_a.angular_velocity
            motor_dp = (self.motor_speed - rel_w) * self._motor_mass
            old = self.motor_impulse
            self.motor_impulse = max(-self.max_motor_force, min(self.max_motor_force, self.motor_impulse + motor_dp))
            real = self.motor_impulse - old
            self.body_a.angular_velocity -= real * self.body_a.inv_inertia
            self.body_b.angular_velocity += real * self.body_b.inv_inertia


class WeldJoint(Joint):
    """Welds two bodies together: anchors coincide AND relative angle is fixed."""

    def __init__(self, body_a: RigidBody, local_a: Vec2, body_b: RigidBody, local_b: Vec2,
                 frequency: float = 8.0, damping: float = 0.5) -> None:
        super().__init__(body_a, body_b)
        self.local_a = local_a
        self.local_b = local_b
        self.reference_angle = body_b.angle - body_a.angle
        self.frequency = frequency
        self.damping = damping
        self.impulse = Vec2.zero()
        self.angular_impulse = 0.0
        self.rA = Vec2.zero()
        self.rB = Vec2.zero()
        self.mass_a = self.mass_b = self.mass_c = self.mass_d = 0.0
        self.angular_mass = 0.0

    def pre_solve(self, dt: float) -> None:
        self.rA = self.body_a.to_world(self.local_a) - self.body_a.position
        self.rB = self.body_b.to_world(self.local_b) - self.body_b.position
        mA = self.body_a.inv_mass
        mB = self.body_b.inv_mass
        iA = self.body_a.inv_inertia
        iB = self.body_b.inv_inertia
        k11 = mA + mB + self.rA.y * self.rA.y * iA + self.rB.y * self.rB.y * iB
        k12 = -self.rA.x * self.rA.y * iA - self.rB.x * self.rB.y * iB
        k22 = mA + mB + self.rA.x * self.rA.x * iA + self.rB.x * self.rB.x * iB
        self.mass_a = k11
        self.mass_b = k12
        self.mass_c = k12
        self.mass_d = k22
        self.angular_mass = iA + iB
        self.angular_mass = 1.0 / self.angular_mass if self.angular_mass > 0.0 else 0.0
        # Warm start.
        P = self.impulse
        self.body_a.apply_impulse(-P, self.body_a.position + self.rA)
        self.body_b.apply_impulse(P, self.body_b.position + self.rB)
        self.body_a.angular_velocity -= self.angular_impulse * self.body_a.inv_inertia
        self.body_b.angular_velocity += self.angular_impulse * self.body_b.inv_inertia

    def solve(self) -> None:
        # Linear.
        va = self.body_a.velocity_at_point(self.body_a.position + self.rA)
        vb = self.body_b.velocity_at_point(self.body_b.position + self.rB)
        rel = vb - va
        try:
            ix, iy = solve_2x2(
                self.mass_a, self.mass_b,
                self.mass_c, self.mass_d,
                -rel.x, -rel.y,
            )
        except ZeroDivisionError:
            ix = iy = 0.0
        impulse = Vec2(ix, iy)
        self.impulse = self.impulse + impulse
        self.body_a.apply_impulse(-impulse, self.body_a.position + self.rA)
        self.body_b.apply_impulse(impulse, self.body_b.position + self.rB)
        # Angular.
        rel_w = self.body_b.angular_velocity - self.body_a.angular_velocity
        C = (self.body_b.angle - self.body_a.angle) - self.reference_angle
        angular_dp = (-rel_w - C * 0.2) * self.angular_mass
        self.angular_impulse += angular_dp
        self.body_a.angular_velocity -= angular_dp * self.body_a.inv_inertia
        self.body_b.angular_velocity += angular_dp * self.body_b.inv_inertia


class MouseJoint(Joint):
    """A soft spring pulling ``body_a`` toward a target world point.

    ``body_b`` is unused (kept for API symmetry); the "other side" is the
    immovable mouse cursor.  Useful for interactive dragging in a demo.
    """

    def __init__(self, body: RigidBody, target: Vec2, local_anchor: Optional[Vec2] = None,
                 frequency: float = 8.0, damping: float = 0.5, max_force: float = 1000.0) -> None:
        super().__init__(body, body)
        self.body = body
        self.target = Vec2(target.x, target.y)
        self.frequency = frequency
        self.damping = damping
        self.max_force = max_force
        if local_anchor is None:
            self.local_anchor = body.to_local(target)
        else:
            self.local_anchor = local_anchor
        self.impulse = Vec2.zero()
        self.rA = Vec2.zero()
        self.mass_a = self.mass_b = self.mass_c = self.mass_d = 0.0
        self.bias = Vec2.zero()
        self.gamma = 0.0

    def set_target(self, target: Vec2) -> None:
        self.target = Vec2(target.x, target.y)

    def pre_solve(self, dt: float) -> None:
        self.rA = self.body.to_world(self.local_anchor) - self.body.position
        mA = self.body.inv_mass
        iA = self.body.inv_inertia
        k11 = mA + self.rA.y * self.rA.y * iA
        k12 = -self.rA.x * self.rA.y * iA
        k22 = mA + self.rA.x * self.rA.x * iA
        # Soft constraint (frequency / damping ratio).
        omega = 2.0 * math.pi * self.frequency
        c = 2.0 * self.body.mass * omega * self.damping
        k = self.body.mass * omega * omega
        if dt > 0.0:
            self.gamma = 1.0 / (dt * (c + dt * k))
        else:
            self.gamma = 0.0
        inv_dt = 1.0 / dt if dt > 0.0 else 0.0
        k11 += self.gamma
        k22 += self.gamma
        self.mass_a = k11
        self.mass_b = k12
        self.mass_c = k12
        self.mass_d = k22
        pa = self.body.position + self.rA
        C = self.target - pa
        self.bias = C * (k * dt) * inv_dt
        # Warm start.
        P = self.impulse
        self.body.apply_impulse(P, self.body.position + self.rA)

    def solve(self) -> None:
        v = self.body.velocity_at_point(self.body.position + self.rA)
        rhs_x = -v.x + self.bias.x - self.impulse.x * self.gamma
        rhs_y = -v.y + self.bias.y - self.impulse.y * self.gamma
        try:
            ix, iy = solve_2x2(
                self.mass_a, self.mass_b,
                self.mass_c, self.mass_d,
                rhs_x, rhs_y,
            )
        except ZeroDivisionError:
            ix = iy = 0.0
        new_impulse = self.impulse + Vec2(ix, iy)
        # Clamp total force.
        mag = new_impulse.length()
        max_step = self.max_force
        if mag > max_step:
            new_impulse = new_impulse * (max_step / mag)
        real = new_impulse - self.impulse
        self.impulse = new_impulse
        self.body.apply_impulse(real, self.body.position + self.rA)