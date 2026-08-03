#!/usr/bin/env python3
"""Demonstrate mesh transforms: render a sphere, then translate, scale, rotate, and mirror it."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcengine import (
    MarchingCubes, SphereSampler, analyze_mesh, write_obj,
    translate, scale, rotate_z, mirror, normalize_size, merge_meshes,
)

# Render base sphere
mc = MarchingCubes(SphereSampler(1.0), resolution=(24, 24, 24))
sphere = mc.run()
print(f"Base sphere:  V={sphere.num_vertices:4d}  F={sphere.num_faces:4d}")

# Translate
moved = translate(sphere, 3, 0, 0)
print(f"Translated:   V={moved.num_vertices:4d}  F={moved.num_faces:4d}  (shifted +3 in x)")

# Scale
big = scale(sphere, 2, 2, 2)
print(f"Scaled 2x:    V={big.num_vertices:4d}  F={big.num_faces:4d}  (2x larger)")

# Rotate
rotated = rotate_z(sphere, 1.5708)  # ~90 degrees
print(f"Rotated 90°Z: V={rotated.num_vertices:4d}  F={rotated.num_faces:4d}")

# Mirror
mirrored = mirror(sphere, "x")
print(f"Mirrored X:   V={mirrored.num_vertices:4d}  F={mirrored.num_faces:4d}")

# Merge: sphere + mirrored sphere = a double sphere
merged = merge_meshes([sphere, mirrored])
print(f"Merged:       V={merged.num_vertices:4d}  F={merged.num_faces:4d}")

# Normalize to unit size
normalized = normalize_size(merged, target_size=4.0)
print(f"Normalized:   V={normalized.num_vertices:4d}  F={normalized.num_faces:4d}")

write_obj(merged, "/tmp/merged_spheres.obj")
print("\nExported merged mesh to /tmp/merged_spheres.obj")