"""Serialization: save/load world state as JSON.

Bodies, joints, and world parameters can be serialized to a plain dict and
written to JSON.  This enables scene files, checkpoints, and networked state
sync.  Shapes are serialized by type + parameters; joints by type + anchors.
"""

from __future__ import annotations

import json
import math
from typing import Any, Dict, List

from .core.body import RigidBody
from .core.shapes import Circle, Polygon
from .core.vec2 import Vec2
from .joints.joints import DistanceJoint, Joint, MouseJoint, RevoluteJoint, WeldJoint
from .world import World

__all__ = ["world_to_dict", "world_to_json", "world_from_dict", "world_from_json",
           "body_to_dict", "body_from_dict",
           "world_to_yaml", "world_from_yaml", "world_to_file", "world_from_file"]


def _vec_to_dict(v: Vec2) -> Dict[str, float]:
    return {"x": v.x, "y": v.y}


def _vec_from_dict(d: Dict[str, float]) -> Vec2:
    return Vec2(d["x"], d["y"])


def _shape_to_dict(shape) -> Dict[str, Any]:
    if isinstance(shape, Circle):
        return {"type": "circle", "radius": shape.radius, "offset": _vec_to_dict(shape.offset)}
    if isinstance(shape, Polygon):
        return {"type": "polygon", "vertices": [_vec_to_dict(v) for v in shape.vertices]}
    raise TypeError(f"cannot serialize shape of type {type(shape)}")


def _shape_from_dict(d: Dict[str, Any]):
    t = d["type"]
    if t == "circle":
        offset = d.get("offset")
        return Circle(d["radius"], _vec_from_dict(offset) if offset else None)
    if t == "polygon":
        verts = [_vec_from_dict(v) for v in d["vertices"]]
        return Polygon(verts)
    raise ValueError(f"unknown shape type: {t}")


def body_to_dict(body: RigidBody) -> Dict[str, Any]:
    """Serialize a single body to a JSON-serializable dict."""
    return {
        "shape": _shape_to_dict(body.shape),
        "position": _vec_to_dict(body.position),
        "angle": body.angle,
        "body_type": body.body_type,
        "density": 1.0 if body.is_dynamic and body.mass > 0 else 1.0,
        "restitution": body.restitution,
        "friction": body.friction,
        "linear_damping": body.linear_damping,
        "angular_damping": body.angular_damping,
        "gravity_scale": body.gravity_scale,
        "linear_velocity": _vec_to_dict(body.linear_velocity),
        "angular_velocity": body.angular_velocity,
        "collision_layer": body.collision_layer,
        "collision_mask": body.collision_mask,
        "is_sensor": body.is_sensor,
        "sleeping": body.sleeping,
        "user_data": body.user_data if isinstance(body.user_data, (str, int, float, bool, type(None))) else None,
    }


def body_from_dict(d: Dict[str, Any]) -> RigidBody:
    """Deserialize a body from a dict produced by :func:`body_to_dict`."""
    shape = _shape_from_dict(d["shape"])
    body = RigidBody(
        shape=shape,
        position=_vec_from_dict(d["position"]),
        angle=d.get("angle", 0.0),
        body_type=d.get("body_type", RigidBody.DYNAMIC),
        density=d.get("density", 1.0),
        restitution=d.get("restitution", 0.2),
        friction=d.get("friction", 0.3),
        linear_damping=d.get("linear_damping", 0.01),
        angular_damping=d.get("angular_damping", 0.01),
        gravity_scale=d.get("gravity_scale", 1.0),
    )
    body.linear_velocity = _vec_from_dict(d.get("linear_velocity", {"x": 0, "y": 0}))
    body.angular_velocity = d.get("angular_velocity", 0.0)
    body.collision_layer = d.get("collision_layer", 0x0001)
    body.collision_mask = d.get("collision_mask", 0xFFFF)
    body.is_sensor = d.get("is_sensor", False)
    body.user_data = d.get("user_data")
    if d.get("sleeping"):
        body.set_sleeping()
    return body


def _joint_to_dict(joint: Joint) -> Dict[str, Any]:
    if isinstance(joint, DistanceJoint):
        return {"type": "distance", "body_a": id(joint.body_a), "body_b": id(joint.body_b),
                "local_a": _vec_to_dict(joint.local_a), "local_b": _vec_to_dict(joint.local_b),
                "length": joint.length, "stiffness": joint.stiffness}
    if isinstance(joint, RevoluteJoint):
        return {"type": "revolute", "body_a": id(joint.body_a), "body_b": id(joint.body_b),
                "local_a": _vec_to_dict(joint.local_a), "local_b": _vec_to_dict(joint.local_b),
                "motor_enabled": joint.motor_enabled, "motor_speed": joint.motor_speed,
                "max_motor_force": joint.max_motor_force}
    if isinstance(joint, WeldJoint):
        return {"type": "weld", "body_a": id(joint.body_a), "body_b": id(joint.body_b),
                "local_a": _vec_to_dict(joint.local_a), "local_b": _vec_to_dict(joint.local_b),
                "frequency": joint.frequency, "damping": joint.damping}
    if isinstance(joint, MouseJoint):
        return {"type": "mouse", "body": id(joint.body), "target": _vec_to_dict(joint.target),
                "local_anchor": _vec_to_dict(joint.local_anchor), "frequency": joint.frequency,
                "damping": joint.damping, "max_force": joint.max_force}
    raise TypeError(f"cannot serialize joint of type {type(joint)}")


