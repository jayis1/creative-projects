"""
Topological Data Analysis (TDA) toolkit.

Pure-Python implementation of persistent homology and related
topological-data-analysis primitives.

Modules
-------
scomplex       : Simplex and SimplexTree data structures.
complexes      : Vietoris–Rips complex builder.
complexes_extra : Weighted Rips, Cech complex, sublevel-set filtration.
matrix         : Boundary matrix and column-reduction (persistence) algorithms.
diagram        : PersistenceDiagram, PersistencePair, barcode helpers.
distance       : Bottleneck and Hausdorff distances between diagrams / point sets.
wasserstein    : Wasserstein distance (Hungarian algorithm).
curves         : Betti curves and persistence landscapes.
images         : Persistence images (vectorized representation for ML).
plot           : ASCII persistence diagram plotting.
io             : JSON serialization / deserialization for diagrams.
cli            : Command-line interface.
"""

from .scomplex import Simplex, SimplexTree
from .complexes import VietorisRipsComplex, rips_filtration
from .complexes_extra import WeightedRipsComplex, CechComplex, SublevelFiltration
from .matrix import BoundaryMatrix, reduce_matrix, compute_persistence
from .diagram import (
    PersistenceDiagram,
    PersistencePair,
    diagrams_from_persistence,
    barcode_string,
)
from .distance import bottleneck_distance, hausdorff_distance
from .wasserstein import wasserstein_distance
from .curves import betti_curve, persistence_landscape, landscape_norm
from .images import persistence_image, image_to_ascii
from .plot import plot_diagram_ascii
from .io import diagrams_to_json, diagrams_from_json, save_diagrams, load_diagrams

__all__ = [
    "Simplex",
    "SimplexTree",
    "VietorisRipsComplex",
    "rips_filtration",
    "WeightedRipsComplex",
    "CechComplex",
    "SublevelFiltration",
    "BoundaryMatrix",
    "reduce_matrix",
    "compute_persistence",
    "PersistenceDiagram",
    "PersistencePair",
    "diagrams_from_persistence",
    "barcode_string",
    "bottleneck_distance",
    "hausdorff_distance",
    "wasserstein_distance",
    "betti_curve",
    "persistence_landscape",
    "landscape_norm",
    "persistence_image",
    "image_to_ascii",
    "plot_diagram_ascii",
    "diagrams_to_json",
    "diagrams_from_json",
    "save_diagrams",
    "load_diagrams",
]

__version__ = "2.0.0"