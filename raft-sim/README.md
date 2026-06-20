# Raft Consensus Algorithm Simulator

A from-scratch, discrete-event simulation of the [Raft consensus algorithm](https://raft.github.io/) — the algorithm that powers etcd, Consul, and countless distributed systems. This implementation covers leader election, log replication, snapshotting, membership changes, and network partition recovery, all driven by a pluggable network model.

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

## Architecture

```
raft-sim/
├── raft/
│   ├── __init__.py      # Package exports
│   ├── types.py         # Data types: NodeRole, LogEntry, RPC messages, NodeState
│   ├── snapshot.py      # Snapshot + SnapshotStore (log compaction)
│   ├── network.py       # Simulated network: latency, loss, partition, reorder
│   ├── node.py          # RaftNode: the core consensus state machine
│   ├── cluster.py       # Cluster driver: orchestrates nodes + network
│   ├── persistence.py   # JSON serialization for cluster save/restore
│   ├── visualizer.py    # ASCII cluster diagrams, partition matrix, log diff
│   ├── scenarios.py     # Pre-defined network failure scenarios
│   ├── invariants.py    # Raft safety property checker
│   └── cli.py           # Command-line interface (6 subcommands)
├── tests/               # pytest test suite (33 tests)
├── examples/            # Example scripts
├── pyproject.toml
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

### Log Replication

- The leader maintains `next_index[]` and `match_index[]` for each follower.
- `next_index[i]` is the next log entry to send to follower *i*; `match_index[i]` is the highest entry known to be replicated.
- On failure (log inconsistency), the leader uses the **conflict optimization**: the follower reports `conflict_index` and `conflict_term`, allowing the leader to jump directly to the right position instead of decrementing one-by-one.
- The leader advances `commit_index` to the highest entry replicated on a majority **that is from the current term** (§5.4.2).

### Snapshotting

- When the retained log exceeds `snapshot_threshold` entries, the leader takes a snapshot up to `commit_index`.
- If a follower is so far behind that `next_index` points before the snapshot, the leader sends an `InstallSnapshot` RPC instead of `AppendEntries`.
- The `SnapshotStore` maintains the logical log as a concatenation of the snapshot boundary + retained entries.

### Network Model

The `Network` class simulates an asynchronous network with:
- **Configurable latency** (`base_latency` + uniform `jitter`)
- **Packet loss** (`drop_rate`)
- **Reordering** (`reorder=True` shuffles eligible messages)
- **Partitions** — `partition(a, b)` or `partition_groups(group_a, group_b)` split nodes bidirectionally
- **Healing** — `heal_all()` or per-pair healing

### Safety Invariants

The invariant checker (`raft.invariants`) verifies five Raft safety properties:

| Invariant | Description |
|-----------|-------------|
| Election Safety | At most one leader per term |
| Log Matching | If two logs contain an entry with the same index and term, they are identical up to that index |
| Leader Completeness | Committed entries are present in the leader's log |
| State Machine Safety | No two nodes apply different commands at the same index |
| Commit Safety | No node has commit_index > last_log_index |

### Failure Scenarios

| Scenario | Description |
|----------|-------------|
| `leader` | Isolate the current leader, then heal — tests re-election and catch-up |
| `split` | Split cluster into two equal groups — tests split-brain prevention |
| `rolling` | Sequentially isolate and heal each node — tests rolling upgrades |
| `flaky` | High packet loss then recovery — tests unreliable networks |
| `cascading` | Isolate nodes one by one until quorum lost, then heal — tests extreme failures |

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

### Persistence

```python
from raft import Cluster, save_cluster, load_cluster
from raft.network import Network, NetworkConfig

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

### CLI

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
```

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

## Examples

See the `examples/` directory for:
- `01_basic_election.py` — Basic leader election and command replication
- `02_partition_recovery.py` — Network partition and recovery
- `03_snapshotting.py` — Snapshotting and log compaction

## Testing

```bash
cd raft-sim
pip install -e .
pytest tests/ -v
```

44 tests covering network, snapshots, leader election, log replication, partition recovery, persistence, visualization, scenarios, invariants, batch submission, and bug regression tests.

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

## References

- Ongaro, D., & Ousterhout, J. (2014). *In Search of an Understandable Consensus Algorithm (Extended Version)*. USENIX ATC.
- The [Raft paper](https://raft.github.io/raft.pdf) and [visualization](https://raft.github.io/).

## License

MIT