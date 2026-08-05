"""
Example 3: Persistence kernels for machine learning.

Demonstrates computing kernel matrices between persistence diagrams
using three different kernels: PSS, PWG, and Fisher.
"""

import math
import tda
from tda.diagram import PersistenceDiagram


def make_circle_diagram(n_points, noise=0.0):
    """Create a persistence diagram from a noisy circle."""
    import random
    random.seed(42)
    pts = []
    for i in range(n_points):
        angle = 2 * math.pi * i / n_points
        x = math.cos(angle) + random.uniform(-noise, noise)
        y = math.sin(angle) + random.uniform(-noise, noise)
        pts.append((x, y))

    vr = tda.VietorisRipsComplex(pts, max_scale=1.5, max_dimension=1)
    tree = vr.build()
    pers = tda.compute_persistence(tree, max_dimension=1, min_persistence=0.05)
    diagrams = tda.diagrams_from_persistence(pers)
    return diagrams.get(1, PersistenceDiagram(1))


def main():
    # Create three diagrams: clean circle, noisy circle, and line.
    d_clean = make_circle_diagram(12, noise=0.0)
    d_noisy = make_circle_diagram(12, noise=0.15)
    d_line = PersistenceDiagram(1)
    d_line.add(0.0, 1.0)

    diagrams = [d_clean, d_noisy, d_line]
    labels = ["clean circle", "noisy circle", "line"]

    print("Persistence diagrams:")
    for label, d in zip(labels, diagrams):
        print(f"  {label}: {d.num_features} features in H1")
    print()

    # Compute kernel matrices.
    for name, kernel_fn, kwargs in [
        ("PSS", tda.pss_kernel, {"sigma": 0.5}),
        ("PWG", tda.pwg_kernel, {"sigma": 0.5}),
        ("Fisher", tda.fisher_kernel, {"sigma": 0.5, "beta": 1.0}),
    ]:
        K = tda.kernel_matrix(diagrams, kernel_fn, **kwargs)
        print(f"{name} kernel matrix:")
        header = "          " + "  ".join(f"{l[:10]:>10}" for l in labels)
        print(header)
        for i, row in enumerate(K):
            print(f"{labels[i][:10]:>10}  " + "  ".join(f"{v:10.4f}" for v in row))
        print()


if __name__ == "__main__":
    main()