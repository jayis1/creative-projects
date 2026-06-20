"""Bug hunt tests — verify bugs before fixing them.

Each test demonstrates a specific bug found during the Phase 3 bug hunt.
The test is written to FAIL before the fix and PASS after.
"""
import pytest

from raft import (
    Cluster,
    NetworkConfig,
    ClusterEvent,
    check_all,
)
from raft.node import KVStateMachine, RaftNode
from raft.snapshot import SnapshotStore
from raft.types import LogEntry, NodeRole
from raft.network import Network
from raft.persistence import save_cluster, load_cluster


class TestMaybeSendSnapshotNeverCalled:
    """BUG: _maybe_send_snapshot is defined but never called.

    When a follower is far behind and the leader has snapshotted,
    the leader should send an InstallSnapshot RPC. But the method
    that does this is never invoked from _send_append_entries.
    """

    def test_snapshot_sent_to_lagging_follower(self):
        """A partitioned follower that misses entries beyond the
        snapshot boundary should receive InstallSnapshot after healing."""
        cluster = Cluster(
            size=3, seed=42,
            network_config=NetworkConfig(seed=42),
            snapshot_threshold=5,
            # Use long election timeout so the partitioned follower
            # doesn't start elections and inflate its term.
            election_timeout_range=(100.0, 200.0),
            heartbeat_interval=1.0,
        )
        leader = cluster.run_until_leader(timeout=500)
        assert leader is not None

        # Partition a follower so it falls behind.
        follower = [n for n in cluster.nodes if n != leader][0]
        cluster.partition_node(follower)

        # Submit enough commands to trigger snapshotting on leader.
        for i in range(15):
            cluster.submit("set", f"k{i}", i)
            cluster.run_for(2)

        # Leader should have a snapshot now.
        leader_node = cluster.nodes[leader]
        assert leader_node.log_store.has_snapshot, "Leader should have snapshotted"

        # Heal the partition.
        cluster.heal_all()
        cluster.run_for(40)

        # The lagging follower should have caught up via InstallSnapshot.
        follower_node = cluster.nodes[follower]
        assert follower_node.state.commit_index >= 10, (
            f"Follower {follower} should have caught up via snapshot, "
            f"but commit_index={follower_node.state.commit_index}"
        )
        # Check the follower received the snapshot.
        assert follower_node.stats.snapshots_installed > 0, (
            "Follower should have received InstallSnapshot RPC"
        )


class TestStatsNeverUpdated:
    """BUG: entries_committed, total_elections, commands_committed
    are defined but never incremented."""

    def test_entries_committed_updated(self):
        cluster = Cluster(size=3, seed=42, network_config=NetworkConfig(seed=42))
        cluster.run_until_leader(timeout=100)
        cluster.submit("set", "x", 42)
        cluster.run_for(20)

        leader = cluster.get_leader()
        node = cluster.nodes[leader]
        # entries_committed should be > 0 after committing an entry.
        assert node.stats.entries_committed > 0, (
            "entries_committed stat should be incremented when commit_index advances"
        )

    def test_total_elections_updated(self):
        cluster = Cluster(size=5, seed=42, network_config=NetworkConfig(seed=42))
        cluster.run_until_leader(timeout=100)
        # total_elections should be > 0 after an election.
        assert cluster.stats.total_elections > 0, (
            "total_elections stat should be incremented when elections start"
        )

    def test_commands_committed_updated(self):
        cluster = Cluster(size=3, seed=42, network_config=NetworkConfig(seed=42))
        cluster.run_until_leader(timeout=100)
        cluster.submit("set", "x", 42)
        cluster.run_for(20)
        assert cluster.stats.commands_committed > 0, (
            "commands_committed stat should be incremented when commands are committed"
        )


class TestVersionMismatch:
    """BUG: pyproject.toml has version 1.0.0 but __init__.py has 1.1.0."""

    def test_versions_match(self):
        from raft import __version__
        # Read pyproject.toml version
        import pathlib
        pp = pathlib.Path(__file__).parent.parent / "pyproject.toml"
        content = pp.read_text()
        # Extract version line
        for line in content.splitlines():
            if line.strip().startswith("version"):
                pyproject_version = line.split("=")[1].strip().strip('"')
                break
        else:
            pytest.fail("Could not find version in pyproject.toml")
        assert __version__ == pyproject_version, (
            f"Version mismatch: __init__.py={__version__}, pyproject.toml={pyproject_version}"
        )


