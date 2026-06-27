"""
Mesh quality metrics and reporting.

Provides detailed analysis of a triangulation:
  * Minimum / maximum / mean angle per triangle and globally
  * Area distribution (min, max, mean, total)
  * Edge-length statistics
  * Aspect-ratio and radius-ratio quality measures
  * Histograms (binned) for angle and area distributions
  * A human-readable text report
  * A machine-readable JSON report

All metrics are computed in pure Python with no external dependencies.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .delaunay import DelaunayTriangulation
from .geometry import Point, Triangle
from .refine import _min_angle_sin_ratio


@dataclass
class AngleStats:
    """Statistics over the three interior angles of every triangle."""
    min_deg: float
    max_deg: float
    mean_deg: float
    median_deg: float
    std_deg: float
    min_angle_count_below_threshold: int = 0


@dataclass
class AreaStats:
    """Statistics over triangle areas."""
    min: float
    max: float
    mean: float
    median: float
    std: float
    total: float


@dataclass
class EdgeStats:
    """Statistics over unique edge lengths."""
    min: float
    max: float
    mean: float
    median: float
    std: float
    count: int


@dataclass
class MeshReport:
    """A full quality report for a triangulation."""
    num_points: int
    num_triangles: int
    num_edges: int
    num_hull_vertices: int
    angle_stats: AngleStats
    area_stats: AreaStats
    edge_stats: EdgeStats
    min_radius_ratio: float  # in [0, 1], 1 = equilateral
    min_aspect_ratio: float  # 2*r_in / r_out, 1 = equilateral
    angle_histogram: Dict[str, int] = field(default_factory=dict)
    area_histogram: Dict[str, int] = field(default_factory=dict)

    # ----- serialisation -----

    def to_dict(self) -> Dict[str, object]:
        return {
            "num_points": self.num_points,
            "num_triangles": self.num_triangles,
            "num_edges": self.num_edges,
            "num_hull_vertices": self.num_hull_vertices,
            "angle_stats": {
                "min_deg": self.angle_stats.min_deg,
                "max_deg": self.angle_stats.max_deg,
                "mean_deg": self.angle_stats.mean_deg,
                "median_deg": self.angle_stats.median_deg,
                "std_deg": self.angle_stats.std_deg,
                "count_below_20deg": self.angle_stats.min_angle_count_below_threshold,
            },
            "area_stats": {
                "min": self.area_stats.min,
                "max": self.area_stats.max,
                "mean": self.area_stats.mean,
                "median": self.area_stats.median,
                "std": self.area_stats.std,
                "total": self.area_stats.total,
            },
            "edge_stats": {
                "min": self.edge_stats.min,
                "max": self.edge_stats.max,
                "mean": self.edge_stats.mean,
                "median": self.edge_stats.median,
                "std": self.edge_stats.std,
                "count": self.edge_stats.count,
            },
            "min_radius_ratio": self.min_radius_ratio,
            "min_aspect_ratio": self.min_aspect_ratio,
            "angle_histogram": self.angle_histogram,
            "area_histogram": self.area_histogram,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    # ----- text report -----

    def to_text(self) -> str:
        lines: List[str] = []
        lines.append("=" * 60)
        lines.append("  MESH QUALITY REPORT")
        lines.append("=" * 60)
        lines.append("")
        lines.append(f"  Points:          {self.num_points}")
        lines.append(f"  Triangles:       {self.num_triangles}")
        lines.append(f"  Edges:           {self.num_edges}")
        lines.append(f"  Hull vertices:   {self.num_hull_vertices}")
        lines.append("")
        lines.append("-" * 60)
        lines.append("  ANGLE STATISTICS (degrees)")
        lines.append("-" * 60)
        a = self.angle_stats
        lines.append(f"  Minimum:         {a.min_deg:8.2f}°")
        lines.append(f"  Maximum:         {a.max_deg:8.2f}°")
        lines.append(f"  Mean:            {a.mean_deg:8.2f}°")
        lines.append(f"  Median:          {a.median_deg:8.2f}°")
        lines.append(f"  Std dev:         {a.std_deg:8.2f}°")
        lines.append(f"  Angles < 20°:    {a.min_angle_count_below_threshold}")
        lines.append("")
        if self.angle_histogram:
            lines.append("  Angle histogram:")
            for label, count in sorted(self.angle_histogram.items()):
                bar = "█" * min(count, 50)
                lines.append(f"    {label:>12s} : {count:4d} {bar}")
            lines.append("")
        lines.append("-" * 60)
        lines.append("  AREA STATISTICS")
        lines.append("-" * 60)
        ar = self.area_stats
        lines.append(f"  Minimum:         {ar.min:12.4f}")
        lines.append(f"  Maximum:         {ar.max:12.4f}")
        lines.append(f"  Mean:            {ar.mean:12.4f}")
        lines.append(f"  Median:          {ar.median:12.4f}")
        lines.append(f"  Std dev:         {ar.std:12.4f}")
        lines.append(f"  Total:           {ar.total:12.4f}")
        lines.append("")
        lines.append("-" * 60)
        lines.append("  EDGE LENGTH STATISTICS")
        lines.append("-" * 60)
        e = self.edge_stats
        lines.append(f"  Minimum:         {e.min:12.4f}")
        lines.append(f"  Maximum:         {e.max:12.4f}")
        lines.append(f"  Mean:            {e.mean:12.4f}")
        lines.append(f"  Median:          {e.median:12.4f}")
        lines.append(f"  Std dev:         {e.std:12.4f}")
        lines.append(f"  Count:           {e.count}")
        lines.append("")
        lines.append("-" * 60)
        lines.append("  QUALITY MEASURES")
        lines.append("-" * 60)
        lines.append(f"  Min radius ratio:    {self.min_radius_ratio:.4f}  (1.0 = equilateral)")
        lines.append(f"  Min aspect ratio:    {self.min_aspect_ratio:.4f}  (1.0 = equilateral)")
        lines.append("")
        # Quality grade
        if self.min_radius_ratio > 0.5 and a.min_deg > 30:
            grade = "A (excellent)"
        elif self.min_radius_ratio > 0.3 and a.min_deg > 20:
            grade = "B (good)"
        elif self.min_radius_ratio > 0.15 and a.min_deg > 10:
            grade = "C (fair)"
        else:
            grade = "D (poor — needs refinement)"
        lines.append(f"  Overall grade:        {grade}")
        lines.append("=" * 60)
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _median(values: List[float]) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    n = len(s)
    mid = n // 2
    if n % 2 == 1:
        return s[mid]
    return (s[mid - 1] + s[mid]) / 2.0


def _std(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0
    m = _mean(values)
    var = sum((v - m) ** 2 for v in values) / len(values)
    return math.sqrt(var)


def _triangle_angles(t: Triangle) -> Tuple[float, float, float]:
    """Return the three interior angles of *t* in radians."""
    a, b, c = t.vertices()
    lab = a.distance_to(b)
    lbc = b.distance_to(c)
    lca = c.distance_to(a)
    # Law of cosines
    def angle(opposite: float, s1: float, s2: float) -> float:
        if s1 < 1e-18 or s2 < 1e-18:
            return 0.0
        cos_a = (s1 * s1 + s2 * s2 - opposite * opposite) / (2.0 * s1 * s2)
        cos_a = max(-1.0, min(1.0, cos_a))
        return math.acos(cos_a)
    ang_a = angle(lbc, lab, lca)  # at vertex a
    ang_b = angle(lca, lab, lbc)  # at vertex b
    ang_c = angle(lab, lbc, lca)  # at vertex c
    return ang_a, ang_b, ang_c


def _inradius(t: Triangle) -> float:
    """Radius of the inscribed circle."""
    a, b, c = t.vertices()
    lab = a.distance_to(b)
    lbc = b.distance_to(c)
    lca = c.distance_to(a)
    s = (lab + lbc + lca) / 2.0
    area = t.area()
    if s < 1e-18:
        return 0.0
    return area / s


def _circumradius(t: Triangle) -> float:
    """Radius of the circumscribed circle."""
    cc = t.circumcircle()
    return cc.radius


def _radius_ratio(t: Triangle) -> float:
    """Radius ratio = 2 * r_in / r_out ∈ [0, 1]. 1 = equilateral."""
    r_in = _inradius(t)
    r_out = _circumradius(t)
    if r_out < 1e-18:
        return 0.0
    return 2.0 * r_in / r_out


def _aspect_ratio(t: Triangle) -> float:
    """Edge-ratio quality = shortest_edge / longest_edge ∈ (0, 1].

    1.0 = equilateral, smaller = skinnier.  This is a normalised quality
    measure (higher is better), unlike the traditional aspect ratio where
    larger is worse.
    """
    a, b, c = t.vertices()
    lengths = [a.distance_to(b), b.distance_to(c), c.distance_to(a)]
    longest = max(lengths)
    shortest = min(lengths)
    if longest < 1e-18:
        return 0.0
    return shortest / longest


def _histogram(values: List[float], bins: int = 10,
               lo: Optional[float] = None,
               hi: Optional[float] = None) -> Dict[str, int]:
    """Build a labelled histogram with *bins* buckets."""
    if not values:
        return {}
    if lo is None:
        lo = min(values)
    if hi is None:
        hi = max(values)
    if hi <= lo:
        return {f"[{lo:.1f}]": len(values)}
    step = (hi - lo) / bins
    counts: Dict[str, int] = {}
    for i in range(bins):
        edge_lo = lo + i * step
        edge_hi = lo + (i + 1) * step
        if i == bins - 1:
            label = f"[{edge_lo:.1f}, {edge_hi:.1f}]"
        else:
            label = f"[{edge_lo:.1f}, {edge_hi:.1f})"
        counts[label] = 0
    for v in values:
        idx = int((v - lo) / step)
        idx = max(0, min(bins - 1, idx))
        key = list(counts.keys())[idx]
        counts[key] += 1
    return counts


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_mesh_report(
    dt: DelaunayTriangulation,
    hull_vertices: Optional[int] = None,
    angle_threshold_deg: float = 20.0,
    angle_bins: int = 9,
    area_bins: int = 10,
) -> MeshReport:
    """Compute a comprehensive :class:`MeshReport` for *dt*."""
    triangles = dt.triangles
    edges = dt.edges()

    # Angle statistics — collect all 3*n angles
    all_angles_rad: List[float] = []
    min_angles_rad: List[float] = []
    for t in triangles:
        angles = _triangle_angles(t)
        all_angles_rad.extend(angles)
        min_angles_rad.append(min(angles))

    all_angles_deg = [math.degrees(a) for a in all_angles_rad]
    min_angles_deg = [math.degrees(a) for a in min_angles_rad]

    threshold_rad = math.radians(angle_threshold_deg)
    count_below = sum(1 for a in min_angles_rad if a < threshold_rad)

    angle_stats = AngleStats(
        min_deg=min(min_angles_deg) if min_angles_deg else 0.0,
        max_deg=max(all_angles_deg) if all_angles_deg else 0.0,
        mean_deg=_mean(all_angles_deg),
        median_deg=_median(all_angles_deg),
        std_deg=_std(all_angles_deg),
        min_angle_count_below_threshold=count_below,
    )

    # Area statistics
    areas = [t.area() for t in triangles]
    area_stats = AreaStats(
        min=min(areas) if areas else 0.0,
        max=max(areas) if areas else 0.0,
        mean=_mean(areas),
        median=_median(areas),
        std=_std(areas),
        total=sum(areas),
    )

    # Edge length statistics
    edge_lengths = [e.a.distance_to(e.b) for e in edges]
    edge_stats = EdgeStats(
        min=min(edge_lengths) if edge_lengths else 0.0,
        max=max(edge_lengths) if edge_lengths else 0.0,
        mean=_mean(edge_lengths),
        median=_median(edge_lengths),
        std=_std(edge_lengths),
        count=len(edge_lengths),
    )

    # Quality measures
    radius_ratios = [_radius_ratio(t) for t in triangles]
    aspect_ratios = [_aspect_ratio(t) for t in triangles]
    # Both are ∈ (0, 1] with 1 = equilateral; higher is better.

    # Histograms
    angle_hist = _histogram(min_angles_deg, bins=angle_bins, lo=0, hi=60)
    area_hist = _histogram(areas, bins=area_bins)

    return MeshReport(
        num_points=len(dt.points),
        num_triangles=len(triangles),
        num_edges=len(edges),
        num_hull_vertices=hull_vertices if hull_vertices is not None else 0,
        angle_stats=angle_stats,
        area_stats=area_stats,
        edge_stats=edge_stats,
        min_radius_ratio=min(radius_ratios) if radius_ratios else 0.0,
        min_aspect_ratio=min(aspect_ratios) if aspect_ratios else 0.0,
        angle_histogram=angle_hist,
        area_histogram=area_hist,
    )