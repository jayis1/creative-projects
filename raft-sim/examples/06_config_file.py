"""Example: configuration file support.

Demonstrates loading a cluster configuration from a YAML file
and running a simulation with the specified parameters.
"""
from pathlib import Path

from raft import Cluster, load_config


def main():
    config_path = Path(__file__).parent.parent / "configs" / "default.yaml"
    print(f"=== Configuration File Example ===\n")
    print(f"Loading config from: {config_path}")

    cfg = load_config(config_path)
    print(f"Cluster size: {cfg.size}")
    print(f"Seed: {cfg.seed}")
    print(f"Election timeout: {cfg.election_timeout_range}")
    print(f"Heartbeat interval: {cfg.heartbeat_interval}")
    print(f"Snapshot threshold: {cfg.snapshot_threshold}")
    print(f"PreVote enabled: {cfg.prevote_enabled}")
    print(f"Network: latency={cfg.network.base_latency}, jitter={cfg.network.jitter}")

    # Build cluster from config.
    cluster = Cluster(
        size=cfg.size,
        network_config=cfg.network,
        seed=cfg.seed,
        election_timeout_range=cfg.election_timeout_range,
        heartbeat_interval=cfg.heartbeat_interval,
        snapshot_threshold=cfg.snapshot_threshold,
        prevote_enabled=cfg.prevote_enabled,
    )

    leader = cluster.run_until_leader(timeout=100)
    print(f"\nLeader elected: node {leader}")

    cluster.submit("set", "hello", "world")
    cluster.run_for(20)
    print(f"hello = {cluster.all_agree('hello')}")
    print(f"\n{cluster.summary()}")


if __name__ == "__main__":
    main()