# Process Miner

Discover a compact process model from event-log CSVs. It groups events by case, orders them by timestamp (stable input order for ties), and reports activity frequencies, case starts/ends, and directly-follows edge counts. It uses only Python's standard library.

## See it in 60 seconds

From this directory run `python3 process_miner.py --demo`. The JSON output includes two cases: `order` branches to `pay` and `cancel`; `pay` continues to `ship`.

Analyze a CSV with columns `case,activity,timestamp` using `python3 process_miner.py events.csv`.

## How it works

Each case trace is sorted by timestamp then original row position. A single pass counts occurrences and adjacent activity pairs; the output is deterministic and JSON-serializable. This is a directly-follows abstraction, not a probabilistic or conformance model.

## Tests

Run `python3 -m unittest discover -s process-miner/tests` from the repository root.
