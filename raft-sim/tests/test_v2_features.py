"""Tests for v2.0 enhancements: PreVote, crash recovery, config, metrics, observers."""

import json
import os
import tempfile
from pathlib import Path

import pytest
import yaml

from raft import (
    Cluster,
    NetworkConfig,
    ClusterEvent,
    ClusterConfig,
    load_config,
    save_config,
    MetricsCollector,
    configure_logging,
    PreVoteRequest,
    PreVoteResponse,
)
from raft.node import RaftNode, KVStateMachine
from raft.network import Network
from raft.prevote import PreVoteRequest as PVReq, PreVoteResponse as PVResp


# ---------------------------------------------------------------------------
# PreVote tests
# ---------------------------------------------------------------------------


class TestPreVote:
    """Tests for the PreVote optimization."""

    def test_prevote_disabled_by_default(self):
        """PreVote should be disabled by default for backward compatibility."""
        cluster = Cluster(size=3, seed=42, network_config=NetworkConfig(seed=42))
        for node in cluster.nodes.values():
            assert not node.prevote_enabled, "PreVote should be disabled by default"

    def test_prevote_enabled_when_requested(self):
        cluster = Cluster(
            size=3, seed=42,
            network_config=NetworkConfig(seed=42),
            prevote_enabled=True,
        )
        for node in cluster.nodes.values():
            assert node.prevote_enabled

    def test_prevote_election_succeeds(self):
        """A cluster with PreVote enabled should still elect a leader."""
        cluster = Cluster(
            size=5, seed=42,
            network_config=NetworkConfig(seed=42),
            prevote_enabled=True,
        )
        leader = cluster.run_until_leader(timeout=200)
        assert leader is not None, "PreVote cluster should elect a leader"

    def test_prevote_message_types(self):
        """PreVoteRequest and PreVoteResponse should be properly typed."""
        req = PreVoteRequest(
            term=1, candidate_id=0, last_log_index=5, last_log_term=2
        )
        resp = PreVoteResponse(term=1, vote_granted=True, voter_id=1)
        assert req.term == 1
        assert resp.vote_granted is True

    def test_prevote_stale_term_rejected(self):
        """A node should not grant a pre-vote for a term ≤ its current term."""
        net = Network()
        net.register(0)
        net.register(1)
        node = RaftNode(0, [1], net, KVStateMachine(), prevote_enabled=True)
        node.state.current_term = 5

        # PreVote for term 5 (not > current) should be rejected.
        req = PVReq(term=5, candidate_id=1, last_log_index=0, last_log_term=0)
        node._handle_prevote_request(1, req)
        # Drain to deliver the message.
        net.drain()
        # Response goes to node 1's inbox.
        msgs = net.inbox(1)
        assert len(msgs) == 1
        resp = msgs[0][1]
        assert isinstance(resp, PVResp)
        assert resp.vote_granted is False

    def test_prevote_higher_term_granted(self):
        """A node should grant a pre-vote for a higher term if log is up-to-date."""
        net = Network()
        net.register(0)
        net.register(1)
        node = RaftNode(0, [1], net, KVStateMachine(), prevote_enabled=True)
        node.state.current_term = 3

        req = PVReq(term=4, candidate_id=1, last_log_index=0, last_log_term=0)
        node._handle_prevote_request(1, req)
        net.drain()
        msgs = net.inbox(1)
        assert len(msgs) == 1
        resp = msgs[0][1]
        assert resp.vote_granted is True

    def test_prevote_leader_rejects(self):
        """A leader should not grant pre-votes."""
        net = Network()
        net.register(0)
        net.register(1)
        node = RaftNode(0, [1], net, KVStateMachine(), prevote_enabled=True)
        # Make node a leader.
        from raft.types import NodeRole
        node.role = NodeRole.LEADER
        node.state.current_term = 5

        req = PVReq(term=6, candidate_id=1, last_log_index=0, last_log_term=0)
        node._handle_prevote_request(1, req)
        net.drain()
        msgs = net.inbox(1)
        resp = msgs[0][1]
        assert resp.vote_granted is False


# ---------------------------------------------------------------------------
# Crash / recovery tests
# ---------------------------------------------------------------------------


