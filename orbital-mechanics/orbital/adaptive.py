"""Adaptive-step numerical propagators for high-accuracy orbit propagation.

Provides:
- ``propagate_rkf45`` — Runge-Kutta-Fehlberg 4(5) with adaptive step control
- ``propagate_dop853`` — Dormand-Prince 8(5,3) with dense output (optional)
- ``propagate_bs``    — Bulirsch-Stoer extrapolation (very high accuracy)

These are ideal when perturbations (J2, drag, third-body) demand
variable step sizes that shrink near periapsis and grow near apoapsis.
"""
from __future__ import annotations

import math
from typing import Callable, Sequence

import numpy as np

from .bodies import Body
from .elements import StateVector

# Type alias for a perturbing acceleration function.
AccelFn = Callable[[np.ndarray, np.ndarray, float], np.ndarray]


def _two_body_accel(r: np.ndarray, body: Body) -> np.ndarray:
    rmag = float(np.linalg.norm(r))
    if rmag < 1e-6:
        return np.zeros(3)
    return -body.mu * r / rmag ** 3


def _deriv(r: np.ndarray, v: np.ndarray, t: float,
           body: Body, extra: AccelFn | None) -> tuple[np.ndarray, np.ndarray]:
    a = _two_body_accel(r, body)
    if extra is not None:
        a = a + np.asarray(extra(r, v, t), dtype=float)
    return v, a


def propagate_rkf45(
    state: StateVector,
    body: Body,
    dt: float,
    rtol: float = 1e-9,
    atol: float = 1e-12,
    h_init: float = 60.0,
    h_min: float = 0.1,
    h_max: float = 600.0,
    extra_accel: AccelFn | None = None,
) -> StateVector:
    """Adaptive Runge-Kutta-Fehlberg 4(5) propagation.

    Uses the classic RKF45 coefficients of Fehlberg with embedded 4th/5th
    error estimation.  Step size is adapted to meet the mixed
    ``(rtol, atol)`` tolerance on the 6-D state vector.

    Parameters
    ----------
    state : StateVector
        Initial state.
    body : Body
        Central body.
    dt : float
        Total time increment [s] (may be negative).
    rtol, atol : float
        Relative and absolute tolerances.
    h_init : float
        Initial step size [s].
    h_min, h_max : float
        Bounds on the step size [s].
    extra_accel : callable, optional
        Perturbing acceleration ``a = f(r, v, t)``.

    Returns
    -------
    StateVector
        Propagated state.
    """
    y = np.concatenate([state.r.copy(), state.v.copy()]).astype(float)
    t = state.t
    direction = 1.0 if dt >= 0 else -1.0
    target = state.t + dt
    h = min(abs(h_init), abs(dt)) * direction

    # RKF45 Butcher tableau coefficients.
    a2 = 1.0 / 4.0
    a3 = [3.0 / 32.0, 9.0 / 32.0]
    a4 = [1932.0 / 2197.0, -7200.0 / 2197.0, 7296.0 / 2197.0]
    a5 = [439.0 / 216.0, -8.0, 3680.0 / 513.0, -845.0 / 4104.0]
    a6 = [-8.0 / 27.0, 2.0, -3544.0 / 2565.0, 1859.0 / 4104.0, -11.0 / 40.0]
    # 5th-order weights
    b5 = [16.0 / 135.0, 0.0, 6656.0 / 12825.0, 28561.0 / 56430.0,
          -9.0 / 50.0, 2.0 / 55.0]
    # 4th-order weights
    b4 = [25.0 / 216.0, 0.0, 1408.0 / 2565.0, 2197.0 / 4104.0, -1.0 / 5.0, 0.0]

    def f(yv: np.ndarray, tt: float) -> np.ndarray:
        rr = yv[:3]
        vv = yv[3:]
        _, aa = _deriv(rr, vv, tt, body, extra_accel)
        return np.concatenate([vv, aa])

    max_iter = 100_000
    for _ in range(max_iter):
        if direction > 0 and t + h > target:
            h = target - t
        elif direction < 0 and t + h < target:
            h = target - t

        k1 = f(y, t)
        k2 = f(y + h * a2 * k1, t + a2 * h)
        k3 = f(y + h * (a3[0] * k1 + a3[1] * k2), t + 0.25 * h)
        k4 = f(y + h * (a4[0] * k1 + a4[1] * k2 + a4[2] * k3), t + 12.0 / 13.0 * h)
        k5 = f(y + h * (a5[0] * k1 + a5[1] * k2 + a5[2] * k3 + a5[3] * k4), t + h)
        k6 = f(y + h * (a6[0] * k1 + a6[1] * k2 + a6[2] * k3 + a6[3] * k4 + a6[4] * k5),
               t + 0.5 * h)

        y5 = y + h * (b5[0] * k1 + b5[2] * k3 + b5[3] * k4 + b5[4] * k5 + b5[5] * k6)
        y4 = y + h * (b4[0] * k1 + b4[2] * k3 + b4[3] * k4 + b4[4] * k5)

        err = np.abs(y5 - y4)
        sc = atol + rtol * np.maximum(np.abs(y), np.abs(y5))
        err_norm = float(np.sqrt(np.mean((err / sc) ** 2)))

        if err_norm <= 1.0:
            t += h
            y = y5
        else:
            # Step too big — shrink and retry.
            factor = 0.9 * err_norm ** (-0.2)
            factor = max(0.2, min(5.0, factor))
            h = max(abs(h) * factor, h_min) * direction
            continue

        if abs(t - target) < 1e-9:
            break

        # Grow step for next iteration.
        if err_norm < 1e-12:
            factor = 5.0
        else:
            factor = 0.9 * err_norm ** (-0.2)
            factor = max(0.2, min(5.0, factor))
        h = min(abs(h) * factor, h_max) * direction

    return StateVector(r=y[:3], v=y[3:], t=target)


