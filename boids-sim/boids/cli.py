"""Command-line interface for the boids flocking simulation.

Enhanced v3.0: animated SVG, stats tracking, multi-species, path following,
quadtree spatial index, structured logging, JSON state export.

Subcommands:
    run       — Run simulation and render frames (SVG/PPM/ASCII/JSON)
    stats     — Run N steps and print JSON statistics
    ascii     — Live terminal ASCII animation
    save      — Run and save final state to JSON
    sweep     — Parameter sweep with range or list values
    presets   — List available named presets
    config    — Save a config template file
    animate   — Generate animated SVG from simulation
    track     — Run simulation and output time-series statistics
    benchmark — Benchmark spatial index performance
"""

from __future__ import annotations
import argparse
import json
import sys
import os
import logging

from boids.simulation import BoidSimulation
from boids.config import SimulationConfig, load_config, save_config, get_preset, list_presets
from boids.renderer import (
    ASCIIRenderer, SVGRenderer, PPMRenderer, TrailSVGRenderer,
    AnimatedSVGRenderer, JSONRenderer,
)

logger = logging.getLogger("boids.cli")


def cmd_run(args: argparse.Namespace) -> int:
    """Run the simulation and render frames."""
    _setup_logging(args)
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

    # set paths if provided
    if args.path:
        waypoints = [(args.path[i], args.path[i+1]) for i in range(0, len(args.path)-1, 2)]
        sim.set_all_paths(waypoints, loop=args.path_loop)

    os.makedirs(args.output, exist_ok=True)

    ascii_renderer = ASCIIRenderer(args.cols, args.rows)
    svg_renderer = SVGRenderer()
    trail_svg_renderer = TrailSVGRenderer()
    ppm_renderer = PPMRenderer()
    json_renderer = JSONRenderer()

    for step in range(args.steps):
        sim.step()
        if step % args.frame_interval == 0:
            # ASCII to stdout for first few frames
            if args.ascii and step < 5:
                print(f"\n=== Step {sim.tick} ===")
                print(ascii_renderer.render(sim))
            # SVG
            if args.svg:
                svg_renderer.render(sim, os.path.join(args.output, f"frame_{step:05d}.svg"))
            # Trail SVG
            if args.trail_svg:
                trail_svg_renderer.render(sim, os.path.join(args.output, f"frame_{step:05d}.svg"))
            # PPM
            if args.ppm:
                ppm_renderer.render(sim, os.path.join(args.output, f"frame_{step:05d}.ppm"), scale=args.scale)
            # JSON state
            if args.json:
                json_renderer.render(sim, os.path.join(args.output, f"frame_{step:05d}.json"))

    # save final state
    if args.save:
        sim.save(args.save)
        print(f"Saved state to {args.save}")

    # print final stats
    stats = sim.stats()
    print(f"\n=== Final Statistics (tick {stats['tick']}) ===")
    print(f"  Boids:      {stats['count']}")
    print(f"  Predators:  {stats['predators']}")
    print(f"  Obstacles:  {stats['obstacles']}")
    print(f"  Avg speed:  {stats['avg_speed']:.2f}")
    print(f"  Alignment:  {stats['alignment']:.3f}  (1.0 = perfectly aligned)")
    print(f"  Centroid:   ({stats['centroid'][0]:.1f}, {stats['centroid'][1]:.1f})")
    print(f"  Spread:     {stats['spread']:.1f}")
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    """Run N steps and report statistics."""
    _setup_logging(args)
    cfg = _build_config(args)
    sim = BoidSimulation(cfg)
    for _ in range(args.steps):
        sim.step()
    stats = sim.stats()
    print(json.dumps(stats, indent=2))
    return 0


def cmd_ascii(args: argparse.Namespace) -> int:
    """Run and display ASCII animation in terminal."""
    _setup_logging(args)
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


def cmd_save(args: argparse.Namespace) -> int:
    """Run N steps and save the final state to a JSON file."""
    _setup_logging(args)
    cfg = _build_config(args)
    sim = BoidSimulation(cfg)
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
    for _ in range(args.steps):
        sim.step()
    sim.save(args.output)
    print(f"Saved simulation state to {args.output}")
    return 0


