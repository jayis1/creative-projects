"""Small, dependency-free sRGB and CIE Lab conversion toolkit."""
from __future__ import annotations

import math

D65 = (0.95047, 1.0, 1.08883)


def _unit(value: float, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{label} must be a finite number")
    if not 0 <= value <= 1:
        raise ValueError(f"{label} must be between 0 and 1")
    return float(value)


def srgb_to_xyz(rgb: tuple[float, float, float]) -> tuple[float, float, float]:
    """Convert gamma-encoded sRGB components in [0, 1] to D65 XYZ."""
    if len(rgb) != 3:
        raise ValueError("RGB must contain exactly three components")
    linear = []
    for i, value in enumerate(rgb):
        c = _unit(value, f"RGB component {i}")
        linear.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    r, g, b = linear
    return (0.4124564*r + 0.3575761*g + 0.1804375*b,
            0.2126729*r + 0.7151522*g + 0.0721750*b,
            0.0193339*r + 0.1191920*g + 0.9503041*b)


def xyz_to_lab(xyz: tuple[float, float, float]) -> tuple[float, float, float]:
    """Convert D65 XYZ (Y normalized to 1) to CIE L*a*b*."""
    if len(xyz) != 3:
        raise ValueError("XYZ must contain exactly three components")
    vals = []
    for i, value in enumerate(xyz):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise ValueError(f"XYZ component {i} must be finite and nonnegative")
        vals.append(value / D65[i])
    delta = 6 / 29
    f = lambda t: t ** (1 / 3) if t > delta**3 else t / (3 * delta**2) + 4 / 29
    fx, fy, fz = map(f, vals)
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def rgb_to_lab(rgb: tuple[float, float, float]) -> tuple[float, float, float]:
    return xyz_to_lab(srgb_to_xyz(rgb))


def delta_e76(first: tuple[float, float, float], second: tuple[float, float, float]) -> float:
    """Return Euclidean CIE76 difference between two L*a*b* coordinates."""
    if len(first) != 3 or len(second) != 3:
        raise ValueError("each Lab color must contain exactly three components")
    for label, color in (("first", first), ("second", second)):
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
               for v in color):
            raise ValueError(f"{label} Lab components must be finite numbers")
    differences = [float(a) - float(b) for a, b in zip(first, second)]
    # Finite coordinates can still overflow during subtraction; never emit inf as a valid distance.
    if any(not math.isfinite(value) for value in differences):
        raise ValueError("Lab distance exceeds the finite float range")
    distance = math.hypot(*differences)
    if not math.isfinite(distance):
        raise ValueError("Lab distance exceeds the finite float range")
    return distance
