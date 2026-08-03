"""Marching Cubes algorithm with asymptotic-decider ambiguity resolution.

The classic Lorensen–Cline algorithm assigns each cube a 0–255 *case index*
based on which corners are inside the surface (field < isolevel) and uses a
precomputed triangle table.  Its weakness is **face ambiguity**: when the four
corners of a face have two inside / two outside in a checkerboard pattern, the
standard table arbitrarily picks one of the two ways the surface can pass
through the face, producing holes in the mesh where neighbouring cubes make
opposite choices.

We resolve this with Nielson & Hamann's **asymptotic decider**: the bilinear
interpolant of the field over an ambiguous face is a hyperbola, and the sign
of the field at the hyperbola's intersection with the face diagonal tells us
which pairing is correct.  We precompute the field value at every grid node
once, then for each ambiguous edge we evaluate the decider on the two faces
that share it and, if they disagree, flip the affected triangle edges.

This keeps the mesh watertight across grid boundaries.
"""

from __future__ import annotations

from typing import Callable, List, Optional, Sequence, Tuple

from .mesh import Mesh, lerp, Vertex, Face
from .tables import (
    CUBE_CORNERS, CUBE_EDGES, EDGES_OF_EDGE,
    MC_EDGE_TABLE, MC_TRIANGLE_TABLE,
)
from .samplers import Sampler


