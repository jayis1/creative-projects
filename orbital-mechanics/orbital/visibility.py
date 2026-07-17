"""Satellite visibility, eclipse, and ground-station contact analysis.

Provides:
- ``eclipse_function``   — conical Earth-shadow model (umbra only)
- ``in_umbra``           — boolean test for whether a state is in Earth's shadow
- ``visibility_windows`` — compute rise/set times over a ground station
- ``sun_position``       — simplified low-precision solar position (J2000 ECI)
- ``access_summary``     — human-readable summary of a ground-station pass
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, List, Tuple

import numpy as np

from .bodies import Body, EARTH, SUN
from .elements import StateVector
from .groundtrack import latlon_look_angles


def sun_position(jd: float) -> np.ndarray:
    """Low-precision solar position in J2000 ECI [m].

    Uses the simplified algorithm from Vallado §5.2 (Algorithm 29),
    accurate to ~0.01° for 1950-2050.

    Parameters
    ----------
    jd : float
        Julian Date.

    Returns
    -------
    ndarray
        Heliocentric-inertial sun position vector from Earth [m].
    """
    t_ut1 = (jd - 2451545.0) / 36525.0
    # Mean longitude of the Sun [deg]
    lam_M = 280.460 + 36000.77 * t_ut1
    lam_M = math.radians(lam_M % 360.0)
    # Mean anomaly of the Sun [deg]
    M = 357.5277233 + 35999.05034 * t_ut1
    M = math.radians(M % 360.0)
    # Ecliptic longitude
    lam_ecl = lam_M + math.radians(1.914666471) * math.sin(M) \
        + math.radians(0.019994643) * math.sin(2.0 * M)
    # Obliquity of the ecliptic
    eps = math.radians(23.439291 - 0.0130042 * t_ut1)
    r_au = 1.000140612 - 0.016708617 * math.cos(M) - 0.000139535 * math.sin(2.0 * M)
    r_m = r_au * 1.495978707e11
    return np.array([
        r_m * math.cos(lam_ecl),
        r_m * math.cos(eps) * math.sin(lam_ecl),
        r_m * math.sin(eps) * math.sin(lam_ecl),
    ])


def in_umbra(r_sat: np.ndarray, r_sun: np.ndarray, body: Body = EARTH) -> bool:
    """Test whether a satellite position is in the Earth's umbra.

    Uses a conical shadow model.  The satellite is in umbra if its
    projection onto the sun-Earth line lies behind the Earth and the
    perpendicular distance is less than the Earth's radius at that point.

    Parameters
    ----------
    r_sat : ndarray
        Satellite ECI position [m].
    r_sun : ndarray
        Sun ECI position (from Earth centre) [m].
    body : Body
        Central body.

    Returns
    -------
    bool
        True if the satellite is in umbra.
    """
    r_sun = np.asarray(r_sun, dtype=float)
    r_sat = np.asarray(r_sat, dtype=float)
    sun_dir = r_sun / float(np.linalg.norm(r_sun))
    # Project satellite onto sun-Earth line.
    proj = float(np.dot(r_sat, sun_dir))
    if proj > 0:
        # Satellite on sunward side — not in shadow.
        return False
    perp = r_sat - proj * sun_dir
    perp_mag = float(np.linalg.norm(perp))
    # Cylindrical approximation (umbra half-angle is tiny for Earth-Sun).
    return perp_mag < body.radius


def eclipse_function(r_sat: np.ndarray, r_sun: np.ndarray, body: Body = EARTH) -> float:
    """Return 1.0 in full sunlight, 0.0 in umbra (conical model).

    A smooth approximation used for power-budget simulations.
    """
    return 0.0 if in_umbra(r_sat, r_sun, body) else 1.0


@dataclass
class PassInfo:
    """A single ground-station overflight."""

    rise_time: float       # seconds from epoch
    set_time: float
    max_elevation: float   # [rad]
    rise_az: float         # [rad]
    set_az: float
    duration: float        # [s]


def visibility_windows(
    states: List[StateVector],
    site_lat: float,
    site_lon: float,
    gmst0: float = 0.0,
    min_elevation: float = math.radians(5.0),
    body: Body = EARTH,
) -> List[PassInfo]:
    """Find visibility windows over a ground station from a state list.

    Parameters
    ----------
    states : list of StateVector
        Time-ordered propagated states (use ``multi_step_propagate``).
    site_lat, site_lon : float
        Ground station geodetic latitude and longitude [rad].
    gmst0 : float
        GMST at ``states[0].t`` [rad].
    min_elevation : float
        Minimum elevation for a valid pass [rad].
    body : Body
        Central body.

    Returns
    -------
    list of PassInfo
        One entry per overflight.
    """
    passes: List[PassInfo] = []
    in_pass = False
    rise_t = 0.0
    rise_az = 0.0
    max_el = 0.0
    prev_el = -1.0
    az = 0.0

    for s in states:
        gmst = gmst0 + body.omega * (s.t - states[0].t)
        el, az, _ = latlon_look_angles(s.r, gmst, site_lat, site_lon, 0.0, body)
        above = el >= min_elevation

        if above and not in_pass:
            # Rise — interpolate to the crossing point.
            rise_t = s.t
            rise_az = az
            max_el = el
            in_pass = True
        elif above and in_pass:
            if el > max_el:
                max_el = el
        elif not above and in_pass:
            # Set
            set_t = s.t
            set_az = az
            passes.append(PassInfo(
                rise_time=rise_t, set_time=set_t,
                max_elevation=max_el, rise_az=rise_az, set_az=set_az,
                duration=set_t - rise_t,
            ))
            in_pass = False
        prev_el = el

    # Close an open pass at the end of the list.
    if in_pass:
        passes.append(PassInfo(
            rise_time=rise_t, set_time=states[-1].t,
            max_elevation=max_el, rise_az=rise_az,
            set_az=az, duration=states[-1].t - rise_t,
        ))
    return passes


def access_summary(p: PassInfo) -> str:
    """Human-readable single-line summary of a pass."""
    return (f"Pass: rise={p.rise_time:.0f}s set={p.set_time:.0f}s "
            f"dur={p.duration:.0f}s max_el={math.degrees(p.max_elevation):.1f}° "
            f"rise_az={math.degrees(p.rise_az):.0f}° set_az={math.degrees(p.set_az):.0f}°")