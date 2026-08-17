"""Command-line interface for the NURBS toolkit."""

from __future__ import annotations

import argparse
import json
import sys
from typing import List, Sequence

from . import (
    BSplineCurve,
    NURBSCurve,
    NURBSSurface,
    BezierCurve,
    bezier_to_bspline,
    knot_insert,
    knot_remove,
    degree_elevate,
    decompose_bezier_segments,
    generate_clamped_uniform_knot_vector,
    generate_uniform_knot_vector,
    validate_knot_vector,
    tessellate_curve,
    tessellate_surface,
    export_obj,
    export_ply_ascii,
    __version__,
)


def _parse_points(s: str) -> List[List[float]]:
    """Parse ``"1,2,3;4,5,6"`` into [[1,2,3],[4,5,6]]."""
    rows = s.split(";")
    return [[float(x) for x in r.split(",")] for r in rows]


def cmd_eval_curve(args: argparse.Namespace) -> None:
    cp = _parse_points(args.points)
    if args.weights:
        w = [float(x) for x in args.weights.split(",")]
        knots = [float(x) for x in args.knots.split(",")]
        c = NURBSCurve(args.degree, knots, cp, w)
    else:
        knots = [float(x) for x in args.knots.split(",")]
        c = BSplineCurve(args.degree, knots, cp)
    pt = c.evaluate(args.u)
    print(json.dumps({"point": pt}))


def cmd_tessellate_curve(args: argparse.Namespace) -> None:
    cp = _parse_points(args.points)
    knots = [float(x) for x in args.knots.split(",")]
    if args.weights:
        w = [float(x) for x in args.weights.split(",")]
        c = NURBSCurve(args.degree, knots, cp, w)
    else:
        c = BSplineCurve(args.degree, knots, cp)
    pts = tessellate_curve(c, args.samples)
    for p in pts:
        print(" ".join(f"{x:.6f}" for x in p))


def cmd_surface_obj(args: argparse.Namespace) -> None:
    # Read a JSON spec file.
    with open(args.spec) as f:
        spec = json.load(f)
    surf = NURBSSurface(
        spec["degree_u"],
        spec["degree_v"],
        spec["knots_u"],
        spec["knots_v"],
        spec["control_points"],
        spec.get("weights"),
    )
    verts, faces = tessellate_surface(surf, args.samples_u, args.samples_v)
    text = export_obj(verts, faces)
    if args.output:
        with open(args.output, "w") as f:
            f.write(text)
        print(f"Wrote {len(verts)} vertices, {len(faces)} faces to {args.output}")
    else:
        sys.stdout.write(text)


def cmd_bezier(args: argparse.Namespace) -> None:
    cp = _parse_points(args.points)
    bz = BezierCurve(cp)
    pt = bz.evaluate(args.t)
    print(json.dumps({"point": pt}))


def cmd_knot_insert(args: argparse.Namespace) -> None:
    cp = _parse_points(args.points)
    knots = [float(x) for x in args.knots.split(",")]
    c = BSplineCurve(args.degree, knots, cp)
    c2 = knot_insert(c, args.u, args.times)
    print(json.dumps({
        "knots": c2.knots,
        "control_points": c2.control_points,
    }))


def cmd_degree_elevate(args: argparse.Namespace) -> None:
    cp = _parse_points(args.points)
    knots = [float(x) for x in args.knots.split(",")]
    c = BSplineCurve(args.degree, knots, cp)
    c2 = degree_elevate(c, args.times)
    print(json.dumps({
        "degree": c2.degree,
        "knots": c2.knots,
        "control_points": c2.control_points,
    }))


def cmd_decompose(args: argparse.Namespace) -> None:
    cp = _parse_points(args.points)
    knots = [float(x) for x in args.knots.split(",")]
    c = BSplineCurve(args.degree, knots, cp)
    segs = decompose_bezier_segments(c)
    print(json.dumps({"segments": segs, "count": len(segs)}))


def cmd_version(args: argparse.Namespace) -> None:
    print(f"nurbs-toolkit v{__version__}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="nurbs",
        description="NURBS & B-spline CAGD toolkit",
    )
    sub = p.add_subparsers(dest="command")

    pe = sub.add_parser("eval-curve", help="Evaluate a curve at a parameter")
    pe.add_argument("--degree", type=int, required=True)
    pe.add_argument("--knots", required=True, help="Comma-separated knots")
    pe.add_argument("--points", required=True, help="x,y,z;x,y,z;...")
    pe.add_argument("--weights", default=None, help="Comma-separated weights")
    pe.add_argument("--u", type=float, required=True)
    pe.set_defaults(func=cmd_eval_curve)

    pt = sub.add_parser("tess-curve", help="Tessellate a curve")
    pt.add_argument("--degree", type=int, required=True)
    pt.add_argument("--knots", required=True)
    pt.add_argument("--points", required=True)
    pt.add_argument("--weights", default=None)
    pt.add_argument("--samples", type=int, default=100)
    pt.set_defaults(func=cmd_tessellate_curve)

    ps = sub.add_parser("surface-obj", help="Export a surface mesh to OBJ")
    ps.add_argument("--spec", required=True, help="JSON surface spec file")
    ps.add_argument("--samples-u", type=int, default=50)
    ps.add_argument("--samples-v", type=int, default=50)
    ps.add_argument("--output", "-o", default=None)
    ps.set_defaults(func=cmd_surface_obj)

    pb = sub.add_parser("bezier", help="Evaluate a Bezier curve")
    pb.add_argument("--points", required=True)
    pb.add_argument("--t", type=float, required=True)
    pb.set_defaults(func=cmd_bezier)

    pk = sub.add_parser("knot-insert", help="Insert a knot")
    pk.add_argument("--degree", type=int, required=True)
    pk.add_argument("--knots", required=True)
    pk.add_argument("--points", required=True)
    pk.add_argument("--u", type=float, required=True)
    pk.add_argument("--times", type=int, default=1)
    pk.set_defaults(func=cmd_knot_insert)

    pd = sub.add_parser("degree-elevate", help="Elevate degree")
    pd.add_argument("--degree", type=int, required=True)
    pd.add_argument("--knots", required=True)
    pd.add_argument("--points", required=True)
    pd.add_argument("--times", type=int, default=1)
    pd.set_defaults(func=cmd_degree_elevate)

    pdz = sub.add_parser("decompose", help="Decompose into Bezier segments")
    pdz.add_argument("--degree", type=int, required=True)
    pdz.add_argument("--knots", required=True)
    pdz.add_argument("--points", required=True)
    pdz.set_defaults(func=cmd_decompose)

    pv = sub.add_parser("version", help="Show version")
    pv.set_defaults(func=cmd_version)

    return p


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 1
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())