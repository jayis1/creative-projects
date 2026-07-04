#!/usr/bin/env python3
"""Example: gravity well — planetary orbits.

Demonstrates the RadialField by simulating bodies orbiting a central
"star". Each body is given an initial tangential velocity to create a
stable (or not-so-stable) orbit.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rigidbody import World, RigidBody, Vec2, Circle
from rigidbody.core.fields import RadialField, DragField
from rigidbody.renderer import AsciiRenderer


def build_world():
    world = World(gravity=Vec2(0, 0), allow_sleeping=False)
    # Central "star" — static body at origin.
    star = RigidBody(Circle(1.0), Vec2(0, 0), body_type=RigidBody.STATIC)
    star.user_data = "star"
    world.add_body(star)
    # Gravity well centered on the star.
    world.add_force_field(RadialField(
        Vec2(0, 0), strength=200, falloff=2.0,
        min_radius=1.0, max_radius=50.0,
    ))
    # Planet 1 — circular orbit.
    p1 = RigidBody(Circle(0.3), Vec2(8, 0), density=1, linear_damping=0)
    p1.linear_velocity = Vec2(0, 5)
    p1.user_data = "planet1"
    world.add_body(p1)
    # Planet 2 — elliptical orbit (different speed).
    p2 = RigidBody(Circle(0.2), Vec2(-12, 0), density=1, linear_damping=0)
    p2.linear_velocity = Vec2(0, -4)
    p2.user_data = "planet2"
    world.add_body(p2)
    # Comet — highly eccentric.
    p3 = RigidBody(Circle(0.15), Vec2(0, 15), density=1, linear_damping=0)
    p3.linear_velocity = Vec2(3, 0)
    p3.user_data = "comet"
    world.add_body(p3)
    return world


def main():
    world = build_world()
    renderer = AsciiRenderer(
        width=80, height=35,
        world_min=Vec2(-20, -15), world_max=Vec2(20, 15),
    )
    dt = 1.0 / 60.0
    frames = int(sys.argv[1]) if len(sys.argv) > 1 else 600
    for i in range(frames):
        os.system("clear" if os.name == "posix" else "cls")
        world.step(dt)
        print(f"Frame {i+1}/{frames}")
        print(renderer.render(world.bodies))
    print("\nFinal positions:")
    for b in world.bodies:
        if b.is_dynamic:
            print(f"  {b.user_data}: pos={b.position} v={b.linear_velocity}")


if __name__ == "__main__":
    main()