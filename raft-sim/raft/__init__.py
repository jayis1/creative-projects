"""Raft consensus algorithm simulator.

A from-scratch discrete-event simulation of the Raft consensus algorithm,
including leader election, log replication, snapshotting, and membership
changes, with a pluggable network model for partition/delay/reordering
experiments.

See: Ongaro, D., & Ousterhout, J. (2014). "In Search of an Understandable
Consensus Algorithm (Extended Version)". USENIX ATC.
"""

from raft.types import (
    NodeRole,
    NodeState,
    LogEntry,
    RequestVoteRequest,
    RequestVoteResponse,
    AppendEntriesRequest,
    AppendEntriesResponse,
    InstallSnapshotRequest,
    InstallSnapshotResponse,
)
from raft.node import RaftNode, StateMachine, KVStateMachine
from raft.network import Network, NetworkConfig
from raft.cluster import Cluster, ClusterEvent
from raft.snapshot import Snapshot, SnapshotStore
from raft.persistence import (
    serialize_node_state,
    deserialize_node_state,
    serialize_cluster,
    save_cluster,
    load_cluster,
)
from raft.visualizer import (
    render_cluster_ascii,
    render_timeline,
    render_partition_matrix,
    render_log_diff,
)
from raft.scenarios import (
    ScenarioStep,
    leader_partition_scenario,
    split_brain_scenario,
    rolling_partition_scenario,
    flaky_network_scenario,
    cascading_failure_scenario,
    run_scenario,
)
from raft.invariants import (
    InvariantViolation,
    InvariantReport,
    check_election_safety,
    check_log_matching,
    check_state_machine_safety,
    check_leader_completeness,
    check_commit_safety,
    check_all,
)

__version__ = "1.1.0"

__all__ = [
    # Core types
    "NodeRole",
    "NodeState",
    "LogEntry",
    "RequestVoteRequest",
    "RequestVoteResponse",
    "AppendEntriesRequest",
    "AppendEntriesResponse",
    "InstallSnapshotRequest",
    "InstallSnapshotResponse",
    # Core classes
    "RaftNode",
    "StateMachine",
    "KVStateMachine",
    "Network",
    "NetworkConfig",
    "Cluster",
    "ClusterEvent",
    "Snapshot",
    "SnapshotStore",
    # Persistence
    "serialize_node_state",
    "deserialize_node_state",
    "serialize_cluster",
    "save_cluster",
    "load_cluster",
    # Visualization
    "render_cluster_ascii",
    "render_timeline",
    "render_partition_matrix",
    "render_log_diff",
    # Scenarios
    "ScenarioStep",
    "leader_partition_scenario",
    "split_brain_scenario",
    "rolling_partition_scenario",
    "flaky_network_scenario",
    "cascading_failure_scenario",
    "run_scenario",
    # Invariants
    "InvariantViolation",
    "InvariantReport",
    "check_election_safety",
    "check_log_matching",
    "check_state_machine_safety",
    "check_leader_completeness",
    "check_commit_safety",
    "check_all",
]