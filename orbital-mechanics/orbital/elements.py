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
from .kepler import solve_kepler_e, solve_kepler_h, solve_kepler_barker


@dataclass
class StateVector:
    """Position [m] and velocity [m/s] vectors in an inertial frame.

    Parameters
    ----------
    r : array-like
        Position vector [m] in the inertial frame.
    v : array-like
        Velocity vector [m/s] in the inertial frame.
    t : float
        Epoch (seconds since reference, default 0.0).
    """

    r: np.ndarray
    v: np.ndarray
    t: float = 0.0

    def __post_init__(self) -> None:
        self.r = np.asarray(self.r, dtype=float).reshape(3)
        self.v = np.asarray(self.v, dtype=float).reshape(3)

    def __repr__(self) -> str:
        return (
            f"StateVector(r=[{self.r[0]:.3f}, {self.r[1]:.3f}, {self.r[2]:.3f}] m, "
            f"v=[{self.v[0]:.3f}, {self.v[1]:.3f}, {self.v[2]:.3f}] m/s, "
            f"t={self.t:.1f} s)"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, StateVector):
            return NotImplemented
        return (
            np.allclose(self.r, other.r)
            and np.allclose(self.v, other.v)
            and abs(self.t - other.t) < 1e-9
        )

    @property
    def speed(self) -> float:
        """Magnitude of the velocity vector [m/s]."""
        return float(np.linalg.norm(self.v))

    @property
    def radius(self) -> float:
        """Magnitude of the position vector [m]."""
        return float(np.linalg.norm(self.r))

    def copy(self) -> "StateVector":
        """Return a deep copy of this state vector."""
        return StateVector(r=self.r.copy(), v=self.v.copy(), t=self.t)


@dataclass
class OrbitalElements:
    """Classical orbital elements with respect to a central body.

    Parameters
    ----------
    a : float
        Semi-major axis [m] (negative if hyperbolic).
    e : float
        Eccentricity (0 ≤ e < 1 elliptic, e = 1 parabolic, e > 1 hyperbolic).
    i : float
        Inclination [rad].
    raan : float
        Right ascension of ascending node Ω [rad].
    argp : float
        Argument of periapsis ω [rad].
    nu : float
        True anomaly ν [rad] at epoch.
    mu : float
        Gravitational parameter [m³/s²] (default: Earth).
    """

    a: float
    e: float
    i: float
    raan: float
    argp: float
    nu: float
    mu: float = field(default=3.986004418e14)

    def __post_init__(self) -> None:
        """Validate element ranges."""
        if self.e < 0:
            raise ValueError(f"Eccentricity must be ≥ 0; got {self.e}")
        if self.a == 0:
            raise ValueError("Semi-major axis cannot be zero")
        if self.mu <= 0:
            raise ValueError(f"Gravitational parameter must be positive; got {self.mu}")

    def __repr__(self) -> str:
        return (
            f"OrbitalElements(a={self.a/1000:.1f} km, e={self.e:.4f}, "
            f"i={math.degrees(self.i):.2f}°, Ω={math.degrees(self.raan):.2f}°, "
            f"ω={math.degrees(self.argp):.2f}°, ν={math.degrees(self.nu):.2f}°)"
        )

    @property
    def is_elliptic(self) -> bool:
        """True if this is a bound (elliptic) orbit."""
        return 0.0 <= self.e < 1.0

    @property
    def is_hyperbolic(self) -> bool:
        """True if this is a hyperbolic orbit."""
        return self.e > 1.0

    @property
    def is_parabolic(self) -> bool:
        """True if this is a parabolic orbit (e ≈ 1)."""
        return abs(self.e - 1.0) < 1e-12

    @property
    def is_circular(self) -> bool:
        """True if this is a near-circular orbit (e ≈ 0)."""
        return self.e < 1e-8

    @property
    def is_equatorial(self) -> bool:
        """True if this is a near-equatorial orbit (i ≈ 0 or i ≈ π)."""
        return self.i < 1e-8 or abs(self.i - math.pi) < 1e-8

    @property
    def period(self) -> float:
        """Orbital period [s] (elliptic only; ``inf`` otherwise)."""
        if self.is_elliptic and self.a > 0:
            return 2.0 * math.pi * math.sqrt(self.a ** 3 / self.mu)
        return float("inf")

    @property
    def mean_motion(self) -> float:
        """Mean motion n = √(μ/a³) [rad/s] (elliptic only; ``nan`` otherwise)."""
        if self.is_elliptic and self.a > 0:
            return math.sqrt(self.mu / self.a ** 3)
        return float("nan")

    @property
    def p(self) -> float:
        """Semi-latus rectum [m]."""
        return self.a * (1.0 - self.e ** 2)

    @property
    def h(self) -> float:
        """Specific angular momentum magnitude [m²/s]."""
        return math.sqrt(self.mu * self.p)

    @property
    def perigee(self) -> float:
        """Periapsis radius [m]."""
        return self.a * (1.0 - self.e)

    @property
    def apogee(self) -> float:
        """Apoapsis radius [m] (``inf`` for hyperbolic/parabolic)."""
        if self.is_hyperbolic or self.is_parabolic:
            return float("inf")
        return self.a * (1.0 + self.e)

    @property
    def energy(self) -> float:
        """Specific orbital energy [J/kg]."""
        return -self.mu / (2.0 * self.a) if not math.isinf(self.a) else 0.0

    @property
    def orbit_type(self) -> str:
        """Human-readable orbit type string."""
        if self.is_parabolic:
            return "parabolic"
        if self.is_hyperbolic:
            return "hyperbolic"
        if self.is_circular:
            return "circular"
        return "elliptic"