class TestCrashRecovery:
    """Tests for node crash and recovery simulation."""

    def test_crash_stops_processing(self):
        """A crashed node should not process messages or tick."""
        cluster = Cluster(size=3, seed=42, network_config=NetworkConfig(seed=42))
        cluster.run_until_leader(timeout=100)

        follower = cluster.get_followers()[0]
        cluster.crash_node(follower)

        assert cluster.nodes[follower].is_crashed
        assert follower in cluster.crashed_nodes()
        assert follower not in cluster.alive_nodes()

        # Run for a while — crashed node shouldn't change state.
        old_term = cluster.nodes[follower].state.current_term
        cluster.run_for(20)
        assert cluster.nodes[follower].state.current_term == old_term

    def test_restart_restores_node(self):
        """A restarted node should resume processing."""
        cluster = Cluster(size=3, seed=42, network_config=NetworkConfig(seed=42))
        cluster.run_until_leader(timeout=100)

        follower = cluster.get_followers()[0]
        cluster.crash_node(follower)
        assert cluster.nodes[follower].is_crashed

        cluster.restart_node(follower)
        assert not cluster.nodes[follower].is_crashed
        assert follower in cluster.alive_nodes()

    def test_crash_recovery_catches_up(self):
        """A crashed follower should catch up after restart."""
        cluster = Cluster(size=5, seed=42, network_config=NetworkConfig(seed=42))
        leader = cluster.run_until_leader(timeout=100)
        assert leader is not None

        # Submit initial commands.
        for i in range(5):
            cluster.submit("set", f"k{i}", i)
        cluster.run_for(20)

        # Crash a follower.
        follower = cluster.get_followers()[0]
        cluster.crash_node(follower)

        # Submit more commands while follower is down.
        for i in range(5, 10):
            cluster.submit("set", f"k{i}", i)
        cluster.run_for(20)

        # Restart and let it catch up.
        cluster.restart_node(follower)
        cluster.run_for(60)

        # The restarted follower should have caught up.
        assert cluster.nodes[follower].state.commit_index >= 5, (
            f"Restarted follower should have caught up, "
            f"commit_index={cluster.nodes[follower].state.commit_index}"
        )

    def test_crash_events_logged(self):
        """Crash and restart events should be logged."""
        cluster = Cluster(size=3, seed=42, network_config=NetworkConfig(seed=42))
        cluster.run_until_leader(timeout=100)

        follower = cluster.get_followers()[0]
        cluster.crash_node(follower)
        cluster.restart_node(follower)

        events = cluster.event_log()
        event_types = [e[1] for e in events]
        assert ClusterEvent.NODE_CRASHED in event_types
        assert ClusterEvent.NODE_RESTARTED in event_types

    def test_crashed_leader_not_returned(self):
        """get_leader should not return a crashed node."""
        cluster = Cluster(size=3, seed=42, network_config=NetworkConfig(seed=42))
        leader = cluster.run_until_leader(timeout=100)
        assert leader is not None

        cluster.crash_node(leader)
        # Run to elect a new leader.
        cluster.run_for(50)
        new_leader = cluster.get_leader()
        assert new_leader != leader
        assert new_leader is not None

    def test_persistent_state_survives_crash(self):
        """Persistent state (term, log) should survive crash+restart."""
        cluster = Cluster(size=3, seed=42, network_config=NetworkConfig(seed=42))
        leader = cluster.run_until_leader(timeout=100)
        cluster.submit("set", "x", 42)
        cluster.run_for(20)

        follower = cluster.get_followers()[0]
        old_term = cluster.nodes[follower].state.current_term
        old_log_len = cluster.nodes[follower].last_log_index

        cluster.crash_node(follower)
        cluster.restart_node(follower)

        # Persistent state preserved.
        assert cluster.nodes[follower].state.current_term == old_term
        assert cluster.nodes[follower].last_log_index == old_log_len


# ---------------------------------------------------------------------------
# Config tests
# ---------------------------------------------------------------------------


class TestConfig:
    """Tests for YAML/JSON configuration support."""

    def test_default_config(self):
        cfg = ClusterConfig()
        assert cfg.size == 5
        assert cfg.prevote_enabled is False

    def test_invalid_size(self):
        with pytest.raises(ValueError, match="size must be"):
            ClusterConfig(size=0)

    def test_invalid_election_range(self):
        with pytest.raises(ValueError, match="lower bound"):
            ClusterConfig(election_timeout_range=(10.0, 5.0))

    def test_load_yaml_config(self):
        yaml_content = """
cluster:
  size: 7
  seed: 100
  election_timeout_range: [4.0, 8.0]
  heartbeat_interval: 0.5
  snapshot_threshold: 30
  prevote_enabled: true
network:
  base_latency: 0.5
  jitter: 0.2
  drop_rate: 0.1
  seed: 100
"""
        with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
            f.write(yaml_content)
            path = f.name
        try:
            cfg = load_config(path)
            assert cfg.size == 7
            assert cfg.seed == 100
            assert cfg.election_timeout_range == (4.0, 8.0)
            assert cfg.heartbeat_interval == 0.5
            assert cfg.snapshot_threshold == 30
            assert cfg.prevote_enabled is True
            assert cfg.network.base_latency == 0.5
            assert cfg.network.drop_rate == 0.1
        finally:
            os.unlink(path)

    def test_load_json_config(self):
        json_content = json.dumps({
            "cluster": {"size": 3, "seed": 50},
            "network": {"base_latency": 2.0, "jitter": 1.0},
        })
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            f.write(json_content)
            path = f.name
        try:
            cfg = load_config(path)
            assert cfg.size == 3
            assert cfg.seed == 50
            assert cfg.network.base_latency == 2.0
        finally:
            os.unlink(path)

    def test_save_and_load_roundtrip(self):
        cfg = ClusterConfig(size=7, seed=99, snapshot_threshold=25)
        with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
            path = f.name
        try:
            save_config(cfg, path)
            cfg2 = load_config(path)
            assert cfg2.size == 7
            assert cfg2.seed == 99
            assert cfg2.snapshot_threshold == 25
        finally:
            os.unlink(path)

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            load_config("/nonexistent/path.yaml")


