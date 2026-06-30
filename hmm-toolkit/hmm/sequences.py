"""Sequence generation and I/O helpers for HMMs."""

from __future__ import annotations

import json
import random
from typing import Dict, List, Optional, Sequence, Tuple

from .hmm import HMM


def generate_sequence(
    hmm: HMM, length: int, rng: Optional[random.Random] = None, seed: Optional[int] = None
) -> Tuple[List[str], List[str]]:
    """Sample a sequence from the HMM.

    Returns
    -------
    states : List[str]
        The hidden state path that was sampled.
    symbols : List[str]
        The emitted observation symbols.
    """
    if length < 0:
        raise ValueError("length must be non-negative")
    if rng is None:
        rng = random.Random(seed)

    states: List[str] = []
    obs: List[str] = []

    if length == 0:
        return states, obs

    # initial state
    state_idx = _sample_categorical(hmm.pi, rng)
    for t in range(length):
        states.append(hmm.states[state_idx])
        sym_idx = _sample_categorical(hmm.B[state_idx], rng)
        obs.append(hmm.symbols[sym_idx])
        if t < length - 1:
            state_idx = _sample_categorical(hmm.A[state_idx], rng)
    return states, obs


def _sample_categorical(probs: Sequence[float], rng: random.Random) -> int:
    """Sample an index from a categorical distribution given by ``probs``.

    Raises ValueError if all probabilities are zero (degenerate distribution).
    """
    total = sum(probs)
    if total <= 0:
        raise ValueError("Cannot sample: probabilities sum to zero")
    r = rng.random() * total  # scale by total in case probs aren't normalised
    cum = 0.0
    for i, p in enumerate(probs):
        cum += p
        if r < cum:
            return i
    # rounding fallback — return last valid index
    return len(probs) - 1


# ---------------------------------------------------------------------------
# JSON serialisation
# ---------------------------------------------------------------------------

def hmm_to_dict(hmm: HMM) -> Dict:
    """Serialise an HMM to a plain dict (JSON-compatible)."""
    return {
        "states": list(hmm.states),
        "symbols": list(hmm.symbols),
        "A": [list(r) for r in hmm.A],
        "B": [list(r) for r in hmm.B],
        "pi": list(hmm.pi),
    }


def hmm_from_dict(data: Dict) -> HMM:
    """Reconstruct an HMM from a dict produced by ``hmm_to_dict``."""
    return HMM(
        states=data["states"],
        symbols=data["symbols"],
        A=data["A"],
        B=data["B"],
        pi=data["pi"],
    )


def save_hmm(hmm: HMM, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(hmm_to_dict(hmm), f, indent=2)


def load_hmm(path: str) -> HMM:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return hmm_from_dict(data)


def save_observation_sequence(
    hmm: HMM, obs_symbols: Sequence[str], path: str
) -> None:
    """Save an observation sequence (as symbol names) to JSON."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"symbols": list(obs_symbols)}, f, indent=2)


def load_observation_sequence(path: str) -> List[str]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return list(data["symbols"])