"""Command-line interface for the Petri net simulator."""

from __future__ import annotations

import argparse
import json
import sys

from . import (
    PetriNet, Place, Transition,
    Simulator,
    compute_t_invariants, compute_p_invariants,
    reachability_graph, analyze_boundedness, analyze_liveness,
    ascii_net, ascii_marking, reachability_ascii, reachability_dot,
)
from .presets import (
    dining_philosophers, producer_consumer, mutual_exclusion,
    workflow_net, state_machine, free_choice_net, readers_writers, simple_buffer,
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
    return 0


def cmd_presets(args: argparse.Namespace) -> int:
    print("Available presets:")
    for name in sorted(PRESETS):
        net = PRESETS[name]()
        print(f"  {name:25s}  ({len(net.places)} places, {len(net.transitions)} transitions)")
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

    p_an = sub.add_parser("analyze", help="Full analysis: boundedness + liveness")
    p_an.add_argument("--max-states", type=int, default=10000)
    p_an.set_defaults(func=cmd_analyze)

    p_show = sub.add_parser("show", help="Show net structure")
    p_show.set_defaults(func=cmd_show)

    p_fire = sub.add_parser("fire", help="Fire a specific sequence of transitions")
    p_fire.add_argument("transitions", nargs="+", help="Transition names in order")
    p_fire.add_argument("--lenient", action="store_true", help="Stop on disabled transition instead of erroring")
    p_fire.set_defaults(func=cmd_fire)

    p_exp = sub.add_parser("export", help="Export net or reachability graph")
    p_exp.add_argument("--format", choices=["json", "dot"], default="json")
    p_exp.add_argument("--max-states", type=int, default=10000)
    p_exp.set_defaults(func=cmd_export)

    p_pre = sub.add_parser("presets", help="List available presets")
    p_pre.set_defaults(func=cmd_presets)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())