"""Enhanced command-line interface for the NURBS toolkit.

Provides subcommands for curve/surface evaluation, tessellation,
export (OBJ/PLY/STL), knot operations, degree elevation, Bezier
decomposition, curvature analysis, offset curves, fitting,
projection, presets, rendering, serialization, and configuration.

Uses structured logging and configuration file support.
"""

from __future__ import annotations

import argparse
import json
import sys
import math
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
    export_stl,
    curve_to_svg,
    surface_to_svg_wireframe,
    fit_bspline_curve,
    fit_bspline_surface,
    project_point,
    arc_length,
    reparameterize_arc_length,
    curvature,
    torsion,
    find_inflections,
    curvature_plot_data,
    max_curvature,
    offset_curve,
    reverse_curve,
    split_curve,
    concatenate_curves,
    intersect_curves,
    make_circle,
    make_sphere_patch,
    make_torus,
    make_cylinder,
    make_cone,
    curve_to_json,
    curve_from_json,
    surface_to_json,
    surface_from_json,
    NURBSConfig,
    get_logger,
    __version__,
)
from .stl_export import export_stl_ascii, export_stl_binary
from .logging_utils import logger


def _parse_points(s: str) -> List[List[float]]:
    """Parse ``"1,2,3;4,5,6"`` into [[1,2,3],[4,5,6]]."""
    rows = s.split(";")
    return [[float(x) for x in r.split(",")] for r in rows]


def _make_curve(args):
    """Build a curve from args."""
    cp = _parse_points(args.points)
    knots = [float(x) for x in args.knots.split(",")]
    if args.weights:
        w = [float(x) for x in args.weights.split(",")]
        return NURBSCurve(args.degree, knots, cp, w)
    return BSplineCurve(args.degree, knots, cp)


# -- Command handlers -------------------------------------------------

def cmd_eval_curve(args):
    """Evaluate a curve at a parameter."""
    c = _make_curve(args)
    pt = c.evaluate(args.u)
    print(json.dumps({"point": pt}))


def cmd_eval_derivative(args):
    """Evaluate a curve derivative at a parameter."""
    c = _make_curve(args)
    d = c.derivative(args.u, args.order)
    print(json.dumps({"derivative": d, "order": args.order}))


def cmd_tessellate_curve(args):
    """Tessellate a curve."""
    c = _make_curve(args)
    pts = tessellate_curve(c, args.samples)
    for p in pts:
        print(" ".join(f"{x:.6f}" for x in p))


def cmd_surface_obj(args):
    """Export a surface mesh to OBJ."""
    with open(args.spec) as f:
        spec = json.load(f)
    surf = NURBSSurface(
        spec["degree_u"], spec["degree_v"],
        spec["knots_u"], spec["knots_v"],
        spec["control_points"], spec.get("weights"),
    )
    verts, faces = tessellate_surface(surf, args.samples_u, args.samples_v)
    text = export_obj(verts, faces)
    if args.output:
        with open(args.output, "w") as f:
            f.write(text)
        print(f"Wrote {len(verts)} vertices, {len(faces)} faces to {args.output}")
    else:
        sys.stdout.write(text)


def cmd_surface_stl(args):
    """Export a surface mesh to STL."""
    with open(args.spec) as f:
        spec = json.load(f)
    surf = NURBSSurface(
        spec["degree_u"], spec["degree_v"],
        spec["knots_u"], spec["knots_v"],
        spec["control_points"], spec.get("weights"),
    )
    verts, faces = tessellate_surface(surf, args.samples_u, args.samples_v)
    if args.binary:
        data = export_stl_binary(verts, faces)
        if args.output:
            with open(args.output, "wb") as f:
                f.write(data)
            print(f"Wrote binary STL: {len(verts)} vertices, {len(faces)} faces to {args.output}")
        else:
            sys.stdout.buffer.write(data)
    else:
        text = export_stl_ascii(verts, faces)
        if args.output:
            with open(args.output, "w") as f:
                f.write(text)
            print(f"Wrote ASCII STL: {len(verts)} vertices, {len(faces)} faces to {args.output}")
        else:
            sys.stdout.write(text)


def cmd_bezier(args):
    """Evaluate a Bezier curve."""
    cp = _parse_points(args.points)
    bz = BezierCurve(cp)
    pt = bz.evaluate(args.t)
    print(json.dumps({"point": pt}))


