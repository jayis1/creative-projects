"""
Topological Data Analysis (TDA) toolkit.

Pure-Python implementation of persistent homology and related
topological-data-analysis primitives.

Modules
-------
scomplex       : Simplex and SimplexTree data structures.
complexes      : Vietoris–Rips complex builder.
complexes_extra : Weighted Rips, Cech complex, sublevel-set filtration.
alpha_complex  : Alpha complex (filtered by smallest-enclosing-ball radius).
matrix         : Boundary matrix and column-reduction (persistence) algorithms.
optimized      : Clearing reduction and sparse Rips complex (k-NN truncation).
diagram        : PersistenceDiagram, PersistencePair, barcode helpers.
distance       : Bottleneck and Hausdorff distances between diagrams / point sets.
wasserstein    : Wasserstein distance (Hungarian algorithm).
curves         : Betti curves and persistence landscapes.
images         : Persistence images (vectorized representation for ML).
statistics     : Summary statistics, entropy, amplitudes, feature vectors.
kernels        : Persistence kernels (PSS, PWG, Fisher) for ML.
batch          : Batch and streaming processing of multiple point clouds.
plot           : ASCII persistence diagram plotting.
io             : JSON serialization / deserialization for diagrams.
config         : Configuration file (YAML/JSON) loading and validation.
exceptions     : Exception hierarchy.
logging_config : Logging utilities.
cli            : Command-line interface.
"""

from .scomplex import Simplex, SimplexTree
from .complexes import VietorisRipsComplex, rips_filtration
from .complexes_extra import WeightedRipsComplex, CechComplex, SublevelFiltration
from .alpha_complex import AlphaComplex
from .matrix import BoundaryMatrix, reduce_matrix, compute_persistence
from .optimized import compute_persistence_clearing, SparseRipsComplex
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
from .statistics import (
    diagram_statistics,
    all_statistics,
    statistics_table,
    persistent_entropy,
    amplitudes,
    vectorize,
)
from .kernels import pss_kernel, pwg_kernel, fisher_kernel, kernel_matrix
from .batch import BatchProcessor, stream_persistence
from .plot import plot_diagram_ascii
from .io import diagrams_to_json, diagrams_from_json, save_diagrams, load_diagrams
from .config import load_config, save_config, validate_config, merge_config, DEFAULT_CONFIG
from .exceptions import (
    TDAError,
    EmptyInputError,
    DimensionMismatchError,
    InvalidParameterError,
    ComputationError,
    FileFormatError,
)

__all__ = [
    # Core
    "Simplex",
    "SimplexTree",
    "VietorisRipsComplex",
    "rips_filtration",
    "WeightedRipsComplex",
    "CechComplex",
    "SublevelFiltration",
    "AlphaComplex",
    "SparseRipsComplex",
    "BoundaryMatrix",
    "reduce_matrix",
    "compute_persistence",
    "compute_persistence_clearing",
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
    # Statistics
    "diagram_statistics",
    "all_statistics",
    "statistics_table",
    "persistent_entropy",
    "amplitudes",
    "vectorize",
    # Kernels
    "pss_kernel",
    "pwg_kernel",
    "fisher_kernel",
    "kernel_matrix",
    # Batch / streaming
    "BatchProcessor",
    "stream_persistence",
    # Config
    "load_config",
    "save_config",
    "validate_config",
    "merge_config",
    "DEFAULT_CONFIG",
    # Exceptions
    "TDAError",
    "EmptyInputError",
    "DimensionMismatchError",
    "InvalidParameterError",
    "ComputationError",
    "FileFormatError",
]

__version__ = "3.0.0"