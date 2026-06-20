"""Example: snapshotting and log compaction."""
from raft import Cluster, NetworkConfig


def main():
    cluster = Cluster(
        size=3,
        seed=7,
        network_config=NetworkConfig(seed=7),
        snapshot_threshold=10,
    )

    print("=== Snapshotting & Log Compaction ===\n")

    leader = cluster.run_until_leader(timeout=100)
    print(f"Leader: node {leader}")
    print(f"Snapshot threshold: {cluster.nodes[leader].snapshot_threshold} entries")

    # Submit enough commands to trigger snapshotting.
    print("\nSubmitting 25 commands...")
    for i in range(25):
        cluster.submit("set", f"k{i}", i)
        cluster.run_for(3)

    print("\nNode states after 25 commands:")
    for nid in sorted(cluster.nodes):
        n = cluster.nodes[nid]
        print(
            f"  Node {nid}: commit={n.state.commit_index:2d} "
            f"applied={n.state.last_applied:2d} "
            f"snapshot={'yes' if n.log_store.has_snapshot else 'no ':3s} "
            f"snap_idx={n.log_store.last_included_index:2d} "
            f"retained_entries={len(n.log_store.entries)}"
        )

    print(f"\nAll agree k24: {cluster.all_agree('k24')}")
    print(f"Log consistent: {cluster.log_consistent()}")


if __name__ == "__main__":
    main()