# Temporal Query Engine

A dependency-free interval index for event timelines. It combines Allen's 13 interval relations with a treap-backed augmented interval tree, giving fast overlap queries while preserving deterministic output ordering.

## How it works

`Event` models a validated half-open interval `[start, end)`. `Event.relation_to` classifies two intervals using Allen's interval algebra. `IntervalIndex` stores events in a randomized-priority treap; each node tracks the maximum end point in its subtree, allowing overlap searches to prune irrelevant branches. Insert/delete are expected O(log n), overlap queries are O(log n + k).

## Usage

From the repository root:

```bash
python3 -m unittest discover -s temporal-query-engine/tests -t temporal-query-engine
python3 -m temporal_query.cli 2 6 --event deploy:0:3:release --event outage:4:8:incident --event idle:10:12
```

Expected query output is JSON containing `deploy` and `outage`. The CLI accepts `ID:START:END[:LABEL]`; `--label LABEL` filters results exactly. Malformed events and non-positive intervals return an error.

Python API:

```python
from temporal_query import Event, IntervalIndex
idx = IntervalIndex([Event("deploy", 0, 3), Event("outage", 4, 8)])
print([event.id for event in idx.overlaps(2, 5)])  # deploy, outage
```

## Known Issues (Resolved)

- Non-finite endpoints (`NaN`/infinity) could enter the index and make ordering/pruning undefined. `Event` now rejects them; regression coverage is in `test_duplicate_and_invalid`.

## Tests and limits

The test suite covers relation classification, ordering, duplicate IDs, invalid ranges, deletion, and boundary-touching intervals. The package is standard-library only and performs no file or network I/O. Event identifiers must be unique and interval endpoints must be finite values supplied by the caller.
