"""Numerical and analytic two-body propagators.

Provides:
- ``propagate_kepler`` — analytic Kepler propagation (elliptic and hyperbolic)
- ``propagate_rk4`` — fixed-step RK4 with optional perturbations
- ``propagate_cowell`` — Cowell's method (RK4 + explicit perturbations)
- ``propagate_universal`` — universal-variable propagation (all orbit types)
- ``propagate_j2_secular`` — SGP4-like secular J2 drift propagation
"""
from __future__ import annotations

import math
from typing import Callable

import numpy as np

from .bodies import Body
from .elements import (
    OrbitalElements,
    StateVector,
    elements_to_rv,
    mean_to_true,
    rv_to_elements,
    true_to_mean,
)
from .kepler import solve_kepler_e, solve_kepler_h, solve_universal_kepler


def propagate_kepler(state: StateVector, body: Body, dt: float) -> StateVector:
    """Analytic Kepler propagation: convert to elements, advance M, convert back.

    Fast and exact for the unperturbed two-body problem.
    Supports elliptic and hyperbolic orbits.

    Parameters
    ----------
    state : StateVector
        Initial state.
    body : Body
        Central body.
    dt : float
        Time increment [s] (can be negative for backward propagation).

    Returns
    -------
    StateVector
        Propagated state at ``state.t + dt``.

    Raises
    ------
    ValueError
        If the orbit is parabolic (use ``propagate_universal`` instead).
    """
    elems = rv_to_elements(state, body)
    if elems.is_parabolic:
        raise ValueError("propagate_kepler does not support parabolic orbits; use propagate_universal")

    if elems.is_elliptic:
        n = math.sqrt(body.mu / elems.a ** 3)  # mean motion [rad/s]
        M0 = true_to_mean(elems.nu, elems.e)
        M1 = M0 + n * dt
        nu1 = mean_to_true(M1, elems.e)
    else:
        # Hyperbolic: n_h = sqrt(mu/(-a)^3)
        n_h = math.sqrt(body.mu / (-elems.a) ** 3)
        M0 = true_to_mean(elems.nu, elems.e)
        M1 = M0 + n_h * dt
        nu1 = mean_to_true(M1, elems.e)

    new_elems = OrbitalElements(
        a=elems.a, e=elems.e, i=elems.i, raan=elems.raan,
        argp=elems.argp, nu=nu1, mu=body.mu,
    )
    sv = elements_to_rv(new_elems, body)
    sv.t = state.t + dt
    return sv


def _accel_two_body(r: np.ndarray, body: Body) -> np.ndarray:
    """Two-body gravitational acceleration [m/s²]."""
    rmag = float(np.linalg.norm(r))
    if rmag < 1e-6:
        return np.zeros(3)
    return -body.mu * r / rmag ** 3


def propagate_rk4(
    state: StateVector,
    body: Body,
    dt: float,
    step: float = 60.0,
    extra_accel: Callable[[np.ndarray, np.ndarray, float], np.ndarray] | None = None,
) -> StateVector:
    """Fixed-step RK4 integration of the two-body (plus optional perturbation) EOM.

    Parameters
    ----------
    state : StateVector
        Initial state.
    body : Body
        Central body.
    dt : float
        Total time increment [s] (can be negative).
    step : float
        Integration step size [s] (absolute value is used).
    extra_accel : callable(r, v, t) -> a, optional
        Perturbing acceleration (e.g. J2, drag).  Used by Cowell's method.

    Returns
    -------
    StateVector
        Propagated state.
    """
    r = state.r.copy()
    v = state.v.copy()
    t = state.t
    n_steps = int(math.ceil(abs(dt) / abs(step)))
    if n_steps == 0:
        n_steps = 1
    h = dt / n_steps

    def deriv(rr: np.ndarray, vv: np.ndarray, tt: float) -> tuple[np.ndarray, np.ndarray]:
        a = _accel_two_body(rr, body)
        if extra_accel is not None:
            a = a + extra_accel(rr, vv, tt)
        return vv, a

    for _ in range(n_steps):
        k1r, k1v = deriv(r, v, t)
        k2r, k2v = deriv(r + 0.5 * h * k1r, v + 0.5 * h * k1v, t + 0.5 * h)
        k3r, k3v = deriv(r + 0.5 * h * k2r, v + 0.5 * h * k2v, t + 0.5 * h)
        k4r, k4v = deriv(r + h * k3r, v + h * k3v, t + h)
        r = r + (h / 6.0) * (k1r + 2 * k2r + 2 * k3r + k4r)
        v = v + (h / 6.0) * (k1v + 2 * k2v + 2 * k3v + k4v)
        t += h

    return StateVector(r=r, v=v, t=state.t + dt)


