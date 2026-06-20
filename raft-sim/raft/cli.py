"""Command-line interface for the Raft simulator."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from raft import Cluster, NetworkConfig
from raft.network import Network
from raft.types import NodeRole


def cmd_run(args: argparse.Namespace) -> int:
    """Run a simulation and print the final cluster state."""
    net_cfg = NetworkConfig(
        base_latency=args.latency,
        jitter=args.jitter,
        drop_rate=args.drop_rate,
        seed=args.seed,
    )
    cluster = Cluster(
        size=args.size,
        network_config=net_cfg,
        election_timeout_range=(args.election_min, args.election_max),
        heartbeat_interval=args.heartbeat,
        snapshot_threshold=args.snapshot_threshold,
        seed=args.seed,
    )

    # Run until leader elected.
    leader = cluster.run_until_leader(timeout=args.timeout)
    if leader is None:
        print("No leader elected within timeout.")
        return 1

    print(f"Leader elected: node {leader} (term {cluster.nodes[leader].state.current_term})")

    # Submit commands if provided.
    if args.commands:
        for cmd_str in args.commands:
            parts = cmd_str.split("=")
            if len(parts) == 2:
                cluster.submit("set", parts[0], parts[1])
            else:
                cluster.submit("noop")
        cluster.run_for(args.duration)

    # Run for the specified duration.
    if not args.commands:
        cluster.run_for(args.duration)

    # Print final status.
    print()
    print(cluster.summary())

    # Print event log if requested.
    if args.events:
        print("\nEvents:")
        for t, event, data in cluster.event_log():
            print(f"  [{t:7.1f}] {event.value}: {data}")

    # JSON output.
    if args.json:
        print()
        print(json.dumps(cluster.status(), indent=2, default=str))

    return 0


def cmd_partition(args: argparse.Namespace) -> int:
    """Run a simulation with a network partition and recovery."""
    net_cfg = NetworkConfig(
        base_latency=args.latency,
        jitter=args.jitter,
        seed=args.seed,
    )
    cluster = Cluster(
        size=args.size,
        network_config=net_cfg,
        seed=args.seed,
    )

    leader = cluster.run_until_leader(timeout=args.timeout)
    if leader is None:
        print("No leader elected.")
        return 1
    print(f"Initial leader: node {leader}")

    # Submit some commands.
    for i in range(args.commands_count):
        cluster.submit("set", f"k{i}", i)
    cluster.run_for(20)
    print(f"Committed {args.commands_count} commands. Log consistent: {cluster.log_consistent()}")

    # Partition the leader.
    print(f"\nPartitioning leader {leader} for {args.partition_duration} time units...")
    cluster.partition_node(leader)
    cluster.run_for(args.partition_duration)

    new_leader = cluster.get_leader()
    print(f"New leader during partition: {new_leader}")

    # Heal.
    print("\nHealing partition...")
    cluster.heal_all()
    cluster.run_for(args.duration)
    print(f"Final leader: {cluster.get_leader()}")
    print(f"Log consistent after healing: {cluster.log_consistent()}")

    # Verify all values.
    ok = True
    for i in range(args.commands_count):
        val = cluster.all_agree(f"k{i}")
        if val != i:
            print(f"  MISMATCH: k{i} = {val} (expected {i})")
            ok = False
    if ok:
        print(f"All {args.commands_count} values consistent after recovery.")

    print()
    print(cluster.summary())
    return 0 if ok else 1


def cmd_election(args: argparse.Namespace) -> int:
    """Run repeated elections to observe split-vote and term progression."""
    net_cfg = NetworkConfig(
        base_latency=args.latency,
        jitter=args.jitter,
        seed=args.seed,
    )
    cluster = Cluster(
        size=args.size,
        network_config=net_cfg,
        seed=args.seed,
    )

    print(f"Running {args.rounds} election rounds (size={args.size})...\n")
    leaders = []
    for r in range(args.rounds):
        # Reset election timers to force new elections.
        for node in cluster.nodes.values():
            if node.is_leader:
                # Force step-down by partitioning then healing.
                cluster.partition_node(node.id)
                cluster.run_for(15)
                cluster.heal_all()
                cluster.run_for(30)
                break
        else:
            cluster.run_for(20)

        leader = cluster.get_leader()
        leaders.append(leader)
        term = cluster.nodes[leader].state.current_term if leader is not None else 0
        print(f"  Round {r + 1}: leader={leader}, term={term}")

    print(f"\nLeader changes: {cluster.stats.leader_changes}")
    print(f"Total elections: {sum(n.stats.elections_started for n in cluster.nodes.values())}")
    return 0


def cmd_scenario(args: argparse.Namespace) -> int:
    """Run a pre-defined failure scenario."""
    from raft.scenarios import (
        leader_partition_scenario,
        split_brain_scenario,
        rolling_partition_scenario,
        flaky_network_scenario,
        cascading_failure_scenario,
        run_scenario,
    )

    scenario_map = {
        "leader": leader_partition_scenario,
        "split": split_brain_scenario,
        "rolling": rolling_partition_scenario,
        "flaky": lambda: flaky_network_scenario(args.drop_rate),
        "cascading": cascading_failure_scenario,
    }

    if args.scenario not in scenario_map:
        print(f"Unknown scenario: {args.scenario}")
        print(f"Available: {', '.join(scenario_map.keys())}")
        return 1

    net_cfg = NetworkConfig(
        base_latency=args.latency,
        jitter=args.jitter,
        seed=args.seed,
    )
    cluster = Cluster(
        size=args.size,
        network_config=net_cfg,
        seed=args.seed,
    )

    leader = cluster.run_until_leader(timeout=args.timeout)
    if leader is None:
        print("No leader elected.")
        return 1
    print(f"Initial leader: node {leader}")

    # Submit some commands first.
    for i in range(args.commands):
        cluster.submit("set", f"k{i}", i)
    cluster.run_for(15)
    print(f"Committed {args.commands} commands.")

    steps = scenario_map[args.scenario]()
    print(f"\nRunning scenario: {args.scenario} ({len(steps)} steps)\n")
    results = run_scenario(cluster, steps, verbose=True)

    print(f"\nFinal leader: {results['final_leader']}")
    print(f"Log consistent: {results['log_consistent']}")
    print(f"Leader changes: {results['leader_changes']}")

    # Check invariants.
    from raft.invariants import check_all
    report = check_all(cluster)
    print(f"\n{report.summary()}")

    # Visualize.
    if args.visualize:
        from raft.visualizer import render_cluster_ascii
        print()
        print(render_cluster_ascii(cluster))

    return 0 if results["log_consistent"] else 1


def cmd_visualize(args: argparse.Namespace) -> int:
    """Run a simulation and render ASCII visualization."""
    from raft.visualizer import (
        render_cluster_ascii,
        render_partition_matrix,
        render_log_diff,
        render_timeline,
    )

    net_cfg = NetworkConfig(
        base_latency=args.latency,
        jitter=args.jitter,
        seed=args.seed,
    )
    cluster = Cluster(
        size=args.size,
        network_config=net_cfg,
        snapshot_threshold=args.snapshot_threshold,
        seed=args.seed,
    )

    leader = cluster.run_until_leader(timeout=args.timeout)
    if leader is None:
        print("No leader elected.")
        return 1

    # Submit commands.
    for i in range(args.commands):
        cluster.submit("set", f"k{i}", i)
    cluster.run_for(args.duration)

    print(render_cluster_ascii(cluster))
    print()
    print(render_partition_matrix(cluster))
    print()
    print(render_log_diff(cluster))
    print()
    print(render_timeline(cluster.event_log()))
    return 0


def cmd_invariants(args: argparse.Namespace) -> int:
    """Run a simulation and check all Raft safety invariants."""
    from raft.invariants import check_all

    net_cfg = NetworkConfig(
        base_latency=args.latency,
        jitter=args.jitter,
        seed=args.seed,
    )
    cluster = Cluster(
        size=args.size,
        network_config=net_cfg,
        seed=args.seed,
    )

    leader = cluster.run_until_leader(timeout=args.timeout)
    if leader is None:
        print("No leader elected.")
        return 1

    # Submit commands and run.
    for i in range(args.commands):
        cluster.submit("set", f"k{i}", i)
    cluster.run_for(args.duration)

    # Optionally partition and heal.
    if args.partition:
        cluster.partition_node(leader)
        cluster.run_for(30)
        cluster.heal_all()
        cluster.run_for(30)

    report = check_all(cluster)
    print(report.summary())
    if args.verbose:
        print()
        print(cluster.summary())
    return 0 if report.passed else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="raft-sim",
        description="Raft consensus algorithm simulator",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # run
    p_run = sub.add_parser("run", help="Run a basic simulation")
    p_run.add_argument("--size", type=int, default=5, help="Cluster size (default 5)")
    p_run.add_argument("--timeout", type=float, default=100, help="Election timeout")
    p_run.add_argument("--duration", type=float, default=30, help="Simulation duration")
    p_run.add_argument("--latency", type=float, default=1.0, help="Network base latency")
    p_run.add_argument("--jitter", type=float, default=0.5, help="Network jitter")
    p_run.add_argument("--drop-rate", type=float, default=0.0, help="Packet drop rate")
    p_run.add_argument("--heartbeat", type=float, default=1.0, help="Heartbeat interval")
    p_run.add_argument("--election-min", type=float, default=5.0)
    p_run.add_argument("--election-max", type=float, default=10.0)
    p_run.add_argument("--snapshot-threshold", type=int, default=50)
    p_run.add_argument("--seed", type=int, default=None)
    p_run.add_argument("--commands", nargs="*", default=None, help="Commands as key=value")
    p_run.add_argument("--events", action="store_true", help="Print event log")
    p_run.add_argument("--json", action="store_true", help="Print JSON status")
    p_run.set_defaults(func=cmd_run)

    # partition
    p_part = sub.add_parser("partition", help="Run a partition-recovery simulation")
    p_part.add_argument("--size", type=int, default=5)
    p_part.add_argument("--timeout", type=float, default=100)
    p_part.add_argument("--duration", type=float, default=30)
    p_part.add_argument("--latency", type=float, default=1.0)
    p_part.add_argument("--jitter", type=float, default=0.5)
    p_part.add_argument("--partition-duration", type=float, default=30)
    p_part.add_argument("--commands-count", type=int, default=5)
    p_part.add_argument("--seed", type=int, default=None)
    p_part.set_defaults(func=cmd_partition)

    # election
    p_elec = sub.add_parser("election", help="Run repeated elections")
    p_elec.add_argument("--size", type=int, default=5)
    p_elec.add_argument("--rounds", type=int, default=5)
    p_elec.add_argument("--latency", type=float, default=1.0)
    p_elec.add_argument("--jitter", type=float, default=0.5)
    p_elec.add_argument("--seed", type=int, default=None)
    p_elec.set_defaults(func=cmd_election)

    # scenario
    p_scen = sub.add_parser("scenario", help="Run a pre-defined failure scenario")
    p_scen.add_argument("scenario", choices=["leader", "split", "rolling", "flaky", "cascading"])
    p_scen.add_argument("--size", type=int, default=5)
    p_scen.add_argument("--timeout", type=float, default=100)
    p_scen.add_argument("--latency", type=float, default=1.0)
    p_scen.add_argument("--jitter", type=float, default=0.5)
    p_scen.add_argument("--drop-rate", type=float, default=0.3)
    p_scen.add_argument("--commands", type=int, default=5)
    p_scen.add_argument("--seed", type=int, default=None)
    p_scen.add_argument("--visualize", action="store_true")
    p_scen.set_defaults(func=cmd_scenario)

    # visualize
    p_vis = sub.add_parser("visualize", help="Run simulation and render ASCII diagrams")
    p_vis.add_argument("--size", type=int, default=5)
    p_vis.add_argument("--timeout", type=float, default=100)
    p_vis.add_argument("--latency", type=float, default=1.0)
    p_vis.add_argument("--jitter", type=float, default=0.5)
    p_vis.add_argument("--duration", type=float, default=30)
    p_vis.add_argument("--commands", type=int, default=10)
    p_vis.add_argument("--snapshot-threshold", type=int, default=50)
    p_vis.add_argument("--seed", type=int, default=None)
    p_vis.set_defaults(func=cmd_visualize)

    # invariants
    p_inv = sub.add_parser("invariants", help="Check Raft safety invariants")
    p_inv.add_argument("--size", type=int, default=5)
    p_inv.add_argument("--timeout", type=float, default=100)
    p_inv.add_argument("--latency", type=float, default=1.0)
    p_inv.add_argument("--jitter", type=float, default=0.5)
    p_inv.add_argument("--duration", type=float, default=30)
    p_inv.add_argument("--commands", type=int, default=10)
    p_inv.add_argument("--partition", action="store_true", help="Also test partition recovery")
    p_inv.add_argument("--verbose", action="store_true")
    p_inv.add_argument("--seed", type=int, default=None)
    p_inv.set_defaults(func=cmd_invariants)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())