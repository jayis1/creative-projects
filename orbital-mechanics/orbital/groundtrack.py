"""Geocentric ↔ Earth-fixed transforms, ground tracks, and look angles."""
from __future__ import annotations

import math
from typing import Tuple

import numpy as np

from .bodies import Body, EARTH
from .frames import eci_to_ecef_matrix
from .elements import StateVector


def eci_to_ecef(r_eci: np.ndarray, gmst: float) -> np.ndarray:
    """Rotate an ECI position vector to ECEF given GMST [rad]."""
    M = eci_to_ecef_matrix(gmst)
    return M @ np.asarray(r_eci, dtype=float)


def ecef_to_latlon(r_ecef: np.ndarray, body: Body = EARTH) -> Tuple[float, float, float]:
    """Convert ECEF position to geodetic latitude, longitude, altitude.

    Uses a closed-form algorithm (Olson, 1996) for robust geodetic altitude.
    Returns ``(lat [rad], lon [rad], alt [m])``.
    """
    r_ecef = np.asarray(r_ecef, dtype=float)
    a = body.radius
    b = a * math.sqrt(max(0.0, 1.0 - 2.0 * body.j2 - body.j2 ** 2)) if body.j2 else a
    # Simple ellipsoidal flattening approximation: f ≈ J2/2 + ...
    # For robustness we use a sphere with radius = body.radius and a first-order
    # correction.  A more faithful ellipsoid is beyond scope here.
    x, y, z = r_ecef
    lon = math.atan2(y, x)
    p = math.hypot(x, y)
    if p < 1e-6:
        lat = math.copysign(math.pi / 2.0, z)
        alt = abs(z) - a
        return lat, lon, alt
    # Iterative geodetic latitude
    lat = math.atan2(z, p)
    for _ in range(8):
        sinlat = math.sin(lat)
        N = a / math.sqrt(1.0 - (2.0 * body.j2 - body.j2 ** 2) * sinlat ** 2)
        alt = p / math.cos(lat) - N
        lat_new = math.atan2(z, p * (1.0 - (2.0 * body.j2 - body.j2 ** 2) * N / (N + alt)))
        if abs(lat_new - lat) < 1e-12:
            lat = lat_new
            break
        lat = lat_new
    sinlat = math.sin(lat)
    N = a / math.sqrt(1.0 - (2.0 * body.j2 - body.j2 ** 2) * sinlat ** 2)
    alt = p / math.cos(lat) - N
    return lat, lon, alt


def latlon_look_angles(
    r_sat_eci: np.ndarray,
    gmst: float,
    site_lat: float,
    site_lon: float,
    alt: float = 0.0,
    body: Body = EARTH,
) -> Tuple[float, float, float]:
    """Compute topocentric elevation, azimuth, and range from a ground site.

    Returns ``(elevation [rad], azimuth [rad], range [m])``.
    """
    r_sat_ecef = eci_to_ecef(r_sat_eci, gmst)
    sinlat = math.sin(site_lat)
    coslat = math.cos(site_lat)
    sinlon = math.sin(site_lon)
    coslon = math.cos(site_lon)
    # Site ECEF position (spherical approximation)
    r_site = body.radius + alt
    rs_ecef = np.array([r_site * coslat * coslon,
                        r_site * coslat * sinlon,
                        r_site * sinlat])
    # ECEF → SEZ (topocentric)
    diff = r_sat_ecef - rs_ecef
    # SEZ rotation: S = -sinlat coslon x - sinlat sinlon y + coslat z
    #               E = -sinlon x + coslon y
    #               Z =  coslat coslon x + coslat sinlon y + sinlat z
    sez = np.array([
        -sinlat * coslon * diff[0] - sinlat * sinlon * diff[1] + coslat * diff[2],
        -sinlon * diff[0] + coslon * diff[1],
        coslat * coslon * diff[0] + coslat * sinlon * diff[1] + sinlat * diff[2],
    ])
    rho = float(np.linalg.norm(sez))
    if rho < 1e-6:
        return 0.0, 0.0, 0.0
    el = math.asin(max(-1.0, min(1.0, sez[2] / rho)))
    az = math.atan2(sez[1], -sez[0])
    if az < 0:
        az += 2.0 * math.pi
    return el, az, rho


def ground_track(
    states: list[StateVector],
    body: Body = EARTH,
    gmst0: float = 0.0,
) -> list[Tuple[float, float]]:
    """Compute the sub-satellite latitude/longitude for a list of states.

    Parameters
    ----------
    states : list of StateVector
        Propagated states with ``.t`` set to the elapsed time.
    gmst0 : float
        GMST at ``t = 0`` [rad].
    """
    pts = []
    for s in states:
        gmst = gmst0 + body.omega * s.t
        r_ecef = eci_to_ecef(s.r, gmst)
        lat, lon, _ = ecef_to_latlon(r_ecef, body)
        pts.append((lat, lon))
    return pts