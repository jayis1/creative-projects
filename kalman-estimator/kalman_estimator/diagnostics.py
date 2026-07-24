"""Estimator diagnostics: innovation statistics, log-likelihood, NIS/NEES.

Provides tools to validate filter consistency:

* **NIS** (Normalized Innovation Squared) — should average to meas_dim
  if the model is correct.
* **NEES** (Normalized Estimation Error Squared) — should average to
  state_dim if the filter is consistent and the true state is known.
* **Log-likelihood** — model fit measure (higher = better fit).
* **AIC / BIC** — model selection criteria.
"""

from __future__ import annotations

import math
import numpy as np


# --------------------------------------------------------------------------- #
# Chi-square survival function and inverse CDF (pure-Python, no scipy).
# Uses the Wilson-Hilferty approximation for the inverse CDF, which is
# accurate to within ~1% for dof >= 1.
# --------------------------------------------------------------------------- #

def _chi2_ppf(p, dof):
    """Approximate chi-square percent point function (inverse CDF).

    Uses the Wilson-Hilferty approximation:
        z ≈ ((p⁰·⁰·⁵ − (1−2/(9d))) / sqrt(2/(9d)))³
    then  X ≈ d * (1 - 2/(9d) + z*sqrt(2/(9d)))³
    """
    if p <= 0:
        return 0.0
    if p >= 1:
        return float("inf")
    # Normal inverse CDF via Beasley-Springer-Moro approximation
    a = [
        -3.969683028665376e+01, 2.209460984245205e+02,
        -2.759285104469687e+02, 1.383577518672690e+02,
        -3.066479806614716e+01, 2.506628277459239e+00,
    ]
    b = [
        -5.447609879822406e+01, 1.615858708804980e+02,
        -1.556989798598866e+02, 6.680131188771972e+01,
        -1.328068155288572e+01,
    ]
    c = [
        -7.784894002430293e-03, -3.223964580411365e-01,
        -2.400758277161838e+00, -2.549732539343734e+00,
        4.374141415064656e+00, 2.938163982698783e+00,
    ]
    d = [
        7.784695709041462e-03, 3.224671290701910e-01,
        2.445134187142662e+00, 3.754408661907416e+00,
    ]
    q = p - 0.5
    if abs(q) <= 0.425:
        r = q * q
        z = (((((a[0]*r + a[1])*r + a[2])*r + a[3])*r + a[4])*r + a[5]) * q / \
            (((((b[0]*r + b[1])*r + b[2])*r + b[3])*r + b[4])*r + 1.0)
    else:
        r = p if q < 0 else 1.0 - p
        if r == 0:
            r = 1e-300
        r = math.sqrt(-math.log(r))
        z = (((((c[0]*r + c[1])*r + c[2])*r + c[3])*r + c[4])*r + c[5]) / \
            ((((d[0]*r + d[1])*r + d[2])*r + d[3])*r + 1.0)
        if q < 0:
            z = -z
    # Wilson-Hilferty
    h = 2.0 / (9.0 * dof)
    return dof * (1.0 - h + z * math.sqrt(h)) ** 3


