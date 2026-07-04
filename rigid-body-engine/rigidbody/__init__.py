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
from .solver.contact_solver import ContactSolver
from .joints.joints import DistanceJoint, Joint, MouseJoint, RevoluteJoint, WeldJoint
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
    "ContactSolver",
    "DistanceJoint",
    "Joint",
    "MouseJoint",
    "RevoluteJoint",
    "WeldJoint",
    "AsciiRenderer",
    "PPMRenderer",
]

__version__ = "1.0.0"