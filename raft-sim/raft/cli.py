"""Command-line interface for the Raft simulator."""

from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Any

from raft import Cluster, NetworkConfig
from raft.logging_utils import configure_logging
from raft.network import Network
from raft.types import NodeRole


def _build_cluster_from_config(args: argparse.Namespace) -> Cluster:
    """Build a Cluster from CLI args, optionally loading a config file."""
    if getattr(args, "config", None):
        from raft.config import load_config
        cfg = load_config(args.config)
        return Cluster(
            size=cfg.size,
            network_config=cfg.network,
            seed=cfg.seed,
            election_timeout_range=cfg.election_timeout_range,
            heartbeat_interval=cfg.heartbeat_interval,
            snapshot_threshold=cfg.snapshot_threshold,
            prevote_enabled=cfg.prevote_enabled,
            linearizable_reads=cfg.linearizable_reads,
        )
    net_cfg = NetworkConfig(
        base_latency=args.latency,
        jitter=args.jitter,
        drop_rate=args.drop_rate,
        seed=args.seed,
    )
    return Cluster(
        size=args.size,
        network_config=net_cfg,
        election_timeout_range=(args.election_min, args.election_max),
        heartbeat_interval=args.heartbeat,
        snapshot_threshold=args.snapshot_threshold,
        seed=args.seed,
        prevote_enabled=not getattr(args, "no_prevote", False),
    )


def cmd_run(args: argparse.Namespace) -> int:
    """Run a simulation and print the final cluster state."""
    if args.verbose:
        configure_logging(level="DEBUG")
    cluster = _build_cluster_from_config(args)

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
    cluster = _build_cluster_from_config(args)

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
    cluster = _build_cluster_from_config(args)

    print(f"Running {args.rounds} election rounds (size={cluster.size})...\n")
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

    cluster = _build_cluster_from_config(args)

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

    cluster = _build_cluster_from_config(args)

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

    cluster = _build_cluster_from_config(args)

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


def cmd_benchmark(args: argparse.Namespace) -> int:
    """Benchmark cluster throughput under various conditions."""
    print(f"Raft-Sim Benchmark (size={args.size}, commands={args.commands})")
    print("=" * 60)

    results: list[dict[str, Any]] = []

    for drop_rate in [0.0, 0.1, 0.3]:
        for latency in [0.5, 1.0, 2.0]:
            net_cfg = NetworkConfig(
                base_latency=latency,
                jitter=0.3,
                drop_rate=drop_rate,
                seed=args.seed,
            )
            cluster = Cluster(
                size=args.size,
                network_config=net_cfg,
                seed=args.seed,
                snapshot_threshold=args.snapshot_threshold,
            )

            wall_start = time.time()
            leader = cluster.run_until_leader(timeout=200)
            if leader is None:
                results.append({
                    "drop_rate": drop_rate,
                    "latency": latency,
                    "leader": None,
                    "sim_time": 0,
                    "wall_time": 0,
                    "throughput": 0,
                })
                continue

            # Submit commands one at a time and measure.
            for i in range(args.commands):
                cluster.submit("set", f"bk{i}", i)
            cluster.run_for(args.duration)

            wall_end = time.time()
            sim_time = cluster.network.time
            wall_elapsed = wall_end - wall_start
            committed = cluster.stats.commands_committed
            throughput = committed / wall_elapsed if wall_elapsed > 0 else 0

            entry = {
                "drop_rate": drop_rate,
                "latency": latency,
                "leader": leader,
                "sim_time": sim_time,
                "wall_time": f"{wall_elapsed:.3f}",
                "committed": committed,
                "throughput": f"{throughput:.1f} cmd/s",
            }
            results.append(entry)
            print(
                f"  drop={drop_rate:.1f} lat={latency:.1f}  "
                f"committed={committed:4d}  "
                f"wall={wall_elapsed:.3f}s  "
                f"throughput={throughput:.1f} cmd/s"
            )

    if args.json:
        print()
        print(json.dumps(results, indent=2))
    return 0