def cmd_sweep(args: argparse.Namespace) -> int:
    """Parameter sweep: vary one parameter and report statistics for each value."""
    _setup_logging(args)
    cfg = _build_config(args)
    param = args.param
    values = _parse_sweep_values(args.values)
    results = []
    for val in values:
        sweep_cfg = SimulationConfig.from_dict(cfg.to_dict())
        if not hasattr(sweep_cfg, param):
            print(f"Error: unknown parameter '{param}'", file=sys.stderr)
            return 1
        setattr(sweep_cfg, param, val)
        sim = BoidSimulation(sweep_cfg)
        for _ in range(args.steps):
            sim.step()
        stats = sim.stats()
        stats["param_value"] = val
        results.append(stats)
        print(f"  {param}={val}: alignment={stats['alignment']:.3f}  spread={stats['spread']:.1f}  avg_speed={stats['avg_speed']:.2f}")
    if args.output:
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)
        print(f"Saved sweep results to {args.output}")
    return 0


def cmd_presets(args: argparse.Namespace) -> int:
    """List available presets."""
    presets = list_presets()
    print("Available presets:")
    for name in presets:
        print(f"  {name}")
    return 0


def cmd_config(args: argparse.Namespace) -> int:
    """Save a default config file template."""
    cfg = _build_config(args)
    save_config(cfg, args.output)
    print(f"Saved config to {args.output}")
    return 0


def cmd_animate(args: argparse.Namespace) -> int:
    """Generate an animated SVG from the simulation."""
    _setup_logging(args)
    cfg = _build_config(args)
    sim = BoidSimulation(cfg)
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
    renderer = AnimatedSVGRenderer(fps=args.fps, loop=not args.no_loop)
    renderer.render(sim, args.output, steps=args.steps)
    print(f"Saved animated SVG to {args.output} ({args.steps} frames at {args.fps} fps)")
    return 0


def cmd_track(args: argparse.Namespace) -> int:
    """Run simulation and output time-series statistics as JSON."""
    _setup_logging(args)
    cfg = _build_config(args)
    sim = BoidSimulation(cfg)
    if args.predators:
        for pair in args.predators:
            x, y = pair
            sim.add_predator(x, y)
    for _ in range(args.steps):
        sim.step()
    history = sim.tracker.history()
    ticks = sim.tracker.ticks()
    output = {
        "ticks": ticks,
        "stats": history,
        "summary": sim.tracker.summary(),
    }
    if args.output:
        with open(args.output, "w") as f:
            json.dump(output, f, indent=2)
        print(f"Saved {len(history)} stat snapshots to {args.output}")
    else:
        print(json.dumps(output, indent=2))
    return 0


def cmd_benchmark(args: argparse.Namespace) -> int:
    """Benchmark spatial index performance."""
    _setup_logging(args)
    import time

    cfg = _build_config(args)
    print(f"Benchmarking with {cfg.num_boids} boids, {args.steps} steps\n")

    for index_type in ("grid", "quadtree"):
        bench_cfg = SimulationConfig.from_dict(cfg.to_dict())
        bench_cfg.spatial_index = index_type
        sim = BoidSimulation(bench_cfg)
        # Warmup
        sim.step()
        start = time.perf_counter()
        for _ in range(args.steps):
            sim.step()
        elapsed = time.perf_counter() - start
        steps_per_sec = args.steps / elapsed
        ms_per_step = (elapsed / args.steps) * 1000
        print(f"  {index_type:10s}: {ms_per_step:.2f} ms/step  ({steps_per_sec:.0f} steps/s)")
    return 0


# --------------------------------------------------------------------------- #
#  Helpers
# --------------------------------------------------------------------------- #
def _setup_logging(args: argparse.Namespace) -> None:
    """Configure logging level from CLI args."""
    level = logging.WARNING
    if getattr(args, "verbose", 0) >= 2:
        level = logging.DEBUG
    elif getattr(args, "verbose", 0) >= 1:
        level = logging.INFO
    logging.basicConfig(level=level, format="[%(name)s] %(levelname)s: %(message)s")


