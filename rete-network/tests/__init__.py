"""
Comprehensive test suite for the Rete engine.

Tests are organized by feature area:
  - test_core.py       — basic engine, facts, conditions, rules
  - test_join.py       — multi-condition joins, variable binding
  - test_negation.py   — negated conditions (NCC)
  - test_conflict.py   — conflict resolution strategies
  - test_tms.py        — truth maintenance system
  - test_query.py      — query API
  - test_serialization.py — JSON/YAML serialization
  - test_cli.py        — CLI smoke tests
  - test_listeners.py  — event listener / observer
  - test_visualization.py — network visualization
  - test_batch.py      — batch operations
  - test_edge_cases.py — edge cases and error handling

Existing files:
  - test_bug_hunt.py   — regression tests from bug hunt phase
"""