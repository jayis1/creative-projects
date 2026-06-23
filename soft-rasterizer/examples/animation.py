#!/usr/bin/env python3
"""Example: Render a turntable animation of a torus.

Produces 36 frames (10° each) of a rotating torus, saved as BMP files
in the `animation_frames/` directory. These can be assembled into a GIF
or video using external tools (e.g., ffmpeg or ImageMagick).
"""

import os
import shutil

from soft_rasterizer import (
    Renderer, Scene, Camera, Light, Object3D,
    Vec3, PhongShader, PhongMaterial, AnimationBuilder, FogShader,
)
from soft_rasterizer.primitives import make_torus


def main():
    scene = Scene()
    scene.background = Vec3(0.05, 0.05, 0.1)
    scene.background_top = Vec3(0.15, 0.1, 0.2)

    scene.lights.append(
        Light.directional(Vec3(-0.5, -1, -0.3), Vec3(1, 1, 0.9), 0.8))
    scene.lights.append(
        Light.point(Vec3(5, 5, 5), Vec3(0.4, 0.4, 0.6), 0.5))

    camera = Camera(position=Vec3(4, 2, 0), target=Vec3(0, 0, 0), fov=50)

    torus = make_torus(major_radius=1.0, minor_radius=0.35,
                       major_segments=24, minor_segments=12)
    shader = PhongShader(material=PhongMaterial(
        diffuse=Vec3(0.7, 0.3, 0.8),
        specular=Vec3(1.0, 1.0, 1.0),
        shininess=96,
        ambient=Vec3(0.15, 0.1, 0.2),
    ))
    # Wrap in fog for atmospheric depth
    fog_shader = FogShader(shader, density=0.04, fog_near=3.0)

    scene.add(Object3D(torus, shader=fog_shader, rotation=Vec3(0.5, 0, 0)))

    renderer = Renderer(240, 180)
    builder = AnimationBuilder(renderer, scene, camera)

    output_dir = "animation_frames"
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)

    files = builder.render_turntable(
        output_dir=output_dir,
        frames=36,
        fmt="bmp",
        prefix="torus",
    )

    print(f"Rendered {len(files)} frames to {output_dir}/")
    print(f"To create a GIF: convert -delay 10 -loop 0 {output_dir}/torus_*.bmp torus.gif")


if __name__ == "__main__":
    main()