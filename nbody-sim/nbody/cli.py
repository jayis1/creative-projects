"""Command-line interface for nbody-sim.

Examples
--------
Run a two-body orbit for 1000 steps and write the energy log:

    python3 -m nbody.cli --preset two-body --steps 1000 --dt 0.01 \\
        --log energy.csv

Render the figure-eight to a sequence of PPM frames:

    python3 -m nbody.cli --preset figure-eight --steps 500 --snapshot-every 5 \\
        --render frames/ --width 512 --height 512
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from typing import List

from .simulation import Body, Simulation


PRESETS = {
    "two-body": lambda args: Simulation.two_body_orbit(
        dt=args.dt, theta=args.theta, softening=args.softening, G=args.G,
    ),
    "figure-eight": lambda args: Simulation.figure_eight(
        dt=args.dt, theta=args.theta, softening=args.softening, G=args.G,
    ),
    "plummer": lambda args: Simulation.plummer_sphere(
        n=args.n_bodies, seed=args.seed, dt=args.dt, theta=args.theta,
        softening=args.softening, G=args.G,
    ),
    "random": lambda args: Simulation.random_cloud(
        n=args.n_bodies, seed=args.seed, dt=args.dt, theta=args.theta,
        softening=args.softening, G=args.G,
    ),
}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="nbody",
        description="2D Barnes-Hut N-body gravity simulator",
    )
    p.add_argument(
        "--preset",
        choices=sorted(PRESETS.keys()),
        default="two-body",
        help="Initial-condition preset to use",
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
        "--verbose", action="store_true", help="Print per-step progress"
    )
    return p


def main(argv: List[str] = None) -> int:
    args = build_parser().parse_args(argv)
    sim = PRESETS[args.preset](args)
    print(
        f"nbody-sim: preset={args.preset} N={len(sim.bodies)} "
        f"steps={args.steps} dt={args.dt} theta={args.theta} "
        f"softening={args.softening} G={args.G}",
        file=sys.stderr,
    )

    snapshots = []
    if args.snapshot_every > 0:
        def on_step(s: Simulation) -> None:
            if s.step_count % args.snapshot_every == 0:
                snapshots.append(s._snapshot(s.step_count, s.t))
                if args.verbose:
                    e = s.integrator.total_energy(s.bodies)
                    print(f"  step {s.step_count}: E={e:.6f}", file=sys.stderr)
    else:
        on_step = None

    result = sim.run(args.steps, snapshot_every=0, on_step=on_step)
    print(
        f"Initial E={result.initial_energy:.6f}  "
        f"Final E={result.final_energy:.6f}  "
        f"dE/E={abs(result.final_energy - result.initial_energy) / max(abs(result.initial_energy), 1e-12):.6e}",
        file=sys.stderr,
    )
    print(
        f"Initial P={result.initial_momentum}  Final P={result.final_momentum}",
        file=sys.stderr,
    )

    # Energy CSV log.
    if args.log and snapshots:
        with open(args.log, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["step", "t", "energy", "px", "py"])
            for snap in snapshots:
                w.writerow([snap.step, snap.t, snap.energy, *snap.momentum])
        print(f"Wrote energy log to {args.log}", file=sys.stderr)

    # PPM rendering.
    if args.render and snapshots:
        from .renderer import Renderer
        r = Renderer(
            width=args.width,
            height=args.height,
            view_size=args.view_size,
            trails=not args.no_trails,
        )
        paths = r.render_sequence(snapshots, args.render)
        print(f"Wrote {len(paths)} PPM frames to {args.render}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())