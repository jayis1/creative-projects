"""Command-line interface for nbody-sim.

Supports:
- Preset initial conditions (two-body, figure-eight, plummer, random,
  solar-system, binary, kuzmin-disk)
- Config files (YAML/JSON/TOML) via ``--config``
- Integrator selection (leapfrog, rk4, forest-ruth)
- Adaptive timestep, COM recentering
- PPM rendering, CSV energy logging, JSON serialization
- Benchmarking Barnes–Hut vs brute force
- Structured logging

Examples
--------
Run a two-body orbit for 1000 steps::

    python3 -m nbody --preset two-body --steps 1000 --dt 0.01 --log energy.csv

Run from a config file::

    python3 -m nbody --config sim.yaml

Use the Forest–Ruth 4th-order symplectic integrator::

    python3 -m nbody --preset figure-eight --integrator forest-ruth --steps 5000
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from typing import Any, List, Optional

from .config import SimConfig, load_config
from .logging_utils import get_logger
from .simulation import Simulation


PRESETS = {
    "two-body": lambda args: Simulation.two_body_orbit(
        dt=args.dt, theta=args.theta, softening=args.softening, G=args.G,
        integrator=args.integrator,
        recenter_com=args.recenter_com, adaptive_dt=args.adaptive_dt,
        adaptive_eta=args.adaptive_eta,
    ),
    "figure-eight": lambda args: Simulation.figure_eight(
        dt=args.dt, theta=args.theta, softening=args.softening, G=args.G,
        integrator=args.integrator,
        recenter_com=args.recenter_com, adaptive_dt=args.adaptive_dt,
        adaptive_eta=args.adaptive_eta,
    ),
    "plummer": lambda args: Simulation.plummer_sphere(
        n=args.n_bodies, seed=args.seed, dt=args.dt, theta=args.theta,
        softening=args.softening, G=args.G,
        integrator=args.integrator,
        recenter_com=args.recenter_com, adaptive_dt=args.adaptive_dt,
        adaptive_eta=args.adaptive_eta,
    ),
    "random": lambda args: Simulation.random_cloud(
        n=args.n_bodies, seed=args.seed, dt=args.dt, theta=args.theta,
        softening=args.softening, G=args.G,
        integrator=args.integrator,
        recenter_com=args.recenter_com, adaptive_dt=args.adaptive_dt,
        adaptive_eta=args.adaptive_eta,
    ),
    "solar-system": lambda args: Simulation.solar_system(
        seed=args.seed, dt=args.dt, theta=args.theta,
        softening=args.softening, G=args.G,
        integrator=args.integrator,
        recenter_com=args.recenter_com, adaptive_dt=args.adaptive_dt,
        adaptive_eta=args.adaptive_eta,
    ),
    "binary": lambda args: Simulation.binary_system(
        dt=args.dt, theta=args.theta, softening=args.softening, G=args.G,
        integrator=args.integrator,
        recenter_com=args.recenter_com, adaptive_dt=args.adaptive_dt,
        adaptive_eta=args.adaptive_eta,
    ),
    "kuzmin-disk": lambda args: Simulation.kuzmin_disk(
        n=args.n_bodies, seed=args.seed, dt=args.dt, theta=args.theta,
        softening=args.softening, G=args.G,
        integrator=args.integrator,
        recenter_com=args.recenter_com, adaptive_dt=args.adaptive_dt,
        adaptive_eta=args.adaptive_eta,
    ),
}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="nbody",
        description=(
            "2D Barnes-Hut N-body gravity simulator v3.0. "
            "Supports multiple integrators, config files, adaptive timestep, "
            "PPM rendering, and more."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  nbody --preset two-body --steps 1000 --log energy.csv\n"
            "  nbody --preset figure-eight --integrator forest-ruth --steps 5000\n"
            "  nbody --config sim.yaml\n"
            "  nbody --preset plummer --n-bodies 200 --render frames/ --color-by-mass\n"
        ),
    )
    p.add_argument(
        "--config", type=str, default="",
        help="Load configuration from a YAML/JSON/TOML file (overrides CLI defaults)",
    )
    p.add_argument(
        "--preset",
        choices=sorted(PRESETS.keys()),
        default="two-body",
        help="Initial-condition preset to use (default: two-body)",
    )
    p.add_argument("--steps", type=int, default=1000, help="Number of steps")
    p.add_argument("--dt", type=float, default=0.01, help="Time step")
    p.add_argument(
        "--theta", type=float, default=0.5, help="Barnes-Hut opening angle"
    )
    p.add_argument(
        "--softening", type=float, default=1.0, help="Plummer softening length"
    )
    p.add_argument("--G", type=float, default=1.0, help="Gravitational constant")
    p.add_argument(
        "--integrator",
        choices=["leapfrog", "rk4", "forest-ruth"],
        default="leapfrog",
        help="Integrator scheme (default: leapfrog)",
    )
    p.add_argument("--n-bodies", type=int, default=100, help="N for presets")
    p.add_argument("--seed", type=int, default=0, help="RNG seed")
    p.add_argument(
        "--snapshot-every",
        type=int,
        default=0,
        help="Record a snapshot every N steps (0 = off)",
    )
    p.add_argument(
        "--log",
        type=str,
        default="",
        help="Write per-snapshot energy/momentum CSV to this path",
    )
    p.add_argument(
        "--render",
        type=str,
        default="",
        help="Render snapshots to PPM frames in this directory",
    )
    p.add_argument(
        "--width", type=int, default=512, help="Render width in pixels"
    )
    p.add_argument(
        "--height", type=int, default=512, help="Render height in pixels"
    )
    p.add_argument(
        "--view-size", type=float, default=15.0,
        help="Half-width of world region rendered",
    )
    p.add_argument(
        "--no-trails", action="store_true", help="Disable motion trails"
    )
    p.add_argument(
        "--color-by-mass", action="store_true",
        help="Color bodies by mass (blue=light, orange=heavy)",
    )
    p.add_argument(
        "--color-by-speed", action="store_true",
        help="Color bodies by speed (red=slow, yellow=fast)",
    )
    p.add_argument(
        "--recenter-com", action="store_true",
        help="Recenter to COM frame (zero total momentum) at start",
    )
    p.add_argument(
        "--adaptive-dt", action="store_true",
        help="Use adaptive timestep based on max acceleration",
    )
    p.add_argument(
        "--adaptive-eta", type=float, default=0.02,
        help="Adaptive timestep safety factor (smaller = more accurate)",
    )
    p.add_argument(
        "--benchmark", action="store_true",
        help="Compare Barnes-Hut vs brute-force accuracy and speed, then exit",
    )
    p.add_argument(
        "--save-json", type=str, default="",
        help="Save snapshots + result to a JSON file",
    )
    p.add_argument(
        "--verbose", action="store_true", help="Print per-step progress"
    )
    p.add_argument(
        "--quiet", action="store_true", help="Suppress info output"
    )
    p.add_argument(
        "--save-config", type=str, default="",
        help="Save the current CLI configuration to a file and exit",
    )
    return p


def _apply_config(args: argparse.Namespace, cfg: SimConfig) -> argparse.Namespace:
    """Overlay config-file values onto argparse args (CLI flags take precedence)."""
    # Only override if the user didn't explicitly set the CLI flag.
    # We use 'default' comparison: if the value is still the default,
    # the config value is used.
    if cfg.preset != "two-body" and args.preset == "two-body":
        args.preset = cfg.preset
    if cfg.steps != 1000 and args.steps == 1000:
        args.steps = cfg.steps
    if cfg.dt != 0.01 and args.dt == 0.01:
        args.dt = cfg.dt
    if cfg.theta != 0.5 and args.theta == 0.5:
        args.theta = cfg.theta
    if cfg.softening != 1.0 and args.softening == 1.0:
        args.softening = cfg.softening
    if cfg.G != 1.0 and args.G == 1.0:
        args.G = cfg.G
    if cfg.n_bodies != 100 and args.n_bodies == 100:
        args.n_bodies = cfg.n_bodies
    if cfg.seed != 0 and args.seed == 0:
        args.seed = cfg.seed
    if cfg.snapshot_every != 0 and args.snapshot_every == 0:
        args.snapshot_every = cfg.snapshot_every
    if cfg.recenter_com:
        args.recenter_com = True
    if cfg.adaptive_dt:
        args.adaptive_dt = True
    if cfg.adaptive_eta != 0.02 and args.adaptive_eta == 0.02:
        args.adaptive_eta = cfg.adaptive_eta
    if cfg.benchmark:
        args.benchmark = True
    if cfg.render.enabled and not args.render:
        args.render = cfg.render.out_dir
    if cfg.render.width != 512 and args.width == 512:
        args.width = cfg.render.width
    if cfg.render.height != 512 and args.height == 512:
        args.height = cfg.render.height
    if cfg.render.view_size != 15.0 and args.view_size == 15.0:
        args.view_size = cfg.render.view_size
    if cfg.render.color_by_mass:
        args.color_by_mass = True
    if cfg.render.color_by_speed:
        args.color_by_speed = True
    if cfg.output.log_csv and not args.log:
        args.log = cfg.output.log_csv
    if cfg.output.save_json and not args.save_json:
        args.save_json = cfg.output.save_json
    if cfg.output.verbose:
        args.verbose = True
    return args


def main(argv: Optional[List[str]] = None) -> int:
    log = get_logger("nbody.cli")
    args = build_parser().parse_args(argv)

    # Load config file if specified.
    if args.config:
        try:
            cfg = load_config(args.config)
            args = _apply_config(args, cfg)
            log.info(f"Loaded config from {args.config}")
        except Exception as e:
            log.error(f"Failed to load config: {e}")
            return 1

    # Save config and exit.
    if args.save_config:
        from .config import SimConfig, RenderConfig, OutputConfig
        cfg = SimConfig(
            preset=args.preset,
            n_bodies=args.n_bodies,
            seed=args.seed,
            dt=args.dt,
            theta=args.theta,
            softening=args.softening,
            G=args.G,
            steps=args.steps,
            recenter_com=args.recenter_com,
            adaptive_dt=args.adaptive_dt,
            adaptive_eta=args.adaptive_eta,
            snapshot_every=args.snapshot_every,
            benchmark=args.benchmark,
            render=RenderConfig(
                enabled=bool(args.render),
                width=args.width,
                height=args.height,
                view_size=args.view_size,
                trails=not args.no_trails,
                color_by_mass=args.color_by_mass,
                color_by_speed=args.color_by_speed,
                out_dir=args.render or "frames",
            ),
            output=OutputConfig(
                log_csv=args.log,
                save_json=args.save_json,
                verbose=args.verbose,
            ),
        )
        from .config import save_config
        save_config(cfg, args.save_config)
        print(f"Saved config to {args.save_config}", file=sys.stderr)
        return 0

    # Create simulation from preset.
    if args.preset not in PRESETS:
        log.error(f"Unknown preset '{args.preset}'")
        return 1
    sim = PRESETS[args.preset](args)

    if not args.quiet:
        log.info(
            f"preset={args.preset} N={len(sim.bodies)} steps={args.steps} "
            f"dt={args.dt} theta={args.theta} softening={args.softening} "
            f"G={args.G} integrator={args.integrator}"
        )

    # Benchmark mode.
    if args.benchmark:
        from .brute_force import benchmark
        res = benchmark(sim.bodies, theta=args.theta, G=args.G,
                        softening=args.softening)
        print(f"Benchmark (N={res['n']}, theta={res['theta']}):")
        print(f"  Barnes-Hut time : {res['bh_time']*1000:.2f} ms")
        print(f"  Brute force time: {res['bf_time']*1000:.2f} ms")
        print(f"  Speedup         : {res['speedup']:.2f}x")
        print(f"  Max rel error   : {res['max_rel_err']:.6e}")
        print(f"  Mean rel error  : {res['mean_rel_err']:.6e}")
        return 0

    # Setup verbose callback.
    verbose_cb = None
    if args.verbose:
        def verbose_cb(s: Simulation) -> None:
            if s.step_count % max(args.snapshot_every, 1) == 0:
                e = s.integrator.total_energy(s.bodies)
                log.info(f"step {s.step_count}: E={e:.6f}")

    # Run simulation.
    result = sim.run(args.steps, snapshot_every=args.snapshot_every,
                     on_step=verbose_cb)
    snapshots = result.snapshots

    if not args.quiet:
        log.info(
            f"Initial E={result.initial_energy:.6f}  "
            f"Final E={result.final_energy:.6f}  "
            f"dE/E={abs(result.final_energy - result.initial_energy) / max(abs(result.initial_energy), 1e-12):.6e}"
        )
        log.info(
            f"Initial P={result.initial_momentum}  Final P={result.final_momentum}"
        )

    # Energy CSV log.
    if args.log and snapshots:
        with open(args.log, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["step", "t", "energy", "px", "py"])
            for snap in snapshots:
                w.writerow([snap.step, snap.t, snap.energy, *snap.momentum])
        log.info(f"Wrote energy log to {args.log}")

    # PPM rendering.
    if args.render and snapshots:
        from .renderer import Renderer
        r = Renderer(
            width=args.width,
            height=args.height,
            view_size=args.view_size,
            trails=not args.no_trails,
            color_by_mass=args.color_by_mass,
            color_by_speed=args.color_by_speed,
        )
        paths = r.render_sequence(snapshots, args.render)
        log.info(f"Wrote {len(paths)} PPM frames to {args.render}")

    # JSON serialization.
    if args.save_json:
        from .serialize import save_result
        result.snapshots = snapshots
        save_result(result, sim, args.save_json)
        log.info(f"Saved run to {args.save_json}")

    return 0


if __name__ == "__main__":
    sys.exit(main())