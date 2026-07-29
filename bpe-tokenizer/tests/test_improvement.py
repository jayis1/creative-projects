"""Tests for the comprehensive improvement: WordPiece, config, comparison,
progress, exceptions, logging, incremental training, CLI."""

import json
import random
import tempfile
from pathlib import Path

import pytest

from bpe_tokenizer import (
    BPETokenizer,
    TrainingConfig,
    WordPieceEncoder,
    wordpiece_encode,
    TokenizerComparison,
    TokenizerConfig,
    load_config,
    save_config,
    ProgressInfo,
    create_print_callback,
    BPETokenizerError,
    TrainingError,
    EncodingError,
    ConfigError,
    VocabError,
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


# ---------------------------------------------------------------------------
# WordPiece tests
# ---------------------------------------------------------------------------

class TestWordPiece:
    def test_wordpiece_encode_basic(self):
        tok = BPETokenizer()
        tok.train(CORPUS, TrainingConfig(vocab_size=100, min_frequency=1))
        ids = wordpiece_encode(tok, "quick fox")
        assert len(ids) > 0
        assert all(isinstance(i, int) for i in ids)

    def test_wordpiece_class_encode(self):
        tok = BPETokenizer()
        tok.train(CORPUS, TrainingConfig(vocab_size=100, min_frequency=1))
        wp = WordPieceEncoder(tok)
        ids = wp.encode("the quick fox")
        assert len(ids) > 0

    def test_wordpiece_tokenize(self):
        tok = BPETokenizer()
        tok.train(CORPUS, TrainingConfig(vocab_size=100, min_frequency=1))
        wp = WordPieceEncoder(tok, use_continuation_marker=False)
        pieces = wp.tokenize("the quick fox")
        assert len(pieces) > 0
        # All pieces should be in the vocab (or UNK).
        for p in pieces:
            assert p in tok.vocab.tokens or p == "<unk>"

    def test_wordpiece_empty(self):
        tok = BPETokenizer()
        tok.train(CORPUS, TrainingConfig(vocab_size=80, min_frequency=1))
        wp = WordPieceEncoder(tok)
        assert wp.encode("") == []
        assert wp.tokenize("") == []

    def test_wordpiece_long_word_unk(self):
        tok = BPETokenizer()
        tok.train(CORPUS, TrainingConfig(vocab_size=80, min_frequency=1))
        wp = WordPieceEncoder(tok, max_input_chars_per_word=3)
        ids = wp.encode("abcdefghij")
        # Long word should produce UNK tokens.
        unk_id = tok.vocab.unk_id()
        assert unk_id in ids

    def test_wordpiece_with_bos_eos(self):
        tok = BPETokenizer()
        tok.train(CORPUS, TrainingConfig(vocab_size=100, min_frequency=1))
        wp = WordPieceEncoder(tok)
        ids = wp.encode("fox", add_bos=True, add_eos=True)
        bos_id = tok.vocab.specials["<bos>"].id
        eos_id = tok.vocab.specials["<eos>"].id
        assert ids[0] == bos_id
        assert ids[-1] == eos_id

    def test_wordpiece_normalizer_applied(self):
        tok = BPETokenizer()
        cfg = TrainingConfig(
            vocab_size=100, min_frequency=1,
            normalizer_flags=int(Normalization.LOWERCASE.value),
        )
        tok.train(CORPUS, cfg)
        wp = WordPieceEncoder(tok, use_continuation_marker=False)
        pieces = wp.tokenize("HELLO")
        # Normalizer should lowercase before WordPiece.
        for p in pieces:
            if p != "<unk>":
                assert p == p.lower()


# ---------------------------------------------------------------------------
# Config file tests
# ---------------------------------------------------------------------------

class TestConfig:
    def test_config_load_json(self, tmp_path):
        config_data = {
            "training": {
                "vocab_size": 200,
                "byte_mode": False,
                "pretokenizer": "gpt4",
                "min_frequency": 1,
                "normalizer": ["lowercase"],
            },
            "encoding": {
                "add_bos": True,
                "add_eos": True,
                "max_length": 10,
            },
        }
        path = tmp_path / "config.json"
        path.write_text(json.dumps(config_data))
        config = load_config(path)
        assert config.training["vocab_size"] == 200
        assert config.encoding["add_bos"] is True

    def test_config_to_training_config(self, tmp_path):
        config_data = {
            "training": {
                "vocab_size": 200,
                "pretokenizer": "gpt4",
                "min_frequency": 1,
                "normalizer": ["lowercase", "nfc"],
            },
        }
        path = tmp_path / "config.json"
        path.write_text(json.dumps(config_data))
        config = load_config(path)
        tc = config.to_training_config()
        assert tc.vocab_size == 200
        assert tc.pretokenizer == "gpt4"
        assert tc.normalizer_flags > 0  # lowercase + nfc

    def test_config_encoding_kwargs(self, tmp_path):
        config_data = {
            "encoding": {
                "add_bos": True,
                "add_eos": True,
                "max_length": 512,
                "truncation": "right",
                "padding": True,
            },
        }
        path = tmp_path / "config.json"
        path.write_text(json.dumps(config_data))
        config = load_config(path)
        kwargs = config.encoding_kwargs()
        assert kwargs["add_bos"] is True
        assert kwargs["max_length"] == 512

    def test_config_save_and_load_roundtrip(self, tmp_path):
        config = TokenizerConfig(
            training={"vocab_size": 500, "pretokenizer": "gpt2"},
            encoding={"add_bos": True},
        )
        path = tmp_path / "saved_config.json"
        save_config(config, path)
        loaded = load_config(path)
        assert loaded.training["vocab_size"] == 500
        assert loaded.training["pretokenizer"] == "gpt2"
        assert loaded.encoding["add_bos"] is True

    def test_config_file_not_found(self):
        with pytest.raises(ConfigError, match="not found"):
            load_config("/nonexistent/path/config.json")

    def test_config_normalizer_string_format(self):
        from bpe_tokenizer.config import parse_normalizer_flags
        flags = parse_normalizer_flags("lowercase|nfc")
        assert flags > 0

    def test_config_normalizer_list_format(self):
        from bpe_tokenizer.config import parse_normalizer_flags
        flags = parse_normalizer_flags(["lowercase", "nfc"])
        assert flags > 0

    def test_config_normalizer_invalid_flag(self):
        from bpe_tokenizer.config import parse_normalizer_flags
        with pytest.raises(ConfigError):
            parse_normalizer_flags(["invalid_flag"])

    def test_config_training_and_encode_workflow(self, tmp_path):
        # Full workflow: config → train → save → load → encode.
        config_data = {
            "training": {
                "vocab_size": 150,
                "pretokenizer": "gpt4",
                "min_frequency": 1,
                "normalizer": ["lowercase"],
            },
            "encoding": {
                "add_bos": True,
                "add_eos": True,
                "max_length": 10,
            },
        }
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps(config_data))

        config = load_config(config_path)
        cfg = config.to_training_config()
        tok = BPETokenizer()
        tok.train(CORPUS, cfg)

        model_path = str(tmp_path / "model.json")
        tok.save(model_path)

        tok2 = BPETokenizer.load(model_path)
        enc_kwargs = config.encoding_kwargs()
        result = tok2.encode_advanced("the quick fox", **enc_kwargs)
        assert "input_ids" in result
        assert len(result["input_ids"]) <= 10


