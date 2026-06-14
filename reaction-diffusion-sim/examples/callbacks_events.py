#!/usr/bin/env python3
"""
Callback and Event System Example — Monitor simulation progress.

Demonstrates:
1. Adding step callbacks
2. Using the event system
3. Collecting data during simulation
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from rdsim import ReactionDiffusionSolver
from rdsim.solver import SimulationEvent

def main():
    solver = ReactionDiffusionSolver("gray-scott", grid_size=64)

    # Track v_std over time using a callback
    history = {"step": [], "v_std": [], "u_mean": []}

    def track_stats(solver):
        stats = solver.compute_statistics()
        history["step"].append(stats["step_count"])
        history["v_std"].append(stats["v_std"])
        history["u_mean"].append(stats["u_mean"])

    solver.add_callback(track_stats, every=100)

    # Use event system to log when perturbation is applied
    def on_perturbation(solver, **kwargs):
        print(f"  [EVENT] Perturbation applied: {kwargs.get('pert_type', 'unknown')}")

    solver.on(SimulationEvent.PERTURBATION_APPLIED, on_perturbation)

    # Apply perturbation (triggers event)
    solver.apply_perturbation()

    print("Running simulation with callbacks...")
    solver.step(2000)

    # Report history
    print(f"\nCollected {len(history['step'])} data points")
    print(f"  v_std range: {min(history['v_std']):.6f} → {max(history['v_std']):.6f}")
    print(f"  u_mean range: {min(history['u_mean']):.6f} → {max(history['u_mean']):.6f}")

    # Find when pattern first emerged (v_std exceeds threshold)
    for step, v_std in zip(history["step"], history["v_std"]):
        if v_std > 0.01:
            print(f"  Pattern emergence detected at step {step} (v_std={v_std:.6f})")
            break

if __name__ == "__main__":
    main()