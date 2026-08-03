#!/usr/bin/env python3
"""Render a sphere via Marching Cubes and export to OBJ + show ASCII preview."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mcengine import MarchingCubes, SphereSampler, analyze_mesh, write_obj, render_ascii_preview

mc = MarchingCubes(SphereSampler(1.0), resolution=(24, 24, 24))
mesh = mc.run()
d = analyze_mesh(mesh)
print(d.summary())
print()
print(render_ascii_preview(mesh, width=50, height=20))