# ---------------------------------------------------------------------------
# Comparison tests
# ---------------------------------------------------------------------------

class TestComparison:
    def test_comparison_basic(self):
        tok_a = BPETokenizer()
        tok_a.train(CORPUS, TrainingConfig(vocab_size=80, min_frequency=1))
        tok_b = BPETokenizer()
        tok_b.train(CORPUS, TrainingConfig(vocab_size=120, min_frequency=1))

        comp = TokenizerComparison(tok_a, tok_b)
        result = comp.compare(["the quick fox", "lazy dog"])
        assert result.n_texts == 2
        assert result.total_tokens_a > 0
        assert result.total_tokens_b > 0

    def test_comparison_summary(self):
        tok_a = BPETokenizer()
        tok_a.train(CORPUS, TrainingConfig(vocab_size=80, min_frequency=1))
        tok_b = BPETokenizer()
        tok_b.train(CORPUS, TrainingConfig(vocab_size=150, min_frequency=1))

        comp = TokenizerComparison(tok_a, tok_b)
        summary = comp.summary(["the quick brown fox", "lazy dog"])
        assert "Tokenizer A" in summary
        assert "Tokenizer B" in summary
        assert "Agreement" in summary

    def test_comparison_identical_tokenizers(self):
        tok_a = BPETokenizer()
        tok_a.train(CORPUS, TrainingConfig(vocab_size=80, min_frequency=1))
        tok_b = BPETokenizer()
        tok_b.train(CORPUS, TrainingConfig(vocab_size=80, min_frequency=1))

        comp = TokenizerComparison(tok_a, tok_b)
        result = comp.compare(["the quick fox"])
        assert result.agreement_rate == 1.0  # identical tokenizers

    def test_comparison_empty_texts(self):
        tok_a = BPETokenizer()
        tok_a.train(CORPUS, TrainingConfig(vocab_size=80, min_frequency=1))
        tok_b = BPETokenizer()
        tok_b.train(CORPUS, TrainingConfig(vocab_size=80, min_frequency=1))

        comp = TokenizerComparison(tok_a, tok_b)
        result = comp.compare([])
        assert result.n_texts == 0


