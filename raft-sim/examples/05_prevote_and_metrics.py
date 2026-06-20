"""Example: PreVote optimization and metrics collection.

Demonstrates the PreVote optimization (Raft §6) which prevents
disruptive elections when a partitioned node reconnects, and shows
how to collect metrics via the observer system.
"""
from raft import (
    Cluster,
    NetworkConfig,
    MetricsCollector,
    ClusterEvent,
)


def main():
    collector = MetricsCollector()

    cluster = Cluster(
        size=5,
        seed=42,
        network_config=NetworkConfig(seed=42),
        prevote_enabled=True,
    )
    cluster.add_observer(collector)

    print("=== PreVote & Metrics Example ===\n")
    print(f"PreVote enabled: {cluster.nodes[0].prevote_enabled}")

    leader = cluster.run_until_leader(timeout=200)
    print(f"Leader elected: node {leader}")

    # Submit commands.
    cluster.submit("set", "x", 42)
    cluster.submit("set", "y", 99)
    cluster.run_for(30)

    # Partition a follower to trigger PreVote on reconnection.
    follower = cluster.get_followers()[0]
    print(f"\n>> Partitioning follower {follower}...")
    cluster.partition_node(follower)
    cluster.run_for(40)

    print(f">> Healing partition...")
    cluster.heal_all()
    cluster.run_for(40)

    # Print metrics.
    print(f"\n{collector.summary()}")

    # Export metrics.
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        collector.export_json(path, cluster=cluster)
        print(f"\nMetrics exported to {path}")
    finally:
        pass  # leave file for inspection

    print(f"\n{cluster.summary()}")


if __name__ == "__main__":
    main()