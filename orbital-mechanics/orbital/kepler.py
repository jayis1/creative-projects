"""Robust solvers for Kepler's equation in several forms.

All solvers converge to a tolerance using Newton / Halley iterations with
sensible safeguards.  Each function returns the principal root.
"""
from __future__ import annotations

import math


def solve_kepler_e(M: float, e: float, tol: float = 1e-12, max_iter: int = 50) -> float:
    """Solve Kepler's equation ``M = E - e sin E`` for the eccentric anomaly E.

    Parameters
    ----------
    M : float
        Mean anomaly [rad].  Any real value is wrapped to ``(-pi, pi]``.
    e : float
        Eccentricity, ``0 <= e < 1`` (elliptic orbit).
    tol : float
        Convergence tolerance on the residual.
    max_iter : int
        Maximum number of Newton iterations.

    Returns
    -------
    float
        Eccentric anomaly E [rad], in the same branch as ``M``.

    Raises
    ------
    ValueError
        If ``e`` is not in the elliptic range.
    """
    if not (0.0 <= e < 1.0):
        raise ValueError(f"solve_kepler_e requires 0 <= e < 1; got e={e}")

    # Wrap M to (-pi, pi].
    M = math.fmod(M, 2.0 * math.pi)
    if M > math.pi:
        M -= 2.0 * math.pi
    elif M <= -math.pi:
        M += 2.0 * math.pi

    # Initial guess: Danby's starter (good for all e).
    E = M + e * math.sin(M)

    for _ in range(max_iter):
        f = E - e * math.sin(E) - M
        fp = 1.0 - e * math.cos(E)
        if abs(fp) < 1e-14:
            # Near-parabolic singularity; nudge E slightly.
            fp = 1e-14
        dE = -f / fp
        # Damp the step to avoid overshoot for high eccentricities.
        if abs(dE) > 1.0:
            dE = math.copysign(1.0, dE)
        E += dE
        if abs(dE) < tol:
            break
    return E


def solve_kepler_h(M: float, e: float, tol: float = 1e-12, max_iter: int = 50) -> float:
    """Solve the hyperbolic Kepler equation ``M = e sinh H - H`` for H.

    Parameters
    ----------
    M : float
        Mean anomaly [rad].
    e : float
        Eccentricity, ``e > 1``.
    tol, max_iter : see :func:`solve_kepler_e`.
    """
    if e <= 1.0:
        raise ValueError(f"solve_kepler_h requires e > 1; got e={e}")
    H = M if M > 0 else M  # initial guess
    for _ in range(max_iter):
        f = e * math.sinh(H) - H - M
        fp = e * math.cosh(H) - 1.0
        dH = -f / fp if abs(fp) > 1e-15 else -f / 1e-15
        H += dH
        if abs(dH) < tol:
            break
    return H


def solve_universal_kepler(
    mu: float,
    r0: float,
    vr0: float,
    a: float,
    dt: float,
    tol: float = 1e-12,
    max_iter: int = 80,
) -> float:
    """Solve the universal variable Kepler equation for the universal anomaly χ.

    Uses the formulation of Bate, Mueller & White (Fundamentals of
    Astrodynamics) with Stumpff functions.  Handles elliptic, parabolic and
    hyperbolic orbits uniformly.

    Parameters
    ----------
    mu : float
        Gravitational parameter [m^3/s^2].
    r0 : float
        Initial radial distance [m].
    vr0 : float
        Initial radial velocity [m/s].
    a : float
        Semi-major axis [m] (negative for hyperbolic orbits).
    dt : float
        Time of flight [s].

    Returns
    -------
    float
        Universal anomaly χ.
    """
    alpha = 1.0 / a  # positive elliptic, zero parabolic, negative hyperbolic

    def stumpff(z: float) -> tuple[float, float, float]:
        # Stumpff functions c0, c1, c2 — numerically stable form.
        if z > 0:
            sq = math.sqrt(z)
            c0 = (1.0 - math.cos(sq)) / z
            c1 = (sq - math.sin(sq)) / (z * sq) if z != 0 else 1.0 / 2.0
            c2 = (1.0 - math.cos(sq)) / z
        elif z < 0:
            sq = math.sqrt(-z)
            c0 = (math.cosh(sq) - 1.0) / (-z)
            c1 = (math.sinh(sq) - sq) / ((-z) * sq)
            c2 = (math.cosh(sq) - 1.0) / (-z)
        else:
            c0, c1, c2 = 0.5, 1.0 / 6.0, 0.5
        return c0, c1, c2

    # Initial guess for chi
    if alpha > 0:
        chi = math.sqrt(mu) * dt * alpha
    else:
        chi = (1.0 if dt >= 0 else -1.0) * math.sqrt(-a) * 2.0  # rough guess

    for _ in range(max_iter):
        z = alpha * chi * chi
        c0, c1, c2 = stumpff(z)
        f = (r0 * vr0 / math.sqrt(mu)) * chi * chi * c1 + (1.0 - alpha * r0) * chi * chi * chi * c2 + r0 * chi - math.sqrt(mu) * dt
        fp = (r0 * vr0 / math.sqrt(mu)) * chi * c0 + (1.0 - alpha * r0) * chi * chi * c1 + r0
        dchi = -f / fp if abs(fp) > 1e-15 else 0.0
        chi += dchi
        if abs(dchi) < tol:
            break
    return chi


def math_sign(x: float) -> float:
    if x > 0:
        return 1.0
    if x < 0:
        return -1.0
    return 0.0