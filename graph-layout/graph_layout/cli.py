"""Command-line interface for the graph_layout toolkit."""

from __future__ import annotations

import argparse
import sys
from typing import Optional

from . import (
    Graph, FruchtermanReingold, KamadaKawai, StressMajorization,
    SugiyamaLayout, TreeLayout, CircularLayout, RadialLayout,
    GridLayout, RandomLayout, LayoutMetrics,
    SVGRenderer, ASCIIRenderer, TextRenderer,
    load_dot, save_dot, load_json, save_json, load_edge_list, save_edge_list,
)
from .generators import (
    complete_bipartite, path_graph, star_graph, cycle_graph,
    petersen_graph, hypercube_graph, erdos_renyi,
    barabasi_albert, watts_strogatz,
)
from .transform import scale_to_fit
from .render import AnimatedSVGRenderer

ALGORITHMS = {
    "fr": FruchtermanReingold,
    "kamada": KamadaKawai,
    "stress": StressMajorization,
    "sugiyama": SugiyamaLayout,
    "tree": TreeLayout,
    "circular": CircularLayout,
    "radial": RadialLayout,
    "grid": GridLayout,
    "random": RandomLayout,
}

FORMAT_LOAD = {"dot": load_dot, "json": load_json, "edges": load_edge_list}


def cmd_layout(args):
    g = _load(args.input, args.format)
    algo_cls = ALGORITHMS[args.algorithm]
    algo = algo_cls(width=args.width, height=args.height, seed=args.seed)
    algo.layout(g)
    _save(g, args.output, args.output_format)
    print(f"Layout '{args.algorithm}' applied to {g.node_count} nodes, "
          f"{g.edge_count} edges → {args.output}")


def cmd_metrics(args):
    g = _load(args.input, args.format)
    m = LayoutMetrics.all_metrics(g)
    for k, v in m.items():
        print(f"  {k:30s} {v:.4f}")


def cmd_ascii(args):
    g = _load(args.input, args.format)
    algo_cls = ALGORITHMS[args.algorithm]
    algo = algo_cls(width=args.width, height=args.height, seed=args.seed)
    algo.layout(g)
    print(ASCIIRenderer(args.ascii_width, args.ascii_height).render(g))


def cmd_compare(args):
    """Run all algorithms and print a metrics comparison table."""
    import copy as _copy
    g = _load(args.input, args.format)
    print(f"{'Algorithm':<25s} {'crossings':>10s} {'variance':>10s} "
          f"{'stress':>10s} {'aspect':>8s}")
    print("-" * 65)
    for name, cls in ALGORITHMS.items():
        g2 = g.copy()
        cls(width=args.width, height=args.height, seed=args.seed).layout(g2)
        m = LayoutMetrics.all_metrics(g2)
        print(f"{name:<25s} {int(m['crossing_count']):>10d} "
              f"{m['edge_length_variance']:>10.2f} "
              f"{m['stress']:>10.2f} {m['aspect_ratio']:>8.2f}")


GENERATORS = {
    "complete-bipartite": lambda a: complete_bipartite(a[0], a[1]),
    "path": lambda a: path_graph(a[0]),
    "star": lambda a: star_graph(a[0]),
    "cycle": lambda a: cycle_graph(a[0]),
    "petersen": lambda a: petersen_graph(),
    "hypercube": lambda a: hypercube_graph(a[0]),
    "erdos-renyi": lambda a: erdos_renyi(a[0], a[1] / 100.0, seed=a[2] if len(a) > 2 else None),
    "barabasi-albert": lambda a: barabasi_albert(a[0], a[1], seed=a[2] if len(a) > 2 else None),
    "watts-strogatz": lambda a: watts_strogatz(a[0], a[1], a[2] / 100.0, seed=a[3] if len(a) > 3 else None),
    "grid": lambda a: Graph.grid_graph(a[0], a[1]),
    "tree": lambda a: Graph.tree_graph(a[0], a[1]),
    "complete": lambda a: Graph.complete_graph(a[0]),
}


