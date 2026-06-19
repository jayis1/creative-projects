"""Command-line interface for the Petri net simulator.

Provides 14 subcommands: simulate, reachability, invariants, analyze,
show, fire, export, presets, reachable, cover, batch, steady-state,
pnml, config.
"""

from __future__ import annotations

import argparse
import json
import sys

from . import (
    PetriNet, Place, Transition,
    Simulator,
    compute_t_invariants, compute_p_invariants,
    reachability_graph, analyze_boundedness, analyze_liveness,
    is_reachable, is_reversible,
    coverability_tree, analyze_traps_siphons,
    ascii_net, ascii_marking, reachability_ascii, reachability_dot,
    StochasticPetriNet, build_ctmc, steady_state_probabilities,
    monte_carlo, expected_time_to_target,
    batch_simulate,
    to_pnml, from_pnml, validate_pnml,
    load_config, save_config,
)
from .logging_util import setup_logging
from .presets import (
    dining_philosophers, producer_consumer, mutual_exclusion,
    workflow_net, state_machine, free_choice_net, readers_writers, simple_buffer,
    token_ring, elevator_system, producer_consumer_chain, database_transaction,
)

PRESETS = {
    "dining_philosophers": lambda: dining_philosophers(3),
    "producer_consumer": lambda: producer_consumer(5),
    "mutual_exclusion": mutual_exclusion,
    "workflow": workflow_net,
    "state_machine": state_machine,
    "free_choice": free_choice_net,
    "readers_writers": lambda: readers_writers(2),
    "simple_buffer": lambda: simple_buffer(3),
    "token_ring": lambda: token_ring(3),
    "elevator": lambda: elevator_system(4),
    "pipeline": lambda: producer_consumer_chain(3),
    "db_transaction": database_transaction,
}


def cmd_simulate(args: argparse.Namespace) -> int:
    net = _get_net(args)
    sim = Simulator(net, seed=args.seed)
    result = sim.random_walk(max_steps=args.steps)
    print(f"Simulation: {result.steps_fired} steps fired")
    print(f"Deadlocked: {result.deadlocked}")
    print(f"Final marking: {ascii_marking(result.final_marking, net)}")
    if args.trace:
        print("\nTrace:")
        for rec in result.trace:
            print(f"  step {rec.step}: {rec.transition}")
            print(f"    before: {ascii_marking(rec.marking_before, net)}")
            print(f"    after:  {ascii_marking(rec.marking_after, net)}")
    return 0


def cmd_reachability(args: argparse.Namespace) -> int:
    net = _get_net(args)
    rg = reachability_graph(net, max_states=args.max_states)
    if args.dot:
        print(reachability_dot(rg))
    else:
        print(reachability_ascii(rg))
    return 0


def cmd_invariants(args: argparse.Namespace) -> int:
    net = _get_net(args)
    place_names = sorted(net.places)
    trans_names = sorted(net.transitions)

    if args.type in ("t", "both"):
        t_invs = compute_t_invariants(net)
        print("T-Invariants (transition multisets that preserve marking):")
        if not t_invs:
            print("  (none)")
        for i, inv in enumerate(t_invs):
            pairs = [f"{trans_names[j]}×{inv[j]}" for j in range(len(inv)) if inv[j] != 0]
            print(f"  #{i}: {', '.join(pairs)}")
        print()

    if args.type in ("p", "both"):
        p_invs = compute_p_invariants(net)
        print("P-Invariants (conserved token sums):")
        if not p_invs:
            print("  (none)")
        for i, inv in enumerate(p_invs):
            pairs = [f"{place_names[j]}×{inv[j]}" for j in range(len(inv)) if inv[j] != 0]
            print(f"  #{i}: {', '.join(pairs)}")
    return 0


def cmd_analyze(args: argparse.Namespace) -> int:
    net = _get_net(args)
    print(ascii_net(net))
    print()

    print("Boundedness:")
    b = analyze_boundedness(net, max_states=args.max_states)
    print(f"  {b}")
    if b.is_bounded:
        for p, mx in sorted(b.max_tokens.items()):
            print(f"    {p}: max={mx}")
    print()

    print("Liveness:")
    l = analyze_liveness(net, max_states=args.max_states)
    print(l)
    print()

    print("Reversibility:")
    rev = is_reversible(net, max_states=args.max_states)
    print(f"  Reversible (home state): {rev}")
    print()

    print("Traps & Siphons:")
    ts = analyze_traps_siphons(net)
    print(f"  {ts}")
    return 0


