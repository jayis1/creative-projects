"""Command line interface for Particle Life."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

from .analysis import summarize_simulation, sweep_parameters
from .engine import ParticleLifeSimulation, SimulationConfig
from .io import dump_csv, dump_json, dump_mapping, load_mapping
from .presets import built_in_presets, get_preset, preset_names
from .render import render_ascii, render_ppm, render_svg

LOGGER = logging.getLogger("particle_life_sim")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Particle Life simulator")
    parser.add_argument("--log-level", default="WARNING", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    subparsers = parser.add_subparsers(dest="command", required=True)

    presets_parser = subparsers.add_parser("presets", help="List bundled presets")
    presets_parser.set_defaults(handler=_handle_presets)

    export_parser = subparsers.add_parser("export-preset", help="Write a preset to JSON or YAML")
    export_parser.add_argument("name", choices=preset_names())
    export_parser.add_argument("--output", required=True)
    export_parser.set_defaults(handler=_handle_export_preset)

    run_parser = subparsers.add_parser("run", help="Run a simulation and print metrics")
    _add_common_run_args(run_parser)
    run_parser.add_argument("--output")
    run_parser.set_defaults(handler=_handle_run)

    timeline_parser = subparsers.add_parser("timeline", help="Run and emit a sampled metrics timeline")
    _add_common_run_args(timeline_parser)
    timeline_parser.add_argument("--sample-every", type=int, default=10)
    timeline_parser.add_argument("--output")
    timeline_parser.set_defaults(handler=_handle_timeline)

    render_parser = subparsers.add_parser("render", help="Run a simulation and write an image")
    _add_common_run_args(render_parser)
    render_parser.add_argument("--format", choices=["ascii", "svg", "ppm"], default="svg")
    render_parser.add_argument("--output", required=True)
    render_parser.add_argument("--columns", type=int, default=60)
    render_parser.add_argument("--rows", type=int, default=24)
    render_parser.add_argument("--pixel-width", type=int, default=320)
    render_parser.add_argument("--pixel-height", type=int, default=240)
    render_parser.set_defaults(handler=_handle_render)

    snapshot_parser = subparsers.add_parser("snapshot", help="Save a simulation snapshot as JSON")
    _add_common_run_args(snapshot_parser)
    snapshot_parser.add_argument("--output", required=True)
    snapshot_parser.set_defaults(handler=_handle_snapshot)

    analyze_parser = subparsers.add_parser("analyze", help="Run a simulation and emit advanced analysis metrics")
    _add_common_run_args(analyze_parser)
    analyze_parser.add_argument("--bins", type=int, default=12)
    analyze_parser.add_argument("--output")
    analyze_parser.set_defaults(handler=_handle_analyze)

    resume_parser = subparsers.add_parser("resume", help="Resume a simulation from a snapshot")
    resume_parser.add_argument("snapshot")
    resume_parser.add_argument("--steps", type=int, default=60)
    resume_parser.add_argument("--dt", type=float, default=0.1)
    resume_parser.add_argument("--substeps", type=int, default=1)
    resume_parser.add_argument("--seed", type=int)
    resume_parser.add_argument("--save-snapshot")
    resume_parser.set_defaults(handler=_handle_resume)

    sweep_parser = subparsers.add_parser("sweep", help="Scan seeds and parameters for interesting behaviors")
    _add_common_run_args(sweep_parser)
    sweep_parser.add_argument("--seeds", nargs="+", type=int, default=[1, 2, 3])
    sweep_parser.add_argument("--force-scales", nargs="+", type=float)
    sweep_parser.add_argument("--drags", nargs="+", type=float)
    sweep_parser.add_argument("--bins", type=int, default=12)
    sweep_parser.add_argument("--top", type=int, default=5)
    sweep_parser.add_argument("--output")
    sweep_parser.set_defaults(handler=_handle_sweep)
    return parser


def _add_common_run_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--preset", choices=preset_names(), default="aurora")
    parser.add_argument("--config")
    parser.add_argument("--steps", type=int, default=120)
    parser.add_argument("--dt", type=float, default=0.1)
    parser.add_argument("--substeps", type=int, default=1)
    parser.add_argument("--seed", type=int)


def _simulation_from_args(args: argparse.Namespace) -> ParticleLifeSimulation:
    if args.config:
        LOGGER.info("Loading config from %s", args.config)
        config = SimulationConfig.from_dict(load_mapping(Path(args.config)), seed=args.seed)
    else:
        LOGGER.info("Loading preset %s", args.preset)
        config = SimulationConfig.from_dict(get_preset(args.preset), seed=args.seed)
    return ParticleLifeSimulation(config)


def _print_or_write(payload: Any, output: str | None) -> None:
    if output:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        dump_json(path, payload)
        LOGGER.info("Wrote JSON report to %s", path)
        print(str(path))
        return
    print(json.dumps(payload, indent=2, sort_keys=True))


def _write_timeline(path: Path, timeline: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() == ".csv":
        flattened = [_flatten_mapping(row) for row in timeline]
        dump_csv(path, flattened)
    else:
        dump_json(path, timeline)


def _flatten_mapping(value: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    flat: dict[str, Any] = {}
    for key, item in value.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(item, dict):
            flat.update(_flatten_mapping(item, full_key))
        else:
            flat[full_key] = item
    return flat


def _handle_presets(args: argparse.Namespace) -> int:
    del args
    for name in preset_names():
        print(name)
    return 0


def _handle_export_preset(args: argparse.Namespace) -> int:
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    dump_mapping(output, built_in_presets()[args.name])
    print(str(output))
    return 0


def _handle_run(args: argparse.Namespace) -> int:
    simulation = _simulation_from_args(args)
    simulation.run(args.steps, dt=args.dt, substeps=args.substeps)
    _print_or_write(simulation.metrics(), args.output)
    return 0


def _handle_timeline(args: argparse.Namespace) -> int:
    simulation = _simulation_from_args(args)
    timeline = simulation.timeline(
        args.steps,
        dt=args.dt,
        substeps=args.substeps,
        sample_every=args.sample_every,
    )
    if args.output:
        output = Path(args.output)
        _write_timeline(output, timeline)
        LOGGER.info("Wrote timeline to %s", output)
        print(str(output))
    else:
        print(json.dumps(timeline, indent=2, sort_keys=True))
    return 0


def _handle_render(args: argparse.Namespace) -> int:
    simulation = _simulation_from_args(args)
    simulation.run(args.steps, dt=args.dt, substeps=args.substeps)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    if args.format == "ascii":
        content = render_ascii(
            simulation.particles,
            simulation.config.species_styles,
            simulation.config.width,
            simulation.config.height,
            columns=args.columns,
            rows=args.rows,
        )
    elif args.format == "ppm":
        content = render_ppm(
            simulation.particles,
            simulation.config.species_styles,
            simulation.config.width,
            simulation.config.height,
            pixel_width=args.pixel_width,
            pixel_height=args.pixel_height,
        )
    else:
        content = render_svg(
            simulation.particles,
            simulation.config.species_styles,
            simulation.config.width,
            simulation.config.height,
        )
    output.write_text(content, encoding="utf-8")
    LOGGER.info("Rendered %s frame to %s", args.format, output)
    print(str(output))
    return 0


def _handle_snapshot(args: argparse.Namespace) -> int:
    simulation = _simulation_from_args(args)
    simulation.run(args.steps, dt=args.dt, substeps=args.substeps)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    simulation.save_snapshot(args.output)
    LOGGER.info("Saved snapshot to %s", args.output)
    print(str(args.output))
    return 0


def _handle_analyze(args: argparse.Namespace) -> int:
    simulation = _simulation_from_args(args)
    simulation.run(args.steps, dt=args.dt, substeps=args.substeps)
    summary = summarize_simulation(simulation, bins=args.bins)
    _print_or_write(summary, args.output)
    return 0


def _handle_resume(args: argparse.Namespace) -> int:
    snapshot = load_mapping(args.snapshot)
    simulation = ParticleLifeSimulation.from_snapshot(snapshot)
    if args.seed is not None:
        simulation.config.seed = args.seed
    simulation.run(args.steps, dt=args.dt, substeps=args.substeps)
    if args.save_snapshot:
        output = Path(args.save_snapshot)
        output.parent.mkdir(parents=True, exist_ok=True)
        simulation.save_snapshot(output)
        LOGGER.info("Saved resumed snapshot to %s", output)
    print(json.dumps(simulation.metrics(), indent=2, sort_keys=True))
    return 0


def _handle_sweep(args: argparse.Namespace) -> int:
    simulation = _simulation_from_args(args)
    force_scales = args.force_scales or [simulation.config.force_scale]
    drags = args.drags or [simulation.config.drag]
    results = sweep_parameters(
        simulation.config,
        steps=args.steps,
        dt=args.dt,
        substeps=args.substeps,
        seeds=args.seeds,
        force_scales=force_scales,
        drags=drags,
        bins=args.bins,
    )
    report = {
        "preset": None if args.config else args.preset,
        "config": args.config,
        "tested": len(results),
        "top": results[: max(1, args.top)],
    }
    _print_or_write(report, args.output)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(level=getattr(logging, args.log_level), format="%(levelname)s %(name)s: %(message)s")
    return args.handler(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