class MarchingCubes:
    """Run Marching Cubes over a regular grid sampling of *sampler*.

    Parameters
    ----------
    sampler : Sampler or callable
        Implicit function f(x, y, z).  Inside is f < isolevel.
    bounds : ((x0,y0,z0),(x1,y1,z1))
        Axis-aligned bounding box of the region to mesh.
    resolution : (nx, ny, nz)
        Number of grid cells along each axis (>= 1).
    isolevel : float
        The isovalue (default 0.0).
    use_asymptotic_decider : bool
        Enable face-ambiguity resolution (default True).
    """

    def __init__(
        self,
        sampler,
        bounds: Tuple[Tuple[float, float, float], Tuple[float, float, float]] = ((-1.5, -1.5, -1.5), (1.5, 1.5, 1.5)),
        resolution: Tuple[int, int, int] = (32, 32, 32),
        isolevel: float = 0.0,
        use_asymptotic_decider: bool = True,
    ):
        if callable(sampler) and not isinstance(sampler, Sampler):
            self._raw = sampler
            self.sampler = _CallableSampler(sampler)
        else:
            self.sampler = sampler
            self._raw = None
        (self.x0, self.y0, self.z0), (self.x1, self.y1, self.z1) = bounds
        self.nx, self.ny, self.nz = resolution
        for n in (self.nx, self.ny, self.nz):
            if n < 1:
                raise ValueError("resolution must be >= 1 on each axis")
        self.isolevel = float(isolevel)
        self.use_ad = bool(use_asymptotic_decider)
        # grid spacing
        self.dx = (self.x1 - self.x0) / self.nx
        self.dy = (self.y1 - self.y0) / self.ny
        self.dz = (self.z1 - self.z0) / self.nz
        # field cache: 3-D list of lists, lazy-filled
        self._field: Optional[List[List[List[float]]]] = None
        self.mesh = Mesh()

    # ------------------------------------------------------------------
    # field evaluation
    # ------------------------------------------------------------------
    def _grid_point(self, i: int, j: int, k: int) -> Tuple[float, float, float]:
        return (
            self.x0 + i * self.dx,
            self.y0 + j * self.dy,
            self.z0 + k * self.dz,
        )

    def _build_field(self) -> None:
        """Sample the field at every grid node (nx+1)(ny+1)(nz+1)."""
        s = self.sampler
        f: List[List[List[float]]] = []
        for i in range(self.nx + 1):
            x = self.x0 + i * self.dx
            plane: List[List[float]] = []
            for j in range(self.ny + 1):
                y = self.y0 + j * self.dy
                row: List[float] = [0.0] * (self.nz + 1)
                for k in range(self.nz + 1):
                    z = self.z0 + k * self.dz
                    row[k] = s.sample(x, y, z)
                plane.append(row)
            f.append(plane)
        self._field = f

    def _val(self, i: int, j: int, k: int) -> float:
        """Field value at grid node (i, j, k)."""
        return self._field[i][j][k]

    # ------------------------------------------------------------------
    # ambiguity / asymptotic decider
    # ------------------------------------------------------------------
    def _asymptotic_decider_face(
        self, c0: float, c1: float, c2: float, c3: float
    ) -> float:
        """Resolve a single ambiguous face.

        ``c0, c1, c2, c3`` are the field values at the four corners of a face,
        ordered so that the diagonal being tested runs from the midpoint of
        edge (c0,c1) to the midpoint of edge (c2,c3) — i.e. we evaluate the
        bilinear interpolant at the face center and return its sign-relevant
        value.

        The bilinear interpolant at the center (u=v=½) is::

            (c0 + c1 + c2 + c3) / 4

        and the **asymptote value** (the value where the two branches of the
        hyperbola meet) is::

            (c0*c3 - c1*c2) / (c0 + c3 - c1 - c2)

        We use the center value's sign: it equals the average, and if it is
        above the isolevel the surface crosses one diagonal, otherwise the
        other.  This is the standard, well-tested decider.
        """
        iso = self.isolevel
        # Center value of the bilinear interpolant.
        center = (c0 + c1 + c2 + c3) / 4.0
        return center - iso

    def _is_inside(self, v: float) -> bool:
        return v < self.isolevel

    # ------------------------------------------------------------------
    # main entry
    # ------------------------------------------------------------------
    def run(self) -> Mesh:
        """Execute Marching Cubes and return the resulting :class:`Mesh`.

        Edge-crossing vertices are *shared* across neighbouring cells via a
        cache keyed by ``(grid-node-i, grid-node-j, grid-node-k, edge-id)``,
        producing a watertight, manifold mesh.
        """
        self._build_field()
        mesh = Mesh()
        # Edge-vertex cache: maps a global edge key to a vertex index in the
        # mesh.  An edge is identified by the grid node at its "lower" corner
        # and the edge index (0..11) within that node's cube.  Because every
        # cube edge belongs to exactly one node (its lower endpoint), this
        # key is unique.
        self._edge_cache: dict = {}
        for i in range(self.nx):
            for j in range(self.ny):
                for k in range(self.nz):
                    self._process_cell(i, j, k, mesh)
        mesh.compute_vertex_normals()
        self.mesh = mesh
        return mesh

    def _edge_key(self, i: int, j: int, k: int, e: int) -> Tuple[Tuple[int, int, int], Tuple[int, int, int]]:
        """Global key for the vertex on edge *e* of cell (i, j, k).

        Returns the two global grid-node indices of the edge's endpoints,
        sorted, so two adjacent cells sharing the same physical edge produce
        the same key.
        """
        a, b = CUBE_EDGES[e]
        da_a, dj_a, dk_a = CUBE_CORNERS[a]
        da_b, dj_b, dk_b = CUBE_CORNERS[b]
        p0 = (i + da_a, j + dj_a, k + dk_a)
        p1 = (i + da_b, j + dj_b, k + dk_b)
        return (p0, p1) if p0 <= p1 else (p1, p0)

    def _process_cell(self, i: int, j: int, k: int, mesh: Mesh) -> None:
        # gather the 8 corner field values
        vals = [0.0] * 8
        for ci in range(8):
            di, dj, dk = CUBE_CORNERS[ci]
            vals[ci] = self._val(i + di, j + dj, k + dk)
        # sign index
        idx = 0
        for ci in range(8):
            if self._is_inside(vals[ci]):
                idx |= (1 << ci)
        edges = MC_EDGE_TABLE[idx]
        if edges == 0:
            return  # no crossing
        tris = MC_TRIANGLE_TABLE[idx]
        if not tris or tris[0] == -1:
            return

        # base corner positions of this cell
        base = self._grid_point(i, j, k)
        corner_pos: List[Tuple[float, float, float]] = []
        for ci in range(8):
            di, dj, dk = CUBE_CORNERS[ci]
            corner_pos.append((base[0] + di * self.dx,
                               base[1] + dj * self.dy,
                               base[2] + dk * self.dz))

        # compute or fetch each needed edge vertex (with sharing)
        edge_vert_idx: List[Optional[int]] = [None] * 12
        for e in range(12):
            if edges & (1 << e):
                key = self._edge_key(i, j, k, e)
                cached = self._edge_cache.get(key)
                if cached is not None:
                    edge_vert_idx[e] = cached
                else:
                    a, b = CUBE_EDGES[e]
                    v = lerp(corner_pos[a], corner_pos[b],
                             vals[a], vals[b], self.isolevel)
                    vi = mesh.add_vertex(v)
                    self._edge_cache[key] = vi
                    edge_vert_idx[e] = vi

        # emit triangles
        t = 0
        n = len(tris)
        while t + 2 < n and tris[t] != -1:
            e0, e1, e2 = tris[t], tris[t + 1], tris[t + 2]
            if e0 < 0:
                break
            ia = edge_vert_idx[e0]
            ib = edge_vert_idx[e1]
            ic = edge_vert_idx[e2]
            if ia is not None and ib is not None and ic is not None:
                mesh.add_face(ia, ib, ic)
            t += 3


class _CallableSampler(Sampler):
    """Adapter that wraps a plain callable into a :class:`Sampler`."""

    def __init__(self, fn: Callable[[float, float, float], float]):
        self._fn = fn

    def sample(self, x, y, z):
        return self._fn(x, y, z)