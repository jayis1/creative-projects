"""Advanced demo: config files, WordPiece, comparison, progress callbacks.

This script demonstrates the v3.0 features added in the comprehensive
improvement pass.
"""

import json
import tempfile
from pathlib import Path

from bpe_tokenizer import (
    BPETokenizer,
    TrainingConfig,
    WordPieceEncoder,
    TokenizerComparison,
    TokenizerConfig,
    load_config,
    ProgressInfo,
    Normalization,
)

CORPUS = """
The quick brown fox jumps over the lazy dog.
The quick brown fox is very quick indeed.
Lazy dogs sleep while quick foxes jump.
The dog and the fox are friends.
Quick quick quick lazy lazy lazy.
A quick brown fox jumped over a lazy dog today.
The fox and the dog became quick friends.
Lazy lazy lazy quick quick quick the end.
"""


def section(title: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")


def demo_config_file():
    """Demo: Load a config file and train."""
    section("Config File Support")
    config_data = {
        "training": {
            "vocab_size": 150,
            "pretokenizer": "gpt4",
            "min_frequency": 1,
            "normalizer": ["lowercase", "nfc"],
        },
        "encoding": {
            "add_bos": True,
            "add_eos": True,
            "max_length": 10,
        },
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(config_data, f, indent=2)
        config_path = f.name

    config = load_config(config_path)
    print(f"  Config loaded from: {config_path}")
    print(f"  Training config: vocab_size={config.training['vocab_size']}")
    print(f"  Normalizer: {config.training['normalizer']}")

    cfg = config.to_training_config()
    tok = BPETokenizer()
    tok.train(CORPUS, cfg)
    print(f"  Trained: vocab_size={tok.vocab_size()}")

    enc_kwargs = config.encoding_kwargs()
    result = tok.encode_advanced("the quick fox", **enc_kwargs)
    print(f"  Encoded with config: {result['input_ids']}")
    print(f"  Length: {len(result['input_ids'])} (max={enc_kwargs['max_length']})")
    Path(config_path).unlink()


def demo_wordpiece():
    """Demo: WordPiece (BERT-style) encoding."""
    section("WordPiece Encoder")
    tok = BPETokenizer()
    tok.train(CORPUS, TrainingConfig(vocab_size=120, min_frequency=1))

    wp = WordPieceEncoder(tok, use_continuation_marker=False)
    text = "the quick brown fox"
    pieces = wp.tokenize(text)
    ids = wp.encode(text)
    print(f"  Text:    {text!r}")
    print(f"  Pieces:  {pieces}")
    print(f"  Ids:     {ids}")
    print(f"  Decoded: {tok.decode(ids)!r}")

    # Compare BPE vs WordPiece
    bpe_ids = tok.encode(text)
    print(f"\n  BPE ids:       {bpe_ids} (len={len(bpe_ids)})")
    print(f"  WordPiece ids: {ids} (len={len(ids)})")


def demo_comparison():
    """Demo: Compare two tokenizers."""
    section("Tokenizer Comparison")
    tok_small = BPETokenizer()
    tok_small.train(CORPUS, TrainingConfig(vocab_size=80, min_frequency=1))
    tok_large = BPETokenizer()
    tok_large.train(CORPUS, TrainingConfig(vocab_size=200, min_frequency=1))

    texts = ["the quick brown fox", "lazy dog jumps", "quick fox"]
    comp = TokenizerComparison(tok_small, tok_large)
    summary = comp.summary(texts)
    print(summary)


def demo_progress():
    """Demo: Progress callbacks during training."""
    section("Progress Callbacks")
    tok = BPETokenizer()

    merge_log = []

    def callback(info: ProgressInfo) -> None:
        merge_log.append((info.iteration, info.merged_token, info.merge_count))

    tok.train(
        CORPUS,
        TrainingConfig(vocab_size=60, min_frequency=1),
        progress_callback=callback,
    )
    print(f"  {len(merge_log)} merges performed:")
    for i, (iteration, token, count) in enumerate(merge_log[:10]):
        print(f"    [{iteration:3d}] {token!r:15s} (count={count})")
    if len(merge_log) > 10:
        print(f"    ... ({len(merge_log) - 10} more)")


def demo_all_encoders():
    """Demo: All three encoding algorithms side by side."""
    section("Encoding Algorithm Comparison")
    from bpe_tokenizer.encoder import BPESentencePiece, bpe_dropout
    import random

    tok = BPETokenizer()
    tok.train(CORPUS, TrainingConfig(vocab_size=100, min_frequency=1))

    text = "the quick brown fox"
    print(f"  Text: {text!r}")

    # Standard BPE
    bpe_ids = tok.encode(text)
    print(f"\n  BPE (greedy-rank):")
    print(f"    ids:    {bpe_ids}")
    print(f"    pieces: {tok.id_to_pieces(bpe_ids)}")
    print(f"    n_tokens: {len(bpe_ids)}")

    # Viterbi/Unigram
    sp = BPESentencePiece(tok)
    viterbi_ids = sp.encode(text)
    print(f"\n  Viterbi (Unigram DP):")
    print(f"    ids:    {viterbi_ids}")
    print(f"    pieces: {tok.id_to_pieces(viterbi_ids)}")
    print(f"    n_tokens: {len(viterbi_ids)}")

    # WordPiece
    wp = WordPieceEncoder(tok, use_continuation_marker=False)
    wp_ids = wp.encode(text)
    print(f"\n  WordPiece (longest-match):")
    print(f"    ids:    {wp_ids}")
    print(f"    pieces: {wp.tokenize(text)}")
    print(f"    n_tokens: {len(wp_ids)}")

    # BPE-dropout
    rng = random.Random(42)
    print(f"\n  BPE-dropout (p=0.3, 3 samples):")
    for i in range(3):
        dropout_ids = bpe_dropout(tok, text, dropout=0.3, rng=rng)
        print(f"    sample {i}: {dropout_ids} (n={len(dropout_ids)})")


def main():
    print("=" * 60)
    print("  BPE Tokenizer v3.0 — Advanced Features Demo")
    print("=" * 60)

    demo_config_file()
    demo_wordpiece()
    demo_comparison()
    demo_progress()
    demo_all_encoders()

    print(f"\n{'=' * 60}")
    print("  Demo complete!")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()