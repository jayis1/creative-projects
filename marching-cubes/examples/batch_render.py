#!/usr/bin/env python3
"""Demonstrate batch rendering from a JSON config file."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcengine.batch import render_config

config_path = os.path.join(os.path.dirname(__file__), "batch_config.json")
results = render_config(config_path)

print(f"\n{'='*60}")
print(f"Batch rendering complete: {len(results)} jobs")
print(f"{'='*60}")
for r in results:
    d = r["diagnostics"]
    print(f"\n  {r['name']}:")
    print(f"    V={d.num_vertices:6d}  F={d.num_faces:6d}  "
          f"chi={d.euler_characteristic:4d}  watertight={d.is_watertight}  "
          f"area={d.surface_area:.3f}  ({r['elapsed']:.2f}s)")
    if r.get("output"):
        print(f"    -> {r['output']}")
    if r.get("preview"):
        print(f"    Preview:")
        print(r["preview"])