def cmd_generate(args):
    """Generate a named graph and save it."""
    gen = GENERATORS.get(args.type)
    if gen is None:
        print(f"Unknown generator '{args.type}'. Available: {list(GENERATORS)}")
        sys.exit(1)
    params = [int(x) for x in args.params]
    g = gen(params)
    _save(g, args.output, args.output_format)
    print(f"Generated {args.type}: {g.node_count} nodes, {g.edge_count} edges → {args.output}")


def _load(path: str, fmt: Optional[str]):
    if fmt is None:
        fmt = path.rsplit(".", 1)[-1] if "." in path else "edges"
    if fmt == "edges":
        return load_edge_list(path)
    elif fmt == "dot":
        return load_dot(path)
    elif fmt == "json":
        return load_json(path)
    raise ValueError(f"Unknown format: {fmt}")


def _save(graph, path: str, fmt: Optional[str]):
    if fmt is None:
        ext = path.rsplit(".", 1)[-1] if "." in path else "json"
    else:
        ext = fmt
    if ext == "json":
        save_json(graph, path)
    elif ext == "dot":
        save_dot(graph, path)
    elif ext == "edges":
        save_edge_list(graph, path)
    elif ext == "svg":
        SVGRenderer().save(graph, path)
    elif ext == "txt":
        TextRenderer().save(graph, path)
    elif ext == "ascii":
        ASCIIRenderer().save(graph, path)
    else:
        raise ValueError(f"Unknown output format: {ext}")


def build_parser():
    p = argparse.ArgumentParser(
        prog="graph-layout",
        description="Force-directed & hierarchical graph layout engine",
    )
    sub = p.add_subparsers(dest="command")

    # layout
    pl = sub.add_parser("layout", help="Compute a layout and save")
    pl.add_argument("input", help="Input graph file")
    pl.add_argument("-o", "--output", default="output.svg", help="Output file")
    pl.add_argument("-a", "--algorithm", default="fr", choices=list(ALGORITHMS))
    pl.add_argument("--format", default=None, help="Input format (dot/json/edges)")
    pl.add_argument("--output-format", default=None, help="Output format")
    pl.add_argument("--width", type=float, default=1000)
    pl.add_argument("--height", type=float, default=1000)
    pl.add_argument("--seed", type=int, default=42)
    pl.set_defaults(func=cmd_layout)

    # metrics
    pm = sub.add_parser("metrics", help="Print layout quality metrics")
    pm.add_argument("input")
    pm.add_argument("--format", default=None)
    pm.set_defaults(func=cmd_metrics)

    # ascii
    pa = sub.add_parser("ascii", help="Render ASCII art of a layout")
    pa.add_argument("input")
    pa.add_argument("-a", "--algorithm", default="fr", choices=list(ALGORITHMS))
    pa.add_argument("--format", default=None)
    pa.add_argument("--width", type=float, default=1000)
    pa.add_argument("--height", type=float, default=1000)
    pa.add_argument("--ascii-width", type=int, default=70)
    pa.add_argument("--ascii-height", type=int, default=25)
    pa.add_argument("--seed", type=int, default=42)
    pa.set_defaults(func=cmd_ascii)

    # compare
    pc = sub.add_parser("compare", help="Compare all algorithms by metrics")
    pc.add_argument("input")
    pc.add_argument("--format", default=None)
    pc.add_argument("--width", type=float, default=1000)
    pc.add_argument("--height", type=float, default=1000)
    pc.add_argument("--seed", type=int, default=42)
    pc.set_defaults(func=cmd_compare)

    # generate
    pg = sub.add_parser("generate", help="Generate a named graph")
    pg.add_argument("type", choices=list(GENERATORS),
                    help="Graph type to generate")
    pg.add_argument("params", nargs="*", default=[],
                    help="Generator parameters (type-specific)")
    pg.add_argument("-o", "--output", default="generated.json",
                    help="Output file")
    pg.add_argument("--output-format", default=None)
    pg.set_defaults(func=cmd_generate)

    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        sys.exit(1)
    args.func(args)


if __name__ == "__main__":
    main()