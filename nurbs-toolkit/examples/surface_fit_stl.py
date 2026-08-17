"""Example: surface fitting and STL export."""
import math
from nurbs import (
    fit_bspline_surface, tessellate_surface,
    export_stl_ascii, export_stl_binary, export_obj,
)

# Generate a saddle-shaped data grid.
print("=== Surface Fitting: Saddle Shape ===")
points = []
for i in range(10):
    row = []
    for j in range(10):
        x = i * 0.3
        y = j * 0.3
        z = x * y * 0.1  # saddle
        row.append([x, y, z])
    points.append(row)

print(f"Data grid: {len(points)}x{len(points[0])} points")

# Fit a bicubic B-spline surface.
surf = fit_bspline_surface(points, degree_u=3, degree_v=3,
                            num_ctrl_u=6, num_ctrl_v=6)
print(f"Fitted surface: {surf}")

# Tessellate and export.
verts, faces = tessellate_surface(surf, 30, 30)
print(f"Tessellated: {len(verts)} vertices, {len(faces)} faces")

# Export to OBJ.
obj = export_obj(verts, faces)
with open("saddle.obj", "w") as f:
    f.write(obj)
print("Wrote saddle.obj")

# Export to ASCII STL.
stl = export_stl_ascii(verts, faces)
with open("saddle_ascii.stl", "w") as f:
    f.write(stl)
print("Wrote saddle_ascii.stl")

# Export to binary STL.
data = export_stl_binary(verts, faces)
with open("saddle_binary.stl", "wb") as f:
    f.write(data)
print(f"Wrote saddle_binary.stl ({len(data)} bytes)")