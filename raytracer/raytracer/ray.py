"""ray.py — Ray primitive."""

from __future__ import annotations

from .vec import Vec3

__all__ = ["Ray"]


class Ray:
    """A parametric ray: ``P(t) = origin + t*direction``.

    ``direction`` is assumed unit-length for the intersection routines to
    produce true distances; the camera and light helpers enforce this.
    """

    __slots__ = ("origin", "direction", "tmin", "tmax")

    def __init__(
        self,
        origin: Vec3,
        direction: Vec3,
        tmin: float = 1e-4,
        tmax: float = float("inf"),
    ) -> None:
        self.origin = origin
        # Normalise defensively so callers cannot accidentally break distance
        # semantics.
        d = direction.length()
        if d == 0.0:
            raise ValueError("Ray direction cannot be zero-length")
        self.direction = direction / d if abs(d - 1.0) > 1e-12 else direction
        self.tmin = tmin
        self.tmax = tmax

    def at(self, t: float) -> Vec3:
        return self.origin + self.direction * t

    def __repr__(self) -> str:
        return f"Ray(o={self.origin}, d={self.direction})"