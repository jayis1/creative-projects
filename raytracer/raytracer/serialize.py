"""serialize.py — JSON / YAML / TOML scene serialization & deserialization.

Scenes are described as a plain dict so they can be saved, shared, and
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
JSON, YAML, and TOML are all accepted by :func:`load_scene_file` (the format
is auto-detected from the file extension or the ``--format`` CLI flag).
"""

from __future__ import annotations

import json
import os
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
    Isotropic,
)
from .texture import (
    Texture,
    SolidColor,
    CheckerTexture,
    NoiseTexture,
    Turbulence,
    Marble,
)
from .primitive import (
    Sphere, Plane, Triangle, XYRect, XZRect, YZRect, Box, Disk, Cylinder,
)
from .bvh import BVHNode, _Hittable
from .camera import Camera
from .renderer import sky_gradient, constant_background
from .scene import Scene

__all__ = [
    "load_scene",
    "load_scene_file",
    "dump_scene",
    "build_material",
    "build_object",
    "build_texture",
    "SUPPORTED_FORMATS",
]

SUPPORTED_FORMATS = ("json", "yaml", "toml")


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _vec(v: Any) -> Vec3:
    if isinstance(v, Vec3):
        return v
    if isinstance(v, (list, tuple)):
        if len(v) != 3:
            raise ValueError(f"expected 3-component vector, got {v!r}")
        return Vec3(float(v[0]), float(v[1]), float(v[2]))
    raise TypeError(f"cannot coerce {v!r} to Vec3")


def _detect_format(path: str, fmt: str = "auto") -> str:
    """Return one of ``json`` / ``yaml`` / ``toml``."""
    if fmt != "auto":
        return fmt.lower()
    ext = os.path.splitext(path)[1].lower().lstrip(".")
    if ext in ("yaml", "yml"):
        return "yaml"
    if ext == "toml":
        return "toml"
    return "json"


def _parse_text(text: str, fmt: str) -> dict:
    if fmt == "json":
        return json.loads(text)
    if fmt == "yaml":
        try:
            import yaml
        except ImportError as e:
            raise ImportError("PyYAML is required to read YAML scene files") from e
        return yaml.safe_load(text)
    if fmt == "toml":
        try:
            import tomllib  # Python 3.11+
        except ImportError:
            import tomli as tomllib  # backport for older Pythons
        return tomllib.loads(text)
    raise ValueError(f"unsupported format {fmt!r}")


# --------------------------------------------------------------------------- #
# Textures
# --------------------------------------------------------------------------- #
def build_texture(spec: Mapping[str, Any]) -> Texture:
    """Construct a :class:`Texture` from a JSON-style mapping."""
    # Allow a bare Vec3 / list as shorthand for SolidColor.
    if isinstance(spec, (list, tuple)):
        return SolidColor(_vec(spec))
    if isinstance(spec, Vec3):
        return SolidColor(spec)
    kind = spec.get("type", "solid")
    if kind == "solid":
        return SolidColor(_vec(spec.get("color", [0.8, 0.8, 0.8])))
    if kind == "checker":
        even = build_texture(spec.get("even", {"type": "solid", "color": [1, 1, 1]}))
        odd = build_texture(spec.get("odd", {"type": "solid", "color": [0, 0, 0]}))
        return CheckerTexture(even, odd, scale=float(spec.get("scale", 1.0)))
    if kind == "noise":
        c1 = _vec(spec.get("color1", [0.2, 0.2, 0.2]))
        c2 = _vec(spec.get("color2", [0.8, 0.8, 0.8]))
        return NoiseTexture(c1, c2, scale=float(spec.get("scale", 4.0)),
                            seed=int(spec.get("seed", 0)))
    if kind == "turbulence":
        color = _vec(spec.get("color", [0.5, 0.5, 0.5]))
        return Turbulence(color, scale=float(spec.get("scale", 4.0)),
                          depth=int(spec.get("depth", 7)),
                          seed=int(spec.get("seed", 0)))
    if kind == "marble":
        c1 = _vec(spec.get("color1", [0.9, 0.9, 0.95]))
        c2 = _vec(spec.get("color2", [0.1, 0.1, 0.15]))
        return Marble(c1, c2, scale=float(spec.get("scale", 4.0)),
                      depth=int(spec.get("depth", 7)),
                      seed=int(spec.get("seed", 0)))
    raise ValueError(f"unknown texture type {kind!r}")


