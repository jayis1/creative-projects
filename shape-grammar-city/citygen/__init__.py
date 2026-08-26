"""Shape grammar city generator."""

from .analysis import compute_stats, shortest_path, validate_city
from .config import GenerationConfig, load_config
from .districts import District, analyze_districts
from .generator import CityMap, Point, Tile, generate_city
from .render import render_ascii, render_svg
from .reports import render_report_html

__all__ = [
    "CityMap",
    "District",
    "GenerationConfig",
    "Point",
    "Tile",
    "analyze_districts",
    "compute_stats",
    "generate_city",
    "load_config",
    "render_ascii",
    "render_report_html",
    "render_svg",
    "shortest_path",
    "validate_city",
]
