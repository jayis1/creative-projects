"""Command line interface for Particle Life."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .engine import ParticleLifeSimulation, SimulationConfig
from .io import dump_json, load_mapping
from .presets import built_in_presets, get_preset, preset_names
from .render import render_ascii, render_ppm, render_svg


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Particle Life simulator")
    subparsers = parser.add_subparsers(dest="command", required=True)

    presets_parser = subparsers.add_parser("presets", help="List bundled presets")
    presets_parser.set_defaults(handler=_handle_presets)

    export_parser = subparsers.add_parser("export-preset", help="Write a preset to JSON")
    export_parser.add_argument("name", choices=preset_names())
    export_parser.add_argument("--output", required=True)
    export_parser.set_defaults(handler=_handle_export_preset)

    run_parser = subparsers.add_parser("run", help="Run a simulation and print metrics")
    _add_common_run_args(run_parser)
    run_parser.set_defaults(handler=_handle_run)

    timeline_parser = subparsers.add_parser("timeline", help="Run and emit a sampled metrics timeline")
    _add_common_run_args(timeline_parser)
    timeline_parser.add_argument("--sample-every", type=int, default=10)
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
        config = SimulationConfig.from_dict(load_mapping(Path(args.config)), seed=args.seed)
    else:
        config = SimulationConfig.from_dict(get_preset(args.preset), seed=args.seed)
    return ParticleLifeSimulation(config)


def _handle_presets(args: argparse.Namespace) -> int:
    del args
    for name in preset_names():
        print(name)
    return 0


def _handle_export_preset(args: argparse.Namespace) -> int:
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    dump_json(args.output, built_in_presets()[args.name])
    print(str(args.output))
    return 0


def _handle_run(args: argparse.Namespace) -> int:
    simulation = _simulation_from_args(args)
    simulation.run(args.steps, dt=args.dt, substeps=args.substeps)
    print(json.dumps(simulation.metrics(), indent=2, sort_keys=True))
    return 0


def _handle_timeline(args: argparse.Namespace) -> int:
    simulation = _simulation_from_args(args)
    timeline = simulation.timeline(
        args.steps,
        dt=args.dt,
        substeps=args.substeps,
        sample_every=args.sample_every,
    )
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
    output.write_text(content)
    print(str(output))
    return 0


def _handle_snapshot(args: argparse.Namespace) -> int:
    simulation = _simulation_from_args(args)
    simulation.run(args.steps, dt=args.dt, substeps=args.substeps)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    simulation.save_snapshot(args.output)
    print(str(args.output))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
