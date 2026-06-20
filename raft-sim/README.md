# Raft Consensus Algorithm Simulator

A from-scratch, discrete-event simulation of the [Raft consensus algorithm](https://raft.github.io/) — the algorithm that powers etcd, Consul, and countless distributed systems. This implementation covers leader election, log replication, snapshotting, membership changes, and network partition recovery, all driven by a pluggable network model.

## What is Raft?

Raft is a consensus algorithm designed for understandability. It solves the problem of getting multiple servers to agree on a single sequence of values (a replicated log) despite node failures, network partitions, and message loss. It decomposes consensus into three subproblems:

1. **Leader Election** — Exactly one leader is elected per term. If the leader fails, followers detect the timeout and a new election begins.
2. **Log Replication** — The leader accepts client commands, appends them to its log, and replicates them to followers. Once a majority acknowledges, the entry is *committed*.
3. **Safety** — Raft guarantees that committed entries are identical across all nodes and never overwritten.

## Features

- **Leader Election** with randomized election timeouts, RequestVote RPCs, and term-based voting
- **Log Replication** via AppendEntries RPCs with the conflict-optimization (fast log backtracking via `conflict_index`/`conflict_term`)
- **Snapshotting** — Log compaction via `InstallSnapshot` RPC when the log exceeds a configurable threshold
- **Membership Changes** — Add/remove nodes at runtime (simplified joint consensus)
- **Network Failure Model** — Configurable latency, jitter, packet loss, reordering, and arbitrary partitions between any set of nodes
- **Partition Recovery** — Automatically re-elects a leader when the old leader is isolated, and catches up the old leader after healing
- **State Machine** — Pluggable state machine interface with a built-in key-value store
- **CLI** — Three subcommands (`run`, `partition`, `election`) for running simulations from the command line
- **Statistics** — Per-node and cluster-wide stats: elections, votes, messages, leader changes, snapshots

## Architecture

```
raft-sim/
├── raft/
│   ├── __init__.py     # Package exports
│   ├── types.py        # Data types: NodeRole, LogEntry, RPC messages, NodeState
│   ├── snapshot.py     # Snapshot + SnapshotStore (log compaction)
│   ├── network.py      # Simulated network: latency, loss, partition, reorder
│   ├── node.py         # RaftNode: the core consensus state machine
│   ├── cluster.py      # Cluster driver: orchestrates nodes + network
│   └── cli.py          # Command-line interface
├── tests/              # pytest test suite
├── examples/           # Example scripts
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

## Usage

### As a Library

```python
from raft import Cluster, NetworkConfig

# Create a 5-node cluster with deterministic seed
cluster = Cluster(size=5, seed=42, network_config=NetworkConfig(seed=42))

# Run until a leader is elected
leader = cluster.run_until_leader(timeout=100)
print(f"Leader: node {leader}")

# Submit commands
cluster.submit("set", "key1", "value1")
cluster.submit("set", "key2", 42)
cluster.run_for(30)  # let replication complete

# Check consistency
assert cluster.all_agree("key1") == "value1"
assert cluster.all_agree("key2") == 42
assert cluster.log_consistent()

# Simulate a partition
cluster.partition_node(leader)
cluster.run_for(30)
print(f"New leader: {cluster.get_leader()}")

# Heal and verify recovery
cluster.heal_all()
cluster.run_for(30)
assert cluster.log_consistent()
```

### CLI

```bash
# Basic simulation
python3 -m raft.cli run --size 5 --duration 30 --json

# Partition recovery
python3 -m raft.cli partition --size 5 --commands-count 10 --partition-duration 30

# Repeated elections
python3 -m raft.cli election --size 7 --rounds 10
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
- Basic leader election and command replication
- Network partition recovery
- Snapshotting with log compaction
- Membership changes (add/remove nodes)

## Testing

```bash
cd raft-sim
pip install -e .
pytest tests/ -v
```

## References

- Ongaro, D., & Ousterhout, J. (2014). *In Search of an Understandable Consensus Algorithm (Extended Version)*. USENIX ATC.
- The [Raft paper](https://raft.github.io/raft.pdf) and [visualization](https://raft.github.io/).

## License

MIT