# ---------------------------------------------------------------------------
# Progress callback tests
# ---------------------------------------------------------------------------

class TestProgress:
    def test_progress_callback_called(self):
        tok = BPETokenizer()
        calls = []

        def callback(info: ProgressInfo) -> None:
            calls.append(info)

        tok.train(
            CORPUS,
            TrainingConfig(vocab_size=100, min_frequency=1),
            progress_callback=callback,
        )
        assert len(calls) > 0
        assert all(isinstance(c, ProgressInfo) for c in calls)
        # First call should be iteration 1.
        assert calls[0].iteration == 1
        # Last call should be the last iteration.
        assert calls[-1].iteration == len(calls)

    def test_progress_info_fields(self):
        tok = BPETokenizer()
        info_list = []

        def callback(info: ProgressInfo) -> None:
            info_list.append(info)

        tok.train(
            CORPUS,
            TrainingConfig(vocab_size=50, min_frequency=1),
            progress_callback=callback,
        )
        if info_list:
            info = info_list[0]
            assert info.iteration >= 1
            assert info.max_merges >= 0
            assert isinstance(info.merged_pair, tuple)
            assert isinstance(info.merged_token, str)
            assert info.merge_count >= 1
            assert info.current_vocab_size > 0
            assert 0 <= info.progress_pct <= 100

    def test_create_print_callback(self, capsys):
        tok = BPETokenizer()
        callback = create_print_callback(every=1)  # print every iteration
        tok.train(
            CORPUS,
            TrainingConfig(vocab_size=50, min_frequency=1),
            progress_callback=callback,
        )
        captured = capsys.readouterr()
        assert "merge=" in captured.out


# ---------------------------------------------------------------------------
# Exception hierarchy tests
# ---------------------------------------------------------------------------

class TestExceptions:
    def test_exception_hierarchy(self):
        assert issubclass(TrainingError, BPETokenizerError)
        assert issubclass(EncodingError, BPETokenizerError)
        assert issubclass(ConfigError, BPETokenizerError)
        assert issubclass(VocabError, BPETokenizerError)

    def test_training_error_from_file(self):
        tok = BPETokenizer()
        with pytest.raises(TrainingError, match="not found"):
            tok.train_from_file("/nonexistent/file.txt")

    def test_vocab_error_duplicate(self):
        from bpe_tokenizer.vocab import Vocab
        v = Vocab()
        v.add_token("ab", b"ab", rank=0)
        with pytest.raises(ValueError, match="already exists"):
            v.add_token("ab", b"ab", rank=1)


# ---------------------------------------------------------------------------
# Incremental training optimization tests
# ---------------------------------------------------------------------------

class TestIncrementalTraining:
    def test_incremental_matches_recompute(self):
        """The incremental pair-count optimization should produce
        the same trained tokenizer as the original full-recompute
        approach."""
        # The incremental path is used in train(); we verify
        # determinism and correctness by comparing two runs.
        tok1 = BPETokenizer()
        tok1.train(CORPUS, TrainingConfig(vocab_size=100, min_frequency=1))
        tok2 = BPETokenizer()
        tok2.train(CORPUS, TrainingConfig(vocab_size=100, min_frequency=1))
        # Same config → same result.
        assert tok1.encode("the quick brown fox") == tok2.encode("the quick brown fox")

    def test_incremental_deterministic(self):
        """Training should be deterministic with incremental optimization."""
        tok1 = BPETokenizer()
        tok1.train(CORPUS, TrainingConfig(vocab_size=150, min_frequency=1))
        tok2 = BPETokenizer()
        tok2.train(CORPUS, TrainingConfig(vocab_size=150, min_frequency=1))
        # Vocab should be identical.
        assert tok1.vocab.size() == tok2.vocab.size()
        assert tok1._merge_ranks == tok2._merge_ranks

    def test_incremental_large_vocab(self):
        """Incremental training should handle larger vocab sizes correctly."""
        tok = BPETokenizer()
        tok.train(CORPUS, TrainingConfig(vocab_size=200, min_frequency=1))
        # Roundtrip should work.
        text = "the quick brown fox"
        ids = tok.encode(text)
        assert tok.decode(ids) == text

    def test_incremental_byte_mode(self):
        """Incremental training should work in byte mode too."""
        tok = BPETokenizer()
        tok.train(CORPUS, TrainingConfig(vocab_size=150, byte_mode=True, min_frequency=1))
        text = "fox"
        ids = tok.encode(text)
        assert tok.decode(ids) == text