class TestLogBarCommittedDisplay:
    """BUG: _render_log_bar uses .lower() on digit strings which has no effect.
    Committed vs uncommitted entries are indistinguishable in the visualization."""

    def test_committed_vs_uncommitted_distinct(self):
        from raft.visualizer import _render_log_bar
        from raft.node import RaftNode, KVStateMachine
        from raft.network import Network
        from raft.types import LogEntry

        net = Network()
        node = RaftNode(0, [1], net, KVStateMachine())
        # Append two entries: first committed, second not.
        node.log_store.append_entries([LogEntry(term=1, command="a", index=1)])
        node.log_store.append_entries([LogEntry(term=1, command="b", index=2)])
        node.state.commit_index = 1  # only first entry committed

        bar = _render_log_bar(node, max_entries=2)
        # The first and second characters should be visually distinct
        # (committed vs uncommitted).
        chars = bar.strip("[]")
        assert chars[0] != chars[1], (
            f"Committed entry ({chars[0]}) should look different from "
            f"uncommitted entry ({chars[1]}) in the log bar"
        )


class TestClusterEventsNotLogged:
    """BUG: ClusterEvent defines ELECTION_STARTED, LOG_COMMITTED,
    SNAPSHOT_TAKEN, MEMBERSHIP_CHANGE but these are never logged."""

    def test_election_started_logged(self):
        cluster = Cluster(size=5, seed=42, network_config=NetworkConfig(seed=42))
        cluster.run_until_leader(timeout=100)
        events = cluster.event_log()
        event_types = [e[1] for e in events]
        assert ClusterEvent.ELECTION_STARTED in event_types, (
            "ELECTION_STARTED events should be logged"
        )

    def test_log_committed_logged(self):
        cluster = Cluster(size=3, seed=42, network_config=NetworkConfig(seed=42))
        cluster.run_until_leader(timeout=100)
        cluster.submit("set", "x", 42)
        cluster.run_for(20)
        events = cluster.event_log()
        event_types = [e[1] for e in events]
        assert ClusterEvent.LOG_COMMITTED in event_types, (
            "LOG_COMMITTED events should be logged when entries are committed"
        )


class TestLoadClusterIgnoresPassedNetwork:
    """BUG: load_cluster creates its own network instead of using the
    passed one, making the network parameter misleading."""

    def test_passed_network_is_used(self):
        import tempfile, os
        cluster = Cluster(size=3, seed=42, network_config=NetworkConfig(seed=42))
        cluster.run_until_leader(timeout=100)
        cluster.submit("set", "x", 42)
        cluster.run_for(20)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            save_cluster(cluster, path)
            # Create a network with a specific time.
            net = Network(NetworkConfig(seed=99))
            net.set_time(123.0)
            cluster2 = load_cluster(path, net)
            # The loaded cluster should use the passed network's time.
            assert cluster2.network.time == 123.0, (
                f"load_cluster should use the passed network (time=123.0), "
                f"but got time={cluster2.network.time}"
            )
        finally:
            os.unlink(path)


class TestAllAgreeWithNoneValue:
    """BUG: all_agree returns None when all nodes agree the value is None,
    making it indistinguishable from disagreement."""

    def test_all_agree_none_is_not_confused_with_disagreement(self):
        cluster = Cluster(size=3, seed=42, network_config=NetworkConfig(seed=42))
        cluster.run_until_leader(timeout=100)
        cluster.run_for(10)
        # No node has key "nonexistent" — they all agree it's absent.
        # all_agree should indicate agreement, not return None (which
        # also means "disagreement").
        result = cluster.all_agree("nonexistent")
        # We can't distinguish None-agreement from disagreement, which is the bug.
        # After the fix, all_agree should return a sentinel or use a different API.
        # For now, let's test a new method that distinguishes.
        agreed, value = cluster.all_agree_detailed("nonexistent")
        assert agreed is True, "All nodes agree the key is absent (None)"
        assert value is None


class TestTruncateIntoSnapshot:
    """BUG: truncate_from into the snapshot region incorrectly removes
    the snapshot entirely rather than keeping it up to the truncation point."""

    def test_truncate_into_snapshot_preserves_partial(self):
        store = SnapshotStore()
        # Create 10 entries, snapshot up to 5.
        for i in range(10):
            store.append_entries([LogEntry(term=1, command=f"c{i}", index=i+1)])
        store.take_snapshot(5, 1, "state", {0, 1})

        # Now truncate from index 3 (within snapshot region).
        # This should NOT destroy the entire snapshot — it's an invalid
        # operation in Raft (you can't un-commit entries), but the
        # behavior should at least not corrupt the store.
        # After the fix, truncating into the snapshot should be a no-op
        # or raise an error, not silently discard the snapshot.
        with pytest.raises((ValueError, RuntimeError)):
            store.truncate_from(3)