def cmd_reachable(args: argparse.Namespace) -> int:
    """Check if a target marking is reachable."""
    net = _get_net(args)
    # parse target marking from command line: place=value pairs
    target: dict[str, int] = {}
    for pair in args.target:
        if "=" not in pair:
            print(f"Error: expected place=value, got '{pair}'", file=sys.stderr)
            return 1
        name, val = pair.split("=", 1)
        target[name.strip()] = int(val.strip())
    result = is_reachable(net, target, max_states=args.max_states)
    print(f"Target marking {target} is {'reachable' if result else 'NOT reachable'}")
    return 0


def cmd_cover(args: argparse.Namespace) -> int:
    """Build and display the coverability tree."""
    net = _get_net(args)
    tree = coverability_tree(net, max_nodes=args.max_nodes)
    print(f"Coverability Tree: {len(tree.nodes)} nodes, {len(tree.edges)} edges")
    print(f"Unbounded: {tree.is_unbounded}")
    if tree.omega_places:
        print(f"Unbounded places (ω): {sorted(tree.omega_places)}")
    print()
    for node_id, node in tree.nodes.items():
        marking_str = ", ".join(
            f"{k}=ω" if v == -1 else f"{k}={v}"
            for k, v in sorted(node.marking.items())
        )
        flags = []
        if node_id == tree.initial_id:
            flags.append("initial")
        if node.is_terminal:
            flags.append("terminal")
        if node.has_omega:
            flags.append("ω")
        flag_str = f" [{', '.join(flags)}]" if flags else ""
        print(f"  {node_id}{flag_str}")
        print(f"    [{marking_str}]")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    net = _get_net(args)
    print(ascii_net(net))
    print()
    print("Initial marking:")
    print(f"  {ascii_marking(net.initial_marking(), net)}")
    return 0


def cmd_fire(args: argparse.Namespace) -> int:
    net = _get_net(args)
    sim = Simulator(net, seed=args.seed)
    result = sim.run_sequence(args.transitions, strict=not args.lenient)
    print(f"Fired {result.steps_fired}/{len(args.transitions)} transitions")
    print(f"Deadlocked: {result.deadlocked}")
    print(f"Final marking: {ascii_marking(result.final_marking, net)}")
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    net = _get_net(args)
    if args.format == "json":
        print(net.to_json())
    elif args.format == "dot":
        rg = reachability_graph(net, max_states=args.max_states)
        print(reachability_dot(rg))
    elif args.format == "pnml":
        print(to_pnml(net))
    elif args.format == "config":
        from .config import to_config_dict
        print(json.dumps(to_config_dict(net), indent=2))
    return 0


def cmd_presets(args: argparse.Namespace) -> int:
    print("Available presets:")
    for name in sorted(PRESETS):
        net = PRESETS[name]()
        print(f"  {name:25s}  ({len(net.places)} places, {len(net.transitions)} transitions)")
    return 0


def cmd_batch(args: argparse.Namespace) -> int:
    """Run batch simulations and report statistics."""
    net = _get_net(args)
    stats = batch_simulate(
        net,
        num_runs=args.runs,
        max_steps=args.steps,
        seed=args.seed,
    )
    print(stats)
    if args.json:
        print()
        print(json.dumps({
            "num_runs": stats.num_runs,
            "deadlock_probability": stats.deadlock_probability,
            "deadlock_ci": [stats.deadlock_ci_low, stats.deadlock_ci_high],
            "mean_steps": stats.mean_steps,
            "std_steps": stats.std_steps,
            "transition_fire_frequencies": stats.transition_fire_frequencies,
        }, indent=2))
    return 0


def cmd_steady_state(args: argparse.Namespace) -> int:
    """Compute steady-state probabilities for a stochastic Petri net."""
    net = _get_net(args)
    spn = StochasticPetriNet(net)

    # Parse rates from command line: transition=rate pairs
    if args.rates:
        for pair in args.rates:
            if "=" not in pair:
                print(f"Error: expected transition=rate, got '{pair}'", file=sys.stderr)
                return 1
            name, rate = pair.split("=", 1)
            spn.set_rate(name.strip(), float(rate.strip()))

    ctmc = build_ctmc(spn, max_states=args.max_states)
    print(f"CTMC: {ctmc.num_states} states")

    probs = steady_state_probabilities(ctmc)
    print("\nSteady-state probabilities:")
    for sid, prob in sorted(probs.items(), key=lambda x: -x[1]):
        marking_str = ", ".join(
            f"{k}={v}" for k, v in sorted(ctmc.states[sid].marking.items())
        )
        print(f"  {sid} (prob={prob:.6f}): [{marking_str}]")
    return 0