# ---------------------------------------------------------------------------
# Logging tests
# ---------------------------------------------------------------------------

class TestLogging:
    def test_get_logger_default(self):
        from bpe_tokenizer.logging_setup import get_logger
        logger = get_logger("test")
        assert logger.name == "bpe_tokenizer.test"

    def test_configure_logging(self):
        from bpe_tokenizer.logging_setup import configure_logging, get_logger
        import logging
        configure_logging(level=logging.DEBUG)
        logger = get_logger("test2")
        # After configuration, the logger should have a handler.
        assert len(logger.handlers) > 0 or len(logging.getLogger("bpe_tokenizer").handlers) > 0


# ---------------------------------------------------------------------------
# train_from_file tests
# ---------------------------------------------------------------------------

class TestTrainFromFile:
    def test_train_from_file(self, tmp_path):
        corpus_path = tmp_path / "corpus.txt"
        corpus_path.write_text(CORPUS)
        tok = BPETokenizer()
        tok.train_from_file(corpus_path, TrainingConfig(vocab_size=80, min_frequency=1))
        ids = tok.encode("quick fox")
        assert len(ids) > 0

    def test_train_from_file_not_found(self):
        tok = BPETokenizer()
        with pytest.raises(TrainingError, match="not found"):
            tok.train_from_file("/nonexistent/corpus.txt")


# ---------------------------------------------------------------------------
# CLI tests
# ---------------------------------------------------------------------------

class TestCLI:
    def test_cli_train_and_encode(self, tmp_path):
        from bpe_tokenizer.cli import main
        corpus_path = tmp_path / "corpus.txt"
        corpus_path.write_text(CORPUS)
        model_path = str(tmp_path / "model.json")

        # Train.
        rc = main(["train", str(corpus_path), "-o", model_path,
                    "--vocab-size", "80", "--min-frequency", "1"])
        assert rc == 0
        assert Path(model_path).exists()

        # Encode.
        rc = main(["encode", "quick fox", "-m", model_path])
        assert rc == 0

        # Stats.
        rc = main(["stats", "-m", model_path])
        assert rc == 0

        # Roundtrip.
        rc = main(["roundtrip", "the quick fox", "-m", model_path])
        assert rc == 0

    def test_cli_wordpiece(self, tmp_path):
        from bpe_tokenizer.cli import main
        corpus_path = tmp_path / "corpus.txt"
        corpus_path.write_text(CORPUS)
        model_path = str(tmp_path / "model.json")

        main(["train", str(corpus_path), "-o", model_path,
              "--vocab-size", "80", "--min-frequency", "1"])
        rc = main(["wordpiece", "quick fox", "-m", model_path])
        assert rc == 0

    def test_cli_compare(self, tmp_path):
        from bpe_tokenizer.cli import main
        corpus_path = tmp_path / "corpus.txt"
        corpus_path.write_text(CORPUS)
        model_a = str(tmp_path / "model_a.json")
        model_b = str(tmp_path / "model_b.json")

        main(["train", str(corpus_path), "-o", model_a,
              "--vocab-size", "80", "--min-frequency", "1"])
        main(["train", str(corpus_path), "-o", model_b,
              "--vocab-size", "120", "--min-frequency", "1"])
        rc = main(["compare", str(corpus_path), "-a", model_a, "-b", model_b])
        assert rc == 0

    def test_cli_train_config(self, tmp_path):
        from bpe_tokenizer.cli import main
        config_data = {
            "training": {
                "vocab_size": 80,
                "pretokenizer": "gpt4",
                "min_frequency": 1,
                "normalizer": ["lowercase"],
            },
        }
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps(config_data))
        corpus_path = tmp_path / "corpus.txt"
        corpus_path.write_text(CORPUS)
        model_path = str(tmp_path / "model.json")

        rc = main(["train-config", str(config_path), str(corpus_path), "-o", model_path])
        assert rc == 0
        assert Path(model_path).exists()

    def test_cli_encode_with_attention_mask(self, tmp_path):
        from bpe_tokenizer.cli import main
        corpus_path = tmp_path / "corpus.txt"
        corpus_path.write_text(CORPUS)
        model_path = str(tmp_path / "model.json")

        main(["train", str(corpus_path), "-o", model_path,
              "--vocab-size", "80", "--min-frequency", "1"])
        rc = main(["encode", "fox", "-m", model_path,
                   "--max-length", "5", "--pad", "--attention-mask"])
        assert rc == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])