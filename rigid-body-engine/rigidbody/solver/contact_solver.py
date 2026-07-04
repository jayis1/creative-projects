"""Sequential-impulse contact solver with Baumgarte position correction.

The solver converts each contact manifold into one or two equality
constraints (normal + tangent) and iterates, applying impulses to drive the
relative velocity at each contact toward the constraint target.  Friction is
modelled as Coulomb friction on the tangent direction, clamped by the
accumulated normal impulse.

This is the same algorithm used by Box2D-lite / Erin Catto's "Iterative
Dynamics with GJK" talks, scaled down to 2D and expressed in plain Python.
"""

from __future__ import annotations

import math
from typing import List

from ..core.body import RigidBody
from ..core.collision import ContactPoint, Manifold
from ..core.vec2 import Vec2

__all__ = ["ContactSolver", "ContactConstraint", "solve_contact_manifold"]

# Baumgarte stabilization: fraction of the penetration error to correct per
# step.  Too large → jitter; too small → bodies sink into each other.
_BAUMGARTE = 0.3
# Slop: don't bother correcting tiny penetrations (avoids jitter at rest).
_LINEAR_SLOP = 0.005


class ContactConstraint:
    """A single contact point turned into solver state.

    Precomputes the effective mass along normal & tangent so the inner solve
    loop only needs a couple of multiplies and an add.
    """

    __slots__ = (
        "point", "normal", "tangent", "rA", "rB",
        "normal_mass", "tangent_mass", "normal_impulse", "tangent_impulse",
        "bias", "body_a", "body_b", "_target_vn",
        "local_a", "local_b",
    )

    def __init__(self, contact: ContactPoint, body_a: RigidBody, body_b: RigidBody) -> None:
        self.point = contact.point
        self.normal = contact.normal
        self.tangent = Vec2(-self.normal.y, self.normal.x)  # perpendicular
        # Store contact offsets in *local* body space so we can recompute the
        # world contact point after the bodies move during position solving.
        self.local_a = body_a.to_local(contact.point)
        self.local_b = body_b.to_local(contact.point)
        self.rA = contact.point - body_a.position
        self.rB = contact.point - body_b.position
        self.body_a = body_a
        self.body_b = body_b

        self.normal_impulse = 0.0
        self.tangent_impulse = 0.0

        # Effective inverse mass along the normal.
        rnA = self.rA.cross(self.normal)
        rnB = self.rB.cross(self.normal)
        kN = (
            body_a.inv_mass
            + body_b.inv_mass
            + (rnA * rnA) * body_a.inv_inertia
            + (rnB * rnB) * body_b.inv_inertia
        )
        self.normal_mass = 1.0 / kN if kN > 0.0 else 0.0

        rtA = self.rA.cross(self.tangent)
        rtB = self.rB.cross(self.tangent)
        kT = (
            body_a.inv_mass
            + body_b.inv_mass
            + (rtA * rtA) * body_a.inv_inertia
            + (rtB * rtB) * body_b.inv_inertia
        )
        self.tangent_mass = 1.0 / kT if kT > 0.0 else 0.0

        # Baumgarte bias: push B away from A along the normal to remove
        # penetration beyond slop.  Stored as a *velocity* target (positive =
        # push apart).  The solver adds this to the restitution target.
        self.bias = _BAUMGARTE * max(0.0, contact.penetration - _LINEAR_SLOP)
        self._target_vn = 0.0


