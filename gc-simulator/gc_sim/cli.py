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

    # Trace a simulation and export the trace
    gc-sim trace --scenario linked_list --output trace.json

    # Replay a trace on a different collector
    gc-sim replay trace.json --collector copying

    # Generate a detailed report with histogram
    gc-sim report --scenario churn --collectors all --histogram

    # Pause-time histogram for a single collector
    gc-sim histogram --collector generational --scenario churn \\
        --num-collections 10
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
from .logging_utils import configure_logging
from .reporting import (
    CollectorReport,
    PauseHistogram,
    format_comparison_report,
    generate_report_json,
    analyse_from_sims,
)
from .replay import TraceReplayer, load_trace, replay_from_file


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
    elif scenario == "churn":
        sim.scenario_churn(**params)
    elif scenario == "cycle_heavy":
        sim.scenario_cycle_heavy(**params)
    elif scenario == "none":
        pass
    else:
        raise ValueError(f"unknown scenario: {scenario}")


def _make_simulator(cfg: SimConfig, *, trace: bool = False) -> GCSimulator:
    return GCSimulator(
        heap_size=cfg.heap_size,
        collector=cfg.collector,
        allocator=cfg.allocator,
        allocator_policy=cfg.allocator_policy,
        trace=trace,
        **cfg.collector_kwargs,
    )


# ---------------------------------------------------------------------------
# Subcommand implementations
# ---------------------------------------------------------------------------

def cmd_list(args) -> int:
    print("Available collectors:")
    for c in available_collectors():
        print(f"  - {c}")
    print("\nAllocators: bump, free_list (policies: first_fit, best_fit, worst_fit)")
    print("\nScenarios: linked_list, binary_tree, random_graph, churn, cycle_heavy, none")
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
    sims = {}
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
            sims[cname] = sim
        except Exception as e:
            if not args.json:
                print(f"{cname:<20} ERROR: {e}")

    if args.json:
        reports = analyse_from_sims(sims)
        print(generate_report_json(reports))
    else:
        reports = analyse_from_sims(sims)
        print(format_comparison_report(reports, include_histogram=args.histogram))
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


def cmd_trace(args) -> int:
    """Run a simulation with event tracing and export the trace."""
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
    sim = _make_simulator(cfg, trace=True)
    _run_scenario(sim, cfg.scenario, cfg.scenario_params, seed=cfg.seed)
    for _ in range(cfg.num_collections):
        sim.collect()

    if sim.tracer is None:
        print("Error: tracing not enabled", file=sys.stderr)
        return 1

    events = sim.tracer.export()
    if args.output:
        sim.tracer.export_json(args.output)
        print(f"Trace saved to {args.output} ({len(events)} events)")
    else:
        print(json.dumps(events, indent=2))

    if args.summary:
        counts = sim.tracer.counts()
        print("\nEvent counts:")
        for et, count in sorted(counts.items()):
            print(f"  {et:<20} {count}")
    return 0


def cmd_replay(args) -> int:
    """Replay a recorded trace on a collector."""
    trace_data = load_trace(args.path)
    sim = replay_from_file(
        args.path,
        collector=args.collector,
        heap_size=args.heap_size,
        run_collections=not args.no_collect,
    )

    if args.json:
        print(json.dumps(sim.stats.as_dict(), indent=2))
    else:
        print(f"Replayed {len(trace_data)} events on {args.collector}")
        print(sim.summary())
        print()
        print(render_stats_table(sim.stats.records))
        print()
        print(f"Heap: {sim.heap.size} cells, used={sim.used}, "
              f"free={sim.free}, frag={sim.fragmentation():.1%}")
    return 0


def cmd_report(args) -> int:
    """Generate a detailed cross-collector comparison report."""
    scenario = args.scenario
    params = _parse_json(args.scenario_params)
    collectors = args.collectors or available_collectors()
    sims = {}
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
            sims[cname] = sim
        except Exception as e:
            if not args.json:
                print(f"{cname:<20} ERROR: {e}")

    reports = analyse_from_sims(sims)
    if args.json:
        print(generate_report_json(reports))
    else:
        print(format_comparison_report(reports, include_histogram=args.histogram))
    return 0


