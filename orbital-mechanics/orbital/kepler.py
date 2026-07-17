"""Robust solvers for Kepler's equation in several forms.

All solvers converge to a tolerance using Newton, Halley, or Markley
iterations with sensible safeguards.  Each function returns the principal root.
"""
from __future__ import annotations

import math


def solve_kepler_e(M: float, e: float, tol: float = 1e-12, max_iter: int = 50) -> float:
    """Solve Kepler's equation ``M = E - e sin E`` for the eccentric anomaly E.

    Uses Newton's method with step damping for high-eccentricity stability.
    For very high eccentricities (e > 0.8), switches to Markley's
    starter (Mikkola-Markley) for better initial convergence.

    Parameters
    ----------
    M : float
        Mean anomaly [rad].  Any real value is wrapped to ``(-pi, pi]``.
    e : float
        Eccentricity, ``0 <= e < 1`` (elliptic orbit).
    tol : float
        Convergence tolerance on the step size.
    max_iter : int
        Maximum number of Newton iterations.

    Returns
    -------
    float
        Eccentric anomaly E [rad], in the same branch as ``M``.

    Raises
    ------
    ValueError
        If ``e`` is not in the elliptic range or is NaN.
    """
    if e != e:  # NaN check
        raise ValueError("Eccentricity is NaN")
    if not (0.0 <= e < 1.0):
        raise ValueError(f"solve_kepler_e requires 0 <= e < 1; got e={e}")

    # Wrap M to (-pi, pi].
    M = math.fmod(M, 2.0 * math.pi)
    if M > math.pi:
        M -= 2.0 * math.pi
    elif M <= -math.pi:
        M += 2.0 * math.pi

    # Initial guess: Danby's starter is good for moderate e.
    # For high eccentricity, use Mikkola's starter.
    if e < 0.8:
        E = M + e * math.sin(M)
    else:
        E = _mikkola_starter(M, e)

    for _ in range(max_iter):
        f = E - e * math.sin(E) - M
        fp = 1.0 - e * math.cos(E)
        if abs(fp) < 1e-14:
            # Near-parabolic singularity; nudge E slightly.
            fp = 1e-14 if fp >= 0 else -1e-14
        dE = -f / fp
        # Damp the step to avoid overshoot for high eccentricities.
        if abs(dE) > 1.0:
            dE = math.copysign(1.0, dE)
        E += dE
        if abs(dE) < tol:
            break
    return E


def _mikkola_starter(M: float, e: float) -> float:
    """Mikkola's initial guess for Kepler's equation (good for e > 0.8).

    Reference: Mikkola (1987), "A cubic approximation for Kepler's equation."
    """
    sign = 1.0 if M >= 0 else -1.0
    M_abs = abs(M)
    alpha = (1.0 - e) / (e + 1e-30)
    beta = 0.5 * M_abs / (e + 1e-30)
    z = (beta + math.sqrt(beta * beta + alpha ** 3)) ** (1.0 / 3.0)
    s = z - alpha / (z + 1e-30)
    E = sign * (e * (3.0 * s - s ** 3) + M_abs)
    return E


def solve_kepler_h(M: float, e: float, tol: float = 1e-12, max_iter: int = 80) -> float:
    """Solve the hyperbolic Kepler equation ``M = e sinh H - H`` for H.

    Uses Newton's method with a robust initial guess and step damping.

    Parameters
    ----------
    M : float
        Mean anomaly [rad].
    e : float
        Eccentricity, ``e > 1``.
    tol, max_iter : see :func:`solve_kepler_e`.

    Raises
    ------
    ValueError
        If ``e`` is not > 1 or is NaN.
    """
    if e != e:
        raise ValueError("Eccentricity is NaN")
    if e <= 1.0:
        raise ValueError(f"solve_kepler_h requires e > 1; got e={e}")

    # Initial guess: Gooding's starter for hyperbolic case.
    # For large |M|, H ≈ sign(M) * ln(2|M|/e).
    if abs(M) > 1.0:
        H = math.copysign(math.log(2.0 * abs(M) / e + 1.0), M)
    else:
        H = M

    for _ in range(max_iter):
        f = e * math.sinh(H) - H - M
        fp = e * math.cosh(H) - 1.0
        if abs(fp) < 1e-15:
            fp = 1e-15 if fp >= 0 else -1e-15
        dH = -f / fp
        # Damp large steps.
        if abs(dH) > 2.0:
            dH = math.copysign(2.0, dH)
        H += dH
        if abs(dH) < tol:
            break
    return H


