"""Basic tests for the Raft simulator."""
import pytest

from raft import Cluster, NetworkConfig
from raft.node import RaftNode, KVStateMachine
from raft.types import NodeRole, LogEntry
from raft.snapshot import SnapshotStore
from raft.network import Network


class TestNetwork:
    def test_basic_send_receive(self):
        net = Network()
        net.register(0)
        net.register(1)
        net.send(0, 1, "hello")
        net.drain()
        msgs = net.inbox(1)
        assert len(msgs) == 1
        assert msgs[0][0] == 0
        assert msgs[0][1] == "hello"

    def test_partition_blocks_messages(self):
        net = Network()
        net.register(0)
        net.register(1)
        net.partition(0, 1)
        net.send(0, 1, "hello")
        net.drain()
        assert len(net.inbox(1)) == 0
        assert net.dropped_count == 1

    def test_heal_partition(self):
        net = Network()
        net.register(0)
        net.register(1)
        net.partition(0, 1)
        net.heal_partition(0, 1)
        net.send(0, 1, "hello")
        net.drain()
        assert len(net.inbox(1)) == 1

    def test_drop_rate(self):
        net = Network(NetworkConfig(drop_rate=1.0, seed=42))
        net.register(0)
        net.register(1)
        net.send(0, 1, "hello")
        net.drain()
        assert len(net.inbox(1)) == 0

    def test_latency(self):
        net = Network(NetworkConfig(base_latency=5.0, jitter=0.0, seed=42))
        net.register(0)
        net.register(1)
        net.send(0, 1, "hello")
        # Message should be queued but not yet deliverable.
        assert net.pending_count() == 1
        # Drain auto-advances time to deliver — so after drain it's delivered.
        net.drain()
        msgs = net.inbox(1)
        assert len(msgs) == 1
        # Verify delivery time was >= 5.0.
        assert msgs[0][2] >= 5.0


class TestSnapshotStore:
    def test_append_and_get(self):
        store = SnapshotStore()
        store.append_entries([LogEntry(term=1, command="a")])
        assert store.last_log_index == 1
        assert store.get_entry(1).command == "a"

    def test_truncate(self):
        store = SnapshotStore()
        store.append_entries([LogEntry(term=1, command="a"), LogEntry(term=1, command="b")])
        removed = store.truncate_from(2)
        assert len(removed) == 1
        assert store.last_log_index == 1

    def test_snapshot_compaction(self):
        store = SnapshotStore()
        for i in range(10):
            store.append_entries([LogEntry(term=1, command=f"c{i}")])
        assert store.last_log_index == 10
        snap = store.take_snapshot(5, 1, "state", {0, 1, 2})
        assert snap.last_included_index == 5
        assert len(store.entries) == 5  # entries 6-10 remain
        assert store.last_log_index == 10

    def test_term_at_index_after_snapshot(self):
        store = SnapshotStore()
        store.append_entries([LogEntry(term=1, command="a"), LogEntry(term=2, command="b")])
        store.take_snapshot(1, 1, "state", {0})
        assert store.term_at_index(1) == 1  # snapshot boundary
        assert store.term_at_index(2) == 2  # retained entry


class TestLeaderElection:
    def test_elects_leader(self):
        cluster = Cluster(size=5, seed=42, network_config=NetworkConfig(seed=42))
        leader = cluster.run_until_leader(timeout=100)
        assert leader is not None
        assert cluster.nodes[leader].is_leader

    def test_single_leader(self):
        cluster = Cluster(size=5, seed=42, network_config=NetworkConfig(seed=42))
        cluster.run_until_leader(timeout=100)
        leaders = [n for n in cluster.nodes.values() if n.is_leader]
        assert len(leaders) == 1

    def test_leader_has_higher_term(self):
        cluster = Cluster(size=5, seed=42, network_config=NetworkConfig(seed=42))
        leader = cluster.run_until_leader(timeout=100)
        assert cluster.nodes[leader].state.current_term >= 1


class TestLogReplication:
    def test_command_replicated(self):
        cluster = Cluster(size=5, seed=42, network_config=NetworkConfig(seed=42))
        cluster.run_until_leader(timeout=100)
        cluster.submit("set", "x", 42)
        cluster.run_for(30)
        assert cluster.all_agree("x") == 42

    def test_multiple_commands(self):
        cluster = Cluster(size=5, seed=42, network_config=NetworkConfig(seed=42))
        cluster.run_until_leader(timeout=100)
        for i in range(10):
            cluster.submit("set", f"k{i}", i)
        cluster.run_for(40)
        for i in range(10):
            assert cluster.all_agree(f"k{i}") == i

    def test_log_consistency(self):
        cluster = Cluster(size=5, seed=42, network_config=NetworkConfig(seed=42))
        cluster.run_until_leader(timeout=100)
        for i in range(5):
            cluster.submit("set", f"k{i}", i)
        cluster.run_for(30)
        assert cluster.log_consistent()


class TestPartitionRecovery:
    def test_leader_partition_recovery(self):
        cluster = Cluster(
            size=5, seed=100,
            network_config=NetworkConfig(seed=100, base_latency=0.5, jitter=0.3),
        )
        leader = cluster.run_until_leader(timeout=100)
        assert leader is not None

        cluster.submit("set", "x", 1)
        cluster.run_for(20)

        cluster.partition_node(leader)
        cluster.run_for(40)
        new_leader = cluster.get_leader()
        assert new_leader is not None
        assert new_leader != leader

        cluster.heal_all()
        cluster.run_for(40)
        assert cluster.log_consistent()
        assert cluster.all_agree("x") == 1