def cmd_knot_insert(args):
    """Insert a knot."""
    c = _make_curve(args)
    c2 = knot_insert(c, args.u, args.times)
    print(json.dumps({
        "knots": c2.knots,
        "control_points": c2.control_points,
    }))


def cmd_degree_elevate(args):
    """Elevate degree."""
    c = _make_curve(args)
    c2 = degree_elevate(c, args.times)
    print(json.dumps({
        "degree": c2.degree,
        "knots": c2.knots,
        "control_points": c2.control_points,
    }))


def cmd_decompose(args):
    """Decompose into Bezier segments."""
    c = _make_curve(args)
    segs = decompose_bezier_segments(c)
    print(json.dumps({"segments": segs, "count": len(segs)}))


def cmd_curvature(args):
    """Compute curvature at a parameter."""
    c = _make_curve(args)
    k = curvature(c, args.u)
    result = {"u": args.u, "curvature": k}
    if len(c.control_points[0]) == 3:
        result["torsion"] = torsion(c, args.u)
    print(json.dumps(result))


def cmd_curvature_plot(args):
    """Generate curvature plot data."""
    c = _make_curve(args)
    us, kappas = curvature_plot_data(c, args.samples)
    data = [{"u": u, "kappa": k} for u, k in zip(us, kappas)]
    if args.output:
        with open(args.output, "w") as f:
            json.dump(data, f, indent=2)
        print(f"Wrote {len(data)} curvature samples to {args.output}")
    else:
        for u, k in zip(us, kappas):
            print(f"{u:.6f} {k:.6f}")


def cmd_inflections(args):
    """Find inflection points."""
    c = _make_curve(args)
    infl = find_inflections(c, samples=args.samples)
    print(json.dumps({"inflections": infl, "count": len(infl)}))


def cmd_max_curvature(args):
    """Find maximum curvature."""
    c = _make_curve(args)
    u_max, k_max = max_curvature(c, args.samples)
    print(json.dumps({"u": u_max, "max_curvature": k_max}))


def cmd_offset(args):
    """Compute offset curve."""
    c = _make_curve(args)
    pts = offset_curve(c, args.distance, args.samples)
    print(json.dumps({"offset_points": pts}))


def cmd_split(args):
    """Split a curve at a parameter."""
    c = _make_curve(args)
    left, right = split_curve(c, args.u)
    print(json.dumps({
        "left": {
            "knots": left.knots,
            "control_points": left.control_points,
        },
        "right": {
            "knots": right.knots,
            "control_points": right.control_points,
        },
    }))


def cmd_reverse(args):
    """Reverse a curve."""
    c = _make_curve(args)
    rev = reverse_curve(c)
    print(json.dumps({
        "knots": rev.knots,
        "control_points": rev.control_points,
    }))


def cmd_intersect(args):
    """Find intersections between two curves."""
    c1 = _make_curve(args)
    c2 = BSplineCurve(args.degree2, [float(x) for x in args.knots2.split(",")], _parse_points(args.points2))
    results = intersect_curves(c1, c2, samples=args.samples)
    print(json.dumps({
        "intersections": [[u, v, p] for u, v, p in results],
        "count": len(results),
    }))


def cmd_fit_curve(args):
    """Fit a B-spline curve to data points."""
    data = _parse_points(args.data)
    c = fit_bspline_curve(data, degree=args.degree, num_control_points=args.num_cp)
    print(json.dumps({
        "degree": c.degree,
        "knots": c.knots,
        "control_points": c.control_points,
    }))


def cmd_project(args):
    """Project a point onto a curve."""
    c = _make_curve(args)
    pt = [float(x) for x in args.point.split(",")]
    u, closest = project_point(c, pt, samples=args.samples)
    print(json.dumps({"u": u, "closest": closest}))


def cmd_arc_length(args):
    """Compute arc length."""
    c = _make_curve(args)
    length = arc_length(c, samples=args.samples)
    print(json.dumps({"arc_length": length}))


def cmd_preset_circle(args):
    """Create a NURBS circle."""
    circ = make_circle(args.radius, (args.cx, args.cy), args.segments)
    print(curve_to_json(circ))


def cmd_preset_torus(args):
    """Create a NURBS torus."""
    torus = make_torus(args.R, args.r, args.u_segs, args.v_segs)
    print(surface_to_json(torus))


