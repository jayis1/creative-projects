"""
Polygon utilities: area, centroid, point-in-polygon, clipping (Sutherland-Hodgman),
and ear-clipping triangulation of simple polygons.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from .geometry import Point, orient2d


def polygon_area(poly: List[Point]) -> float:
    """Unsigned shoelace area of a polygon."""
    n = len(poly)
    if n < 3:
        return 0.0
    s = 0.0
    for i in range(n):
        j = (i + 1) % n
        s += poly[i].x * poly[j].y - poly[j].x * poly[i].y
    return abs(s) / 2.0


def polygon_centroid(poly: List[Point]) -> Point:
    """Area-weighted centroid of a simple polygon."""
    n = len(poly)
    if n == 0:
        raise ValueError("Empty polygon has no centroid")
    if n < 3:
        return Point(sum(p.x for p in poly) / n, sum(p.y for p in poly) / n)
    cx = 0.0
    cy = 0.0
    area2 = 0.0
    for i in range(n):
        j = (i + 1) % n
        cross = poly[i].x * poly[j].y - poly[j].x * poly[i].y
        cx += (poly[i].x + poly[j].x) * cross
        cy += (poly[i].y + poly[j].y) * cross
        area2 += cross
    area2 *= 0.5
    if abs(area2) < 1e-18:
        return Point(sum(p.x for p in poly) / n, sum(p.y for p in poly) / n)
    return Point(cx / (6.0 * area2), cy / (6.0 * area2))


def point_in_polygon(p: Point, poly: List[Point]) -> bool:
    """Ray-casting point-in-polygon test.

    Casts a horizontal ray from *p* to +x and counts edge crossings.
    An odd count means *p* is inside.
    """
    inside = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i].x, poly[i].y
        xj, yj = poly[j].x, poly[j].y
        if (yi > p.y) != (yj > p.y):
            x_cross = (xj - xi) * (p.y - yi) / (yj - yi) + xi
            if p.x < x_cross:
                inside = not inside
        j = i
    return inside


def sutherland_hodgman_clip(
    subject: List[Point], clip: List[Point]
) -> List[Point]:
    """Clip *subject* polygon against convex *clip* polygon.

    *clip* must be convex and given in consistent winding order (CW or CCW).
    """
    output = list(subject)
    cn = len(clip)
    # Determine clip winding
    clip_ccw = _signed_area(clip) > 0

    for i in range(cn):
        if not output:
            break
        input_list = output
        output = []
        a = clip[i]
        b = clip[(i + 1) % cn]
        # Inside test: point is inside if on the correct side of edge a→b
        def inside(pt: Point) -> bool:
            o = orient2d(a, b, pt)
            return o >= 0 if clip_ccw else o <= 0

        j = len(input_list)
        for k in range(j):
            cur = input_list[k]
            nxt = input_list[(k + 1) % j]
            cur_in = inside(cur)
            nxt_in = inside(nxt)
            if cur_in:
                output.append(cur)
                if not nxt_in:
                    inter = _ray_intersect(cur, nxt, a, b)
                    if inter is not None:
                        output.append(inter)
            else:
                if nxt_in:
                    inter = _ray_intersect(cur, nxt, a, b)
                    if inter is not None:
                        output.append(inter)
    return output


def _signed_area(poly: List[Point]) -> float:
    n = len(poly)
    s = 0.0
    for i in range(n):
        j = (i + 1) % n
        s += poly[i].x * poly[j].y - poly[j].x * poly[i].y
    return s / 2.0


def _ray_intersect(p1: Point, p2: Point, p3: Point, p4: Point) -> Optional[Point]:
    """Line-line intersection (infinite lines)."""
    x1, y1 = p1.x, p1.y
    x2, y2 = p2.x, p2.y
    x3, y3 = p3.x, p3.y
    x4, y4 = p4.x, p4.y
    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(denom) < 1e-18:
        return None
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
    return Point(x1 + t * (x2 - x1), y1 + t * (y2 - y1))


def ear_clip_triangulate(poly: List[Point]) -> List[Tuple[Point, Point, Point]]:
    """Triangulate a simple polygon via ear clipping.

    Returns a list of triangles (as 3-tuples of Points).  Handles both CW
    and CCW input by normalising to CCW first.
    """
    if len(poly) < 3:
        return []
    # Normalise to CCW
    pts = list(poly)
    if _signed_area(pts) < 0:
        pts.reverse()

    triangles: List[Tuple[Point, Point, Point]] = []
    indices = list(range(len(pts)))
    while len(indices) > 2:
        n = len(indices)
        ear_found = False
        for i in range(n):
            prev_i = indices[(i - 1) % n]
            cur_i = indices[i]
            next_i = indices[(i + 1) % n]
            a, b, c = pts[prev_i], pts[cur_i], pts[next_i]
            # Convex? (CCW → orientation > 0)
            if orient2d(a, b, c) <= 0:
                continue
            # No other vertex inside the triangle?
            is_ear = True
            for j in indices:
                if j in (prev_i, cur_i, next_i):
                    continue
                if point_in_polygon(pts[j], [a, b, c]):
                    is_ear = False
                    break
            if is_ear:
                triangles.append((a, b, c))
                del indices[i]
                ear_found = True
                break
        if not ear_found:
            # Degenerate / self-intersecting — bail out
            break
    return triangles