def _joint_from_dict(d: Dict[str, Any], body_map: Dict[int, RigidBody]) -> Joint:
    """Reconstruct a joint from a dict.

    The dict uses ``body_a_idx`` / ``body_b_idx`` / ``body_idx`` (body indices
    in the world's body list) for the serialized form.
    """
    t = d["type"]
    if t == "distance":
        return DistanceJoint(
            body_map[d["body_a_idx"]], _vec_from_dict(d["local_a"]),
            body_map[d["body_b_idx"]], _vec_from_dict(d["local_b"]),
            length=d.get("length"), stiffness=d.get("stiffness", 1.0))
    if t == "revolute":
        return RevoluteJoint(
            body_map[d["body_a_idx"]], _vec_from_dict(d["local_a"]),
            body_map[d["body_b_idx"]], _vec_from_dict(d["local_b"]),
            motor_enabled=d.get("motor_enabled", False),
            motor_speed=d.get("motor_speed", 0.0),
            max_motor_force=d.get("max_motor_force", 0.0))
    if t == "weld":
        return WeldJoint(
            body_map[d["body_a_idx"]], _vec_from_dict(d["local_a"]),
            body_map[d["body_b_idx"]], _vec_from_dict(d["local_b"]),
            frequency=d.get("frequency", 8.0), damping=d.get("damping", 0.5))
    if t == "mouse":
        return MouseJoint(
            body_map[d["body_idx"]], _vec_from_dict(d["target"]),
            local_anchor=_vec_from_dict(d.get("local_anchor", {"x": 0, "y": 0})),
            frequency=d.get("frequency", 8.0), damping=d.get("damping", 0.5),
            max_force=d.get("max_force", 1000.0))
    raise ValueError(f"unknown joint type: {t}")


def world_to_dict(world: World) -> Dict[str, Any]:
    """Serialize a world (bodies + joints + parameters) to a dict."""
    bodies = [body_to_dict(b) for b in world.bodies]
    # Build id→index map for joints.
    id_map = {id(b): i for i, b in enumerate(world.bodies)}
    joints = []
    for j in world.joints:
        jd = _joint_to_dict(j)
        # Replace id() with body index.
        if "body_a" in jd and "body_b" in jd:
            jd["body_a_idx"] = id_map.get(jd["body_a"], -1)
            jd["body_b_idx"] = id_map.get(jd["body_b"], -1)
        elif "body" in jd:
            jd["body_idx"] = id_map.get(jd["body"], -1)
        joints.append(jd)
    return {
        "gravity": _vec_to_dict(world.gravity),
        "velocity_iterations": world.velocity_iterations,
        "position_iterations": world.position_iterations,
        "joint_iterations": world.joint_iterations,
        "allow_sleeping": world.allow_sleeping,
        "bodies": bodies,
        "joints": joints,
        "step_count": world.step_count,
    }


def world_from_dict(d: Dict[str, Any]) -> World:
    """Deserialize a world from a dict produced by :func:`world_to_dict`."""
    world = World(
        gravity=_vec_from_dict(d.get("gravity", {"x": 0, "y": -9.81})),
        velocity_iterations=d.get("velocity_iterations", 10),
        position_iterations=d.get("position_iterations", 5),
        joint_iterations=d.get("joint_iterations", 5),
        allow_sleeping=d.get("allow_sleeping", True),
    )
    for bd in d.get("bodies", []):
        world.add_body(body_from_dict(bd))
    # Rebuild joints using body indices.
    body_map = {i: b for i, b in enumerate(world.bodies)}
    for jd in d.get("joints", []):
        world.add_joint(_joint_from_dict(jd, body_map))
    world.step_count = d.get("step_count", 0)
    return world


def world_to_json(world: World, path: str, indent: int = 2) -> None:
    """Serialize *world* to a JSON file at *path*."""
    with open(path, "w") as f:
        json.dump(world_to_dict(world), f, indent=indent)


def world_from_json(path: str) -> World:
    """Load a world from a JSON file at *path*."""
    with open(path, "r") as f:
        return world_from_dict(json.load(f))


def world_to_yaml(world: World, path: str) -> None:
    """Serialize *world* to a YAML file at *path*.

    Requires the optional ``pyyaml`` dependency.  Falls back to JSON
    written with a ``.yaml`` extension if PyYAML is not installed.
    """
    try:
        import yaml  # type: ignore
    except ImportError:
        # Fallback: write JSON with a note.
        with open(path, "w") as f:
            f.write("# PyYAML not installed; JSON follows\n")
            json.dump(world_to_dict(world), f, indent=2)
        return
    with open(path, "w") as f:
        yaml.dump(world_to_dict(world), f, default_flow_style=False, sort_keys=False)


def world_from_yaml(path: str) -> World:
    """Load a world from a YAML file at *path*.

    Falls back to JSON parsing if the file is actually JSON (detected by
    the first non-whitespace character being ``{`` or ``[``).
    """
    try:
        import yaml  # type: ignore
    except ImportError:
        # Fallback: treat as JSON.
        with open(path, "r") as f:
            return world_from_dict(json.load(f))
    with open(path, "r") as f:
        content = f.read()
    # Auto-detect JSON files.
    stripped = content.lstrip()
    if stripped.startswith("{") or stripped.startswith("["):
        return world_from_dict(json.loads(content))
    return world_from_dict(yaml.safe_load(content))


def world_to_file(world: World, path: str) -> None:
    """Save a world to JSON or YAML based on file extension."""
    if path.endswith((".yaml", ".yml")):
        world_to_yaml(world, path)
    else:
        world_to_json(world, path)


def world_from_file(path: str) -> World:
    """Load a world from JSON or YAML based on file extension."""
    if path.endswith((".yaml", ".yml")):
        return world_from_yaml(path)
    return world_from_json(path)