#!/usr/bin/env python3
"""Demonstrate mesh file I/O: write a mesh, read it back, convert formats."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcengine import (
    MarchingCubes, TorusSampler, analyze_mesh,
    write_obj, write_stl_binary, write_ply_ascii, write_ply_binary,
    read_obj, read_stl_binary, read_ply_ascii, read_mesh,
)

# Render a torus
mc = MarchingCubes(
    TorusSampler(1.0, 0.35),
    bounds=((-1.5, -1.5, -1.0), (1.5, 1.5, 1.0)),
    resolution=(24, 24, 24),
)
mesh = mc.run()
d = analyze_mesh(mesh)
print(f"Original mesh:  V={mesh.num_vertices:4d}  F={mesh.num_faces:4d}  "
      f"chi={d.euler_characteristic}  watertight={d.is_watertight}")

# Write in multiple formats
write_obj(mesh, "/tmp/torus.obj")
write_stl_binary(mesh, "/tmp/torus.stl")
write_ply_ascii(mesh, "/tmp/torus.ply")  # ASCII for round-trip reading
write_ply_binary(mesh, "/tmp/torus_bin.ply")
print("\nExported: /tmp/torus.obj, /tmp/torus.stl, /tmp/torus.ply")

# Read back OBJ
loaded_obj = read_obj("/tmp/torus.obj")
d_obj = analyze_mesh(loaded_obj)
print(f"\nRead OBJ:       V={loaded_obj.num_vertices:4d}  F={loaded_obj.num_faces:4d}  "
      f"chi={d_obj.euler_characteristic}")

# Read back STL (binary)
loaded_stl = read_stl_binary("/tmp/torus.stl")
d_stl = analyze_mesh(loaded_stl)
print(f"Read STL:       V={loaded_stl.num_vertices:4d}  F={loaded_stl.num_faces:4d}  "
      f"chi={d_stl.euler_characteristic}")

# Read back PLY
loaded_ply = read_ply_ascii("/tmp/torus.ply")
d_ply = analyze_mesh(loaded_ply)
print(f"Read PLY:       V={loaded_ply.num_vertices:4d}  F={loaded_ply.num_faces:4d}  "
      f"chi={d_ply.euler_characteristic}")

# Auto-detect format
auto = read_mesh("/tmp/torus.obj")
print(f"\nAuto-detect:    read {auto.num_faces} faces from .obj")

# Convert OBJ to STL
print("\nConverting OBJ -> STL via auto-detect readers...")
mesh2 = read_mesh("/tmp/torus.obj")
write_stl_binary(mesh2, "/tmp/torus_converted.stl")
print("Converted to /tmp/torus_converted.stl")