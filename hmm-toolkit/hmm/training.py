"""Advanced training and evaluation utilities.

Provides:

* **K-fold cross-validation** for HMM model selection
* **Grid search** over hyper-parameters
* **Constrained Baum-Welch** with locked transitions or emissions
* **Multiple random restarts** to avoid local optima
* **Convergence diagnostics** with logging
"""

from __future__ import annotations

import logging
import math
import random
from typing import Dict, List, Optional, Sequence, Tuple

from .hmm import HMM
from .algorithms import forward, backward, baum_welch, baum_welch_multi
from .logging_config import get_logger

_log = get_logger()


# ---------------------------------------------------------------------------
# Cross-validation
# ---------------------------------------------------------------------------

def k_fold_cross_validation(
    states: Sequence[str],
    symbols: Sequence[str],
    obs_sequences: Sequence[Sequence[int]],
    n_states_options: Optional[Sequence[int]] = None,
    k: int = 5,
    iterations: int = 50,
    seed: int = 42,
) -> List[Dict]:
    """K-fold cross-validation for selecting the number of hidden states.

    Parameters
    ----------
    states, symbols : base state/symbol names (states may be truncated)
    obs_sequences : list of observation sequences (as int indices)
    n_states_options : list of state counts to try (e.g. [2, 3, 4])
    k : number of folds
    iterations : Baum-Welch iterations
    seed : RNG seed for reproducibility

    Returns
    -------
    results : list of dicts with keys: n_states, fold, train_ll, val_ll
    """
    if n_states_options is None:
        n_states_options = [2, 3]
    n_seqs = len(obs_sequences)
    if n_seqs < k:
        k = n_seqs
    rng = random.Random(seed)
    indices = list(range(n_seqs))
    rng.shuffle(indices)
    fold_size = n_seqs // k
    results: List[Dict] = []

    for n_states in n_states_options:
        state_names = [f"S{i}" for i in range(n_states)]
        for fold in range(k):
            val_idx = set(indices[fold * fold_size:(fold + 1) * fold_size])
            train_idx = [i for i in indices if i not in val_idx]
            val_seqs = [obs_sequences[i] for i in val_idx]
            train_seqs = [obs_sequences[i] for i in train_idx]
            if not train_seqs:
                continue
            hmm = HMM.random(state_names, symbols, seed=seed + fold * 100 + n_states)
            train_ll, _ = baum_welch_multi(hmm, train_seqs, iterations=iterations)
            # Validation log-likelihood
            val_ll = sum(
                forward(hmm, vs)[2] for vs in val_seqs
                if forward(hmm, vs)[2] != -math.inf
            )
            results.append({
                "n_states": n_states,
                "fold": fold,
                "train_ll": train_ll,
                "val_ll": val_ll,
            })
            _log.debug("CV n_states=%d fold=%d train_ll=%.2f val_ll=%.2f",
                        n_states, fold, train_ll, val_ll)

    return results


def summarize_cv_results(results: List[Dict]) -> "Dict[int, Dict[str, float]]":
    """Summarise cross-validation results grouped by n_states."""
    summary: Dict[int, Dict[str, List[float]]] = {}
    for r in results:
        ns = r["n_states"]
        if ns not in summary:
            summary[ns] = {"train_lls": [], "val_lls": []}
        summary[ns]["train_lls"].append(r["train_ll"])
        summary[ns]["val_lls"].append(r["val_ll"])
    out: Dict[int, Dict[str, float]] = {}
    for ns, vals in summary.items():
        out[ns] = {
            "mean_train_ll": sum(vals["train_lls"]) / len(vals["train_lls"]),
            "mean_val_ll": sum(vals["val_lls"]) / len(vals["val_lls"]),
            "n_folds": float(len(vals["val_lls"])),
        }
    return out


# ---------------------------------------------------------------------------
# Multiple random restarts
# ---------------------------------------------------------------------------

def train_with_restarts(
    states: Sequence[str],
    symbols: Sequence[str],
    obs: Sequence[int],
    n_restarts: int = 10,
    iterations: int = 100,
    seed: int = 0,
) -> Tuple[HMM, float, int]:
    """Run Baum-Welch from multiple random initialisations, keep the best.

    Returns (best_model, best_log_likelihood, best_restart_index).
    """
    best_hmm: Optional[HMM] = None
    best_ll = -math.inf
    best_idx = -1
    for r in range(n_restarts):
        hmm = HMM.random(states, symbols, seed=seed + r * 1000)
        ll, iters = baum_welch(hmm, obs, iterations=iterations)
        _log.debug("Restart %d: ll=%.4f (iters=%d)", r, ll, iters)
        if ll > best_ll:
            best_ll = ll
            best_hmm = hmm
            best_idx = r
    assert best_hmm is not None
    return best_hmm, best_ll, best_idx


