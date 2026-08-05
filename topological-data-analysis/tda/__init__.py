"""
Topological Data Analysis (TDA) toolkit.

Pure-Python implementation of persistent homology and related
topological-data-analysis primitives.

Modules
-------
scomplex   : Simplex and SimplexTree data structures.
complexes  : Vietoris–Rips and alpha-style complex builders.
matrix     : Boundary matrix and column-reduction (persistence) algorithms.
diagram    : PersistenceDiagram, PersistencePair, barcode helpers.
distance   : Bottleneck and Hausdorff distances between diagrams / point sets.
curves     : Betti curves and persistence landscapes.
io         : JSON serialization / deserialization for diagrams.
cli        : Command-line interface.
"""

from .scomplex import Simplex, SimplexTree
from .complexes import VietorisRipsComplex
from .matrix import BoundaryMatrix, reduce_matrix, compute_persistence
from .diagram import PersistenceDiagram, PersistencePair, diagrams_from_persistence, barcode_string
from .distance import bottleneck_distance, hausdorff_distance
from .curves import betti_curve, persistence_landscape

__all__ = [
    "Simplex",
    "SimplexTree",
    "VietorisRipsComplex",
    "BoundaryMatrix",
    "reduce_matrix",
    "compute_persistence",
    "PersistenceDiagram",
    "PersistencePair",
    "diagrams_from_persistence",
    "barcode_string",
    "bottleneck_distance",
    "hausdorff_distance",
    "betti_curve",
    "persistence_landscape",
]

__version__ = "1.0.0"