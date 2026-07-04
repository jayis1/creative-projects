"""Command-line interface for the rigid-body engine.

Subcommands:
  * run   — load a scene JSON, simulate, render ASCII frames.
  * save  — create a demo scene and save it as JSON.
  * info  — print info about a scene file.
  * render— load a scene, simulate, write PPM frames.
  * energy— load a scene, simulate, print energy/momentum diagnostics.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import List, Optional

from .core.body import RigidBody
from .core.shapes import Circle, Polygon
from .core.vec2 import Vec2
from .diagnostics import Diagnostics
from .joints.joints import DistanceJoint, RevoluteJoint, WeldJoint
from .renderer.renderer import AsciiRenderer, PPMRenderer
from .serialize import world_from_json, world_to_json
from .world import World

__all__ = ["main", "build_parser"]


def _build_demo_world() -> World:
    """Build the built-in demo scene."""
    world = World(gravity=Vec2(0.0, -9.81), velocity_iterations=12, position_iterations=4)
    floor = RigidBody(Polygon.box(24.0, 1.0), Vec2(0.0, -0.5), body_type=RigidBody.STATIC,
                      friction=0.6, restitution=0.0)
    floor.user_data = "floor"
    world.add_body(floor)
    for i in range(5):
        b = RigidBody(Polygon.box(1.5, 1.0), Vec2(0.0, 0.5 + i * 1.05),
                      body_type=RigidBody.DYNAMIC, density=2.0, friction=0.5, restitution=0.05)
        b.user_data = f"box{i}"
        world.add_body(b)
    ball = RigidBody(Circle(0.7), Vec2(8.0, 1.0), body_type=RigidBody.DYNAMIC,
                     density=3.0, friction=0.3, restitution=0.5)
    ball.linear_velocity = Vec2(-8.0, 0.0)
    ball.user_data = "ball"
    world.add_body(ball)
    pivot = RigidBody(Polygon.box(0.4, 0.4), Vec2(-6.0, 15.0), body_type=RigidBody.STATIC)
    world.add_body(pivot)
    bob = RigidBody(Circle(0.6), Vec2(-6.0, 11.0), body_type=RigidBody.DYNAMIC,
                    density=5.0, friction=0.3, restitution=0.1)
    world.add_body(bob)
    world.add_joint(RevoluteJoint(pivot, Vec2.zero(), bob, Vec2(0.0, 4.0)))
    ramp = RigidBody(Polygon.box(8.0, 0.5), Vec2(4.0, 3.0), angle=-0.35,
                     body_type=RigidBody.STATIC, friction=0.3)
    world.add_body(ramp)
    return world


def cmd_save(args: argparse.Namespace) -> int:
    world = _build_demo_world()
    world_to_json(world, args.output)
    print(f"Saved demo scene to {args.output} ({len(world.bodies)} bodies, {len(world.joints)} joints)")
    return 0


def cmd_info(args: argparse.Namespace) -> int:
    world = world_from_json(args.scene)
    print(f"Scene: {args.scene}")
    print(f"  Bodies: {len(world.bodies)}")
    print(f"  Joints: {len(world.joints)}")
    print(f"  Force fields: {len(world.force_fields)}")
    print(f"  Gravity: ({world.gravity.x}, {world.gravity.y})")
    print(f"  Iterations: vel={world.velocity_iterations} pos={world.position_iterations} joint={world.joint_iterations}")
    for i, b in enumerate(world.bodies):
        tag = b.user_data if b.user_data else f"body{i}"
        print(f"  [{i}] {b.body_type:8s} {b.shape.shape_type:8s} pos=({b.position.x:.2f}, {b.position.y:.2f}) tag={tag}")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    if args.scene:
        world = world_from_json(args.scene)
    else:
        world = _build_demo_world()
    renderer = AsciiRenderer(width=args.width, height=args.height,
                             world_min=Vec2(*args.bounds[:2]),
                             world_max=Vec2(*args.bounds[2:]))
    dt = 1.0 / args.fps
    for i in range(args.frames):
        if not args.no_clear:
            os.system("clear" if os.name == "posix" else "cls")
        world.step(dt)
        print(f"Frame {i+1}/{args.frames}  contacts={world.contact_count}  bodies={len(world.bodies)}")
        print(renderer.render(world.bodies))
    print("\nFinal positions:")
    for b in world.bodies:
        if b.is_dynamic:
            tag = b.user_data if b.user_data else "?"
            print(f"  {tag}: pos=({b.position.x:.3f}, {b.position.y:.3f}) angle={b.angle:.2f}")
    if args.output:
        world_to_json(world, args.output)
        print(f"\nSaved final state to {args.output}")
    return 0


def cmd_render(args: argparse.Namespace) -> int:
    if args.scene:
        world = world_from_json(args.scene)
    else:
        world = _build_demo_world()
    renderer = PPMRenderer(
        output_dir=args.output_dir,
        width=args.width, height=args.height,
        world_min=Vec2(*args.bounds[:2]),
        world_max=Vec2(*args.bounds[2:]),
    )
    dt = 1.0 / args.fps
    for i in range(args.frames):
        world.step(dt)
        path = renderer.render_frame(world.bodies)
        if (i + 1) % 30 == 0:
            print(f"  rendered frame {i+1}/{args.frames} → {path}")
    print(f"\nDone. {args.frames} PPM frames in {args.output_dir}/")
    print("Assemble with: ffmpeg -framerate %d -i %s/frame_%%04d.ppm out.gif" % (args.fps, args.output_dir))
    return 0


def cmd_energy(args: argparse.Namespace) -> int:
    if args.scene:
        world = world_from_json(args.scene)
    else:
        world = _build_demo_world()
    diag = Diagnostics()
    dt = 1.0 / args.fps
    for _ in range(args.frames):
        world.step(dt)
        diag.sample(world.bodies)
    report = diag.report()
    print(f"Energy & momentum over {args.frames} steps:")
    for k in ["kinetic", "potential", "total", "px", "py", "angular"]:
        if f"{k}_min" in report:
            print(f"  {k:10s}: min={report[f'{k}_min']:+.4f}  max={report[f'{k}_max']:+.4f}  mean={report[f'{k}_mean']:+.4f}")
    print(f"  energy drift: {diag.energy_drift():.4%}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rigid-body",
        description="2D rigid body physics engine CLI",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_save = sub.add_parser("save", help="Save the built-in demo scene as JSON")
    p_save.add_argument("output", help="Output JSON path")
    p_save.set_defaults(func=cmd_save)

    p_info = sub.add_parser("info", help="Print info about a scene file")
    p_info.add_argument("scene", help="Scene JSON path")
    p_info.set_defaults(func=cmd_info)

    p_run = sub.add_parser("run", help="Simulate and render ASCII frames")
    p_run.add_argument("--scene", "-s", help="Scene JSON (default: built-in demo)")
    p_run.add_argument("--frames", "-f", type=int, default=180, help="Number of frames")
    p_run.add_argument("--fps", type=int, default=60, help="Frames per second")
    p_run.add_argument("--width", type=int, default=72, help="ASCII width")
    p_run.add_argument("--height", type=int, default=28, help="ASCII height")
    p_run.add_argument("--bounds", type=float, nargs=4, default=[-13, -1, 13, 17],
                        help="World bounds: minX minY maxX maxY")
    p_run.add_argument("--no-clear", action="store_true", help="Don't clear screen between frames")
    p_run.add_argument("--output", "-o", help="Save final state as JSON")
    p_run.set_defaults(func=cmd_run)

    p_render = sub.add_parser("render", help="Simulate and write PPM image frames")
    p_render.add_argument("--scene", "-s", help="Scene JSON (default: built-in demo)")
    p_render.add_argument("--output-dir", "-o", default="frames", help="Output directory for PPM frames")
    p_render.add_argument("--frames", "-f", type=int, default=180, help="Number of frames")
    p_render.add_argument("--fps", type=int, default=60, help="Frames per second")
    p_render.add_argument("--width", type=int, default=320, help="Image width")
    p_render.add_argument("--height", type=int, default=240, help="Image height")
    p_render.add_argument("--bounds", type=float, nargs=4, default=[-13, -1, 13, 17],
                           help="World bounds: minX minY maxX maxY")
    p_render.set_defaults(func=cmd_render)

    p_energy = sub.add_parser("energy", help="Simulate and report energy/momentum")
    p_energy.add_argument("--scene", "-s", help="Scene JSON (default: built-in demo)")
    p_energy.add_argument("--frames", "-f", type=int, default=300, help="Number of frames")
    p_energy.add_argument("--fps", type=int, default=60, help="Frames per second")
    p_energy.set_defaults(func=cmd_energy)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)