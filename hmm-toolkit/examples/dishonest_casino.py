"""Example: the classic Dishonest Casino HMM.

A dealer sometimes uses a loaded die. We model two hidden states:
  - F: fair die   (emits 1-6 uniformly)
  - L: loaded die (emits 6 with 50% probability, others 10% each)

This script builds the model, generates a sample, runs Viterbi, and trains
a fresh random HMM with Baum-Welch to recover the parameters.
"""

from __future__ import annotations

import random

from hmm import HMM, forward, viterbi, baum_welch, generate_sequence


def build_casino_hmm() -> HMM:
    states = ["F", "L"]
    symbols = ["1", "2", "3", "4", "5", "6"]
    A = [
        [0.95, 0.05],  # F -> F/L
        [0.10, 0.90],  # L -> F/L
    ]
    B = [
        [1 / 6] * 6,              # fair
        [0.10, 0.10, 0.10, 0.10, 0.10, 0.50],  # loaded
    ]
    pi = [0.5, 0.5]
    return HMM(states, symbols, A, B, pi)


def main() -> None:
    model = build_casino_hmm()
    print("=== Dishonest Casino HMM ===")
    print(repr(model))

    # generate
    rng = random.Random(42)
    true_states, obs_symbols = generate_sequence(model, length=300, rng=rng)
    print(f"\nGenerated 300 rolls. Loaded-state fraction: "
          f"{true_states.count('L') / len(true_states):.2f}")

    # viterbi
    obs = model.observation_sequence(obs_symbols)
    path, logp = viterbi(model, obs)
    decoded = [model.states[i] for i in path]
    matches = sum(1 for a, b in zip(true_states, decoded) if a == b)
    print(f"Viterbi accuracy: {matches}/{len(true_states)} = {matches / len(true_states):.2%}")

    # forward log-likelihood
    _, _, ll = forward(model, obs)
    print(f"Log-likelihood under true model: {ll:.2f}")

    # train a fresh random model from the observations
    fresh = HMM.random(["F", "L"], ["1", "2", "3", "4", "5", "6"], seed=7)
    final_ll, iters = baum_welch(fresh, obs, iterations=200, tol=1e-5, verbose=False)
    print(f"\nBaum-Welch converged in {iters} iters, final LL={final_ll:.2f}")
    print("Recovered transition matrix:")
    for i, s in enumerate(fresh.states):
        print(f"  {s}: " + "  ".join(f"{v:.3f}" for v in fresh.A[i]))
    print("Recovered emission matrix:")
    for i, s in enumerate(fresh.states):
        print(f"  {s}: " + "  ".join(f"{v:.3f}" for v in fresh.B[i]))


if __name__ == "__main__":
    main()