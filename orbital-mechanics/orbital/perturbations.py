"""Perturbation accelerations for use with Cowell propagation."""
from __future__ import annotations

import math

import numpy as np

from .bodies import Body, EARTH


def j2_acceleration(r: np.ndarray, body: Body = EARTH) -> np.ndarray:
    """J2 oblateness perturbation acceleration [m/s^2].

    Reference: Vallado Eq.(8.56).
    """
    r = np.asarray(r, dtype=float)
    rmag = float(np.linalg.norm(r))
    if rmag < 1e-6:
        return np.zeros(3)
    x, y, z = r
    r2 = rmag * rmag
    factor = -1.5 * body.j2 * body.mu * body.radius ** 2 / r2 ** 2.5
    term = 5.0 * (z / rmag) ** 2
    ax = factor * x * (1.0 - term)
    ay = factor * y * (1.0 - term)
    az = factor * z * (3.0 - term)
    return np.array([ax, ay, az])


def drag_acceleration(
    r: np.ndarray,
    v: np.ndarray,
    body: Body = EARTH,
    Cd: float = 2.2,
    area: float = 1.0,
    mass: float = 1000.0,
    rho0: float = 3.6e-13,
    H: float = 8_500.0,
) -> np.ndarray:
    """Exponential-atmosphere drag acceleration [m/s^2].

    Parameters
    ----------
    Cd : float
        Drag coefficient.
    area : float
        Cross-sectional area [m^2].
    mass : float
        Spacecraft mass [kg].
    rho0 : float
        Reference density at ``body.radius`` [kg/m^3].
    H : float
        Scale height [m].
    """
    r = np.asarray(r, dtype=float)
    v = np.asarray(v, dtype=float)
    rmag = float(np.linalg.norm(r))
    alt = rmag - body.radius
    if alt < 0:
        alt = 0.0
    rho = rho0 * math.exp(-alt / H)
    vmag = float(np.linalg.norm(v))
    if vmag < 1e-6:
        return np.zeros(3)
    return -0.5 * rho * vmag * (Cd * area / mass) * v