# ---------------------------------------------------------------------------
# Constrained Baum-Welch (lock specific transitions or emissions)
# ---------------------------------------------------------------------------

def constrained_baum_welch(
    hmm: HMM,
    obs: Sequence[int],
    locked_transitions: Optional[Sequence[Tuple[int, int]]] = None,
    locked_emissions: Optional[Sequence[Tuple[int, int]]] = None,
    locked_pi: Optional[Sequence[int]] = None,
    iterations: int = 100,
    tol: float = 1e-6,
    smooth: float = 1e-10,
    verbose: bool = False,
) -> Tuple[float, int]:
    """Baum-Welch with some parameters *locked* (not updated).

    Parameters
    ----------
    locked_transitions : list of (i, j) — A[i][j] stays fixed
    locked_emissions : list of (i, k) — B[i][k] stays fixed
    locked_pi : list of i — pi[i] stays fixed

    Returns (final_log_likelihood, iterations_run).
    """
    N = hmm.n_states
    M = hmm.n_symbols
    T = len(obs)
    if T < 2:
        raise ValueError("Baum-Welch needs at least 2 observations")

    locked_A = set(locked_transitions or [])
    locked_B = set(locked_emissions or [])
    locked_pi = set(locked_pi or [])

    prev_ll = -math.inf
    iters_run = 0
    for it in range(iterations):
        iters_run = it + 1
        alpha, scales, ll = forward(hmm, obs)
        if ll == -math.inf:
            return ll, iters_run
        beta = backward(hmm, obs, scales)

        gamma = [[0.0] * N for _ in range(T)]
        for t in range(T):
            denom = sum(alpha[t][i] * beta[t][i] for i in range(N))
            if denom <= 0:
                denom = smooth
            for i in range(N):
                gamma[t][i] = alpha[t][i] * beta[t][i] / denom

        xi = [[[0.0] * N for _ in range(N)] for _ in range(T - 1)]
        for t in range(T - 1):
            ot1 = obs[t + 1]
            denom = 0.0
            for i in range(N):
                for j in range(N):
                    denom += alpha[t][i] * hmm.A[i][j] * hmm.B[j][ot1] * beta[t + 1][j]
            if denom <= 0:
                denom = smooth
            for i in range(N):
                for j in range(N):
                    xi[t][i][j] = (
                        alpha[t][i] * hmm.A[i][j] * hmm.B[j][ot1] * beta[t + 1][j]
                    ) / denom

        # Re-estimate with locks
        new_pi = list(hmm.pi)
        for i in range(N):
            if i not in locked_pi:
                new_pi[i] = gamma[0][i]
        # renormalise unlocked pi entries
        unlocked = [i for i in range(N) if i not in locked_pi]
        if unlocked:
            s = sum(new_pi[i] for i in unlocked)
            if s > 0:
                for i in unlocked:
                    new_pi[i] /= s

        new_A = [list(row) for row in hmm.A]
        for i in range(N):
            denom_a = sum(gamma[t][i] for t in range(T - 1))
            if denom_a <= 0:
                denom_a = smooth
            unlocked_j = [j for j in range(N) if (i, j) not in locked_A]
            for j in range(N):
                if (i, j) not in locked_A:
                    num = sum(xi[t][i][j] for t in range(T - 1))
                    new_A[i][j] = (num + smooth) / (denom_a + smooth * N)
            # renormalise unlocked entries in row i
            if unlocked_j:
                s = sum(new_A[i][j] for j in unlocked_j)
                if s > 0:
                    for j in unlocked_j:
                        new_A[i][j] /= s

        new_B = [list(row) for row in hmm.B]
        for i in range(N):
            denom_b = sum(gamma[t][i] for t in range(T))
            if denom_b <= 0:
                denom_b = smooth
            unlocked_k = [k for k in range(M) if (i, k) not in locked_B]
            for k in range(M):
                if (i, k) not in locked_B:
                    num = sum(gamma[t][i] for t in range(T) if obs[t] == k)
                    new_B[i][k] = (num + smooth) / (denom_b + smooth * M)
            if unlocked_k:
                s = sum(new_B[i][k] for k in unlocked_k)
                if s > 0:
                    for k in unlocked_k:
                        new_B[i][k] /= s

        # Save locked values so we can restore them after set_parameters
        # (which normalises all rows, including locked entries)
        locked_A_vals = {(i, j): hmm.A[i][j] for (i, j) in locked_A}
        locked_B_vals = {(i, k): hmm.B[i][k] for (i, k) in locked_B}
        locked_pi_vals = {i: hmm.pi[i] for i in locked_pi}

        # For locked pi: restore original and renormalise only unlocked entries
        for i, v in locked_pi_vals.items():
            new_pi[i] = v
        if unlocked_pi := [i for i in range(N) if i not in locked_pi]:
            s = sum(new_pi[i] for i in unlocked_pi)
            locked_sum = sum(locked_pi_vals.values())
            if s > 0 and locked_sum < 1.0:
                target = 1.0 - locked_sum
                for i in unlocked_pi:
                    new_pi[i] = new_pi[i] / s * target

        # For locked A: restore original and renormalise only unlocked entries in each row
        for (i, j), v in locked_A_vals.items():
            new_A[i][j] = v
        for i in range(N):
            unlocked_j = [j for j in range(N) if (i, j) not in locked_A]
            locked_sum = sum(v for (ii, jj), v in locked_A_vals.items() if ii == i)
            if unlocked_j:
                s = sum(new_A[i][j] for j in unlocked_j)
                if s > 0 and locked_sum < 1.0:
                    target = 1.0 - locked_sum
                    for j in unlocked_j:
                        new_A[i][j] = new_A[i][j] / s * target

        # For locked B: restore original and renormalise only unlocked entries
        for (i, k), v in locked_B_vals.items():
            new_B[i][k] = v
        for i in range(N):
            unlocked_k = [k for k in range(M) if (i, k) not in locked_B]
            locked_sum = sum(v for (ii, kk), v in locked_B_vals.items() if ii == i)
            if unlocked_k:
                s = sum(new_B[i][k] for k in unlocked_k)
                if s > 0 and locked_sum < 1.0:
                    target = 1.0 - locked_sum
                    for k in unlocked_k:
                        new_B[i][k] = new_B[i][k] / s * target

        hmm.set_parameters(A=new_A, B=new_B, pi=new_pi)
        # Restore locked values after set_parameters normalisation
        for (i, j), v in locked_A_vals.items():
            hmm.A[i][j] = v
        for (i, k), v in locked_B_vals.items():
            hmm.B[i][k] = v
        for i, v in locked_pi_vals.items():
            hmm.pi[i] = v
        hmm.reset_log_cache()
        if verbose:
            print(f"  iter {it + 1}: log-likelihood = {ll:.6f}")
        if abs(ll - prev_ll) < tol:
            break
        prev_ll = ll

    _, _, final_ll = forward(hmm, obs)
    return final_ll, iters_run


