"""Example: offset curves, splitting, and reversal."""
import math
from nurbs import (
    BSplineCurve, generate_clamped_uniform_knot_vector,
    offset_curve, split_curve, reverse_curve, concatenate_curves,
    tessellate_curve, arc_length,
)

# Create a cubic B-spline curve.
cps = [[0, 0, 0], [1, 3, 0], [3, 3, 0], [4, 0, 0]]
U = generate_clamped_uniform_knot_vector(3, 3)
curve = BSplineCurve(3, U, cps)
print("=== Original Curve ===")
print(f"  Degree: {curve.degree}")
print(f"  Range: {curve.parameter_range}")
print(f"  Arc length: {arc_length(curve):.4f}")

# Offset curve.
print("\n=== Offset Curve (distance=0.5) ===")
offset_pts = offset_curve(curve, 0.5, samples=20)
print(f"  {len(offset_pts)} offset points")
print(f"  First: {offset_pts[0]}")
print(f"  Last:  {offset_pts[-1]}")

# Split at u=0.5.
print("\n=== Split at u=0.5 ===")
left, right = split_curve(curve, 0.5)
print(f"  Left:  degree={left.degree}, range={left.parameter_range}, cps={len(left.control_points)}")
print(f"  Right: degree={right.degree}, range={right.parameter_range}, cps={len(right.control_points)}")
# Verify junction.
p_left = left.evaluate(left.parameter_range[1])
p_right = right.evaluate(right.parameter_range[0])
print(f"  Junction: left_end={p_left}, right_start={p_right}")

# Reverse.
print("\n=== Reversed Curve ===")
rev = reverse_curve(curve)
print(f"  Range: {rev.parameter_range}")
p_start = rev.evaluate(rev.parameter_range[0])
p_end = rev.evaluate(rev.parameter_range[1])
print(f"  Start (was end): {p_start}")
print(f"  End (was start): {p_end}")

# Concatenate.
print("\n=== Concatenate Two Curves ===")
cp2 = [[4, 0, 0], [5, -3, 0], [7, -3, 0], [8, 0, 0]]
curve2 = BSplineCurve(3, U, cp2)
merged = concatenate_curves(curve, curve2)
print(f"  Merged: degree={merged.degree}, cps={len(merged.control_points)}")
p0 = merged.evaluate(merged.parameter_range[0])
p1 = merged.evaluate(merged.parameter_range[1])
print(f"  Start: {p0}")
print(f"  End:   {p1}")