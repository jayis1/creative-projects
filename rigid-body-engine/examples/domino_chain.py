#!/usr/bin/env python3
"""Example: domino chain reaction.

Sets up a row of upright boxes and tips the first one over, creating a
chain reaction. Demonstrates polygon-polygon collision, friction, and
stacking stability.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rigidbody import World, RigidBody, Vec2, Polygon
from rigidbody.renderer import AsciiRenderer


def build_world():
    world = World(
        gravity=Vec2(0.0, -9.81),
        velocity_iterations=15,
        position_iterations=6,
        allow_sleeping=False,
    )
    floor = RigidBody(
        Polygon.box(30.0, 1.0), Vec2(0.0, -0.5),
        body_type=RigidBody.STATIC, friction=0.7
    )
    world.add_body(floor)

    # Row of dominoes (tall thin boxes).
    n = 12
    for i in range(n):
        x = -8.0 + i * 1.2
        domino = RigidBody(
            Polygon.box(0.3, 2.0), Vec2(x, 1.0),
            body_type=RigidBody.DYNAMIC, density=3.0,
            friction=0.5, restitution=0.1,
            linear_damping=0.1, angular_damping=0.1,
        )
        domino.user_data = f"domino{i}"
        world.add_body(domino)

    # Tip the first domino.
    domino0 = world.bodies[1]
    domino0.apply_impulse(Vec2(3.0, 0), Vec2(domino0.position.x, domino0.position.y + 0.8))

    return world


def main():
    world = build_world()
    renderer = AsciiRenderer(
        width=80, height=30,
        world_min=Vec2(-12, -1), world_max=Vec2(12, 8),
    )
    dt = 1.0 / 60.0
    frames = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    for i in range(frames):
        os.system("clear" if os.name == "posix" else "cls")
        world.step(dt)
        print(f"Frame {i+1}/{frames}  contacts={world.contact_count}")
        print(renderer.render(world.bodies))
    print("\nFinal positions:")
    for b in world.bodies:
        if b.is_dynamic:
            print(f"  {b.user_data}: angle={b.angle:.2f} pos={b.position}")


if __name__ == "__main__":
    main()