# ---------------------------------------------------------------------------
# Hyperparameter grid search
# ---------------------------------------------------------------------------

def grid_search(
    states: Sequence[str],
    symbols: Sequence[str],
    obs: Sequence[int],
    n_restarts: int = 5,
    iterations: int = 100,
    smooth_values: Optional[Sequence[float]] = None,
    tol_values: Optional[Sequence[float]] = None,
    seed: int = 0,
) -> List[Dict]:
    """Grid search over Baum-Welch hyperparameters (smooth, tol).

    Returns a list of dicts with keys: smooth, tol, best_ll, restart_idx.
    """
    if smooth_values is None:
        smooth_values = [1e-10, 1e-6, 1e-3]
    if tol_values is None:
        tol_values = [1e-4, 1e-6, 1e-8]
    results: List[Dict] = []
    for sm in smooth_values:
        for tl in tol_values:
            best_ll = -math.inf
            best_idx = -1
            for r in range(n_restarts):
                hmm = HMM.random(states, symbols, seed=seed + r)
                ll, _ = baum_welch(hmm, obs, iterations=iterations, tol=tl, smooth=sm)
                if ll > best_ll:
                    best_ll = ll
                    best_idx = r
            results.append({"smooth": sm, "tol": tl, "best_ll": best_ll, "restart_idx": best_idx})
            _log.debug("Grid sm=%e tol=%e ll=%.4f", sm, tl, best_ll)
    return results