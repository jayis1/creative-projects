"""Scene configuration via JSON files.

Allows defining complete scenes (objects, lights, camera, shaders,
materials, textures) in a JSON file for reproducible renders without
writing Python code.

Example JSON structure::

    {
      "camera": {
        "position": [3, 2, 4],
        "target": [0, 0, 0],
        "fov": 60,
        "near": 0.1,
        "far": 100
      },
      "lights": [
        {"type": "directional", "direction": [-0.5, -1, -0.3],
         "color": [1, 1, 0.9], "intensity": 0.8},
        {"type": "point", "position": [5, 5, 5],
         "color": [0.4, 0.4, 0.6], "intensity": 0.5}
      ],
      "background": [0.05, 0.05, 0.08],
      "objects": [
        {
          "primitive": "cube",
          "size": 2.0,
          "shader": "phong",
          "material": {
            "diffuse": [0.9, 0.7, 0.5],
            "specular": [0.9, 0.9, 0.9],
            "shininess": 64,
            "ambient": [0.2, 0.2, 0.2]
          },
          "texture": {"type": "checker", "squares": 4},
          "position": [0, 0, 0],
          "rotation": [0.3, 0.8, 0],
          "scale": 1.0
        }
      ]
    }
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from .math3d import Vec3
from .scene import Scene, Camera, Light, Object3D
from .shaders import (FlatShader, GouraudShader, PhongShader,
                      PhongMaterial, WireframeShader, NormalShader,
                      DepthShader, ToonShader, FogShader,
                      CrosshatchShader, MatcapShader)
from .texture import CheckerTexture, Texture
from .primitives import (make_cube, make_sphere, make_plane, make_cylinder,
                         make_torus, make_tetrahedron, make_octahedron)
from .mesh import OBJLoader

__all__ = ["SceneConfig"]

logger = logging.getLogger(__name__)

_PRIMITIVES = {
    "cube": make_cube,
    "sphere": make_sphere,
    "plane": make_plane,
    "cylinder": make_cylinder,
    "torus": make_torus,
    "tetrahedron": make_tetrahedron,
    "octahedron": make_octahedron,
}

_SHADER_FACTORIES = {
    "flat": lambda mat, **kw: FlatShader(material=mat),
    "gouraud": lambda mat, **kw: GouraudShader(material=mat),
    "phong": lambda mat, **kw: PhongShader(material=mat),
    "normal": lambda mat, **kw: NormalShader(),
    "depth": lambda mat, **kw: DepthShader(**kw),
    "wireframe": lambda mat, **kw: WireframeShader(**kw),
    "toon": lambda mat, **kw: ToonShader(material=mat, **kw),
    "crosshatch": lambda mat, **kw: CrosshatchShader(material=mat, **kw),
    "matcap": lambda mat, **kw: MatcapShader(material=mat, **kw),
}


def _vec3(val) -> Vec3:
    """Convert a list/tuple of 3 numbers to a Vec3."""
    if isinstance(val, Vec3):
        return val
    return Vec3(float(val[0]), float(val[1]), float(val[2]))


def _parse_material(data: dict) -> PhongMaterial:
    """Parse a material dict into a PhongMaterial."""
    return PhongMaterial(
        ambient=_vec3(data["ambient"]) if "ambient" in data else None,
        diffuse=_vec3(data["diffuse"]) if "diffuse" in data else None,
        specular=_vec3(data["specular"]) if "specular" in data else None,
        shininess=float(data.get("shininess", 32.0)),
        emissive=_vec3(data["emissive"]) if "emissive" in data else None,
    )


def _parse_texture(data: dict):
    """Parse a texture config dict."""
    tex_type = data.get("type", "checker")
    if tex_type == "checker":
        return CheckerTexture(
            squares=int(data.get("squares", 8)),
            color_a=_vec3(data["color_a"]) if "color_a" in data else None,
            color_b=_vec3(data["color_b"]) if "color_b" in data else None,
        )
    return None


def _parse_shader(data: dict):
    """Parse a shader config dict into a shader instance."""
    name = data.get("name", "phong")
    if name not in _SHADER_FACTORIES:
        raise ValueError(f"Unknown shader: {name}. Available: {list(_SHADER_FACTORIES)}")

    mat = _parse_material(data.get("material", {})) if "material" in data else PhongMaterial()

    # Extract shader-specific kwargs
    kwargs = {}
    if "bands" in data:
        kwargs["bands"] = int(data["bands"])
    if "outline_threshold" in data:
        kwargs["outline_threshold"] = float(data["outline_threshold"])
    if "line_width" in data:
        kwargs["line_width"] = float(data["line_width"])
    if "line_color" in data:
        kwargs["line_color"] = _vec3(data["line_color"])
    if "near_dist" in data:
        kwargs["near_dist"] = float(data["near_dist"])
    if "far_dist" in data:
        kwargs["far_dist"] = float(data["far_dist"])

    shader = _SHADER_FACTORIES[name](mat, **kwargs)

    # Wrap in fog if requested
    if data.get("fog"):
        fog_data = data["fog"] if isinstance(data["fog"], dict) else {}
        shader = FogShader(
            shader,
            fog_color=_vec3(fog_data["color"]) if "color" in fog_data else None,
            density=float(fog_data.get("density", 0.05)),
            fog_near=float(fog_data.get("near", 5.0)),
        )

    return shader


def _parse_light(data: dict) -> Light:
    """Parse a light config dict into a Light."""
    ltype = data.get("type", "point")
    color = _vec3(data["color"]) if "color" in data else Vec3(1, 1, 1)
    intensity = float(data.get("intensity", 1.0))

    if ltype == "directional":
        return Light.directional(
            _vec3(data["direction"]), color, intensity)
    elif ltype == "point":
        return Light.point(
            _vec3(data["position"]), color, intensity)
    elif ltype == "ambient":
        return Light.ambient(color, intensity)
    else:
        raise ValueError(f"Unknown light type: {ltype}")


def _parse_object(data: dict) -> Object3D:
    """Parse an object config dict into an Object3D."""
    # Build mesh
    if "obj" in data:
        mesh = OBJLoader.load(data["obj"])
        # Center and scale
        c = mesh.center()
        mesh.translate(Vec3(-c.x, -c.y, -c.z))
        minp, maxp = mesh.bounds()
        max_extent = max(maxp.x - minp.x, maxp.y - minp.y, maxp.z - minp.z)
        if max_extent > 0:
            mesh.scale(2.0 / max_extent)
    elif "primitive" in data:
        prim = data["primitive"]
        if prim not in _PRIMITIVES:
            raise ValueError(f"Unknown primitive: {prim}. Available: {list(_PRIMITIVES)}")
        size = float(data.get("size", 1.5))
        # Map "size" to the appropriate keyword for each primitive
        if prim == "cube":
            mesh = make_cube(size=size)
        elif prim == "sphere":
            mesh = make_sphere(radius=size, segments=int(data.get("segments", 16)),
                               rings=int(data.get("rings", 12)))
        elif prim == "plane":
            mesh = make_plane(size=size, divisions=int(data.get("divisions", 1)))
        elif prim == "cylinder":
            mesh = make_cylinder(radius=size, height=float(data.get("height", 2.0)),
                                 segments=int(data.get("segments", 16)))
        elif prim == "torus":
            mesh = make_torus(major_radius=size,
                              minor_radius=float(data.get("minor_radius", 0.3)),
                              major_segments=int(data.get("major_segments", 24)),
                              minor_segments=int(data.get("minor_segments", 12)))
        elif prim == "tetrahedron":
            mesh = make_tetrahedron(size=size)
        elif prim == "octahedron":
            mesh = make_octahedron(size=size)
        else:
            mesh = _PRIMITIVES[prim]()
    else:
        raise ValueError("Object must have 'primitive' or 'obj' key")

    # Texture
    texture = _parse_texture(data["texture"]) if "texture" in data else None

    # Shader
    shader = _parse_shader(data.get("shader", {"name": "phong"}))

    # Transform
    position = _vec3(data["position"]) if "position" in data else Vec3(0, 0, 0)
    rotation = _vec3(data["rotation"]) if "rotation" in data else Vec3(0, 0, 0)
    scale = float(data.get("scale", 1.0))

    return Object3D(mesh, shader=shader, position=position,
                    rotation=rotation, scale=scale, texture=texture)


class SceneConfig:
    """Load and build scenes from JSON configuration files."""

    @staticmethod
    def load(filepath: str) -> tuple[Scene, Camera]:
        """Load a JSON scene config and return (scene, camera).

        Args:
            filepath: Path to the JSON scene file.

        Returns:
            A tuple of (Scene, Camera) ready for rendering.
        """
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Scene config not found: {filepath}")

        with open(path) as f:
            config = json.load(f)

        logger.info("Loading scene config: %s", filepath)

        # Camera
        cam_data = config.get("camera", {})
        camera = Camera(
            position=_vec3(cam_data.get("position", [0, 0, 5])),
            target=_vec3(cam_data.get("target", [0, 0, 0])),
            fov=float(cam_data.get("fov", 60)),
            near=float(cam_data.get("near", 0.1)),
            far=float(cam_data.get("far", 100)),
        )

        # Scene
        scene = Scene()

        # Background
        if "background" in config:
            scene.background = _vec3(config["background"])

        # Lights
        for light_data in config.get("lights", []):
            scene.add(_parse_light(light_data))

        # Objects
        for obj_data in config.get("objects", []):
            scene.add(_parse_object(obj_data))

        logger.info("Scene loaded: %d objects, %d lights",
                     len(scene.objects), len(scene.lights))
        return scene, camera

    @staticmethod
    def save_template(filepath: str) -> None:
        """Write a template JSON scene file for reference."""
        template = {
            "camera": {
                "position": [3, 2, 4],
                "target": [0, 0, 0],
                "fov": 60,
                "near": 0.1,
                "far": 100
            },
            "lights": [
                {"type": "directional",
                 "direction": [-0.5, -1, -0.3],
                 "color": [1, 1, 0.9],
                 "intensity": 0.8},
                {"type": "point",
                 "position": [5, 5, 5],
                 "color": [0.4, 0.4, 0.6],
                 "intensity": 0.5}
            ],
            "background": [0.05, 0.05, 0.08],
            "objects": [
                {
                    "primitive": "cube",
                    "size": 2.0,
                    "shader": {
                        "name": "phong",
                        "material": {
                            "diffuse": [0.9, 0.7, 0.5],
                            "specular": [0.9, 0.9, 0.9],
                            "shininess": 64,
                            "ambient": [0.2, 0.2, 0.2]
                        }
                    },
                    "texture": {"type": "checker", "squares": 4},
                    "position": [0, 0, 0],
                    "rotation": [0.3, 0.8, 0],
                    "scale": 1.0
                }
            ]
        }
        with open(filepath, "w") as f:
            json.dump(template, f, indent=2)
        logger.info("Wrote scene template: %s", filepath)