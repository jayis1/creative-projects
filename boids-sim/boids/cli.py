"""Command-line interface for the boids flocking simulation."""

from __future__ import annotations
import argparse
import json
import sys
import os

from boids.simulation import BoidSimulation, SimulationConfig
from boids.renderer import ASCIIRenderer, SVGRenderer, PPMRenderer


def cmd_run(args: argparse.Namespace) -> int:
    """Run the simulation and render frames."""
    cfg = _build_config(args)
    sim = BoidSimulation(cfg)

    # setup obstacles and predators
    if args.obstacles:
        for pair in args.obstacles:
            x, y, r = pair
            sim.add_obstacle(x, y, r)
    if args.predators:
        for pair in args.predators:
            x, y = pair
            sim.add_predator(x, y)
    if args.goal:
        sim.set_goal(args.goal[0], args.goal[1])

    os.makedirs(args.output, exist_ok=True)

    ascii_renderer = ASCIIRenderer(args.cols, args.rows)
    svg_renderer = SVGRenderer()
    pp_m_renderer = PPMRenderer()

    for step in range(args.steps):
        sim.step()
        if step % args.frame_interval == 0:
            # ASCII to stdout for first few frames
            if args.ascii and step < 5:
                print(f"\n=== Step {sim.tick} ===")
                print(ascii_renderer.render(sim))
            # SVG
            if args.svg:
                svg_renderer.render(
                    sim, os.path.join(args.output, f"frame_{step:05d}.svg")
                )
            # PPM
            if args.ppm:
                pp_m_renderer.render(
                    sim,
                    os.path.join(args.output, f"frame_{step:05d}.ppm"),
                    scale=args.scale,
                )
            # JSON state
            if args.json:
                with open(
                    os.path.join(args.output, f"frame_{step:05d}.json"), "w"
                ) as f:
                    json.dump(sim.to_dict(), f, indent=2)

    # print final stats
    stats = sim.stats()
    print(f"\n=== Final Statistics (tick {stats['tick']}) ===")
    print(f"  Boids:      {stats['count']}")
    print(f"  Predators:  {stats['predators']}")
    print(f"  Obstacles:  {stats['obstacles']}")
    print(f"  Avg speed:  {stats['avg_speed']:.2f}")
    print(f"  Alignment:  {stats['alignment']:.3f}  (1.0 = perfectly aligned)")
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    """Run N steps and report statistics."""
    cfg = _build_config(args)
    sim = BoidSimulation(cfg)
    for _ in range(args.steps):
        sim.step()
    stats = sim.stats()
    print(json.dumps(stats, indent=2))
    return 0


def cmd_ascii(args: argparse.Namespace) -> int:
    """Run and display ASCII animation in terminal."""
    cfg = _build_config(args)
    sim = BoidSimulation(cfg)
    renderer = ASCIIRenderer(args.cols, args.rows)
    for step in range(args.steps):
        sim.step()
        frame = renderer.render(sim)
        # clear screen and render
        sys.stdout.write("\033[2J\033[H")
        sys.stdout.write(f"=== Step {sim.tick} ===\n")
        sys.stdout.write(frame)
        sys.stdout.write("\n")
        sys.stdout.flush()
    stats = sim.stats()
    print(f"\nAlignment: {stats['alignment']:.3f}  Avg speed: {stats['avg_speed']:.2f}")
    return 0


def _build_config(args: argparse.Namespace) -> SimulationConfig:
    cfg = SimulationConfig()
    if args.num_boids is not None:
        cfg.num_boids = args.num_boids
    if args.width is not None:
        cfg.width = args.width
    if args.height is not None:
        cfg.height = args.height
    if args.sep is not None:
        cfg.w_sep = args.sep
    if args.ali is not None:
        cfg.w_ali = args.ali
    if args.coh is not None:
        cfg.w_coh = args.coh
    if args.max_speed is not None:
        cfg.max_speed = args.max_speed
    if args.wrap is not None:
        cfg.use_wrap = args.wrap
    return cfg


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="boids-sim",
        description="Boids flocking simulation — Reynolds 1987",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # common options
    def add_common(p: argparse.ArgumentParser) -> None:
        p.add_argument("-n", "--num-boids", type=int, default=None, help="Number of boids")
        p.add_argument("--width", type=float, default=None, help="World width")
        p.add_argument("--height", type=float, default=None, help="World height")
        p.add_argument("--sep", type=float, default=None, help="Separation weight")
        p.add_argument("--ali", type=float, default=None, help="Alignment weight")
        p.add_argument("--coh", type=float, default=None, help="Cohesion weight")
        p.add_argument("--max-speed", type=float, default=None, help="Max speed")
        p.add_argument("--wrap", action="store_true", default=None, help="Toroidal wrap")

    # run
    p_run = subparsers.add_parser("run", help="Run simulation and render frames")
    add_common(p_run)
    p_run.add_argument("-s", "--steps", type=int, default=100, help="Simulation steps")
    p_run.add_argument("-o", "--output", default="output", help="Output directory")
    p_run.add_argument("--frame-interval", type=int, default=10, help="Render every N steps")
    p_run.add_argument("--ascii", action="store_true", help="Print ASCII frames to stdout")
    p_run.add_argument("--svg", action="store_true", help="Export SVG frames")
    p_run.add_argument("--ppm", action="store_true", help="Export PPM frames")
    p_run.add_argument("--json", action="store_true", help="Export JSON state frames")
    p_run.add_argument("--scale", type=float, default=1.0, help="PPM scale factor")
    p_run.add_argument("--cols", type=int, default=80, help="ASCII cols")
    p_run.add_argument("--rows", type=int, default=24, help="ASCII rows")
    p_run.add_argument(
        "--obstacles", nargs=3, type=float, action="append",
        metavar=("X", "Y", "R"), help="Add obstacle (repeatable)",
    )
    p_run.add_argument(
        "--predators", nargs=2, type=float, action="append",
        metavar=("X", "Y"), help="Add predator at (X, Y) (repeatable)",
    )
    p_run.add_argument(
        "--goal", nargs=2, type=float, metavar=("X", "Y"),
        help="Set goal position boids seek toward",
    )
    p_run.set_defaults(func=cmd_run)

    # stats
    p_stats = subparsers.add_parser("stats", help="Run simulation and print stats")
    add_common(p_stats)
    p_stats.add_argument("-s", "--steps", type=int, default=100, help="Steps")
    p_stats.set_defaults(func=cmd_stats)

    # ascii
    p_ascii = subparsers.add_parser("ascii", help="Live ASCII animation")
    add_common(p_ascii)
    p_ascii.add_argument("-s", "--steps", type=int, default=100, help="Steps")
    p_ascii.add_argument("--cols", type=int, default=80, help="ASCII cols")
    p_ascii.add_argument("--rows", type=int, default=24, help="ASCII rows")
    p_ascii.set_defaults(func=cmd_ascii)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())