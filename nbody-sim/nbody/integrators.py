"""Integration schemes for N-body systems.

Provides multiple integrators beyond the original leapfrog:

- :class:`LeapfrogIntegrator` — kick–drift–kick (KDK) symplectic, O(dt²).
  The default and recommended integrator for most use cases.
- :class:`RK4Integrator` — classical 4th-order Runge–Kutta. Higher accuracy
  per step but **not** symplectic — energy drifts secularly. Best for
  short, high-accuracy runs.
- :class:`ForestRuthIntegrator` — 4th-order symplectic integrator (three
  leapfrog steps with special timestep coefficients). Keeps energy
  bounded *and* has O(dt⁴) local truncation error. The best long-run
  integrator for demanding orbits.

All integrators share the same interface:
- ``step(bodies, dt)`` — mutate bodies in place
- ``total_energy(bodies)`` — total mechanical energy
- ``total_momentum(bodies)`` — linear momentum vector
- ``center_of_mass(bodies)`` — center-of-mass position
"""

from __future__ import annotations

import copy
import math
from typing import Callable, List, Tuple

from .barnes_hut import BHTree
from .body import Body

# Type alias for the force evaluator function signature.
ForceFunc = Callable[[List[Body]], List[Tuple[float, float]]]


def _bh_force_evaluator(theta: float, softening: float, G: float) -> ForceFunc:
    """Return a force evaluator that builds a Barnes–Hut tree each call."""

    tree = BHTree(theta=theta, softening=softening, G=G)

    def evaluate(bodies: List[Body]) -> List[Tuple[float, float]]:
        point_masses = [(b.x, b.y, b.m) for b in bodies]
        tree.build(point_masses)
        return [tree.force_on(pm) for pm in point_masses]

    return evaluate


# ─── Leapfrog (KDK) ─────────────────────────────────────────────────

class LeapfrogIntegrator:
    """Kick–drift–kick leapfrog integrator (symplectic, O(dt²)).

    This is the standard choice for long-running gravity simulations
    because the energy error stays bounded over exponentially long times.

    Each step:

    .. code-block:: text

        v_{1/2} = v_0    + ½·a(x_0)·dt     # kick (half)
        x_1     = x_0    + v_{1/2}·dt      # drift (full)
        v_1     = v_{1/2} + ½·a(x_1)·dt    # kick (half)
    """

    def __init__(
        self,
        theta: float = 0.5,
        softening: float = 1.0,
        G: float = 1.0,
    ) -> None:
        self.theta = theta
        self.softening = softening
        self.G = G
        self._compute_accelerations = _bh_force_evaluator(theta, softening, G)

    def step(self, bodies: List[Body], dt: float) -> None:
        """Advance ``bodies`` by one KDK step of length ``dt``."""
        if dt == 0.0 or not bodies:
            return
        # Kick (half)
        accels = self._compute_accelerations(bodies)
        for b, (ax, ay) in zip(bodies, accels):
            b.vx += 0.5 * dt * ax
            b.vy += 0.5 * dt * ay
        # Drift (full)
        for b in bodies:
            b.x += dt * b.vx
            b.y += dt * b.vy
        # Kick (half) with refreshed accelerations
        accels = self._compute_accelerations(bodies)
        for b, (ax, ay) in zip(bodies, accels):
            b.vx += 0.5 * dt * ax
            b.vy += 0.5 * dt * ay

    def total_energy(self, bodies: List[Body]) -> float:
        """Total mechanical energy (kinetic + softened potential)."""
        ke = 0.0
        for b in bodies:
            ke += 0.5 * b.m * (b.vx * b.vx + b.vy * b.vy)
        pe = 0.0
        n = len(bodies)
        soft_sq = self.softening * self.softening
        for i in range(n):
            bi = bodies[i]
            for j in range(i + 1, n):
                bj = bodies[j]
                dx = bj.x - bi.x
                dy = bj.y - bi.y
                r = math.sqrt(dx * dx + dy * dy + soft_sq)
                pe -= self.G * bi.m * bj.m / r
        return ke + pe

    def total_momentum(self, bodies: List[Body]) -> Tuple[float, float]:
        px = sum(b.m * b.vx for b in bodies)
        py = sum(b.m * b.vy for b in bodies)
        return (px, py)

    def center_of_mass(self, bodies: List[Body]) -> Tuple[float, float]:
        m = sum(b.m for b in bodies)
        if m == 0.0:
            return (0.0, 0.0)
        cx = sum(b.m * b.x for b in bodies) / m
        cy = sum(b.m * b.y for b in bodies) / m
        return (cx, cy)


