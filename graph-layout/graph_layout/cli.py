"""Command-line interface for the graph_layout toolkit.

Subcommands:
  layout    — compute a layout and save
  metrics   — print layout quality metrics
  ascii     — render ASCII art of a layout
  compare   — compare all algorithms by metrics
  generate  — generate a named graph
  analyze   — run graph algorithms (centrality, MST, community detection)
  pipeline  — run a full pipeline from a JSON/TOML config file
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from typing import Optional

from . import (
    Graph, FruchtermanReingold, KamadaKawai, StressMajorization,
    SugiyamaLayout, TreeLayout, CircularLayout, RadialLayout,
    GridLayout, RandomLayout, DRGraphLayout, PivotMDSLayout,
    LayoutMetrics,
    SVGRenderer, ASCIIRenderer, TextRenderer, AnimatedSVGRenderer,
    HTMLRenderer, MatrixRenderer,
    load_dot, save_dot, load_json, save_json, load_edge_list, save_edge_list,
    load_config, validate_config,
    setup_logging, get_logger,
)
from .generators import (
    complete_bipartite, path_graph, star_graph, cycle_graph,
    petersen_graph, hypercube_graph, erdos_renyi,
    barabasi_albert, watts_strogatz,
)
from .algorithms import (
    bfs, dfs, dijkstra, degree_centrality, closeness_centrality,
    betweenness_centrality, minimum_spanning_tree, has_cycle,
    topological_sort, label_propagation,
)
from .render import AnimatedSVGRenderer
from .transform import scale_to_fit

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
    "drgraph": DRGraphLayout,
    "pivot-mds": PivotMDSLayout,
}

FORMAT_LOAD = {"dot": load_dot, "json": load_json, "edges": load_edge_list}


def cmd_layout(args):
    logger = get_logger()
    logger.info(f"Loading graph from {args.input}")
    g = _load(args.input, args.format)
    logger.info(f"Loaded {g.node_count} nodes, {g.edge_count} edges")
    algo_cls = ALGORITHMS[args.algorithm]
    algo = algo_cls(width=args.width, height=args.height, seed=args.seed)
    logger.info(f"Running {args.algorithm} layout...")
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


def cmd_analyze(args):
    """Run graph algorithms on a graph file."""
    g = _load(args.input, args.format)
    if args.analysis == "bfs":
        result = bfs(g, args.start or list(g.nodes)[0])
        print("BFS order:", " → ".join(result))
    elif args.analysis == "dfs":
        result = dfs(g, args.start or list(g.nodes)[0])
        print("DFS order:", " → ".join(result))
    elif args.analysis == "dijkstra":
        dist = dijkstra(g, args.start or list(g.nodes)[0])
        for nid, d in sorted(dist.items()):
            print(f"  {args.start} → {nid}: {d:.2f}")
    elif args.analysis == "degree":
        c = degree_centrality(g)
        for nid, v in sorted(c.items(), key=lambda x: -x[1]):
            print(f"  {nid:15s} {v:.4f}")
    elif args.analysis == "closeness":
        c = closeness_centrality(g)
        for nid, v in sorted(c.items(), key=lambda x: -x[1]):
            print(f"  {nid:15s} {v:.4f}")
    elif args.analysis == "betweenness":
        c = betweenness_centrality(g)
        for nid, v in sorted(c.items(), key=lambda x: -x[1]):
            print(f"  {nid:15s} {v:.4f}")
    elif args.analysis == "mst":
        mst = minimum_spanning_tree(g)
        total = sum(w for _, _, w in mst)
        print(f"MST: {len(mst)} edges, total weight = {total:.2f}")
        for u, v, w in mst:
            print(f"  {u} -- {v}  (w={w})")
    elif args.analysis == "cycle":
        print(f"Has cycle: {has_cycle(g)}")
    elif args.analysis == "topo":
        try:
            order = topological_sort(g)
            print("Topological order:", " → ".join(order))
        except ValueError as e:
            print(f"Error: {e}")
    elif args.analysis == "community":
        communities = label_propagation(g, seed=args.seed)
        n_comm = len(set(communities.values()))
        print(f"Detected {n_comm} communities:")
        by_comm = {}
        for nid, c in communities.items():
            by_comm.setdefault(c, []).append(nid)
        for c, members in sorted(by_comm.items()):
            print(f"  Community {c}: {', '.join(members)}")


def cmd_pipeline(args):
    """Run a full pipeline from a JSON/TOML config file."""
    logger = get_logger()
    logger.info(f"Loading config from {args.config}")
    config = load_config(args.config)
    validate_config(config)

    # Build or load graph
    if "graph" in config and "generator" in config["graph"]:
        gen_name = config["graph"]["generator"]
        gen_params = config["graph"].get("params", [])
        gen = GENERATORS.get(gen_name)
        if gen is None:
            print(f"Unknown generator '{gen_name}'")
            sys.exit(1)
        g = gen([int(x) for x in gen_params])
    elif "graph" in config and "input" in config["graph"]:
        g = _load(config["graph"]["input"],
                   config["graph"].get("format"))
    else:
        print("Config must specify a graph 'generator' or 'input'")
        sys.exit(1)

    # Apply layout
    layout_cfg = config["layout"]
    algo_cls = ALGORITHMS.get(layout_cfg["algorithm"])
    if algo_cls is None:
        print(f"Unknown algorithm '{layout_cfg['algorithm']}'")
        sys.exit(1)
    algo = algo_cls(
        width=layout_cfg.get("width", 1000),
        height=layout_cfg.get("height", 1000),
        seed=layout_cfg.get("seed", 42),
    )
    algo.layout(g)

    # Render
    render_cfg = config.get("render", {})
    output = render_cfg.get("output", "output.svg")
    fmt = render_cfg.get("format", "svg")
    _save(g, output, fmt)
    print(f"Pipeline complete → {output}")

    # Metrics
    if config.get("metrics", False):
        m = LayoutMetrics.all_metrics(g)
        print("Metrics:")
        for k, v in m.items():
            print(f"  {k:30s} {v:.4f}")


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
    elif ext == "html":
        HTMLRenderer().save(graph, path)
    elif ext == "txt":
        TextRenderer().save(graph, path)
    elif ext == "ascii":
        ASCIIRenderer().save(graph, path)
    elif ext == "matrix":
        MatrixRenderer().save(graph, path)
    else:
        raise ValueError(f"Unknown output format: {ext}")


def build_parser():
    p = argparse.ArgumentParser(
        prog="graph-layout",
        description="Force-directed & hierarchical graph layout engine "
                    "(v3.0.0 — 11 layouts, 6 renderers, graph algorithms)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  graph-layout generate petersen -o petersen.json
  graph-layout layout petersen.json -o petersen.svg -a fr
  graph-layout compare petersen.json
  graph-layout analyze petersen.json --analysis betweenness
  graph-layout pipeline config.json
""",
    )
    p.add_argument("--verbose", "-v", action="store_true", default=False,
                    help="enable debug logging")
    sub = p.add_subparsers(dest="command")

    # layout
    pl = sub.add_parser("layout", help="Compute a layout and save")
    pl.add_argument("input", help="Input graph file")
    pl.add_argument("-o", "--output", default="output.svg", help="Output file")
    pl.add_argument("-a", "--algorithm", default="fr", choices=list(ALGORITHMS))
    pl.add_argument("--format", default=None, help="Input format (dot/json/edges)")
    pl.add_argument("--output-format", default=None,
                    help="Output format (svg/html/json/dot/edges/txt/ascii/matrix)")
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

    # analyze
    pa2 = sub.add_parser("analyze", help="Run graph algorithms")
    pa2.add_argument("input", help="Input graph file")
    pa2.add_argument("--analysis", required=True,
                     choices=["bfs", "dfs", "dijkstra", "degree",
                              "closeness", "betweenness", "mst", "cycle",
                              "topo", "community"],
                     help="Algorithm to run")
    pa2.add_argument("--start", default=None, help="Starting node (for bfs/dfs/dijkstra)")
    pa2.add_argument("--format", default=None)
    pa2.add_argument("--seed", type=int, default=42)
    pa2.set_defaults(func=cmd_analyze)

    # pipeline
    pp = sub.add_parser("pipeline", help="Run a full pipeline from a config file")
    pp.add_argument("config", help="JSON or TOML config file")
    pp.set_defaults(func=cmd_pipeline)

    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        sys.exit(1)
    # setup logging
    level = "DEBUG" if getattr(args, "verbose", False) else "INFO"
    setup_logging(level=level)
    args.func(args)


if __name__ == "__main__":
    main()