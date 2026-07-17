"""Elementary rotation matrices and ECI↔ECEF frame transforms."""
from __future__ import annotations

import math
from typing import Sequence

import numpy as np


def rot1(angle: float) -> np.ndarray:
    """Rotation about the x-axis by ``angle`` radians (3×3)."""
    c, s = math.cos(angle), math.sin(angle)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]], dtype=float)


def rot2(angle: float) -> np.ndarray:
    """Rotation about the y-axis by ``angle`` radians (3×3)."""
    c, s = math.cos(angle), math.sin(angle)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]], dtype=float)


def rot3(angle: float) -> np.ndarray:
    """Rotation about the z-axis by ``angle`` radians (3×3)."""
    c, s = math.cos(angle), math.sin(angle)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], dtype=float)


def eci_to_ecef_matrix(gmst: float, xp: float = 0.0, yp: float = 0.0) -> np.ndarray:
    """Build the ECI → ECEF rotation matrix.

    Parameters
    ----------
    gmst : float
        Greenwich Mean Sidereal Time [rad].
    xp, yp : float
        Polar-motion offsets [rad].  Default 0 (negligible for most uses).
    """
    # Rotation by GMST about z, followed by polar motion (rot1/rot2 of xp/yp).
    r = rot3(gmst)
    if xp or yp:
        r = rot1(yp) @ rot2(xp) @ r
    return r


def apply_matrix(M: np.ndarray, v: Sequence[float]) -> np.ndarray:
    """Apply rotation matrix ``M`` to vector ``v``; returns a new ndarray."""
    return M @ np.asarray(v, dtype=float)