"""Example: Visualisation features.

Demonstrates the ASCII visualisation tools: transition diagrams,
Viterbi path rendering, posterior heatmaps, and entropy sparklines.
"""

from __future__ import annotations

from hmm import HMM, generate_sequence
from hmm.viz import (
    transition_diagram,
    viterbi_path_visualization,
    posterior_heatmap,
    entropy_sparkline,
    format_model,
)


def main() -> None:
    print("=== HMM Visualisation Demo ===\n")

    # Weather model
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
    model = HMM(states, symbols, A, B, pi)

    # 1. Model parameters
    print("--- Model Parameters ---")
    print(format_model(model))

    # 2. Transition diagram
    print("\n--- Transition Diagram ---")
    print(transition_diagram(model))

    # 3. Generate and visualise a Viterbi path
    _, obs = generate_sequence(model, length=15, seed=42)
    print("\n--- Viterbi Path ---")
    print(viterbi_path_visualization(model, obs))

    # 4. Posterior heatmap
    print("\n--- Posterior Heatmap ---")
    print(posterior_heatmap(model, obs))

    # 5. Entropy sparkline
    print("\n--- Entropy Sparkline ---")
    print(entropy_sparkline(model, obs))


if __name__ == "__main__":
    main()