# ─── RK4 ─────────────────────────────────────────────────────────────

class RK4Integrator:
    """Classical 4th-order Runge–Kutta integrator.

    Higher per-step accuracy than leapfrog but **not symplectic** — energy
    drifts secularly. Best for short, high-accuracy runs where the
    integrator error needs to be very small.

    Each step:
        k1 = f(y0)
        k2 = f(y0 + dt/2 * k1)
        k3 = f(y0 + dt/2 * k2)
        k4 = f(y0 + dt * k3)
        y1 = y0 + dt/6 * (k1 + 2*k2 + 2*k3 + k4)
    """

    def __init__(
        self,
        theta: float = 0.5,
        softening: float = 1.0,
        G: float = 1.0,
    ) -> None:
        self.theta = theta
        self.softening = softening
        self.G = G
        self._compute_accelerations = _bh_force_evaluator(theta, softening, G)

    def _state_to_list(self, bodies: List[Body]):
        """Extract (x, y, vx, vy) arrays from bodies."""
        return [(b.x, b.y, b.vx, b.vy) for b in bodies]

    def _restore_state(self, bodies: List[Body], state) -> None:
        """Write (x, y, vx, vy) back into bodies."""
        for b, (x, y, vx, vy) in zip(bodies, state):
            b.x, b.y, b.vx, b.vy = x, y, vx, vy

    def step(self, bodies: List[Body], dt: float) -> None:
        """Advance ``bodies`` by one RK4 step of length ``dt``."""
        if dt == 0.0 or not bodies:
            return
        n = len(bodies)
        s0 = self._state_to_list(bodies)

        # k1 = f(s0)
        a1 = self._compute_accelerations(bodies)
        # k2 = f(s0 + dt/2 * k1)
        for b, (x, y, vx, vy), (ax, ay) in zip(bodies, s0, a1):
            b.x = x + 0.5 * dt * vx
            b.y = y + 0.5 * dt * vy
            b.vx = vx + 0.5 * dt * ax
            b.vy = vy + 0.5 * dt * ay
        a2 = self._compute_accelerations(bodies)
        # k3 = f(s0 + dt/2 * k2)
        for b, (x, y, vx, vy), (ax, ay) in zip(bodies, s0, a2):
            b.x = x + 0.5 * dt * vx
            b.y = y + 0.5 * dt * vy
            b.vx = vx + 0.5 * dt * ax
            b.vy = vy + 0.5 * dt * ay
        a3 = self._compute_accelerations(bodies)
        # k4 = f(s0 + dt * k3)
        for b, (x, y, vx, vy), (ax, ay) in zip(bodies, s0, a3):
            b.x = x + dt * vx
            b.y = y + dt * vy
            b.vx = vx + dt * ax
            b.vy = vy + dt * ay
        a4 = self._compute_accelerations(bodies)
        # Combine: y1 = s0 + dt/6 * (k1 + 2*k2 + 2*k3 + k4)
        for b, (x, y, vx, vy), (ax1, ay1), (ax2, ay2), (ax3, ay3), (ax4, ay4) in zip(
            bodies, s0, a1, a2, a3, a4
        ):
            b.x = x + dt / 6.0 * (vx + 2 * (vx + 0.5 * dt * ax1) + 2 * (vx + 0.5 * dt * ax2) + (vx + dt * ax3))
            b.y = y + dt / 6.0 * (vy + 2 * (vy + 0.5 * dt * ay1) + 2 * (vy + 0.5 * dt * ay2) + (vy + dt * ay3))
            b.vx = vx + dt / 6.0 * (ax1 + 2 * ax2 + 2 * ax3 + ax4)
            b.vy = vy + dt / 6.0 * (ay1 + 2 * ay2 + 2 * ay3 + ay4)

    def total_energy(self, bodies: List[Body]) -> float:
        """Total mechanical energy (kinetic + softened potential)."""
        ke = 0.0
        for b in bodies:
            ke += 0.5 * b.m * (b.vx * b.vx + b.vy * b.vy)
        pe = 0.0
        n = len(bodies)
        soft_sq = self.softening * self.softening
        for i in range(n):
            bi = bodies[i]
            for j in range(i + 1, n):
                bj = bodies[j]
                dx = bj.x - bi.x
                dy = bj.y - bi.y
                r = math.sqrt(dx * dx + dy * dy + soft_sq)
                pe -= self.G * bi.m * bj.m / r
        return ke + pe

    def total_momentum(self, bodies: List[Body]) -> Tuple[float, float]:
        px = sum(b.m * b.vx for b in bodies)
        py = sum(b.m * b.vy for b in bodies)
        return (px, py)

    def center_of_mass(self, bodies: List[Body]) -> Tuple[float, float]:
        m = sum(b.m for b in bodies)
        if m == 0.0:
            return (0.0, 0.0)
        cx = sum(b.m * b.x for b in bodies) / m
        cy = sum(b.m * b.y for b in bodies) / m
        return (cx, cy)