# --------------------------------------------------------------------------- #
# Materials
# --------------------------------------------------------------------------- #
def build_material(spec: Mapping[str, Any]) -> Material:
    """Construct a Material from a JSON-style mapping.

    The ``albedo``/``color`` field accepts either a Vec3 (list of 3 floats) or a
    full texture mapping (e.g. ``{"type": "noise", ...}``) so textured
    materials can be expressed in scene files.
    """
    kind = spec.get("type", "matte")
    if kind == "matte":
        albedo = spec.get("albedo", [0.8, 0.8, 0.8])
        if isinstance(albedo, Mapping):
            return Matte(build_texture(albedo))
        return Matte(_vec(albedo))
    if kind == "metal":
        albedo = spec.get("albedo", [0.8, 0.8, 0.8])
        tex = build_texture(albedo) if isinstance(albedo, Mapping) else _vec(albedo)
        return Metal(tex, fuzz=float(spec.get("fuzz", 0.0)))
    if kind == "dielectric":
        return Dielectric(float(spec.get("ior", 1.5)),
                          albedo=_vec(spec.get("albedo", [1, 1, 1])))
    if kind == "emissive":
        color = spec.get("color", [1, 1, 1])
        tex = build_texture(color) if isinstance(color, Mapping) else _vec(color)
        return Emissive(tex, intensity=float(spec.get("intensity", 1.0)))
    if kind == "checker":
        a = build_material(spec.get("a", {"type": "matte"}))
        b = build_material(spec.get("b", {"type": "matte"}))
        return Checker(a, b, scale=float(spec.get("scale", 1.0)))
    if kind == "isotropic":
        albedo = spec.get("albedo", [0.5, 0.5, 0.5])
        tex = build_texture(albedo) if isinstance(albedo, Mapping) else _vec(albedo)
        return Isotropic(tex)
    raise ValueError(f"unknown material type {kind!r}")


# --------------------------------------------------------------------------- #
# Primitives
# --------------------------------------------------------------------------- #
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
    if kind == "xzrect":
        return XZRect(
            float(spec["x0"]), float(spec["x1"]),
            float(spec["z0"]), float(spec["z1"]),
            float(spec["y"]), material,
        )
    if kind == "yzrect":
        return YZRect(
            float(spec["y0"]), float(spec["y1"]),
            float(spec["z0"]), float(spec["z1"]),
            float(spec["x"]), material,
        )
    if kind == "box":
        return Box(_vec(spec["min"]), _vec(spec["max"]), material)
    if kind == "disk":
        return Disk(_vec(spec["center"]), _vec(spec["normal"]),
                    float(spec["radius"]), material)
    if kind == "cylinder":
        return Cylinder(
            _vec(spec["center"]),
            float(spec["radius"]),
            float(spec.get("y0", spec["center"].y if isinstance(spec["center"], Vec3) else spec["center"][1])),
            float(spec.get("y1", (spec["center"].y if isinstance(spec["center"], Vec3) else spec["center"][1]) + 1.0)),
            material,
            capped=bool(spec.get("capped", True)),
        )
    raise ValueError(f"unknown object type {kind!r}")


# --------------------------------------------------------------------------- #
# Backgrounds
# --------------------------------------------------------------------------- #
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


# --------------------------------------------------------------------------- #
# Scene loaders
# --------------------------------------------------------------------------- #
def load_scene(doc: Mapping[str, Any], aspect: float = 16.0 / 9.0) -> Scene:
    """Build a :class:`Scene` from a JSON/YAML/TOML-style mapping."""
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
    # Collect emissive lights for NEE.
    lights = [o for o in objs if _is_emissive(o)]
    return Scene(world, cam, background=bg, lights=lights or None)


def _is_emissive(obj: _Hittable) -> bool:
    """Heuristic: an object is a light if its material emits nonzero color."""
    mat = getattr(obj, "material", None)
    if mat is None:
        return False
    try:
        albedo = mat.emitted_albedo()
        return albedo.length_squared() > 0
    except Exception:
        return False


def load_scene_file(path: str, aspect: float = 16.0 / 9.0, fmt: str = "auto") -> Scene:
    """Load a scene from a JSON, YAML, or TOML file.

    The format is auto-detected from the file extension unless ``fmt`` is
    specified.
    """
    actual_fmt = _detect_format(path, fmt)
    with open(path) as f:
        text = f.read()
    doc = _parse_text(text, actual_fmt)
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