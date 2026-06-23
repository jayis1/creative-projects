#!/usr/bin/env python3
"""Example: Apply post-processing effects to a rendered scene.

Renders a Phong-shaded sphere, then applies edge detection and vignette
post-processing for a stylised look.
"""

from soft_rasterizer import (
    Renderer, Scene, Camera, Light, Object3D,
    Vec3, PhongShader, PhongMaterial,
    post_edge_detect, post_vignette,
)
from soft_rasterizer.primitives import make_sphere


def main():
    scene = Scene()
    scene.background = Vec3(0.08, 0.08, 0.1)
    scene.background_top = Vec3(0.15, 0.12, 0.2)

    scene.lights.append(
        Light.directional(Vec3(-0.5, -1, -0.3), Vec3(1, 1, 0.9), 0.9))
    scene.lights.append(
        Light.point(Vec3(3, 3, 3), Vec3(0.5, 0.7, 1.0), 0.6))

    camera = Camera(position=Vec3(0, 1, 4), target=Vec3(0, 0, 0), fov=50)

    sphere = make_sphere(radius=1.2, segments=24, rings=16)
    scene.add(Object3D(sphere, shader=PhongShader(material=PhongMaterial(
        diffuse=Vec3(0.6, 0.8, 0.9),
        specular=Vec3(1.0, 1.0, 1.0),
        shininess=128,
    ))))

    renderer = Renderer(300, 240)
    renderer.render(scene, camera)

    # Apply post-processing
    post_edge_detect(renderer.framebuffer, threshold=0.15)
    post_vignette(renderer.framebuffer, strength=0.6, falloff=0.9)

    renderer.save_bmp("example_postprocess.bmp")
    print(f"Rendered with post-processing → example_postprocess.bmp")


if __name__ == "__main__":
    main()