# ─── Forest–Ruth 4th-order symplectic ──────────────────────────────

# Forest–Ruth coefficients: three leapfrog sub-steps with special dt weights.
# The coefficients satisfy the 4th-order symplectic condition.
# θ = 1 / (2 - 2^(1/3)) ≈ 1.3512...
_FR_THETA = 1.0 / (2.0 - 2.0 ** (1.0 / 3.0))
_FR_W0 = -2 ** (1.0 / 3.0) / (2.0 - 2 ** (1.0 / 3.0))
_FR_W1 = 1.0 / (2.0 - 2 ** (1.0 / 3.0))
# Timestep weights: w0*dt, w1*dt, w1*dt, w0*dt  (sum = dt)
# Velocity (kick) weights: w1, w0, w1 (three kicks, each with half-weights)
# Standard formulation:
#   c_d = [w1/2, (w0+w1)/2, (w0+w1)/2, w1/2]  (drift)
#   c_k = [w1, w0, w1]                          (kick)
_FR_KICK = [_FR_W1, _FR_W0, _FR_W1]
_FR_DRIFT = [
    0.5 * _FR_W1,
    0.5 * (_FR_W0 + _FR_W1),
    0.5 * (_FR_W0 + _FR_W1),
    0.5 * _FR_W1,
]