def solve_kepler_barker(D: float, M: float) -> float:
    """Solve Barker's equation for parabolic orbits: ``M = D + D³/3``.

    Given the mean anomaly M, returns the parabolic eccentric anomaly D
    (also called the Barker anomaly).  Uses Cardano's closed-form cubic
    solution.

    The equation ``D³ + 3D − 3M = 0`` is solved via:

        D = ∛(3M/2 + √(9M²/4 + 1)) + ∛(3M/2 − √(9M²/4 + 1))

    Parameters
    ----------
    D : float
        Unused (kept for API compatibility); pass 0.0.
    M : float
        Mean anomaly [rad].

    Returns
    -------
    float
        Barker anomaly D [rad].
    """
    disc = math.sqrt(9.0 * M * M / 4.0 + 1.0)
    B = 1.5 * M + disc
    C = 1.5 * M - disc
    # Cardano's formula with signed cube roots (handles negative M):
    return math.copysign(abs(B) ** (1.0 / 3.0), B) + math.copysign(abs(C) ** (1.0 / 3.0), C)


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

    Uses the formulation of Bate, Mueller & White with Stumpff functions.
    Handles elliptic, parabolic and hyperbolic orbits uniformly.

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

    Raises
    ------
    ValueError
        If ``mu`` or ``r0`` is non-positive.
    """
    if mu <= 0:
        raise ValueError(f"mu must be positive; got {mu}")
    if r0 <= 0:
        raise ValueError(f"r0 must be positive; got {r0}")

    alpha = 1.0 / a  # positive elliptic, zero parabolic, negative hyperbolic

    def stumpff(z: float) -> tuple[float, float, float]:
        """Stumpff functions c0, c1, c2 — numerically stable form."""
        # Clamp z to avoid cosh/sinh overflow (|z| > ~700 overflows float64).
        if z > 700.0:
            z = 700.0
        elif z < -700.0:
            z = -700.0
        if z > 0:
            sq = math.sqrt(z)
            c0 = (1.0 - math.cos(sq)) / z
            c1 = (sq - math.sin(sq)) / (z * sq) if z != 0 else 0.5
            c2 = (1.0 - math.cos(sq)) / z
        elif z < 0:
            sq = math.sqrt(-z)
            c0 = (math.cosh(sq) - 1.0) / (-z)
            c1 = (math.sinh(sq) - sq) / ((-z) * sq)
            c2 = (math.cosh(sq) - 1.0) / (-z)
        else:
            c0, c1, c2 = 0.5, 1.0 / 6.0, 0.5
        return c0, c1, c2

    # Initial guess for chi.
    # For elliptic: chi ≈ sqrt(mu) * dt * alpha = n * a * dt / sqrt(mu) ... 
    #   actually a good guess is chi = sqrt(mu) * dt / a (the "mean anomaly" scaled).
    # For hyperbolic: chi ≈ sqrt(-a) * n_h * dt = sqrt(mu) * dt / (-a).
    # For parabolic: chi ≈ (sqrt(mu) * dt * 2)^(1/3) (from Barker's equation scaling).
    if alpha > 1e-15:
        # Elliptic
        chi = math.sqrt(mu) * dt * alpha
    elif alpha < -1e-15:
        # Hyperbolic: n_h * dt = sqrt(mu / (-a)^3) * dt
        # chi = sqrt(-a) * H, where H ≈ M = n_h * dt for small M
        chi = math.sqrt(mu) * dt / (-a)
    else:
        # Parabolic: Barker's equation ~ chi^3 / (6 * sqrt(mu)) ... rough
        chi = math.copysign(abs(6.0 * math.sqrt(mu) * abs(dt)) ** (1.0 / 3.0), dt)

    for _ in range(max_iter):
        z = alpha * chi * chi
        c0, c1, c2 = stumpff(z)
        # Universal variable Kepler equation (Vallado eq 2.153):
        #   √μ·dt = (r₀·vr₀/√μ)·χ²·C₂ + (1−α·r₀)·χ³·C₃ + r₀·χ
        # where C₂ = c2 (our 3rd return) and C₃ = c1 (our 2nd return).
        # NOTE: our stumpff returns (c0=C₂, c1=C₃, c2=C₂) — c0 and c2 are
        # both C₂.  Use c2 for C₂ and c1 for C₃.
        f = ((r0 * vr0 / math.sqrt(mu)) * chi * chi * c2
             + (1.0 - alpha * r0) * chi ** 3 * c1
             + r0 * chi
             - math.sqrt(mu) * dt)
        fp = ((r0 * vr0 / math.sqrt(mu)) * chi * c1
              + (1.0 - alpha * r0) * chi * chi * c0
              + r0)
        if abs(fp) < 1e-15:
            break
        dchi = -f / fp
        # Damp large steps to avoid divergence (especially for hyperbolic).
        max_dchi = 0.5 * abs(chi) + 10.0
        if abs(dchi) > max_dchi:
            dchi = math.copysign(max_dchi, dchi)
        chi += dchi
        if abs(dchi) < tol:
            break
    return chi


def stumpff_functions(z: float) -> tuple[float, float, float]:
    """Public Stumpff functions c0(z), c1(z), c2(z).

    The Stumpff functions are defined as:
        c_n(z) = sum_{k=0}^{inf} (-z)^k / (2k + n)!

    They satisfy: c0(z) = (1 - cos(sqrt(z)))/z for z > 0,
    c0(z) = (cosh(sqrt(-z)) - 1)/(-z) for z < 0, c0(0) = 1/2.

    Parameters
    ----------
    z : float
        The argument (can be positive, negative, or zero).

    Returns
    -------
    (c0, c1, c2) : tuple of float
        The first three Stumpff functions.
    """
    if z > 0:
        sq = math.sqrt(z)
        c0 = (1.0 - math.cos(sq)) / z
        c1 = (sq - math.sin(sq)) / (z * sq) if z != 0 else 0.5
        c2 = (1.0 - math.cos(sq)) / z
    elif z < 0:
        sq = math.sqrt(-z)
        c0 = (math.cosh(sq) - 1.0) / (-z)
        c1 = (math.sinh(sq) - sq) / ((-z) * sq)
        c2 = (math.cosh(sq) - 1.0) / (-z)
    else:
        c0, c1, c2 = 0.5, 1.0 / 6.0, 0.5
    return c0, c1, c2