"""Particle Life simulator package."""

from .analysis import summarize_simulation, sweep_parameters
from .engine import ParticleLifeSimulation, SimulationConfig
from .io import dump_csv, dump_json, dump_mapping, load_mapping
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
    "load_mapping",
    "dump_json",
    "dump_mapping",
    "dump_csv",
    "summarize_simulation",
    "sweep_parameters",
]