def cmd_crash_recovery(args: argparse.Namespace) -> int:
    """Simulate node crashes and recoveries."""
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

    print("=== Crash & Recovery Simulation ===\n")

    leader = cluster.run_until_leader(timeout=100)
    if leader is None:
        print("No leader elected.")
        return 1
    print(f"Initial leader: node {leader}")

    # Submit initial commands.
    for i in range(5):
        cluster.submit("set", f"k{i}", i)
    cluster.run_for(20)
    print(f"Committed 5 commands. Consistent: {cluster.log_consistent()}")

    # Crash a follower.
    follower = [n for n in cluster.nodes if n != leader][0]
    print(f"\n>> Crashing follower {follower}...")
    cluster.crash_node(follower)
    cluster.run_for(15)
    print(f"  Crashed nodes: {cluster.crashed_nodes()}")
    print(f"  Alive nodes: {cluster.alive_nodes()}")
    print(f"  Leader: {cluster.get_leader()}")

    # Submit more commands while follower is down.
    for i in range(5, 10):
        cluster.submit("set", f"k{i}", i)
    cluster.run_for(20)
    print(f"  Committed 5 more commands (follower down)")

    # Restart the follower.
    print(f"\n>> Restarting follower {follower}...")
    cluster.restart_node(follower)
    cluster.run_for(40)
    print(f"  Crashed nodes: {cluster.crashed_nodes()}")
    print(f"  Follower {follower} commit_index: {cluster.nodes[follower].state.commit_index}")

    # Verify consistency.
    ok = True
    for i in range(10):
        val = cluster.all_agree(f"k{i}")
        if val != i:
            print(f"  MISMATCH: k{i} = {val} (expected {i})")
            ok = False

    if ok:
        print(f"\nAll 10 values consistent after crash recovery! ✓")

    # Now crash the leader.
    current_leader = cluster.get_leader()
    assert current_leader is not None, "Should have a leader"
    print(f"\n>> Crashing leader {current_leader}...")
    cluster.crash_node(current_leader)
    cluster.run_for(30)
    new_leader = cluster.get_leader()
    print(f"  New leader: {new_leader}")

    # Restart old leader.
    print(f"\n>> Restarting old leader {current_leader}...")
    cluster.restart_node(current_leader)
    cluster.run_for(40)
    print(f"  Final leader: {cluster.get_leader()}")
    print(f"  Log consistent: {cluster.log_consistent()}")

    # Check invariants.
    report = check_all(cluster)
    print(f"\n{report.summary()}")

    print(f"\n{cluster.summary()}")
    return 0 if report.passed else 1


