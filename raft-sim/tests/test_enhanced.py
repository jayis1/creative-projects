"""Tests for Phase 2 enhancements: persistence, visualization, scenarios, invariants."""
import os
import tempfile

import pytest

from raft import (
    Cluster,
    NetworkConfig,
    save_cluster,
    load_cluster,
    render_cluster_ascii,
    render_partition_matrix,
    render_log_diff,
    render_timeline,
    leader_partition_scenario,
    split_brain_scenario,
    rolling_partition_scenario,
    flaky_network_scenario,
    run_scenario,
    check_all,
    check_election_safety,
    check_log_matching,
    check_state_machine_safety,
    check_commit_safety,
    serialize_node_state,
    deserialize_node_state,
)
from raft.network import Network


class TestPersistence:
    def test_serialize_node_state(self):
        cluster = Cluster(size=3, seed=42, network_config=NetworkConfig(seed=42))
        cluster.run_until_leader(timeout=100)
        cluster.submit("set", "x", 42)
        cluster.run_for(20)

        leader = cluster.get_leader()
        data = serialize_node_state(cluster.nodes[leader])
        assert data["node_id"] == leader
        assert data["role"] == "leader"
        assert len(data["log_entries"]) >= 1
        assert data["state_machine"]["x"] == 42

    def test_save_and_load_cluster(self):
        cluster = Cluster(size=3, seed=42, network_config=NetworkConfig(seed=42))
        cluster.run_until_leader(timeout=100)
        cluster.submit("set", "x", 42)
        cluster.run_for(20)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            save_cluster(cluster, path)
            assert os.path.getsize(path) > 0

            net = Network(NetworkConfig(seed=42))
            cluster2 = load_cluster(path, net)
            assert cluster2.size == 3
            assert cluster2.all_agree("x") == 42
        finally:
            os.unlink(path)

    def test_deserialize_preserves_term(self):
        cluster = Cluster(size=3, seed=42, network_config=NetworkConfig(seed=42))
        cluster.run_until_leader(timeout=100)
        leader = cluster.get_leader()
        original_term = cluster.nodes[leader].state.current_term

        data = serialize_node_state(cluster.nodes[leader])
        net = Network()
        net.register(leader)
        node = deserialize_node_state(data, net)
        assert node.state.current_term == original_term


class TestVisualization:
    def test_render_cluster_ascii(self):
        cluster = Cluster(size=3, seed=42, network_config=NetworkConfig(seed=42))
        cluster.run_until_leader(timeout=100)
        output = render_cluster_ascii(cluster)
        assert "Raft Cluster" in output
        assert "Node" in output

    def test_render_partition_matrix(self):
        cluster = Cluster(size=3, seed=42, network_config=NetworkConfig(seed=42))
        cluster.run_until_leader(timeout=100)
        output = render_partition_matrix(cluster)
        assert "Connectivity" in output

    def test_render_log_diff(self):
        cluster = Cluster(size=3, seed=42, network_config=NetworkConfig(seed=42))
        cluster.run_until_leader(timeout=100)
        cluster.submit("set", "x", 1)
        cluster.run_for(20)
        output = render_log_diff(cluster)
        assert "Log Comparison" in output or "empty" in output

    def test_render_timeline(self):
        cluster = Cluster(size=3, seed=42, network_config=NetworkConfig(seed=42))
        cluster.run_until_leader(timeout=100)
        output = render_timeline(cluster.event_log())
        assert "Timeline" in output


class TestScenarios:
    def test_leader_partition_scenario(self):
        cluster = Cluster(size=5, seed=100, network_config=NetworkConfig(seed=100))
        cluster.run_until_leader(timeout=100)
        cluster.submit("set", "x", 1)
        cluster.run_for(15)

        steps = leader_partition_scenario()
        results = run_scenario(cluster, steps, verbose=False)
        assert results["final_leader"] is not None
        assert results["log_consistent"]

    def test_flaky_network_scenario(self):
        cluster = Cluster(size=5, seed=200, network_config=NetworkConfig(seed=200))
        cluster.run_until_leader(timeout=100)
        steps = flaky_network_scenario(drop_rate=0.3)
        results = run_scenario(cluster, steps, verbose=False)
        # Should still have a leader after network stabilizes.
        assert results["final_leader"] is not None

    def test_rolling_partition_scenario(self):
        cluster = Cluster(size=3, seed=300, network_config=NetworkConfig(seed=300))
        cluster.run_until_leader(timeout=100)
        steps = rolling_partition_scenario()[:4]  # just first couple
        results = run_scenario(cluster, steps, verbose=False)
        # Should recover after healing.
        assert results["final_leader"] is not None


class TestInvariants:
    def test_all_pass_on_healthy_cluster(self):
        cluster = Cluster(size=5, seed=50, network_config=NetworkConfig(seed=50))
        cluster.run_until_leader(timeout=100)
        for i in range(5):
            cluster.submit("set", f"k{i}", i)
        cluster.run_for(30)
        report = check_all(cluster)
        assert report.passed, report.summary()

    def test_election_safety(self):
        cluster = Cluster(size=5, seed=42, network_config=NetworkConfig(seed=42))
        cluster.run_until_leader(timeout=100)
        report = check_election_safety(cluster)
        assert report.passed

    def test_commit_safety(self):
        cluster = Cluster(size=3, seed=42, network_config=NetworkConfig(seed=42))
        cluster.run_until_leader(timeout=100)
        report = check_commit_safety(cluster)
        assert report.passed

    def test_log_matching(self):
        cluster = Cluster(size=3, seed=42, network_config=NetworkConfig(seed=42))
        cluster.run_until_leader(timeout=100)
        cluster.submit("set", "x", 1)
        cluster.run_for(20)
        report = check_log_matching(cluster)
        assert report.passed

    def test_state_machine_safety(self):
        cluster = Cluster(size=3, seed=42, network_config=NetworkConfig(seed=42))
        cluster.run_until_leader(timeout=100)
        cluster.submit("set", "x", 1)
        cluster.run_for(20)
        report = check_state_machine_safety(cluster)
        assert report.passed


class TestBatchSubmission:
    def test_submit_batch(self):
        cluster = Cluster(size=3, seed=77, network_config=NetworkConfig(seed=77))
        cluster.run_until_leader(timeout=100)
        cmds = [["set", f"b{i}", i] for i in range(10)]
        count = cluster.submit_batch(cmds)
        assert count == 10
        cluster.run_for(30)
        for i in range(10):
            assert cluster.all_agree(f"b{i}") == i

    def test_submit_and_wait(self):
        cluster = Cluster(size=3, seed=88, network_config=NetworkConfig(seed=88))
        cluster.run_until_leader(timeout=100)
        ok = cluster.submit_and_wait("set", "waited", True, timeout=30)
        assert ok
        assert cluster.all_agree("waited") == True