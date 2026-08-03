"""Volume-data sampler: mesh a 3-D scalar field given as a nested list.

This allows the toolkit to mesh arbitrary volumetric data (e.g. medical CT
scans, simulation output) without an analytic function.  The field is
trilinearly interpolated from the grid samples.
"""

from __future__ import annotations

from typing import List, Sequence, Tuple

from .samplers import Sampler


class VolumeSampler(Sampler):
    """Mesh a 3-D scalar field provided as a nested list ``data[i][j][k]``.

    The field is trilinearly interpolated between grid nodes.  The grid spans
    the bounding box ``(0,0,0)`` to ``(nx-1, ny-1, nz-1)`` in index space, and
    is mapped to the physical ``bounds`` region.
    """

    def __init__(self, data: Sequence[Sequence[Sequence[float]]],
                 bounds: Tuple[Tuple[float, float, float], Tuple[float, float, float]] = ((0.0, 0.0, 0.0), (1.0, 1.0, 1.0))):
        self.data = data
        self.nx = len(data)
        self.ny = len(data[0]) if self.nx else 0
        self.nz = len(data[0][0]) if self.ny else 0
        (self.x0, self.y0, self.z0), (self.x1, self.y1, self.z1) = bounds
        if self.nx < 2 or self.ny < 2 or self.nz < 2:
            raise ValueError("VolumeSampler needs at least a 2×2×2 grid")

    def sample(self, x: float, y: float, z: float) -> float:
        # Map physical coordinates to index space
        fi = (x - self.x0) / (self.x1 - self.x0) * (self.nx - 1)
        fj = (y - self.y0) / (self.y1 - self.y0) * (self.ny - 1)
        fk = (z - self.z0) / (self.z1 - self.z0) * (self.nz - 1)
        # Clamp
        fi = max(0.0, min(self.nx - 1.001, fi))
        fj = max(0.0, min(self.ny - 1.001, fj))
        fk = max(0.0, min(self.nz - 1.001, fk))
        i0 = int(fi); j0 = int(fj); k0 = int(fk)
        di = fi - i0; dj = fj - j0; dk = fk - k0
        # Trilinear interpolation
        d = self.data
        v000 = d[i0][j0][k0]
        v001 = d[i0][j0][k0 + 1]
        v010 = d[i0][j0 + 1][k0]
        v011 = d[i0][j0 + 1][k0 + 1]
        v100 = d[i0 + 1][j0][k0]
        v101 = d[i0 + 1][j0][k0 + 1]
        v110 = d[i0 + 1][j0 + 1][k0]
        v111 = d[i0 + 1][j0 + 1][k0 + 1]
        c00 = v000 * (1 - dk) + v001 * dk
        c01 = v010 * (1 - dk) + v011 * dk
        c10 = v100 * (1 - dk) + v101 * dk
        c11 = v110 * (1 - dk) + v111 * dk
        c0 = c00 * (1 - dj) + c01 * dj
        c1 = c10 * (1 - dj) + c11 * dj
        return c0 * (1 - di) + c1 * di

    def gradient(self, x: float, y: float, z: float) -> Tuple[float, float, float]:
        h = 0.01
        fx = self.sample(x + h, y, z) - self.sample(x - h, y, z)
        fy = self.sample(x, y + h, z) - self.sample(x, y - h, z)
        fz = self.sample(x, y, z + h) - self.sample(x, y, z - h)
        return (fx / (2 * h), fy / (2 * h), fz / (2 * h))