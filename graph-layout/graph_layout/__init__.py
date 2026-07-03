"""graph_layout: from-scratch force-directed & hierarchical graph layout engine.

Pure-Python (stdlib only) graph drawing toolkit with multiple layout algorithms,
quality metrics, graph generators, transforms, and SVG/ASCII/text rendering.
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
from .render import SVGRenderer, ASCIIRenderer, TextRenderer, AnimatedSVGRenderer
from .io_utils import load_dot, save_dot, load_json, save_json, load_edge_list, save_edge_list
from .generators import (
    complete_bipartite, path_graph, star_graph, cycle_graph,
    petersen_graph, hypercube_graph, erdos_renyi,
    barabasi_albert, watts_strogatz,
)
from .transform import (
    bounding_box, scale_to_fit, normalize, translate, rotate, center_on_origin,
)

__version__ = "2.0.0"
__all__ = [
    "Graph", "Node", "Edge",
    "FruchtermanReingold", "KamadaKawai", "StressMajorization",
    "SugiyamaLayout", "TreeLayout", "CircularLayout", "RadialLayout",
    "GridLayout", "RandomLayout",
    "LayoutMetrics",
    "SVGRenderer", "ASCIIRenderer", "TextRenderer", "AnimatedSVGRenderer",
    "load_dot", "save_dot", "load_json", "save_json",
    "load_edge_list", "save_edge_list",
    "complete_bipartite", "path_graph", "star_graph", "cycle_graph",
    "petersen_graph", "hypercube_graph", "erdos_renyi",
    "barabasi_albert", "watts_strogatz",
    "bounding_box", "scale_to_fit", "normalize", "translate",
    "rotate", "center_on_origin",
]