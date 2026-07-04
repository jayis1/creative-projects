"""The physics world: ties bodies, broad phase, narrow phase, and solvers."""

from __future__ import annotations

import math
from typing import Callable, List, Optional

from .core.body import RigidBody
from .core.broadphase import BroadPhase
from .core.collision import Manifold, collide
from .core.fields import ForceField
from .core.vec2 import Vec2
from .joints.joints import Joint
from .solver.contact_solver import ContactSolver

__all__ = ["World"]


class World:
    """Container & orchestrator for a rigid-body simulation.

    Steps each frame:
      1. Integrate forces → velocities.
      2. Broad phase → candidate pairs.
      3. Narrow phase → manifolds.
      4. Solve joints (pre-solve then iterate).
      5. Solve contacts (velocity constraints, position correction).
      6. Integrate velocities → positions.
      7. Sleeping logic.
    """

    def __init__(
        self,
        gravity: Vec2 = Vec2(0.0, -9.81),
        velocity_iterations: int = 10,
        position_iterations: int = 5,
        joint_iterations: int = 5,
        allow_sleeping: bool = True,
    ) -> None:
        self.gravity = gravity
        self.velocity_iterations = velocity_iterations
        self.position_iterations = position_iterations
        self.joint_iterations = joint_iterations
        self.allow_sleeping = allow_sleeping
        self.bodies: List[RigidBody] = []
        self.joints: List[Joint] = []
        self.force_fields: List["ForceField"] = []
        self.broad_phase = BroadPhase()
        self.contact_solver = ContactSolver(iterations=velocity_iterations)
        # Callbacks.
        self.on_collision: Optional[Callable[[int, int, Manifold], None]] = None
        # Counters for diagnostics.
        self.step_count = 0
        self.contact_count = 0

    # ------------------------------------------------------------------ #
    # body / joint management
    # ------------------------------------------------------------------ #
    def add_body(self, body: RigidBody) -> int:
        idx = len(self.bodies)
        self.bodies.append(body)
        body.update_aabb()
        return idx

    def remove_body(self, index: int) -> None:
        if 0 <= index < len(self.bodies):
            self.bodies.pop(index)
            # Rebuild AABBs are stale but broad phase recomputes next step.

    def add_joint(self, joint: Joint) -> None:
        self.joints.append(joint)

    def add_force_field(self, field: ForceField) -> None:
        """Register a force field applied to all dynamic bodies each step."""
        self.force_fields.append(field)

    # ------------------------------------------------------------------ #
    # stepping
    # ------------------------------------------------------------------ #
    def step(self, dt: float) -> None:
        if dt <= 0.0:
            return
        # Wake bodies that have accumulated force or moved.
        for b in self.bodies:
            if (b.force.length_sq() > 0.0 or b.torque != 0.0) and b.sleeping:
                b.set_awake()

        # 0. Apply force fields (before integration).
        for field in self.force_fields:
            for b in self.bodies:
                if b.is_dynamic and not b.sleeping:
                    field.apply(b, dt)

        # 1. Integrate forces into velocities (semi-implicit Euler).
        for b in self.bodies:
            if b.sleeping or b.is_static:
                continue
            b.integrate(self.gravity, dt)
            b.clear_forces()

        # 2. Broad phase.
        for b in self.bodies:
            b.update_aabb()
        pairs = self.broad_phase.update(self.bodies)
        # Debug: uncomment to trace broad-phase pairs.
        # if pairs:
        #     print(f"  broadphase pairs: {pairs}")

        # 3. Narrow phase → manifolds (with collision filtering).
        manifolds: List[tuple[int, int, Manifold]] = []
        for ia, ib in pairs:
            a = self.bodies[ia]
            b = self.bodies[ib]
            # Skip pairs where both are immovable.
            if a.inv_mass == 0.0 and b.inv_mass == 0.0:
                continue
            # Collision filter: both directions must match.
            if not ((a.collision_mask & b.collision_layer) and (b.collision_mask & a.collision_layer)):
                continue
            m = collide(a.shape, b.shape, a.position, a.angle, b.position, b.angle)
            if m is not None:
                m.body_a = ia
                m.body_b = ib
                manifolds.append((ia, ib, m))
                if self.on_collision is not None:
                    self.on_collision(ia, ib, m)
        self.contact_count = sum(m.contact_count for _, _, m in manifolds)

        # 4. Build contact solver constraints and solve velocity.
        self.contact_solver.clear()
        for ia, ib, m in manifolds:
            a = self.bodies[ia]
            b = self.bodies[ib]
            # Sensors generate callbacks but no solver constraints.
            if a.is_sensor or b.is_sensor:
                continue
            self.contact_solver.add_manifold(m, a, b, dt)
        self.contact_solver.dt = dt
        self.contact_solver.solve()

        # 5. Solve joints.
        for joint in self.joints:
            joint.pre_solve(dt)
        for _ in range(self.joint_iterations):
            for joint in self.joints:
                joint.solve()

        # 6. Position correction (Baumgarte already applied in solve; this
        #    is the extra position-solve pass to reduce residual overlap).
        for _ in range(self.position_iterations):
            self.contact_solver.solve_position()

        # 7. Sleeping logic.
        if self.allow_sleeping:
            self._update_sleeping(dt)

        self.step_count += 1

    def _update_sleeping(self, dt: float) -> None:
        for b in self.bodies:
            if not b.is_dynamic or not b.allow_sleep or b.sleeping:
                continue
            vel_sq = b.linear_velocity.length_sq() + b.angular_velocity * b.angular_velocity
            if vel_sq < b._sleep_threshold * b._sleep_threshold:
                b.sleep_time += dt
                if b.sleep_time >= b._sleep_time_limit:
                    b.set_sleeping()
            else:
                b.sleep_time = 0.0

    # ------------------------------------------------------------------ #
    # queries
    # ------------------------------------------------------------------ #
    def bodies_at(self, point: Vec2) -> List[int]:
        """Return indices of bodies whose shape contains *point*."""
        from .core.collision import point_in_polygon
        from .core.shapes import Circle, Polygon
        out = []
        for i, b in enumerate(self.bodies):
            if b.aabb and not b.aabb.contains(point):
                continue
            if isinstance(b.shape, Circle):
                center = b.shape.offset.rotate(b.angle) + b.position
                if (point - center).length_sq() <= b.shape.radius * b.shape.radius:
                    out.append(i)
            elif isinstance(b.shape, Polygon):
                if point_in_polygon(point, b.shape, b.position, b.angle):
                    out.append(i)
        return out

    def find_body(self, tag: str) -> Optional[RigidBody]:
        """Find a body by its ``user_data`` tag (if set to a string)."""
        for b in self.bodies:
            if isinstance(b.user_data, str) and b.user_data == tag:
                return b
        return None