# --------------------------------------------------------------------------- #
#  Conversions
# --------------------------------------------------------------------------- #
def rv_to_elements(state: StateVector, body: Body) -> OrbitalElements:
    """Convert a Cartesian state vector into classical orbital elements.

    Parameters
    ----------
    state : StateVector
        Position and velocity in the inertial frame.
    body : Body
        Central body whose gravity field defines the orbit.

    Returns
    -------
    OrbitalElements
        Classical orbital elements.

    Raises
    ------
    ValueError
        If position or angular momentum is zero (degenerate orbit).
    """
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
    """Convert classical orbital elements to a Cartesian state vector at ν.

    Parameters
    ----------
    elements : OrbitalElements
        Classical orbital elements.
    body : Body, optional
        Central body.  If None, uses ``elements.mu``.

    Returns
    -------
    StateVector
        Position and velocity in the inertial frame at the true anomaly ν.
    """
    mu = body.mu if body is not None else elements.mu
    e = elements.e
    nu = elements.nu
    a = elements.a
    p = elements.p

    # Radius in the perifocal frame
    r_pfq = p / (1.0 + e * math.cos(nu))
    # Handle parabolic
    if math.isinf(a):
        vmag = math.sqrt(2.0 * mu / r_pfq)  # energy = 0
    else:
        vmag = math.sqrt(abs(2.0 * mu / r_pfq - mu / a))

    r_pfq_vec = np.array([r_pfq * math.cos(nu), r_pfq * math.sin(nu), 0.0])
    # Velocity direction in perifocal: v_pfq = (mu/h) * [-sin ν, e + cos ν, 0]
    h = math.sqrt(mu * abs(p))
    v_pfq_vec = (mu / h) * np.array([-math.sin(nu), e + math.cos(nu), 0.0])

    # Rotation: PQW → ECI = R3(Ω) R1(i) R3(ω)
    from .frames import rot1, rot3
    R = rot3(elements.raan) @ rot1(elements.i) @ rot3(elements.argp)
    r_eci = R @ r_pfq_vec
    v_eci = R @ v_pfq_vec
    return StateVector(r=r_eci, v=v_eci, t=0.0)


