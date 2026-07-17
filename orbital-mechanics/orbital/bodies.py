"""Predefined celestial bodies used as the central gravitational source."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Body:
    """A point-mass central body with physical parameters.

    Attributes
    ----------
    name : str
        Human-readable name.
    mu : float
        Standard gravitational parameter GM [m^3 / s^2].
    radius : float
        Equatorial radius [m].
    j2 : float
        Second zonal harmonic (dimensionless).  Zero for bodies without an
        oblateness model.
    omega : float
        Sidereal rotation rate [rad / s].  Zero for non-rotating bodies.
    """

    name: str
    mu: float
    radius: float
    j2: float = 0.0
    omega: float = 0.0


EARTH = Body(
    name="Earth",
    mu=3.986004418e14,
    radius=6_378_136.3,
    j2=1.082626173e-3,
    omega=7.2921159e-5,
)
MOON = Body(
    name="Moon",
    mu=4.9048695e12,
    radius=1_737_400.0,
    j2=2.03e-4,
    omega=2.6617e-6,
)
SUN = Body(
    name="Sun",
    mu=1.32712440018e20,
    radius=6.957e8,
    j2=2.0e-7,
    omega=2.9e-6,
)
MARS = Body(
    name="Mars",
    mu=4.282837e13,
    radius=3_389_500.0,
    j2=1.960454e-3,
    omega=7.0882181e-5,
)
VENUS = Body(
    name="Venus",
    mu=3.24858592e14,
    radius=6_051_800.0,
    j2=4.0e-6,
    omega=-2.9925e-7,
)