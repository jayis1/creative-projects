"""Particle Life simulator package."""

from .engine import ParticleLifeSimulation, SimulationConfig
from .presets import built_in_presets, preset_names
from .render import render_ascii, render_ppm, render_svg

__all__ = [
    "ParticleLifeSimulation",
    "SimulationConfig",
    "built_in_presets",
    "preset_names",
    "render_ascii",
    "render_ppm",
    "render_svg",
]
