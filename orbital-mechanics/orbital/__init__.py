"""
orbital-mechanics — a pure-Python library for two-body orbital mechanics.

Modules
-------
elements      : classical Keplerian element ↔ state-vector conversions
twobody       : numerical propagation (RK4, Cowell, universal, J2 secular) and analytic
adaptive      : adaptive-step propagators (RKF45, Bulirsch-Stoer)
maneuvers     : Hohmann, bi-elliptic, Lambert, plane change, porkchop, Δv
perturbations : J2 secular drift and atmospheric drag (simplified)
groundtrack   : geocentric → ECEF → lat/lon (sub-satellite point), look angles
bodies        : predefined central bodies (Earth, Moon, Sun, Mars, ...)
kepler        : robust solvers for Kepler's equation (E, H, Barker, universal)
frames        : rotation matrices, Euler-angle transforms, ECI↔ECEF
tle           : NORAD Two-Line Element set parser
visibility    : eclipse/umbra, ground-station visibility windows, sun position
mission       : repeat-ground-track, frozen orbits, Lagrange points, station-keeping
config        : YAML/JSON/TOML configuration loading
io_csv        : CSV/JSON export of state series and ground tracks
viz           : ASCII-art orbit, ground-track, and porkchop visualisations
logging_utils : structured logging and timing helpers
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
from .adaptive import (
    propagate_rkf45,
    propagate_bs,
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
from .tle import TLE, parse_tle, parse_tle_set
from .visibility import (
    sun_position,
    in_umbra,
    eclipse_function,
    visibility_windows,
    access_summary,
    PassInfo,
)
from .mission import (
    repeat_groundtrack_orbit,
    frozen_orbit_argp,
    lagrange_points,
    stationkeeping_delta_v,
    RepeatGroundTrack,
    LagrangePoint,
)
from .config import (
    OrbitConfig,
    SatelliteConfig,
    PropagationConfig,
    GroundStationConfig,
    OutputConfig,
    load_config,
)
from .io_csv import states_to_csv, groundtrack_to_csv, states_to_json
from .viz import ascii_orbit_xy, ascii_ground_track, ascii_porkchop
from .logging_utils import get_logger, set_log_level, timed

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
    # adaptive
    "propagate_rkf45", "propagate_bs",
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
    # tle
    "TLE", "parse_tle", "parse_tle_set",
    # visibility
    "sun_position", "in_umbra", "eclipse_function",
    "visibility_windows", "access_summary", "PassInfo",
    # mission
    "repeat_groundtrack_orbit", "frozen_orbit_argp", "lagrange_points",
    "stationkeeping_delta_v", "RepeatGroundTrack", "LagrangePoint",
    # config
    "OrbitConfig", "SatelliteConfig", "PropagationConfig",
    "GroundStationConfig", "OutputConfig", "load_config",
    # io
    "states_to_csv", "groundtrack_to_csv", "states_to_json",
    # viz
    "ascii_orbit_xy", "ascii_ground_track", "ascii_porkchop",
    # logging
    "get_logger", "set_log_level", "timed",
]

__version__ = "3.0.0"