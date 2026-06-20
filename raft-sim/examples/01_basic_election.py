"""Example: basic leader election and command replication."""
from raft import Cluster, NetworkConfig


def main():
    cluster = Cluster(size=5, seed=42, network_config=NetworkConfig(seed=42))

    print("=== Basic Raft Simulation ===\n")
    print(f"Created cluster of {cluster.size} nodes")

    leader = cluster.run_until_leader(timeout=100)
    print(f"Leader elected: node {leader}")

    print("\nSubmitting commands...")
    cluster.submit("set", "name", "raft")
    cluster.submit("set", "version", 1)
    cluster.submit("set", "consensus", True)
    cluster.run_for(20)

    print(f"\nname = {cluster.all_agree('name')}")
    print(f"version = {cluster.all_agree('version')}")
    print(f"consensus = {cluster.all_agree('consensus')}")
    print(f"Log consistent: {cluster.log_consistent()}")

    print(f"\n{cluster.summary()}")


if __name__ == "__main__":
    main()