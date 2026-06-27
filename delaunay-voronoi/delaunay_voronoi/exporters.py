"""
Export utilities: OBJ mesh, PNG raster (via stdlib zlib), boundary extraction,
and STL-like ASCII mesh.

These let the toolkit interoperate with 3-D modelling software (Blender,
MeshLab) and image viewers without any external dependencies.
"""

from __future__ import annotations

import math
import struct
import zlib
from typing import Dict, List, Optional, Set, Tuple

from .delaunay import DelaunayTriangulation
from .geometry import Edge, Point, Triangle
from .convex_hull import convex_hull


# --------------------------------------------------------------------------- #
#  OBJ export
# --------------------------------------------------------------------------- #

def export_obj(dt: DelaunayTriangulation, z: float = 0.0) -> str:
    """Export a triangulation as a Wavefront OBJ string (2.5-D, z=0).

    Vertices are listed first, then faces (1-indexed).  Duplicate point
    objects are collapsed by coordinate so that the OBJ is minimal.
    """
    # Build a coordinate → index map
    index_map: Dict[Tuple[float, float], int] = {}
    vertices: List[Point] = []
    for p in dt.points:
        key = (p.x, p.y)
        if key not in index_map:
            index_map[key] = len(vertices) + 1  # OBJ is 1-indexed
            vertices.append(p)

    lines: List[str] = ["# Delaunay triangulation exported by delaunay-voronoi"]
    for v in vertices:
        lines.append(f"v {v.x:.6f} {v.y:.6f} {z:.6f}")

    # Faces — map each triangle vertex to its index
    for t in dt.triangles:
        idx = []
        for v in t.vertices():
            key = (v.x, v.y)
            idx.append(index_map.get(key, -1))
        if all(i > 0 for i in idx):
            lines.append(f"f {idx[0]} {idx[1]} {idx[2]}")

    return "\n".join(lines) + "\n"


def save_obj(dt: DelaunayTriangulation, path: str, z: float = 0.0) -> None:
    """Save a triangulation to *path* in OBJ format."""
    with open(path, "w") as f:
        f.write(export_obj(dt, z=z))


# --------------------------------------------------------------------------- #
#  ASCII STL (triangulation as a flat mesh)
# --------------------------------------------------------------------------- #

def export_ascii_stl(dt: DelaunayTriangulation, z: float = 0.0) -> str:
    """Export a triangulation as an ASCII STL string (flat mesh at z)."""
    lines: List[str] = ["solid delaunay_mesh"]
    for t in dt.triangles:
        a, b, c = t.vertices()
        # Compute normal (all z=0 → normal = (0, 0, 1) or (0, 0, -1))
        cross = (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x)
        nz = 1.0 if cross > 0 else -1.0
        lines.append(f"  facet normal 0.0 0.0 {nz:.6f}")
        lines.append("    outer loop")
        lines.append(f"      vertex {a.x:.6f} {a.y:.6f} {z:.6f}")
        lines.append(f"      vertex {b.x:.6f} {b.y:.6f} {z:.6f}")
        lines.append(f"      vertex {c.x:.6f} {c.y:.6f} {z:.6f}")
        lines.append("    endloop")
        lines.append("  endfacet")
    lines.append("endsolid delaunay_mesh")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- #
#  PNG export (pure stdlib via zlib)
# --------------------------------------------------------------------------- #

def export_png(
    width: int,
    height: int,
    pixels: bytes,
    path: str,
) -> None:
    """Write an RGB PNG file using only the standard library.

    *pixels* must be a bytes/bytearray of length ``width*height*3``
    (row-major, top-to-bottom, R G B per pixel).
    """
    if len(pixels) != width * height * 3:
        raise ValueError(
            f"Expected {width*height*3} bytes of pixel data, got {len(pixels)}"
        )

    def _chunk(chunk_type: bytes, data: bytes) -> bytes:
        c = chunk_type + data
        crc = zlib.crc32(c) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + c + struct.pack(">I", crc)

    # PNG signature
    sig = b"\x89PNG\r\n\x1a\n"

    # IHDR
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)  # 8-bit RGB

    # IDAT — raw scanlines with filter byte 0
    raw = bytearray()
    stride = width * 3
    for y in range(height):
        raw.append(0)  # filter type: None
        raw.extend(pixels[y * stride:(y + 1) * stride])
    compressed = zlib.compress(bytes(raw), level=9)

    # IEND
    png = sig + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", compressed) + _chunk(b"IEND", b"")

    with open(path, "wb") as f:
        f.write(png)


