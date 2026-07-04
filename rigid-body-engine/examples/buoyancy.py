#!/usr/bin/env python3
"""Example: buoyancy — floating boxes in fluid.

Demonstrates the BuoyancyField force field. Two boxes with different
densities are dropped into a fluid; the lighter one floats and the heavier
one sinks.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rigidbody import World, RigidBody, Vec2, Polygon
from rigidbody.core.fields import BuoyancyField
from rigidbody.renderer import AsciiRenderer


def build_world():
    world = World(gravity=Vec2(0.0, -9.81), allow_sleeping=False)
    floor = RigidBody(
        Polygon.box(20.0, 1.0), Vec2(0.0, -6.5),
        body_type=RigidBody.STATIC, friction=0.6
    )
    world.add_body(floor)

    # Fluid surface at y=0
    world.add_force_field(BuoyancyField(
        fluid_level=0.0, fluid_density=1.5,
        gravity=Vec2(0, -9.81), drag=0.8,
    ))

    # Light box (density < fluid density) — floats.
    light = RigidBody(
        Polygon.box(2.0, 2.0), Vec2(-3.0, 5.0),
        body_type=RigidBody.DYNAMIC, density=0.5,
        friction=0.3, restitution=0.2,
    )
    light.user_data = "light"
    world.add_body(light)

    # Heavy box (density > fluid density) — sinks.
    heavy = RigidBody(
        Polygon.box(2.0, 2.0), Vec2(3.0, 5.0),
        body_type=RigidBody.DYNAMIC, density=3.0,
        friction=0.3, restitution=0.2,
    )
    heavy.user_data = "heavy"
    world.add_body(heavy)

    return world


def main():
    world = build_world()
    renderer = AsciiRenderer(
        width=70, height=30,
        world_min=Vec2(-10, -8), world_max=Vec2(10, 8),
    )
    dt = 1.0 / 60.0
    frames = int(sys.argv[1]) if len(sys.argv) > 1 else 400
    for i in range(frames):
        os.system("clear" if os.name == "posix" else "cls")
        world.step(dt)
        print(f"Frame {i+1}/{frames}")
        print(renderer.render(world.bodies))
    light = world.bodies[1]
    heavy = world.bodies[2]
    print(f"\nLight box final y: {light.position.y:.2f} (should be above floor)")
    print(f"Heavy box final y: {heavy.position.y:.2f} (should be on floor)")


if __name__ == "__main__":
    main()