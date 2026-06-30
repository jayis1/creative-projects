"""Example: Weather prediction with HMMs.

Hidden states: Sunny, Cloudy, Rainy
Observations: Walk, Shop, Clean

We build a known model, generate data, then train a fresh model from scratch
to recover the parameters.
"""

from __future__ import annotations

import random

from hmm import HMM, generate_sequence, forward, viterbi, baum_welch, posterior_decode
from hmm.analysis import state_entropy, expected_state_dwell_time


def build_weather_hmm() -> HMM:
    states = ["Sunny", "Cloudy", "Rainy"]
    symbols = ["Walk", "Shop", "Clean"]
    A = [
        [0.70, 0.25, 0.05],
        [0.30, 0.40, 0.30],
        [0.10, 0.30, 0.60],
    ]
    B = [
        [0.60, 0.30, 0.10],
        [0.20, 0.50, 0.30],
        [0.05, 0.15, 0.80],
    ]
    pi = [0.60, 0.30, 0.10]
    return HMM(states, symbols, A, B, pi)


def main() -> None:
    model = build_weather_hmm()
    print("=== Weather HMM ===")
    print(repr(model))

    # Expected dwell times
    dwell = expected_state_dwell_time(model)
    print("\nExpected dwell times:")
    for s, d in zip(model.states, dwell):
        print(f"  {s:>8}: {d:.2f} steps")

    # Generate data
    rng = random.Random(123)
    true_states, obs_syms = generate_sequence(model, length=200, rng=rng)
    obs = model.observation_sequence(obs_syms)

    # Viterbi decode
    path, logp = viterbi(model, obs)
    decoded = [model.states[i] for i in path]
    matches = sum(1 for a, b in zip(true_states, decoded) if a == b)
    print(f"\nViterbi accuracy: {matches}/200 = {matches/200:.1%}")

    # Posterior entropy (uncertainty)
    entropies = state_entropy(model, obs)
    avg_entropy = sum(entropies) / len(entropies)
    print(f"Average posterior entropy: {avg_entropy:.4f} bits")

    # Train from scratch
    fresh = HMM.random(["Sunny", "Cloudy", "Rainy"], ["Walk", "Shop", "Clean"], seed=99)
    _, _, ll_before = forward(fresh, obs)
    final_ll, iters = baum_welch(fresh, obs, iterations=200, tol=1e-5)
    print(f"\nBaum-Welch: {iters} iterations, LL {ll_before:.2f} -> {final_ll:.2f}")


if __name__ == "__main__":
    main()