class ContactSolver:
    """Runs iterative impulses over a batch of contact constraints."""

    def __init__(self, iterations: int = 10, friction_iterations: int = 4) -> None:
        self.iterations = iterations
        self.friction_iterations = friction_iterations
        self.constraints: List[ContactConstraint] = []
        self.friction = 0.0
        self.restitution = 0.0
        self.dt = 0.0

    def add_manifold(self, manifold: Manifold, body_a: RigidBody, body_b: RigidBody, dt: float) -> None:
        self.dt = dt
        self.friction = math.sqrt(body_a.friction * body_b.friction)
        self.restitution = min(body_a.restitution, body_b.restitution)
        for cp in manifold.points:
            self.constraints.append(ContactConstraint(cp, body_a, body_b))

    def clear(self) -> None:
        self.constraints.clear()

    def solve(self) -> None:
        # Pre-step: compute restitution target and Baumgarte bias velocity.
        for c in self.constraints:
            va = c.body_a.velocity_at_point(c.point)
            vb = c.body_b.velocity_at_point(c.point)
            rel = vb - va
            vn = rel.dot(c.normal)
            # Baumgarte bias velocity (positive = push B away from A).
            bias_v = c.bias / self.dt if self.dt > 0.0 else 0.0
            # Restitution only applies on approach (vn < 0): bounce velocity.
            restitution_v = -vn * self.restitution if vn < 0.0 else 0.0
            # Total target relative normal velocity (separation + bounce).
            c._target_vn = bias_v + restitution_v  # noqa: SLF001
            # Warm start: re-apply accumulated impulse.
            P = c.normal * c.normal_impulse + c.tangent * c.tangent_impulse
            c.body_a.apply_impulse(-P, c.point)
            c.body_b.apply_impulse(P, c.point)

        # Iterate.
        for _ in range(self.iterations):
            self._solve_friction()
            self._solve_normal()

    def _solve_normal(self) -> None:
        for c in self.constraints:
            va = c.body_a.velocity_at_point(c.point)
            vb = c.body_b.velocity_at_point(c.point)
            rel = vb - va
            vn = rel.dot(c.normal)
            dp = (c._target_vn - vn) * c.normal_mass  # noqa: SLF001
            # Clamp accumulated impulse ≥ 0 (contact can only push, not pull).
            new_impulse = max(0.0, c.normal_impulse + dp)
            real_dp = new_impulse - c.normal_impulse
            c.normal_impulse = new_impulse
            P = c.normal * real_dp
            c.body_a.apply_impulse(-P, c.point)
            c.body_b.apply_impulse(P, c.point)

    def _solve_friction(self) -> None:
        for c in self.constraints:
            va = c.body_a.velocity_at_point(c.point)
            vb = c.body_b.velocity_at_point(c.point)
            rel = vb - va
            vt = rel.dot(c.tangent)
            dp = -vt * c.tangent_mass
            # Coulomb friction clamp: |tangent impulse| ≤ friction * normal impulse.
            max_fr = c.normal_impulse * self.friction
            new_impulse = c.tangent_impulse + dp
            new_impulse = max(-max_fr, min(max_fr, new_impulse))
            real_dp = new_impulse - c.tangent_impulse
            c.tangent_impulse = new_impulse
            P = c.tangent * real_dp
            c.body_a.apply_impulse(-P, c.point)
            c.body_b.apply_impulse(P, c.point)

    def solve_position(self) -> None:
        """Separate overlapping bodies using a Baumgarte position correction.

        Recomputes the world contact points from the stored local offsets so
        that rotations during the velocity solve are correctly accounted for.
        """
        for c in self.constraints:
            pa = c.body_a.to_world(c.local_a)
            pb = c.body_b.to_world(c.local_b)
            d = pb - pa
            # Penetration = how far B has moved along the normal past A (positive
            # means overlap because normal points A→B and contact pushes apart).
            penetration = -d.dot(c.normal)
            correction_mag = max(0.0, penetration - _LINEAR_SLOP) * _BAUMGARTE
            if correction_mag <= 0.0:
                continue
            correction = c.normal * correction_mag
            total_inv = c.body_a.inv_mass + c.body_b.inv_mass
            if total_inv <= 0.0:
                continue
            scale = 1.0 / total_inv
            c.body_a.position = c.body_a.position - correction * (c.body_a.inv_mass * scale)
            c.body_b.position = c.body_b.position + correction * (c.body_b.inv_mass * scale)