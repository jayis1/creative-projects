#!/usr/bin/env python3
"""Example: Render a multi-object scene with different shaders.

Demonstrates rendering multiple objects with different shading models:
- A Phong-shaded textured cube
- A toon-shaded sphere
- A normal-visualisation torus
"""

from soft_rasterizer import (
    Renderer, Scene, Camera, Light, Object3D,
    Vec3, PhongShader, PhongMaterial, ToonShader, NormalShader,
    CheckerTexture,
)
from soft_rasterizer.primitives import make_cube, make_sphere, make_torus


def main():
    scene = Scene()
    scene.background = Vec3(0.03, 0.03, 0.05)
    scene.background_top = Vec3(0.1, 0.08, 0.15)

    # Three lights for interesting illumination
    scene.lights.append(
        Light.directional(Vec3(-0.5, -1, -0.3), Vec3(1, 0.95, 0.8), 0.7))
    scene.lights.append(
        Light.point(Vec3(-4, 3, 4), Vec3(0.3, 0.5, 1.0), 0.5))
    scene.lights.append(
        Light.point(Vec3(4, 2, -2), Vec3(1.0, 0.4, 0.3), 0.4))

    camera = Camera(position=Vec3(0, 3, 7), target=Vec3(0, 0, 0), fov=55)

    # Phong-shaded textured cube (left)
    cube = make_cube(size=1.5)
    cube.texture = CheckerTexture(squares=4)
    scene.add(Object3D(
        cube,
        shader=PhongShader(material=PhongMaterial(
            diffuse=Vec3(0.8, 0.7, 0.5),
            specular=Vec3(0.9, 0.9, 0.9),
            shininess=64,
        )),
        position=Vec3(-2, 0, 0),
        rotation=Vec3(0.2, 0.5, 0),
    ))

    # Toon-shaded sphere (center)
    sphere = make_sphere(radius=1.0, segments=20, rings=14)
    scene.add(Object3D(
        sphere,
        shader=ToonShader(
            material=PhongMaterial(
                diffuse=Vec3(0.9, 0.5, 0.3),
                ambient=Vec3(0.3, 0.2, 0.2),
            ),
            bands=4,
        ),
        position=Vec3(0, 0, 0),
    ))

    # Normal-visualisation torus (right)
    torus = make_torus(major_radius=0.7, minor_radius=0.25)
    scene.add(Object3D(
        torus,
        shader=NormalShader(),
        position=Vec3(2, 0, 0),
        rotation=Vec3(0.5, 0, 0),
    ))

    renderer = Renderer(400, 300)
    renderer.render(scene, camera)
    renderer.save_bmp("example_multi.bmp")
    print(f"Rendered {renderer.width}x{renderer.height} → example_multi.bmp")
    print(f"Stats: {renderer.stats}")


if __name__ == "__main__":
    main()