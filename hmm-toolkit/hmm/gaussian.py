"""Gaussian-emission HMM for continuous observation sequences.

This module provides ``GaussianHMM``, an HMM variant whose emission
distributions are univariate or multivariate Gaussians instead of discrete
symbol tables.  It supports the same Forward / Backward / Viterbi /
Baum-Welch machinery as the discrete ``HMM`` class but operates on
real-valued observation vectors.

Only the Python standard library is used (``math``, ``random``).
For multivariate support we implement a small linear-algebra helpers module
(``_linalg``) so no NumPy is required.
"""

from __future__ import annotations

import math
import random
from typing import List, Optional, Sequence, Tuple

from . import _linalg


# ---------------------------------------------------------------------------
# Small linear-algebra helpers (avoids NumPy dependency)
# ---------------------------------------------------------------------------


def _gaussian_log_pdf(x: Sequence[float], mean: Sequence[float],
                      cov: Sequence[Sequence[float]]) -> float:
    """Log probability density of a multivariate Gaussian.

    ``cov`` is a D×D covariance matrix.  Uses the closed-form determinant
    and inverse via Gaussian elimination (fine for moderate D).
    """
    D = len(mean)
    diff = [x[i] - mean[i] for i in range(D)]
    det = _linalg.det(cov)
    if det <= 0:
        # Degenerate covariance — fall back to a tiny ridge
        cov = _linalg.add_ridge(cov, 1e-9)
        det = _linalg.det(cov)
    inv = _linalg.inv(cov)
    # quadratic form: diff^T * inv * diff
    quad = sum(diff[i] * sum(diff[j] * inv[j][i] for j in range(D))
               for i in range(D))
    log_norm = -0.5 * (D * math.log(2 * math.pi) + math.log(det))
    return log_norm - 0.5 * quad


