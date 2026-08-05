"""
Example 1: Basic persistent homology of geometric shapes.

Demonstrates computing persistent homology for:
- A circle (expect H0=1, H1=1)
- A filled triangle (expect H0=1, no H1)
- Two disconnected clusters (expect H0=2)
"""

import math
import tda


def circle_example():
    """8 points on a unit circle: H0=1, H1=1 essential."""
    print("=" * 60)
    print("Circle (8 points on unit circle)")
    print("=" * 60)

    pts = [(math.cos(2 * math.pi * i / 8), math.sin(2 * math.pi * i / 8))
          for i in range(8)]

    vr = tda.VietorisRipsComplex(pts, max_scale=1.0, max_dimension=1)
    tree = vr.build()
    pers = tda.compute_persistence(tree, max_dimension=1, min_persistence=0.01)
    diagrams = tda.diagrams_from_persistence(pers)

    print(tda.barcode_string(diagrams))
    print()

    # Show statistics
    print(tda.statistics_table(diagrams))
    print()


def triangle_example():
    """Filled triangle: H0=1 essential, H1=0."""
    print("=" * 60)
    print("Filled triangle (equilateral)")
    print("=" * 60)

    pts = [(0, 0), (1, 0), (0.5, 0.866)]
    vr = tda.VietorisRipsComplex(pts, max_scale=2.0, max_dimension=2)
    tree = vr.build()
    pers = tda.compute_persistence(tree, max_dimension=2, min_persistence=0.01)
    diagrams = tda.diagrams_from_persistence(pers)

    print(tda.plot_diagram_ascii(diagrams))
    print()


def clusters_example():
    """Two disconnected clusters: H0=2 essential."""
    print("=" * 60)
    print("Two disconnected clusters")
    print("=" * 60)

    pts = [
        (0, 0), (0.5, 0), (0.25, 0.4),    # cluster 1
        (5, 5), (5.5, 5), (5.25, 5.4),    # cluster 2
    ]
    vr = tda.VietorisRipsComplex(pts, max_scale=1.0, max_dimension=0)
    tree = vr.build()
    pers = tda.compute_persistence(tree, max_dimension=0)

    h0 = pers.get(0, [])
    essential = [p for p in h0 if p[1] == float('inf')]
    print(f"H0 features: {len(h0)} (essential: {len(essential)})")
    print(f"Expected: 2 essential (one per cluster)")
    print()


if __name__ == "__main__":
    circle_example()
    triangle_example()
    clusters_example()