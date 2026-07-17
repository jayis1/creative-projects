"""Classical Keplerian element ↔ Cartesian state-vector conversions.

All angles are in radians.  Distances in metres, velocities in m/s.
Reference: Vallado, *Fundamentals of Astrodynamics and Applications*.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Tuple

import numpy as np

from .bodies import Body
from .kepler import solve_kepler_e, solve_kepler_h


@dataclass
class StateVector:
    """Position [m] and velocity [m/s] vectors in an inertial frame."""

    r: np.ndarray
    v: np.ndarray
    t: float = 0.0  # epoch (seconds since reference)

    def __post_init__(self) -> None:
        self.r = np.asarray(self.r, dtype=float).reshape(3)
        self.v = np.asarray(self.v, dtype=float).reshape(3)


@dataclass
class OrbitalElements:
    """Classical orbital elements with respect to a central body."""

    a: float        # semi-major axis [m] (negative if hyperbolic)
    e: float        # eccentricity
    i: float        # inclination [rad]
    raan: float     # right ascension of ascending node Ω [rad]
    argp: float     # argument of periapsis ω [rad]
    nu: float       # true anomaly ν [rad] at epoch
    mu: float = field(default=3.986004418e14)

    @property
    def is_elliptic(self) -> bool:
        return 0.0 <= self.e < 1.0

    @property
    def is_hyperbolic(self) -> bool:
        return self.e > 1.0

    @property
    def is_parabolic(self) -> bool:
        return abs(self.e - 1.0) < 1e-12

    @property
    def period(self) -> float:
        """Orbital period [s] (elliptic only; ``inf`` otherwise)."""
        if self.is_elliptic and self.a > 0:
            return 2.0 * math.pi * math.sqrt(self.a ** 3 / self.mu)
        return float("inf")

    @property
    def p(self) -> float:
        """Semi-latus rectum [m]."""
        return self.a * (1.0 - self.e ** 2)

    @property
    def perigee(self) -> float:
        """Periapsis radius [m]."""
        return self.a * (1.0 - self.e)

    @property
    def apogee(self) -> float:
        """Apoapsis radius [m] (``inf`` for hyperbolic)."""
        if self.is_hyperbolic or self.is_parabolic:
            return float("inf")
        return self.a * (1.0 + self.e)


# --------------------------------------------------------------------------- #
#  Conversions
# --------------------------------------------------------------------------- #
def rv_to_elements(state: StateVector, body: Body) -> OrbitalElements:
    """Convert a Cartesian state vector into classical orbital elements."""
    r = state.r
    v = state.v
    mu = body.mu
    rmag = float(np.linalg.norm(r))
    vmag = float(np.linalg.norm(v))

    if rmag < 1e-9:
        raise ValueError("Position vector is zero; cannot compute elements.")

    # Angular momentum
    h = np.cross(r, v)
    hmag = float(np.linalg.norm(h))
    if hmag < 1e-9:
        raise ValueError("Angular momentum is zero (radial orbit); elements undefined.")

    # Node vector
    n = np.cross([0, 0, 1], h)
    nmag = float(np.linalg.norm(n))

    # Eccentricity vector
    evec = (np.cross(v, h) / mu) - (r / rmag)
    e = float(np.linalg.norm(evec))

    # Specific energy → semi-major axis
    energy = vmag * vmag / 2.0 - mu / rmag
    if abs(e - 1.0) < 1e-10:
        a = float("inf")  # parabolic
    else:
        a = -mu / (2.0 * energy)

    # Inclination
    i = math.acos(max(-1.0, min(1.0, h[2] / hmag)))

    # RAAN
    if nmag > 1e-9:
        raan = math.acos(max(-1.0, min(1.0, n[0] / nmag)))
        if n[1] < 0:
            raan = 2.0 * math.pi - raan
    else:
        raan = 0.0  # equatorial → undefined, set to 0

    # Argument of periapsis
    if nmag > 1e-9 and e > 1e-9:
        argp = math.acos(max(-1.0, min(1.0, float(np.dot(n, evec)) / (nmag * e))))
        if evec[2] < 0:
            argp = 2.0 * math.pi - argp
    elif e > 1e-9:
        # Equatorial orbit: ω measured from x-axis to evec
        argp = math.acos(max(-1.0, min(1.0, evec[0] / e)))
        if evec[1] < 0:
            argp = 2.0 * math.pi - argp
    else:
        argp = 0.0  # circular → undefined, set to 0

    # True anomaly
    if e > 1e-9:
        nu = math.acos(max(-1.0, min(1.0, float(np.dot(evec, r)) / (e * rmag))))
        if float(np.dot(r, v)) < 0:
            nu = 2.0 * math.pi - nu
    else:
        # Circular: use argument of latitude
        if nmag > 1e-9:
            nu = math.acos(max(-1.0, min(1.0, float(np.dot(n, r)) / (nmag * rmag))))
            if r[2] < 0:
                nu = 2.0 * math.pi - nu
        else:
            nu = math.acos(max(-1.0, min(1.0, r[0] / rmag)))
            if r[1] < 0:
                nu = 2.0 * math.pi - nu

    return OrbitalElements(a=a, e=e, i=i, raan=raan, argp=argp, nu=nu, mu=mu)


def elements_to_rv(elements: OrbitalElements, body: Body | None = None) -> StateVector:
    """Convert classical orbital elements to a Cartesian state vector at ν."""
    mu = body.mu if body is not None else elements.mu
    e = elements.e
    nu = elements.nu
    a = elements.a
    p = elements.p

    # Radius and speed in the perifocal frame
    r_pfq = p / (1.0 + e * math.cos(nu))
    # Handle parabolic
    if math.isinf(a):
        # Parabolic: use p directly; v magnitude from vis-viva with a→inf
        vmag = math.sqrt(2.0 * mu / r_pfq - 0.0)  # energy=0
    else:
        vmag = math.sqrt(2.0 * mu / r_pfq - mu / a)

    r_pfq_vec = np.array([r_pfq * math.cos(nu), r_pfq * math.sin(nu), 0.0])
    # Velocity direction in perifocal: dr/dν and dν/dt
    # v_pfq = (mu/h) * [-sin ν, e + cos ν, 0]
    h = math.sqrt(mu * p)
    v_pfq_vec = (mu / h) * np.array([-math.sin(nu), e + math.cos(nu), 0.0])

    # Rotation from perifocal to geocentric equatorial: R3(-Ω) R1(-i) R3(-ω)
    from .frames import rot1, rot2, rot3
    # Standard: PQW → ECI = R3(Ω) R1(i) R3(ω)
    R = rot3(elements.raan) @ rot1(elements.i) @ rot3(elements.argp)
    r_eci = R @ r_pfq_vec
    v_eci = R @ v_pfq_vec
    return StateVector(r=r_eci, v=v_eci, t=0.0)


def true_to_mean(nu: float, e: float) -> float:
    """Convert true anomaly ν to mean anomaly M [rad] (elliptic or hyperbolic)."""
    if e < 1.0:
        E = 2.0 * math.atan2(math.sqrt(1.0 - e) * math.sin(nu / 2.0),
                             math.sqrt(1.0 + e) * math.cos(nu / 2.0))
        M = E - e * math.sin(E)
    elif e > 1.0:
        H = 2.0 * math.atanh(math.sqrt((e - 1.0) / (e + 1.0)) * math.tan(nu / 2.0)) \
            if abs(nu) < math.acos(-1.0 / e) else float("nan")
        M = e * math.sinh(H) - H
    else:
        # Parabolic
        D = math.tan(nu / 2.0)
        M = D + D ** 3 / 3.0
    return M


def mean_to_true(M: float, e: float) -> float:
    """Convert mean anomaly M to true anomaly ν [rad]."""
    if e < 1.0:
        E = solve_kepler_e(M, e)
        nu = 2.0 * math.atan2(math.sqrt(1.0 + e) * math.sin(E / 2.0),
                              math.sqrt(1.0 - e) * math.cos(E / 2.0))
    elif e > 1.0:
        H = solve_kepler_h(M, e)
        nu = 2.0 * math.atan2(math.sqrt(e + 1.0) * math.sinh(H / 2.0),
                              math.sqrt(e - 1.0) * math.cosh(H / 2.0))
    else:
        # Parabolic: M = D + D^3/3, solve iteratively (Newton)
        D = (3.0 * M) ** (1.0 / 3.0)
        for _ in range(50):
            f = D + D ** 3 / 3.0 - M
            fp = 1.0 + D * D
            dD = -f / fp
            D += dD
            if abs(dD) < 1e-12:
                break
        nu = 2.0 * math.atan(D)
    return math.fmod(nu + 2.0 * math.pi, 2.0 * math.pi) if nu < 0 else math.fmod(nu, 2.0 * math.pi)