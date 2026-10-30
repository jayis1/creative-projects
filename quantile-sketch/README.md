# Quantile Sketch

A dependency-free streaming quantile estimator for large numeric streams. The Greenwald–Khanna summary stores rank bounds rather than every observation, allowing approximate percentile queries in sublinear memory.

## Demo

`python3 quantile_sketch.py --demo` summarizes 10,000 deterministic values and prints selected quantiles and summary size.

## Usage

Provide a JSON numeric array either in a file or on stdin:

`python3 quantile_sketch.py samples.jsonl --jsonl --epsilon 0.01 --quantiles 0.5 0.95 0.99` reads one JSON number per non-empty line incrementally; omit the filename to read stdin. Invalid records report their line number. For JSON-array input use `python3 quantile_sketch.py samples.json --quantiles 0.5 0.95 0.99`.

Smaller epsilon gives tighter rank bounds at a higher memory cost. The sketch accepts finite numeric observations; values are not retained as a raw stream. API: `QuantileSketch(epsilon)`, `insert`, `extend`, `quantile`, and `summary_size`.

## How it works

Each sorted summary entry stores a representative value, a minimum rank increment `g`, and a rank uncertainty `delta`. Insertions maintain order; periodic compression merges adjacent tuples only when their combined rank uncertainty fits the `2 * epsilon * n` threshold. A query walks cumulative rank bounds and returns an estimate within the configured rank-error budget.

## Limitations

The command-line interface reads a JSON array into memory before summarizing, while the Python API supports true incremental ingestion. This is an approximate rank guarantee, not a bound on numeric-value error. Python 3.10+, standard library only.

## Tests

Run `python3 -m unittest discover -s tests -v`.