class GaussianHMM:
    """Hidden Markov Model with Gaussian (continuous) emissions.

    Parameters
    ----------
    states : Sequence[str]
        Names of the hidden states.
    n_dim : int
        Dimensionality of the observation vectors.
    A : Sequence[Sequence[float]], shape (N, N)
        Transition matrix.
    means : Sequence[Sequence[float]], shape (N, D)
        Mean vector for each state's Gaussian.
    covs : Sequence[Sequence[Sequence[float]]], shape (N, D, D)
        Covariance matrix for each state.
    pi : Sequence[float], shape (N,)
        Initial state distribution.
    """

    def __init__(
        self,
        states: Sequence[str],
        n_dim: int,
        A: Sequence[Sequence[float]],
        means: Sequence[Sequence[float]],
        covs: Sequence[Sequence[Sequence[float]]],
        pi: Sequence[float],
    ) -> None:
        self.states: List[str] = list(states)
        self.n_states: int = len(self.states)
        self.n_dim: int = n_dim

        if self.n_states == 0:
            raise ValueError("GaussianHMM must have at least one state")
        if n_dim < 1:
            raise ValueError("n_dim must be >= 1")
        if len(set(self.states)) != self.n_states:
            raise ValueError("Duplicate state names are not allowed")
        if len(A) != self.n_states:
            raise ValueError(f"A must have {self.n_states} rows")
        for i, row in enumerate(A):
            if len(row) != self.n_states:
                raise ValueError(f"A[{i}] has wrong number of columns")
        if len(means) != self.n_states:
            raise ValueError("means must have one row per state")
        if len(covs) != self.n_states:
            raise ValueError("covs must have one matrix per state")
        if len(pi) != self.n_states:
            raise ValueError("pi must have one entry per state")
        for m in means:
            if len(m) != n_dim:
                raise ValueError("mean vector dimension mismatch")
        for c in covs:
            if len(c) != n_dim or any(len(r) != n_dim for r in c):
                raise ValueError("covariance matrix shape mismatch")

        from .hmm import _normalise_rows, _normalise_row, _validate_non_negative, _validate_vector
        _validate_non_negative("A", A)
        _validate_vector("pi", pi)
        self.A = _normalise_rows(A)
        self.pi = _normalise_row(pi)
        self.means: List[List[float]] = [list(m) for m in means]
        self.covs: List[List[List[float]]] = [[list(r) for r in c] for c in covs]

        # Precompute log A / pi
        self._log_A: Optional[List[List[float]]] = None
        self._log_pi: Optional[List[float]] = None

    # -- log caches --
    @staticmethod
    def _safe_log(x: float) -> float:
        return math.log(x) if x > 0 else -math.inf

    @property
    def log_A(self) -> List[List[float]]:
        if self._log_A is None:
            self._log_A = [[self._safe_log(v) for v in row] for row in self.A]
        return self._log_A

    @property
    def log_pi(self) -> List[float]:
        if self._log_pi is None:
            self._log_pi = [self._safe_log(v) for v in self.pi]
        return self._log_pi

    # -- emission log-prob --
    def emission_log_prob(self, state_idx: int, x: Sequence[float]) -> float:
        return _gaussian_log_pdf(x, self.means[state_idx], self.covs[state_idx])

    # -- Forward --
    def forward(self, obs: Sequence[Sequence[float]]) -> Tuple[List[List[float]], List[float], float]:
        """Scaled forward algorithm for continuous observations."""
        N = self.n_states
        T = len(obs)
        if T == 0:
            return [], [], 0.0
        alpha = [[0.0] * N for _ in range(T)]
        scales = [0.0] * T
        for i in range(N):
            alpha[0][i] = self.pi[i] * math.exp(self.emission_log_prob(i, obs[0]))
        s0 = sum(alpha[0])
        if s0 <= 0:
            return alpha, scales, -math.inf
        scales[0] = s0
        for i in range(N):
            alpha[0][i] /= s0
        for t in range(1, T):
            for j in range(N):
                acc = sum(alpha[t - 1][i] * self.A[i][j] for i in range(N))
                alpha[t][j] = acc * math.exp(self.emission_log_prob(j, obs[t]))
            s = sum(alpha[t])
            if s <= 0:
                return alpha, scales, -math.inf
            scales[t] = s
            for j in range(N):
                alpha[t][j] /= s
        ll = sum(math.log(s) for s in scales)
        return alpha, scales, ll

    # -- Backward --
    def backward(self, obs: Sequence[Sequence[float]], scales: Optional[Sequence[float]] = None) -> List[List[float]]:
        N = self.n_states
        T = len(obs)
        if T == 0:
            return []
        if scales is None:
            _, scales, _ = self.forward(obs)
        beta = [[0.0] * N for _ in range(T)]
        s_last = scales[T - 1] if scales[T - 1] > 0 else 1.0
        for i in range(N):
            beta[T - 1][i] = 1.0 / s_last
        for t in range(T - 2, -1, -1):
            for i in range(N):
                acc = sum(self.A[i][j] * math.exp(self.emission_log_prob(j, obs[t + 1])) * beta[t + 1][j]
                          for j in range(N))
                s_t = scales[t] if scales[t] > 0 else 1.0
                beta[t][i] = acc / s_t
        return beta

    # -- Viterbi --
    def viterbi(self, obs: Sequence[Sequence[float]]) -> Tuple[List[int], float]:
        N = self.n_states
        T = len(obs)
        if T == 0:
            return [], 0.0
        delta = [[-math.inf] * N for _ in range(T)]
        psi = [[0] * N for _ in range(T)]
        for i in range(N):
            delta[0][i] = self.log_pi[i] + self.emission_log_prob(i, obs[0])
        for t in range(1, T):
            for j in range(N):
                best_val, best_idx = -math.inf, 0
                for i in range(N):
                    val = delta[t - 1][i] + self.log_A[i][j]
                    if val > best_val:
                        best_val, best_idx = val, i
                delta[t][j] = best_val + self.emission_log_prob(j, obs[t])
                psi[t][j] = best_idx
        best_last, best_lp = 0, delta[T - 1][0]
        for i in range(1, N):
            if delta[T - 1][i] > best_lp:
                best_lp, best_last = delta[T - 1][i], i
        if best_lp == -math.inf:
            return [], -math.inf
        path = [0] * T
        path[T - 1] = best_last
        for t in range(T - 2, -1, -1):
            path[t] = psi[t + 1][path[t + 1]]
        return path, best_lp

    # -- Baum-Welch for Gaussian emissions --
    def baum_welch(self, obs: Sequence[Sequence[float]],
                   iterations: int = 50, tol: float = 1e-4,
                   smooth: float = 1e-6, verbose: bool = False) -> Tuple[float, int]:
        """EM training for Gaussian HMM (single sequence, updates in place)."""
        N = self.n_states
        D = self.n_dim
        T = len(obs)
        if T < 2:
            raise ValueError("Need at least 2 observations")
        prev_ll = -math.inf
        iters_run = 0
        for it in range(iterations):
            iters_run = it + 1
            alpha, scales, ll = self.forward(obs)
            if ll == -math.inf:
                return ll, iters_run
            beta = self.backward(obs, scales)
            # gamma
            gamma = [[0.0] * N for _ in range(T)]
            for t in range(T):
                denom = sum(alpha[t][i] * beta[t][i] for i in range(N))
                if denom <= 0:
                    denom = smooth
                for i in range(N):
                    gamma[t][i] = alpha[t][i] * beta[t][i] / denom
            # xi
            xi_sum = [[0.0] * N for _ in range(N)]
            for t in range(T - 1):
                denom = 0.0
                for i in range(N):
                    for j in range(N):
                        denom += alpha[t][i] * self.A[i][j] * \
                                 math.exp(self.emission_log_prob(j, obs[t + 1])) * \
                                 beta[t + 1][j]
                if denom <= 0:
                    denom = smooth
                for i in range(N):
                    for j in range(N):
                        xi_sum[i][j] += (
                            alpha[t][i] * self.A[i][j] *
                            math.exp(self.emission_log_prob(j, obs[t + 1])) *
                            beta[t + 1][j]
                        ) / denom
            # M-step
            new_pi = [gamma[0][i] for i in range(N)]
            new_A = [[0.0] * N for _ in range(N)]
            for i in range(N):
                denom_a = sum(gamma[t][i] for t in range(T - 1))
                if denom_a <= 0:
                    denom_a = smooth
                for j in range(N):
                    new_A[i][j] = (xi_sum[i][j] + smooth) / (denom_a + smooth * N)
            new_means = [[0.0] * D for _ in range(N)]
            new_covs = [[[0.0] * D for _ in range(D)] for _ in range(N)]
            for i in range(N):
                denom_b = sum(gamma[t][i] for t in range(T))
                if denom_b <= 0:
                    denom_b = smooth
                for d in range(D):
                    new_means[i][d] = sum(gamma[t][i] * obs[t][d] for t in range(T)) / denom_b
                for d1 in range(D):
                    for d2 in range(D):
                        new_covs[i][d1][d2] = sum(
                            gamma[t][i] * (obs[t][d1] - new_means[i][d1]) *
                            (obs[t][d2] - new_means[i][d2])
                            for t in range(T)
                        ) / denom_b + (smooth if d1 == d2 else 0.0)
            # commit
            self.A = new_A
            self.pi = new_pi
            self.means = new_means
            self.covs = new_covs
            self._log_A = None
            self._log_pi = None
            if verbose:
                print(f"  iter {it + 1}: log-likelihood = {ll:.6f}")
            if abs(ll - prev_ll) < tol:
                break
            prev_ll = ll
        _, _, final_ll = self.forward(obs)
        return final_ll, iters_run

    def __repr__(self) -> str:
        return (f"GaussianHMM(states={self.states}, n_dim={self.n_dim}, "
                f"n_states={self.n_states})")


# -- factory --
def random_gaussian_hmm(
    states: Sequence[str],
    n_dim: int,
    rng: Optional[random.Random] = None,
    seed: Optional[int] = None,
) -> GaussianHMM:
    """Create a GaussianHMM with random (but valid) parameters."""
    if rng is None:
        rng = random.Random(seed)
    N = len(states)

    def rand_row(k: int) -> List[float]:
        vals = [rng.random() for _ in range(k)]
        s = sum(vals)
        return [v / s for v in vals]

    A = [rand_row(N) for _ in range(N)]
    pi = rand_row(N)
    means = [[rng.gauss(0, 1) for _ in range(n_dim)] for _ in range(N)]
    covs = []
    for _ in range(N):
        c = [[0.0] * n_dim for _ in range(n_dim)]
        for d in range(n_dim):
            c[d][d] = 1.0  # identity covariance
        covs.append(c)
    return GaussianHMM(states, n_dim, A, means, covs, pi)