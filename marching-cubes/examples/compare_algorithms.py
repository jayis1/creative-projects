#!/usr/bin/env python3
"""Compare MC vs MT vs Dual Contouring on a torus."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mcengine import (MarchingCubes, MarchingTetrahedra, DualContouring,
                      TorusSampler, analyze_mesh, write_obj)

bounds = ((-1.5, -1.5, -1.0), (1.5, 1.5, 1.0))
res = (32, 32, 32)

for name, cls in [("MC", MarchingCubes), ("MT", MarchingTetrahedra), ("DC", DualContouring)]:
    algo = cls(TorusSampler(1.0, 0.35), bounds=bounds, resolution=res)
    mesh = algo.run()
    d = analyze_mesh(mesh)
    print(f"{name}: V={mesh.num_vertices:5d}  F={mesh.num_faces:5d}  "
          f"watertight={d.is_watertight}  chi={d.euler_characteristic:3d}  "
          f"genus={d.genus}  area={d.surface_area:.3f}")
    write_obj(mesh, f"/tmp/torus_{name.lower()}.obj")