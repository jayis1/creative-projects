"""Command-line interface for the GC simulator.

Usage examples::

    # Run a mark-sweep collection on a linked-list scenario
    gc-sim run --collector mark_sweep --scenario linked_list \\
        --scenario-params '{"n": 20, "obj_size": 8}'

    # Visualise the heap after allocation
    gc-sim viz --heap-size 128 --collector copying --scenario binary_tree \\
        --scenario-params '{"depth": 3, "obj_size": 4}'

    # Compare collectors
    gc-sim compare --heap-size 512 --scenario random_graph \\
        --scenario-params '{"n": 50, "edge_prob": 0.05}'

    # List available collectors
    gc-sim list

    # Save/load config
    gc-sim config-save my_run.json --collector generational
    gc-sim config-load my_run.json
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional

from . import __version__
from .simulator import GCSimulator
from .collectors import available_collectors
from .config import SimConfig, load_config, save_config
from .visualizer import render_heap_ascii, render_stats_table, render_object_graph_dot
from .stats import StatsTracker


def _parse_json(s: Optional[str]) -> dict:
    if not s:
        return {}
    return json.loads(s)


def _run_scenario(sim: GCSimulator, scenario: str, params: dict, seed=None):
    """Run a scenario on ``sim``."""
    if scenario == "linked_list":
        sim.scenario_linked_list(**params)
    elif scenario == "binary_tree":
        sim.scenario_binary_tree(**params)
    elif scenario == "random_graph":
        sim.scenario_random_graph(seed=seed, **params)
    elif scenario == "none":
        pass
    else:
        raise ValueError(f"unknown scenario: {scenario}")


def _make_simulator(cfg: SimConfig) -> GCSimulator:
    return GCSimulator(
        heap_size=cfg.heap_size,
        collector=cfg.collector,
        allocator=cfg.allocator,
        allocator_policy=cfg.allocator_policy,
        **cfg.collector_kwargs,
    )


def cmd_list(args) -> int:
    print("Available collectors:")
    for c in available_collectors():
        print(f"  - {c}")
    print("\nAllocators: bump, free_list")
    print(f"\ngc-sim version {__version__}")
    return 0


def cmd_run(args) -> int:
    cfg = SimConfig(
        heap_size=args.heap_size,
        collector=args.collector,
        allocator=args.allocator,
        allocator_policy=args.allocator_policy,
        scenario=args.scenario,
        scenario_params=_parse_json(args.scenario_params),
        num_collections=args.num_collections,
        seed=args.seed,
    )
    cfg.validate()
    sim = _make_simulator(cfg)
    _run_scenario(sim, cfg.scenario, cfg.scenario_params, seed=cfg.seed)

    for _ in range(cfg.num_collections):
        stats = sim.collect()

    if args.json:
        print(json.dumps(sim.stats.as_dict(), indent=2))
    else:
        print(sim.summary())
        print()
        print(render_stats_table(sim.stats.records))
        print()
        print(f"Heap: {sim.heap.size} cells, used={sim.used}, "
              f"free={sim.free}, frag={sim.fragmentation():.1%}")
    return 0


def cmd_viz(args) -> int:
    cfg = SimConfig(
        heap_size=args.heap_size,
        collector=args.collector,
        allocator=args.allocator,
        allocator_policy=args.allocator_policy,
        scenario=args.scenario,
        scenario_params=_parse_json(args.scenario_params),
        seed=args.seed,
    )
    cfg.validate()
    sim = _make_simulator(cfg)
    _run_scenario(sim, cfg.scenario, cfg.scenario_params, seed=cfg.seed)
    if args.dot:
        print(render_object_graph_dot(sim.heap, sim.roots))
    else:
        print(render_heap_ascii(sim.heap, use_color=not args.no_color))
    return 0


def cmd_compare(args) -> int:
    scenario = args.scenario
    params = _parse_json(args.scenario_params)
    collectors = args.collectors or available_collectors()
    results = []
    for cname in collectors:
        cfg = SimConfig(
            heap_size=args.heap_size,
            collector=cname,
            allocator=args.allocator,
            allocator_policy=args.allocator_policy,
            scenario=scenario,
            scenario_params=params,
            num_collections=args.num_collections,
            seed=args.seed,
        )
        try:
            sim = _make_simulator(cfg)
            _run_scenario(sim, cfg.scenario, cfg.scenario_params, seed=cfg.seed)
            for _ in range(cfg.num_collections):
                sim.collect()
            results.append((cname, sim.stats))
        except Exception as e:
            results.append((cname, str(e)))

    if args.json:
        out = {}
        for cname, st in results:
            if isinstance(st, StatsTracker):
                out[cname] = st.as_dict()
            else:
                out[cname] = {"error": str(st)}
        print(json.dumps(out, indent=2))
    else:
        print(f"{'collector':<20} {'#coll':>5} {'total_pause':>11} "
              f"{'avg_pause':>9} {'max_pause':>9} {'avg_surv':>8} "
              f"{'freed':>6}")
        print("-" * 72)
        for cname, st in results:
            if isinstance(st, StatsTracker):
                print(f"{cname:<20} {st.num_collections:>5} "
                      f"{st.total_pause:>11} {st.avg_pause:>9.1f} "
                      f"{st.max_pause:>9} {st.avg_survival:>7.1%} "
                      f"{st.total_freed:>6}")
            else:
                print(f"{cname:<20} ERROR: {st}")
    return 0


def cmd_config_save(args) -> int:
    cfg = SimConfig(
        heap_size=args.heap_size,
        collector=args.collector,
        allocator=args.allocator,
        allocator_policy=args.allocator_policy,
        scenario=args.scenario,
        scenario_params=_parse_json(args.scenario_params),
        num_collections=args.num_collections,
        output_format=args.output_format,
        seed=args.seed,
    )
    cfg.validate()
    save_config(cfg, args.path)
    print(f"Config saved to {args.path}")
    return 0


def cmd_config_load(args) -> int:
    cfg = load_config(args.path)
    sim = _make_simulator(cfg)
    _run_scenario(sim, cfg.scenario, cfg.scenario_params, seed=cfg.seed)
    for _ in range(cfg.num_collections):
        sim.collect()
    print(sim.summary())
    return 0


def cmd_benchmark(args) -> int:
    from .benchmark import benchmark_all, format_benchmark_table
    scenario_name = args.scenario
    params = _parse_json(args.scenario_params)

    def scenario_fn(sim: GCSimulator) -> None:
        _run_scenario(sim, scenario_name, params, seed=args.seed)

    collectors = args.collectors or available_collectors()
    results = benchmark_all(
        heap_size=args.heap_size,
        scenario_fn=scenario_fn,
        num_collections=args.num_collections,
        collectors=collectors,
        allocator=args.allocator,
        allocator_policy=args.allocator_policy,
    )
    if args.json:
        import json as _json
        print(_json.dumps([r.as_dict() for r in results], indent=2))
    else:
        print(format_benchmark_table(results))
    return 0


def cmd_snapshot(args) -> int:
    cfg = SimConfig(
        heap_size=args.heap_size,
        collector=args.collector,
        allocator=args.allocator,
        allocator_policy=args.allocator_policy,
        scenario=args.scenario,
        scenario_params=_parse_json(args.scenario_params),
        seed=args.seed,
    )
    cfg.validate()
    sim = _make_simulator(cfg)
    _run_scenario(sim, cfg.scenario, cfg.scenario_params, seed=cfg.seed)
    if args.after_collect:
        sim.collect()
    import json as _json
    print(_json.dumps(sim.snapshot(), indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="gc-sim",
        description="Heap & garbage-collector simulator",
    )
    p.add_argument("--version", action="version", version=f"gc-sim {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    # list
    sp = sub.add_parser("list", help="List available collectors and allocators")
    sp.set_defaults(func=cmd_list)

    # run
    sp = sub.add_parser("run", help="Run a simulation")
    sp.add_argument("--heap-size", type=int, default=1024)
    sp.add_argument("--collector", default="mark_sweep")
    sp.add_argument("--allocator", default="bump")
    sp.add_argument("--allocator-policy", default="first_fit")
    sp.add_argument("--scenario", default="linked_list")
    sp.add_argument("--scenario-params", default="{}", help="JSON dict")
    sp.add_argument("--num-collections", type=int, default=1)
    sp.add_argument("--seed", type=int, default=None)
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_run)

    # viz
    sp = sub.add_parser("viz", help="Visualise the heap")
    sp.add_argument("--heap-size", type=int, default=128)
    sp.add_argument("--collector", default="mark_sweep")
    sp.add_argument("--allocator", default="bump")
    sp.add_argument("--allocator-policy", default="first_fit")
    sp.add_argument("--scenario", default="linked_list")
    sp.add_argument("--scenario-params", default="{}", help="JSON dict")
    sp.add_argument("--seed", type=int, default=None)
    sp.add_argument("--dot", action="store_true", help="Output Graphviz DOT")
    sp.add_argument("--no-color", action="store_true")
    sp.set_defaults(func=cmd_viz)

    # compare
    sp = sub.add_parser("compare", help="Compare collectors")
    sp.add_argument("--heap-size", type=int, default=512)
    sp.add_argument("--collector", "--collectors", dest="collectors",
                    nargs="*", default=None)
    sp.add_argument("--allocator", default="bump")
    sp.add_argument("--allocator-policy", default="first_fit")
    sp.add_argument("--scenario", default="random_graph")
    sp.add_argument("--scenario-params", default="{}", help="JSON dict")
    sp.add_argument("--num-collections", type=int, default=1)
    sp.add_argument("--seed", type=int, default=None)
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_compare)

    # config-save
    sp = sub.add_parser("config-save", help="Save config to file")
    sp.add_argument("path")
    sp.add_argument("--heap-size", type=int, default=1024)
    sp.add_argument("--collector", default="mark_sweep")
    sp.add_argument("--allocator", default="bump")
    sp.add_argument("--allocator-policy", default="first_fit")
    sp.add_argument("--scenario", default="linked_list")
    sp.add_argument("--scenario-params", default="{}", help="JSON dict")
    sp.add_argument("--num-collections", type=int, default=1)
    sp.add_argument("--output-format", default="text")
    sp.add_argument("--seed", type=int, default=None)
    sp.set_defaults(func=cmd_config_save)

    # config-load
    sp = sub.add_parser("config-load", help="Load and run config from file")
    sp.add_argument("path")
    sp.set_defaults(func=cmd_config_load)

    # benchmark
    sp = sub.add_parser("benchmark", help="Benchmark multiple collectors")
    sp.add_argument("--heap-size", type=int, default=512)
    sp.add_argument("--collector", "--collectors", dest="collectors",
                    nargs="*", default=None)
    sp.add_argument("--allocator", default="bump")
    sp.add_argument("--allocator-policy", default="first_fit")
    sp.add_argument("--scenario", default="random_graph")
    sp.add_argument("--scenario-params", default="{}", help="JSON dict")
    sp.add_argument("--num-collections", type=int, default=3)
    sp.add_argument("--seed", type=int, default=42)
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_benchmark)

    # snapshot
    sp = sub.add_parser("snapshot", help="Dump heap snapshot as JSON")
    sp.add_argument("--heap-size", type=int, default=128)
    sp.add_argument("--collector", default="mark_sweep")
    sp.add_argument("--allocator", default="bump")
    sp.add_argument("--allocator-policy", default="first_fit")
    sp.add_argument("--scenario", default="linked_list")
    sp.add_argument("--scenario-params", default="{}", help="JSON dict")
    sp.add_argument("--seed", type=int, default=None)
    sp.add_argument("--after-collect", action="store_true",
                    help="Run a collection before snapshotting")
    sp.set_defaults(func=cmd_snapshot)

    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())