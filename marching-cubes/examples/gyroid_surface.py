#!/usr/bin/env python3
"""Mesh the gyroid minimal surface and export to STL."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mcengine import MarchingCubes, GyroidSampler, analyze_mesh, write_stl_binary

mc = MarchingCubes(GyroidSampler(), bounds=((-3, -3, -3), (3, 3, 3)), resolution=(48, 48, 48))
mesh = mc.run()
d = analyze_mesh(mesh)
print(f"Gyroid: V={mesh.num_vertices} F={mesh.num_faces}")
print(f"Surface area: {d.surface_area:.3f}")
write_stl_binary(mesh, "/tmp/gyroid.stl")
print("Exported to /tmp/gyroid.stl")