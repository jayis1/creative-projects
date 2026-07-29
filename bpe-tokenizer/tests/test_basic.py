"""Basic smoke tests for the BPE tokenizer."""

import pytest
from bpe_tokenizer import BPETokenizer, TrainingConfig


CORPUS = """
The quick brown fox jumps over the lazy dog.
The quick brown fox is very quick indeed.
Lazy dogs sleep while quick foxes jump.
The dog and the fox are friends.
Quick quick quick lazy lazy lazy.
"""


def test_train_and_encode():
    tok = BPETokenizer()
    cfg = TrainingConfig(vocab_size=80, min_frequency=1, verbose=False)
    tok.train(CORPUS, cfg)
    ids = tok.encode("quick fox")
    assert len(ids) > 0
    assert all(isinstance(i, int) for i in ids)


def test_roundtrip_ascii():
    tok = BPETokenizer()
    cfg = TrainingConfig(vocab_size=80, min_frequency=1)
    tok.train(CORPUS, cfg)
    text = "quick brown fox"
    ids = tok.encode(text)
    decoded = tok.decode(ids)
    assert decoded == text, f"roundtrip failed: {decoded!r} != {text!r}"


def test_vocab_size():
    tok = BPETokenizer()
    cfg = TrainingConfig(vocab_size=50, min_frequency=1)
    tok.train(CORPUS, cfg)
    assert tok.vocab_size() <= 50 + 4  # specials may push slightly over


def test_special_tokens():
    tok = BPETokenizer()
    cfg = TrainingConfig(vocab_size=80, min_frequency=1)
    tok.train(CORPUS, cfg)
    ids = tok.encode("fox", add_bos=True, add_eos=True)
    # BOS should be id 0 or 1 (first special)
    assert ids[0] < 4  # BOS is a special token
    assert ids[-1] < 4  # EOS is a special token


def test_batch_encoding():
    tok = BPETokenizer()
    cfg = TrainingConfig(vocab_size=80, min_frequency=1)
    tok.train(CORPUS, cfg)
    texts = ["quick fox", "lazy dog", "the"]
    results = tok.encode_batch(texts, padding=True)
    assert all(len(r) == len(results[0]) for r in results)


def test_byte_mode():
    tok = BPETokenizer()
    cfg = TrainingConfig(vocab_size=120, byte_mode=True, min_frequency=1)
    tok.train(CORPUS, cfg)
    ids = tok.encode("fox")
    assert len(ids) > 0
    decoded = tok.decode(ids)
    assert decoded == "fox"


def test_save_load(tmp_path):
    tok = BPETokenizer()
    cfg = TrainingConfig(vocab_size=80, min_frequency=1)
    tok.train(CORPUS, cfg)
    path = str(tmp_path / "tok.json")
    tok.save(path)
    tok2 = BPETokenizer.load(path)
    text = "quick fox"
    assert tok.encode(text) == tok2.encode(text)


def test_empty_input():
    tok = BPETokenizer()
    cfg = TrainingConfig(vocab_size=80, min_frequency=1)
    tok.train(CORPUS, cfg)
    assert tok.encode("") == []
    ids_empty = tok.encode("", add_bos=True, add_eos=True)
    # BOS and EOS ids depend on the specials ordering (PAD=0, BOS=1, EOS=2, UNK=3)
    assert len(ids_empty) == 2
    assert ids_empty[0] == tok.vocab.specials["<bos>"].id
    assert ids_empty[1] == tok.vocab.specials["<eos>"].id


def test_cache():
    tok = BPETokenizer()
    cfg = TrainingConfig(vocab_size=80, min_frequency=1)
    tok.train(CORPUS, cfg)
    text = "quick brown fox"
    ids1 = tok.encode(text)
    ids2 = tok.encode(text)
    assert ids1 == ids2
    stats = tok.stats()
    assert stats.cache_hits >= 1


def test_dropout():
    from bpe_tokenizer.encoder import bpe_dropout
    import random
    tok = BPETokenizer()
    cfg = TrainingConfig(vocab_size=80, min_frequency=1)
    tok.train(CORPUS, cfg)
    rng = random.Random(42)
    ids = bpe_dropout(tok, "quick brown fox", dropout=0.3, rng=rng)
    assert len(ids) > 0


def test_viterbi():
    from bpe_tokenizer.encoder import BPESentencePiece
    tok = BPETokenizer()
    cfg = TrainingConfig(vocab_size=80, min_frequency=1)
    tok.train(CORPUS, cfg)
    sp = BPESentencePiece(tok)
    ids = sp.encode("quick fox")
    assert len(ids) > 0
    assert tok.decode(ids) == "quick fox"


def test_unicode():
    tok = BPETokenizer()
    cfg = TrainingConfig(vocab_size=150, min_frequency=1)
    tok.train("héllo wörld ☃ test naïve", cfg)
    ids = tok.encode("héllo")
    assert len(ids) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])