def cmd_expected_time(args: argparse.Namespace) -> int:
    """Compute expected time to reach a target marking."""
    net = _get_net(args)
    spn = StochasticPetriNet(net)

    if args.rates:
        for pair in args.rates:
            if "=" not in pair:
                print(f"Error: expected transition=rate, got '{pair}'", file=sys.stderr)
                return 1
            name, rate = pair.split("=", 1)
            spn.set_rate(name.strip(), float(rate.strip()))

    target: dict[str, int] = {}
    for pair in args.target:
        if "=" not in pair:
            print(f"Error: expected place=value, got '{pair}'", file=sys.stderr)
            return 1
        name, val = pair.split("=", 1)
        target[name.strip()] = int(val.strip())

    result = expected_time_to_target(spn, target, max_states=args.max_states)
    print(f"Expected time to reach {target}: {result.expected_time:.4f}")
    print(f"Target reachable: {result.found_target}")
    return 0


def cmd_pnml(args: argparse.Namespace) -> int:
    """Export/import/validate PNML."""
    if args.action == "export":
        net = _get_net(args)
        print(to_pnml(net))
    elif args.action == "import":
        if not args.pnml_file:
            print("Error: --pnml-file required for import", file=sys.stderr)
            return 1
        with open(args.pnml_file) as f:
            net = from_pnml(f.read())
        print(f"Imported: {net}")
        print(ascii_net(net))
    elif args.action == "validate":
        if not args.pnml_file:
            print("Error: --pnml-file required for validate", file=sys.stderr)
            return 1
        with open(args.pnml_file) as f:
            issues = validate_pnml(f.read())
        if issues:
            print(f"PNML validation found {len(issues)} issue(s):")
            for issue in issues:
                print(f"  - {issue}")
            return 1
        else:
            print("PNML is valid ✓")
    return 0


def cmd_config(args: argparse.Namespace) -> int:
    """Export/import config files."""
    if args.action == "export":
        net = _get_net(args)
        save_config(net, args.output, format=args.format)
        print(f"Saved config to {args.output}")
    elif args.action == "import":
        net = load_config(args.input)
        print(f"Loaded: {net}")
        print(ascii_net(net))
    elif args.action == "show":
        net = load_config(args.input)
        print(ascii_net(net))
        print()
        print("Initial marking:")
        print(f"  {ascii_marking(net.initial_marking(), net)}")
    return 0


def cmd_monte_carlo(args: argparse.Namespace) -> int:
    """Run Monte Carlo simulation."""
    net = _get_net(args)
    result = monte_carlo(net, num_runs=args.runs, max_steps=args.steps, seed=args.seed)
    print(result)
    return 0