def cmd_preset_cylinder(args):
    """Create a NURBS cylinder."""
    cyl = make_cylinder(args.radius, args.height, args.segments)
    print(surface_to_json(cyl))


def cmd_preset_cone(args):
    """Create a NURBS cone."""
    cone = make_cone(args.radius, args.height, args.segments)
    print(surface_to_json(cone))


def cmd_preset_sphere(args):
    """Create a NURBS sphere patch."""
    sp = make_sphere_patch(args.radius)
    print(surface_to_json(sp))


def cmd_render_svg(args):
    """Render a curve to SVG."""
    c = _make_curve(args)
    svg = curve_to_svg(c, samples=args.samples, width=args.width, height=args.height)
    if args.output:
        with open(args.output, "w") as f:
            f.write(svg)
        print(f"Wrote SVG to {args.output}")
    else:
        sys.stdout.write(svg)


def cmd_render_surface_svg(args):
    """Render a surface wireframe to SVG."""
    with open(args.spec) as f:
        spec = json.load(f)
    surf = NURBSSurface(
        spec["degree_u"], spec["degree_v"],
        spec["knots_u"], spec["knots_v"],
        spec["control_points"], spec.get("weights"),
    )
    svg = surface_to_svg_wireframe(surf, args.samples_u, args.samples_v, args.width, args.height)
    if args.output:
        with open(args.output, "w") as f:
            f.write(svg)
        print(f"Wrote SVG to {args.output}")
    else:
        sys.stdout.write(svg)


def cmd_serialize(args):
    """Serialize a curve to JSON."""
    c = _make_curve(args)
    print(curve_to_json(c))


def cmd_deserialize(args):
    """Deserialize and evaluate a curve from JSON."""
    with open(args.file) as f:
        c = curve_from_json(f.read())
    pt = c.evaluate(args.u)
    print(json.dumps({"point": pt}))


def cmd_config(args):
    """Show or save default configuration."""
    cfg = NURBSConfig()
    if args.save_config:
        cfg.save(args.save_config)
        print(f"Saved config to {args.save_config}")
    else:
        print(cfg.to_json())


def cmd_version(args):
    """Show version."""
    print(f"nurbs-toolkit v{__version__}")