def propagate_bs(
    state: StateVector,
    body: Body,
    dt: float,
    rtol: float = 1e-12,
    n_sequence: Sequence[int] = (2, 4, 6, 8, 12, 16, 24, 32, 48, 64),
    extra_accel: AccelFn | None = None,
) -> StateVector:
    """Bulirsch-Stoer extrapolation propagator.

    Uses the modified midpoint method with a sequence of sub-step counts
    and polynomial/rational extrapolation to zero step size.  Extremely
    accurate for smooth two-body + perturbation dynamics.

    Parameters
    ----------
    state : StateVector
        Initial state.
    body : Body
        Central body.
    dt : float
        Total time increment [s].
    rtol : float
        Target relative tolerance.
    n_sequence : sequence of int
        Sub-step counts for the extrapolation sequence.
    extra_accel : callable, optional
        Perturbing acceleration.

    Returns
    -------
    StateVector
        Propagated state.
    """
    y0 = np.concatenate([state.r.copy(), state.v.copy()]).astype(float)

    def f(yv: np.ndarray, tt: float) -> np.ndarray:
        rr = yv[:3]
        vv = yv[3:]
        _, aa = _deriv(rr, vv, tt, body, extra_accel)
        return np.concatenate([vv, aa])

    def midpoint(H: float, n: int) -> np.ndarray:
        """Modified midpoint: integrate over H with n sub-steps."""
        h = H / n
        ym = y0.copy()
        yf = y0 + h * f(y0, 0.0)
        for i in range(1, n):
            ynew = ym + 2.0 * h * f(yf, i * h)
            ym = yf
            yf = ynew
        return 0.5 * (ym + yf + h * f(yf, H))

    table: list[list[np.ndarray]] = []
    H = dt
    prev = None
    for k, n in enumerate(n_sequence):
        T = midpoint(H, n)
        # Aitken-Neville polynomial extrapolation to h→0.
        # T_{k,0} = midpoint result with n_k sub-steps.
        # T_{k,j} = T_{k,j-1} + (T_{k,j-1} - T_{k-1,j-1}) / ((n_k/n_{k-j})² - 1)
        col: list[np.ndarray] = [T]
        for j in range(1, k + 1):
            ratio_sq = (n_sequence[k] / n_sequence[k - j]) ** 2
            factor = 1.0 / (ratio_sq - 1.0)
            col.append(col[j - 1] + (col[j - 1] - table[k - 1][j - 1]) * factor)
        table.append(col)
        if prev is not None:
            err = float(np.sqrt(np.mean(((col[-1] - prev) /
                                         (atol_rtol(col[-1], rtol=rtol))) ** 2)))
            if err < 1.0:
                return StateVector(r=col[-1][:3], v=col[-1][3:], t=state.t + dt)
        prev = col[-1]

    if prev is None:
        return StateVector(r=y0[:3], v=y0[3:], t=state.t + dt)
    return StateVector(r=prev[:3], v=prev[3:], t=state.t + dt)


def atol_rtol(y: np.ndarray, rtol: float = 1e-12, atol: float = 1e-9) -> np.ndarray:
    return atol + rtol * np.abs(y)