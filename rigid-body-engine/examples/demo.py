#!/usr/bin/env python3
"""Demo: stack of boxes, a ball, a pendulum, and a ramp.

Renders ASCII frames to stdout so you can watch the simulation evolve in the
terminal without any GUI dependencies.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rigidbody import World, RigidBody, Vec2, Polygon, Circle
from rigidbody.joints import DistanceJoint, RevoluteJoint
from rigidbody.renderer import AsciiRenderer

def build_world():
    world = World(gravity=Vec2(0.0, -9.81), velocity_iterations=12, position_iterations=4)

    # Floor.
    floor = RigidBody(Polygon.box(24.0, 1.0), Vec2(0.0, -0.5), body_type=RigidBody.STATIC,
                      friction=0.6, restitution=0.0)
    floor.user_data = "floor"
    world.add_body(floor)

    # Left & right walls.
    lw = RigidBody(Polygon.box(1.0, 20.0), Vec2(-12.0, 10.0), body_type=RigidBody.STATIC, friction=0.6)
    rw = RigidBody(Polygon.box(1.0, 20.0), Vec2(12.0, 10.0), body_type=RigidBody.STATIC, friction=0.6)
    world.add_body(lw)
    world.add_body(rw)

    # Stack of 5 boxes.
    for i in range(5):
        b = RigidBody(Polygon.box(1.5, 1.0), Vec2(0.0, 0.5 + i * 1.05),
                      body_type=RigidBody.DYNAMIC, density=2.0, friction=0.5, restitution=0.05)
        b.user_data = f"box{i}"
        world.add_body(b)

    # Ball rolling in from the right.
    ball = RigidBody(Circle(0.7), Vec2(8.0, 1.0), body_type=RigidBody.DYNAMIC,
                     density=3.0, friction=0.3, restitution=0.5)
    ball.linear_velocity = Vec2(-8.0, 0.0)
    ball.user_data = "ball"
    world.add_body(ball)

    # Pendulum: a pivot fixed to the ceiling, a bob hanging by a rod.
    pivot_body = RigidBody(Polygon.box(0.4, 0.4), Vec2(-6.0, 15.0), body_type=RigidBody.STATIC)
    world.add_body(pivot_body)
    bob = RigidBody(Circle(0.6), Vec2(-6.0, 11.0), body_type=RigidBody.DYNAMIC, density=5.0,
                    friction=0.3, restitution=0.1)
    world.add_body(bob)
    # Revolute pin at the pivot, motor off.
    world.add_joint(RevoluteJoint(pivot_body, Vec2.zero(), bob, Vec2(0.0, 4.0)))

    # Ramp (a static tilted box).
    ramp = RigidBody(Polygon.box(8.0, 0.5), Vec2(4.0, 3.0), angle=-0.35,
                     body_type=RigidBody.STATIC, friction=0.3)
    world.add_body(ramp)

    return world

def main():
    world = build_world()
    renderer = AsciiRenderer(width=72, height=28,
                             world_min=Vec2(-13, -1), world_max=Vec2(13, 17))
    dt = 1.0 / 60.0
    frames = int(float(sys.argv[1]) if len(sys.argv) > 1 else 180)
    for i in range(frames):
        # Clear screen for animation effect.
        os.system("clear" if os.name == "posix" else "cls")
        world.step(dt)
        print(f"Frame {i+1}/{frames}  contacts={world.contact_count}  bodies={len(world.bodies)}")
        print(renderer.render(world.bodies))
    print("\nFinal positions:")
    for b in world.bodies:
        if b.is_dynamic:
            print(f"  {b.user_data}: pos={b.position} angle={b.angle:.2f} sleeping={b.sleeping}")

if __name__ == "__main__":
    main()