"""
Example 6: Alpha complex and sparse Rips for efficient computation.

Compares the full Vietoris–Rips complex with the alpha complex and
the sparse (k-NN truncated) Rips complex in terms of simplex count and
persistence results.
"""

import math
import time
import tda


def main():
    # Generate a moderate point cloud.
    pts = [(math.cos(2*math.pi*i/20), math.sin(2*math.pi*i/20))
           for i in range(20)]
    # Add some interior points.
    pts += [(0.0, 0.0), (0.3, 0.0), (-0.3, 0.0), (0.0, 0.3), (0.0, -0.3)]

    print(f"Point cloud: {len(pts)} points")
    print()

    # Full Rips complex.
    t0 = time.perf_counter()
    vr = tda.VietorisRipsComplex(pts, max_scale=1.5, max_dimension=2)
    tree_vr = vr.build()
    t_vr = time.perf_counter() - t0
    pers_vr = tda.compute_persistence(tree_vr, max_dimension=2, min_persistence=0.01)

    print(f"Full Rips:       {tree_vr.num_simplices():>5} simplices, "
          f"{t_vr*1000:.1f}ms")
    for dim in sorted(pers_vr):
        n = len(pers_vr[dim])
        print(f"  H{dim}: {n} features")

    # Alpha complex.
    t0 = time.perf_counter()
    ac = tda.AlphaComplex(pts, alpha=0.75, max_dimension=2)
    tree_ac = ac.build()
    t_ac = time.perf_counter() - t0
    pers_ac = tda.compute_persistence(tree_ac, max_dimension=2, min_persistence=0.01)

    print(f"\nAlpha complex:   {tree_ac.num_simplices():>5} simplices, "
          f"{t_ac*1000:.1f}ms")
    for dim in sorted(pers_ac):
        n = len(pers_ac[dim])
        print(f"  H{dim}: {n} features")

    # Sparse Rips (k=5 nearest neighbours).
    t0 = time.perf_counter()
    sr = tda.SparseRipsComplex(pts, k=5, max_scale=1.5, max_dimension=2)
    tree_sr = sr.build()
    t_sr = time.perf_counter() - t0
    pers_sr = tda.compute_persistence(tree_sr, max_dimension=2, min_persistence=0.01)

    print(f"\nSparse Rips (k=5): {tree_sr.num_simplices():>5} simplices, "
          f"{t_sr*1000:.1f}ms")
    for dim in sorted(pers_sr):
        n = len(pers_sr[dim])
        print(f"  H{dim}: {n} features")

    # Clearing reduction.
    t0 = time.perf_counter()
    pers_clr = tda.compute_persistence_clearing(tree_vr, max_dimension=2,
                                                  min_persistence=0.01)
    t_clr = time.perf_counter() - t0

    print(f"\nClearing reduction: {t_clr*1000:.1f}ms (same results as standard)")
    for dim in sorted(pers_clr):
        n = len(pers_clr[dim])
        print(f"  H{dim}: {n} features")


if __name__ == "__main__":
    main()