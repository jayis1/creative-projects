"""Example: Lyapunov exponent proxy — measuring sensitivity to initial conditions.

This example runs two copies of Rule 30 from slightly different initial states
and measures the Hamming distance over time. An exponentially growing distance
indicates chaos (positive Lyapunov exponent).
"""
from cellular_automaton import ElementaryRule, lyapunov_proxy


def main():
    rule = ElementaryRule(30)
    distances = lyapunov_proxy(rule, width=100, steps=50, perturbation=1)

    print("Lyapunov Proxy — Rule 30 (chaotic)")
    print("Hamming distance between perturbed copies over time:\n")
    for i, d in enumerate(distances):
        bar = "█" * min(d, 50)
        print(f"  Step {i:2d}: {d:4d} {bar}")

    print(f"\nFinal distance: {distances[-1]} / {100} cells")
    print(f"Growth ratio: {distances[-1] / max(distances[0], 1):.2f}x")
    print("\nRule 30 shows exponential divergence — hallmark of chaos.")


if __name__ == "__main__":
    main()