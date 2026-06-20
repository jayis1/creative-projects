"""examples/render_all.py — Render every preset scene + JSON/YAML/TOML scenes.

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
    build_solar_system,
    build_marble_hall,
    build_nebula,
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
    print(f"{time.time()-t0:.2f}s -> {name}.png ({r.stats.rays} rays)")


def main():
    # Preset scenes (small for quick demonstration)
    render_preset("three_balls", build_three_balls, 80, 45, 2, 4)
    render_preset("cornell", build_cornell_box, 60, 60, 2, 4)
    render_preset("random", build_random_spheres, 80, 45, 1, 3)
    render_preset("solar_system", build_solar_system, 80, 45, 2, 4)
    render_preset("marble_hall", build_marble_hall, 80, 45, 2, 4)
    render_preset("nebula", build_nebula, 80, 45, 2, 3)

    # JSON scene
    scene_path = os.path.join(os.path.dirname(__file__), "sample_scene.json")
    scene = load_scene_file(scene_path, aspect=160 / 90)
    r = scene.make_renderer(samples=4, max_depth=6, seed=7)
    pixels = r.render(scene.camera, 160, 90)
    imageio.write_png(os.path.join(OUT, "json_scene.png"), pixels)
    print("json_scene -> json_scene.png")

    # YAML scene
    yaml_path = os.path.join(os.path.dirname(__file__), "cornell_textured.yaml")
    try:
        scene = load_scene_file(yaml_path, aspect=120 / 120)
        r = scene.make_renderer(samples=4, max_depth=6, seed=7)
        pixels = r.render(scene.camera, 120, 120)
        imageio.write_png(os.path.join(OUT, "yaml_scene.png"), pixels)
        print("yaml_scene -> yaml_scene.png")
    except ImportError:
        print("YAML scene skipped (PyYAML not installed)")

    # TOML scene
    toml_path = os.path.join(os.path.dirname(__file__), "marble_hall.toml")
    try:
        scene = load_scene_file(toml_path, aspect=160 / 90)
        r = scene.make_renderer(samples=4, max_depth=6, seed=7)
        pixels = r.render(scene.camera, 160, 90)
        imageio.write_png(os.path.join(OUT, "toml_scene.png"), pixels)
        print("toml_scene -> toml_scene.png")
    except ImportError:
        print("TOML scene skipped (tomli not installed)")

    # Normal-shading debug pass
    scene = build_three_balls(aspect=160 / 90)
    r = scene.make_renderer(samples=1, mode="normal", seed=7)
    pixels = r.render(scene.camera, 160, 90)
    imageio.write_png(os.path.join(OUT, "normals.png"), pixels)
    print("normals -> normals.png")

    # Depth debug pass
    scene = build_three_balls(aspect=160 / 90)
    r = scene.make_renderer(samples=1, mode="depth", ao_distance=10, seed=7)
    pixels = r.render(scene.camera, 160, 90)
    imageio.write_png(os.path.join(OUT, "depth.png"), pixels)
    print("depth -> depth.png")

    # AO pass
    scene = build_three_balls(aspect=160 / 90)
    r = scene.make_renderer(samples=16, mode="ao", ao_distance=2.0, seed=7)
    pixels = r.render(scene.camera, 160, 90)
    imageio.write_png(os.path.join(OUT, "ao.png"), pixels)
    print("ao -> ao.png")

    # Animation: 3-frame orbit of three-balls
    from raytracer.animation import orbit_path, render_animation
    scene = build_three_balls(aspect=160 / 90)
    positions = orbit_path(Vec3(0, 0, -1), 3.0, 1.0, 3)
    paths = render_animation(
        scene=scene, eye_positions=positions,
        out_dir=os.path.join(OUT, "orbit"),
        width=80, height=45, samples=2, max_depth=3,
        fmt="png", progress=False,
    )
    print(f"orbit -> {len(paths)} frames in orbit/")

    print(f"\nAll outputs in {OUT}/")


if __name__ == "__main__":
    from raytracer import Vec3
    main()