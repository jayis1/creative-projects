#!/usr/bin/env python3
"""
Parameter Sweep Example — Explore how F affects pattern diversity.

Demonstrates:
1. Using the parameter_sweep utility
2. Comparing patterns across parameter values
3. Collecting statistics for analysis
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from rdsim import ReactionDiffusionSolver, save_frame_fast

def main():
    # Sweep F parameter from 0.02 to 0.06
    F_values = np.linspace(0.02, 0.06, 9)
    grid_size = 64
    steps = 3000

    print(f"Parameter sweep: F from {F_values[0]:.3f} to {F_values[-1]:.3f}")
    print(f"Grid: {grid_size}x{grid_size}, Steps: {steps}")
    print("-" * 50)

    results = {}
    for F in F_values:
        solver = ReactionDiffusionSolver(
            "gray-scott", grid_size=grid_size,
            params={"F": round(F, 4), "k": 0.062, "Du": 0.16, "Dv": 0.08},
        )
        solver.apply_perturbation({
            "type": "center_square", "size": 15, "u_val": 0.0, "v_val": 1.0,
        })
        solver.step(steps)

        stats = solver.compute_statistics()
        results[F] = stats["v_std"]

        # Save each frame
        out = f"sweep_F_{F:.4f}.png"
        save_frame_fast(solver.u, solver.v, out, field="v", cmap="inferno")
        print(f"  F={F:.4f}: v_std={stats['v_std']:.6f} → {out}")

    print("-" * 50)
    # Find the most interesting F (highest v_std)
    best_F = max(results, key=results.get)
    print(f"Most pattern diversity at F={best_F:.4f} (v_std={results[best_F]:.6f})")

if __name__ == "__main__":
    main()