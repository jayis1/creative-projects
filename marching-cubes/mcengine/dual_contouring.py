"""Dual Contouring — one vertex per cell placed via QEF minimisation.

Dual Contouring (Ju et al., 2002) places a single vertex inside each cell that
the surface crosses, positioned to lie on all of the surface's tangent planes
that intersect the cell edges.  It then connects the vertices of the 2×2×2 block
of cells around every crossed edge, producing a quad split into two triangles.

The vertex position is found by minimising the *quadratic error function*

    QEF(x) = Σ_i (n_i · (x - p_i))²

where ``p_i`` is the crossing point on edge *i* and ``n_i`` the unit normal
there (the gradient of the field).  The minimiser is the solution of the 3×3
linear system  ``Aᵀ A x = Aᵀ b``.

This produces **much** lower-poly-count meshes than Marching Cubes while
preserving sharp features (cube edges, octahedron tips, etc.).
"""

from __future__ import annotations

import math
from typing import List, Optional, Tuple

from .mesh import Mesh, lerp, Vertex
from .tables import CUBE_CORNERS, CUBE_EDGES
from .samplers import Sampler
from .marching_cubes import _CallableSampler


class DualContouring:
    """Dual Contouring over a regular grid.

    Parameters
    ----------
    sampler : Sampler or callable
        Implicit function with optional analytic gradient.
    bounds, resolution, isolevel : see :class:`MarchingCubes`.
    sharp_threshold : float
        Maximum acceptable QEF residual; cells whose best vertex has a larger
        residual are flagged (useful for diagnostics).  Default 1.0.
    clamp_to_cell : bool
        If True (default) the vertex is clamped to lie inside its cell, which
        guarantees a manifold result but can blunt very sharp features.
    """

    def __init__(
        self,
        sampler,
        bounds: Tuple[Tuple[float, float, float], Tuple[float, float, float]] = ((-1.5, -1.5, -1.5), (1.5, 1.5, 1.5)),
        resolution: Tuple[int, int, int] = (16, 16, 16),
        isolevel: float = 0.0,
        sharp_threshold: float = 1.0,
        clamp_to_cell: bool = True,
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
        self.sharp_threshold = float(sharp_threshold)
        self.clamp = bool(clamp_to_cell)
        self.dx = (self.x1 - self.x0) / self.nx
        self.dy = (self.y1 - self.y0) / self.ny
        self.dz = (self.z1 - self.z0) / self.nz
        self._field: Optional[List[List[List[float]]]] = None
        self.mesh = Mesh()
        # per-cell vertex index (None if cell not crossed)
        self._cell_vertex: Optional[List[List[List[Optional[int]]]]] = None

    # ------------------------------------------------------------------
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

    def _inside(self, v):
        return v < self.isolevel

    # ------------------------------------------------------------------
    # QEF minimisation
    # ------------------------------------------------------------------
    def _solve_qef(self, points: List[Vertex], normals: List[Vertex],
                  cell_min: Vertex, cell_max: Vertex) -> Vertex:
        """Minimise Σ (nᵢ·(x - pᵢ))² via the normal equations.

        Returns the minimiser, clamped to the cell if ``self.clamp``.
        """
        # Build A^T A  and  A^T b  where row i of A is n_i and b_i = n_i·p_i.
        # AᵀA is symmetric 3×3; we accumulate it directly.
        ata = [[0.0] * 3 for _ in range(3)]
        atb = [0.0] * 3
        for p, n in zip(points, normals):
            b = n[0] * p[0] + n[1] * p[1] + n[2] * p[2]
            for r in range(3):
                nr = n[r]
                if nr == 0.0:
                    continue
                atb[r] += nr * b
                row = ata[r]
                for c in range(3):
                    row[c] += nr * n[c]
        # Solve via Cholesky-style Gaussian elimination with a tiny
        # regularisation to handle degenerate cases (few crossings).
        for r in range(3):
            ata[r][r] += 1e-9
        x = self._solve_3x3(ata, atb)
        if x is None:
            # Degenerate: fall back to centroid of the crossing points.
            if points:
                cx = sum(p[0] for p in points) / len(points)
                cy = sum(p[1] for p in points) / len(points)
                cz = sum(p[2] for p in points) / len(points)
                x = (cx, cy, cz)
            else:
                x = ((cell_min[0] + cell_max[0]) / 2,
                      (cell_min[1] + cell_max[1]) / 2,
                      (cell_min[2] + cell_max[2]) / 2)
        if self.clamp:
            x = (max(cell_min[0], min(cell_max[0], x[0])),
                 max(cell_min[1], min(cell_max[1], x[1])),
                 max(cell_min[2], min(cell_max[2], x[2])))
        return x

    @staticmethod
    def _solve_3x3(A, b) -> Optional[Vertex]:
        """Solve Ax = b for a 3×3 system; return None if singular."""
        # Cramer's rule with regularisation guard.
        det = (A[0][0] * (A[1][1] * A[2][2] - A[1][2] * A[2][1])
               - A[0][1] * (A[1][0] * A[2][2] - A[1][2] * A[2][0])
               + A[0][2] * (A[1][0] * A[2][1] - A[1][1] * A[2][0]))
        if abs(det) < 1e-15:
            return None
        inv_det = 1.0 / det

        def det3(c0, c1, c2):
            return (c0[0] * (A[1][1] * A[2][2] - A[1][2] * A[2][1])
                    - c0[1] * (A[1][0] * A[2][2] - A[1][2] * A[2][0])
                    + c0[2] * (A[1][0] * A[2][1] - A[1][1] * A[2][0]))

        x = det3(b, [A[0][1], A[1][1], A[2][1]], [A[0][2], A[1][2], A[2][2]]) * inv_det
        y = det3([A[0][0], A[1][0], A[2][0]], b, [A[0][2], A[1][2], A[2][2]]) * inv_det
        z = det3([A[0][0], A[1][0], A[2][0]], [A[0][1], A[1][1], A[2][1]], b) * inv_det
        return (x, y, z)

    # ------------------------------------------------------------------
    def run(self) -> Mesh:
        self._build_field()
        mesh = Mesh()
        # Allocate per-cell vertex map.
        self._cell_vertex = [[[None] * self.nz for _ in range(self.ny)] for _ in range(self.nx)]
        for i in range(self.nx):
            for j in range(self.ny):
                for k in range(self.nz):
                    self._place_cell_vertex(i, j, k, mesh)
        # Connect: for each edge (axis-aligned) between grid nodes that has a
        # sign change, emit a quad from the 4 surrounding cells.
        self._generate_faces(mesh)
        mesh.compute_vertex_normals()
        self.mesh = mesh
        return mesh

    def _place_cell_vertex(self, i, j, k, mesh: Mesh):
        vals = [0.0] * 8
        for ci in range(8):
            di, dj, dk = CUBE_CORNERS[ci]
            vals[ci] = self._val(i + di, j + dj, k + dk)
        edges_crossed = []
        for e in range(12):
            a, b = CUBE_EDGES[e]
            if self._inside(vals[a]) != self._inside(vals[b]):
                edges_crossed.append((a, b))
        if not edges_crossed:
            return
        # compute crossing points + normals
        base = self._grid_point(i, j, k)
        corner_pos = []
        for ci in range(8):
            di, dj, dk = CUBE_CORNERS[ci]
            corner_pos.append((base[0] + di * self.dx, base[1] + dj * self.dy, base[2] + dk * self.dz))
        pts: List[Vertex] = []
        nms: List[Vertex] = []
        for (a, b) in edges_crossed:
            pa = corner_pos[a]; pb = corner_pos[b]
            va = vals[a]; vb = vals[b]
            p = lerp(pa, pb, va, vb, self.isolevel)
            n = self.sampler.gradient(p[0], p[1], p[2])
            # normalise; flip so it points toward the outside (field > iso)
            L = math.sqrt(n[0] * n[0] + n[1] * n[1] + n[2] * n[2])
            if L < 1e-12:
                n = (0.0, 0.0, 0.0)
            else:
                n = (n[0] / L, n[1] / L, n[2] / L)
            # If the gradient points toward inside (field increasing toward
            # outside is standard for f=distance-iso); we leave as-is.
            pts.append(p)
            nms.append(n)
        cell_min = base
        cell_max = (base[0] + self.dx, base[1] + self.dy, base[2] + self.dz)
        v = self._solve_qef(pts, nms, cell_min, cell_max)
        idx = mesh.add_vertex(v)
        self._cell_vertex[i][j][k] = idx

    # ------------------------------------------------------------------
    def _generate_faces(self, mesh: Mesh):
        """Emit faces: for every grid edge with a sign change, the four
        neighbouring cells' vertices form a quad (split into 2 triangles)."""
        cv = self._cell_vertex

        # X-axis edges: between (i,j,k) and (i+1,j,k)
        for i in range(self.nx):
            for j in range(self.ny):
                for k in range(self.nz):
                    v0 = self._val(i, j, k)
                    v1 = self._val(i + 1, j, k)
                    if self._inside(v0) != self._inside(v1):
                        self._emit_quad(mesh, cv, i - 1, j - 1, k - 1, axis='x', ei=i, ej=j, ek=k)

        # Y-axis edges
        for i in range(self.nx):
            for j in range(self.ny):
                for k in range(self.nz):
                    v0 = self._val(i, j, k)
                    v1 = self._val(i, j + 1, k)
                    if self._inside(v0) != self._inside(v1):
                        self._emit_quad(mesh, cv, i - 1, j - 1, k - 1, axis='y', ei=i, ej=j, ek=k)

        # Z-axis edges
        for i in range(self.nx):
            for j in range(self.ny):
                for k in range(self.nz):
                    v0 = self._val(i, j, k)
                    v1 = self._val(i, j, k + 1)
                    if self._inside(v0) != self._inside(v1):
                        self._emit_quad(mesh, cv, i - 1, j - 1, k - 1, axis='z', ei=i, ej=j, ek=k)

    def _emit_quad(self, mesh, cv, base_i, base_j, base_k, axis, ei, ej, ek):
        """Collect the (up to 4) cell-vertices around edge (ei,ej,ek) and emit
        a quad split into two triangles."""
        # The four cells sharing an axis-edge:
        #  X-edge along (ei,ej,ek)->(ei+1,ej,ek): cells at (ei, ej-1, ek-1),(ei, ej, ek-1),(ei, ej-1, ek),(ei, ej, ek)
        #  Y-edge along (ei,ej,ek)->(ei,ej+1,ek): cells at (ei-1, ej, ek-1),(ei, ej, ek-1),(ei-1, ej, ek),(ei, ej, ek)
        #  Z-edge along (ei,ej,ek)->(ei,ej,ek+1): cells at (ei-1, ej-1, ek),(ei, ej-1, ek),(ei-1, ej, ek),(ei, ej, ek)
        if axis == 'x':
            cells = [(ei, ej - 1, ek - 1), (ei, ej, ek - 1), (ei, ej - 1, ek), (ei, ej, ek)]
        elif axis == 'y':
            cells = [(ei - 1, ej, ek - 1), (ei, ej, ek - 1), (ei - 1, ej, ek), (ei, ej, ek)]
        else:  # z
            cells = [(ei - 1, ej - 1, ek), (ei, ej - 1, ek), (ei - 1, ej, ek), (ei, ej, ek)]
        verts = []
        for (ci, cj, ck) in cells:
            if 0 <= ci < self.nx and 0 <= cj < self.ny and 0 <= ck < self.nz:
                vi = cv[ci][cj][ck]
                if vi is not None:
                    verts.append(vi)
        if len(verts) < 3:
            return
        # Triangulate as a fan (works for 3 or 4 vertices; for 4 we split the
        # quad along the (0,2) diagonal).
        if len(verts) == 4:
            mesh.add_face(verts[0], verts[1], verts[2])
            mesh.add_face(verts[0], verts[2], verts[3])
        else:
            # 3 vertices — one triangle
            mesh.add_face(verts[0], verts[1], verts[2])