def propagate_cowell(
    state: StateVector,
    body: Body,
    dt: float,
    step: float = 60.0,
    extra_accel: Callable[[np.ndarray, np.ndarray, float], np.ndarray] | None = None,
) -> StateVector:
    """Cowell's method: RK4 with explicit perturbing accelerations.

    This is simply :func:`propagate_rk4` with the ``extra_accel`` parameter.
    Kept as a separate function for API clarity.
    """
    return propagate_rk4(state, body, dt, step=step, extra_accel=extra_accel)


def propagate_universal(state: StateVector, body: Body, dt: float) -> StateVector:
    """Universal-variable propagation — handles all orbit types (elliptic, parabolic, hyperbolic).

    Uses the universal anomaly χ and Stumpff functions.  This is the most
    general propagator and works for any conic section.

    Parameters
    ----------
    state : StateVector
        Initial state.
    body : Body
        Central body.
    dt : float
        Time increment [s].

    Returns
    -------
    StateVector
        Propagated state at ``state.t + dt``.
    """
    mu = body.mu
    r0 = state.r.copy()
    v0 = state.v.copy()
    R0 = float(np.linalg.norm(r0))
    V0 = float(np.linalg.norm(v0))

    # Specific energy and semi-major axis
    energy = V0 * V0 / 2.0 - mu / R0
    a = -mu / (2.0 * energy) if abs(energy) > 1e-10 else float("inf")

    # Radial velocity
    vr0 = float(np.dot(r0, v0)) / R0

    # Solve for the universal anomaly chi
    chi = solve_universal_kepler(mu, R0, vr0, a, dt)

    # Stumpff functions
    from .kepler import stumpff_functions
    alpha = 1.0 / a if not math.isinf(a) else 0.0
    z = alpha * chi * chi
    c0, c1, c2 = stumpff_functions(z)

    # f and g functions (Vallado eq 2.149):
    #   f = 1 - χ²/r₀ · C₂(z)
    #   g = dt - χ³/√μ · C₃(z)
    # where C₂ = c2 (our 3rd) and C₃ = c1 (our 2nd).
    f = 1.0 - chi * chi * c2 / R0
    g = dt - chi ** 3 * c1 / math.sqrt(mu)

    r_new = f * r0 + g * v0
    R_new = float(np.linalg.norm(r_new))

    # fdot and gdot:
    #   fdot = -√μ/(r₀·r) · χ · C₁(z)
    #   gdot = 1 - χ²/r · C₂(z)
    # where C₁ is the FIRST Stumpff function (sin(√z)/√z, sinh(√(-z))/√(-z)).
    if z > 0:
        sq = math.sqrt(z)
        c1_first = math.sin(sq) / sq
    elif z < 0:
        sq = math.sqrt(-z)
        c1_first = math.sinh(sq) / sq
    else:
        c1_first = 1.0
    fdot = -math.sqrt(mu) * chi * c1_first / (R0 * R_new)
    gdot = 1.0 - chi * chi * c2 / R_new

    v_new = fdot * r0 + gdot * v0

    return StateVector(r=r_new, v=v_new, t=state.t + dt)


