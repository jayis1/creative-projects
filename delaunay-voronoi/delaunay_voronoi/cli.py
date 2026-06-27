#!/usr/bin/env python3
"""Command-line interface for the Delaunay-Voronoi toolkit.

Subcommands:
  diagram    Generate a Delaunay/Voronoi SVG from random points
  animate    Generate an animated SVG of Lloyd relaxation
  refine     Ruppert's quality mesh refinement
  voronoi    Flat-shaded Voronoi PPM raster
  info       Print triangulation statistics
  json       Save triangulation as JSON
"""

from __future__ import annotations

import argparse
import os
import sys

from .delaunay import DelaunayTriangulation
from .geometry import Point
from .lloyd import generate_poisson_seed, lloyd_relaxation
from .voronoi import VoronoiDiagram
from .render import render_svg, render_ppm
from .animate import render_lloyd_animation
from .refine import ruppert_refine
from .convex_hull import convex_hull
from .serialize import save_json, triangulation_to_dict
from .spatial import nearest_neighbor, locate_point


def _build_common_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("-n", "--num-points", type=int, default=30, help="Number of random sites.")
    p.add_argument("-w", "--width", type=int, default=800, help="Image width (px).")
    p.add_argument("--height", type=int, default=600, help="Image height (px).")
    p.add_argument("--seed", type=int, default=42, help="Random seed.")


def _make_points(args) -> tuple[list[Point], tuple[Point, Point]]:
    box = (Point(0, 0), Point(args.width, args.height))
    pts = generate_poisson_seed(args.num_points, box, seed=args.seed)
    return pts, box


def cmd_diagram(args) -> None:
    pts, box = _make_points(args)
    if args.lloyd > 0:
        pts = lloyd_relaxation(pts, iterations=args.lloyd, clip_box=box, seed=args.seed)
    dt = DelaunayTriangulation.from_points(pts)
    vd = VoronoiDiagram.from_delaunay(dt, clip_box=box)
    hull = convex_hull(pts)
    svg = render_svg(
        width=args.width, height=args.height,
        delaunay_edges=dt.edges(), voronoi_edges=vd.edges,
        points=pts, hull=hull,
        show_delaunay=not args.no_delaunay, show_voronoi=not args.no_voronoi,
    )
    with open(args.output, "w") as f:
        f.write(svg)
    print(f"Generated {len(pts)} points, {len(dt.triangles)} triangles, "
          f"{len(vd.edges)} Voronoi edges, hull has {len(hull)} vertices.")
    print(f"Saved to {args.output}")


def cmd_animate(args) -> None:
    pts, box = _make_points(args)
    svg = render_lloyd_animation(
        pts, iterations=args.lloyd, width=args.width, height=args.height,
        frame_duration_ms=args.frame_ms, seed=args.seed,
    )
    with open(args.output, "w") as f:
        f.write(svg)
    print(f"Animated SVG ({args.lloyd} Lloyd iterations) saved to {args.output}")


def cmd_refine(args) -> None:
    pts, box = _make_points(args)
    refined = ruppert_refine(pts, min_angle_deg=args.min_angle, max_area=args.max_area)
    dt = DelaunayTriangulation.from_points(refined)
    vd = VoronoiDiagram.from_delaunay(dt, clip_box=box)
    svg = render_svg(
        width=args.width, height=args.height,
        delaunay_edges=dt.edges(), voronoi_edges=vd.edges,
        points=refined, show_voronoi=False,
    )
    with open(args.output, "w") as f:
        f.write(svg)
    print(f"Refined to {len(refined)} points, {len(dt.triangles)} triangles "
          f"(min angle target {args.min_angle}°). Saved to {args.output}")


def cmd_voronoi_ppm(args) -> None:
    pts, box = _make_points(args)
    data = render_ppm(width=args.width, height=args.height, points=pts)
    with open(args.output, "wb") as f:
        f.write(data)
    print(f"Flat-shaded Voronoi PPM ({len(pts)} sites) saved to {args.output}")