class FilterDiagnostics:
    """Collect and analyse innovation/residual statistics during a filter run.

    Parameters
    ----------
    state_dim : int
        Dimension of the state vector.
    meas_dim : int
        Dimension of the measurement vector.
    """

    def __init__(self, state_dim=None, meas_dim=None):
        self.state_dim = state_dim
        self.meas_dim = meas_dim
        self.innovations = []      # y_k = z_k - H x_k
        self.innovation_cov = []   # S_k
        self.states = []           # posterior means
        self.covariances = []      # posterior covariances
        self.true_states = []      # ground truth (if available)

    def record(self, innovation, S, state, P, true_state=None):
        """Record one time-step's data.

        Parameters
        ----------
        innovation : (m,) array
            Innovation vector y = z - H·x_pred (or z - h(x_pred) for EKF/UKF).
        S : (m, m) array
            Innovation covariance.
        state : (n,) array
            Posterior state estimate.
        P : (n, n) array
            Posterior covariance.
        true_state : (n,) array, optional
            Ground-truth state for NEES computation.
        """
        self.innovations.append(np.asarray(innovation, dtype=float).ravel())
        self.innovation_cov.append(np.atleast_2d(S).astype(float))
        self.states.append(np.asarray(state, dtype=float).ravel())
        self.covariances.append(np.atleast_2d(P).astype(float))
        if true_state is not None:
            self.true_states.append(np.asarray(true_state, dtype=float).ravel())

    # ------------------------------------------------------------------ #
    # NIS  (Normalized Innovation Squared)
    # ------------------------------------------------------------------ #
    def nis(self):
        """Return array of NIS values: yᵀ S⁻¹ y.

        Under a correctly specified model, NIS ~ χ²(meas_dim).
        Uses np.linalg.pinv for robustness against singular S.
        """
        nis_values = []
        for y, S in zip(self.innovations, self.innovation_cov):
            # Use pinv for robustness against singular S
            S_inv = np.linalg.pinv(S)
            nis_values.append(y @ S_inv @ y)
        return np.array(nis_values)

    def nis_confidence_interval(self, confidence=0.95):
        """Two-sided confidence interval for individual NIS values.

        Returns (lower, upper) such that a fraction *confidence* of
        NIS values should fall within, if the model is correct.
        """
        if self.meas_dim is None:
            raise ValueError("meas_dim must be set to compute NIS CI")
        dof = self.meas_dim
        lower = _chi2_ppf((1 - confidence) / 2, dof)
        upper = _chi2_ppf(1 - (1 - confidence) / 2, dof)
        return lower, upper

    # ------------------------------------------------------------------ #
    # NEES (Normalized Estimation Error Squared)
    # ------------------------------------------------------------------ #
    def nees(self):
        """Return array of NEES values (requires true_states).

        Under a consistent filter, NEES ~ χ²(state_dim).
        Uses np.linalg.pinv for robustness against singular P.
        """
        if not self.true_states:
            raise ValueError("true_states not recorded; cannot compute NEES")
        nees_values = []
        for x_est, P, x_true in zip(self.states, self.covariances, self.true_states):
            err = x_est - x_true
            # Use pinv for robustness against singular P
            P_inv = np.linalg.pinv(P)
            nees_values.append(err @ P_inv @ err)
        return np.array(nees_values)

    # ------------------------------------------------------------------ #
    # Log-likelihood, AIC, BIC
    # ------------------------------------------------------------------ #
    def log_likelihood(self):
        """Total Gaussian log-likelihood of the measurement sequence.

        For each step:
            ln p(z_k | z_{1:k-1}) = -½ [yᵀ S⁻¹ y + ln|S| + m ln(2π)]
        Uses np.linalg.pinv for robustness against singular S.
        """
        ll = 0.0
        for y, S in zip(self.innovations, self.innovation_cov):
            m = y.shape[0]
            S_inv = np.linalg.pinv(S)
            sign, logdet = np.linalg.slogdet(S)
            # If S is singular, slogdet returns sign=0; use a large negative
            # logdet to avoid inf without crashing
            if sign == 0:
                logdet = -1e300
            ll += -0.5 * (y @ S_inv @ y + logdet + m * np.log(2 * np.pi))
        return ll

    def average_log_likelihood(self):
        n = len(self.innovations)
        if n == 0:
            return 0.0
        return self.log_likelihood() / n

    def aic(self, n_params):
        """Akaike Information Criterion: 2k - 2LL."""
        return 2 * n_params - 2 * self.log_likelihood()

    def bic(self, n_params):
        """Bayesian Information Criterion: k·ln(N) - 2LL.

        Returns NaN if no data has been recorded (N=0).
        """
        n = len(self.innovations)
        if n == 0:
            return float("nan")
        return n_params * np.log(n) - 2 * self.log_likelihood()

    # ------------------------------------------------------------------ #
    # Summary
    # ------------------------------------------------------------------ #
    def summary(self):
        """Return a dict of diagnostic statistics."""
        result = {
            "n_steps": len(self.innovations),
            "log_likelihood": self.log_likelihood(),
            "avg_log_likelihood": self.average_log_likelihood(),
        }
        nis = self.nis()
        result["nis_mean"] = float(np.mean(nis))
        result["nis_std"] = float(np.std(nis))
        if self.meas_dim is not None:
            lo, hi = self.nis_confidence_interval()
            result["nis_ci_lower"] = float(lo)
            result["nis_ci_upper"] = float(hi)
            result["nis_in_ci"] = float(np.mean((nis >= lo) & (nis <= hi)))
        if self.true_states:
            nees = self.nees()
            result["nees_mean"] = float(np.mean(nees))
        return result