#!/usr/bin/env python3
"""
Quick Start Example — Gray-Scott coral pattern.

Demonstrates the basic workflow:
1. Create a solver
2. Apply a perturbation
3. Run the simulation
4. Save the result
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rdsim import ReactionDiffusionSolver, save_frame

def main():
    # Create solver with Gray-Scott model
    solver = ReactionDiffusionSolver("gray-scott", grid_size=128)

    # Apply a center perturbation to break symmetry
    solver.apply_perturbation({
        "type": "center_square",
        "size": 20,
        "u_val": 0.0,
        "v_val": 1.0,
    })

    print(f"Running 8000 steps...")
    solver.step(8000)

    # Save the result
    save_frame(solver.u, solver.v, "coral_output.png", field="v", cmap="inferno")
    print(f"Saved to coral_output.png")

    # Print statistics
    stats = solver.compute_statistics()
    print(f"Statistics: u_mean={stats['u_mean']:.4f}, v_mean={stats['v_mean']:.4f}")

if __name__ == "__main__":
    main()