def render_png(
    width: int,
    height: int,
    points: List[Point],
    background: Tuple[int, int, int] = (15, 15, 23),
    point_color: Tuple[int, int, int] = (91, 192, 190),
    cell_colors: Optional[List[Tuple[int, int, int]]] = None,
    draw_points: bool = True,
) -> bytes:
    """Render a flat-shaded Voronoi diagram to RGB pixel bytes (for PNG).

    Uses a :class:`SpatialHashGrid` for O(k) nearest-site lookup instead
    of the O(n) brute force in ``render_ppm`` — typically 10-50× faster
    for large point sets.
    """
    from .spatial_hash import SpatialHashGrid

    if not points:
        return bytes(background) * (width * height)

    # Assign colours
    site_colors: Dict[Point, Tuple[int, int, int]] = {}
    for i, p in enumerate(points):
        if cell_colors and i < len(cell_colors):
            site_colors[p] = cell_colors[i]
        else:
            r = (i * 47) % 256
            g = (i * 113) % 256
            b = (i * 197) % 256
            site_colors[p] = (r, g, b)

    # Build spatial grid for fast nearest-neighbour
    grid = SpatialHashGrid.from_points(points)

    pixels = bytearray(width * height * 3)
    bg = bytes(background)
    # Flat-fill background
    for i in range(0, len(pixels), 3):
        pixels[i:i + 3] = bg

    for y in range(height):
        row = y * width * 3
        for x in range(width):
            nearest = grid.nearest(Point(float(x), float(y)))
            if nearest is not None:
                colour = site_colors[nearest]
                idx = row + x * 3
                pixels[idx] = colour[0]
                pixels[idx + 1] = colour[1]
                pixels[idx + 2] = colour[2]

    # Draw points on top
    if draw_points:
        for p in points:
            px, py = int(p.x), int(p.y)
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    nx, ny = px + dx, py + dy
                    if 0 <= nx < width and 0 <= ny < height:
                        idx = (ny * width + nx) * 3
                        pixels[idx:idx + 3] = bytes(point_color)

    return bytes(pixels)


def save_png(
    width: int,
    height: int,
    points: List[Point],
    path: str,
    background: Tuple[int, int, int] = (15, 15, 23),
    point_color: Tuple[int, int, int] = (91, 192, 190),
    cell_colors: Optional[List[Tuple[int, int, int]]] = None,
) -> None:
    """Render and save a Voronoi PNG in one call."""
    pixels = render_png(width, height, points, background, point_color, cell_colors)
    export_png(width, height, pixels, path)


# --------------------------------------------------------------------------- #
#  Boundary extraction
# --------------------------------------------------------------------------- #

def extract_boundary_edges(dt: DelaunayTriangulation) -> List[Edge]:
    """Return the boundary (hull) edges of a triangulation.

    A boundary edge is one shared by exactly one triangle.
    """
    edge_count: Dict[Edge, int] = {}
    for t in dt.triangles:
        for e in t.edges():
            edge_count[e] = edge_count.get(e, 0) + 1
    return [e for e, c in edge_count.items() if c == 1]


def extract_boundary_loops(dt: DelaunayTriangulation) -> List[List[Point]]:
    """Extract ordered boundary loops from a triangulation.

    Each loop is a list of Points in traversal order.  For a simply-
    connected mesh there is one loop (the convex hull boundary); for a
    mesh with holes there will be multiple loops.
    """
    boundary = extract_boundary_edges(dt)
    if not boundary:
        return []

    # Build adjacency from boundary edges
    adj: Dict[Point, List[Point]] = {}
    for e in boundary:
        adj.setdefault(e.a, []).append(e.b)
        adj.setdefault(e.b, []).append(e.a)

    visited_edges: Set[Tuple[Tuple[float, float], Tuple[float, float]]] = set()
    loops: List[List[Point]] = []

    for start in adj:
        if any(start in loop for loop in loops):
            continue
        loop: List[Point] = [start]
        current = start
        prev: Optional[Point] = None
        while True:
            neighbours = adj.get(current, [])
            next_node: Optional[Point] = None
            for nb in neighbours:
                if nb == prev:
                    continue
                ca = (current.x, current.y)
                na = (nb.x, nb.y)
                edge_key = (ca, na) if ca <= na else (na, ca)
                if edge_key not in visited_edges:
                    next_node = nb
                    visited_edges.add(edge_key)
                    break
            if next_node is None:
                break
            if next_node == start:
                break
            loop.append(next_node)
            prev = current
            current = next_node
        if len(loop) >= 3:
            loops.append(loop)

    return loops