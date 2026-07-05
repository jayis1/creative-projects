"""Fractal Explorer — Complex dynamics fractal renderer.

A from-scratch, pure-Python library for rendering escape-time and other
fractals with zero external dependencies (stdlib only).

Public API
----------
The package re-exports the most useful names so that::

    from fractal_explorer import Viewport, render_fractal, write_png

works out of the box.  See :mod:`fractal_explorer.cli` for the CLI entry
point and :mod:`fractal_explorer` submodules for advanced usage.
"""
from __future__ import annotations

from .palettes import (
    _lerp, _lerp_color, _clamp_byte, _hsb_to_rgb, _cycle_hue_palette,
    _gradient_stops, rainbow_palette, fire_palette, ice_palette,
    grayscale_palette, electric_palette, sunset_palette, ocean_palette,
    magma_palette, earth_palette, custom_palette_from_hex, PALETTES,
    get_palette,
)
from .iterators import (
    _mandelbrot_iter, _mandelbrot_de_iter, _julia_iter, _burning_ship_iter,
    _tricorn_iter, _celtic_iter, _phoenix_iter, _magnet_iter, _newton_iter,
    _custom_iter, FRACTALS, DE_CAPABLE, get_fractal,
)
from .traps import (
    OrbitTrap, PointTrap, LineTrap, CircleTrap, CrossTrap,
    StripeTrap, SpiralTrap, TRAPS, make_trap,
)
from .viewport import Viewport
from .coloring import _smooth_iter, _true_distance, _compute_pixel
from .render import _render_row_worker, render_fractal, render_histogram_coloring
from .hp import mandelbrot_decimal, render_mandelbrot_hp
from .io_writers import write_ppm, write_png, write_svg, write_ascii, write_tga
from .zoom import render_zoom_sequence
from .julia import explore_julia
from .benchmark import benchmark
from .config import _load_config, _merge_config, _detect_explicit_args
from .buddhabrot import render_buddhabrot, AntiBuddhabrot
from .lyapunov import render_lyapunov
from .ifs import IFSFractal, BARNSLEY_FERN, SIERPINSKI_TRIANGLE, DRAGON_CURVE, render_ifs
from .filters import (
    box_blur, gaussian_blur, edge_detect, emboss, grayscale_filter,
    invert, brightness, contrast, apply_filter, FILTERS,
)
from .animation import render_julia_morph, render_color_cycle
from .presets import PresetManager, PRESETS, save_preset, load_preset

# Logging is configured at the package level so submodules share it.
import logging as _logging
logger = _logging.getLogger("fractal_explorer")
logger.addHandler(_logging.NullHandler())

__version__ = "1.1.0"
__author__ = "Hermes Agent"
__all__ = [
    # palettes
    "PALETTES", "get_palette", "rainbow_palette", "fire_palette",
    "ice_palette", "grayscale_palette", "electric_palette", "sunset_palette",
    "ocean_palette", "magma_palette", "earth_palette",
    "custom_palette_from_hex",
    "_lerp", "_lerp_color", "_clamp_byte", "_hsb_to_rgb",
    "_cycle_hue_palette", "_gradient_stops",
    # iterators
    "FRACTALS", "DE_CAPABLE", "get_fractal",
    "_mandelbrot_iter", "_mandelbrot_de_iter", "_julia_iter",
    "_burning_ship_iter", "_tricorn_iter", "_celtic_iter", "_phoenix_iter",
    "_magnet_iter", "_newton_iter", "_custom_iter",
    # traps
    "OrbitTrap", "PointTrap", "LineTrap", "CircleTrap", "CrossTrap",
    "StripeTrap", "SpiralTrap", "TRAPS", "make_trap",
    # viewport
    "Viewport",
    # coloring
    "_smooth_iter", "_true_distance", "_compute_pixel",
    # render
    "_render_row_worker", "render_fractal", "render_histogram_coloring",
    # hp
    "mandelbrot_decimal", "render_mandelbrot_hp",
    # io
    "write_ppm", "write_png", "write_svg", "write_ascii", "write_tga",
    # zoom
    "render_zoom_sequence",
    # julia
    "explore_julia",
    # benchmark
    "benchmark",
    # config
    "_load_config", "_merge_config", "_detect_explicit_args",
    # new features
    "render_buddhabrot", "AntiBuddhabrot",
    "render_lyapunov",
    "IFSFractal", "BARNSLEY_FERN", "SIERPINSKI_TRIANGLE", "DRAGON_CURVE",
    "render_ifs",
    "box_blur", "gaussian_blur", "edge_detect", "emboss", "grayscale_filter",
    "invert", "brightness", "contrast", "apply_filter", "FILTERS",
    "render_julia_morph", "render_color_cycle",
    "PresetManager", "PRESETS", "save_preset", "load_preset",
    # meta
    "__version__", "__author__",
]