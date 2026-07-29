# BPE Tokenizer

A from-scratch **Byte Pair Encoding (BPE)** tokenizer for NLP, implementing the core algorithm used by GPT-2, GPT-4, Llama-3, and other modern language models — plus advanced features like **Unigram/Viterbi segmentation** (SentencePiece-style), **BPE-dropout** for data augmentation, **text normalization**, **truncation strategies**, and **tokenizer quality analysis**.

## Features

### Core BPE
- **Greedy merge training**: learns the most frequent byte/character pairs iteratively, with deterministic tie-breaking
- **Greedy-rank encoding**: applies learned merges by priority (lowest rank = highest priority)
- **Character-level mode**: operates on Unicode codepoints
- **Byte-level mode**: GPT-2-style byte-to-unicode mapping (handles any byte value, including invalid UTF-8)
- **Pre-tokenization**: GPT-2 / GPT-4 / Llama-3 regex patterns, whitespace split, or no-split (with stdlib `re` fallback when `regex` module is unavailable)
- **Special tokens**: PAD, BOS, EOS, UNK (configurable)
- **Batch encoding**: with optional padding and max-length truncation
- **LRU encode cache**: thread-safe, configurable capacity
- **JSON serialization**: save/load trained tokenizers (including normalizer config)

### Advanced Encoders
- **Unigram model** (`BPESentencePiece`): Viterbi-style DP segmentation that maximizes token log-probabilities (optimal segmentation, not greedy)
- **BPE-dropout** (`bpe_dropout`): stochastic merge dropping for data augmentation and robustness training (Provilkov et al. 2020)
- **Viterbi segmentation** (`viterbi_segment`): standalone DP segmenter using Unigram scores

### Text Normalization
- **Configurable normalizer** with 8 flags: `LOWERCASE`, `NFC`, `NFD`, `NFKC`, `NFKD`, `STRIP_ACCENTS`, `STRIP_WHITESPACE`, `REMOVE_CONTROL`, `CRLF_TO_LF`, `REPLACE_ZWSP`
- Applied before pre-tokenization during both training and encoding
- Serialized with the tokenizer for consistent encoding after load

### Post-Processing
- **Truncation strategies**: right, left, middle (with special-token preservation)
- **Attention mask generation**: binary mask for padding tokens
- **Special-token stripping**: remove specials from id sequences

### Analysis & Diagnostics
- **TokenizerAnalyzer**: evaluates tokenizer quality on a corpus
- **Metrics**: compression ratio (chars/token, bytes/token), token-length distribution (mean/median/min/max), subword fertility (tokens/word), coverage, UNK rate
- **Top-N token frequency**: most common tokens by count
- **Piece-length histogram**: distribution of token lengths
- **Human-readable summary**: formatted report via `analyzer.summary()`

### CLI
9 subcommands: `train`, `encode`, `decode`, `batch`, `dropout`, `viterbi`, `stats`, `roundtrip`, `analyze`

## How It Works

### BPE Training

1. **Normalize** the corpus (if a normalizer is configured).
2. **Pre-tokenize** into words/chunks using a regex pattern (e.g., GPT-4's pattern that splits on word boundaries, numbers, and punctuation).
3. **Initialize** the vocabulary with all unique base units (characters or bytes).
4. **Iteratively merge** the most frequent adjacent pair across all words. Each merge creates a new token with an incrementing rank.
5. **Stop** when the target vocab size is reached or no pair meets the minimum frequency threshold.

### BPE Encoding

1. **Normalize** the input text (if configured).
2. **Pre-tokenize** the text.
3. **Split** each chunk into base units (characters or bytes).
4. **Greedily merge** adjacent pairs by lowest merge rank (highest priority) until no more merges apply.
5. **Convert** the resulting symbols to token ids.
6. **Post-process**: add BOS/EOS, truncate, pad, generate attention mask.

### Unigram/Viterbi Segmentation

Instead of greedy merge-rank encoding, the Unigram model scores each possible segmentation by the sum of log-probabilities of its tokens. The Viterbi algorithm finds the globally optimal segmentation via dynamic programming in O(n·L) time, where n is the text length and L is the maximum piece length.

### BPE-Dropout

At each merge step, with probability `p`, the best pair is skipped and the next-best pair is merged instead. This produces different segmentations on different calls, augmenting training data and improving model robustness to tokenization noise.

## Installation

```bash
cd bpe-tokenizer
pip install -e .
# Optional: better Unicode regex support
pip install regex
```

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
```

### Advanced Encoders

```python
from bpe_tokenizer.encoder import BPESentencePiece, bpe_dropout
import random

# Unigram/Viterbi encoding (optimal segmentation)
sp = BPESentencePiece(tok)
ids = sp.encode("hello world")

# BPE-dropout (stochastic, for data augmentation)
rng = random.Random(42)
for _ in range(5):
    ids = bpe_dropout(tok, "hello world", dropout=0.1, rng=rng)
    print(tok.id_to_pieces(ids))
```

### Tokenizer Analysis

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

### Text Normalization

```python
from bpe_tokenizer import Normalization, Normalizer

# Combine multiple normalizations
norm = Normalizer(Normalization.LOWERCASE | Normalization.STRIP_ACCENTS | Normalization.STRIP_WHITESPACE)
print(norm("  Héllo  Wörld  "))  # → "hello world"
```

### CLI

```bash
# Train (with lowercase + strip accents)
bpe-tokenizer train corpus.txt -o tokenizer.json --vocab-size 2000 --byte-mode --lowercase --strip-accents

# Encode
bpe-tokenizer encode "hello world" -m tokenizer.json --bos --eos --pieces

# Decode
bpe-tokenizer decode 1 42 17 2 -m tokenizer.json

# Batch encode
bpe-tokenizer batch texts.txt -m tokenizer.json --pad --output encoded.json

# BPE-dropout
bpe-tokenizer dropout "hello world" -m tokenizer.json --p 0.15 --n 10 --seed 42

# Viterbi encoding
bpe-tokenizer viterbi "hello world" -m tokenizer.json

# Analyze tokenizer quality
bpe-tokenizer analyze corpus.txt -m tokenizer.json

# Stats
bpe-tokenizer stats -m tokenizer.json

# Round-trip test
bpe-tokenizer roundtrip "the quick brown fox" -m tokenizer.json
```

## Project Structure

```
bpe-tokenizer/
├── bpe_tokenizer/
│   ├── __init__.py        # Public API
│   ├── tokenizer.py       # Core BPE: training, encoding, decoding, serialization
│   ├── encoder.py         # Advanced: Unigram/Viterbi, BPE-dropout
│   ├── vocab.py           # Vocabulary data structures (Token, SpecialToken, Vocab)
│   ├── pretokenize.py     # Pre-tokenizers (GPT-2/GPT-4/Llama-3 regex, byte-level)
│   ├── cache.py           # Thread-safe LRU encode cache
│   ├── normalizer.py      # Text normalization (lowercase, NFC, strip accents, etc.)
│   ├── postprocess.py     # Truncation, attention masks, special-token stripping
│   ├── analyzer.py        # Tokenizer quality analysis & diagnostics
│   └── cli.py             # argparse CLI (9 subcommands)
├── tests/
│   ├── test_basic.py      # 12 core tests
│   └── test_enhanced.py   # 22 tests for enhancements
├── examples/
│   ├── demo.py            # Python API demo
│   └── sample.txt         # Sample corpus
├── pyproject.toml
└── README.md
```

## Testing

```bash
pytest tests/ -v  # 34 tests
```

## License

MIT