#!/usr/bin/env python3
"""Command-line interface for the Delaunay-Voronoi toolkit."""

from __future__ import annotations

import argparse
import sys

from .delaunay import DelaunayTriangulation
from .geometry import Point
from .lloyd import generate_poisson_seed, lloyd_relaxation
from .voronoi import VoronoiDiagram
from .render import render_svg
from .convex_hull import convex_hull


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Generate Delaunay/Voronoi diagrams from random points."
    )
    parser.add_argument(
        "-n", "--num-points", type=int, default=30,
        help="Number of random sites to generate.",
    )
    parser.add_argument(
        "-w", "--width", type=int, default=800,
        help="Image width in pixels.",
    )
    parser.add_argument(
        "--height", type=int, default=600,
        help="Image height in pixels.",
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed for reproducibility.",
    )
    parser.add_argument(
        "--lloyd", type=int, default=0,
        help="Number of Lloyd relaxation iterations (0 = off).",
    )
    parser.add_argument(
        "-o", "--output", default="diagram.svg",
        help="Output SVG file path.",
    )
    parser.add_argument(
        "--no-voronoi", action="store_true",
        help="Hide Voronoi edges.",
    )
    parser.add_argument(
        "--no-delaunay", action="store_true",
        help="Hide Delaunay edges.",
    )
    args = parser.parse_args(argv)

    box = (Point(0, 0), Point(args.width, args.height))
    pts = generate_poisson_seed(args.num_points, box, seed=args.seed)
    if args.lloyd > 0:
        pts = lloyd_relaxation(pts, iterations=args.lloyd, clip_box=box, seed=args.seed)

    dt = DelaunayTriangulation.from_points(pts)
    vd = VoronoiDiagram.from_delaunay(dt, clip_box=box)
    hull = convex_hull(pts)

    svg = render_svg(
        width=args.width,
        height=args.height,
        delaunay_edges=dt.edges(),
        voronoi_edges=vd.edges,
        points=pts,
        hull=hull,
        show_delaunay=not args.no_delaunay,
        show_voronoi=not args.no_voronoi,
    )
    with open(args.output, "w") as f:
        f.write(svg)

    print(f"Generated {len(pts)} points, {len(dt.triangles)} triangles, "
          f"{len(vd.edges)} Voronoi edges, hull has {len(hull)} vertices.")
    print(f"Saved to {args.output}")


if __name__ == "__main__":
    main()