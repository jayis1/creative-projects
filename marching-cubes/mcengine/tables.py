"""Marching-cubes lookup tables and cube topology.

Cube corner numbering (right-handed, origin at (0,0,0))::

      7--------6         z
     /|       /|         |  / y
    4--------5 |         | /
    | |      | |         |/
    | 3------|-2         o--------x
    |/       |/
    0--------1

Edge numbering (12 edges)::

    edge 0  -> (0,1)   edge 1  -> (1,2)   edge 2  -> (2,3)   edge 3  -> (3,0)
    edge 4  -> (4,5)   edge 5  -> (5,6)   edge 6  -> (6,7)   edge 7  -> (7,4)
    edge 8  -> (0,4)   edge 9  -> (1,5)   edge 10 -> (2,6)  edge 11 -> (3,7)
"""

from __future__ import annotations
from typing import Dict, List, Tuple

# Corner positions in unit cube (corner index -> (x, y, z) with x/y/z in {0,1}).
CUBE_CORNERS: Tuple[Tuple[int, int, int], ...] = (
    (0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0),
    (0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1),
)

# Each edge is a pair of corner indices.
CUBE_EDGES: Tuple[Tuple[int, int], ...] = (
    (0, 1), (1, 2), (2, 3), (3, 0),
    (4, 5), (5, 6), (6, 7), (7, 4),
    (0, 4), (1, 5), (2, 6), (3, 7),
)

# For each of the 12 edges, the 4 corners of the two faces sharing that edge
# (used by the asymptotic-decider ambiguity test).
EDGES_OF_EDGE: Tuple[Tuple[int, int, int, int], ...] = (
    (2, 7, 3, 6),  # edge 0 (0,1)
    (5, 4, 0, 6),  # edge 1 (1,2)
    (0, 7, 1, 6),  # edge 2 (2,3)
    (2, 5, 0, 7),  # edge 3 (3,0)
    (6, 1, 7, 0),  # edge 4 (4,5)
    (4, 3, 1, 7),  # edge 5 (5,6)
    (4, 3, 5, 2),  # edge 6 (6,7)
    (6, 1, 4, 3),  # edge 7 (7,4)
    (3, 5, 2, 1),  # edge 8 (0,4)
    (0, 7, 2, 6),  # edge 9 (1,5)
    (3, 4, 0, 5),  # edge 10 (2,6)
    (2, 5, 0, 6),  # edge 11 (3,7)
)

# ---------------------------------------------------------------------------
# Edge-cross table: for each of the 256 cube sign patterns, a 12-bit mask
# where bit e means edge e is crossed by the isosurface.  Bit i of the sign
# pattern is 1 when corner i is *inside* (field < isolevel).
#
# This table is compact (256 ints) and reliable — it only depends on which
# corners are inside, which is purely topological.  The triangle table below
# is *generated* from this to avoid transcription errors.
# ---------------------------------------------------------------------------
MC_EDGE_TABLE: Tuple[int, ...] = (
    0x000, 0x109, 0x203, 0x30a, 0x406, 0x50f, 0x605, 0x70c,
    0x80c, 0x905, 0xa0f, 0xb06, 0xc0a, 0xd03, 0xe09, 0xf00,
    0x190, 0x099, 0x393, 0x29a, 0x596, 0x49f, 0x795, 0x69c,
    0x99c, 0x895, 0xb9f, 0xa96, 0xd9a, 0xc93, 0xf99, 0xe90,
    0x230, 0x339, 0x033, 0x13a, 0x636, 0x73f, 0x435, 0x53c,
    0xa3c, 0xb35, 0x83f, 0x936, 0xe3a, 0xf33, 0xc39, 0xd30,
    0x3a0, 0x2a9, 0x1a3, 0x0aa, 0x7a6, 0x6af, 0x5a5, 0x4ac,
    0xbac, 0xaa5, 0x9af, 0x8a6, 0xfaa, 0xea3, 0xda9, 0xca0,
    0x460, 0x569, 0x663, 0x76a, 0x066, 0x16f, 0x265, 0x36c,
    0xc6c, 0xd65, 0xe6f, 0xf66, 0x86a, 0x963, 0xa69, 0xb60,
    0x5f0, 0x4f9, 0x7f3, 0x6fa, 0x1f6, 0x0ff, 0x3f5, 0x2fc,
    0xdfc, 0xcf5, 0xfff, 0xef6, 0x9fa, 0x8f3, 0xbf9, 0xaf0,
    0x650, 0x759, 0x453, 0x55a, 0x256, 0x35f, 0x055, 0x15c,
    0xe5c, 0xf55, 0xc5f, 0xd56, 0xa5a, 0xb53, 0x859, 0x950,
    0x7c0, 0x6c9, 0x5c3, 0x4ca, 0x3c6, 0x2cf, 0x1c5, 0x0cc,
    0xfcc, 0xec5, 0xdcf, 0xcc6, 0xbca, 0xac3, 0x9c9, 0x8c0,
    0x8c0, 0x9c9, 0xac3, 0xbca, 0xcc6, 0xdcf, 0xec5, 0xfcc,
    0x0cc, 0x1c5, 0x2cf, 0x3c6, 0x4ca, 0x5c3, 0x6c9, 0x7c0,
    0x950, 0x859, 0xb53, 0xa5a, 0xd56, 0xc5f, 0xf55, 0xe5c,
    0x15c, 0x055, 0x35f, 0x256, 0x55a, 0x453, 0x759, 0x650,
    0xaf0, 0xbf9, 0x8f3, 0x9fa, 0xef6, 0xfff, 0xcf5, 0xdfc,
    0x2fc, 0x3f5, 0x0ff, 0x1f6, 0x6fa, 0x7f3, 0x4f9, 0x5f0,
    0xb60, 0xa69, 0x963, 0x86a, 0xf66, 0xe6f, 0xd65, 0xc6c,
    0x36c, 0x265, 0x16f, 0x066, 0x76a, 0x663, 0x569, 0x460,
    0xca0, 0xda9, 0xea3, 0xfaa, 0x8a6, 0x9af, 0xaa5, 0xbac,
    0x4ac, 0x5a5, 0x6af, 0x7a6, 0x0aa, 0x1a3, 0x2a9, 0x3a0,
    0xd30, 0xc39, 0xf33, 0xe3a, 0x936, 0x83f, 0xb35, 0xa3c,
    0x53c, 0x435, 0x73f, 0x636, 0x13a, 0x033, 0x339, 0x230,
    0xe90, 0xf99, 0xc93, 0xd9a, 0xa96, 0xb9f, 0x895, 0x99c,
    0x69c, 0x795, 0x49f, 0x596, 0x29a, 0x393, 0x099, 0x190,
    0xf00, 0xe09, 0xd03, 0xc0a, 0xb06, 0xa0f, 0x905, 0x80c,
    0x70c, 0x605, 0x50f, 0x406, 0x30a, 0x203, 0x109, 0x000,
)


