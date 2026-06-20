"""raytracer — A from-scratch recursive ray tracer in pure Python.

Public API
----------
* :class:`Vec3`        – 3D vector math
* :class:`Ray`         – parametric ray
* :class:`Camera`      – pinhole camera with depth-of-field
* :class:`Renderer`    – recursive path-tracing integrator
* :class:`Scene`       – preset scenes / camera bundles
* :class:`Material`    – base material class
* :class:`Matte`, :class:`Metal`, :class:`Dielectric`, :class:`Emissive`,
  :class:`Checker`, :class:`Isotropic` – concrete BSDFs
* :class:`Sphere`, :class:`Plane`, :class:`Triangle`, :class:`XYRect`,
  :class:`XZRect`, :class:`YZRect`, :class:`Box`, :class:`Disk`,
  :class:`Cylinder` – geometry
* :class:`BVHNode`, :class:`HittableList`, :class:`AABB` – acceleration
* :class:`Texture`, :class:`SolidColor`, :class:`CheckerTexture`,
  :class:`PerlinNoise`, :class:`NoiseTexture`, :class:`Turbulence`,
  :class:`Marble`, :class:`ImageTexture` – textures
* :mod:`raytracer.animation` – camera animation helpers
* :mod:`raytracer.logging`  – structured logging
"""

from .vec import Vec3
from .ray import Ray
from .camera import Camera
from .renderer import Renderer, sky_gradient, constant_background, ConstantBackground, RenderStats, MODES
from .scene import (
    Scene,
    build_three_balls,
    build_cornell_box,
    build_random_spheres,
    build_solar_system,
    build_marble_hall,
    build_nebula,
    PRESETS,
)
from .material import (
    Material,
    Matte,
    Metal,
    Dielectric,
    Emissive,
    Checker,
    Isotropic,
    HitRecord,
)
from .texture import (
    Texture,
    SolidColor,
    CheckerTexture,
    PerlinNoise,
    NoiseTexture,
    Turbulence,
    Marble,
    ImageTexture,
)
from .primitive import (
    Primitive,
    Sphere,
    Plane,
    Triangle,
    XYRect,
    XZRect,
    YZRect,
    Box,
    Disk,
    Cylinder,
)
from .bvh import BVHNode, HittableList, AABB
from . import imageio
from . import serialize
from . import animation
from . import logging as _logging
from .serialize import (
    load_scene,
    load_scene_file,
    dump_scene,
    build_material,
    build_object,
    build_texture,
)

__all__ = [
    "Vec3",
    "Ray",
    "Camera",
    "Renderer",
    "RenderStats",
    "sky_gradient",
    "constant_background",
    "ConstantBackground",
    "MODES",
    "Scene",
    "build_three_balls",
    "build_cornell_box",
    "build_random_spheres",
    "build_solar_system",
    "build_marble_hall",
    "build_nebula",
    "PRESETS",
    "Material",
    "Matte",
    "Metal",
    "Dielectric",
    "Emissive",
    "Checker",
    "Isotropic",
    "HitRecord",
    "Texture",
    "SolidColor",
    "CheckerTexture",
    "PerlinNoise",
    "NoiseTexture",
    "Turbulence",
    "Marble",
    "ImageTexture",
    "Primitive",
    "Sphere",
    "Plane",
    "Triangle",
    "XYRect",
    "XZRect",
    "YZRect",
    "Box",
    "Disk",
    "Cylinder",
    "BVHNode",
    "HittableList",
    "AABB",
    "imageio",
    "serialize",
    "animation",
    "load_scene",
    "load_scene_file",
    "dump_scene",
    "build_material",
    "build_object",
    "build_texture",
]

__version__ = "2.0.0"