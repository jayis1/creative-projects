"""
Example 4: Batch processing and feature extraction.

Shows how to process multiple point clouds and extract vectorized
features for downstream ML pipelines.
"""

import math
import json
import tda


def make_shape(shape_type, n=10):
    """Generate a point cloud for a given shape type."""
    if shape_type == "circle":
        return [(math.cos(2*math.pi*i/n), math.sin(2*math.pi*i/n))
                for i in range(n)]
    elif shape_type == "line":
        return [(i / n, 0) for i in range(n)]
    elif shape_type == "square":
        pts = []
        per_side = n // 4
        for i in range(per_side):
            t = i / per_side
            pts.append((t, 0))
            pts.append((1, t))
            pts.append((1 - t, 1))
            pts.append((0, 1 - t))
        return pts
    else:
        raise ValueError(f"Unknown shape: {shape_type}")


def main():
    # Create multiple point clouds of different shapes.
    shapes = ["circle", "line", "circle", "square", "line"]
    point_clouds = [make_shape(s, n=12) for s in shapes]

    print(f"Processing {len(point_clouds)} point clouds...")
    for i, s in enumerate(shapes):
        print(f"  {i}: {s} ({len(point_clouds[i])} points)")

    # Batch process: compute persistence and statistics.
    bp = tda.BatchProcessor(
        point_clouds,
        max_scale=2.0,
        max_dimension=1,
        min_persistence=0.05,
    )

    print("\n--- Statistics ---")
    stats = bp.run_with_stats()
    for i, s in enumerate(stats):
        h0 = s.get(0, {})
        h1 = s.get(1, {})
        print(f"  Cloud {i} ({shapes[i]:>6}): "
              f"H0={h0.get('num_features', 0)}, "
              f"H1={h1.get('num_features', 0)}, "
              f"entropy_H1={h1.get('entropy', 0):.4f}")

    # Extract vectorized features for ML.
    print("\n--- Feature vectors (max_features=5) ---")
    vectors = bp.run_with_vectors(max_features=5)
    for i, vec in enumerate(vectors):
        print(f"  Cloud {i} ({shapes[i]:>6}): dim={len(vec)}, "
              f"first 6: {vec[:6]}")

    # Streaming: process one at a time.
    print("\n--- Streaming ---")
    for i, diag in enumerate(tda.stream_persistence(
        point_clouds, max_scale=2.0, max_dimension=1, min_persistence=0.05
    )):
        dims = sorted(diag.keys())
        counts = {d: diag[d].num_features for d in dims}
        print(f"  Cloud {i} ({shapes[i]:>6}): {counts}")


if __name__ == "__main__":
    main()