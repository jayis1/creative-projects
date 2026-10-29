# Entropy Lab

A dependency-free Shannon entropy and symbol-frequency analyzer for UTF-8 text. It reports empirical zero-order entropy (not a compression guarantee), normalized entropy, and the equivalent effective alphabet size; Unicode is counted by code point.

Maintained by [jayis1](https://github.com/jayis1).

## Try it in 10 seconds

```sh
printf 'abracadabra' | python3 entropy_lab.py
```

The command reports 11 symbols, 5 distinct code points, Shannon entropy, normalized entropy, effective symbols, and a frequency table.

## Usage

```sh
python3 entropy_lab.py --help
printf 'abracadabra' | python3 entropy_lab.py --top 5
printf 'aabb' | python3 entropy_lab.py --json --window 2
python3 -m unittest discover -s . -p 'test_*.py'
```

Input is read from a UTF-8 file or standard input. `--top N` controls the number of displayed symbols. `--json` emits machine-readable JSON. `--window N` additionally reports the unweighted mean entropy of consecutive, non-overlapping windows, including a final short window. Both numeric options must be non-negative; zero disables window analysis. Unreadable files and malformed UTF-8 produce a clear argparse error.

## Entropy metrics

- **Shannon entropy** (`entropy`) is `-Σ p(x) log₂ p(x)` in bits per code point.
- **Normalized entropy** (`normalized_entropy`) divides by `log₂(distinct)`, scaling distribution evenness to 0–1. It is zero for empty and single-symbol input.
- **Effective symbols** (`effective_symbols`) is `2 ** entropy`: the size of a uniform alphabet with the same entropy. It ranges from 1 to the number of distinct symbols.

For `ab`, entropy is 1 bit/symbol, normalized entropy is 1, and effective symbols is 2. JSON output includes all three metrics and the original frequencies.

## How it works

A frequency table is built in one pass; the probability of each code point is its count divided by the input length. The tool computes the metrics directly from that empirical distribution. Input is never modified or transmitted.

## Limitations

This is zero-order character entropy, not a compressor or contextual language model. It does not predict actual encoded size. Unicode is counted by code point rather than grapheme cluster. Window means weight each window equally, including a shorter final window.

## Tests

Run `python3 -m unittest discover -s . -p 'test_*.py'` from this directory. The dependency-free suite covers entropy metrics, empty and constant input, Unicode, JSON/window CLI behavior, invalid types, and negative bounds.

## Recent improvements

- Added normalized entropy and effective-alphabet-size metrics to the API, text output, and JSON output, with coverage for uniform, biased, constant, and empty distributions.
- Earlier pipeline improvements added JSON output and non-overlapping window analysis.

Alternatives considered: event-log anomaly scoring, word-frequency Zipf plotting, byte-level protocol histograms.
