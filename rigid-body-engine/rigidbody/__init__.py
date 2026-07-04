"""rigid-body-engine: a 2D rigid body physics engine in pure Python.

Public API::

    from rigidbody import World, RigidBody, Vec2
    from rigidbody import Circle, Polygon, DistanceJoint, RevoluteJoint
"""

from .core.body import RigidBody
from .core.shapes import AABB, Circle, Polygon, Shape
from .core.vec2 import Vec2
from .core.mat22 import Mat22
from .core.collision import Manifold, collide, point_in_polygon
from .core.broadphase import BroadPhase
from .core.fields import BuoyancyField, DragField, ForceField, RadialField, UniformField
from .solver.contact_solver import ContactSolver
from .joints.joints import DistanceJoint, Joint, MouseJoint, PrismaticJoint, RevoluteJoint, WeldJoint
from .diagnostics import Diagnostics, compute_energy, compute_momentum
from .serialize import (
    body_from_dict, body_to_dict,
    world_from_dict, world_from_json,
    world_to_dict, world_to_json,
    world_from_yaml, world_to_yaml,
    world_from_file, world_to_file,
)
from .raycast import RayCastHit, ray_cast, ray_cast_body
from .logger import configure_logging, get_logger
from .world import World
from .renderer.renderer import AsciiRenderer, PPMRenderer

__all__ = [
    "World",
    "RigidBody",
    "Vec2",
    "Mat22",
    "AABB",
    "Circle",
    "Polygon",
    "Shape",
    "Manifold",
    "collide",
    "point_in_polygon",
    "BroadPhase",
    "ForceField",
    "UniformField",
    "RadialField",
    "DragField",
    "BuoyancyField",
    "ContactSolver",
    "DistanceJoint",
    "Joint",
    "MouseJoint",
    "PrismaticJoint",
    "RevoluteJoint",
    "WeldJoint",
    "Diagnostics",
    "compute_energy",
    "compute_momentum",
    "body_to_dict",
    "body_from_dict",
    "world_to_dict",
    "world_from_dict",
    "world_to_json",
    "world_from_json",
    "world_to_yaml",
    "world_from_yaml",
    "world_to_file",
    "world_from_file",
    "AsciiRenderer",
    "PPMRenderer",
    "RayCastHit",
    "ray_cast",
    "ray_cast_body",
    "configure_logging",
    "get_logger",
]

__version__ = "3.0.0"