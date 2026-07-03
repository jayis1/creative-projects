"""graph_layout: from-scratch force-directed & hierarchical graph layout engine.

Pure-Python (stdlib only) graph drawing toolkit with multiple layout algorithms,
quality metrics, graph generators, transforms, SVG/ASCII/text rendering,
graph algorithms (shortest paths, centrality, MST, community detection),
and configuration-file support.

Version 3.0.0 adds:
- Graph algorithms module (BFS, DFS, Dijkstra, centrality, MST, community detection)
- DRGraph and PivotMDS layout algorithms
- HTML and Matrix renderers
- Configuration file support (JSON / TOML)
- Structured logging
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
from .advanced_layouts import DRGraphLayout, PivotMDSLayout
from .metrics import LayoutMetrics
from .render import SVGRenderer, ASCIIRenderer, TextRenderer, AnimatedSVGRenderer
from .html_renderer import HTMLRenderer
from .matrix_renderer import MatrixRenderer
from .io_utils import load_dot, save_dot, load_json, save_json, load_edge_list, save_edge_list
from .generators import (
    complete_bipartite, path_graph, star_graph, cycle_graph,
    petersen_graph, hypercube_graph, erdos_renyi,
    barabasi_albert, watts_strogatz,
)
from .transform import (
    bounding_box, scale_to_fit, normalize, translate, rotate, center_on_origin,
)
from .algorithms import (
    bfs, dfs, dijkstra, all_pairs_shortest_paths,
    degree_centrality, closeness_centrality, betweenness_centrality,
    minimum_spanning_tree, has_cycle, topological_sort, label_propagation,
)
from .config import load_config, validate_config
from .logging_utils import setup_logging, get_logger

__version__ = "3.0.0"
__all__ = [
    # Core
    "Graph", "Node", "Edge",
    # Layouts
    "FruchtermanReingold", "KamadaKawai", "StressMajorization",
    "SugiyamaLayout", "TreeLayout", "CircularLayout", "RadialLayout",
    "GridLayout", "RandomLayout", "DRGraphLayout", "PivotMDSLayout",
    # Metrics
    "LayoutMetrics",
    # Renderers
    "SVGRenderer", "ASCIIRenderer", "TextRenderer", "AnimatedSVGRenderer",
    "HTMLRenderer", "MatrixRenderer",
    # I/O
    "load_dot", "save_dot", "load_json", "save_json",
    "load_edge_list", "save_edge_list",
    # Generators
    "complete_bipartite", "path_graph", "star_graph", "cycle_graph",
    "petersen_graph", "hypercube_graph", "erdos_renyi",
    "barabasi_albert", "watts_strogatz",
    # Transforms
    "bounding_box", "scale_to_fit", "normalize", "translate",
    "rotate", "center_on_origin",
    # Algorithms
    "bfs", "dfs", "dijkstra", "all_pairs_shortest_paths",
    "degree_centrality", "closeness_centrality", "betweenness_centrality",
    "minimum_spanning_tree", "has_cycle", "topological_sort",
    "label_propagation",
    # Config & Logging
    "load_config", "validate_config", "setup_logging", "get_logger",
]