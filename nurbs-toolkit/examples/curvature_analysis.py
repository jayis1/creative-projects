"""Example: curvature analysis of a NURBS circle."""
import math
from nurbs import make_circle, curvature, curvature_plot_data, max_curvature, find_inflections

# Create a unit circle.
circle = make_circle(1.0, (0, 0), 4)
print("=== Curvature Analysis of a Unit Circle ===")
print(f"Expected curvature: 1.0 (κ = 1/R)")
print()

# Curvature at several points.
for u in [0.0, 0.5, 1.0, 1.5, 2.0, 3.0]:
    k = curvature(circle, u)
    p = circle.evaluate(u)
    print(f"  u={u:.1f}: point=({p[0]:.4f}, {p[1]:.4f}), κ={k:.6f}")

print()

# Maximum curvature.
u_max, k_max = max_curvature(circle, samples=1000)
print(f"Max curvature: κ={k_max:.6f} at u={u_max:.4f}")

# Generate curvature plot data.
us, kappas = curvature_plot_data(circle, samples=50)
print(f"\nCurvature plot: {len(us)} samples")
print(f"  Mean κ: {sum(kappas)/len(kappas):.6f}")
print(f"  Min  κ: {min(kappas):.6f}")
print(f"  Max  κ: {max(kappas):.6f}")

# Inflection points.
infl = find_inflections(circle, samples=1000)
print(f"\nInflection points: {len(infl)} found")
for u in infl:
    print(f"  u = {u:.6f}")