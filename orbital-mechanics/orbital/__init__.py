"""
orbital-mechanics — a pure-Python library for two-body orbital mechanics.

Modules
-------
elements     : classical Keplerian element ↔ state-vector conversions
twobody      : numerical propagation (RK4, Cowell, universal, J2 secular) and analytic
maneuvers    : Hohmann, bi-elliptic, Lambert, plane change, porkchop, Δv
perturbations: J2 secular drift and atmospheric drag (simplified)
groundtrack  : geocentric → ECEF → lat/lon (sub-satellite point), look angles
bodies       : predefined central bodies (Earth, Moon, Sun, Mars, ...)
kepler       : robust solvers for Kepler's equation (E, H, Barker, universal)
frames       : rotation matrices, Euler-angle transforms, ECI↔ECEF
"""
from .elements import (
    rv_to_elements,
    elements_to_rv,
    OrbitalElements,
    StateVector,
    true_to_mean,
    mean_to_true,
    true_to_eccentric,
    eccentric_to_true,
)
from .kepler import (
    solve_kepler_e,
    solve_kepler_h,
    solve_kepler_barker,
    solve_universal_kepler,
    stumpff_functions,
)
from .bodies import Body, EARTH, MOON, SUN, MARS, VENUS
from .twobody import (
    propagate_kepler,
    propagate_rk4,
    propagate_cowell,
    propagate_universal,
    propagate_j2_secular,
    multi_step_propagate,
)
from .maneuvers import (
    hohmann_transfer,
    bielliptic_transfer,
    lambert_izzo,
    compute_dv,
    plane_change_delta_v,
    combined_plane_change_delta_v,
    minimum_energy_tof,
    porkchop_data,
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
    # elements
    "rv_to_elements", "elements_to_rv", "OrbitalElements", "StateVector",
    "true_to_mean", "mean_to_true", "true_to_eccentric", "eccentric_to_true",
    # kepler
    "solve_kepler_e", "solve_kepler_h", "solve_kepler_barker",
    "solve_universal_kepler", "stumpff_functions",
    # bodies
    "Body", "EARTH", "MOON", "SUN", "MARS", "VENUS",
    # twobody
    "propagate_kepler", "propagate_rk4", "propagate_cowell",
    "propagate_universal", "propagate_j2_secular", "multi_step_propagate",
    # maneuvers
    "hohmann_transfer", "bielliptic_transfer", "lambert_izzo", "compute_dv",
    "plane_change_delta_v", "combined_plane_change_delta_v",
    "minimum_energy_tof", "porkchop_data",
    # groundtrack
    "eci_to_ecef", "ecef_to_latlon", "latlon_look_angles", "ground_track",
    # perturbations
    "j2_acceleration", "drag_acceleration",
    # frames
    "rot1", "rot2", "rot3", "eci_to_ecef_matrix",
]

__version__ = "2.0.0"