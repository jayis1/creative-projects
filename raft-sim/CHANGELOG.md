# Changelog

All notable changes to the raft-sim project are documented in this file.

## [2.0.0] — 2026-06-20

### Added — Major Features
- **PreVote optimization** (Raft thesis §6) — prevents disruptive elections
  when a partitioned node reconnects. New `PreVoteRequest`/`PreVoteResponse`
  RPC types and handler logic in `RaftNode`. Enabled via `prevote_enabled=True`.
- **Crash/recovery simulation** — `crash_node()` / `restart_node()` on `Cluster`,
  with `crash()` / `restart()` on `RaftNode`. Crashed nodes stop processing
  messages; persistent state (term, log) survives restart. New `NODE_CRASHED`
  and `NODE_RESTARTED` cluster events.
- **Configuration file support** — `raft.config` module with `ClusterConfig`,
  `load_config()`, `save_config()` supporting YAML and JSON formats. Three
  example configs in `configs/` directory.
- **Metrics collection and export** — `raft.metrics.MetricsCollector` observer
  that records all cluster events and exports to JSON or CSV.
- **Observer/callback system** — `Cluster.add_observer()` / `remove_observer()`
  for event-driven monitoring without polling.
- **Logging integration** — `raft.logging_utils` with `configure_logging()`,
  `get_logger()`, and `StructuredEventLogger` for Python `logging` integration.
- **Linearizable reads** — `RaftNode.linearizable_read()` using the ReadIndex
  technique (opt-in via `linearizable_reads=True`).
- **Benchmark CLI subcommand** — tests throughput under various network
  conditions (latency × drop rate matrix).
- **Crash recovery CLI subcommand** — interactive crash/recovery demo.
- **Config CLI subcommand** — generate and display configuration files.
- **GitHub Actions CI** — runs tests on Python 3.10, 3.11, 3.12 with
  CLI smoke tests.
- **LICENSE** — MIT license file.
- **CONTRIBUTING.md** — developer guide for contributing.
- **3 new example scripts** — crash recovery, PreVote+metrics, config files.
- **31 new tests** (75 total) covering PreVote, crash recovery, config,
  metrics, observers, and logging.

### Changed
- Version bumped to 2.0.0.
- `pyproject.toml` now declares `pyyaml` as a dependency.
- CLI refactored to support `--config` flag for loading YAML/JSON configs.
- CLI now has 9 subcommands (was 6): added `benchmark`, `crash`, `config`.
- `RaftNode` constructor accepts `prevote_enabled` and `linearizable_reads` flags.
- `Cluster` constructor accepts `prevote_enabled` and `linearizable_reads` flags.
- `Cluster.step()` skips crashed nodes (no message delivery, no ticking).
- `Cluster.get_leader()` excludes crashed nodes.
- Node `status()` includes `crashed` and `prevote_enabled` fields.

## [1.1.0] — 2026-06-20

### Added
- JSON persistence and serialization (`save_cluster`, `load_cluster`).
- ASCII visualization (cluster diagrams, partition matrix, log diff, timeline).
- 5 pre-defined failure scenarios (leader, split, rolling, flaky, cascading).
- 5 Raft safety invariant checks.
- Batch submission (`submit_batch`, `submit_and_wait`).
- 3 new CLI subcommands (`scenario`, `visualize`, `invariants`).
- 17 new tests (33 total).

### Fixed (Phase 3 Bug Hunt)
- InstallSnapshot now sent to lagging followers.
- `entries_committed`, `total_elections`, `commands_committed` stats now updated.
- Version mismatch between `pyproject.toml` and `__init__.py` resolved.
- Log bar committed/uncommitted entries now visually distinct.
- `ELECTION_STARTED` and `LOG_COMMITTED` events now logged.
- `load_cluster` now uses the passed network parameter.
- `all_agree_detailed()` added to disambiguate None values.
- `truncate_from` into snapshot region now raises `ValueError`.
- 11 regression tests added (44 total).

## [1.0.0] — 2026-06-20

### Added
- Core Raft consensus algorithm: leader election, log replication, snapshotting.
- Pluggable network model with latency, jitter, packet loss, reordering, partitions.
- Membership changes (simplified joint consensus).
- Key-value state machine with pluggable interface.
- CLI with 3 subcommands (`run`, `partition`, `election`).
- Per-node and cluster-wide statistics.
- 16 tests.