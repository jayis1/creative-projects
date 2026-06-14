"""
rdsim — Reaction-Diffusion Pattern Simulator

A pure-Python simulator for Turing patterns using Gray-Scott,
FitzHugh-Nagumo, Gierer-Meinhardt, and Brusselator models.

Usage:
    from rdsim import ReactionDiffusionSolver, get_model, list_presets

    solver = ReactionDiffusionSolver("gray-scott", grid_size=128)
    solver.apply_perturbation()
    solver.step(5000)
    u, v = solver.get_state()
"""

__version__ = "2.0.0"
__author__ = "Creative Projects"

from rdsim.solver import ReactionDiffusionSolver, apply_laplacian, LAPLACIAN_STENCIL
from rdsim.models import get_model, MODELS, register_model
from rdsim.presets import get_preset, list_presets, ALL_PRESETS
from rdsim.visualization import (
    save_frame, save_frame_fast, render_frame_grid,
    save_gif, render_frame, save_video,
)
from rdsim.config import load_config, SimulationConfig