# ---------------------------------------------------------------------------
# Triangle table: loaded from a verified JSON file generated from the
# scikit-image Lorensen–Cline ("classic") lookup table.  Each entry is a list
# of edge indices (3 per triangle), terminated by -1.
# ---------------------------------------------------------------------------
import json as _json
import os as _os

_TRI_TABLE_PATH = _os.path.join(_os.path.dirname(__file__), "mc_triangle_table.json")
with open(_TRI_TABLE_PATH) as _fh:
    MC_TRIANGLE_TABLE: List[List[int]] = _json.load(_fh)

assert len(MC_TRIANGLE_TABLE) == 256, "MC_TRIANGLE_TABLE must have 256 entries"


# ---------------------------------------------------------------------------
# Tetrahedral decomposition of a cube (5 tetrahedra) for Marching Tetrahedra.
# Each tetra is a 4-tuple of corner indices.
# ---------------------------------------------------------------------------
CUBE_TETRAHEDRA: Tuple[Tuple[int, int, int, int], ...] = (
    (0, 1, 2, 5),
    (0, 2, 3, 7),
    (0, 5, 2, 7),
    (2, 7, 5, 6),
    (0, 4, 5, 7),
)

# The 6 edges of a tetrahedron, as pairs of local vertex indices (0..3).
TETRA_EDGES: Tuple[Tuple[int, int], ...] = (
    (0, 1), (1, 2), (2, 0),
    (0, 3), (1, 3), (2, 3),
)

# Marching-tetrahedra triangle table.
# Index = 4-bit sign pattern (bit i set => corner i inside / below isolevel).
# Each entry is a list of edge indices (0..5), 3 per triangle, -1 terminated.
MT_TRIANGLE_TABLE: Tuple[Tuple[int, ...], ...] = (
    (-1, -1, -1, -1, -1, -1),               # 0: no crossing
    (0, 4, 3, -1, -1, -1),                   # 1: v0 inside
    (1, 3, 5, -1, -1, -1),                   # 2: v1 inside
    (0, 1, 5, 5, 4, 0, -1),                  # 3: v0,v1 inside
    (2, 4, 5, -1, -1, -1),                   # 4: v2 inside
    (0, 4, 5, 5, 2, 0, -1),                  # 5: v0,v2 inside
    (1, 3, 4, 4, 2, 5, -1),                  # 6: v1,v2 inside
    (0, 4, 5, 0, 5, 1, 1, 5, 2, -1),         # 7: v0,v1,v2 inside
    (3, 2, 4, -1, -1, -1),                   # 8: v3 inside
    (0, 3, 4, -1, -1, -1),                   # 9: v0,v3 inside
    (1, 5, 3, 3, 0, 2, 2, 3, 4, -1),         # 10: v1,v3 inside
    (4, 3, 1, 4, 1, 0, -1),                  # 11: v0,v1,v3 inside
    (2, 5, 3, 3, 4, 2, -1),                  # 12: v2,v3 inside
    (0, 4, 3, 3, 2, 0, 2, 3, 5, -1),         # 13: v0,v2,v3 inside
    (1, 3, 5, 3, 1, 4, 4, 1, 2, -1),         # 14: v1,v2,v3 inside
    (-1, -1, -1, -1, -1, -1),               # 15: all inside -> no surface
)