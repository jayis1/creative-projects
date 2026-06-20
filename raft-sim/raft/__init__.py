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
from raft.node import RaftNode
from raft.network import Network, NetworkConfig
from raft.cluster import Cluster, ClusterEvent
from raft.snapshot import Snapshot

__version__ = "1.0.0"

__all__ = [
    "NodeRole",
    "NodeState",
    "LogEntry",
    "RequestVoteRequest",
    "RequestVoteResponse",
    "AppendEntriesRequest",
    "AppendEntriesResponse",
    "InstallSnapshotRequest",
    "InstallSnapshotResponse",
    "RaftNode",
    "Network",
    "NetworkConfig",
    "Cluster",
    "ClusterEvent",
    "Snapshot",
]