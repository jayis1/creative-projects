"""Numerical Jacobian computation via central finite differences.

Useful for the EKF when analytical Jacobians are tedious or error-prone
to derive.  The implementation uses a central-difference stencil with
an adaptive step size.
"""

from __future__ import annotations

from typing import Callable

import numpy as np


def numerical_jacobian(
    func: Callable,
    x: np.ndarray,
    eps: float = 1e-6,
    *args,
) -> np.ndarray:
    """Compute the Jacobian of *func* at *x* via central finite differences.

    Parameters
    ----------
    func : callable(x, *args) -> (m,) array
        Function whose Jacobian is to be computed.  Must accept a 1-D
        array and return a 1-D array.
    x : (n,) array
        Point at which to evaluate the Jacobian.
    eps : float
        Step size for the finite-difference stencil (relative to the
        magnitude of each component).
    *args : additional positional arguments passed to *func*.

    Returns
    -------
    J : (m, n) array
        Jacobian matrix ``d func / d x``.
    """
    x = np.asarray(x, dtype=float).ravel()
    n = x.shape[0]
    f0 = np.asarray(func(x, *args), dtype=float).ravel()
    m = f0.shape[0]
    J = np.zeros((m, n))
    for j in range(n):
        h = eps * max(1.0, abs(x[j]))
        x_plus = x.copy()
        x_plus[j] += h
        x_minus = x.copy()
        x_minus[j] -= h
        f_plus = np.asarray(func(x_plus, *args), dtype=float).ravel()
        f_minus = np.asarray(func(x_minus, *args), dtype=float).ravel()
        J[:, j] = (f_plus - f_minus) / (2.0 * h)
    return J


class NumericalJacobianEKF:
    """Mixin / helper that provides numerical-Jacobian EKF usage.

    Instead of passing analytical ``F_jac`` / ``H_jac`` to the EKF,
    use this wrapper which computes them automatically via finite
    differences.

    Parameters
    ----------
    f, h, Q, R, x0, P0 : as in :class:`ExtendedKalmanFilter`.
    eps : finite-difference step size.
    """

    def __init__(self, f, h, Q, R, x0, P0, eps: float = 1e-6):
        # import here to avoid circular dependency
        from .ekf import ExtendedKalmanFilter

        self._f = f
        self._h = h
        self._eps = eps

        def F_jac(x, u):
            return numerical_jacobian(lambda xx: f(xx, u), x, eps)

        def H_jac(x):
            return numerical_jacobian(h, x, eps)

        self.ekf = ExtendedKalmanFilter(f, h, F_jac, H_jac, Q, R, x0, P0)
        # expose key attributes
        self._delegate = self.ekf

    def predict(self, u=None):
        self.ekf.predict(u)

    def update(self, z):
        self.ekf.update(z)

    def step(self, z, u=None):
        return self.ekf.step(z, u)

    @property
    def state(self):
        return self.ekf.state

    @property
    def covariance(self):
        return self.ekf.covariance