def _build_config(args: argparse.Namespace) -> SimulationConfig:
    """Build config from CLI args, optionally loading from file or preset."""
    # Start from config file if specified
    if getattr(args, "config_file", None):
        cfg = load_config(args.config_file)
    elif getattr(args, "preset", None):
        cfg = get_preset(args.preset)
    else:
        cfg = SimulationConfig()

    # Override with CLI args
    if getattr(args, "num_boids", None) is not None:
        cfg.num_boids = args.num_boids
    if getattr(args, "width", None) is not None:
        cfg.width = args.width
    if getattr(args, "height", None) is not None:
        cfg.height = args.height
    if getattr(args, "sep", None) is not None:
        cfg.w_sep = args.sep
    if getattr(args, "ali", None) is not None:
        cfg.w_ali = args.ali
    if getattr(args, "coh", None) is not None:
        cfg.w_coh = args.coh
    if getattr(args, "max_speed", None) is not None:
        cfg.max_speed = args.max_speed
    if getattr(args, "wrap", None):
        cfg.use_wrap = True
    if getattr(args, "trail", None) is not None:
        cfg.trail_length = args.trail
    if getattr(args, "spatial_index", None) is not None:
        cfg.spatial_index = args.spatial_index
    if getattr(args, "num_species", None) is not None:
        cfg.num_species = args.num_species
    return cfg


