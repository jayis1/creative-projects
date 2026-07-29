# 🧩 BPE Tokenizer

> A from-scratch **Byte Pair Encoding (BPE)** tokenizer with WordPiece, Unigram/Viterbi segmentation, BPE-dropout, config files, and tokenizer comparison tools.

![Python](https://img.shields.io/badge/python-3.10+-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Tests](https://img.shields.io/badge/tests-85%20passing-brightgreen)
![Version](https://img.shields.io/badge/version-3.0.0-orange)
![Pure Stdlib](https://img.shields.io/badge/pure-stdlib-success)

A pure-Python implementation of the tokenization algorithms used by **GPT-2**, **GPT-4**, **LLaMA-3**, **BERT**, and **SentencePiece** — built from scratch with no external NLP dependencies. Features four encoding algorithms (BPE, Viterbi/Unigram, WordPiece, BPE-dropout), configurable pre-tokenizers, text normalization, config file support, progress callbacks, and a 12-subcommand CLI.

---

## Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Usage](#usage)
  - [Python API](#python-api)
  - [WordPiece Encoding (BERT-style)](#wordpiece-encoding-bert-style)
  - [Unigram/Viterbi Segmentation](#unigramviterbi-segmentation)
  - [BPE-Dropout](#bpe-dropout)
  - [Config Files](#config-files)
  - [Progress Callbacks](#progress-callbacks)
  - [Tokenizer Comparison](#tokenizer-comparison)
  - [Text Normalization](#text-normalization)
  - [Analysis & Diagnostics](#analysis--diagnostics)
  - [CLI](#cli)
- [Architecture](#architecture)
- [How It Works](#how-it-works)
- [Testing](#testing)
- [Known Issues (Resolved)](#known-issues-resolved)
- [Changelog](#changelog)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

---

## Features

### Core BPE
- **Greedy merge training**: learns the most frequent byte/character pairs iteratively, with deterministic tie-breaking
- **Incremental pair counting**: optimized training that updates counts incrementally instead of recomputing from scratch each iteration
- **Greedy-rank encoding**: applies learned merges by priority (lowest rank = highest priority)
- **Character-level mode**: operates on Unicode codepoints
- **Byte-level mode**: GPT-2-style byte-to-unicode mapping (handles any byte value, including invalid UTF-8)
- **Pre-tokenization**: GPT-2 / GPT-4 / Llama-3 regex patterns, whitespace split, or no-split (with stdlib `re` fallback when `regex` module is unavailable)
- **Special tokens**: PAD, BOS, EOS, UNK (configurable)
- **Batch encoding**: with optional padding and max-length truncation
- **LRU encode cache**: thread-safe, configurable capacity
- **JSON serialization**: save/load trained tokenizers (including normalizer config)
- **train_from_file**: train directly from a corpus file path

### Four Encoding Algorithms
| Algorithm | Style | Description |
|----------|-------|-------------|
| **BPE** | GPT-2/4 | Greedy merge-rank encoding (standard) |
| **Viterbi/Unigram** | SentencePiece | DP-based globally optimal segmentation |
| **WordPiece** | BERT | Longest-match-first greedy segmentation |
| **BPE-dropout** | Research | Stochastic merge dropping for data augmentation |

### Text Normalization
- **Configurable normalizer** with 8 flags: `LOWERCASE`, `NFC`, `NFD`, `NFKC`, `NFKD`, `STRIP_ACCENTS`, `STRIP_WHITESPACE`, `REMOVE_CONTROL`, `CRLF_TO_LF`, `REPLACE_ZWSP`
- Applied before pre-tokenization during both training and encoding
- Serialized with the tokenizer for consistent encoding after load

### Post-Processing
- **Truncation strategies**: right, left, middle (with special-token preservation)
- **Attention mask generation**: binary mask for padding tokens
- **Special-token stripping**: remove specials from id sequences

### Config & Tooling
- **JSON/TOML config files**: reproducible training and encoding setups
- **Progress callbacks**: monitor training progress programmatically
- **Custom exception hierarchy**: `BPETokenizerError` base with specific subclasses
- **Centralized logging**: configurable via `configure_logging()`

### Analysis & Diagnostics
- **TokenizerAnalyzer**: evaluates tokenizer quality on a corpus
- **Metrics**: compression ratio (chars/token, bytes/token), token-length distribution (mean/median/min/max), subword fertility (tokens/word), coverage, UNK rate
- **Top-N token frequency**: most common tokens by count
- **Piece-length histogram**: distribution of token lengths
- **Human-readable summary**: formatted report via `analyzer.summary()`

### Tokenizer Comparison
- **Side-by-side comparison** of two tokenizers on a shared corpus
- **Agreement rate**: fraction of texts producing identical id sequences
- **Compression comparison**: chars/token for each tokenizer
- **Per-text mismatch details**: see exactly where tokenizers differ

### CLI
12 subcommands: `train`, `train-config`, `encode`, `decode`, `batch`, `dropout`, `viterbi`, `wordpiece`, `stats`, `roundtrip`, `analyze`, `compare`

---

## Quick Start

```bash
cd bpe-tokenizer
pip install -e .
bpe-tokenizer train examples/sample.txt -o tokenizer.json --vocab-size 1000 --lowercase
bpe-tokenizer encode "the quick brown fox" -m tokenizer.json --pieces
```

```python
from bpe_tokenizer import BPETokenizer, TrainingConfig, Normalization

tok = BPETokenizer()
cfg = TrainingConfig(vocab_size=1000, normalizer_flags=int(Normalization.LOWERCASE.value))
tok.train("Your training corpus text here...", cfg)

ids = tok.encode("hello world", add_bos=True, add_eos=True)
text = tok.decode(ids)
print(f"ids={ids}, decoded={text!r}")
```

---

## Installation

### From source (recommended)

```bash
cd bpe-tokenizer
pip install -e .

# Optional: better Unicode regex support (recommended for GPT-4/Llama-3 patterns)
pip install regex

# Development dependencies
pip install -e ".[dev]"
```

### Requirements

- **Python**: 3.10+ (3.11+ required for TOML config files)
- **Dependencies**: None (pure stdlib). `regex` package is optional.

---

## Usage

### Python API

```python
from bpe_tokenizer import BPETokenizer, TrainingConfig, Normalization

# Train with lowercase normalization
tok = BPETokenizer()
cfg = TrainingConfig(
    vocab_size=1000,
    byte_mode=False,
    pretokenizer="gpt4",
    normalizer_flags=int(Normalization.LOWERCASE.value),
)
tok.train("Your training corpus text here...", cfg)

# Encode
ids = tok.encode("hello world", add_bos=True, add_eos=True)

# Decode
text = tok.decode(ids)

# Advanced encoding with truncation + attention mask
result = tok.encode_advanced(
    "hello world",
    max_length=16,
    truncation="right",
    return_attention_mask=True,
    pad_id=0,
)
# result = {"input_ids": [...], "attention_mask": [...]}

# Batch with padding
batch = tok.encode_batch(["hello", "world", "foo"], padding=True)

# Save / Load (normalizer config is preserved)
tok.save("tokenizer.json")
tok2 = BPETokenizer.load("tokenizer.json")

# Train from file
tok3 = BPETokenizer()
tok3.train_from_file("corpus.txt", cfg)
```

### WordPiece Encoding (BERT-style)

WordPiece performs longest-match-first segmentation, the algorithm used by BERT:

```python
from bpe_tokenizer import WordPieceEncoder

wp = WordPieceEncoder(tok, use_continuation_marker=False)
pieces = wp.tokenize("the quick brown fox")
ids = wp.encode("the quick brown fox")
print(f"pieces: {pieces}")
print(f"decoded: {tok.decode(ids)!r}")
```

### Unigram/Viterbi Segmentation

```python
from bpe_tokenizer.encoder import BPESentencePiece

# Unigram/Viterbi encoding (optimal segmentation)
sp = BPESentencePiece(tok)
ids = sp.encode("hello world")
```

### BPE-Dropout

```python
from bpe_tokenizer.encoder import bpe_dropout
import random

# BPE-dropout (stochastic, for data augmentation)
rng = random.Random(42)
for _ in range(5):
    ids = bpe_dropout(tok, "hello world", dropout=0.1, rng=rng)
    print(tok.id_to_pieces(ids))
```

### Config Files

Create a JSON config file for reproducible training:

```json
{
  "training": {
    "vocab_size": 32000,
    "byte_mode": false,
    "pretokenizer": "gpt4",
    "min_frequency": 2,
    "normalizer": ["lowercase", "nfc"]
  },
  "encoding": {
    "add_bos": true,
    "add_eos": true,
    "max_length": 512,
    "truncation": "right",
    "return_attention_mask": true,
    "pad_id": 0
  }
}
```

Use it in Python:

```python
from bpe_tokenizer import load_config, BPETokenizer

config = load_config("config.json")
cfg = config.to_training_config()
tok = BPETokenizer()
tok.train(corpus, cfg)

# Use encoding settings from config
enc_kwargs = config.encoding_kwargs()
result = tok.encode_advanced("hello world", **enc_kwargs)
```

Or via CLI:

```bash
bpe-tokenizer train-config config.json corpus.txt -o tokenizer.json
```

### Progress Callbacks

Monitor training progress programmatically:

```python
from bpe_tokenizer import BPETokenizer, TrainingConfig, ProgressInfo

def callback(info: ProgressInfo) -> None:
    print(f"  [{info.iteration}/{info.max_merges}] "
          f"({info.progress_pct:.1f}%) "
          f"merge={info.merged_token!r} count={info.merge_count}")

tok = BPETokenizer()
tok.train(corpus, TrainingConfig(vocab_size=1000), progress_callback=callback)
```

### Tokenizer Comparison

Compare two tokenizers on a shared corpus:

```python
from bpe_tokenizer import TokenizerComparison

comp = TokenizerComparison(tok_small, tok_large)
summary = comp.summary(["the quick brown fox", "lazy dog"])
print(summary)
# Reports: agreement rate, avg tokens, chars/token, per-text mismatches
```

### Text Normalization

```python
from bpe_tokenizer import Normalization, Normalizer

# Combine multiple normalizations
norm = Normalizer(Normalization.LOWERCASE | Normalization.STRIP_ACCENTS | Normalization.STRIP_WHITESPACE)
print(norm("  Héllo  Wörld  "))  # → "hello world"
```

### Analysis & Diagnostics

```python
from bpe_tokenizer import TokenizerAnalyzer

analyzer = TokenizerAnalyzer(tok)
texts = ["the quick brown fox", "lazy dog jumps"]
result = analyzer.analyze(texts)
print(f"Compression: {result.chars_per_token:.2f} chars/token")
print(f"UNK rate: {result.unk_rate:.2%}")

# Or get a formatted summary
print(analyzer.summary(texts))
```

### CLI

```bash
# Train (with lowercase + strip accents)
bpe-tokenizer train corpus.txt -o tokenizer.json --vocab-size 2000 --byte-mode --lowercase --strip-accents --progress

# Train from config file
bpe-tokenizer train-config config.json corpus.txt -o tokenizer.json

# Encode
bpe-tokenizer encode "hello world" -m tokenizer.json --bos --eos --pieces

# Encode with truncation + padding + attention mask
bpe-tokenizer encode "hello world" -m tokenizer.json --max-length 16 --pad --attention-mask

# Decode
bpe-tokenizer decode 1 42 17 2 -m tokenizer.json

# Batch encode
bpe-tokenizer batch texts.txt -m tokenizer.json --pad --output encoded.json

# BPE-dropout
bpe-tokenizer dropout "hello world" -m tokenizer.json --p 0.15 --n 10 --seed 42

# Viterbi encoding
bpe-tokenizer viterbi "hello world" -m tokenizer.json

# WordPiece encoding
bpe-tokenizer wordpiece "hello world" -m tokenizer.json

# Analyze tokenizer quality
bpe-tokenizer analyze corpus.txt -m tokenizer.json

# Compare two tokenizers
bpe-tokenizer compare corpus.txt -a tokenizer_a.json -b tokenizer_b.json

# Stats
bpe-tokenizer stats -m tokenizer.json

# Round-trip test
bpe-tokenizer roundtrip "the quick brown fox" -m tokenizer.json
```

---

## Architecture

```
bpe_tokenizer/
├── __init__.py        # Public API — 30+ exports
├── tokenizer.py       # Core: BPE training (incremental), encoding, decoding, serialization
├── encoder.py        # Advanced: Unigram/Viterbi DP, BPE-dropout
├── wordpiece.py      # WordPiece (BERT-style) longest-match encoder
├── vocab.py          # Vocabulary data structures (Token, SpecialToken, Vocab)
├── pretokenize.py    # Pre-tokenizers (GPT-2/GPT-4/Llama-3 regex, byte-level)
├── cache.py          # Thread-safe LRU encode cache
├── normalizer.py     # Text normalization (lowercase, NFC, strip accents, etc.)
├── postprocess.py    # Truncation, attention masks, special-token stripping
├── analyzer.py       # Tokenizer quality analysis & diagnostics
├── comparison.py     # Side-by-side tokenizer comparison tool
├── config.py         # JSON/TOML config file loading and validation
├── progress.py       # Training progress callback infrastructure
├── exceptions.py     # Custom exception hierarchy
├── logging_setup.py  # Centralized logging configuration
└── cli.py            # argparse CLI (12 subcommands)
```

### Module Dependency Graph

```
                    ┌──────────┐
                    │  cli.py  │
                    └────┬─────┘
              ┌──────────┼──────────┐
              ▼          ▼          ▼
         ┌────────┐ ┌────────┐ ┌──────────┐
         │config  │ │progress│ │tokenizer │
         │  .py   │ │  .py   │ │  .py     │
         └────────┘ └────────┘ └────┬─────┘
                                     │
           ┌──────────┬──────────┬───┴───┬──────────┐
           ▼          ▼          ▼       ▼          ▼
      ┌────────┐ ┌────────┐ ┌───────┐ ┌──────┐ ┌────────┐
      │vocab.py│ │pretoken│ │cache  │ │normal│ │encoder │
      │        │ │  .py   │ │  .py  │ │izer  │ │  .py   │
      └────────┘ └────────┘ └───────┘ └──────┘ └────────┘
                                                              ┌───────────┐
                           ┌───────────────────────────────── │wordpiece  │
                           │                                    │  .py     │
                           │                                    └───────────┘
              ┌────────────┼────────────┐
              ▼            ▼            ▼
         ┌────────┐  ┌──────────┐  ┌─────────┐
         │analyze│  │comparison│  │  post   │
         │  .py  │  │   .py    │  │process  │
         └───────┘  └──────────┘  └─────────┘
```

---

## How It Works

### BPE Training (Incremental)

1. **Normalize** the corpus (if a normalizer is configured).
2. **Pre-tokenize** into words/chunks using a regex pattern.
3. **Initialize** the vocabulary with all unique base units.
4. **Count all pairs** across all words (computed once).
5. **Iteratively merge** the most frequent adjacent pair. After each merge:
   - Only update pair counts for words containing the merged pair (**incremental update**).
   - Decrement old pair counts, increment new pair counts.
   - Remove zero-count entries.
6. **Stop** when target vocab size is reached or no pair meets minimum frequency.

**Optimization**: The incremental pair-counting approach avoids recomputing all pair counts from scratch each iteration, reducing complexity from O(M · total_symbols) to O(M · affected_words) where M is the number of merges.

### BPE Encoding

1. **Normalize** → **Pre-tokenize** → **Split** into base units.
2. **Greedily merge** adjacent pairs by lowest merge rank until no merges apply.
3. **Convert** symbols to token ids, **Post-process** (BOS/EOS, truncate, pad, mask).

### Unigram/Viterbi Segmentation

The Unigram model scores segmentations by the sum of log-probabilities of tokens. Viterbi DP finds the globally optimal segmentation in O(n·L) time (n = text length, L = max piece length).

### WordPiece (BERT-style)

Longest-match-first: at each position, find the longest substring in the vocabulary. Optionally uses `##` continuation markers for non-initial subwords. Deterministic and greedy-optimal.

### BPE-Dropout

At each merge step, with probability `p`, the best pair is skipped and the next-best is merged. Produces different segmentations per call, augmenting training data (Provilkov et al. 2020).

---

## Testing

```bash
# Run all 85 tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=bpe_tokenizer --cov-report=term-missing

# Run specific test suite
pytest tests/test_improvement.py -v    # 39 new tests
pytest tests/test_basic.py -v          # 12 core tests
pytest tests/test_enhanced.py -v        # 22 enhanced tests
pytest tests/test_bug_hunt.py -v        # 12 bug-hunt tests
```

### Test Summary

| Suite | Tests | Coverage |
|-------|-------|----------|
| `test_basic.py` | 12 | Core training, encoding, decoding, cache, save/load |
| `test_enhanced.py` | 22 | Normalizer, postprocess, advanced encoding, analyzer |
| `test_bug_hunt.py` | 12 | Bug fixes, edge cases, error handling |
| `test_improvement.py` | 39 | WordPiece, config, comparison, progress, exceptions, CLI |
| **Total** | **85** | All passing ✅ |

---

## Known Issues (Resolved)

1. **Tie-breaking in merge selection was inverted** — `max()` with key `(count, pair)` selected the lexicographically *largest* pair on ties. Fixed by using `min()` with key `(-count, pair)`.

2. **Dead code in `_rebuild_merge_ranks`** — A first loop iterated over all tokens and did nothing. Removed.

3. **`encode_advanced` didn't pad when `pad_id` was None** — When `return_attention_mask=True` and `max_length` was set but `pad_id` wasn't provided, no padding was applied. Fixed to always pad when `max_length` + `return_attention_mask` are set.

4. **`encode_batch` truncation ignored special tokens** — `r[:max_length]` could cut off BOS/EOS tokens. Fixed to use `truncate()` with `keep_specials=True`.

5. **`BPESentencePiece.encode` skipped normalization** — Viterbi encoding bypassed the normalizer. Fixed by applying the normalizer before pre-tokenization.

6. **`Vocab.add_token` silently overwrote duplicate pieces** — Adding a token with an existing piece string would create id collisions. Fixed to raise `ValueError` on duplicates.

---

## Changelog

### v3.0.0 — Comprehensive Improvement
- ✨ **WordPiece encoder** — BERT-style longest-match-first segmentation with `##` continuation markers
- ✨ **Tokenizer comparison tool** — side-by-side comparison of two tokenizers with agreement rate and per-text mismatch details
- ✨ **Config file support** — JSON and TOML config files for reproducible training and encoding setups
- ✨ **Progress callbacks** — `ProgressInfo` dataclass and callback infrastructure for monitoring training
- ✨ **Incremental training optimization** — pair counts updated incrementally instead of recomputed each iteration
- ✨ **Custom exception hierarchy** — `BPETokenizerError` base with `TrainingError`, `EncodingError`, `ConfigError`, etc.
- ✨ **Centralized logging** — `configure_logging()` and `get_logger()` utilities
- ✨ **`train_from_file()`** — train directly from a corpus file path
- ✨ **3 new CLI subcommands** — `train-config`, `wordpiece`, `compare` (12 total)
- ✨ **39 new tests** (85 total, all passing)
- ✨ **GitHub Actions CI** — tests across Python 3.10/3.11/3.12
- ✨ **CONTRIBUTING.md**, **LICENSE**, example config files
- ✨ **Advanced demo script** showcasing all v3.0 features

### v2.0.0 — Enhanced + Bug Hunt
- Unigram/Viterbi segmentation, BPE-dropout
- Text normalization (8 flags)
- Truncation strategies, attention masks
- Tokenizer quality analyzer
- CLI with 9 subcommands
- 6 bugs found and fixed

### v1.0.0 — Initial Release
- Core BPE training and encoding
- Character and byte-level modes
- GPT-2/GPT-4/Llama-3 pre-tokenizers
- Thread-safe LRU cache
- JSON serialization

---

## Roadmap

- [ ] **EM (Expectation-Maximization) training** for the Unigram model
- [ ] **HuggingFace-compatible tokenizer.json** export format
- [ ] **Multi-threaded batch encoding** for large datasets
- [ ] **Sentence-level pre-tokenization** for paragraph-aware splitting
- [ ] **Vocab pruning** — remove low-frequency tokens post-training
- [ ] **Online learning** — continue training an existing tokenizer on new text
- [ ] **Visualization tool** — render tokenization as colored spans
- [ ] **Benchmark suite** — compare compression against HuggingFace tokenizers

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style, and pull request guidelines.

```bash
# Quick start for contributors
git clone https://github.com/jayis1/creative-projects.git
cd creative-projects/bpe-tokenizer
pip install -e ".[dev]"
pytest tests/ -v
```

---

## License

[MIT](LICENSE) — © 2026 creative-projects