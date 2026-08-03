#!/usr/bin/env python3
"""Demonstrate Loop subdivision: render a coarse sphere and subdivide it smooth."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcengine import (
    MarchingCubes, SphereSampler, analyze_mesh, write_obj,
    loop_subdivide, subdivide_n, render_ascii_preview,
)

# Render a low-resolution sphere
mc = MarchingCubes(SphereSampler(1.0), resolution=(8, 8, 8))
mesh = mc.run()
d0 = analyze_mesh(mesh)
print(f"Original:     V={mesh.num_vertices:4d}  F={mesh.num_faces:4d}  chi={d0.euler_characteristic}")

# 1 iteration of Loop subdivision (4x faces)
sub1 = loop_subdivide(mesh)
d1 = analyze_mesh(sub1)
print(f"Subdivide 1x: V={sub1.num_vertices:4d}  F={sub1.num_faces:4d}  chi={d1.euler_characteristic}")

# 2 iterations (16x faces)
sub2 = subdivide_n(mesh, 2)
d2 = analyze_mesh(sub2)
print(f"Subdivide 2x: V={sub2.num_vertices:4d}  F={sub2.num_faces:4d}  chi={d2.euler_characteristic}")

# 3 iterations (64x faces)
sub3 = subdivide_n(mesh, 3)
d3 = analyze_mesh(sub3)
print(f"Subdivide 3x: V={sub3.num_vertices:4d}  F={sub3.num_faces:4d}  chi={d3.euler_characteristic}")

print(f"\nEuler characteristic preserved: {d0.euler_characteristic} == {d3.euler_characteristic}")

# Preview
print("\nOriginal (8³):")
print(render_ascii_preview(mesh, width=40, height=14))

print("\nSubdivided 3x:")
print(render_ascii_preview(sub3, width=40, height=14))

write_obj(mesh, "/tmp/sphere_coarse.obj")
write_obj(sub3, "/tmp/sphere_smooth.obj")
print("\nExported: /tmp/sphere_coarse.obj, /tmp/sphere_smooth.obj")