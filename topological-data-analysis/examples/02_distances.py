"""
Example 2: Distance metrics between persistence diagrams.

Shows how to compute bottleneck, Wasserstein, and Hausdorff distances
between two persistence diagrams.
"""

import tda
from tda.diagram import PersistenceDiagram


def main():
    # Create two slightly different diagrams.
    d1 = PersistenceDiagram(0)
    d1.add(0.0, 1.0)
    d1.add(0.0, 2.0)
    d1.add(0.0, float('inf'))

    d2 = PersistenceDiagram(0)
    d2.add(0.0, 1.5)
    d2.add(0.0, 2.5)
    d2.add(0.0, float('inf'))

    print("Diagram 1:", [f"({p.birth:.1f}, {p.death:.1f})" for p in d1.pairs])
    print("Diagram 2:", [f"({p.birth:.1f}, {p.death:.1f})" for p in d2.pairs])
    print()

    bn = tda.bottleneck_distance(d1, d2)
    print(f"Bottleneck distance:      {bn:.6f}")

    w1 = tda.wasserstein_distance(d1, d2, p=1.0)
    print(f"Wasserstein distance (p=1): {w1:.6f}")

    w2 = tda.wasserstein_distance(d1, d2, p=2.0)
    print(f"Wasserstein distance (p=2): {w2:.6f}")

    w_inf = tda.wasserstein_distance(d1, d2, p=float('inf'))
    print(f"Wasserstein distance (p=∞): {w_inf:.6f}")

    hs = tda.hausdorff_distance(d1, d2)
    print(f"Hausdorff distance:       {hs:.6f}")

    print()
    print("--- Statistics ---")
    s1 = tda.diagram_statistics(d1)
    s2 = tda.diagram_statistics(d2)
    print(f"D1: {s1['num_features']} features, entropy={tda.persistent_entropy(d1):.4f}")
    print(f"D2: {s2['num_features']} features, entropy={tda.persistent_entropy(d2):.4f}")


if __name__ == "__main__":
    main()