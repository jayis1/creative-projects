"""
orbital-mechanics — a pure-Python library for two-body orbital mechanics.

Modules
-------
elements     : classical Keplerian element ↔ state-vector conversions
twobody      : numerical propagation (RK4, Cowell) and analytic propagation
maneuvers    : Hohmann, bi-elliptic, and generalized Lambert transfers
perturbations: J2 secular drift and atmospheric drag (simplified)
groundtrack  : geocentric → ECEF → lat/lon (sub-satellite point), look angles
bodies       : predefined central bodies (Earth, Moon, Sun, Mars, ...)
kepler       : robust solvers for Kepler's equation (E, H, and the unified form)
frames       : rotation matrices, Euler-angle transforms, ECI↔ECEF
"""
from .elements import (
    rv_to_elements,
    elements_to_rv,
    OrbitalElements,
    StateVector,
)
from .kepler import solve_kepler_e, solve_kepler_h, solve_universal_kepler
from .bodies import Body, EARTH, MOON, SUN, MARS, VENUS
from .twobody import propagate_kepler, propagate_rk4, propagate_cowell
from .maneuvers import (
    hohmann_transfer,
    bielliptic_transfer,
    lambert_izzo,
    compute_dv,
)
from .groundtrack import (
    eci_to_ecef,
    ecef_to_latlon,
    latlon_look_angles,
    ground_track,
)
from .perturbations import j2_acceleration, drag_acceleration
from .frames import rot1, rot2, rot3, eci_to_ecef_matrix

__all__ = [
    "rv_to_elements", "elements_to_rv", "OrbitalElements", "StateVector",
    "solve_kepler_e", "solve_kepler_h", "solve_universal_kepler",
    "Body", "EARTH", "MOON", "SUN", "MARS", "VENUS",
    "propagate_kepler", "propagate_rk4", "propagate_cowell",
    "hohmann_transfer", "bielliptic_transfer", "lambert_izzo", "compute_dv",
    "eci_to_ecef", "ecef_to_latlon", "latlon_look_angles", "ground_track",
    "j2_acceleration", "drag_acceleration",
    "rot1", "rot2", "rot3", "eci_to_ecef_matrix",
]

__version__ = "1.0.0"