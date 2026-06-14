#!/usr/bin/env python3
"""
Custom Model Registration Example — Add your own reaction kinetics.

Demonstrates:
1. Defining custom reaction kinetics
2. Registering with the model registry
3. Running a simulation with the custom model
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from rdsim import ReactionDiffusionSolver, register_model, save_frame_fast
from rdsim.models import MODELS

def main():
    # Define a simple activator-inhibitor model:
    # du/dt = Du*Lap(u) + alpha*u - beta*u*v
    # dv/dt = Dv*Lap(v) + gamma*u*v - delta*v
    # This is a Lotka-Volterra-like reaction-diffusion system

    def lotka_volterra_react(u, v, params):
        alpha = params.get("alpha", 1.0)
        beta = params.get("beta", 0.5)
        gamma = params.get("gamma", 0.5)
        delta = params.get("delta", 0.3)
        du = alpha * u - beta * u * v
        dv = gamma * u * v - delta * v
        return du, dv

    def lotka_volterra_default_state(n, params=None):
        rng = np.random.default_rng(42)
        u = np.ones((n, n)) * 1.0 + rng.normal(0, 0.05, (n, n))
        v = np.ones((n, n)) * 2.0 + rng.normal(0, 0.05, (n, n))
        return np.clip(u, 0, None), np.clip(v, 0, None)

    # Register the custom model
    register_model(
        name="lotka-volterra",
        react_fn=lotka_volterra_react,
        defaults={"Du": 0.02, "Dv": 0.04, "alpha": 1.0, "beta": 0.5,
                  "gamma": 0.5, "delta": 0.3},
        default_state_fn=lotka_volterra_default_state,
        perturbation_fn=lambda: {"type": "random", "noise": 0.05},
        param_names=["Du", "Dv", "alpha", "beta", "gamma", "delta"],
        description="Lotka-Volterra reaction-diffusion (predator-prey)",
        stability_clamp=(0, None),
    )

    print(f"Custom model registered. Available models: {list(MODELS.keys())}")

    # Run the custom model
    solver = ReactionDiffusionSolver("lotka-volterra", grid_size=64, dt=0.01)
    solver.apply_perturbation()
    solver.step(2000)

    save_frame_fast(solver.u, solver.v, "lotka_volterra_output.png",
                    field="v", cmap="viridis")
    print("Saved lotka_volterra_output.png")

    stats = solver.compute_statistics()
    print(f"Statistics: u_mean={stats['u_mean']:.4f}, v_mean={stats['v_mean']:.4f}")

if __name__ == "__main__":
    main()