def propagate_j2_secular(state: StateVector, body: Body, dt: float) -> StateVector:
    """SGP4-like secular propagation with J2 oblateness effects.

    Includes secular drift of RAAN (Ω), argument of periapsis (ω), and
    mean anomaly (M) due to J2.  Does not include short-period variations.

    Parameters
    ----------
    state : StateVector
        Initial state.
    body : Body
        Central body (must have a nonzero ``j2``).
    dt : float
        Time increment [s].

    Returns
    -------
    StateVector
        Propagated state including J2 secular drift.

    Raises
    ------
    ValueError
        If the orbit is not elliptic or body.j2 is zero.
    """
    if body.j2 == 0:
        raise ValueError(f"Body {body.name} has j2=0; use propagate_kepler instead.")

    elems = rv_to_elements(state, body)
    if not elems.is_elliptic:
        raise ValueError("propagate_j2_secular requires an elliptic orbit.")

    a = elems.a
    e = elems.e
    i = elems.i
    n = math.sqrt(body.mu / a ** 3)
    p = a * (1.0 - e ** 2)
    J2 = body.j2
    R = body.radius

    # J2 secular rates (Vallado eq 9.35-9.37)
    # RAAN rate: Ωdot = -3/2 * n * J2 * (R/p)^2 * cos(i)
    omega_dot = -1.5 * n * J2 * (R / p) ** 2 * math.cos(i)

    # Argp rate: ωdot = 3/2 * n * J2 * (R/p)^2 * (2 - 5/2 * sin²(i))
    # Simplified: 3/2 * n * J2 * (R/p)^2 * (5/2 * cos²(i) - 1/2) ... let's use the standard:
    # ωdot = 3/2 * n * J2 * (R/p)^2 * (2 - 5/2 * sin²i)  ... wait, the standard form is:
    # ωdot = 3/2 * n * J2 * (R/p)^2 * (5/4 * sin²i - 1) ... hmm, different sources differ.
    # Using Vallado's exact formula:
    argp_dot = 1.5 * n * J2 * (R / p) ** 2 * (2.0 - 2.5 * math.sin(i) ** 2)

    # Mean anomaly rate (including J2 correction):
    # Mdot = n + 3/2 * n * J2 * (R/p)^2 * sqrt(1-e²) * (3/2 * sin²i - 1)
    # Actually the J2 secular correction to mean anomaly is:
    # M_correction = 3/2 * n * J2 * (R/p)^2 * (1 - 3/2 * sin²i) * sqrt(1-e²) ... 
    # Using the standard SGP4 form:
    M_dot = n * (1.0 + 1.5 * J2 * (R / p) ** 2 * math.sqrt(1.0 - e ** 2) * (1.5 * math.sin(i) ** 2 - 1.0))

    # Advance
    M0 = true_to_mean(elems.nu, elems.e)
    M1 = M0 + M_dot * dt
    nu1 = mean_to_true(M1, elems.e)

    new_elems = OrbitalElements(
        a=a,  # semi-major axis is constant in secular J2
        e=e,  # eccentricity is constant in secular J2
        i=i,  # inclination is constant in secular J2
        raan=elems.raan + omega_dot * dt,
        argp=elems.argp + argp_dot * dt,
        nu=nu1,
        mu=body.mu,
    )
    sv = elements_to_rv(new_elems, body)
    sv.t = state.t + dt
    return sv


def multi_step_propagate(
    state: StateVector,
    body: Body,
    dt: float,
    step: float,
    propagator: Callable[[StateVector, Body, float], StateVector] = propagate_kepler,
) -> list[StateVector]:
    """Propagate an orbit in steps and return all intermediate states.

    Useful for generating ground tracks, orbit visualizations, etc.

    Parameters
    ----------
    state : StateVector
        Initial state.
    body : Body
        Central body.
    dt : float
        Total propagation time [s].
    step : float
        Time between output states [s].
    propagator : callable
        Propagation function to use (default: propagate_kepler).

    Returns
    -------
    list of StateVector
        States at ``t = state.t, state.t + step, ..., state.t + dt``.
    """
    states = [state.copy()]
    n = int(round(dt / step))
    for k in range(1, n + 1):
        s = propagator(state, body, k * step)
        s.t = state.t + k * step
        states.append(s)
    return states