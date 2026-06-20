"""examples/render_all.py — Render every preset scene + a JSON scene to /tmp.

Run with the project venv active::

    python examples/render_all.py
"""

from __future__ import annotations

import os
import sys
import time

# Make the package importable when run as a script.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from raytracer import (
    build_three_balls,
    build_cornell_box,
    build_random_spheres,
    imageio,
    load_scene_file,
)

OUT = "/tmp/raytracer_examples"
os.makedirs(OUT, exist_ok=True)


def render_preset(name, builder, w, h, samples, depth):
    print(f"[{name}] {w}x{h} s={samples} d={depth} ...", end=" ", flush=True)
    t0 = time.time()
    scene = builder(aspect=w / h)
    r = scene.make_renderer(samples=samples, max_depth=depth, seed=7)
    pixels = r.render(scene.camera, w, h)
    imageio.write_png(os.path.join(OUT, f"{name}.png"), pixels)
    print(f"{time.time()-t0:.2f}s -> {name}.png")


def main():
    render_preset("three_balls", build_three_balls, 160, 90, 4, 6)
    render_preset("cornell", build_cornell_box, 120, 120, 4, 6)
    render_preset("random", build_random_spheres, 160, 90, 2, 4)

    # JSON scene
    scene_path = os.path.join(os.path.dirname(__file__), "sample_scene.json")
    scene = load_scene_file(scene_path, aspect=160 / 90)
    r = scene.make_renderer(samples=4, max_depth=6, seed=7)
    pixels = r.render(scene.camera, 160, 90)
    imageio.write_png(os.path.join(OUT, "json_scene.png"), pixels)
    print("json_scene -> json_scene.png")

    # Normal-shading debug pass
    scene = build_three_balls(aspect=160 / 90)
    r = scene.make_renderer(samples=1, mode="normal", seed=7)
    pixels = r.render(scene.camera, 160, 90)
    imageio.write_png(os.path.join(OUT, "normals.png"), pixels)
    print("normals -> normals.png")

    # AO pass
    scene = build_three_balls(aspect=160 / 90)
    r = scene.make_renderer(samples=16, mode="ao", ao_distance=2.0, seed=7)
    pixels = r.render(scene.camera, 160, 90)
    imageio.write_png(os.path.join(OUT, "ao.png"), pixels)
    print("ao -> ao.png")

    print(f"\nAll outputs in {OUT}/")


if __name__ == "__main__":
    main()