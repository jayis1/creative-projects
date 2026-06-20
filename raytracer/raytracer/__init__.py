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
  :class:`Checker` – concrete BSDFs
* :class:`Sphere`, :class:`Plane`, :class:`Triangle`, :class:`XYRect` – geometry
* :class:`BVHNode`, :class:`HittableList`, :class:`AABB` – acceleration
"""

from .vec import Vec3
from .ray import Ray
from .camera import Camera
from .renderer import Renderer, sky_gradient, constant_background
from .scene import Scene, build_three_balls, build_cornell_box, build_random_spheres
from .material import (
    Material,
    Matte,
    Metal,
    Dielectric,
    Emissive,
    Checker,
    HitRecord,
)
from .primitive import Primitive, Sphere, Plane, Triangle, XYRect
from .bvh import BVHNode, HittableList, AABB
from . import imageio

__all__ = [
    "Vec3",
    "Ray",
    "Camera",
    "Renderer",
    "sky_gradient",
    "constant_background",
    "Scene",
    "build_three_balls",
    "build_cornell_box",
    "build_random_spheres",
    "Material",
    "Matte",
    "Metal",
    "Dielectric",
    "Emissive",
    "Checker",
    "HitRecord",
    "Primitive",
    "Sphere",
    "Plane",
    "Triangle",
    "XYRect",
    "BVHNode",
    "HittableList",
    "AABB",
    "imageio",
]

__version__ = "1.0.0"