def cmd_info(args) -> None:
    pts, box = _make_points(args)
    dt = DelaunayTriangulation.from_points(pts)
    vd = VoronoiDiagram.from_delaunay(dt, clip_box=box)
    hull = convex_hull(pts)
    print(f"Points:        {len(pts)}")
    print(f"Triangles:     {len(dt.triangles)}")
    print(f"Delaunay edges:{len(dt.edges())}")
    print(f"Voronoi edges: {len(vd.edges)}")
    print(f"Voronoi cells: {len(vd.cells)}")
    print(f"Hull vertices: {len(hull)}")
    # Min angle stats
    import math
    from .refine import _min_angle_sin_ratio
    if dt.triangles:
        ratios = [_min_angle_sin_ratio(t) for t in dt.triangles]
        min_deg = math.degrees(math.asin(min(max(min(ratios), 0.0), 1.0)))
        avg_deg = math.degrees(math.asin(sum(ratios) / len(ratios)))
        print(f"Min angle:     {min_deg:.1f}°")
        print(f"Avg min-angle: {avg_deg:.1f}°")


def cmd_json(args) -> None:
    pts, box = _make_points(args)
    dt = DelaunayTriangulation.from_points(pts)
    save_json(triangulation_to_dict(dt), args.output)
    print(f"Triangulation JSON saved to {args.output}")


def cmd_nearest(args) -> None:
    pts, box = _make_points(args)
    dt = DelaunayTriangulation.from_points(pts)
    q = Point(args.x, args.y)
    nn = nearest_neighbor(dt, q)
    loc = locate_point(dt, q)
    print(f"Query: ({q.x}, {q.y})")
    print(f"Nearest site: ({nn.x:.4f}, {nn.y:.4f}), distance={nn.distance_to(q):.4f}")
    if loc:
        print(f"Containing triangle: ({loc.a.x:.2f},{loc.a.y:.2f}) "
              f"({loc.b.x:.2f},{loc.b.y:.2f}) ({loc.c.x:.2f},{loc.c.y:.2f})")
    else:
        print("Query is outside the convex hull.")


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="delaunay-voronoi",
        description="Computational geometry toolkit: Delaunay, Voronoi, Lloyd, Ruppert.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # diagram
    p = sub.add_parser("diagram", help="Generate Delaunay/Voronoi SVG.")
    _build_common_args(p)
    p.add_argument("--lloyd", type=int, default=0, help="Lloyd relaxation iterations.")
    p.add_argument("-o", "--output", default="diagram.svg")
    p.add_argument("--no-voronoi", action="store_true")
    p.add_argument("--no-delaunay", action="store_true")
    p.set_defaults(func=cmd_diagram)

    # animate
    p = sub.add_parser("animate", help="Animated SVG of Lloyd relaxation.")
    _build_common_args(p)
    p.add_argument("--lloyd", type=int, default=8, help="Lloyd iterations.")
    p.add_argument("--frame-ms", type=int, default=600, help="Frame duration (ms).")
    p.add_argument("-o", "--output", default="animation.svg")
    p.set_defaults(func=cmd_animate)

    # refine
    p = sub.add_parser("refine", help="Ruppert's quality mesh refinement.")
    _build_common_args(p)
    p.add_argument("--min-angle", type=float, default=30.0, help="Min triangle angle (degrees).")
    p.add_argument("--max-area", type=float, default=None, help="Max triangle area.")
    p.add_argument("-o", "--output", default="refined.svg")
    p.set_defaults(func=cmd_refine)

    # voronoi ppm
    p = sub.add_parser("ppm", help="Flat-shaded Voronoi PPM raster.")
    _build_common_args(p)
    p.add_argument("-o", "--output", default="voronoi.ppm")
    p.set_defaults(func=cmd_voronoi_ppm)

    # info
    p = sub.add_parser("info", help="Print triangulation statistics.")
    _build_common_args(p)
    p.set_defaults(func=cmd_info)

    # json
    p = sub.add_parser("json", help="Save triangulation as JSON.")
    _build_common_args(p)
    p.add_argument("-o", "--output", default="triangulation.json")
    p.set_defaults(func=cmd_json)

    # nearest
    p = sub.add_parser("nearest", help="Find nearest site to a query point.")
    _build_common_args(p)
    p.add_argument("--x", type=float, required=True, help="Query x.")
    p.add_argument("--y", type=float, required=True, help="Query y.")
    p.set_defaults(func=cmd_nearest)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()