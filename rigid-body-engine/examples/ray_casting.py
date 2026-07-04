#!/usr/bin/env python3
"""Example: ray casting — line-of-sight query.

Creates a scene with obstacles and casts rays to demonstrate the ray
casting API. Prints which body each ray hits and the contact point.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rigidbody import World, RigidBody, Vec2, Polygon, Circle


def build_world():
    world = World(gravity=Vec2(0, 0))
    # Obstacle wall
    wall = RigidBody(Polygon.box(1.0, 8.0), Vec2(0, 0), body_type=RigidBody.STATIC)
    wall.user_data = "wall"
    world.add_body(wall)
    # Circular obstacle
    ball = RigidBody(Circle(1.5), Vec2(5, 3), body_type=RigidBody.STATIC)
    ball.user_data = "ball"
    world.add_body(ball)
    # Polygon obstacle
    poly = RigidBody(Polygon.regular_polygon(5, 2.0), Vec2(5, -3),
                     angle=0.5, body_type=RigidBody.STATIC)
    poly.user_data = "pentagon"
    world.add_body(poly)
    return world


def main():
    world = build_world()
    world.step(1 / 60)  # Initialize AABBs

    # Cast rays from the left toward the right.
    rays = [
        ("horizontal", Vec2(-5, 0), Vec2(1, 0)),
        ("upward", Vec2(-5, 0), Vec2(1, 0.5)),
        ("downward", Vec2(-5, 0), Vec2(1, -0.5)),
        ("straight up", Vec2(0, -8), Vec2(0, 1)),
    ]

    for label, origin, direction in rays:
        hit = world.ray_cast(origin, direction, max_distance=50)
        print(f"Ray '{label}': origin={origin}, dir={direction}")
        if hit is None:
            print("  → no hit")
        else:
            body = world.bodies[hit.body_index]
            tag = body.user_data or f"body{hit.body_index}"
            print(f"  → hit {tag} at ({hit.point.x:.2f}, {hit.point.y:.2f}) "
                  f"normal=({hit.normal.x:.2f}, {hit.normal.y:.2f}) "
                  f"dist={hit.fraction:.2f}")

    # Demonstrate the 'ignore' parameter.
    print("\nIgnoring the wall:")
    hit = world.ray_cast(Vec2(-5, 0), Vec2(1, 0), max_distance=50, ignore={0})
    if hit:
        tag = world.bodies[hit.body_index].user_data
        print(f"  → hit {tag} instead")


if __name__ == "__main__":
    main()