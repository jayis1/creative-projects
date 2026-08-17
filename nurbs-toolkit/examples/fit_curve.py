"""Example: fit a B-spline curve to noisy data and render it."""
import math
from nurbs import fit_bspline_curve, curve_to_svg, arc_length

# Generate noisy sine-wave data.
data = [[i * 0.5, math.sin(i * 0.5) + 0.05 * ((i % 3) - 1), 0] for i in range(20)]

# Fit a cubic B-spline with 8 control points.
curve = fit_bspline_curve(data, degree=3, num_control_points=8)
print(f"Fitted curve: {curve}")
print(f"Arc length: {arc_length(curve):.4f}")

# Render to SVG.
svg = curve_to_svg(curve, samples=200, width=600, height=300, show_control_polygon=True)
with open("fitted_curve.svg", "w") as f:
    f.write(svg)
print("Wrote fitted_curve.svg")