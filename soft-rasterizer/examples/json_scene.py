#!/usr/bin/env python3
"""Example: Load a scene from a JSON config file and render it.

Demonstrates using SceneConfig to define a scene declaratively in JSON,
then render it without writing any scene-building Python code.
"""

from soft_rasterizer import Renderer, SceneConfig


def main():
    # Load the scene from a JSON config file
    scene, camera = SceneConfig.load("examples/multi_object_scene.json")

    # Render
    renderer = Renderer(400, 300)
    renderer.render(scene, camera)
    renderer.save_bmp("example_json_config.bmp")

    print(f"Rendered {renderer.width}x{renderer.height} → example_json_config.bmp")
    print(f"Stats: {renderer.stats}")


if __name__ == "__main__":
    main()