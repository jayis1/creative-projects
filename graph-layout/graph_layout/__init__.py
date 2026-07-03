"""graph_layout: from-scratch force-directed & hierarchical graph layout engine.

Pure-Python (stdlib only) graph drawing toolkit with multiple layout algorithms,
quality metrics, and SVG/ASCII/text rendering.
"""

from .graph import Graph, Node, Edge
from .layouts import (
    FruchtermanReingold,
    KamadaKawai,
    StressMajorization,
    SugiyamaLayout,
    TreeLayout,
    CircularLayout,
    RadialLayout,
    GridLayout,
    RandomLayout,
)
from .metrics import LayoutMetrics
from .render import SVGRenderer, ASCIIRenderer, TextRenderer
from .io_utils import load_dot, save_dot, load_json, save_json, load_edge_list, save_edge_list

__version__ = "1.0.0"
__all__ = [
    "Graph", "Node", "Edge",
    "FruchtermanReingold", "KamadaKawai", "StressMajorization",
    "SugiyamaLayout", "TreeLayout", "CircularLayout", "RadialLayout",
    "GridLayout", "RandomLayout",
    "LayoutMetrics",
    "SVGRenderer", "ASCIIRenderer", "TextRenderer",
    "load_dot", "save_dot", "load_json", "save_json",
    "load_edge_list", "save_edge_list",
]