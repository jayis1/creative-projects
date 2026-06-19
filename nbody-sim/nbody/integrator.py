"""Symplectic leapfrog (kick–drift–kick) integrator for N-body systems.

The leapfrog scheme is the standard choice for long-running gravity simulations
because it is *symplectic*: the energy error stays bounded over exponentially
long times, rather than drifting secularly as with naive Euler integration.

Each step performs three sub-steps:

1. **Kick**   – half-step velocity update from current accelerations.
2. **Drift**  – full-step position update using the kicked velocities.
3. **Kick**   – second half-step velocity update from accelerations recomputed
   at the new positions.

The :class:`LeapfrogIntegrator` is stateless apart from its parameters; it
operates on lists of :class:`~nbody.simulation.Body` objects in place so the
caller can keep references stable.
"""

from __future__ import annotations

import math
from typing import Callable, List

from .barnes_hut import BHTree
from .body import Body


class LeapfrogIntegrator:
    """Kick–drift–kick leapfrog integrator.

    Parameters
    ----------
    theta, softening, G:
        Forwarded to the :class:`~nbody.barnes_hut.BHTree` built each step.
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
        self._tree = BHTree(theta=theta, softening=softening, G=G)

    # -- helpers --------------------------------------------------------

    def _compute_accelerations(self, bodies: List[Body]) -> List[tuple]:
        """Rebuild the tree and return accelerations for every body."""
        point_masses = [(b.x, b.y, b.m) for b in bodies]
        self._tree.build(point_masses)
        return [self._tree.force_on(pm) for pm in point_masses]

    # -- public API -----------------------------------------------------

    def step(self, bodies: List[Body], dt: float) -> None:
        """Advance ``bodies`` by one kick–drift–kick step of length ``dt``.

        Mutates each body's ``x``, ``y``, ``vx``, ``vy`` in place.
        """
        if dt == 0.0:
            return
        if not bodies:
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
        """Total mechanical energy (kinetic + potential) of the system."""
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

    def total_momentum(self, bodies: List[Body]) -> tuple:
        px = sum(b.m * b.vx for b in bodies)
        py = sum(b.m * b.vy for b in bodies)
        return (px, py)

    def center_of_mass(self, bodies: List[Body]) -> tuple:
        m = sum(b.m for b in bodies)
        if m == 0.0:
            return (0.0, 0.0)
        cx = sum(b.m * b.x for b in bodies) / m
        cy = sum(b.m * b.y for b in bodies) / m
        return (cx, cy)


__all__ = ["LeapfrogIntegrator"]