"""Example: Advanced training with cross-validation and random restarts.

Demonstrates model selection (choosing the number of hidden states)
via k-fold cross-validation, and training with multiple random restarts
to avoid local optima.
"""

from __future__ import annotations

import random

from hmm import HMM, generate_sequence, forward
from hmm.training import (
    k_fold_cross_validation,
    summarize_cv_results,
    train_with_restarts,
    grid_search,
)


def main() -> None:
    print("=== Advanced Training — CV & Restarts ===\n")

    # Build a true 3-state model
    states = ["S0", "S1", "S2"]
    symbols = ["A", "B", "C", "D"]
    A = [[0.8, 0.15, 0.05], [0.1, 0.8, 0.1], [0.05, 0.15, 0.8]]
    B = [[0.7, 0.1, 0.1, 0.1], [0.1, 0.7, 0.1, 0.1], [0.1, 0.1, 0.1, 0.7]]
    pi = [0.5, 0.3, 0.2]
    true_model = HMM(states, symbols, A, B, pi)

    # Generate multiple observation sequences
    rng = random.Random(42)
    obs_seqs = []
    for _ in range(20):
        _, syms = generate_sequence(true_model, length=50, rng=rng)
        obs_seqs.append(true_model.observation_sequence(syms))

    # 1) Cross-validation: try 2, 3, 4 states
    print("--- K-Fold Cross-Validation ---")
    results = k_fold_cross_validation(
        states, symbols, obs_seqs,
        n_states_options=[2, 3, 4],
        k=5, iterations=30, seed=42,
    )
    summary = summarize_cv_results(results)
    print(f"{'n_states':>10} {'mean_train_ll':>15} {'mean_val_ll':>15}")
    for ns in sorted(summary):
        s = summary[ns]
        print(f"{ns:>10} {s['mean_train_ll']:>15.2f} {s['mean_val_ll']:>15.2f}")
    best_ns = max(summary, key=lambda ns: summary[ns]["mean_val_ll"])
    print(f"\nRecommended: {best_ns} states")

    # 2) Random restarts on a single long sequence
    print("\n--- Random Restarts ---")
    long_obs = obs_seqs[0]
    best_hmm, best_ll, best_idx = train_with_restarts(
        states, symbols, long_obs,
        n_restarts=8, iterations=50, seed=0,
    )
    print(f"Best restart: #{best_idx}, log-likelihood: {best_ll:.4f}")

    # 3) Grid search over smoothing/tolerance
    print("\n--- Grid Search ---")
    grid = grid_search(
        states, symbols, long_obs,
        n_restarts=3, iterations=30, seed=0,
    )
    print(f"{'smooth':>12} {'tol':>12} {'best_ll':>12}")
    for r in grid:
        print(f"{r['smooth']:>12.2e} {r['tol']:>12.2e} {r['best_ll']:>12.4f}")
    best = max(grid, key=lambda r: r["best_ll"])
    print(f"\nBest: smooth={best['smooth']:.2e}, tol={best['tol']:.2e}")


if __name__ == "__main__":
    main()