def _parse_sweep_values(values_str: str) -> list:
    """Parse a comma-separated list of values, or a range 'start:stop:step'."""
    if ":" in values_str and values_str.count(":") == 2:
        parts = values_str.split(":")
        start, stop, step = float(parts[0]), float(parts[1]), float(parts[2])
        if step == 0:
            raise ValueError("step cannot be zero")
        values = []
        current = start
        if step > 0:
            while current <= stop + 1e-9:
                values.append(current)
                current += step
        else:
            while current >= stop - 1e-9:
                values.append(current)
                current += step
        return values
    else:
        parts = values_str.split(",")
        result = []
        for p in parts:
            p = p.strip()
            try:
                result.append(int(p))
            except ValueError:
                result.append(float(p))
        return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="boids-sim",
        description="Boids flocking simulation v3.0 — Reynolds 1987",
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
        p.add_argument("--wrap", action="store_true", default=False, help="Toroidal wrap")
        p.add_argument("--trail", type=int, default=None, help="Trail length (0=off)")
        p.add_argument("--config-file", type=str, default=None, help="Load config from JSON/YAML/TOML file")
        p.add_argument("--preset", type=str, default=None, help="Use a named preset")
        p.add_argument("--spatial-index", type=str, default=None, choices=["grid", "quadtree"], help="Spatial index type")
        p.add_argument("--num-species", type=int, default=None, help="Number of species for multi-species flocking")
        p.add_argument("-v", "--verbose", action="count", default=0, help="Increase verbosity (-v info, -vv debug)")

    # run
    p_run = subparsers.add_parser("run", help="Run simulation and render frames")
    add_common(p_run)
    p_run.add_argument("-s", "--steps", type=int, default=100, help="Simulation steps")
    p_run.add_argument("-o", "--output", default="output", help="Output directory")
    p_run.add_argument("--frame-interval", type=int, default=10, help="Render every N steps")
    p_run.add_argument("--ascii", action="store_true", help="Print ASCII frames to stdout")
    p_run.add_argument("--svg", action="store_true", help="Export SVG frames")
    p_run.add_argument("--trail-svg", action="store_true", help="Export trail SVG frames")
    p_run.add_argument("--ppm", action="store_true", help="Export PPM frames")
    p_run.add_argument("--json", action="store_true", help="Export JSON state frames")
    p_run.add_argument("--scale", type=float, default=1.0, help="PPM scale factor")
    p_run.add_argument("--cols", type=int, default=80, help="ASCII cols")
    p_run.add_argument("--rows", type=int, default=24, help="ASCII rows")
    p_run.add_argument("--save", type=str, default=None, help="Save final state to JSON file")
    p_run.add_argument("--obstacles", nargs=3, type=float, action="append", metavar=("X", "Y", "R"), help="Add obstacle (repeatable)")
    p_run.add_argument("--predators", nargs=2, type=float, action="append", metavar=("X", "Y"), help="Add predator (repeatable)")
    p_run.add_argument("--goal", nargs=2, type=float, metavar=("X", "Y"), help="Set goal position")
    p_run.add_argument("--path", nargs="+", type=float, metavar="X Y ...", help="Waypoint coords for path following (x1 y1 x2 y2 ...)")
    p_run.add_argument("--path-loop", action="store_true", default=False, help="Loop the path")
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

    # save
    p_save = subparsers.add_parser("save", help="Run and save final state")
    add_common(p_save)
    p_save.add_argument("-s", "--steps", type=int, default=100, help="Steps")
    p_save.add_argument("output", type=str, help="Output JSON file path")
    p_save.add_argument("--obstacles", nargs=3, type=float, action="append", metavar=("X", "Y", "R"), help="Add obstacle")
    p_save.add_argument("--predators", nargs=2, type=float, action="append", metavar=("X", "Y"), help="Add predator")
    p_save.add_argument("--goal", nargs=2, type=float, metavar=("X", "Y"), help="Set goal")
    p_save.set_defaults(func=cmd_save)

    # sweep
    p_sweep = subparsers.add_parser("sweep", help="Parameter sweep")
    add_common(p_sweep)
    p_sweep.add_argument("--param", type=str, required=True, help="Parameter to sweep")
    p_sweep.add_argument("--values", type=str, required=True, help="Comma-separated values or start:stop:step range")
    p_sweep.add_argument("-s", "--steps", type=int, default=100, help="Steps per value")
    p_sweep.add_argument("-o", "--output", type=str, default=None, help="Save results JSON")
    p_sweep.set_defaults(func=cmd_sweep)

    # presets
    p_presets = subparsers.add_parser("presets", help="List available presets")
    p_presets.set_defaults(func=cmd_presets)

    # config
    p_config = subparsers.add_parser("config", help="Save a config template file")
    add_common(p_config)
    p_config.add_argument("output", type=str, help="Output config file path (.json/.yaml/.toml)")
    p_config.set_defaults(func=cmd_config)

    # animate
    p_animate = subparsers.add_parser("animate", help="Generate animated SVG")
    add_common(p_animate)
    p_animate.add_argument("-s", "--steps", type=int, default=100, help="Number of steps to animate")
    p_animate.add_argument("-o", "--output", type=str, default="flock.svg", help="Output SVG file")
    p_animate.add_argument("--fps", type=float, default=10.0, help="Frames per second")
    p_animate.add_argument("--no-loop", action="store_true", default=False, help="Don't loop animation")
    p_animate.add_argument("--obstacles", nargs=3, type=float, action="append", metavar=("X", "Y", "R"), help="Add obstacle")
    p_animate.add_argument("--predators", nargs=2, type=float, action="append", metavar=("X", "Y"), help="Add predator")
    p_animate.add_argument("--goal", nargs=2, type=float, metavar=("X", "Y"), help="Set goal")
    p_animate.set_defaults(func=cmd_animate)

    # track
    p_track = subparsers.add_parser("track", help="Run simulation and output time-series statistics")
    add_common(p_track)
    p_track.add_argument("-s", "--steps", type=int, default=100, help="Number of steps")
    p_track.add_argument("-o", "--output", type=str, default=None, help="Save results to JSON file")
    p_track.add_argument("--predators", nargs=2, type=float, action="append", metavar=("X", "Y"), help="Add predator")
    p_track.set_defaults(func=cmd_track)

    # benchmark
    p_bench = subparsers.add_parser("benchmark", help="Benchmark spatial index performance")
    add_common(p_bench)
    p_bench.add_argument("-s", "--steps", type=int, default=50, help="Steps to benchmark")
    p_bench.set_defaults(func=cmd_benchmark)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())