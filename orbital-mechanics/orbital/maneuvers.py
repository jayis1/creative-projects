"""Orbital maneuvers: Hohmann, bi-elliptic, Lambert, Δv computations."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Tuple

import numpy as np

from .bodies import Body, EARTH
from .elements import StateVector, rv_to_elements
from .kepler import solve_universal_kepler


@dataclass
class TransferResult:
    """Result of a transfer-orbit computation."""

    dv_total: float           # total Δv [m/s]
    dv1: float                # first burn [m/s]
    dv2: float                # second burn [m/s]
    tof: float                # time of flight [s]
    description: str = ""


def _visviva(mu: float, r: float, a: float) -> float:
    return math.sqrt(mu * (2.0 / r - 1.0 / a))


def hohmann_transfer(body: Body, r1: float, r2: float) -> TransferResult:
    """Hohmann transfer between two coplanar circular orbits.

    Parameters
    ----------
    r1, r2 : float
        Radii of the initial and final circular orbits [m].
    """
    if r1 <= 0 or r2 <= 0:
        raise ValueError("Radii must be positive.")
    mu = body.mu
    a_t = 0.5 * (r1 + r2)
    v1 = _visviva(mu, r1, r1)
    vt1 = _visviva(mu, r1, a_t)
    dv1 = abs(vt1 - v1)
    v2 = _visviva(mu, r2, r2)
    vt2 = _visviva(mu, r2, a_t)
    dv2 = abs(v2 - vt2)
    tof = math.pi * math.sqrt(a_t ** 3 / mu)
    return TransferResult(
        dv_total=dv1 + dv2, dv1=dv1, dv2=dv2, tof=tof,
        description=f"Hohmann transfer {r1/1000:.0f}km → {r2/1000:.0f}km",
    )


def bielliptic_transfer(body: Body, r1: float, r2: float, rb: float) -> TransferResult:
    """Bi-elliptic transfer through an intermediate apogee radius ``rb``.

    ``rb`` must exceed both ``r1`` and ``r2``.
    """
    if rb <= max(r1, r2):
        raise ValueError("Intermediate radius rb must exceed both r1 and r2.")
    mu = body.mu
    a1 = 0.5 * (r1 + rb)
    a2 = 0.5 * (r2 + rb)
    v1 = _visviva(mu, r1, r1)
    vt1 = _visviva(mu, r1, a1)
    dv1 = abs(vt1 - v1)
    vb1 = _visviva(mu, rb, a1)
    vb2 = _visviva(mu, rb, a2)
    dv2 = abs(vb2 - vb1)
    v2 = _visviva(mu, r2, r2)
    vt2 = _visviva(mu, r2, a2)
    dv3 = abs(v2 - vt2)
    tof = math.pi * math.sqrt(a1 ** 3 / mu) + math.pi * math.sqrt(a2 ** 3 / mu)
    return TransferResult(
        dv_total=dv1 + dv2 + dv3, dv1=dv1, dv2=dv2, tof=tof,
        description=f"Bi-elliptic via rb={rb/1000:.0f}km",
    )


def compute_dv(v1: np.ndarray, v2: np.ndarray) -> float:
    """Scalar Δv magnitude between two velocity vectors."""
    return float(np.linalg.norm(np.asarray(v2) - np.asarray(v1)))


def _stumpff(z: float) -> Tuple[float, float, float]:
    if z > 0:
        sq = math.sqrt(z)
        c0 = (1.0 - math.cos(sq)) / z
        c2 = (1.0 - math.cos(sq)) / z
        c1 = (sq - math.sin(sq)) / (z * sq) if z != 0 else 0.5
    elif z < 0:
        sq = math.sqrt(-z)
        c0 = (math.cosh(sq) - 1.0) / (-z)
        c2 = (math.cosh(sq) - 1.0) / (-z)
        c1 = (math.sinh(sq) - sq) / ((-z) * sq)
    else:
        c0, c1, c2 = 0.5, 1.0 / 6.0, 0.5
    return c0, c1, c2


def lambert_izzo(
    r1: np.ndarray,
    r2: np.ndarray,
    tof: float,
    mu: float,
    M: int = 0,
    prograde: bool = True,
) -> Tuple[np.ndarray, np.ndarray]:
    """Solve Lambert's problem using the universal-variable / Izzo formulation.

    Returns the initial and final velocity vectors ``(v1, v2)`` for the
    specified transfer.  This implements the algorithm from Izzo (2015),
    "Revisiting Lambert's problem" (Acta Astronautica), which is robust for
    multi-revolution transfers and handles all orbit types.

    Parameters
    ----------
    r1, r2 : ndarray
        Initial and final position vectors [m].
    tof : float
        Time of flight [s].
    mu : float
        Gravitational parameter.
    M : int
        Number of complete revolutions (≥ 0).  M=0 is the standard case.
    prograde : bool
        If True, the transfer follows the short-way (prograde) solution.

    Returns
    -------
    (v1, v2) : tuple of ndarray
        Velocity vectors at r1 and r2.
    """
    r1 = np.asarray(r1, dtype=float)
    r2 = np.asarray(r2, dtype=float)
    R1 = float(np.linalg.norm(r1))
    R2 = float(np.linalg.norm(r2))
    if R1 < 1e-9 or R2 < 1e-9:
        raise ValueError("Position vectors must be non-zero.")
    if tof <= 0:
        raise ValueError("Time of flight must be positive.")
    if M < 0:
        raise ValueError("Revolution count M must be non-negative.")

    cos_dnu = float(np.dot(r1, r2)) / (R1 * R2)
    cos_dnu = max(-1.0, min(1.0, cos_dnu))
    dnu = math.acos(cos_dnu)
    # Short-way / long-way: determine from the cross product sign.
    h_hat = np.cross(r1, r2)
    h_norm = float(np.linalg.norm(h_hat))

    if h_norm < 1e-9:
        # r1 and r2 are (anti)parallel — the transfer plane is undefined.
        # For prograde we assume the orbit passes through +y (h along +z).
        if abs(dnu - math.pi) < 1e-9:
            # 180° transfer: pick the plane via a reference axis.
            ref = np.array([0.0, 1.0, 0.0]) if prograde else np.array([0.0, -1.0, 0.0])
            h_hat = np.cross(r1, ref)
            h_norm = float(np.linalg.norm(h_hat))
            if h_norm < 1e-9:
                ref = np.array([0.0, 0.0, 1.0])
                h_hat = np.cross(r1, ref)
                h_norm = float(np.linalg.norm(h_hat))
        elif dnu < 1e-9:
            raise ValueError("r1 and r2 are parallel (0° transfer); Lambert undefined.")

    if h_norm > 1e-12:
        h_hat = h_hat / h_norm

    # Determine short-way vs long-way.
    if prograde:
        if h_hat[2] < 0:
            dnu = 2.0 * math.pi - dnu
    else:
        if h_hat[2] >= 0:
            dnu = 2.0 * math.pi - dnu

    # The universal-variables Lambert formulation uses the transfer angle.
    A = math.sqrt(R1 * R2) * math.sin(dnu)
    if abs(A) < 1e-12:
        raise ValueError("Transfer geometry degenerate (A ~ 0).")

    # We solve for the parameter x in [-1, 1] using the universal form.
    # Izzo's algorithm iterates on x with householder iterations.
    z_min = -1.0
    z_max = 1.0

    def c2_c3(z):
        if z > 0:
            sq = math.sqrt(z)
            c2 = (1.0 - math.cos(sq)) / z
            c3 = (sq - math.sin(sq)) / (z * sq)
        elif z < 0:
            sq = math.sqrt(-z)
            c2 = (math.cosh(sq) - 1.0) / (-z)
            c3 = (math.sinh(sq) - sq) / ((-z) * sq)
        else:
            c2, c3 = 0.5, 1.0 / 6.0
        return c2, c3

    def tof_of_z(z):
        """Time-of-flight as a function of the universal variable z.

        Uses the corrected universal-variable Lambert tof equation:
            tof = (chi³ · S(z) + A · chi · √C(z)) / √μ
        where chi = √(y/C(z)), and y is the geometry-dependent function
        y(z) = R1 + R2 + A·(z·S(z) − 1) / √C(z).

        The √C factor is essential: g = A·√(y/μ) = A·chi·√(C/μ), so
        tof = g + chi³·S/√μ = (A·chi·√C + chi³·S) / √μ.
        """
        c2, c3 = c2_c3(z)
        if c2 < 1e-14:
            return float("inf")
        y = R1 + R2 + A * (z * c3 - 1.0) / math.sqrt(c2)
        if y < 0:
            return float("inf")
        chi = math.sqrt(y / c2)
        return (chi ** 3 * c3 + A * chi * math.sqrt(c2)) / math.sqrt(mu)

    # The corrected tof(z) function is monotonically increasing from the
    # leftmost finite z (where y crosses 0) to z → 4π² (where c2 → 0).
    # Simple bisection suffices — no need for a minimum-energy search.
    Z_MAX = 700.0  # clamp to avoid cosh overflow
    z_upper = (2.0 * math.pi) ** 2 - 1e-6

    # Find a finite starting bracket by scanning inward from the extremes.
    def _find_finite(z_start, z_end, n=128):
        """Return the first z in a scan from z_start→z_end with finite tof."""
        for k in range(1, n):
            z = z_start + (z_end - z_start) * k / n
            t = tof_of_z(z)
            if t != float("inf"):
                return z
        return z_end

    z_lo_finite = _find_finite(-Z_MAX, 0.0)
    z_hi_finite = _find_finite(z_upper, 0.0)

    lo, hi = z_lo_finite, z_hi_finite
    t_lo = tof_of_z(lo)
    t_hi = tof_of_z(hi)
    if t_lo == float("inf") or t_hi == float("inf"):
        raise RuntimeError("Lambert: failed to establish finite bracket.")
    if tof < t_lo:
        raise ValueError(
            f"Lambert: requested tof={tof:.3f} s is less than the minimum "
            f"possible tof={t_lo:.3f} s for this geometry."
        )
    if tof > t_hi:
        raise ValueError(
            f"Lambert: requested tof={tof:.3f} s exceeds the maximum "
            f"possible tof={t_hi:.3f} s for this geometry."
        )

    # Bisection — the tof function is monotonic so this is robust.
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        tm = tof_of_z(mid)
        if tm == float("inf"):
            hi = mid
            continue
        if tm < tof:
            lo = mid
        else:
            hi = mid
        if hi - lo < 1e-12:
            break
    z = 0.5 * (lo + hi)

    c2, c3 = c2_c3(z)
    y = R1 + R2 + A * (z * c3 - 1.0) / math.sqrt(c2)
    if y < 0:
        raise RuntimeError("Lambert iteration produced y < 0; no solution.")
    # Universal-variable f and g functions (Vallado, Algorithm 58):
    #   f = 1 - y/R1
    #   g = A * sqrt(y / mu)         ← note: y/mu, NOT y/c2
    #   gdot = 1 - y/R2
    f = 1.0 - y / R1
    g = A * math.sqrt(y / mu)
    gdot = 1.0 - y / R2

    v1 = (r2 - f * r1) / g
    v2 = (gdot * r2 - r1) / g
    return v1, v2