#!/usr/bin/env python3
"""Example: Render a textured Phong-shaded cube using the Python API.

This is the simplest way to get started — render a single cube with
checkerboard texture and Phong shading to a PPM file.
"""

from soft_rasterizer import (
    Renderer, Scene, Camera, Light, Object3D,
    Vec3, PhongShader, PhongMaterial, CheckerTexture,
)
from soft_rasterizer.primitives import make_cube


def main():
    # Create a scene with lights
    scene = Scene()
    scene.lights.append(
        Light.directional(Vec3(-0.5, -1, -0.3), Vec3(1, 1, 0.9), 0.8))
    scene.lights.append(
        Light.point(Vec3(5, 5, 5), Vec3(0.4, 0.4, 0.6), 0.5))

    # Set a dark blue gradient background
    scene.background = Vec3(0.02, 0.02, 0.05)
    scene.background_top = Vec3(0.08, 0.08, 0.15)

    # Camera
    camera = Camera(position=Vec3(3, 2, 4), target=Vec3(0, 0, 0), fov=60)

    # Create a textured cube
    cube = make_cube(size=2.0)
    cube.texture = CheckerTexture(squares=4)
    material = PhongMaterial(
        diffuse=Vec3(0.9, 0.7, 0.5),
        specular=Vec3(0.9, 0.9, 0.9),
        shininess=64,
        ambient=Vec3(0.2, 0.2, 0.2),
    )
    obj = Object3D(cube, shader=PhongShader(material=material),
                   rotation=Vec3(0.3, 0.8, 0))
    scene.add(obj)

    # Render and save
    renderer = Renderer(320, 240)
    renderer.render(scene, camera)
    renderer.save_ppm("example_cube.ppm")
    print(f"Rendered {renderer.width}x{renderer.height} → example_cube.ppm")
    print(f"Stats: {renderer.stats}")


if __name__ == "__main__":
    main()