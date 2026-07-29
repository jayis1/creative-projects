# BPE Tokenizer

A from-scratch **Byte Pair Encoding (BPE)** tokenizer for NLP, implementing the core algorithm used by GPT-2, GPT-4, Llama-3, and other modern language models — plus advanced features like **Unigram/Viterbi segmentation** (SentencePiece-style) and **BPE-dropout** for data augmentation.

## Features

### Core BPE
- **Greedy merge training**: learns the most frequent byte/character pairs iteratively, with deterministic tie-breaking
- **Greedy-rank encoding**: applies learned merges by priority (lowest rank = highest priority)
- **Character-level mode**: operates on Unicode codepoints
- **Byte-level mode**: GPT-2-style byte-to-unicode mapping (handles any byte value, including invalid UTF-8)
- **Pre-tokenization**: GPT-2 / GPT-4 / Llama-3 regex patterns, whitespace split, or no-split
- **Special tokens**: PAD, BOS, EOS, UNK (configurable)
- **Batch encoding**: with optional padding and max-length truncation
- **LRU encode cache**: thread-safe, configurable capacity
- **JSON serialization**: save/load trained tokenizers

### Advanced Encoders
- **Unigram model** (`BPESentencePiece`): Viterbi-style DP segmentation that maximizes token log-probabilities (optimal segmentation, not greedy)
- **BPE-dropout** (`bpe_dropout`): stochastic merge dropping for data augmentation and robustness training (Provilkov et al. 2020)
- **Viterbi segmentation** (`viterbi_segment`): standalone DP segmenter using Unigram scores

### CLI
8 subcommands: `train`, `encode`, `decode`, `batch`, `dropout`, `viterbi`, `stats`, `roundtrip`

## How It Works

### BPE Training

1. **Pre-tokenize** the corpus into words/chunks using a regex pattern (e.g., GPT-4's pattern that splits on word boundaries, numbers, and punctuation).
2. **Initialize** the vocabulary with all unique base units (characters or bytes).
3. **Iteratively merge** the most frequent adjacent pair across all words. Each merge creates a new token with an incrementing rank.
4. **Stop** when the target vocab size is reached or no pair meets the minimum frequency threshold.

### BPE Encoding

1. **Pre-tokenize** the input text.
2. **Split** each chunk into base units (characters or bytes).
3. **Greedily merge** adjacent pairs by lowest merge rank (highest priority) until no more merges apply.
4. **Convert** the resulting symbols to token ids.

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
from bpe_tokenizer import BPETokenizer, TrainingConfig

# Train
tok = BPETokenizer()
cfg = TrainingConfig(vocab_size=1000, byte_mode=False, pretokenizer="gpt4")
tok.train("Your training corpus text here...", cfg)

# Encode
ids = tok.encode("hello world", add_bos=True, add_eos=True)
# → [1, 42, 17, 2]

# Decode
text = tok.decode(ids)
# → "hello world"

# Batch with padding
batch = tok.encode_batch(["hello", "world", "foo"], padding=True)
# → [[42, 17, 0], [55, 0, 0], [33, 0, 0]]

# Save / Load
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

### CLI

```bash
# Train
bpe-tokenizer train corpus.txt -o tokenizer.json --vocab-size 2000 --byte-mode

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
│   └── cli.py             # argparse CLI (8 subcommands)
├── tests/
│   └── test_basic.py      # 12 tests
├── examples/
│   ├── demo.py            # Python API demo
│   └── sample.txt         # Sample corpus
├── pyproject.toml
└── README.md
```

## Testing

```bash
pytest tests/ -v
```

## License

MIT