# ---------------------------------------------------------------------------
# Metrics tests
# ---------------------------------------------------------------------------


class TestMetrics:
    """Tests for the metrics collector."""

    def test_metrics_collector_records_events(self):
        collector = MetricsCollector()
        cluster = Cluster(size=3, seed=42, network_config=NetworkConfig(seed=42))
        cluster.add_observer(collector)
        cluster.run_until_leader(timeout=100)
        cluster.submit("set", "x", 1)
        cluster.run_for(20)

        # Should have collected events.
        assert len(collector.snapshots) > 0
        assert collector._elections > 0 or collector._leader_changes > 0

    def test_metrics_export_json(self):
        collector = MetricsCollector()
        cluster = Cluster(size=3, seed=42, network_config=NetworkConfig(seed=42))
        cluster.add_observer(collector)
        cluster.run_until_leader(timeout=100)
        cluster.submit("set", "x", 1)
        cluster.run_for(20)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            collector.export_json(path, cluster=cluster)
            data = json.loads(Path(path).read_text())
            assert "events" in data
            assert "summary" in data
            assert "cluster" in data
            assert len(data["events"]) > 0
        finally:
            os.unlink(path)

    def test_metrics_export_csv(self):
        collector = MetricsCollector()
        cluster = Cluster(size=3, seed=42, network_config=NetworkConfig(seed=42))
        cluster.add_observer(collector)
        cluster.run_until_leader(timeout=100)

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            path = f.name
        try:
            collector.export_csv(path)
            content = Path(path).read_text()
            assert "sim_time" in content  # header
            assert "event_type" in content
        finally:
            os.unlink(path)

    def test_metrics_summary(self):
        collector = MetricsCollector()
        cluster = Cluster(size=3, seed=42, network_config=NetworkConfig(seed=42))
        cluster.add_observer(collector)
        cluster.run_until_leader(timeout=100)

        summary = collector.summary()
        assert "Metrics Summary" in summary

    def test_metrics_crash_events(self):
        collector = MetricsCollector()
        cluster = Cluster(size=3, seed=42, network_config=NetworkConfig(seed=42))
        cluster.add_observer(collector)
        cluster.run_until_leader(timeout=100)

        follower = cluster.get_followers()[0]
        cluster.crash_node(follower)
        cluster.restart_node(follower)

        assert collector._crashes == 1
        assert collector._restarts == 1


# ---------------------------------------------------------------------------
# Observer tests
# ---------------------------------------------------------------------------


class TestObservers:
    """Tests for the observer/callback system."""

    def test_observer_called_on_event(self):
        events_received = []

        def observer(event, data):
            events_received.append((event, data))

        cluster = Cluster(size=3, seed=42, network_config=NetworkConfig(seed=42))
        cluster.add_observer(observer)
        cluster.run_until_leader(timeout=100)

        # Should have received at least one LEADER_ELECTED event.
        event_types = [e[0] for e in events_received]
        assert ClusterEvent.LEADER_ELECTED in event_types

    def test_observer_removed(self):
        events_received = []

        def observer(event, data):
            events_received.append(event)

        cluster = Cluster(size=3, seed=42, network_config=NetworkConfig(seed=42))
        cluster.add_observer(observer)
        cluster.run_until_leader(timeout=100)
        count_before = len(events_received)

        cluster.remove_observer(observer)
        cluster.submit("set", "x", 1)
        cluster.run_for(20)

        assert len(events_received) == count_before

    def test_observer_exception_doesnt_crash(self):
        def bad_observer(event, data):
            raise RuntimeError("Observer error")

        cluster = Cluster(size=3, seed=42, network_config=NetworkConfig(seed=42))
        cluster.add_observer(bad_observer)
        # Should not raise.
        cluster.run_until_leader(timeout=100)


# ---------------------------------------------------------------------------
# Logging tests
# ---------------------------------------------------------------------------


class TestLogging:
    """Tests for logging utilities."""

    def test_configure_logging(self):
        configure_logging(level="DEBUG")
        import logging
        logger = logging.getLogger("raft")
        assert logger.level == logging.DEBUG

    def test_get_logger(self):
        from raft.logging_utils import get_logger
        log = get_logger("raft.test")
        assert log.name == "raft.test"

    def test_structured_event_logger(self):
        from raft.logging_utils import StructuredEventLogger
        slog = StructuredEventLogger("raft.test.structured")
        # Should not raise.
        slog.event("TestEvent", node=0, term=1)