"""Tests for Phase 2 enhancements: normalizer, postprocess, analyzer, advanced encoding."""

import pytest
from bpe_tokenizer import (
    BPETokenizer,
    TrainingConfig,
    Normalization,
    Normalizer,
    TruncationStrategy,
    truncate,
    make_attention_mask,
    strip_specials,
    TokenizerAnalyzer,
)


CORPUS = """
The quick brown fox jumps over the lazy dog.
The quick brown fox is very quick indeed.
Lazy dogs sleep while quick foxes jump.
The dog and the fox are friends.
Quick quick quick lazy lazy lazy.
"""


class TestNormalizer:
    def test_lowercase(self):
        norm = Normalizer(Normalization.LOWERCASE)
        assert norm("Hello World") == "hello world"

    def test_nfc(self):
        norm = Normalizer(Normalization.NFC)
        # NFD form of é is e + combining accent; NFC should compose it
        nfd = "e\u0301"
        assert norm(nfd) == "é"

    def test_strip_accents(self):
        norm = Normalizer(Normalization.NFD | Normalization.STRIP_ACCENTS)
        assert norm("héllo wörld") == "hello world"

    def test_strip_whitespace(self):
        norm = Normalizer(Normalization.STRIP_WHITESPACE)
        assert norm("  hello   world  ") == "hello world"

    def test_crlf_to_lf(self):
        norm = Normalizer(Normalization.CRLF_TO_LF)
        assert norm("line1\r\nline2\r") == "line1\nline2\n"

    def test_combined(self):
        norm = Normalizer(Normalization.LOWERCASE | Normalization.STRIP_WHITESPACE)
        assert norm("  Hello  WORLD  ") == "hello world"

    def test_none(self):
        norm = Normalizer(Normalization.NONE)
        assert norm("Hello World") == "Hello World"

    def test_remove_control(self):
        norm = Normalizer(Normalization.REMOVE_CONTROL)
        assert norm("hello\x00world\x01!") == "helloworld!"

    def test_normalizer_in_tokenizer(self):
        # Train with lowercase normalization via config flags.
        tok = BPETokenizer()
        cfg = TrainingConfig(
            vocab_size=80, min_frequency=1,
            normalizer_flags=int(Normalization.LOWERCASE.value),
        )
        tok.train(CORPUS, cfg)
        # The normalizer should lowercase before encoding.
        ids = tok.encode("HELLO")
        decoded = tok.decode(ids)
        assert decoded == "hello"  # lowercased by normalizer


class TestPostprocess:
    def test_truncate_right(self):
        ids = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        result = truncate(ids, 5, TruncationStrategy.RIGHT, keep_specials=False)
        assert result == [1, 2, 3, 4, 5]

    def test_truncate_left(self):
        ids = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        result = truncate(ids, 5, TruncationStrategy.LEFT, keep_specials=False)
        assert result == [6, 7, 8, 9, 10]

    def test_truncate_middle(self):
        ids = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        result = truncate(ids, 4, TruncationStrategy.MIDDLE, keep_specials=False)
        assert len(result) == 4
        assert result[0] == 1
        assert result[-1] == 10

    def test_truncate_keep_specials(self):
        # BOS=1, content=[2,3,4,5,6], EOS=7
        ids = [1, 2, 3, 4, 5, 6, 7]
        specials = {1, 7}
        result = truncate(ids, 4, TruncationStrategy.RIGHT, keep_specials=True, special_ids=specials)
        assert result[0] == 1  # BOS kept
        assert result[-1] == 7  # EOS kept
        assert len(result) == 4

    def test_truncate_noop(self):
        ids = [1, 2, 3]
        assert truncate(ids, 5, TruncationStrategy.RIGHT) == [1, 2, 3]

    def test_attention_mask(self):
        ids = [5, 3, 0, 0]
        mask = make_attention_mask(ids, pad_id=0)
        assert mask == [1, 1, 0, 0]

    def test_strip_specials(self):
        ids = [1, 5, 6, 2, 7, 3]
        specials = {1, 2, 3}
        result = strip_specials(ids, specials)
        assert result == [5, 6, 7]


class TestAdvancedEncoding:
    def test_encode_advanced_basic(self):
        tok = BPETokenizer()
        tok.train(CORPUS, TrainingConfig(vocab_size=80, min_frequency=1))
        result = tok.encode_advanced("quick fox")
        assert "input_ids" in result
        assert len(result["input_ids"]) > 0

    def test_encode_advanced_max_length(self):
        tok = BPETokenizer()
        tok.train(CORPUS, TrainingConfig(vocab_size=80, min_frequency=1))
        result = tok.encode_advanced("quick brown fox", max_length=2)
        assert len(result["input_ids"]) == 2

    def test_encode_advanced_attention_mask(self):
        tok = BPETokenizer()
        tok.train(CORPUS, TrainingConfig(vocab_size=80, min_frequency=1))
        result = tok.encode_advanced("fox", max_length=5, return_attention_mask=True,
                                     pad_id=0)
        assert "attention_mask" in result
        assert len(result["attention_mask"]) == 5
        # Padded positions should have mask=0
        assert 0 in result["attention_mask"]


class TestAnalyzer:
    def test_analyze(self):
        tok = BPETokenizer()
        tok.train(CORPUS, TrainingConfig(vocab_size=80, min_frequency=1))
        analyzer = TokenizerAnalyzer(tok)
        result = analyzer.analyze(["quick brown fox", "lazy dog"])
        assert result.n_texts == 2
        assert result.n_tokens > 0
        assert result.chars_per_token > 0
        assert result.vocab_size > 0

    def test_summary(self):
        tok = BPETokenizer()
        tok.train(CORPUS, TrainingConfig(vocab_size=80, min_frequency=1))
        analyzer = TokenizerAnalyzer(tok)
        summary = analyzer.summary(["quick brown fox"])
        assert "Compression" in summary
        assert "Vocabulary" in summary
        assert "Fertility" in summary


class TestSerializationWithNormalizer:
    def test_save_load_with_normalizer(self, tmp_path):
        tok = BPETokenizer()
        cfg = TrainingConfig(vocab_size=80, min_frequency=1,
                             normalizer_flags=int(Normalization.LOWERCASE.value))
        tok.train(CORPUS, cfg)
        path = str(tmp_path / "tok_norm.json")
        tok.save(path)
        tok2 = BPETokenizer.load(path)
        assert tok2.normalizer is not None
        # Encoding should produce the same result (lowercased).
        assert tok.encode("HELLO") == tok2.encode("HELLO")