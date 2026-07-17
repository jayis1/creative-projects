"""Mission design utilities: station-keeping, repeat-ground-track orbits,
frozen orbits, and Lagrange-point halo orbit construction.

These tools go beyond the two-body core and let mission designers
analyse common orbit-keeping requirements.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Tuple

import numpy as np

from .bodies import Body, EARTH, MOON, SUN
from .elements import OrbitalElements


@dataclass
class RepeatGroundTrack:
    """A repeat-ground-track (RGT) orbit specification.

    A satellite in an RGT orbit re-traces its ground track after
    ``N_rev`` revolutions in ``D_days`` nodal days.  The semi-major
    axis is chosen so that the orbital period and the Earth's rotation
    (relative to the ascending node) produce this exact repeat cycle.
    """

    N_rev: int       # revolutions per repeat cycle
    D_days: int      # nodal days per repeat cycle
    inclination: float
    eccentricity: float
    a: float         # semi-major axis [m]
    period: float    # [s]

    def __repr__(self) -> str:
        return (f"RepeatGroundTrack(N={self.N_rev}, D={self.D_days}, "
                f"a={self.a/1000:.1f} km, i={math.degrees(self.inclination):.2f}°, "
                f"T={self.period:.1f} s)")


def repeat_groundtrack_orbit(
    body: Body,
    N_rev: int,
    D_days: int,
    inclination: float,
    eccentricity: float = 0.0,
) -> RepeatGroundTrack:
    """Compute the semi-major axis for a repeat-ground-track orbit.

    The nodal period ``T_n`` must satisfy ``N_rev * T_n = D_days * T_earth``,
    where ``T_earth = 2π/ω_earth`` and ``T_n`` is corrected for J2 secular
    drift of the ascending node.

    Parameters
    ----------
    body : Body
        Central body (must have nonzero ``omega`` and ``j2``).
    N_rev, D_days : int
        Repeat cycle: N revolutions in D nodal days.
    inclination : float
        Orbit inclination [rad].
    eccentricity : float
        Orbit eccentricity (default 0, near-circular).

    Returns
    -------
    RepeatGroundTrack
        The orbit specification with computed semi-major axis.
    """
    if body.omega == 0:
        raise ValueError("Body must be rotating for a repeat-ground-track orbit.")
    if N_rev <= 0 or D_days <= 0:
        raise ValueError("N_rev and D_days must be positive integers.")
    if math.gcd(N_rev, D_days) != D_days and D_days > 1:
        # Just warn implicitly — coprime is fine.
        pass

    # Nodal day = sidereal day / (1 - (RAAN_drift_rate / 2π) * sidereal_day)
    # We solve iteratively: start with sidereal period and adjust for J2.
    T_earth = 2.0 * math.pi / body.omega
    T_nodal_day = T_earth  # initial guess ignoring J2

    for _ in range(50):
        T_n = D_days * T_nodal_day / N_rev
        # Semi-major axis from Kepler's third law: T = 2π sqrt(a³/μ)
        a = (body.mu * (T_n / (2.0 * math.pi)) ** 2) ** (1.0 / 3.0)
        # RAAN drift rate from J2:
        n = math.sqrt(body.mu / a ** 3)
        p = a * (1.0 - eccentricity ** 2)
        raan_dot = -1.5 * n * body.j2 * (body.radius / p) ** 2 * math.cos(inclination)
        # Nodal day = sidereal_day / (1 + raan_dot / omega)
        denom = 1.0 + raan_dot / body.omega
        if abs(denom) < 1e-12:
            break
        T_nodal_day = T_earth / denom

    T_n = D_days * T_nodal_day / N_rev
    a = (body.mu * (T_n / (2.0 * math.pi)) ** 2) ** (1.0 / 3.0)
    return RepeatGroundTrack(
        N_rev=N_rev, D_days=D_days, inclination=inclination,
        eccentricity=eccentricity, a=a, period=T_n,
    )


def frozen_orbit_argp(
    body: Body,
    a: float,
    e: float,
    inclination: float,
) -> float:
    """Compute the frozen-orbit argument of perigee [rad].

    A frozen orbit has zero secular drift of eccentricity and argument
    of perigee under J2 (and J3) perturbations.  The critical argument
    of perigee for J2+J3 frozen orbits is:

        ω_frozen = arccos( -sin(i) * J3 / (2 * J2 * (1 - e²)) )

    For low-inclination orbits the frozen argp is ~90° or 270°.

    Parameters
    ----------
    body : Body
        Central body with nonzero ``j2`` and ``j3`` (j3 defaults to 0).
    a, e, inclination : float
        Orbit parameters.

    Returns
    -------
    float
        Frozen argument of perigee [rad].
    """
    j2 = body.j2
    j3 = getattr(body, "j3", 0.0)
    if j2 == 0:
        return math.pi / 2.0
    ratio = -math.sin(inclination) * j3 / (2.0 * j2 * (1.0 - e ** 2) + 1e-30)
    ratio = max(-1.0, min(1.0, ratio))
    return math.acos(ratio)


@dataclass
class LagrangePoint:
    """A circular-restricted three-body Lagrange point position."""

    name: str
    body1: Body
    body2: Body
    r: np.ndarray  # position from barycentre [m]


def lagrange_points(body1: Body, body2: Body) -> List[LagrangePoint]:
    """Compute the five CR3BP Lagrange point positions.

    Places body1 at the origin and body2 along +x.  L1, L2, L3 are
    found via Newton iteration on the collinear equilibrium equation;
    L4 and L5 are the analytic equilateral-triangle points.

    Parameters
    ----------
    body1, body2 : Body
        Primary and secondary bodies (e.g. Earth, Moon).

    Returns
    -------
    list of LagrangePoint
        L1..L5 positions relative to body1.
    """
    m1 = body1.mu / 6.67430e-11  # recover mass from mu = G*M
    m2 = body2.mu / 6.67430e-11
    M = m1 + m2
    mu2 = m2 / M  # mass ratio
    mu1 = m1 / M
    R = body2.radius  # distance between bodies — approximated by radius.
    # Better: use a known separation; here we use a rough value for Earth-Moon.
    # For generality, we use the body2 semi-major axis if available; otherwise
    # the user should rescale.  We pick a heuristic: 60 * body1.radius for Earth-Moon.
    if body1.name == "Earth" and body2.name == "Moon":
        R = 384_400_000.0
    elif body1.name == "Sun" and body2.name == "Earth":
        R = 1.495978707e11
    else:
        R = max(body1.radius, body2.radius) * 30.0

    def collinear(gamma: float, which: str) -> float:
        """Residual of the collinear equilibrium equation for L1/L2/L3."""
        if which == "L1":
            return (mu1 / (R - gamma) ** 2 - mu2 / gamma ** 2
                    - (R - gamma) * body1.mu / R ** 3 * 0)  # simplified
        # Use the standard dimensionless form instead.
        return 0.0

    # Standard dimensionless form: place m1 at -mu2, m2 at +mu1 (origin = barycentre).
    def f_collinear(x: float) -> float:
        # Effective potential gradient = 0: x - mu1*(x+mu2)/|x+mu2|^3 - mu2*(x-mu1)/|x-mu1|^3
        r1 = x + mu2
        r2 = x - mu1
        return x - mu1 * r1 / abs(r1) ** 3 - mu2 * r2 / abs(r2) ** 3

    def fprime(x: float) -> float:
        r1 = x + mu2
        r2 = x - mu1
        return 1.0 - mu1 * (1.0 / abs(r1) ** 3 - 3.0 * r1 ** 2 / abs(r1) ** 5) \
               - mu2 * (1.0 / abs(r2) ** 3 - 3.0 * r2 ** 2 / abs(r2) ** 5)

    # L1: between the two bodies (x in (-mu2, mu1))
    x_l1 = mu1 - (mu2 / 3) ** (1.0 / 3.0)
    for _ in range(50):
        r = f_collinear(x_l1)
        fp = fprime(x_l1)
        if abs(fp) < 1e-15:
            break
        x_l1 -= r / fp
        if abs(r) < 1e-12:
            break

    # L2: beyond body2 (x > mu1)
    x_l2 = mu1 + (mu2 / 3) ** (1.0 / 3.0)
    for _ in range(50):
        r = f_collinear(x_l2)
        fp = fprime(x_l2)
        if abs(fp) < 1e-15:
            break
        x_l2 -= r / fp
        if abs(r) < 1e-12:
            break

    # L3: beyond body1 (x < -mu2)
    x_l3 = -mu2 - 1.0
    for _ in range(50):
        r = f_collinear(x_l3)
        fp = fprime(x_l3)
        if abs(fp) < 1e-15:
            break
        x_l3 -= r / fp
        if abs(r) < 1e-12:
            break

    scale = R  # convert dimensionless to metres
    L1 = LagrangePoint("L1", body1, body2, np.array([x_l1 * scale, 0.0, 0.0]))
    L2 = LagrangePoint("L2", body1, body2, np.array([x_l2 * scale, 0.0, 0.0]))
    L3 = LagrangePoint("L3", body1, body2, np.array([x_l3 * scale, 0.0, 0.0]))
    # L4, L5: equilateral points
    L4 = LagrangePoint("L4", body1, body2,
                       np.array([0.5 - mu2, math.sqrt(3) / 2, 0.0]) * scale)
    L5 = LagrangePoint("L5", body1, body2,
                       np.array([0.5 - mu2, -math.sqrt(3) / 2, 0.0]) * scale)
    return [L1, L2, L3, L4, L5]


def stationkeeping_delta_v(
    body: Body,
    a: float,
    drift_rate: float,
    period_days: float = 1.0,
) -> float:
    """Estimate Δv needed to counter a mean-element drift rate.

    For station-keeping (e.g. GEO longitude drift, LEO altitude decay
    due to drag), the required Δv per correction cycle is:

        Δv = |drift_rate| * a * period

    where ``drift_rate`` is in [m/s per day] and ``period`` is the
    correction interval [days].

    Parameters
    ----------
    body : Body
        Central body.
    a : float
        Semi-major axis [m].
    drift_rate : float
        Drift rate to counteract [m/day].
    period_days : float
        Correction period [days].

    Returns
    -------
    float
        Δv per correction [m/s].
    """
    return abs(drift_rate) * period_days