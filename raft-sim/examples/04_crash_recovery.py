"""Example: node crash and recovery simulation.

Demonstrates that the cluster maintains consistency even when nodes
crash and restart, with persistent state preservation.
"""
from raft import Cluster, NetworkConfig, check_all


def main():
    cluster = Cluster(
        size=5,
        seed=42,
        network_config=NetworkConfig(seed=42),
    )

    print("=== Crash & Recovery Simulation ===\n")

    leader = cluster.run_until_leader(timeout=100)
    print(f"Initial leader: node {leader}")

    # Submit initial commands.
    for i in range(5):
        cluster.submit("set", f"k{i}", i)
    cluster.run_for(20)
    print(f"Committed 5 commands. Consistent: {cluster.log_consistent()}")

    # Crash a follower.
    follower = cluster.get_followers()[0]
    print(f"\n>> Crashing follower {follower}...")
    cluster.crash_node(follower)
    cluster.run_for(15)
    print(f"  Crashed: {cluster.crashed_nodes()}")
    print(f"  Alive: {cluster.alive_nodes()}")

    # Submit more commands while follower is down.
    for i in range(5, 10):
        cluster.submit("set", f"k{i}", i)
    cluster.run_for(20)
    print(f"  Committed 5 more commands (follower down)")

    # Restart the follower.
    print(f"\n>> Restarting follower {follower}...")
    cluster.restart_node(follower)
    cluster.run_for(60)

    # Verify consistency.
    ok = True
    for i in range(10):
        val = cluster.all_agree(f"k{i}")
        if val != i:
            print(f"  ✗ k{i} = {val} (expected {i})")
            ok = False
    if ok:
        print(f"\nAll 10 values consistent after crash recovery! ✓")

    # Check invariants.
    report = check_all(cluster)
    print(f"\n{report.summary()}")

    print(f"\n{cluster.summary()}")


if __name__ == "__main__":
    main()