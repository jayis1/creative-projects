"""Example: create an exact NURBS circle and verify it."""
import math
from nurbs import make_circle, tessellate_curve

circle = make_circle(radius=2.0, center=(0, 0), segments=4)
print(f"Circle: {circle}")
print(f"Parameter range: {circle.parameter_range}")

# Verify radius at multiple points.
for u in [0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0]:
    p = circle.evaluate(u)
    r = math.hypot(p[0], p[1])
    print(f"  u={u:.1f}: point=({p[0]:.4f}, {p[1]:.4f}), radius={r:.6f}")