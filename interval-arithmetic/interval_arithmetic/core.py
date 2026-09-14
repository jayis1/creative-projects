"""Closed real intervals with conservative elementary operations."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable


def _down(value: float) -> float:
    return math.nextafter(value, -math.inf)


def _up(value: float) -> float:
    return math.nextafter(value, math.inf)


@dataclass(frozen=True, slots=True)
class Interval:
    """A closed interval [lower, upper] containing real values."""

    lower: float
    upper: float

    def __post_init__(self) -> None:
        if math.isnan(self.lower) or math.isnan(self.upper):
            raise ValueError("interval endpoints cannot be NaN")
        if self.lower > self.upper:
            raise ValueError("lower endpoint must not exceed upper endpoint")

    @classmethod
    def point(cls, value: float) -> "Interval":
        return cls(float(value), float(value))

    @classmethod
    def hull(cls, values: Iterable[float]) -> "Interval":
        items = [float(v) for v in values]
        if not items:
            raise ValueError("cannot build an interval from no values")
        return cls(min(items), max(items))

    def __contains__(self, value: float) -> bool:
        return self.lower <= value <= self.upper

    def width(self) -> float:
        return self.upper - self.lower

    def midpoint(self) -> float:
        return (self.lower + self.upper) / 2.0

    def radius(self) -> float:
        return self.width() / 2.0

    def __add__(self, other: "Interval | float") -> "Interval":
        rhs = as_interval(other)
        return Interval(_down(self.lower + rhs.lower), _up(self.upper + rhs.upper))

    __radd__ = __add__

    def __neg__(self) -> "Interval":
        return Interval(-self.upper, -self.lower)

    def __sub__(self, other: "Interval | float") -> "Interval":
        return self + (-as_interval(other))

    def __rsub__(self, other: "Interval | float") -> "Interval":
        return as_interval(other) - self

    def __mul__(self, other: "Interval | float") -> "Interval":
        rhs = as_interval(other)
        products = (self.lower * rhs.lower, self.lower * rhs.upper,
                    self.upper * rhs.lower, self.upper * rhs.upper)
        return Interval(_down(min(products)), _up(max(products)))

    __rmul__ = __mul__

    def reciprocal(self) -> "Interval":
        if 0.0 in self:
            raise ZeroDivisionError("interval crosses zero")
        return Interval(_down(1.0 / self.upper), _up(1.0 / self.lower)) if self.lower > 0 else Interval(_down(1.0 / self.upper), _up(1.0 / self.lower))

    def __truediv__(self, other: "Interval | float") -> "Interval":
        return self * as_interval(other).reciprocal()

    def __rtruediv__(self, other: "Interval | float") -> "Interval":
        return as_interval(other) / self

    def intersect(self, other: "Interval") -> "Interval | None":
        low, high = max(self.lower, other.lower), min(self.upper, other.upper)
        return None if low > high else Interval(low, high)

    def __repr__(self) -> str:
        return f"Interval({self.lower:.12g}, {self.upper:.12g})"


def as_interval(value: Interval | float) -> Interval:
    return value if isinstance(value, Interval) else Interval.point(value)


def interval_sum(values: Iterable[Interval | float]) -> Interval:
    result = Interval.point(0.0)
    for value in values:
        result += as_interval(value)
    return result


def interval_product(values: Iterable[Interval | float]) -> Interval:
    result = Interval.point(1.0)
    for value in values:
        result *= as_interval(value)
    return result
