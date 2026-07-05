#!/usr/bin/env python3
"""Compatibility shim — imports from the fractal_explorer package.

This file exists so that legacy code and the original test suite that did
``from fractal import ...`` continue to work without modification. New code
should import from :mod:`fractal_explorer` directly.
"""
from __future__ import annotations

import os
import sys

# Make the package importable.
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from fractal_explorer import *  # noqa: F401,F403
from fractal_explorer.cli import build_cli, main, _parse_complex, _parse_rgb
from fractal_explorer.cli import _add_render_args, _build_trap, _apply_config_file
from fractal_explorer.cli import cmd_render, cmd_julia, cmd_newton, cmd_zoom
from fractal_explorer.cli import cmd_ascii, cmd_palette, cmd_explore
from fractal_explorer.cli import cmd_benchmark, cmd_info