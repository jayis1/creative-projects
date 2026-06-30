"""Example: Gaussian HMM for 1-D signal clustering.

Demonstrates a continuous-emission HMM that discovers two regimes
(low-variance and high-variance) in a synthetic 1-D signal.
"""

from __future__ import annotations

import random

from hmm.gaussian import GaussianHMM, random_gaussian_hmm


def main() -> None:
    print("=== Gaussian HMM — 1-D Signal Clustering ===\n")

    # Build a true 2-state Gaussian HMM
    states = ["Low", "High"]
    A = [[0.92, 0.08], [0.10, 0.90]]
    means = [[0.0], [10.0]]
    covs = [[[1.0]], [[2.0]]]
    pi = [0.8, 0.2]

    true_model = GaussianHMM(states, 1, A, means, covs, pi)
    print(f"True model: {true_model}")
    print(f"  means: {true_model.means}")

    # Generate a synthetic signal by sampling from the true model
    rng = random.Random(42)
    signal = []
    state = 0 if rng.random() < pi[0] else 1
    for _ in range(200):
        m = true_model.means[state][0]
        c = true_model.covs[state][0][0]
        signal.append([rng.gauss(m, c ** 0.5)])
        # transition
        if rng.random() < true_model.A[state][1 - state]:
            state = 1 - state

    print(f"\nGenerated {len(signal)} data points")

    # Train a fresh model
    fresh = random_gaussian_hmm(states, 1, seed=99)
    print(f"\nBefore training: means={fresh.means}")

    final_ll, iters = fresh.baum_welch(signal, iterations=50, verbose=False)
    print(f"After training ({iters} iters): means={fresh.means}")
    print(f"Final log-likelihood: {final_ll:.2f}")

    # Viterbi decode
    path, logp = fresh.viterbi(signal)
    low_count = path.count(0)
    high_count = path.count(1)
    print(f"\nViterbi path: {low_count} Low, {high_count} High")
    print(f"Viterbi log-prob: {logp:.2f}")


if __name__ == "__main__":
    main()