def _get_net(args: argparse.Namespace) -> PetriNet:
    if args.preset:
        if args.preset not in PRESETS:
            print(f"Unknown preset: {args.preset}", file=sys.stderr)
            print(f"Available: {', '.join(sorted(PRESETS))}", file=sys.stderr)
            sys.exit(1)
        return PRESETS[args.preset]()
    elif args.file:
        with open(args.file) as f:
            return PetriNet.from_json(f.read())
    else:
        print("Error: must specify --preset or --file", file=sys.stderr)
        sys.exit(1)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="petri",
        description="Petri net (P/T net) simulator and analysis toolkit",
    )
    parser.add_argument("--preset", help="Use a preset net")
    parser.add_argument("--file", "-f", help="Load net from JSON file")
    parser.add_argument("--seed", type=int, default=None, help="Random seed")
    parser.add_argument("--log-level", default="WARNING",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                        help="Logging verbosity")
    parser.add_argument("--log-file", default=None, help="Log to file")

    sub = parser.add_subparsers(dest="command", required=True)

    p_sim = sub.add_parser("simulate", help="Run a random-walk simulation")
    p_sim.add_argument("--steps", type=int, default=100)
    p_sim.add_argument("--trace", action="store_true", help="Print full trace")
    p_sim.set_defaults(func=cmd_simulate)

    p_reach = sub.add_parser("reachability", help="Build reachability graph")
    p_reach.add_argument("--dot", action="store_true", help="Output as DOT")
    p_reach.add_argument("--max-states", type=int, default=10000)
    p_reach.set_defaults(func=cmd_reachability)

    p_inv = sub.add_parser("invariants", help="Compute T/P invariants")
    p_inv.add_argument("--type", choices=["t", "p", "both"], default="both")
    p_inv.set_defaults(func=cmd_invariants)

    p_an = sub.add_parser("analyze", help="Full analysis: boundedness, liveness, reversibility, traps/siphons")
    p_an.add_argument("--max-states", type=int, default=10000)
    p_an.set_defaults(func=cmd_analyze)

    p_reach_target = sub.add_parser("reachable", help="Check if a target marking is reachable")
    p_reach_target.add_argument("target", nargs="+", help="Target marking as place=value pairs")
    p_reach_target.add_argument("--max-states", type=int, default=10000)
    p_reach_target.set_defaults(func=cmd_reachable)

    p_cover = sub.add_parser("cover", help="Build coverability tree (Karp-Miller)")
    p_cover.add_argument("--max-nodes", type=int, default=50000)
    p_cover.set_defaults(func=cmd_cover)

    p_show = sub.add_parser("show", help="Show net structure")
    p_show.set_defaults(func=cmd_show)

    p_fire = sub.add_parser("fire", help="Fire a specific sequence of transitions")
    p_fire.add_argument("transitions", nargs="+", help="Transition names in order")
    p_fire.add_argument("--lenient", action="store_true", help="Stop on disabled transition instead of erroring")
    p_fire.set_defaults(func=cmd_fire)

    p_exp = sub.add_parser("export", help="Export net or reachability graph")
    p_exp.add_argument("--format", choices=["json", "dot", "pnml", "config"], default="json")
    p_exp.add_argument("--max-states", type=int, default=10000)
    p_exp.set_defaults(func=cmd_export)

    p_pre = sub.add_parser("presets", help="List available presets")
    p_pre.set_defaults(func=cmd_presets)

    # New: batch simulation
    p_batch = sub.add_parser("batch", help="Run batch simulations with statistics")
    p_batch.add_argument("--runs", type=int, default=1000, help="Number of simulation runs")
    p_batch.add_argument("--steps", type=int, default=1000, help="Max steps per run")
    p_batch.add_argument("--json", action="store_true", help="Also output JSON summary")
    p_batch.set_defaults(func=cmd_batch)

    # New: steady-state analysis
    p_ss = sub.add_parser("steady-state", help="Compute steady-state probabilities (stochastic PN)")
    p_ss.add_argument("--rates", nargs="*", help="Transition firing rates as name=rate pairs")
    p_ss.add_argument("--max-states", type=int, default=10000)
    p_ss.set_defaults(func=cmd_steady_state)

    # New: expected time to target
    p_et = sub.add_parser("expected-time", help="Expected time to reach a target marking")
    p_et.add_argument("target", nargs="+", help="Target marking as place=value pairs")
    p_et.add_argument("--rates", nargs="*", help="Transition firing rates as name=rate pairs")
    p_et.add_argument("--max-states", type=int, default=10000)
    p_et.set_defaults(func=cmd_expected_time)

    # New: PNML
    p_pnml = sub.add_parser("pnml", help="PNML (XML) export/import/validate")
    p_pnml.add_argument("action", choices=["export", "import", "validate"])
    p_pnml.add_argument("--pnml-file", help="PNML file for import/validate")
    p_pnml.set_defaults(func=cmd_pnml)

    # New: config files
    p_cfg = sub.add_parser("config", help="Config file (JSON/YAML) export/import")
    p_cfg.add_argument("action", choices=["export", "import", "show"])
    p_cfg.add_argument("--input", help="Input config file")
    p_cfg.add_argument("--output", help="Output config file")
    p_cfg.add_argument("--format", choices=["json", "yaml"], default="json")
    p_cfg.set_defaults(func=cmd_config)

    # New: Monte Carlo
    p_mc = sub.add_parser("monte-carlo", help="Monte Carlo simulation with deadlock estimation")
    p_mc.add_argument("--runs", type=int, default=1000, help="Number of simulation runs")
    p_mc.add_argument("--steps", type=int, default=1000, help="Max steps per run")
    p_mc.set_defaults(func=cmd_monte_carlo)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # Setup logging
    setup_logging(level=args.log_level, log_file=args.log_file)

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())