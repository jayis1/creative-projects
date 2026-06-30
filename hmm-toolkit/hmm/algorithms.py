"""Core HMM algorithms: Forward, Backward, Viterbi, Baum-Welch.

All implemented in pure Python using the scaled (log-space where appropriate)
formulations to avoid numerical underflow on long sequences.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Protocol, Sequence, Tuple


class _HMMLike(Protocol):
    """Structural protocol satisfied by both ``HMM`` and ``ProfileHMM``."""
    n_states: int
    n_symbols: int
    A: Sequence[Sequence[float]]
    B: Sequence[Sequence[float]]
    pi: Sequence[float]
    log_A: Sequence[Sequence[float]]
    log_B: Sequence[Sequence[float]]
    log_pi: Sequence[float]

    def set_parameters(self, *args, **kwargs) -> None: ...


def _validate_observations(hmm: _HMMLike, obs: Sequence[int]) -> None:
    """Check that all observation indices are in [0, n_symbols)."""
    M = hmm.n_symbols
    for t, o in enumerate(obs):
        if o < 0 or o >= M:
            raise ValueError(
                f"observation at t={t} is {o}, must be in [0, {M})"
            )


# ---------------------------------------------------------------------------
# Forward algorithm (scaled) — returns alpha scaling factors and log-likelihood
# ---------------------------------------------------------------------------

def forward(hmm: _HMMLike, obs: Sequence[int]) -> Tuple[List[List[float]], List[float], float]:
    """Scaled forward algorithm.

    Parameters
    ----------
    hmm : HMM
    obs : sequence of int
        Observation sequence as integer indices.

    Returns
    -------
    alpha : List[List[float]], shape (T, N)
        Scaled forward probabilities.
    scales : List[float], shape (T,)
        Per-time-step scaling factors.
    log_likelihood : float
        log P(O | model).
    """
    _validate_observations(hmm, obs)
    N = hmm.n_states
    T = len(obs)
    if T == 0:
        return [], [], 0.0

    alpha = [[0.0] * N for _ in range(T)]
    scales = [0.0] * T

    # t = 0: initialisation
    o0 = obs[0]
    for i in range(N):
        alpha[0][i] = hmm.pi[i] * hmm.B[i][o0]
    s0 = sum(alpha[0])
    if s0 <= 0:
        # impossible observation under this model
        return alpha, scales, -math.inf
    scales[0] = s0
    for i in range(N):
        alpha[0][i] /= s0

    # induction
    for t in range(1, T):
        ot = obs[t]
        s_t = 0.0
        for j in range(N):
            acc = 0.0
            for i in range(N):
                acc += alpha[t - 1][i] * hmm.A[i][j]
            alpha[t][j] = acc * hmm.B[j][ot]
            s_t += alpha[t][j]
        if s_t <= 0:
            return alpha, scales, -math.inf
        scales[t] = s_t
        for j in range(N):
            alpha[t][j] /= s_t

    log_likelihood = sum(math.log(s) for s in scales)
    return alpha, scales, log_likelihood


# ---------------------------------------------------------------------------
# Backward algorithm (scaled) — uses the same scale factors from forward()
# ---------------------------------------------------------------------------

def backward(
    hmm: _HMMLike, obs: Sequence[int], scales: Optional[Sequence[float]] = None
) -> List[List[float]]:
    """Scaled backward algorithm.

    If ``scales`` is provided (e.g. from a prior ``forward`` call) they are
    reused; otherwise the function computes them internally.

    Returns ``beta``, shape (T, N), scaled backward probabilities.
    """
    _validate_observations(hmm, obs)
    N = hmm.n_states
    T = len(obs)
    if T == 0:
        return []

    if scales is None:
        _, scales, _ = forward(hmm, obs)

    beta = [[0.0] * N for _ in range(T)]

    # t = T-1: initialisation
    s_last = scales[T - 1] if scales[T - 1] > 0 else 1.0
    for i in range(N):
        beta[T - 1][i] = 1.0 / s_last

    # induction
    for t in range(T - 2, -1, -1):
        ot1 = obs[t + 1]
        s_t = scales[t] if scales[t] > 0 else 1.0
        for i in range(N):
            acc = 0.0
            for j in range(N):
                acc += hmm.A[i][j] * hmm.B[j][ot1] * beta[t + 1][j]
            beta[t][i] = acc / s_t
    return beta


# ---------------------------------------------------------------------------
# Viterbi algorithm (log-space) — best state path
# ---------------------------------------------------------------------------

def viterbi(hmm: _HMMLike, obs: Sequence[int]) -> Tuple[List[int], float]:
    """Viterbi algorithm in log-space.

    Returns
    -------
    path : List[int]
        Most likely sequence of hidden-state indices.
    log_prob : float
        Log-probability of the best path. ``-inf`` if the sequence is
        impossible under the model.
    """
    _validate_observations(hmm, obs)
    N = hmm.n_states
    T = len(obs)
    if T == 0:
        return [], 0.0

    log_A = hmm.log_A
    log_B = hmm.log_B
    log_pi = hmm.log_pi

    delta = [[-math.inf] * N for _ in range(T)]
    psi = [[0] * N for _ in range(T)]  # backpointers

    # initialisation
    o0 = obs[0]
    for i in range(N):
        delta[0][i] = log_pi[i] + log_B[i][o0]

    # recursion
    for t in range(1, T):
        ot = obs[t]
        for j in range(N):
            best_val = -math.inf
            best_idx = 0
            for i in range(N):
                val = delta[t - 1][i] + log_A[i][j]
                if val > best_val:
                    best_val = val
                    best_idx = i
            delta[t][j] = best_val + log_B[j][ot]
            psi[t][j] = best_idx

    # termination
    best_last = 0
    best_log_prob = delta[T - 1][0]
    for i in range(1, N):
        if delta[T - 1][i] > best_log_prob:
            best_log_prob = delta[T - 1][i]
            best_last = i

    if best_log_prob == -math.inf:
        # Impossible sequence: return empty path rather than a misleading [0]*T
        return [], -math.inf

    # backtrace
    path = [0] * T
    path[T - 1] = best_last
    for t in range(T - 2, -1, -1):
        path[t] = psi[t + 1][path[t + 1]]

    return path, best_log_prob


# ---------------------------------------------------------------------------
# Baum-Welch — EM parameter estimation
# ---------------------------------------------------------------------------

def baum_welch(
    hmm: _HMMLike,
    obs: Sequence[int],
    iterations: int = 100,
    tol: float = 1e-6,
    smooth: float = 1e-10,
    verbose: bool = False,
) -> Tuple[float, int]:
    """Baum-Welch EM training (in-place update of ``hmm``).

    Parameters
    ----------
    hmm : HMM
        Model to train (modified in place).
    obs : sequence of int
        Observation sequence as integer indices.
    iterations : int
        Maximum number of EM iterations.
    tol : float
        Convergence threshold on log-likelihood improvement.
    smooth : float
        Additive smoothing constant to prevent zero probabilities.
    verbose : bool
        If True, print per-iteration log-likelihood.

    Returns
    -------
    final_log_likelihood : float
    iterations_run : int
    """
    N = hmm.n_states
    M = hmm.n_symbols
    T = len(obs)
    if T < 2:
        raise ValueError("Baum-Welch needs at least 2 observations")

    prev_ll = -math.inf
    iters_run = 0

    for it in range(iterations):
        iters_run = it + 1
        alpha, scales, ll = forward(hmm, obs)
        if ll == -math.inf:
            # impossible sequence — cannot train
            return ll, iters_run
        beta = backward(hmm, obs, scales)

        # gamma[t][i] = P(state i at t | O, model)
        gamma = [[0.0] * N for _ in range(T)]
        # xi[t][i][j] = P(state i at t, state j at t+1 | O, model)
        xi = [[[0.0] * N for _ in range(N)] for _ in range(T - 1)]

        for t in range(T):
            denom = sum(alpha[t][i] * beta[t][i] for i in range(N))
            if denom <= 0:
                denom = smooth
            for i in range(N):
                gamma[t][i] = (alpha[t][i] * beta[t][i]) / denom

        for t in range(T - 1):
            ot1 = obs[t + 1]
            denom = 0.0
            for i in range(N):
                for j in range(N):
                    denom += (
                        alpha[t][i] * hmm.A[i][j] * hmm.B[j][ot1] * beta[t + 1][j]
                    )
            if denom <= 0:
                denom = smooth
            for i in range(N):
                for j in range(N):
                    xi[t][i][j] = (
                        alpha[t][i] * hmm.A[i][j] * hmm.B[j][ot1] * beta[t + 1][j]
                    ) / denom

        # re-estimate pi
        new_pi = [gamma[0][i] for i in range(N)]

        # re-estimate A
        new_A = [[smooth] * N for _ in range(N)]
        for i in range(N):
            denom_a = sum(gamma[t][i] for t in range(T - 1))
            if denom_a <= 0:
                denom_a = smooth
            for j in range(N):
                num = sum(xi[t][i][j] for t in range(T - 1))
                new_A[i][j] = (num + smooth) / (denom_a + smooth * N)

        # re-estimate B
        new_B = [[smooth] * M for _ in range(N)]
        for i in range(N):
            denom_b = sum(gamma[t][i] for t in range(T))
            if denom_b <= 0:
                denom_b = smooth
            for k in range(M):
                num = sum(gamma[t][i] for t in range(T) if obs[t] == k)
                new_B[i][k] = (num + smooth) / (denom_b + smooth * M)

        # normalise and commit
        hmm.set_parameters(A=new_A, B=new_B, pi=new_pi)

        if verbose:
            print(f"  iter {it + 1}: log-likelihood = {ll:.6f}")

        if abs(ll - prev_ll) < tol:
            break
        prev_ll = ll

    # final ll after last update
    _, _, final_ll = forward(hmm, obs)
    return final_ll, iters_run


def baum_welch_multi(
    hmm: _HMMLike,
    obs_list: Sequence[Sequence[int]],
    iterations: int = 100,
    tol: float = 1e-6,
    smooth: float = 1e-10,
    verbose: bool = False,
) -> Tuple[float, int]:
    """Baum-Welch EM training on **multiple** independent observation sequences.

    Accumulates expected counts across all sequences before the M-step, which
    is the correct way to train on multiple i.i.d. observation sequences.

    Returns (total_final_log_likelihood, iterations_run).
    """
    N = hmm.n_states
    M = hmm.n_symbols
    if not obs_list:
        raise ValueError("obs_list must not be empty")
    for o in obs_list:
        if len(o) < 2:
            raise ValueError("Each observation sequence needs at least 2 observations")

    prev_total_ll = -math.inf
    iters_run = 0

    for it in range(iterations):
        iters_run = it + 1
        # accumulators
        pi_num = [0.0] * N
        A_num = [[0.0] * N for _ in range(N)]
        A_denom = [0.0] * N
        B_num = [[0.0] * M for _ in range(N)]
        B_denom = [0.0] * N
        total_ll = 0.0

        for obs in obs_list:
            alpha, scales, ll = forward(hmm, obs)
            if ll == -math.inf:
                continue
            beta = backward(hmm, obs, scales)
            total_ll += ll

            T = len(obs)
            # gamma
            gamma = [[0.0] * N for _ in range(T)]
            for t in range(T):
                denom = sum(alpha[t][i] * beta[t][i] for i in range(N))
                if denom <= 0:
                    denom = smooth
                for i in range(N):
                    gamma[t][i] = (alpha[t][i] * beta[t][i]) / denom

            # xi
            for t in range(T - 1):
                ot1 = obs[t + 1]
                denom = 0.0
                for i in range(N):
                    for j in range(N):
                        denom += (
                            alpha[t][i] * hmm.A[i][j] * hmm.B[j][ot1] * beta[t + 1][j]
                        )
                if denom <= 0:
                    denom = smooth
                for i in range(N):
                    for j in range(N):
                        xi_tij = (
                            alpha[t][i] * hmm.A[i][j] * hmm.B[j][ot1] * beta[t + 1][j]
                        ) / denom
                        A_num[i][j] += xi_tij
                        A_denom[i] += gamma[t][i]

            for t in range(T):
                for i in range(N):
                    B_num[i][obs[t]] += gamma[t][i]
                    B_denom[i] += gamma[t][i]

            # pi: use first-timestep gamma of each sequence
            for i in range(N):
                pi_num[i] += gamma[0][i]

        # re-estimate
        n_seqs = len(obs_list)
        new_pi = [(pi_num[i] + smooth) / (n_seqs + smooth * N) for i in range(N)]
        new_A = [[(A_num[i][j] + smooth) / (A_denom[i] + smooth * N) for j in range(N)]
                 for i in range(N)]
        new_B = [[(B_num[i][k] + smooth) / (B_denom[i] + smooth * M) for k in range(M)]
                 for i in range(N)]

        hmm.set_parameters(A=new_A, B=new_B, pi=new_pi)

        if verbose:
            print(f"  iter {it + 1}: total log-likelihood = {total_ll:.6f}")

        if abs(total_ll - prev_total_ll) < tol:
            break
        prev_total_ll = total_ll

    # final total ll
    final_total = 0.0
    for obs in obs_list:
        _, _, ll = forward(hmm, obs)
        if ll != -math.inf:
            final_total += ll
    return final_total, iters_run


# ---------------------------------------------------------------------------
# Convenience: posterior decoding
# ---------------------------------------------------------------------------

def posterior_decode(hmm: _HMMLike, obs: Sequence[int]) -> Tuple[List[int], List[List[float]]]:
    """Posterior (forward-backward) decoding.

    Returns the per-timestep argmax-posterior state path and the full gamma
    posterior matrix.
    """
    N = hmm.n_states
    T = len(obs)
    if T == 0:
        return [], []

    alpha, scales, ll = forward(hmm, obs)
    if ll == -math.inf:
        return [0] * T, [[0.0] * N for _ in range(T)]
    beta = backward(hmm, obs, scales)

    gamma = [[0.0] * N for _ in range(T)]
    path = [0] * T
    for t in range(T):
        denom = sum(alpha[t][i] * beta[t][i] for i in range(N))
        if denom <= 0:
            denom = 1.0
        best_i, best_p = 0, -1.0
        for i in range(N):
            gamma[t][i] = (alpha[t][i] * beta[t][i]) / denom
            if gamma[t][i] > best_p:
                best_p = gamma[t][i]
                best_i = i
        path[t] = best_i
    return path, gamma