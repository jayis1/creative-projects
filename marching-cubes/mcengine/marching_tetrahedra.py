"""Marching Tetrahedra — unambiguous isosurface extraction.

Each cube is split into 5 tetrahedra.  A tetrahedron has only 16 sign cases and
**no face ambiguity** (a tetra face is a triangle, not a quadrilateral), so the
resulting mesh is always topologically consistent across cells — no holes from
ambiguity.  The trade-off is ~5× the per-cell work and slightly more triangles.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from .mesh import Mesh, lerp, Vertex
from .tables import CUBE_CORNERS, CUBE_TETRAHEDRA, TETRA_EDGES, MT_TRIANGLE_TABLE
from .samplers import Sampler
from .marching_cubes import _CallableSampler


class MarchingTetrahedra:
    """Marching Tetrahedra over a regular grid.

    Constructor parameters mirror :class:`MarchingCubes`; there is no
    ambiguity-resolution option because tetrahedra are inherently unambiguous.
    """

    def __init__(
        self,
        sampler,
        bounds: Tuple[Tuple[float, float, float], Tuple[float, float, float]] = ((-1.5, -1.5, -1.5), (1.5, 1.5, 1.5)),
        resolution: Tuple[int, int, int] = (24, 24, 24),
        isolevel: float = 0.0,
    ):
        if callable(sampler) and not isinstance(sampler, Sampler):
            self.sampler = _CallableSampler(sampler)
        else:
            self.sampler = sampler
        (self.x0, self.y0, self.z0), (self.x1, self.y1, self.z1) = bounds
        self.nx, self.ny, self.nz = resolution
        for n in (self.nx, self.ny, self.nz):
            if n < 1:
                raise ValueError("resolution must be >= 1 on each axis")
        self.isolevel = float(isolevel)
        self.dx = (self.x1 - self.x0) / self.nx
        self.dy = (self.y1 - self.y0) / self.ny
        self.dz = (self.z1 - self.z0) / self.nz
        self._field: Optional[List[List[List[float]]]] = None
        self.mesh = Mesh()

    def _grid_point(self, i, j, k):
        return (self.x0 + i * self.dx, self.y0 + j * self.dy, self.z0 + k * self.dz)

    def _build_field(self):
        s = self.sampler
        f = []
        for i in range(self.nx + 1):
            x = self.x0 + i * self.dx
            plane = []
            for j in range(self.ny + 1):
                y = self.y0 + j * self.dy
                row = [0.0] * (self.nz + 1)
                for k in range(self.nz + 1):
                    z = self.z0 + k * self.dz
                    row[k] = s.sample(x, y, z)
                plane.append(row)
            f.append(plane)
        self._field = f

    def _val(self, i, j, k):
        return self._field[i][j][k]

    def run(self) -> Mesh:
        self._build_field()
        mesh = Mesh()
        self._edge_cache: dict = {}
        for i in range(self.nx):
            for j in range(self.ny):
                for k in range(self.nz):
                    self._process_cell(i, j, k, mesh)
        mesh.compute_vertex_normals()
        self.mesh = mesh
        return mesh

    def _cube_edge_key(self, i: int, j: int, k: int, ca: int, cb: int):
        """Global key for the vertex between cube corners ca and cb of cell (i,j,k)."""
        da_a, dj_a, dk_a = CUBE_CORNERS[ca]
        da_b, dj_b, dk_b = CUBE_CORNERS[cb]
        p0 = (i + da_a, j + dj_a, k + dk_a)
        p1 = (i + da_b, j + dj_b, k + dk_b)
        return (p0, p1) if p0 <= p1 else (p1, p0)

    def _process_cell(self, i: int, j: int, k: int, mesh: Mesh) -> None:
        vals = [0.0] * 8
        for ci in range(8):
            di, dj, dk = CUBE_CORNERS[ci]
            vals[ci] = self._val(i + di, j + dj, k + dk)
        base = self._grid_point(i, j, k)
        corner_pos = []
        for ci in range(8):
            di, dj, dk = CUBE_CORNERS[ci]
            corner_pos.append((base[0] + di * self.dx,
                               base[1] + dj * self.dy,
                               base[2] + dk * self.dz))
        for tet in CUBE_TETRAHEDRA:
            self._process_tetra(i, j, k, tet, vals, corner_pos, mesh)

    def _process_tetra(self, i: int, j: int, k: int, tet, vals, corner_pos, mesh: Mesh) -> None:
        tv = [vals[c] for c in tet]          # 4 field values
        tp = [corner_pos[c] for c in tet]    # 4 positions
        tc = [tet[c] for c in range(4)]      # 4 cube corner indices
        idx = 0
        for v in tv:
            if v < self.isolevel:
                idx = (idx << 1) | 1
            else:
                idx = idx << 1
        # our MT_TRIANGLE_TABLE uses bit 0 = corner 0 (LSB), but we built idx
        # MSB-first; reverse the bits for the 4-bit pattern.
        idx = ((idx & 1) << 3) | (idx & 2) << 1 | (idx & 4) >> 1 | (idx >> 3) & 1
        entry = MT_TRIANGLE_TABLE[idx]
        if entry[0] == -1:
            return
        # compute or fetch the 6 edge vertices (with sharing via cache)
        ev: List[Optional[int]] = [None] * 6
        for ei in range(6):
            a, b = TETRA_EDGES[ei]
            ca, cb = tc[a], tc[b]
            key = self._cube_edge_key(i, j, k, ca, cb)
            cached = self._edge_cache.get(key)
            if cached is not None:
                ev[ei] = cached
            else:
                v = lerp(tp[a], tp[b], tv[a], tv[b], self.isolevel)
                vi = mesh.add_vertex(v)
                self._edge_cache[key] = vi
                ev[ei] = vi
        t = 0
        n = len(entry)
        while t + 2 < n and entry[t] != -1:
            e0, e1, e2 = entry[t], entry[t + 1], entry[t + 2]
            if e0 < 0: break
            ia = ev[e0]; ib = ev[e1]; ic = ev[e2]
            if ia is not None and ib is not None and ic is not None:
                mesh.add_face(ia, ib, ic)
            t += 3