def cmd_config_show(args: argparse.Namespace) -> int:
    """Show or generate a configuration file."""
    from raft.config import ClusterConfig, save_config

    cfg = ClusterConfig(
        size=args.size,
        seed=args.seed,
        election_timeout_range=(args.election_min, args.election_max),
        heartbeat_interval=args.heartbeat,
        snapshot_threshold=args.snapshot_threshold,
        network=NetworkConfig(
            base_latency=args.latency,
            jitter=args.jitter,
            drop_rate=args.drop_rate,
            seed=args.seed,
        ),
        prevote_enabled=not args.no_prevote,
    )

    if args.output:
        save_config(cfg, args.output)
        print(f"Config written to {args.output}")
    else:
        # Print as YAML to stdout.
        import yaml
        data = {
            "cluster": {
                "size": cfg.size,
                "seed": cfg.seed,
                "election_timeout_range": list(cfg.election_timeout_range),
                "heartbeat_interval": cfg.heartbeat_interval,
                "snapshot_threshold": cfg.snapshot_threshold,
                "prevote_enabled": cfg.prevote_enabled,
                "crash_recovery_enabled": cfg.crash_recovery_enabled,
                "linearizable_reads": cfg.linearizable_reads,
            },
            "network": {
                "base_latency": cfg.network.base_latency,
                "jitter": cfg.network.jitter,
                "drop_rate": cfg.network.drop_rate,
                "reorder": cfg.network.reorder,
                "seed": cfg.network.seed,
            },
        }
        print(yaml.dump(data, default_flow_style=False, sort_keys=False))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="raft-sim",
        description="Raft consensus algorithm simulator (v2.0)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # Common args helper.
    def add_common_args(p: argparse.ArgumentParser) -> None:
        p.add_argument("--config", type=str, default=None, help="Path to YAML/JSON config file")
        p.add_argument("--size", type=int, default=5, help="Cluster size (default 5)")
        p.add_argument("--timeout", type=float, default=100, help="Election timeout")
        p.add_argument("--duration", type=float, default=30, help="Simulation duration")
        p.add_argument("--latency", type=float, default=1.0, help="Network base latency")
        p.add_argument("--jitter", type=float, default=0.5, help="Network jitter")
        p.add_argument("--drop-rate", type=float, default=0.0, help="Packet drop rate")
        p.add_argument("--heartbeat", type=float, default=1.0, help="Heartbeat interval")
        p.add_argument("--election-min", type=float, default=5.0)
        p.add_argument("--election-max", type=float, default=10.0)
        p.add_argument("--snapshot-threshold", type=int, default=50)
        p.add_argument("--seed", type=int, default=None)
        p.add_argument("--no-prevote", action="store_true", help="Disable PreVote optimization")

    # run
    p_run = sub.add_parser("run", help="Run a basic simulation")
    add_common_args(p_run)
    p_run.add_argument("--commands", nargs="*", default=None, help="Commands as key=value")
    p_run.add_argument("--events", action="store_true", help="Print event log")
    p_run.add_argument("--json", action="store_true", help="Print JSON status")
    p_run.add_argument("--verbose", action="store_true", help="Enable debug logging")
    p_run.set_defaults(func=cmd_run)

    # partition
    p_part = sub.add_parser("partition", help="Run a partition-recovery simulation")
    add_common_args(p_part)
    p_part.add_argument("--partition-duration", type=float, default=30)
    p_part.add_argument("--commands-count", type=int, default=5)
    p_part.set_defaults(func=cmd_partition)

    # election
    p_elec = sub.add_parser("election", help="Run repeated elections")
    add_common_args(p_elec)
    p_elec.add_argument("--rounds", type=int, default=5)
    p_elec.set_defaults(func=cmd_election)

    # scenario
    p_scen = sub.add_parser("scenario", help="Run a pre-defined failure scenario")
    add_common_args(p_scen)
    p_scen.add_argument("scenario", choices=["leader", "split", "rolling", "flaky", "cascading"])
    p_scen.add_argument("--commands", type=int, default=5)
    p_scen.add_argument("--visualize", action="store_true")
    p_scen.set_defaults(func=cmd_scenario)

    # visualize
    p_vis = sub.add_parser("visualize", help="Run simulation and render ASCII diagrams")
    add_common_args(p_vis)
    p_vis.add_argument("--commands", type=int, default=10)
    p_vis.set_defaults(func=cmd_visualize)

    # invariants
    p_inv = sub.add_parser("invariants", help="Check Raft safety invariants")
    add_common_args(p_inv)
    p_inv.add_argument("--commands", type=int, default=10)
    p_inv.add_argument("--partition", action="store_true", help="Also test partition recovery")
    p_inv.add_argument("--verbose", action="store_true")
    p_inv.set_defaults(func=cmd_invariants)

    # benchmark
    p_bench = sub.add_parser("benchmark", help="Benchmark throughput under various network conditions")
    add_common_args(p_bench)
    p_bench.add_argument("--commands", type=int, default=50)
    p_bench.add_argument("--json", action="store_true", help="Print results as JSON")
    p_bench.set_defaults(func=cmd_benchmark)

    # crash-recovery
    p_crash = sub.add_parser("crash", help="Simulate node crashes and recoveries")
    add_common_args(p_crash)
    p_crash.set_defaults(func=cmd_crash_recovery)

    # config
    p_cfg = sub.add_parser("config", help="Show or generate a configuration file")
    add_common_args(p_cfg)
    p_cfg.add_argument("--output", "-o", type=str, default=None, help="Write config to file")
    p_cfg.set_defaults(func=cmd_config_show)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())