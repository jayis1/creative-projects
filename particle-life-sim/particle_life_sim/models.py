"""Data models used by the particle life simulator."""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt


@dataclass(slots=True)
class Particle:
    """A single particle with position, velocity, and species id."""

    x: float
    y: float
    vx: float
    vy: float
    species: int

    def speed(self) -> float:
        return sqrt(self.vx * self.vx + self.vy * self.vy)


@dataclass(slots=True)
class SpeciesStyle:
    """Color and metadata used by renderers."""

    name: str
    color: str
