"""Example: curve intersection and trimming."""
from nurbs import BSplineCurve, NURBSCurve, intersect_curves, TrimmingLoop, make_circle

print("=== Curve Intersection ===")

# Two curves that cross.
c1 = BSplineCurve(1, [0, 0, 1, 1], [[0, 0, 0], [1, 1, 0]])
c2 = BSplineCurve(1, [0, 0, 1, 1], [[0, 1, 0], [1, 0, 0]])

results = intersect_curves(c1, c2, samples=50)
print(f"Found {len(results)} intersection(s):")
for u, v, p in results:
    print(f"  u={u:.4f}, v={v:.4f}, point={p}")

print()
print("=== Trimming Loop ===")

# Create a square trimming loop in parameter space.
segs = [
    BSplineCurve(1, [0, 0, 1, 1], [[0.2, 0.2], [0.8, 0.2]]),
    BSplineCurve(1, [0, 0, 1, 1], [[0.8, 0.2], [0.8, 0.8]]),
    BSplineCurve(1, [0, 0, 1, 1], [[0.8, 0.8], [0.2, 0.8]]),
    BSplineCurve(1, [0, 0, 1, 1], [[0.2, 0.8], [0.2, 0.2]]),
]
loop = TrimmingLoop(segs)

# Check points.
test_points = [(0.5, 0.5), (0.1, 0.1), (0.9, 0.9), (0.5, 0.2)]
for u, v in test_points:
    inside = loop.is_inside(u, v)
    print(f"  ({u}, {v}): {'inside' if inside else 'outside'}")