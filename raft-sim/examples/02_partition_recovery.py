"""Example: network partition and recovery."""
from raft import Cluster, NetworkConfig


def main():
    cluster = Cluster(
        size=5,
        seed=100,
        network_config=NetworkConfig(seed=100, base_latency=0.5, jitter=0.3),
    )

    print("=== Partition Recovery ===\n")

    leader = cluster.run_until_leader(timeout=100)
    print(f"Initial leader: node {leader}")

    # Submit commands.
    for i in range(10):
        cluster.submit("set", f"k{i}", i)
    cluster.run_for(20)
    print(f"Committed 10 commands. Consistent: {cluster.log_consistent()}")

    # Partition the leader.
    print(f"\n>> Isolating leader {leader}...")
    cluster.partition_node(leader)
    cluster.run_for(30)

    new_leader = cluster.get_leader()
    print(f"New leader: {new_leader} (old leader {leader} is {cluster.nodes[leader].role.value})")

    # Submit more commands to the new leader.
    for i in range(10, 15):
        cluster.submit("set", f"k{i}", i)
    cluster.run_for(20)
    print(f"Submitted 5 more commands to new leader")

    # Heal.
    print("\n>> Healing partition...")
    cluster.heal_all()
    cluster.run_for(30)

    final_leader = cluster.get_leader()
    print(f"Final leader: {final_leader}")
    print(f"Log consistent: {cluster.log_consistent()}")

    # Verify all values.
    ok = True
    for i in range(15):
        val = cluster.all_agree(f"k{i}")
        status = "✓" if val == i else "✗"
        if val != i:
            ok = False
            print(f"  {status} k{i} = {val} (expected {i})")
    if ok:
        print(f"\nAll 15 values consistent after recovery! ✓")

    print(f"\n{cluster.summary()}")


if __name__ == "__main__":
    main()