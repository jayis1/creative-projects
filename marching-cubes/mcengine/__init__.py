"""mcengine — a from-scratch isosurface extraction toolkit.

Implements three classic meshing algorithms that convert an implicit
function f(x, y, z) = isolevel into a triangle mesh:

* :class:`MarchingCubes` — the classic Lorensen–Cline algorithm with
  correct top/bottom-face ambiguity resolution via the *asymptotic decider*
  (Nielson & Hamann 1991).
* :class:`MarchingTetrahedra` — decomposes each cube into five tetrahedra
  and extracts the isosurface inside each.  Tetrahedral cells are
  topologically unambiguous.
* :class:`DualContouring` — generates one vertex per cell placed at the
  intersection of the surface's tangent planes (QEF minimisation), then
  connects the vertices of four neighbouring cells sharing an edge that
  the surface crosses.

Meshes are returned as a simple :class:`Mesh` dataclass holding vertex /
face / normal arrays (plain Python lists) and can be exported to several
text/binary formats.

The entire toolkit is pure-Python (standard library only) so it works
without NumPy.

Additional features
-------------------
* Mesh transforms (translate, scale, rotate, mirror, normalize)
* Loop subdivision for mesh refinement
* Mesh file readers (OBJ, OFF, PLY, STL)
* Batch rendering from JSON/TOML config files
* Preset configurations for common surfaces
* Comprehensive mesh diagnostics
* ASCII art preview renderer
"""

from .mesh import Mesh, Vertex, Face, lerp
from .tables import CUBE_CORNERS, CUBE_EDGES, EDGES_OF_EDGE, MC_TRIANGLE_TABLE, MC_EDGE_TABLE
from .marching_cubes import MarchingCubes
from .marching_tetrahedra import MarchingTetrahedra
from .dual_contouring import DualContouring
from .samplers import (
    Sampler,
    SphereSampler,
    TorusSampler,
    Genus2Sampler,
    GyroidSampler,
    HeartSampler,
    BooleanOpsSampler,
    SuperquadricSampler,
    HyperboloidSampler,
    NoisySampler,
    SteinerSampler,
    OctahedronSampler,
)
from .export import (
    write_obj,
    write_ply_ascii,
    write_ply_binary,
    write_stl_ascii,
    write_stl_binary,
    write_off,
    write_gltf_minimal,
)
from .diagnostics import (
    MeshDiagnostics,
    compute_bounding_box,
    euler_characteristic,
    analyze_mesh,
)
from .vec3 import Vec3, normalize, cross, dot
from .ascii_preview import render_ascii_preview
from .volume_sampler import VolumeSampler
from .simplify import simplify_mesh
from .transforms import (
    translate, scale, scale_uniform, rotate_x, rotate_y, rotate_z,
    mirror, center, normalize_size, merge_meshes,
)
from .subdivision import loop_subdivide, subdivide_n
from .mesh_io import (
    read_obj, read_off, read_ply_ascii, read_stl_ascii, read_stl_binary,
    read_mesh,
)
from .config import (
    PRESETS, get_preset, list_presets, load_config, save_config,
    normalize_job,
)
from .batch import render_job, render_config, render_preset
from .logging_util import get_logger, set_log_level

__version__ = "2.0.0"

__all__ = [
    # Core algorithms
    "MarchingCubes",
    "MarchingTetrahedra",
    "DualContouring",
    # Mesh data structures
    "Mesh",
    "Vertex",
    "Face",
    "Vec3",
    "lerp",
    "normalize",
    "cross",
    "dot",
    # Tables
    "CUBE_CORNERS",
    "CUBE_EDGES",
    "EDGES_OF_EDGE",
    "MC_TRIANGLE_TABLE",
    "MC_EDGE_TABLE",
    # Samplers
    "Sampler",
    "SphereSampler",
    "TorusSampler",
    "Genus2Sampler",
    "GyroidSampler",
    "HeartSampler",
    "BooleanOpsSampler",
    "SuperquadricSampler",
    "HyperboloidSampler",
    "NoisySampler",
    "SteinerSampler",
    "OctahedronSampler",
    "VolumeSampler",
    # Export
    "write_obj",
    "write_ply_ascii",
    "write_ply_binary",
    "write_stl_ascii",
    "write_stl_binary",
    "write_off",
    "write_gltf_minimal",
    # Import
    "read_obj",
    "read_off",
    "read_ply_ascii",
    "read_stl_ascii",
    "read_stl_binary",
    "read_mesh",
    # Diagnostics
    "MeshDiagnostics",
    "compute_bounding_box",
    "euler_characteristic",
    "analyze_mesh",
    # Preview
    "render_ascii_preview",
    # Simplification
    "simplify_mesh",
    # Transforms
    "translate",
    "scale",
    "scale_uniform",
    "rotate_x",
    "rotate_y",
    "rotate_z",
    "mirror",
    "center",
    "normalize_size",
    "merge_meshes",
    # Subdivision
    "loop_subdivide",
    "subdivide_n",
    # Config & batch
    "PRESETS",
    "get_preset",
    "list_presets",
    "load_config",
    "save_config",
    "normalize_job",
    "render_job",
    "render_config",
    "render_preset",
    # Logging
    "get_logger",
    "set_log_level",
]