def cmd_histogram(args) -> int:
    """Show pause-time histogram for a single collector."""
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
        sim.collect()

    hist = PauseHistogram.from_records(sim.stats.records)
    if args.json:
        print(json.dumps(hist.to_dict(), indent=2))
    else:
        print(hist.render_ascii())
    return 0


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="gc-sim",
        description="Heap & garbage-collector simulator v" + __version__,
    )
    p.add_argument("--version", action="version", version=f"gc-sim {__version__}")
    p.add_argument("--log-level", default="WARNING",
                   help="Logging level (DEBUG/INFO/WARNING/ERROR)")
    p.add_argument("--log-file", default=None, help="Log file path (default: stderr)")
    sub = p.add_subparsers(dest="command", required=True)

    # list
    sp = sub.add_parser("list", help="List available collectors, allocators and scenarios")
    sp.set_defaults(func=cmd_list)

    # run
    sp = sub.add_parser("run", help="Run a simulation")
    sp.add_argument("--heap-size", type=int, default=1024)
    sp.add_argument("--collector", default="mark_sweep")
    sp.add_argument("--allocator", default="bump")
    sp.add_argument("--allocator-policy", default="first_fit")
    sp.add_argument("--scenario", default="linked_list",
                    help="linked_list/binary_tree/random_graph/churn/cycle_heavy/none")
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
    sp = sub.add_parser("compare", help="Compare collectors (summary table)")
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
    sp.add_argument("--histogram", action="store_true",
                    help="Include pause-time histograms in output")
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

    # trace
    sp = sub.add_parser("trace", help="Run a simulation with event tracing")
    sp.add_argument("--heap-size", type=int, default=1024)
    sp.add_argument("--collector", default="mark_sweep")
    sp.add_argument("--allocator", default="bump")
    sp.add_argument("--allocator-policy", default="first_fit")
    sp.add_argument("--scenario", default="linked_list")
    sp.add_argument("--scenario-params", default="{}", help="JSON dict")
    sp.add_argument("--num-collections", type=int, default=1)
    sp.add_argument("--seed", type=int, default=None)
    sp.add_argument("--output", "-o", default=None, help="Save trace to JSON file")
    sp.add_argument("--summary", action="store_true",
                    help="Print event count summary")
    sp.set_defaults(func=cmd_trace)

    # replay
    sp = sub.add_parser("replay", help="Replay a recorded trace on a collector")
    sp.add_argument("path", help="Path to JSON trace file")
    sp.add_argument("--collector", default="mark_sweep")
    sp.add_argument("--heap-size", type=int, default=1024)
    sp.add_argument("--no-collect", action="store_true",
                    help="Skip collection events during replay")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_replay)

    # report
    sp = sub.add_parser("report",
                        help="Generate a detailed cross-collector comparison report")
    sp.add_argument("--heap-size", type=int, default=512)
    sp.add_argument("--collector", "--collectors", dest="collectors",
                    nargs="*", default=None)
    sp.add_argument("--allocator", default="bump")
    sp.add_argument("--allocator-policy", default="first_fit")
    sp.add_argument("--scenario", default="churn")
    sp.add_argument("--scenario-params", default="{}", help="JSON dict")
    sp.add_argument("--num-collections", type=int, default=5)
    sp.add_argument("--seed", type=int, default=42)
    sp.add_argument("--histogram", action="store_true",
                    help="Include pause-time histograms in report")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_report)

    # histogram
    sp = sub.add_parser("histogram",
                        help="Show pause-time histogram for a single collector")
    sp.add_argument("--heap-size", type=int, default=512)
    sp.add_argument("--collector", default="mark_sweep")
    sp.add_argument("--allocator", default="bump")
    sp.add_argument("--allocator-policy", default="first_fit")
    sp.add_argument("--scenario", default="churn")
    sp.add_argument("--scenario-params", default="{}", help="JSON dict")
    sp.add_argument("--num-collections", type=int, default=5)
    sp.add_argument("--seed", type=int, default=42)
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_histogram)

    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    # Configure logging if requested
    if hasattr(args, "log_level") and args.log_level:
        configure_logging(level=args.log_level, logfile=getattr(args, "log_file", None))
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())