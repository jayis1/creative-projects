# Entropy Lab

A dependency-free Shannon entropy and symbol-frequency analyzer for UTF-8 text. It reports empirical zero-order entropy (not a compression guarantee) and handles Unicode code points directly.

## Try it in 10 seconds

```sh
printf 'abracadabra' | python3 entropy_lab.py
```

Expected: `Symbols: 11  distinct: 5` and an entropy value of `2.040373 bits/symbol`.

## How it works

The tool counts occurrences with a frequency table, then computes `-Σ p(x) log₂ p(x)`. Input may be a UTF-8 file or standard input. No data is modified or transmitted.

## Usage

```sh
python3 entropy_lab.py sample.txt --top 5
python3 -m unittest discover -s . -p 'test_*.py'
```

`--top` controls how many frequent symbols are shown. Empty input reports zero entropy. `--json` emits machine-readable output; `--window N` reports the mean entropy of consecutive, non-overlapping windows (including a final short window). `--window` and `--top` must be non-negative. Malformed UTF-8 and unreadable files produce an argparse error. Entropy measures single-symbol distribution only; it does not model context or predict actual encoded size.

```sh
printf 'aabb' | python3 entropy_lab.py --json --window 2
```

## Known Issues (Resolved)

No implementation bugs were confirmed in the bounded source review. Adversarial regression coverage now checks empty input, Unicode, invalid API types, negative CLI bounds, and window processing with a short final chunk; all pass. No fixes are claimed from this review.

## Limitations

This is zero-order character entropy, not a compressor or contextual language model. Unicode is counted by code point, not grapheme cluster.

Alternatives considered: event-log anomaly scoring, word-frequency Zipf plotting, byte-level protocol histograms.
