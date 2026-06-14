#!/usr/bin/env python3
"""
Reaction-Diffusion Pattern Simulator — Main Entry Point

Simulates Turing patterns using Gray-Scott, FitzHugh-Nagumo,
Gierer-Meinhardt, and Brusselator models with visualization.

Usage:
    # Quick start with a preset
    python3 rd_sim.py --preset coral

    # Custom parameters
    python3 rd_sim.py --model gray-scott --feed 0.035 --kill 0.065 --grid 256

    # Animated GIF output
    python3 rd_sim.py --preset mitosis --gif output.gif --gif-frames 50

    # Grid of snapshots
    python3 rd_sim.py --preset labyrinth --grid-view --grid-rows 4 --grid-cols 4

    # Adaptive time stepping
    python3 rd_sim.py --preset spots --adaptive

    # Statistics output
    python3 rd_sim.py --preset waves --stats

    # Resume from checkpoint
    python3 rd_sim.py --resume checkpoint.npz --steps 2000
"""

import argparse
import sys
import os
import time
import json

# Add project directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import get_model, MODELS
from solver import ReactionDiffusionSolver
from presets import get_preset, list_presets, ALL_PRESETS
from visualization import (save_frame, save_frame_fast, render_frame_grid,
                           save_gif)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Reaction-Diffusion Pattern Simulator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Available presets:
  """ + "\n  ".join(f"{name}: {desc}" for name, desc in list_presets())
    )

    # Model selection
    parser.add_argument("--model", "-m", choices=list(MODELS.keys()),
                        default=None, help="Reaction model to use")
    parser.add_argument("--preset", "-p", default=None,
                        help="Parameter preset name (see list below)")

    # Grid parameters
    parser.add_argument("--grid", "-g", type=int, default=None,
                        help="Grid size NxN (default: 128, or preset-specified)")
    parser.add_argument("--steps", "-s", type=int, default=None,
                        help="Number of simulation steps (default: 5000, or preset-specified)")
    parser.add_argument("--dt", type=float, default=None,
                        help="Time step size (default: model-specific)")

    # Gray-Scott specific
    parser.add_argument("--feed", "-f", type=float, default=None,
                        help="Gray-Scott feed rate (F)")
    parser.add_argument("--kill", "-k", type=float, default=None,
                        help="Gray-Scott kill rate (k)")

    # Integration method
    parser.add_argument("--method", choices=["euler", "rk2"], default="euler",
                        help="Integration method (default: euler)")
    parser.add_argument("--adaptive", action="store_true",
                        help="Use adaptive time stepping")
    parser.add_argument("--no-clamp", action="store_true",
                        help="Disable field clamping (may be unstable)")

    # Boundary conditions
    parser.add_argument("--bc", choices=["periodic", "dirichlet", "neumann"],
                        default="periodic",
                        help="Boundary condition (default: periodic)")

    # Perturbation
    parser.add_argument("--perturbation", choices=[
        "center_square", "ring", "cross", "random", "corner", "multi_spot"
    ], default=None, help="Perturbation type")
    parser.add_argument("--pert-size", type=int, default=20,
                        help="Perturbation size (default: 20)")

    # Visualization
    parser.add_argument("--field", choices=["u", "v", "composite", "difference", "gradient"],
                        default="v",
                        help="Field to visualize (default: v)")
    parser.add_argument("--cmap", default="inferno",
                        help="Matplotlib colormap (default: inferno)")
    parser.add_argument("--output", "-o", default=None,
                        help="Output PNG file path")
    parser.add_argument("--grid-view", action="store_true",
                        help="Show progression as a grid of snapshots")
    parser.add_argument("--grid-rows", type=int, default=3,
                        help="Grid rows for grid view (default: 3)")
    parser.add_argument("--grid-cols", type=int, default=3,
                        help="Grid columns for grid view (default: 3)")

    # Batch frames
    parser.add_argument("--frames-dir", default=None,
                        help="Directory to save frame PNGs")
    parser.add_argument("--every", type=int, default=100,
                        help="Save frame every N steps (default: 100)")

    # GIF output
    parser.add_argument("--gif", default=None,
                        help="Output animated GIF file path")
    parser.add_argument("--gif-frames", type=int, default=60,
                        help="Number of frames for GIF (default: 60)")
    parser.add_argument("--gif-fps", type=int, default=15,
                        help="GIF frames per second (default: 15)")

    # Checkpoint
    parser.add_argument("--checkpoint", default=None,
                        help="Save checkpoint file after simulation")
    parser.add_argument("--resume", default=None,
                        help="Resume from checkpoint file")

    # Statistics
    parser.add_argument("--stats", action="store_true",
                        help="Print simulation statistics at the end")
    parser.add_argument("--stats-file", default=None,
                        help="Save statistics to JSON file")

    # List options
    parser.add_argument("--list-presets", action="store_true",
                        help="List all available presets and exit")
    parser.add_argument("--list-models", action="store_true",
                        help="List all available models and exit")

    return parser.parse_args()


def main():
    args = parse_args()

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

    # ── Determine model and params ──
    model_name = args.model or "gray-scott"
    params = {}
    dt = 1.0
    grid_size = args.grid  # None means user didn't specify
    steps = args.steps     # None means user didn't specify
    pert_config = None

    # Load preset overrides
    if args.preset:
        preset = get_preset(args.preset)
        model_name = preset["model"]
        params.update(preset["params"])
        dt = preset.get("dt", dt)
        # Only use preset grid size if user didn't override via --grid
        if grid_size is None:
            grid_size = preset.get("grid_size", 128)
        # Only use preset steps if user didn't override via --steps
        if steps is None:
            steps = preset.get("steps", 5000)
        pert_config = preset.get("perturbation", None)
    
    # Default grid size if not specified by user or preset
    if grid_size is None:
        grid_size = 128
    # Default steps if not specified by user or preset
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
    if args.perturbation:
        pert_type = args.perturbation
        pert_config = _make_pert_config(pert_type, args.pert_size, grid_size)

    # ── Create solver ──
    if args.resume:
        print(f"Resuming from checkpoint: {args.resume}")
        solver = ReactionDiffusionSolver.load_checkpoint(args.resume)
        print(f"  Model: {solver.model_name}, Grid: {solver.n}x{solver.n}, "
              f"Step: {solver.step_count}")
    else:
        solver = ReactionDiffusionSolver(
            model_name=model_name,
            grid_size=grid_size,
            params=params,
            bc=args.bc,
            dt=dt,
            clamp=not args.no_clamp,
        )
        if pert_config:
            solver.apply_perturbation(pert_config)
        print(f"Model: {solver.model_name}, Grid: {solver.n}x{solver.n}, "
              f"dt={solver.dt}, steps={steps}")
        print(f"Params: {solver.params}")

    # ── Run simulation ──
    if args.gif:
        # Animated GIF mode
        print(f"Generating {args.gif_frames}-frame GIF...")
        t0 = time.time()
        save_gif(solver, steps, frames=args.gif_frames, filepath=args.gif,
                 field=args.field, cmap=args.cmap, fps=args.gif_fps,
                 method=args.method)
        elapsed = time.time() - t0
        print(f"  Completed in {elapsed:.1f}s")

    elif args.frames_dir:
        # Batch mode: save frames periodically
        os.makedirs(args.frames_dir, exist_ok=True)
        every = args.every
        
        # Save initial frame
        frame_path = os.path.join(args.frames_dir, f"frame_{solver.step_count:06d}.png")
        save_frame_fast(solver.u, solver.v, frame_path,
                        field=args.field, cmap=args.cmap)
        print(f"  Saved {frame_path}")

        total_frames = steps // every
        for i in range(1, total_frames + 1):
            solver.step(every, method=args.method)
            frame_path = os.path.join(args.frames_dir, f"frame_{solver.step_count:06d}.png")
            save_frame_fast(solver.u, solver.v, frame_path,
                            field=args.field, cmap=args.cmap)
            if i % 10 == 0 or i == total_frames:
                print(f"  Step {solver.step_count}/{steps} ({i}/{total_frames} frames)")
        
        print(f"Saved {total_frames + 1} frames to {args.frames_dir}")

    elif args.grid_view:
        # Grid snapshot view
        rows, cols = args.grid_rows, args.grid_cols
        fig = render_frame_grid(solver, steps, grid_shape=(rows, cols),
                                field=args.field, cmap=args.cmap,
                                method=args.method)
        out_path = args.output or "grid_output.png"
        os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
        fig.savefig(out_path, dpi=150, bbox_inches="tight")
        print(f"Saved grid view to {out_path}")

    else:
        # Standard mode: run and save final state
        print(f"Running {steps} steps...")
        t0 = time.time()
        if args.adaptive:
            solver.adaptive_step(steps, method=args.method)
        else:
            solver.step(steps, method=args.method)
        elapsed = time.time() - t0
        print(f"  Completed in {elapsed:.2f}s ({steps/elapsed:.0f} steps/s)")

        # Save output
        out_path = args.output or "output.png"
        save_frame(solver.u, solver.v, out_path, field=args.field, cmap=args.cmap)
        print(f"  Saved to {out_path}")

    # ── Statistics ──
    if args.stats or args.stats_file:
        stats = solver.compute_statistics()
        if args.stats:
            print("\nSimulation Statistics:")
            for key, val in stats.items():
                print(f"  {key}: {val:.6f}" if isinstance(val, float) else f"  {key}: {val}")
        if args.stats_file:
            with open(args.stats_file, "w") as f:
                json.dump(stats, f, indent=2)
            print(f"  Statistics saved to {args.stats_file}")

    # ── Checkpoint ──
    if args.checkpoint:
        solver.save_checkpoint(args.checkpoint)
        print(f"Checkpoint saved to {args.checkpoint}")


def _make_pert_config(pert_type, size, grid_size):
    """Build a perturbation config dict from CLI args."""
    if pert_type == "center_square":
        return {"type": "center_square", "size": size, "u_val": 0.0, "v_val": 1.0}
    elif pert_type == "ring":
        return {"type": "ring", "radius": grid_size // 4, "thickness": 3,
                "u_val": 0.5, "v_val": 1.0}
    elif pert_type == "cross":
        return {"type": "cross", "size": size, "u_val": 0.0, "v_val": 1.0}
    elif pert_type == "random":
        return {"type": "random", "noise": 0.02}
    elif pert_type == "corner":
        return {"type": "corner", "size": size, "u_val": 0.0, "v_val": 1.0}
    elif pert_type == "multi_spot":
        return {"type": "multi_spot", "count": 5, "size": size,
                "u_val": 0.0, "v_val": 1.0}
    else:
        return {"type": "center_square", "size": size, "u_val": 0.0, "v_val": 1.0}


if __name__ == "__main__":
    main()