#!/usr/bin/env python3
"""
Reaction-Diffusion Pattern Simulator — Main Entry Point

Simulates Turing patterns using Gray-Scott, FitzHugh-Nagumo,
Gierer-Meinhardt, Brusselator, and Schnakenberg models with visualization.

Usage:
    # Quick start with a preset
    python3 -m rdsim --preset coral

    # Custom parameters
    python3 -m rdsim --model gray-scott --feed 0.035 --kill 0.065 --grid 256

    # Animated GIF output
    python3 -m rdsim --preset mitosis --gif output.gif --gif-frames 50

    # Grid of snapshots
    python3 -m rdsim --preset labyrinth --grid-view --grid-rows 4 --grid-cols 4

    # Adaptive time stepping with RK4
    python3 -m rdsim --preset spots --adaptive --method rk4

    # From config file
    python3 -m rdsim --config simulation.yaml

    # Parameter sweep
    python3 -m rdsim --model gray-scott --sweep F --sweep-range 0.02,0.06 --sweep-steps 10
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from typing import Any, Dict, Optional

from rdsim.models import get_model, MODELS
from rdsim.solver import ReactionDiffusionSolver
from rdsim.presets import get_preset, list_presets, ALL_PRESETS
from rdsim.visualization import (
    save_frame, save_frame_fast, render_frame_grid, save_gif, save_video,
)
from rdsim.config import load_config, SimulationConfig


def setup_logging(level: str = "INFO") -> None:
    """Configure logging for the application."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="rdsim",
        description="Reaction-Diffusion Pattern Simulator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Available presets:
  """ + "\n  ".join(f"{name}: {desc}" for name, desc in list_presets()),
    )

    # Config file
    parser.add_argument(
        "--config", "-c", default=None,
        help="Load configuration from YAML/TOML/JSON file",
    )

    # Model selection
    parser.add_argument(
        "--model", "-m", choices=list(MODELS.keys()),
        default=None, help="Reaction model to use",
    )
    parser.add_argument(
        "--preset", "-p", default=None,
        help="Parameter preset name (see list below)",
    )

    # Grid parameters
    parser.add_argument(
        "--grid", "-g", type=int, default=None,
        help="Grid size NxN (default: 128, or preset-specified)",
    )
    parser.add_argument(
        "--steps", "-s", type=int, default=None,
        help="Number of simulation steps (default: 5000, or preset-specified)",
    )
    parser.add_argument(
        "--dt", type=float, default=None,
        help="Time step size (default: model-specific)",
    )

    # Gray-Scott specific
    parser.add_argument(
        "--feed", "-f", type=float, default=None,
        help="Gray-Scott feed rate (F)",
    )
    parser.add_argument(
        "--kill", "-k", type=float, default=None,
        help="Gray-Scott kill rate (k)",
    )

    # Integration method
    parser.add_argument(
        "--method", choices=["euler", "rk2", "rk4"], default="euler",
        help="Integration method (default: euler)",
    )
    parser.add_argument(
        "--adaptive", action="store_true",
        help="Use adaptive time stepping",
    )
    parser.add_argument(
        "--no-clamp", action="store_true",
        help="Disable field clamping (may be unstable)",
    )

    # Boundary conditions
    parser.add_argument(
        "--bc", choices=["periodic", "dirichlet", "neumann"],
        default="periodic",
        help="Boundary condition (default: periodic)",
    )

    # Perturbation
    parser.add_argument(
        "--perturbation", choices=[
            "center_square", "ring", "cross", "random", "corner", "multi_spot",
        ],
        default=None, help="Perturbation type",
    )
    parser.add_argument(
        "--pert-size", type=int, default=20,
        help="Perturbation size (default: 20)",
    )

    # Visualization
    parser.add_argument(
        "--field", choices=["u", "v", "composite", "difference", "gradient"],
        default="v", help="Field to visualize (default: v)",
    )
    parser.add_argument(
        "--cmap", default="inferno",
        help="Matplotlib colormap (default: inferno)",
    )
    parser.add_argument(
        "--output", "-o", default=None,
        help="Output PNG file path",
    )
    parser.add_argument(
        "--grid-view", action="store_true",
        help="Show progression as a grid of snapshots",
    )
    parser.add_argument(
        "--grid-rows", type=int, default=3,
        help="Grid rows for grid view (default: 3)",
    )
    parser.add_argument(
        "--grid-cols", type=int, default=3,
        help="Grid columns for grid view (default: 3)",
    )

    # Batch frames
    parser.add_argument(
        "--frames-dir", default=None,
        help="Directory to save frame PNGs",
    )
    parser.add_argument(
        "--every", type=int, default=100,
        help="Save frame every N steps (default: 100)",
    )

    # GIF output
    parser.add_argument(
        "--gif", default=None,
        help="Output animated GIF file path",
    )
    parser.add_argument(
        "--gif-frames", type=int, default=60,
        help="Number of frames for GIF (default: 60)",
    )
    parser.add_argument(
        "--gif-fps", type=int, default=15,
        help="GIF frames per second (default: 15)",
    )

    # Video output
    parser.add_argument(
        "--video", default=None,
        help="Output video file path (MP4/WebM)",
    )
    parser.add_argument(
        "--video-fps", type=int, default=30,
        help="Video frames per second (default: 30)",
    )

    # Checkpoint
    parser.add_argument(
        "--checkpoint", default=None,
        help="Save checkpoint file after simulation",
    )
    parser.add_argument(
        "--resume", default=None,
        help="Resume from checkpoint file",
    )

    # Statistics
    parser.add_argument(
        "--stats", action="store_true",
        help="Print simulation statistics at the end",
    )
    parser.add_argument(
        "--stats-file", default=None,
        help="Save statistics to JSON file",
    )

    # Parameter sweep
    parser.add_argument(
        "--sweep", default=None,
        help="Parameter name to sweep",
    )
    parser.add_argument(
        "--sweep-range", default=None,
        help="Sweep range as 'start,end' (e.g., '0.02,0.06')",
    )
    parser.add_argument(
        "--sweep-steps", type=int, default=10,
        help="Number of sweep steps (default: 10)",
    )
    parser.add_argument(
        "--sweep-output", default="sweep_results.json",
        help="Output file for sweep results (default: sweep_results.json)",
    )

    # List options
    parser.add_argument(
        "--list-presets", action="store_true",
        help="List all available presets and exit",
    )
    parser.add_argument(
        "--list-models", action="store_true",
        help="List all available models and exit",
    )

    # Logging
    parser.add_argument(
        "--log-level", default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)",
    )

    # Seed
    parser.add_argument(
        "--seed", type=int, default=None,
        help="Random seed for reproducibility",
    )

    return parser.parse_args()


def _make_pert_config(pert_type: str, size: int, grid_size: int) -> Dict[str, Any]:
    """Build a perturbation config dict from CLI args."""
    configs = {
        "center_square": {"type": "center_square", "size": size, "u_val": 0.0, "v_val": 1.0},
        "ring": {"type": "ring", "radius": grid_size // 4, "thickness": 3, "u_val": 0.5, "v_val": 1.0},
        "cross": {"type": "cross", "size": size, "u_val": 0.0, "v_val": 1.0},
        "random": {"type": "random", "noise": 0.02},
        "corner": {"type": "corner", "size": size, "u_val": 0.0, "v_val": 1.0},
        "multi_spot": {"type": "multi_spot", "count": 5, "size": size, "u_val": 0.0, "v_val": 1.0},
    }
    return configs.get(pert_type, configs["center_square"])


def main() -> None:
    args = parse_args()
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)

    # ── List and exit ──
    if args.list_presets:
        print("Available presets:")
        for name, desc in list_presets():
            print(f"  {name:20s} {desc}")
        return

    if args.list_models:
        print("Available models:")
        for name, config in MODELS.items():
            print(f"  {name:20s} {config['description']}")
        return

    # ── Load from config file if specified ──
    if args.config:
        logger.info(f"Loading configuration from {args.config}")
        config = load_config(args.config)
        # CLI args override config file
        model_name = args.model or config.model
        params = dict(config.params)
        grid_size = args.grid if args.grid is not None else config.grid_size
        steps = args.steps if args.steps is not None else config.steps
        dt = args.dt if args.dt is not None else config.dt
        bc = args.bc if args.bc != "periodic" else config.bc
        method = args.method if args.method != "euler" else config.method
    else:
        # ── Determine model and params from CLI ──
        model_name = args.model or "gray-scott"
        params: Dict[str, float] = {}
        dt = 1.0
        grid_size = args.grid
        steps = args.steps
        pert_config = None
        bc = args.bc
        method = args.method

        if args.preset:
            preset = get_preset(args.preset)
            model_name = preset["model"]
            params.update(preset["params"])
            dt = preset.get("dt", dt)
            if grid_size is None:
                grid_size = preset.get("grid_size", 128)
            if steps is None:
                steps = preset.get("steps", 5000)
            pert_config = preset.get("perturbation", None)

        if grid_size is None:
            grid_size = 128
        if steps is None:
            steps = 5000

        # CLI overrides (take precedence over preset)
        if args.feed is not None:
            params["F"] = args.feed
        if args.kill is not None:
            params["k"] = args.kill
        if args.dt is not None:
            dt = args.dt

    # Perturbation override
    pert_config = None
    if args.perturbation:
        pert_config = _make_pert_config(args.perturbation, args.pert_size, grid_size)

    # ── Seed ──
    if args.seed is not None:
        import numpy as np
        np.random.seed(args.seed)
        logger.info(f"Random seed set to {args.seed}")

    # ── Parameter sweep mode ──
    if args.sweep:
        if not args.sweep_range:
            logger.error("--sweep-range is required with --sweep")
            sys.exit(1)
        start, end = map(float, args.sweep_range.split(","))
        values = [start + i * (end - start) / (args.sweep_steps - 1)
                  for i in range(args.sweep_steps)]
        logger.info(f"Running parameter sweep: {args.sweep} from {start} to {end}")
        results = ReactionDiffusionSolver.parameter_sweep(
            model_name=model_name,
            param_name=args.sweep,
            values=values,
            grid_size=grid_size,
            steps=steps,
            method=method,
        )
        with open(args.sweep_output, "w") as f:
            json.dump(
                {"parameter": args.sweep, "results": {str(k): v for k, v in results.items()}},
                f, indent=2,
            )
        print(f"Parameter sweep results saved to {args.sweep_output}")
        for val, metric in results.items():
            print(f"  {args.sweep}={val}: {metric:.6f}")
        return

    # ── Create solver ──
    if args.resume:
        logger.info(f"Resuming from checkpoint: {args.resume}")
        solver = ReactionDiffusionSolver.load_checkpoint(args.resume)
        logger.info(
            f"  Model: {solver.model_name}, Grid: {solver.n}x{solver.n}, "
            f"Step: {solver.step_count}"
        )
    else:
        solver = ReactionDiffusionSolver(
            model_name=model_name,
            grid_size=grid_size,
            params=params,
            bc=bc,
            dt=dt,
            clamp=not args.no_clamp,
        )
        if pert_config:
            solver.apply_perturbation(pert_config)
        else:
            solver.apply_perturbation()
        logger.info(
            f"Model: {solver.model_name}, Grid: {solver.n}x{solver.n}, "
            f"dt={solver.dt}, steps={steps}"
        )
        logger.info(f"Params: {solver.params}")

    # ── Run simulation ──
    if args.gif:
        print(f"Generating {args.gif_frames}-frame GIF...")
        t0 = time.time()
        save_gif(
            solver, steps, frames=args.gif_frames, filepath=args.gif,
            field=args.field, cmap=args.cmap, fps=args.gif_fps,
            method=method,
        )
        elapsed = time.time() - t0
        print(f"  Completed in {elapsed:.1f}s")

    elif args.video:
        print(f"Generating video...")
        t0 = time.time()
        save_video(
            solver, steps, filepath=args.video,
            field=args.field, cmap=args.cmap, fps=args.video_fps,
            method=method,
        )
        elapsed = time.time() - t0
        print(f"  Completed in {elapsed:.1f}s")

    elif args.frames_dir:
        os.makedirs(args.frames_dir, exist_ok=True)
        every = args.every
        frame_path = os.path.join(
            args.frames_dir, f"frame_{solver.step_count:06d}.png"
        )
        save_frame_fast(solver.u, solver.v, frame_path,
                        field=args.field, cmap=args.cmap)
        print(f"  Saved {frame_path}")

        total_frames = steps // every
        for i in range(1, total_frames + 1):
            solver.step(every, method=method)
            frame_path = os.path.join(
                args.frames_dir, f"frame_{solver.step_count:06d}.png"
            )
            save_frame_fast(solver.u, solver.v, frame_path,
                            field=args.field, cmap=args.cmap)
            if i % 10 == 0 or i == total_frames:
                print(f"  Step {solver.step_count}/{steps} ({i}/{total_frames} frames)")

        print(f"Saved {total_frames + 1} frames to {args.frames_dir}")

    elif args.grid_view:
        rows, cols = args.grid_rows, args.grid_cols
        fig = render_frame_grid(
            solver, steps, grid_shape=(rows, cols),
            field=args.field, cmap=args.cmap, method=method,
        )
        out_path = args.output or "grid_output.png"
        os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
        fig.savefig(out_path, dpi=150, bbox_inches="tight")
        print(f"Saved grid view to {out_path}")

    else:
        print(f"Running {steps} steps with {method}...")
        t0 = time.time()
        if args.adaptive:
            solver.adaptive_step(steps, method=method)
        else:
            solver.step(steps, method=method)
        elapsed = time.time() - t0
        print(f"  Completed in {elapsed:.2f}s ({steps / elapsed:.0f} steps/s)")

        out_path = args.output or "output.png"
        save_frame(solver.u, solver.v, out_path, field=args.field, cmap=args.cmap)
        print(f"  Saved to {out_path}")

    # ── Statistics ──
    if args.stats or args.stats_file:
        stats = solver.compute_statistics()
        if args.stats:
            print("\nSimulation Statistics:")
            for key, val in stats.items():
                if isinstance(val, float):
                    print(f"  {key}: {val:.6f}")
                else:
                    print(f"  {key}: {val}")
        if args.stats_file:
            with open(args.stats_file, "w") as f:
                json.dump(stats, f, indent=2)
            print(f"  Statistics saved to {args.stats_file}")

    # ── Checkpoint ──
    if args.checkpoint:
        solver.save_checkpoint(args.checkpoint)
        print(f"Checkpoint saved to {args.checkpoint}")


if __name__ == "__main__":
    main()