class ForestRuthIntegrator:
    """4th-order symplectic integrator (Forest–Ruth).

    Uses three concatenated leapfrog sub-steps with special timestep
    weights to achieve O(dt⁴) accuracy while remaining symplectic
    (bounded energy error). The best integrator for long, demanding
    simulations.

    The Forest–Ruth coefficients are::

        θ = 1 / (2 - 2^(1/3))
        w0 = -2^(1/3) / (2 - 2^(1/3))
        w1 = 1 / (2 - 2^(1/3))

    The step is a sequence of three kicks and four drifts:

    .. code-block:: text

        drift(w1/2·dt) → kick(w1·dt) → drift((w0+w1)/2·dt)
        → kick(w0·dt) → drift((w0+w1)/2·dt) → kick(w1·dt) → drift(w1/2·dt)
    """

    def __init__(
        self,
        theta: float = 0.5,
        softening: float = 1.0,
        G: float = 1.0,
    ) -> None:
        self.theta = theta
        self.softening = softening
        self.G = G
        self._compute_accelerations = _bh_force_evaluator(theta, softening, G)

    def step(self, bodies: List[Body], dt: float) -> None:
        """Advance ``bodies`` by one Forest–Ruth step of length ``dt``."""
        if dt == 0.0 or not bodies:
            return
        # Three kicks, four drifts interleaved.
        # Drift 0
        for b in bodies:
            b.x += _FR_DRIFT[0] * dt * b.vx
            b.y += _FR_DRIFT[0] * dt * b.vy
        # Kick 0
        accels = self._compute_accelerations(bodies)
        for b, (ax, ay) in zip(bodies, accels):
            b.vx += _FR_KICK[0] * dt * ax
            b.vy += _FR_KICK[0] * dt * ay
        # Drift 1
        for b in bodies:
            b.x += _FR_DRIFT[1] * dt * b.vx
            b.y += _FR_DRIFT[1] * dt * b.vy
        # Kick 1
        accels = self._compute_accelerations(bodies)
        for b, (ax, ay) in zip(bodies, accels):
            b.vx += _FR_KICK[1] * dt * ax
            b.vy += _FR_KICK[1] * dt * ay
        # Drift 2
        for b in bodies:
            b.x += _FR_DRIFT[2] * dt * b.vx
            b.y += _FR_DRIFT[2] * dt * b.vy
        # Kick 2
        accels = self._compute_accelerations(bodies)
        for b, (ax, ay) in zip(bodies, accels):
            b.vx += _FR_KICK[2] * dt * ax
            b.vy += _FR_KICK[2] * dt * ay
        # Drift 3
        for b in bodies:
            b.x += _FR_DRIFT[3] * dt * b.vx
            b.y += _FR_DRIFT[3] * dt * b.vy

    def total_energy(self, bodies: List[Body]) -> float:
        ke = 0.0
        for b in bodies:
            ke += 0.5 * b.m * (b.vx * b.vx + b.vy * b.vy)
        pe = 0.0
        n = len(bodies)
        soft_sq = self.softening * self.softening
        for i in range(n):
            bi = bodies[i]
            for j in range(i + 1, n):
                bj = bodies[j]
                dx = bj.x - bi.x
                dy = bj.y - bi.y
                r = math.sqrt(dx * dx + dy * dy + soft_sq)
                pe -= self.G * bi.m * bj.m / r
        return ke + pe

    def total_momentum(self, bodies: List[Body]) -> Tuple[float, float]:
        px = sum(b.m * b.vx for b in bodies)
        py = sum(b.m * b.vy for b in bodies)
        return (px, py)

    def center_of_mass(self, bodies: List[Body]) -> Tuple[float, float]:
        m = sum(b.m for b in bodies)
        if m == 0.0:
            return (0.0, 0.0)
        cx = sum(b.m * b.x for b in bodies) / m
        cy = sum(b.m * b.y for b in bodies) / m
        return (cx, cy)


# ─── Integrator registry ────────────────────────────────────────────

INTEGRATORS = {
    "leapfrog": LeapfrogIntegrator,
    "rk4": RK4Integrator,
    "forest-ruth": ForestRuthIntegrator,
}


def make_integrator(name: str, theta: float = 0.5, softening: float = 1.0,
                    G: float = 1.0):
    """Factory: create an integrator by name.

    Parameters
    ----------
    name:
        One of 'leapfrog', 'rk4', 'forest-ruth'.
    """
    name = name.strip().lower()
    if name not in INTEGRATORS:
        raise ValueError(
            f"Unknown integrator '{name}'. "
            f"Available: {list(INTEGRATORS.keys())}"
        )
    return INTEGRATORS[name](theta=theta, softening=softening, G=G)


__all__ = [
    "LeapfrogIntegrator",
    "RK4Integrator",
    "ForestRuthIntegrator",
    "INTEGRATORS",
    "make_integrator",
]