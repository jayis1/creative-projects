# Raft Consensus Algorithm Simulator

<div align="center">

**A from-scratch, discrete-event simulation of the [Raft consensus algorithm](https://raft.github.io/) — the algorithm that powers etcd, Consul, and countless distributed systems.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests: 75](https://img.shields.io/badge/tests-75%20passing-brightgreen.svg)](#testing)
[![Version: 2.0.0](https://img.shields.io/badge/version-2.0.0-blue.svg)](#changelog)

</div>

---

## Table of Contents

- [What is Raft?](#what-is-raft)
- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [How It Works](#how-it-works)
- [Usage](#usage)
  - [As a Library](#as-a-library)
  - [CLI Interface](#cli-interface)
  - [Configuration Files](#configuration-files)
  - [Crash Recovery Simulation](#crash-recovery-simulation)
  - [PreVote Optimization](#prevote-optimization)
  - [Metrics Collection](#metrics-collection)
  - [Persistence](#persistence)
  - [Failure Scenarios](#failure-scenarios)
  - [Custom State Machine](#custom-state-machine)
- [Safety Invariants](#safety-invariants)
- [Visualization](#visualization)
- [Examples](#examples)
- [Testing](#testing)
- [Known Issues (Resolved)](#known-issues-resolved)
- [Changelog](#changelog)
- [Contributing](#contributing)
- [Roadmap](#roadmap)
- [References](#references)
- [License](#license)

## What is Raft?

Raft is a consensus algorithm designed for understandability. It solves the problem of getting multiple servers to agree on a single sequence of values (a replicated log) despite node failures, network partitions, and message loss. It decomposes consensus into three subproblems:

1. **Leader Election** — Exactly one leader is elected per term. If the leader fails, followers detect the timeout and a new election begins.
2. **Log Replication** — The leader accepts client commands, appends them to its log, and replicates them to followers. Once a majority acknowledges, the entry is *committed*.
3. **Safety** — Raft guarantees that committed entries are identical across all nodes and never overwritten.

## Features

### Core (v1.0)
- **Leader Election** with randomized election timeouts, RequestVote RPCs, and term-based voting
- **Log Replication** via AppendEntries RPCs with the conflict-optimization (fast log backtracking via `conflict_index`/`conflict_term`)
- **Snapshotting** — Log compaction via `InstallSnapshot` RPC when the log exceeds a configurable threshold
- **Membership Changes** — Add/remove nodes at runtime (simplified joint consensus)
- **Network Failure Model** — Configurable latency, jitter, packet loss, reordering, and arbitrary partitions between any set of nodes
- **Partition Recovery** — Automatically re-elects a leader when the old leader is isolated, and catches up the old leader after healing
- **State Machine** — Pluggable state machine interface with a built-in key-value store
- **CLI** — Three subcommands (`run`, `partition`, `election`) for running simulations from the command line
- **Statistics** — Per-node and cluster-wide stats: elections, votes, messages, leader changes, snapshots

### Enhancements (v1.1)
- **Persistence & Serialization** — Save/restore entire cluster state to JSON, including log entries, snapshots, state machine, and node roles
- **ASCII Visualization** — Cluster state diagrams, connectivity/partition matrices, side-by-side log comparison, and event timelines
- **Failure Scenarios** — 5 pre-defined scenarios: leader partition, split-brain, rolling failures, flaky network, and cascading failure
- **Safety Invariant Checker** — Verifies 5 Raft safety properties: Election Safety, Log Matching, Leader Completeness, State Machine Safety, Commit Safety
- **Batch Submission** — `submit_batch()` for multiple commands and `submit_and_wait()` for synchronous commit confirmation
- **Extended CLI** — 3 new subcommands (`scenario`, `visualize`, `invariants`) for a total of 6

### Major Improvements (v2.0)
- **PreVote Optimization** (Raft §6) — Prevents disruptive elections when a partitioned node reconnects, with `PreVoteRequest`/`PreVoteResponse` RPCs
- **Crash/Recovery Simulation** — `crash_node()` / `restart_node()` with persistent state preservation (term, log, snapshot survive restart)
- **Configuration File Support** — Load/save cluster configs from YAML or JSON files with `ClusterConfig`, `load_config()`, `save_config()`
- **Metrics Collection & Export** — `MetricsCollector` observer that records all cluster events and exports to JSON or CSV
- **Observer/Callback System** — `Cluster.add_observer()` for event-driven monitoring
- **Logging Integration** — Python `logging` module support with structured event logging
- **Linearizable Reads** — ReadIndex technique for strongly consistent reads from the leader
- **Benchmark CLI** — Throughput testing under various network conditions
- **Crash Recovery CLI** — Interactive crash/recovery demonstration
- **Config CLI** — Generate and display configuration files
- **9 CLI Subcommands** total (was 6)
- **GitHub Actions CI** — Automated testing on Python 3.10, 3.11, 3.12
- **75 tests** (was 44)

## Installation

### From Source

```bash
git clone https://github.com/jayis1/creative-projects.git
cd creative-projects/raft-sim
pip install -e ".[dev]"
```

### Requirements

- Python 3.10+
- PyYAML (for configuration file support)

### Verify Installation

```bash
# Run the test suite
pytest tests/ -v

# Try the CLI
python3 -m raft.cli run --size 5 --duration 20 --seed 42
```

## Quick Start

```python
from raft import Cluster, NetworkConfig, check_all

# Create a 5-node cluster with deterministic seed
cluster = Cluster(size=5, seed=42, network_config=NetworkConfig(seed=42))

# Run until a leader is elected
leader = cluster.run_until_leader(timeout=100)
print(f"Leader: node {leader}")

# Submit commands
cluster.submit("set", "x", 42)
cluster.run_for(20)
assert cluster.all_agree("x") == 42

# Check safety invariants
report = check_all(cluster)
assert report.passed
print("All safety invariants satisfied ✓")
```

## Architecture

```
raft-sim/
├── raft/
│   ├── __init__.py      # Package exports (v2.0.0)
│   ├── types.py         # Data types: NodeRole, LogEntry, RPC messages, NodeState
│   ├── snapshot.py      # Snapshot + SnapshotStore (log compaction)
│   ├── network.py       # Simulated network: latency, loss, partition, reorder
│   ├── node.py          # RaftNode: core consensus state machine + PreVote + crash
│   ├── cluster.py       # Cluster driver: orchestrates nodes + network + observers
│   ├── prevote.py       # PreVote RPC messages (§6 optimization)          [v2.0]
│   ├── config.py        # YAML/JSON configuration support                  [v2.0]
│   ├── metrics.py       # Metrics collection and JSON/CSV export           [v2.0]
│   ├── logging_utils.py # Python logging integration                       [v2.0]
│   ├── persistence.py   # JSON serialization for cluster save/restore
│   ├── visualizer.py    # ASCII cluster diagrams, partition matrix, log diff
│   ├── scenarios.py     # Pre-defined network failure scenarios
│   ├── invariants.py    # Raft safety property checker
│   └── cli.py           # Command-line interface (9 subcommands)
├── tests/               # pytest test suite (75 tests)
│   ├── test_raft.py         # Core tests (16)
│   ├── test_enhanced.py     # Phase 2 tests (17)
│   ├── test_bug_hunt.py     # Bug regression tests (11)
│   └── test_v2_features.py  # v2.0 feature tests (31)                    [v2.0]
├── examples/            # Example scripts
│   ├── 01_basic_election.py
│   ├── 02_partition_recovery.py
│   ├── 03_snapshotting.py
│   ├── 04_crash_recovery.py       [v2.0]
│   ├── 05_prevote_and_metrics.py  [v2.0]
│   └── 06_config_file.py          [v2.0]
├── configs/             # Example configuration files                    [v2.0]
│   ├── default.yaml
│   ├── high_stress.yaml
│   └── large_cluster.yaml
├── .github/workflows/   # CI configuration                              [v2.0]
├── pyproject.toml
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE
└── README.md
```

## How It Works

### Simulation Model

The simulator uses a **discrete-event model**:

1. **`Cluster.step()`** is called repeatedly, each time advancing the simulation clock by a fixed step.
2. **`Network.drain()`** delivers all messages whose delivery time has arrived.
3. Each node processes its inbox via `RaftNode.handle_message()`, which dispatches to the appropriate RPC handler.
4. Each node is then `tick()`ed, which fires election timeouts (followers/candidates) or heartbeats (leaders).

### Leader Election

- Each follower has a randomized election timeout (default 5–10 time units).
- If a follower doesn't receive an AppendEntries (heartbeat) before the timeout, it transitions to **candidate**, increments its term, votes for itself, and sends `RequestVote` RPCs to all peers.
- A candidate wins if it receives votes from a **majority** of nodes.
- The log-up-to-date check (§5.4.1) ensures that only candidates with sufficiently up-to-date logs can win.

### PreVote Optimization (v2.0)

When PreVote is enabled, a node whose election timer expires does **not** immediately increment its term. Instead, it sends a `PreVoteRequest` with `term + 1` (proposed) and asks peers if they *would* vote for it. Only if a majority grant pre-votes does the node proceed to a real election. This prevents a partitioned node from inflating its term and disrupting the cluster upon reconnection.

```python
cluster = Cluster(size=5, seed=42, prevote_enabled=True)
```

### Log Replication

- The leader maintains `next_index[]` and `match_index[]` for each follower.
- `next_index[i]` is the next log entry to send to follower *i*; `match_index[i]` is the highest entry known to be replicated.
- On failure (log inconsistency), the leader uses the **conflict optimization**: the follower reports `conflict_index` and `conflict_term`, allowing the leader to jump directly to the right position instead of decrementing one-by-one.
- The leader advances `commit_index` to the highest entry replicated on a majority **that is from the current term** (§5.4.2).

### Snapshotting

- When the retained log exceeds `snapshot_threshold` entries, the leader takes a snapshot up to `commit_index`.
- If a follower is so far behind that `next_index` points before the snapshot, the leader sends an `InstallSnapshot` RPC instead of `AppendEntries`.
- The `SnapshotStore` maintains the logical log as a concatenation of the snapshot boundary + retained entries.

### Crash/Recovery (v2.0)

- `crash_node(id)` simulates a node crash: the node stops processing messages and timers. Volatile state (commit_index, next_index, match_index) is lost.
- `restart_node(id)` simulates recovery: persistent state (current_term, voted_for, log, snapshot) is preserved. The node starts as a follower with a fresh election timer.
- The restarted node catches up via normal AppendEntries replication from the leader.

```python
cluster.crash_node(2)       # Node 2 crashes
cluster.run_for(20)         # Cluster continues without it
cluster.restart_node(2)     # Node 2 restarts
cluster.run_for(60)         # Node 2 catches up
```

### Network Model

The `Network` class simulates an asynchronous network with:
- **Configurable latency** (`base_latency` + uniform `jitter`)
- **Packet loss** (`drop_rate`)
- **Reordering** (`reorder=True` shuffles eligible messages)
- **Partitions** — `partition(a, b)` or `partition_groups(group_a, group_b)` split nodes bidirectionally
- **Healing** — `heal_all()` or per-pair healing

## Usage

### As a Library

```python
from raft import Cluster, NetworkConfig, check_all, render_cluster_ascii

# Create a 5-node cluster with deterministic seed
cluster = Cluster(size=5, seed=42, network_config=NetworkConfig(seed=42))

# Run until a leader is elected
leader = cluster.run_until_leader(timeout=100)
print(f"Leader: node {leader}")

# Submit commands (batch + synchronous wait)
cluster.submit_batch([["set", "k1", "v1"], ["set", "k2", "v2"]])
cluster.run_for(20)
assert cluster.all_agree("k1") == "v1"

# Submit and wait for commit
assert cluster.submit_and_wait("set", "k3", 42, timeout=30)

# Check safety invariants
report = check_all(cluster)
assert report.passed

# Visualize
print(render_cluster_ascii(cluster))

# Simulate a partition
cluster.partition_node(leader)
cluster.run_for(30)
print(f"New leader: {cluster.get_leader()}")

# Heal and verify recovery
cluster.heal_all()
cluster.run_for(30)
assert cluster.log_consistent()
assert check_all(cluster).passed
```

### CLI Interface

The CLI provides 9 subcommands:

```bash
# Basic simulation
python3 -m raft.cli run --size 5 --duration 30 --json

# Partition recovery
python3 -m raft.cli partition --size 5 --commands-count 10 --partition-duration 30

# Repeated elections
python3 -m raft.cli election --size 7 --rounds 10

# Run a pre-defined failure scenario
python3 -m raft.cli scenario leader --size 5 --seed 100 --visualize
python3 -m raft.cli scenario flaky --size 5 --drop-rate 0.3

# Visualize cluster state
python3 -m raft.cli visualize --size 5 --commands 10

# Check safety invariants
python3 -m raft.cli invariants --size 5 --partition --verbose

# Benchmark throughput under various network conditions     [v2.0]
python3 -m raft.cli benchmark --size 3 --commands 50 --duration 30

# Simulate node crashes and recoveries                      [v2.0]
python3 -m raft.cli crash --size 5 --seed 42 --duration 40

# Generate or display configuration files                  [v2.0]
python3 -m raft.cli config --size 7 --seed 100
python3 -m raft.cli config --size 5 -o my_config.yaml
```

### Configuration Files

Load cluster configuration from YAML or JSON files:

```bash
# Run with a config file
python3 -m raft.cli run --config configs/default.yaml

# Use the high-stress config
python3 -m raft.cli run --config configs/high_stress.yaml --duration 60
```

Example YAML config (`configs/default.yaml`):

```yaml
cluster:
  size: 5
  seed: 42
  election_timeout_range: [4.0, 8.0]
  heartbeat_interval: 1.0
  snapshot_threshold: 50
  prevote_enabled: false
network:
  base_latency: 1.0
  jitter: 0.5
  drop_rate: 0.0
  reorder: false
  seed: 42
```

Programmatic config usage:

```python
from raft import ClusterConfig, load_config, save_config

# Load from file
cfg = load_config("configs/default.yaml")
cluster = Cluster(
    size=cfg.size,
    network_config=cfg.network,
    seed=cfg.seed,
    election_timeout_range=cfg.election_timeout_range,
    prevote_enabled=cfg.prevote_enabled,
)

# Save a config
save_config(cfg, "my_config.json")
```

### Crash Recovery Simulation

```python
from raft import Cluster, NetworkConfig, check_all

cluster = Cluster(size=5, seed=42, network_config=NetworkConfig(seed=42))
leader = cluster.run_until_leader(timeout=100)

# Submit initial commands
for i in range(5):
    cluster.submit("set", f"k{i}", i)
cluster.run_for(20)

# Crash a follower
follower = cluster.get_followers()[0]
cluster.crash_node(follower)

# Submit more commands while follower is down
for i in range(5, 10):
    cluster.submit("set", f"k{i}", i)
cluster.run_for(20)

# Restart and let it catch up
cluster.restart_node(follower)
cluster.run_for(60)

# Verify consistency
for i in range(10):
    assert cluster.all_agree(f"k{i}") == i

# Safety invariants still hold
assert check_all(cluster).passed
```

### PreVote Optimization

```python
from raft import Cluster, NetworkConfig

# Enable PreVote to prevent disruptive elections
cluster = Cluster(
    size=5,
    seed=42,
    network_config=NetworkConfig(seed=42),
    prevote_enabled=True,
)
leader = cluster.run_until_leader(timeout=200)

# Partition a follower — its term won't inflate
follower = cluster.get_followers()[0]
cluster.partition_node(follower)
cluster.run_for(40)

# Heal — the follower rejoins without disrupting the leader
cluster.heal_all()
cluster.run_for(40)
```

### Metrics Collection

```python
from raft import Cluster, NetworkConfig, MetricsCollector

collector = MetricsCollector()
cluster = Cluster(size=5, seed=42, network_config=NetworkConfig(seed=42))
cluster.add_observer(collector)

cluster.run_until_leader(timeout=100)
cluster.submit("set", "x", 42)
cluster.run_for(20)

# Print summary
print(collector.summary())

# Export to JSON (includes cluster state snapshot)
collector.export_json("metrics.json", cluster=cluster)

# Export events to CSV
collector.export_csv("events.csv")
```

### Observer System

```python
from raft import Cluster, NetworkConfig, ClusterEvent

def my_observer(event: ClusterEvent, data: dict) -> None:
    if event == ClusterEvent.LEADER_ELECTED:
        print(f"New leader: {data['leader']} (term {data['term']})")

cluster = Cluster(size=5, seed=42, network_config=NetworkConfig(seed=42))
cluster.add_observer(my_observer)
cluster.run_until_leader(timeout=100)
```

### Persistence

```python
from raft import Cluster, NetworkConfig, save_cluster, load_cluster
from raft.network import Network

cluster = Cluster(size=5, seed=42)
cluster.run_until_leader(timeout=100)
cluster.submit("set", "x", 42)
cluster.run_for(20)

# Save to JSON
save_cluster(cluster, "cluster_state.json")

# Restore
net = Network(NetworkConfig(seed=42))
cluster2 = load_cluster("cluster_state.json", net)
assert cluster2.all_agree("x") == 42
```

### Failure Scenarios

```python
from raft import Cluster, NetworkConfig, leader_partition_scenario, run_scenario

cluster = Cluster(size=5, seed=100, network_config=NetworkConfig(seed=100))
cluster.run_until_leader(timeout=100)
cluster.submit("set", "x", 1)
cluster.run_for(15)

steps = leader_partition_scenario()
results = run_scenario(cluster, steps, verbose=True)
assert results["log_consistent"]
```

| Scenario | Description |
|----------|-------------|
| `leader` | Isolate the current leader, then heal — tests re-election and catch-up |
| `split` | Split cluster into two equal groups — tests split-brain prevention |
| `rolling` | Sequentially isolate and heal each node — tests rolling upgrades |
| `flaky` | High packet loss then recovery — tests unreliable networks |
| `cascading` | Isolate nodes one by one until quorum lost, then heal — tests extreme failures |

### Custom State Machine

```python
from raft import Cluster
from raft.node import StateMachine

class CounterSM(StateMachine):
    def __init__(self):
        self.count = 0
    def apply(self, command):
        if command == "increment":
            self.count += 1
            return self.count
    def snapshot(self):
        return self.count
    def restore(self, state):
        self.count = state

cluster = Cluster(size=5, state_machine_factory=CounterSM)
```

## Safety Invariants

The invariant checker (`raft.invariants`) verifies five Raft safety properties:

| Invariant | Description |
|-----------|-------------|
| Election Safety | At most one leader per term |
| Log Matching | If two logs contain an entry with the same index and term, they are identical up to that index |
| Leader Completeness | Committed entries are present in the leader's log |
| State Machine Safety | No two nodes apply different commands at the same index |
| Commit Safety | No node has commit_index > last_log_index |

## Visualization

```
================================================================================
  Raft Cluster  |  size=5  time=52.0  leader=1  changes=1
================================================================================
  ★ Node 0 [LDR] T2  commit=10 applied=10 log=10 ← leader
    [1234567890]
  ○ Node 1 [FLW] T2  commit=10 applied=10 log=10
    [1234567890]
  ○ Node 2 [FLW] T2  commit=10 applied=10 log=10
    [1234567890]
  ○ Node 3 [FLW] T2  commit=10 applied=10 log=10
    [1234567890]
  ○ Node 4 [FLW] T2  commit=10 applied=10 log=10
    [1234567890]

  Network: all connected
================================================================================
```

## Examples

See the `examples/` directory for:
- `01_basic_election.py` — Basic leader election and command replication
- `02_partition_recovery.py` — Network partition and recovery
- `03_snapshotting.py` — Snapshotting and log compaction
- `04_crash_recovery.py` — Node crash and recovery with consistency verification **[v2.0]**
- `05_prevote_and_metrics.py` — PreVote optimization with metrics collection **[v2.0]**
- `06_config_file.py` — Loading configuration from YAML files **[v2.0]**

Run any example:

```bash
python3 examples/04_crash_recovery.py
```

## Testing

```bash
cd raft-sim
pip install -e ".[dev]"
pytest tests/ -v
```

**75 tests** covering:
- Network model (latency, loss, partition, reorder)
- Snapshots and log compaction
- Leader election and term progression
- Log replication and conflict optimization
- Partition recovery and split-brain prevention
- Persistence (save/load cluster state)
- Visualization (ASCII diagrams, log diff, timeline)
- Failure scenarios (leader, split, rolling, flaky, cascading)
- Safety invariant checks
- Batch submission and synchronous wait
- Bug regression tests (11 tests)
- PreVote optimization (7 tests) **[v2.0]**
- Crash/recovery simulation (6 tests) **[v2.0]**
- Configuration files (5 tests) **[v2.0]**
- Metrics collection (5 tests) **[v2.0]**
- Observer system (3 tests) **[v2.0]**
- Logging utilities (3 tests) **[v2.0]**

Run with coverage:

```bash
pytest tests/ --cov=raft --cov-report=term-missing
```

## Known Issues (Resolved)

The following bugs were found during the Phase 3 bug hunt and have been fixed:

1. **InstallSnapshot never sent to lagging followers** — The `_maybe_send_snapshot()` method was defined but never called from `_send_append_entries()`. When a follower fell behind the leader's snapshot boundary, the leader attempted regular AppendEntries instead of sending an InstallSnapshot RPC. **Fix**: Added a check in `_send_append_entries()` that detects when `next_index` falls before the snapshot boundary and calls `_maybe_send_snapshot()` instead.

2. **Statistics never incremented** — `NodeStats.entries_committed` and `ClusterStats.total_elections`/`commands_committed` were defined but never updated. **Fix**: `entries_committed` is now incremented in `_advance_commit_index()`. `total_elections` and `commands_committed` are tracked in `Cluster.step()` by diffing cumulative node stats.

3. **Version mismatch** — `pyproject.toml` reported version 1.0.0 while `__init__.py` reported 1.1.0. **Fix**: Aligned `pyproject.toml` to 1.1.0.

4. **Log bar committed/uncommitted indistinguishable** — `_render_log_bar()` applied `.lower()` to digit strings (e.g., `"1"`) which are already lowercase, making committed and uncommitted entries look identical. **Fix**: Uncommitted entries are now rendered as `~` instead of digits, making them visually distinct from committed entries (digits).

5. **Cluster events never logged** — `ClusterEvent.ELECTION_STARTED`, `LOG_COMMITTED`, `SNAPSHOT_TAKEN`, and `MEMBERSHIP_CHANGE` were defined but never emitted to the event log. **Fix**: `ELECTION_STARTED` and `LOG_COMMITTED` are now logged in `Cluster.step()`.

6. **`load_cluster` ignored passed network** — The function created a new `Cluster` (with its own network) instead of using the network passed as a parameter, making the parameter misleading. **Fix**: The function now directly constructs the cluster object using the passed network.

7. **`all_agree` ambiguous for None values** — `all_agree()` returned `None` both when all nodes agreed the value was absent and when they disagreed, making the two cases indistinguishable. **Fix**: Added `all_agree_detailed()` which returns `(agreed: bool, value)` to disambiguate.

8. **`truncate_from` into snapshot region silently corrupted store** — Truncating at an index within the snapshot region silently discarded the entire snapshot and all retained entries, corrupting the log store. **Fix**: The method now raises a `ValueError` when asked to truncate into the snapshot region, since committed entries are permanent in Raft.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for the full version history.

### v2.0.0 Highlights
- PreVote optimization (Raft §6)
- Crash/recovery simulation with persistent state
- YAML/JSON configuration file support
- Metrics collection and JSON/CSV export
- Observer/callback system
- Logging integration
- Linearizable reads (ReadIndex)
- 3 new CLI subcommands (benchmark, crash, config)
- GitHub Actions CI
- 31 new tests (75 total)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on developing and contributing to raft-sim.

## Roadmap

- [ ] Batch log replication (multiple entries per AppendEntries with flow control)
- [ ] Raft group configuration changes (joint consensus with C_old + C_new)
- [ ] ReadIndex with actual heartbeat round-trip for linearizable reads
- [ ] Network topology model (weighted graph instead of flat partition set)
- [ ] Protocol Buffers serialization for inter-node messages
- [ ] Web dashboard for real-time visualization
- [ ] Comparison mode: run two configurations side-by-side
- [ ] Chaos engineering framework with random failure injection
- [ ] Performance profiling and optimization (Cython hotspots)
- [ ] Multi-Raft (multiple Raft groups sharing the same nodes)

## References

- Ongaro, D., & Ousterhout, J. (2014). *In Search of an Understandable Consensus Algorithm (Extended Version)*. USENIX ATC.
- Ongaro, D. (2014). *Consensus: Bridging Theory and Practice*. PhD Thesis (PreVote, ReadIndex, and other optimizations).
- The [Raft paper](https://raft.github.io/raft.pdf) and [visualization](https://raft.github.io/).

## License

MIT — See [LICENSE](LICENSE) for details.