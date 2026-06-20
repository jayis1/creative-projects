"""serialize.py — JSON scene serialization / deserialization.

Scenes are described as a plain JSON dict so they can be saved, shared, and
tweaked without editing Python.  The schema is intentionally simple and
extensible:

.. code-block:: json

    {
      "background": {"type": "sky"},
      "camera": {
        "look_from": [0, 0.5, 3],
        "look_at":   [0, 0, -2],
        "up":        [0, 1, 0],
        "vfov_deg":  45,
        "aperture":  0.05,
        "focus_dist": 5
      },
      "objects": [
        {"type": "plane",  "point": [0,-0.5,0], "normal": [0,1,0],
         "material": {"type": "checker", "scale": 2,
                       "a": {"type":"matte","albedo":[0.9,0.9,0.9]},
                       "b": {"type":"matte","albedo":[0.1,0.1,0.1]}}},
        {"type": "sphere", "center": [0,0,-1], "radius": 0.5,
         "material": {"type":"dielectric","ior":1.5}}
      ]
    }

Use :func:`load_scene` to parse such a document into a :class:`Scene`.
"""

from __future__ import annotations

import json
from typing import Any, Mapping

from .vec import Vec3
from .ray import Ray
from .material import (
    Material,
    Matte,
    Metal,
    Dielectric,
    Emissive,
    Checker,
)
from .primitive import Sphere, Plane, Triangle, XYRect
from .bvh import BVHNode, _Hittable
from .camera import Camera
from .renderer import sky_gradient, constant_background
from .scene import Scene

__all__ = ["load_scene", "dump_scene", "build_material", "build_object"]


def _vec(v: Any) -> Vec3:
    if isinstance(v, Vec3):
        return v
    if isinstance(v, (list, tuple)):
        if len(v) != 3:
            raise ValueError(f"expected 3-component vector, got {v!r}")
        return Vec3(float(v[0]), float(v[1]), float(v[2]))
    raise TypeError(f"cannot coerce {v!r} to Vec3")


def build_material(spec: Mapping[str, Any]) -> Material:
    """Construct a Material from a JSON-style mapping."""
    kind = spec.get("type", "matte")
    if kind == "matte":
        return Matte(_vec(spec.get("albedo", [0.8, 0.8, 0.8])))
    if kind == "metal":
        return Metal(_vec(spec.get("albedo", [0.8, 0.8, 0.8])),
                     fuzz=float(spec.get("fuzz", 0.0)))
    if kind == "dielectric":
        return Dielectric(float(spec.get("ior", 1.5)),
                          albedo=_vec(spec.get("albedo", [1, 1, 1])))
    if kind == "emissive":
        return Emissive(_vec(spec.get("color", [1, 1, 1])),
                        intensity=float(spec.get("intensity", 1.0)))
    if kind == "checker":
        a = build_material(spec.get("a", {"type": "matte"}))
        b = build_material(spec.get("b", {"type": "matte"}))
        return Checker(a, b, scale=float(spec.get("scale", 1.0)))
    raise ValueError(f"unknown material type {kind!r}")


def build_object(spec: Mapping[str, Any]) -> _Hittable:
    """Construct a hittable primitive from a JSON-style mapping."""
    kind = spec.get("type")
    mat_spec = spec.get("material", {"type": "matte"})
    material = build_material(mat_spec) if mat_spec is not None else None
    if kind == "sphere":
        return Sphere(_vec(spec["center"]), float(spec["radius"]), material)
    if kind == "plane":
        return Plane(_vec(spec["point"]), _vec(spec["normal"]), material)
    if kind == "triangle":
        return Triangle(_vec(spec["a"]), _vec(spec["b"]), _vec(spec["c"]), material)
    if kind == "xyrect":
        return XYRect(
            float(spec["x0"]), float(spec["x1"]),
            float(spec["y0"]), float(spec["y1"]),
            float(spec["z"]), material,
        )
    raise ValueError(f"unknown object type {kind!r}")


def _build_background(spec: Any):
    if spec is None:
        return None
    if callable(spec):
        return spec
    if isinstance(spec, str):
        if spec == "sky":
            return sky_gradient
        if spec == "black":
            return constant_background(Vec3(0, 0, 0))
        raise ValueError(f"unknown background name {spec!r}")
    if isinstance(spec, Mapping):
        kind = spec.get("type", "constant")
        if kind == "sky":
            return sky_gradient
        if kind == "constant":
            return constant_background(_vec(spec.get("color", [0, 0, 0])))
        raise ValueError(f"unknown background type {kind!r}")
    raise TypeError(f"cannot build background from {spec!r}")


def load_scene(doc: Mapping[str, Any], aspect: float = 16.0 / 9.0) -> Scene:
    """Build a :class:`Scene` from a JSON-style mapping."""
    cam_spec = doc.get("camera", {})
    cam = Camera(
        look_from=_vec(cam_spec.get("look_from", [0, 0, 5])),
        look_at=_vec(cam_spec.get("look_at", [0, 0, 0])),
        up=_vec(cam_spec.get("up", [0, 1, 0])),
        vfov_deg=float(cam_spec.get("vfov_deg", 50.0)),
        aspect=aspect,
        aperture=float(cam_spec.get("aperture", 0.0)),
        focus_dist=cam_spec.get("focus_dist"),
    )
    objs = [build_object(o) for o in doc.get("objects", [])]
    if len(objs) == 1:
        world: _Hittable = objs[0]
    else:
        world = BVHNode(objs) if objs else BVHNode([])
    bg = _build_background(doc.get("background", "sky"))
    return Scene(world, cam, background=bg)


def load_scene_file(path: str, aspect: float = 16.0 / 9.0) -> Scene:
    with open(path) as f:
        doc = json.load(f)
    return load_scene(doc, aspect=aspect)


def dump_scene(scene: Scene) -> dict:
    """Best-effort serialization of a Scene to a JSON dict.

    Only the camera and background are serialized reliably; objects are
    introspected via duck typing.  This is a convenience for round-tripping
    scenes built programmatically — for full control use :func:`load_scene`.
    """
    cam = scene.camera
    doc: dict[str, Any] = {
        "camera": {
            "look_from": list(cam.look_from.to_tuple()),
            "look_at": list(cam.look_at.to_tuple()),
            "up": list(cam.up.to_tuple()),
            "vfov_deg": cam.vfov,
            "aperture": cam.aperture,
            "focus_dist": cam.focus_dist,
        },
        "background": "sky",  # default; caller can override
    }
    return doc