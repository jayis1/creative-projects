"""The :class:`Body` dataclass — a single point mass in 2-D space.

Lives in its own module to avoid circular imports between
:mod:`nbody.simulation` and :mod:`nbody.integrator`.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Body:
    """A point mass in 2-D space.

    Fields are intentionally left mutable (the integrator updates them in
    place); use :meth:`copy` when you need a snapshot.
    """

    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    m: float = 1.0
    # Optional label, used by renderers / diagnostics.
    name: str = ""

    def copy(self) -> "Body":
        return Body(self.x, self.y, self.vx, self.vy, self.m, self.name)


__all__ = ["Body"]