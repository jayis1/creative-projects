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

    def sqrt(self) -> "Interval":
        if self.lower < 0:
            raise ValueError("square root interval cannot contain negative values")
        return Interval(_down(math.sqrt(self.lower)), _up(math.sqrt(self.upper)))

    def exp(self) -> "Interval":
        return Interval(_down(math.exp(self.lower)), _up(math.exp(self.upper)))

    def log(self) -> "Interval":
        if self.lower <= 0:
            raise ValueError("log interval must be strictly positive")
        return Interval(_down(math.log(self.lower)), _up(math.log(self.upper)))

    def sin(self) -> "Interval":
        return _trig_interval(self, math.sin, math.pi / 2)

    def cos(self) -> "Interval":
        return _trig_interval(self, math.cos, 0.0)

    def intersect(self, other: "Interval") -> "Interval | None":
        low, high = max(self.lower, other.lower), min(self.upper, other.upper)
        return None if low > high else Interval(low, high)

    def __repr__(self) -> str:
        return f"Interval({self.lower:.12g}, {self.upper:.12g})"


def _trig_interval(interval: Interval, function, critical_offset: float) -> Interval:
    """Bound a periodic function, widening to [-1, 1] across a full period."""
    if interval.width() >= 2 * math.pi:
        return Interval(-1.0, 1.0)
    points = [interval.lower, interval.upper]
    period = math.pi
    first = math.ceil((interval.lower - critical_offset) / period)
    last = math.floor((interval.upper - critical_offset) / period)
    points.extend(critical_offset + n * period for n in range(first, last + 1))
    values = [function(point) for point in points]
    return Interval(_down(min(values)), _up(max(values)))


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