def true_to_mean(nu: float, e: float) -> float:
    """Convert true anomaly ν to mean anomaly M [rad] (elliptic, hyperbolic, or parabolic).

    Parameters
    ----------
    nu : float
        True anomaly [rad].
    e : float
        Eccentricity.

    Returns
    -------
    float
        Mean anomaly M [rad].
    """
    if e < 1.0:
        E = 2.0 * math.atan2(math.sqrt(1.0 - e) * math.sin(nu / 2.0),
                             math.sqrt(1.0 + e) * math.cos(nu / 2.0))
        M = E - e * math.sin(E)
    elif e > 1.0:
        # Hyperbolic: check that ν is within the asymptotic limit
        nu_max = math.acos(-1.0 / e)
        if abs(nu) > nu_max:
            return float("nan")
        H = 2.0 * math.atanh(math.sqrt((e - 1.0) / (e + 1.0)) * math.tan(nu / 2.0))
        M = e * math.sinh(H) - H
    else:
        # Parabolic
        D = math.tan(nu / 2.0)
        M = D + D ** 3 / 3.0
    return M


def mean_to_true(M: float, e: float) -> float:
    """Convert mean anomaly M to true anomaly ν [rad].

    Handles elliptic (e < 1), hyperbolic (e > 1), and parabolic (e = 1) cases.

    Parameters
    ----------
    M : float
        Mean anomaly [rad].
    e : float
        Eccentricity.

    Returns
    -------
    float
        True anomaly ν [rad] in [0, 2π).
    """
    if e < 1.0:
        E = solve_kepler_e(M, e)
        nu = 2.0 * math.atan2(math.sqrt(1.0 + e) * math.sin(E / 2.0),
                              math.sqrt(1.0 - e) * math.cos(E / 2.0))
    elif e > 1.0:
        H = solve_kepler_h(M, e)
        nu = 2.0 * math.atan2(math.sqrt(e + 1.0) * math.sinh(H / 2.0),
                              math.sqrt(e - 1.0) * math.cosh(H / 2.0))
    else:
        # Parabolic: use Barker's equation (closed-form)
        D = solve_kepler_barker(0.0, M)
        nu = 2.0 * math.atan(D)
    # Wrap to [0, 2π)
    return math.fmod(nu + 2.0 * math.pi, 2.0 * math.pi)


def true_to_eccentric(nu: float, e: float) -> float:
    """Convert true anomaly ν to eccentric anomaly E (elliptic) or H (hyperbolic).

    Parameters
    ----------
    nu : float
        True anomaly [rad].
    e : float
        Eccentricity.

    Returns
    -------
    float
        Eccentric anomaly E [rad] (elliptic) or H [rad] (hyperbolic).
    """
    if e < 1.0:
        return 2.0 * math.atan2(math.sqrt(1.0 - e) * math.sin(nu / 2.0),
                                math.sqrt(1.0 + e) * math.cos(nu / 2.0))
    elif e > 1.0:
        return 2.0 * math.atanh(math.sqrt((e - 1.0) / (e + 1.0)) * math.tan(nu / 2.0))
    else:
        return math.tan(nu / 2.0)  # Barker anomaly D


def eccentric_to_true(E: float, e: float) -> float:
    """Convert eccentric anomaly E (or H for hyperbolic) to true anomaly ν.

    Parameters
    ----------
    E : float
        Eccentric anomaly E [rad] (elliptic) or H [rad] (hyperbolic).
    e : float
        Eccentricity.

    Returns
    -------
    float
        True anomaly ν [rad].
    """
    if e < 1.0:
        return 2.0 * math.atan2(math.sqrt(1.0 + e) * math.sin(E / 2.0),
                                math.sqrt(1.0 - e) * math.cos(E / 2.0))
    elif e > 1.0:
        return 2.0 * math.atan2(math.sqrt(e + 1.0) * math.sinh(E / 2.0),
                                math.sqrt(e - 1.0) * math.cosh(E / 2.0))
    else:
        return 2.0 * math.atan(E)  # parabolic: E is the Barker anomaly D