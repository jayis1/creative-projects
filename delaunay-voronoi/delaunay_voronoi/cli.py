#!/usr/bin/env python3
"""Command-line interface for the Delaunay-Voronoi toolkit.

Subcommands:
  diagram     Generate a Delaunay/Voronoi SVG from random points
  animate     Generate an animated SVG of Lloyd relaxation
  refine      Ruppert's quality mesh refinement
  ppm         Flat-shaded Voronoi PPM raster
  png         Flat-shaded Voronoi PNG raster (stdlib zlib, no deps)
  info        Print triangulation statistics
  mesh-stats  Detailed mesh quality report (angles, areas, quality)
  json        Save triangulation as JSON
  from-json   Render a diagram from a previously saved JSON triangulation
  nearest     Find nearest site to a query point
  obj         Export triangulation as Wavefront OBJ
  stl         Export triangulation as ASCII STL
  boundary    Extract and report boundary edges/loops
  compare     Side-by-side SVG: before vs after Lloyd relaxation
  config      Generate a default config file (JSON or TOML)

Global options:
  --config PATH    Load algorithm/render defaults from a config file
  --log-level L    Set logging level (DEBUG, INFO, WARNING, ERROR)
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Optional

from .delaunay import DelaunayTriangulation
from .geometry import Point
from .lloyd import generate_poisson_seed, lloyd_relaxation
from .voronoi import VoronoiDiagram
from .render import render_svg, render_ppm
from .animate import render_lloyd_animation
from .refine import ruppert_refine
from .convex_hull import convex_hull
from .serialize import save_json, load_json, triangulation_to_dict, triangulation_from_dict
from .spatial import nearest_neighbor, locate_point, k_nearest_neighbors
from .metrics import compute_mesh_report
from .exporters import (
    save_obj, export_ascii_stl, save_png,
    extract_boundary_edges, extract_boundary_loops,
)
from .config import Config, load_config, save_config
from .logging_utils import get_logger

log = get_logger("cli")


# --------------------------------------------------------------------------- #
#  Shared helpers
# --------------------------------------------------------------------------- #

def _build_common_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("-n", "--num-points", type=int, default=30,
                   help="Number of random sites.")
    p.add_argument("-w", "--width", type=int, default=800,
                   help="Image width (px).")
    p.add_argument("--height", type=int, default=600,
                   help="Image height (px).")
    p.add_argument("--seed", type=int, default=42, help="Random seed.")


def _apply_config(args) -> Config:
    """Load a config file if --config was given, and merge with CLI args."""
    config = Config()
    if getattr(args, "config", None):
        try:
            config = load_config(args.config)
            log.info("Loaded config from %s", args.config)
        except Exception as e:
            log.warning("Failed to load config %s: %s", args.config, e)
    # CLI overrides config
    if hasattr(args, "num_points") and args.num_points == 30 and config.algorithm.num_points != 30:
        args.num_points = config.algorithm.num_points
    if hasattr(args, "seed") and args.seed == 42 and config.algorithm.seed != 42:
        args.seed = config.algorithm.seed
    return config


def _make_points(args, config: Optional[Config] = None) -> tuple[list[Point], tuple[Point, Point]]:
    box = (Point(0, 0), Point(args.width, args.height))
    pts = generate_poisson_seed(args.num_points, box, seed=args.seed)
    return pts, box


# --------------------------------------------------------------------------- #
#  Subcommand implementations
# --------------------------------------------------------------------------- #

def cmd_diagram(args) -> None:
    config = _apply_config(args)
    pts, box = _make_points(args, config)
    if args.lloyd > 0:
        log.info("Running %d Lloyd relaxation iterations", args.lloyd)
        pts = lloyd_relaxation(pts, iterations=args.lloyd, clip_box=box, seed=args.seed)
    dt = DelaunayTriangulation.from_points(pts)
    vd = VoronoiDiagram.from_delaunay(dt, clip_box=box)
    hull = convex_hull(pts)
    svg = render_svg(
        width=args.width, height=args.height,
        delaunay_edges=dt.edges(), voronoi_edges=vd.edges,
        points=pts, hull=hull,
        show_delaunay=not args.no_delaunay, show_voronoi=not args.no_voronoi,
        background=config.render.background,
        delaunay_color=config.render.delaunay_color,
        voronoi_color=config.render.voronoi_color,
        point_color=config.render.point_color,
        hull_color=config.render.hull_color,
    )
    with open(args.output, "w") as f:
        f.write(svg)
    log.info("Generated %d points, %d triangles, %d Voronoi edges, hull %d vertices",
             len(pts), len(dt.triangles), len(vd.edges), len(hull))
    print(f"Generated {len(pts)} points, {len(dt.triangles)} triangles, "
          f"{len(vd.edges)} Voronoi edges, hull has {len(hull)} vertices.")
    print(f"Saved to {args.output}")


def cmd_animate(args) -> None:
    config = _apply_config(args)
    pts, box = _make_points(args, config)
    svg = render_lloyd_animation(
        pts, iterations=args.lloyd, width=args.width, height=args.height,
        frame_duration_ms=args.frame_ms, seed=args.seed,
    )
    with open(args.output, "w") as f:
        f.write(svg)
    print(f"Animated SVG ({args.lloyd} Lloyd iterations) saved to {args.output}")


def cmd_refine(args) -> None:
    config = _apply_config(args)
    pts, box = _make_points(args, config)
    log.info("Running Ruppert refinement (min_angle=%.1f°, max_area=%s)",
             args.min_angle, args.max_area)
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
    config = _apply_config(args)
    pts, box = _make_points(args, config)
    data = render_ppm(width=args.width, height=args.height, points=pts)
    with open(args.output, "wb") as f:
        f.write(data)
    print(f"Flat-shaded Voronoi PPM ({len(pts)} sites) saved to {args.output}")


def cmd_voronoi_png(args) -> None:
    config = _apply_config(args)
    pts, box = _make_points(args, config)
    log.info("Rendering PNG (%dx%d, %d sites) via spatial-hash acceleration",
             args.width, args.height, len(pts))
    save_png(args.width, args.height, pts, args.output)
    print(f"Flat-shaded Voronoi PNG ({len(pts)} sites) saved to {args.output}")


def cmd_info(args) -> None:
    config = _apply_config(args)
    pts, box = _make_points(args, config)
    dt = DelaunayTriangulation.from_points(pts)
    vd = VoronoiDiagram.from_delaunay(dt, clip_box=box)
    hull = convex_hull(pts)
    print(f"Points:        {len(pts)}")
    print(f"Triangles:     {len(dt.triangles)}")
    print(f"Delaunay edges:{len(dt.edges())}")
    print(f"Voronoi edges: {len(vd.edges)}")
    print(f"Voronoi cells: {len(vd.cells)}")
    print(f"Hull vertices: {len(hull)}")
    import math
    from .refine import _min_angle_sin_ratio
    if dt.triangles:
        ratios = [_min_angle_sin_ratio(t) for t in dt.triangles]
        min_deg = math.degrees(math.asin(min(max(min(ratios), 0.0), 1.0)))
        avg_deg = math.degrees(math.asin(sum(ratios) / len(ratios)))
        print(f"Min angle:     {min_deg:.1f}°")
        print(f"Avg min-angle: {avg_deg:.1f}°")


def cmd_mesh_stats(args) -> None:
    """Print a detailed mesh quality report."""
    config = _apply_config(args)
    pts, box = _make_points(args, config)
    dt = DelaunayTriangulation.from_points(pts)
    hull = convex_hull(pts)
    report = compute_mesh_report(dt, hull_vertices=len(hull))
    if args.json:
        with open(args.output, "w") as f:
            f.write(report.to_json())
        print(f"Mesh report (JSON) saved to {args.output}")
    else:
        print(report.to_text())


def cmd_json(args) -> None:
    config = _apply_config(args)
    pts, box = _make_points(args, config)
    dt = DelaunayTriangulation.from_points(pts)
    save_json(triangulation_to_dict(dt), args.output)
    print(f"Triangulation JSON saved to {args.output}")


def cmd_from_json(args) -> None:
    """Render an SVG from a previously saved JSON triangulation."""
    data = load_json(args.input)
    dt = triangulation_from_dict(data)
    pts = dt.points
    if not pts:
        print("No points in JSON file.")
        return
    # Compute bounding box for Voronoi clipping
    from .geometry import bounding_box
    box = bounding_box(pts)
    # Expand slightly
    margin = 10
    box = (Point(box[0].x - margin, box[0].y - margin),
           Point(box[1].x + margin, box[1].y + margin))
    vd = VoronoiDiagram.from_delaunay(dt, clip_box=box)
    hull = convex_hull(pts)
    svg = render_svg(
        width=int(box[1].x), height=int(box[1].y),
        delaunay_edges=dt.edges(), voronoi_edges=vd.edges,
        points=pts, hull=hull,
    )
    with open(args.output, "w") as f:
        f.write(svg)
    print(f"Rendered {len(pts)} points, {len(dt.triangles)} triangles from JSON.")
    print(f"Saved to {args.output}")


def cmd_nearest(args) -> None:
    config = _apply_config(args)
    pts, box = _make_points(args, config)
    dt = DelaunayTriangulation.from_points(pts)
    q = Point(args.x, args.y)
    nn = nearest_neighbor(dt, q)
    loc = locate_point(dt, q)
    print(f"Query: ({q.x}, {q.y})")
    print(f"Nearest site: ({nn.x:.4f}, {nn.y:.4f}), distance={nn.distance_to(q):.4f}")
    if args.knn:
        knn = k_nearest_neighbors(dt, q, args.knn)
        print(f"k-NN (k={args.knn}):")
        for i, p in enumerate(knn):
            print(f"  {i+1}. ({p.x:.4f}, {p.y:.4f}) distance={p.distance_to(q):.4f}")
    if loc:
        print(f"Containing triangle: ({loc.a.x:.2f},{loc.a.y:.2f}) "
              f"({loc.b.x:.2f},{loc.b.y:.2f}) ({loc.c.x:.2f},{loc.c.y:.2f})")
    else:
        print("Query is outside the convex hull.")


def cmd_obj(args) -> None:
    """Export triangulation as OBJ."""
    config = _apply_config(args)
    pts, box = _make_points(args, config)
    dt = DelaunayTriangulation.from_points(pts)
    save_obj(dt, args.output)
    print(f"OBJ mesh ({len(pts)} points, {len(dt.triangles)} triangles) saved to {args.output}")


def cmd_stl(args) -> None:
    """Export triangulation as ASCII STL."""
    config = _apply_config(args)
    pts, box = _make_points(args, config)
    dt = DelaunayTriangulation.from_points(pts)
    with open(args.output, "w") as f:
        f.write(export_ascii_stl(dt))
    print(f"ASCII STL ({len(dt.triangles)} triangles) saved to {args.output}")


def cmd_boundary(args) -> None:
    """Extract and report boundary edges and loops."""
    config = _apply_config(args)
    pts, box = _make_points(args, config)
    dt = DelaunayTriangulation.from_points(pts)
    edges = extract_boundary_edges(dt)
    loops = extract_boundary_loops(dt)
    print(f"Boundary edges: {len(edges)}")
    print(f"Boundary loops: {len(loops)}")
    for i, loop in enumerate(loops):
        print(f"  Loop {i+1}: {len(loop)} vertices")
        if args.verbose:
            for p in loop:
                print(f"    ({p.x:.2f}, {p.y:.2f})")
    if args.output:
        import json
        data = {
            "boundary_edges": [[e.a.x, e.a.y, e.b.x, e.b.y] for e in edges],
            "boundary_loops": [[[p.x, p.y] for p in loop] for loop in loops],
        }
        with open(args.output, "w") as f:
            json.dump(data, f, indent=2)
        print(f"Boundary data saved to {args.output}")


def cmd_compare(args) -> None:
    """Side-by-side SVG: before vs after Lloyd relaxation."""
    config = _apply_config(args)
    pts, box = _make_points(args, config)
    dt_before = DelaunayTriangulation.from_points(pts)
    relaxed = lloyd_relaxation(pts, iterations=args.lloyd, clip_box=box, seed=args.seed)
    dt_after = DelaunayTriangulation.from_points(relaxed)
    vd_after = VoronoiDiagram.from_delaunay(dt_after, clip_box=box)
    hull_after = convex_hull(relaxed)
    # Render side-by-side
    w = args.width
    h = args.height
    total_w = w * 2 + 20
    svg_left = render_svg(width=w, height=h, delaunay_edges=dt_before.edges(),
                          points=pts, show_voronoi=False)
    svg_right = render_svg(width=w, height=h, delaunay_edges=dt_after.edges(),
                           voronoi_edges=vd_after.edges, points=relaxed, hull=hull_after)
    # Combine into one SVG
    combined = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{total_w}" height="{h}" '
        f'viewBox="0 0 {total_w} {h}">'
        f'<text x="{w//2}" y="20" fill="#9bf6ff" text-anchor="middle" font-size="14">Before</text>'
        f'<text x="{w + 20 + w//2}" y="20" fill="#9bf6ff" text-anchor="middle" font-size="14">After Lloyd</text>'
    )
    # Extract inner content from each SVG
    def extract_inner(svg: str) -> str:
        start = svg.find("<svg")
        start = svg.find(">", start) + 1
        end = svg.rfind("</svg>")
        return svg[start:end]
    combined += f'<g transform="translate(0,0)">{extract_inner(svg_left)}</g>'
    combined += f'<g transform="translate({w + 20},0)">{extract_inner(svg_right)}</g>'
    combined += "</svg>"
    with open(args.output, "w") as f:
        f.write(combined)
    print(f"Comparison SVG saved to {args.output}")
    print(f"  Before: {len(pts)} points, {len(dt_before.triangles)} triangles")
    print(f"  After:  {len(relaxed)} points, {len(dt_after.triangles)} triangles")


def cmd_config(args) -> None:
    """Generate a default configuration file."""
    config = Config()
    save_config(config, args.output)
    print(f"Default config saved to {args.output}")
    print(f"Format: {os.path.splitext(args.output)[1]}")


# --------------------------------------------------------------------------- #
#  Parser setup
# --------------------------------------------------------------------------- #

def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="delaunay-voronoi",
        description="Computational geometry toolkit: Delaunay, Voronoi, Lloyd, Ruppert.",
    )
    parser.add_argument("--config", default=None, metavar="PATH",
                        help="Load defaults from a config file (JSON/TOML/YAML).")
    parser.add_argument("--log-level", default="INFO",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                        help="Logging verbosity.")
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

    # ppm
    p = sub.add_parser("ppm", help="Flat-shaded Voronoi PPM raster.")
    _build_common_args(p)
    p.add_argument("-o", "--output", default="voronoi.ppm")
    p.set_defaults(func=cmd_voronoi_ppm)

    # png
    p = sub.add_parser("png", help="Flat-shaded Voronoi PNG raster (stdlib zlib).")
    _build_common_args(p)
    p.add_argument("-o", "--output", default="voronoi.png")
    p.set_defaults(func=cmd_voronoi_png)

    # info
    p = sub.add_parser("info", help="Print triangulation statistics.")
    _build_common_args(p)
    p.set_defaults(func=cmd_info)

    # mesh-stats
    p = sub.add_parser("mesh-stats", help="Detailed mesh quality report.")
    _build_common_args(p)
    p.add_argument("--json", action="store_true", help="Output as JSON.")
    p.add_argument("-o", "--output", default="mesh_report.json")
    p.set_defaults(func=cmd_mesh_stats)

    # json
    p = sub.add_parser("json", help="Save triangulation as JSON.")
    _build_common_args(p)
    p.add_argument("-o", "--output", default="triangulation.json")
    p.set_defaults(func=cmd_json)

    # from-json
    p = sub.add_parser("from-json", help="Render SVG from a saved JSON triangulation.")
    p.add_argument("input", help="Input JSON file.")
    p.add_argument("-o", "--output", default="from_json.svg")
    p.set_defaults(func=cmd_from_json)

    # nearest
    p = sub.add_parser("nearest", help="Find nearest site to a query point.")
    _build_common_args(p)
    p.add_argument("--x", type=float, required=True, help="Query x.")
    p.add_argument("--y", type=float, required=True, help="Query y.")
    p.add_argument("--knn", type=int, default=0, help="Also print k nearest neighbours.")
    p.set_defaults(func=cmd_nearest)

    # obj
    p = sub.add_parser("obj", help="Export triangulation as Wavefront OBJ.")
    _build_common_args(p)
    p.add_argument("-o", "--output", default="mesh.obj")
    p.set_defaults(func=cmd_obj)

    # stl
    p = sub.add_parser("stl", help="Export triangulation as ASCII STL.")
    _build_common_args(p)
    p.add_argument("-o", "--output", default="mesh.stl")
    p.set_defaults(func=cmd_stl)

    # boundary
    p = sub.add_parser("boundary", help="Extract and report boundary edges/loops.")
    _build_common_args(p)
    p.add_argument("--verbose", "-v", action="store_true", help="Print all loop vertices.")
    p.add_argument("-o", "--output", default=None, help="Save boundary as JSON.")
    p.set_defaults(func=cmd_boundary)

    # compare
    p = sub.add_parser("compare", help="Side-by-side SVG: before vs after Lloyd.")
    _build_common_args(p)
    p.add_argument("--lloyd", type=int, default=10, help="Lloyd iterations.")
    p.add_argument("-o", "--output", default="compare.svg")
    p.set_defaults(func=cmd_compare)

    # config
    p = sub.add_parser("config", help="Generate a default config file.")
    p.add_argument("-o", "--output", default="config.json",
                   help="Output path (.json or .toml).")
    p.set_defaults(func=cmd_config)

    args = parser.parse_args(argv)

    # Configure logging
    from .logging_utils import configure_logging
    configure_logging(args.log_level)

    args.func(args)


if __name__ == "__main__":
    main()