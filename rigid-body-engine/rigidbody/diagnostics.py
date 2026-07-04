"""Diagnostics: energy, momentum, and simulation statistics.

These helpers compute aggregate quantities over the world's bodies, useful for
verifying conservation laws, detecting numerical drift, or reporting in a UI.
"""

from __future__ import annotations

from typing import Dict, List

from .core.body import RigidBody
from .core.vec2 import Vec2

__all__ = ["Diagnostics", "compute_energy", "compute_momentum"]


def compute_energy(bodies: List[RigidBody]) -> Dict[str, float]:
    """Return kinetic, potential (relative to y=0), and total energy.

    ``potential`` is computed as ``m * g * h`` with ``g = 9.81`` and ``h = y``;
    this is only meaningful if gravity points in ``-y``.  For other gravity
    directions the caller should interpret ``potential`` accordingly.
    """
    g = 9.81
    ke = 0.0
    pe = 0.0
    for b in bodies:
        if b.is_static:
            continue
        v_sq = b.linear_velocity.length_sq()
        ke += 0.5 * b.mass * v_sq + 0.5 * b.inertia * b.angular_velocity ** 2
        pe += b.mass * g * b.position.y
    return {"kinetic": ke, "potential": pe, "total": ke + pe}


def compute_momentum(bodies: List[RigidBody]) -> Dict[str, float]:
    """Return linear (x, y) and angular momentum of all non-static bodies."""
    px = py = L = 0.0
    for b in bodies:
        if b.is_static:
            continue
        px += b.mass * b.linear_velocity.x
        py += b.mass * b.linear_velocity.y
        L += b.inertia * b.angular_velocity
    return {"px": px, "py": py, "angular": L}


class Diagnostics:
    """Tracks per-step energy/momentum for drift analysis.

    Call :meth:`sample` after each ``world.step()``.  Then use :meth:`report`
    or access :attr:`history` for plotting or assertion.
    """

    def __init__(self) -> None:
        self.history: List[Dict[str, float]] = []
        self.step_count = 0

    def sample(self, bodies: List[RigidBody]) -> Dict[str, float]:
        e = compute_energy(bodies)
        p = compute_momentum(bodies)
        record = {**e, **p, "step": self.step_count}
        self.history.append(record)
        self.step_count += 1
        return record

    def report(self) -> Dict[str, float]:
        """Return min/max/mean of each tracked quantity."""
        if not self.history:
            return {}
        keys = [k for k in self.history[0] if k != "step"]
        stats: Dict[str, float] = {}
        for k in keys:
            vals = [r[k] for r in self.history]
            stats[f"{k}_min"] = min(vals)
            stats[f"{k}_max"] = max(vals)
            stats[f"{k}_mean"] = sum(vals) / len(vals)
        return stats

    def energy_drift(self) -> float:
        """Return ``(E_last - E_first) / |E_first|`` — relative energy drift.

        A well-behaved simulation should keep this near zero (a few percent).
        Large drift indicates the timestep is too large or the solver needs
        more iterations.
        """
        if len(self.history) < 2:
            return 0.0
        e0 = self.history[0]["total"]
        e1 = self.history[-1]["total"]
        if abs(e0) < 1e-12:
            return 0.0
        return (e1 - e0) / abs(e0)