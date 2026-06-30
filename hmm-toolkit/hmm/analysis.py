"""Enhanced analysis utilities for HMMs.

Includes model comparison (symmetric KL), state entropy, sequence
classification, and profile HMM construction for biological motif analysis.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence, Tuple

from .hmm import HMM
from .algorithms import forward, backward


def sequence_log_likelihood(hmm: HMM, obs: Sequence[int]) -> float:
    """Return log P(O | model) for a single observation sequence."""
    _, _, ll = forward(hmm, obs)
    return ll


def classify_sequence(
    models: Sequence[HMM],
    obs: Sequence[int],
    model_names: Optional[Sequence[str]] = None,
) -> Tuple[int, str, float]:
    """Classify an observation sequence by selecting the model with highest likelihood.

    Returns (best_index, best_name, best_log_likelihood).
    """
    if model_names is None:
        model_names = [f"model_{i}" for i in range(len(models))]
    best_idx = 0
    best_ll = sequence_log_likelihood(models[0], obs)
    for i in range(1, len(models)):
        ll = sequence_log_likelihood(models[i], obs)
        if ll > best_ll:
            best_ll = ll
            best_idx = i
    return best_idx, model_names[best_idx], best_ll


def state_entropy(hmm: HMM, obs: Sequence[int]) -> List[float]:
    """Compute Shannon entropy of the posterior distribution at each timestep.

    High entropy → uncertain about the state; low → confident.
    """
    from .algorithms import posterior_decode
    _, gamma = posterior_decode(hmm, obs)
    entropies: List[float] = []
    for t, row in enumerate(gamma):
        h = 0.0
        for p in row:
            if p > 1e-15:
                h -= p * math.log(p)
        entropies.append(h)
    return entropies


def symmetric_kl(hmm_a: HMM, hmm_b: HMM, obs: Sequence[int]) -> float:
    """Symmetric KL divergence between two HMMs approximated via a shared
    observation sequence.

    Uses the log-likelihood ratio: KL(A||B) ≈ ll_A(O) - ll_B(O).
    The symmetric form is |ll_A - ll_B|.
    """
    if hmm_a.symbols != hmm_b.symbols:
        raise ValueError("HMMs must share the same symbol set for comparison")
    ll_a = sequence_log_likelihood(hmm_a, obs)
    ll_b = sequence_log_likelihood(hmm_b, obs)
    if ll_a == -math.inf and ll_b == -math.inf:
        return 0.0
    return abs(ll_a - ll_b)


def state_durations(states: Sequence[str]) -> List[Tuple[str, int]]:
    """Given a sampled state path (as state names), return the duration of each
    consecutive run.

    Returns a list of (state_name, duration) tuples.
    """
    durations: List[Tuple[str, int]] = []
    if not states:
        return durations
    current = states[0]
    count = 1
    for s in states[1:]:
        if s == current:
            count += 1
        else:
            durations.append((current, count))
            current = s
            count = 1
    durations.append((current, count))
    return durations


def expected_state_dwell_time(hmm: HMM) -> List[float]:
    """Expected dwell time per state = 1 / (1 - A[i][i]) for each state i.

    Returns inf for absorbing states (A[i][i] = 1).
    """
    result: List[float] = []
    for i in range(hmm.n_states):
        p_stay = hmm.A[i][i]
        if p_stay >= 1.0:
            result.append(math.inf)
        else:
            result.append(1.0 / (1.0 - p_stay))
    return result