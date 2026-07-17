"""Numerical and analytic two-body propagators."""
from __future__ import annotations

import math
from typing import Callable

import numpy as np

from .bodies import Body, EARTH
from .elements import (
    OrbitalElements,
    StateVector,
    elements_to_rv,
    mean_to_true,
    rv_to_elements,
    true_to_mean,
)
from .kepler import solve_kepler_e


def propagate_kepler(state: StateVector, body: Body, dt: float) -> StateVector:
    """Analytic Kepler propagation: convert to elements, advance M, convert back.

    Fast and exact for the unperturbed two-body problem.
    """
    elems = rv_to_elements(state, body)
    if not elems.is_elliptic:
        raise ValueError("propagate_kepler currently supports elliptic orbits only.")
    n = math.sqrt(body.mu / elems.a ** 3)  # mean motion [rad/s]
    M0 = true_to_mean(elems.nu, elems.e)
    M1 = M0 + n * dt
    nu1 = mean_to_true(M1, elems.e)
    new_elems = OrbitalElements(
        a=elems.a, e=elems.e, i=elems.i, raan=elems.raan,
        argp=elems.argp, nu=nu1, mu=body.mu,
    )
    sv = elements_to_rv(new_elems, body)
    sv.t = state.t + dt
    return sv


def _accel_two_body(r: np.ndarray, body: Body) -> np.ndarray:
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
    extra_accel : callable(r, v, t) -> a
        Optional perturbing acceleration (e.g. J2, drag).  Used by Cowell.
    """
    r = state.r.copy()
    v = state.v.copy()
    t = state.t
    n_steps = int(math.ceil(abs(dt) / abs(step)))
    h = dt / n_steps if n_steps else dt

    def deriv(rr, vv, tt):
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
    """Cowell's method: RK4 with explicit perturbing accelerations."""
    return propagate_rk4(state, body, dt, step=step, extra_accel=extra_accel)