# -- Parser builder ----------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """Build the argparse CLI with all subcommands."""
    p = argparse.ArgumentParser(
        prog="nurbs",
        description="NURBS & B-spline CAGD toolkit v" + __version__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  nurbs eval-curve --degree 3 --knots 0,0,0,0,1,1,1,1 --points "0,0,0;1,2,0;3,2,0;4,0,0" --u 0.5
  nurbs curvature --degree 3 --knots 0,0,0,0,1,1,1,1 --points "0,0;1,2;3,2;4,0" --u 0.5
  nurbs preset-circle --radius 2 --segments 4
  nurbs preset-torus --R 3 --r 1 --u-segs 4 --v-segs 4
  nurbs offset --degree 3 --knots 0,0,0,0,1,1,1,1 --points "0,0;1,2;3,2;4,0" --distance 0.5
  nurbs fit-curve --data "0,0,0;1,1,0;2,0.5,0;3,1,0;4,0,0" --degree 3 --num-cp 4
  nurbs arc-length --degree 3 --knots 0,0,0,0,1,1,1,1 --points "0,0;1,2;3,2;4,0" --samples 1000
  nurbs config --save-config nurbs.json
  nurbs version
""",
    )
    sub = p.add_subparsers(dest="command")

    # Common curve args helper.
    def add_curve_args(sp):
        sp.add_argument("--degree", type=int, required=True)
        sp.add_argument("--knots", required=True, help="Comma-separated knots")
        sp.add_argument("--points", required=True, help="x,y,z;x,y,z;...")
        sp.add_argument("--weights", default=None, help="Comma-separated weights")

    # eval-curve
    pe = sub.add_parser("eval-curve", help="Evaluate a curve at a parameter")
    add_curve_args(pe)
    pe.add_argument("--u", type=float, required=True)
    pe.set_defaults(func=cmd_eval_curve)

    # eval-derivative
    pd = sub.add_parser("eval-derivative", help="Evaluate a curve derivative")
    add_curve_args(pd)
    pd.add_argument("--u", type=float, required=True)
    pd.add_argument("--order", type=int, default=1)
    pd.set_defaults(func=cmd_eval_derivative)

    # tess-curve
    pt = sub.add_parser("tess-curve", help="Tessellate a curve")
    add_curve_args(pt)
    pt.add_argument("--samples", type=int, default=100)
    pt.set_defaults(func=cmd_tessellate_curve)

    # surface-obj
    ps = sub.add_parser("surface-obj", help="Export a surface mesh to OBJ")
    ps.add_argument("--spec", required=True, help="JSON surface spec file")
    ps.add_argument("--samples-u", type=int, default=50)
    ps.add_argument("--samples-v", type=int, default=50)
    ps.add_argument("--output", "-o", default=None)
    ps.set_defaults(func=cmd_surface_obj)

    # surface-stl
    pst = sub.add_parser("surface-stl", help="Export a surface mesh to STL")
    pst.add_argument("--spec", required=True, help="JSON surface spec file")
    pst.add_argument("--samples-u", type=int, default=50)
    pst.add_argument("--samples-v", type=int, default=50)
    pst.add_argument("--output", "-o", default=None)
    pst.add_argument("--binary", action="store_true", help="Binary STL format")
    pst.set_defaults(func=cmd_surface_stl)

    # bezier
    pb = sub.add_parser("bezier", help="Evaluate a Bezier curve")
    pb.add_argument("--points", required=True)
    pb.add_argument("--t", type=float, required=True)
    pb.set_defaults(func=cmd_bezier)

    # knot-insert
    pk = sub.add_parser("knot-insert", help="Insert a knot")
    add_curve_args(pk)
    pk.add_argument("--u", type=float, required=True)
    pk.add_argument("--times", type=int, default=1)
    pk.set_defaults(func=cmd_knot_insert)

    # degree-elevate
    pde = sub.add_parser("degree-elevate", help="Elevate degree")
    add_curve_args(pde)
    pde.add_argument("--times", type=int, default=1)
    pde.set_defaults(func=cmd_degree_elevate)

    # decompose
    pdz = sub.add_parser("decompose", help="Decompose into Bezier segments")
    add_curve_args(pdz)
    pdz.set_defaults(func=cmd_decompose)

    # curvature
    pc = sub.add_parser("curvature", help="Compute curvature at a parameter")
    add_curve_args(pc)
    pc.add_argument("--u", type=float, required=True)
    pc.set_defaults(func=cmd_curvature)

    # curvature-plot
    pcp = sub.add_parser("curvature-plot", help="Generate curvature plot data")
    add_curve_args(pcp)
    pcp.add_argument("--samples", type=int, default=200)
    pcp.add_argument("--output", "-o", default=None)
    pcp.set_defaults(func=cmd_curvature_plot)

    # inflections
    pi = sub.add_parser("inflections", help="Find inflection points")
    add_curve_args(pi)
    pi.add_argument("--samples", type=int, default=500)
    pi.set_defaults(func=cmd_inflections)

    # max-curvature
    pmc = sub.add_parser("max-curvature", help="Find maximum curvature")
    add_curve_args(pmc)
    pmc.add_argument("--samples", type=int, default=500)
    pmc.set_defaults(func=cmd_max_curvature)

    # offset
    po = sub.add_parser("offset", help="Compute offset curve")
    add_curve_args(po)
    po.add_argument("--distance", type=float, required=True)
    po.add_argument("--samples", type=int, default=100)
    po.set_defaults(func=cmd_offset)

    # split
    pspl = sub.add_parser("split", help="Split a curve at a parameter")
    add_curve_args(pspl)
    pspl.add_argument("--u", type=float, required=True)
    pspl.set_defaults(func=cmd_split)

    # reverse
    prev = sub.add_parser("reverse", help="Reverse a curve")
    add_curve_args(prev)
    prev.set_defaults(func=cmd_reverse)

    # intersect
    pint = sub.add_parser("intersect", help="Find intersections between two curves")
    add_curve_args(pint)
    pint.add_argument("--degree2", type=int, required=True)
    pint.add_argument("--knots2", required=True)
    pint.add_argument("--points2", required=True)
    pint.add_argument("--samples", type=int, default=200)
    pint.set_defaults(func=cmd_intersect)

    # fit-curve
    pfit = sub.add_parser("fit-curve", help="Fit a B-spline to data points")
    pfit.add_argument("--data", required=True, help="x,y,z;x,y,z;...")
    pfit.add_argument("--degree", type=int, default=3)
    pfit.add_argument("--num-cp", type=int, default=8)
    pfit.set_defaults(func=cmd_fit_curve)

    # project
    pproj = sub.add_parser("project", help="Project a point onto a curve")
    add_curve_args(pproj)
    pproj.add_argument("--point", required=True, help="x,y,z")
    pproj.add_argument("--samples", type=int, default=100)
    pproj.set_defaults(func=cmd_project)

    # arc-length
    pal = sub.add_parser("arc-length", help="Compute arc length")
    add_curve_args(pal)
    pal.add_argument("--samples", type=int, default=1000)
    pal.set_defaults(func=cmd_arc_length)

    # preset-circle
    pcirc = sub.add_parser("preset-circle", help="Create a NURBS circle")
    pcirc.add_argument("--radius", type=float, default=1.0)
    pcirc.add_argument("--cx", type=float, default=0.0)
    pcirc.add_argument("--cy", type=float, default=0.0)
    pcirc.add_argument("--segments", type=int, default=4)
    pcirc.set_defaults(func=cmd_preset_circle)

    # preset-torus
    ptor = sub.add_parser("preset-torus", help="Create a NURBS torus")
    ptor.add_argument("--R", type=float, default=2.0)
    ptor.add_argument("--r", type=float, default=0.5)
    ptor.add_argument("--u-segs", type=int, default=4)
    ptor.add_argument("--v-segs", type=int, default=4)
    ptor.set_defaults(func=cmd_preset_torus)

    # preset-cylinder
    pcyl = sub.add_parser("preset-cylinder", help="Create a NURBS cylinder")
    pcyl.add_argument("--radius", type=float, default=1.0)
    pcyl.add_argument("--height", type=float, default=2.0)
    pcyl.add_argument("--segments", type=int, default=4)
    pcyl.set_defaults(func=cmd_preset_cylinder)

    # preset-cone
    pcone = sub.add_parser("preset-cone", help="Create a NURBS cone")
    pcone.add_argument("--radius", type=float, default=1.0)
    pcone.add_argument("--height", type=float, default=2.0)
    pcone.add_argument("--segments", type=int, default=4)
    pcone.set_defaults(func=cmd_preset_cone)

    # preset-sphere
    psph = sub.add_parser("preset-sphere", help="Create a NURBS sphere patch")
    psph.add_argument("--radius", type=float, default=1.0)
    psph.set_defaults(func=cmd_preset_sphere)

    # render-svg
    psvg = sub.add_parser("render-svg", help="Render a curve to SVG")
    add_curve_args(psvg)
    psvg.add_argument("--samples", type=int, default=100)
    psvg.add_argument("--width", type=int, default=400)
    psvg.add_argument("--height", type=int, default=400)
    psvg.add_argument("--output", "-o", default=None)
    psvg.set_defaults(func=cmd_render_svg)

    # render-surface-svg
    pssvg = sub.add_parser("render-surface-svg", help="Render a surface wireframe to SVG")
    pssvg.add_argument("--spec", required=True)
    pssvg.add_argument("--samples-u", type=int, default=20)
    pssvg.add_argument("--samples-v", type=int, default=20)
    pssvg.add_argument("--width", type=int, default=400)
    pssvg.add_argument("--height", type=int, default=400)
    pssvg.add_argument("--output", "-o", default=None)
    pssvg.set_defaults(func=cmd_render_surface_svg)

    # serialize
    pser = sub.add_parser("serialize", help="Serialize a curve to JSON")
    add_curve_args(pser)
    pser.set_defaults(func=cmd_serialize)

    # deserialize
    pdes = sub.add_parser("deserialize", help="Deserialize and evaluate a curve from JSON")
    pdes.add_argument("--file", required=True)
    pdes.add_argument("--u", type=float, required=True)
    pdes.set_defaults(func=cmd_deserialize)

    # config
    pcfg = sub.add_parser("config", help="Show or save configuration")
    pcfg.add_argument("--save-config", default=None, help="Save config to file")
    pcfg.set_defaults(func=cmd_config)

    # version
    pv = sub.add_parser("version", help="Show version")
    pv.set_defaults(func=cmd_version)

    return p


def main(argv: Sequence[str] | None = None) -> int:
    """Main CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 1
    try:
        args.func(args)
    except Exception as e:
        logger.error(f"Error: {e}")
        print(f"Error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())