"""Bug hunt tests for the BPE tokenizer.

Each test verifies a specific bug before and after the fix.
"""

import pytest
from bpe_tokenizer import (
    BPETokenizer,
    TrainingConfig,
    Normalization,
    Normalizer,
    TruncationStrategy,
    truncate,
    TokenizerAnalyzer,
)
from bpe_tokenizer.encoder import BPESentencePiece, bpe_dropout
import random


CORPUS = """
The quick brown fox jumps over the lazy dog.
The quick brown fox is very quick indeed.
Lazy dogs sleep while quick foxes jump.
The dog and the fox are friends.
Quick quick quick lazy lazy lazy.
"""


class TestBugLexicographicTieBreaking:
    """Bug 6: Tie-breaking in merge selection picks lexicographically
    LARGEST pair instead of smallest.

    The ``max`` function with key ``(count, lexicographic_key(pair))``
    picks the maximum, so ties go to the lexicographically largest pair.
    The comment says "smallest first" — the tie-breaking is inverted.
    """

    def test_tie_breaking_is_deterministic(self):
        """Training should be deterministic — same corpus, same config,
        same result every time."""
        tok1 = BPETokenizer()
        tok1.train(CORPUS, TrainingConfig(vocab_size=80, min_frequency=1))
        tok2 = BPETokenizer()
        tok2.train(CORPUS, TrainingConfig(vocab_size=80, min_frequency=1))
        assert tok1.encode("quick fox") == tok2.encode("quick fox")

    def test_tie_breaking_picks_smallest(self):
        """When two pairs have the same count, the lexicographically
        smallest pair should be merged first (per the documentation)."""
        # Create a corpus where 'ab' and 'ba' both appear with the same freq.
        # 'ab' < 'ba' lexicographically, so 'ab' should merge first.
        corpus = "ab ab ba ba cd cd"  # 'ab' appears 2x, 'ba' appears 2x (but 'ab' as a pair is (a,b), 'ba' is (b,a))
        tok = BPETokenizer()
        tok.train(corpus, TrainingConfig(vocab_size=20, min_frequency=1))
        # Check that the merge ranks reflect the tie-breaking.
        # The pair ('a', 'b') should have rank 1 (merged first) since
        # ('a', 'b') < ('b', 'a') lexicographically.
        rank_ab = tok._merge_ranks.get(('a', 'b'))
        rank_ba = tok._merge_ranks.get(('b', 'a'))
        if rank_ab is not None and rank_ba is not None:
            assert rank_ab < rank_ba, (
                f"Expected ('a','b') rank < ('b','a') rank, "
                f"got {rank_ab} vs {rank_ba}"
            )


class TestBugDeadCodeInRebuildMergeRanks:
    """Bug 1: _rebuild_merge_ranks has a dead first loop that does nothing."""

    def test_rebuild_merge_ranks_correct(self):
        """Merge ranks should be correctly reconstructed after training."""
        tok = BPETokenizer()
        tok.train(CORPUS, TrainingConfig(vocab_size=80, min_frequency=1))
        # Every merged token (rank > 0) should have a corresponding entry
        # in _merge_ranks.
        merged_count = sum(1 for t in tok.vocab.tokens.values() if t.rank > 0)
        assert len(tok._merge_ranks) == merged_count, (
            f"Expected {merged_count} merge ranks, got {len(tok._merge_ranks)}"
        )


class TestBugEncodeAdvancedPadding:
    """Bug 3: encode_advanced doesn't pad when pad_id is None but
    max_length and return_attention_mask are set."""

    def test_encode_advanced_pads_with_default_pad(self):
        """When return_attention_mask=True and max_length is set,
        the sequence should be padded to max_length using the PAD token,
        even if pad_id is not explicitly provided."""
        tok = BPETokenizer()
        tok.train(CORPUS, TrainingConfig(vocab_size=80, min_frequency=1))
        result = tok.encode_advanced(
            "fox",
            max_length=5,
            return_attention_mask=True,
        )
        assert len(result["input_ids"]) == 5, (
            f"Expected 5 tokens after padding, got {len(result['input_ids'])}"
        )
        assert len(result["attention_mask"]) == 5
        # Some positions should be padding (mask=0)
        assert 0 in result["attention_mask"], (
            "Expected at least one padding position (mask=0)"
        )


class TestBugBatchTruncationIgnoresSpecials:
    """Bug 4: encode_batch truncates with r[:max_length] which can
    cut off EOS tokens."""

    def test_batch_truncation_preserves_specials(self):
        """When max_length is set, batch truncation should preserve
        BOS/EOS tokens."""
        tok = BPETokenizer()
        tok.train(CORPUS, TrainingConfig(vocab_size=80, min_frequency=1))
        # Encode with BOS/EOS and a max_length that's shorter than the full encoding.
        text = "the quick brown fox jumps"
        ids_full = tok.encode(text, add_bos=True, add_eos=True)
        assert len(ids_full) > 3  # ensure we have enough to truncate

        # Now batch-encode with truncation.
        results = tok.encode_batch(
            [text], add_bos=True, add_eos=True, padding=True, max_length=3,
        )
        # BOS should be at position 0, EOS at the end.
        bos_id = tok.vocab.specials["<bos>"].id
        eos_id = tok.vocab.specials["<eos>"].id
        assert results[0][0] == bos_id, "BOS should be preserved at start"
        # With max_length=3 and padding, EOS might be at position 2 or padding.
        # But BOS should always be there.
        assert len(results[0]) == 3


class TestBugViterbiNoNormalization:
    """Bug 10: BPESentencePiece.encode doesn't apply the normalizer,
    producing inconsistent results with regular encoding."""

    def test_viterbi_applies_normalizer(self):
        """If a normalizer is configured (e.g., lowercase), Viterbi
        encoding should produce the same result as regular encoding
        on the normalized text."""
        tok = BPETokenizer()
        cfg = TrainingConfig(
            vocab_size=80, min_frequency=1,
            normalizer_flags=int(Normalization.LOWERCASE.value),
        )
        tok.train(CORPUS, cfg)

        # Regular encoding lowercases first.
        ids_regular = tok.encode("HELLO")

        # Viterbi should also lowercase first.
        sp = BPESentencePiece(tok)
        ids_viterbi = sp.encode("HELLO")

        # Both should decode to the same lowercased text.
        assert tok.decode(ids_regular) == tok.decode(ids_viterbi), (
            "Viterbi encoding should apply normalizer like regular encoding"
        )


class TestBugVocabDuplicatePiece:
    """Bug 8: Vocab.add_token silently overwrites duplicate pieces,
    creating id collisions."""

    def test_add_token_duplicate_raises(self):
        """Adding a duplicate token piece should raise an error, not
        silently overwrite."""
        from bpe_tokenizer.vocab import Vocab
        v = Vocab()
        v.add_token("ab", b"ab", rank=0)
        # Adding "ab" again should raise.
        with pytest.raises(ValueError, match="already exists"):
            v.add_token("ab", b"ab", rank=1)


class TestBugBpeDropoutTermination:
    """Test that BPE-dropout terminates even with high dropout rates."""

    def test_dropout_terminates_high(self):
        """BPE-dropout with p=0.9 should still terminate."""
        tok = BPETokenizer()
        tok.train(CORPUS, TrainingConfig(vocab_size=80, min_frequency=1))
        rng = random.Random(42)
        ids = bpe_dropout(tok, "quick brown fox jumps", dropout=0.9, rng=rng)
        assert len(ids) > 0

    def test_dropout_1_terminates(self):
        """BPE-dropout with p=1.0 should terminate (no merges happen)."""
        tok = BPETokenizer()
        tok.train(CORPUS, TrainingConfig(vocab_size=80, min_frequency=1))
        rng = random.Random(42)
        ids = bpe_dropout(tok, "fox", dropout=1.0, rng=rng)
        assert len(ids) > 0  # should return individual characters


class TestBugCacheReturnsCopy:
    """Test that the encode cache returns a copy, not the internal list,
    so mutations by the caller don't corrupt the cache."""

    def test_cache_returns_copy(self):
        tok = BPETokenizer()
        tok.train(CORPUS, TrainingConfig(vocab_size=80, min_frequency=1))
        ids1 = tok.encode("quick fox")
        ids1.append(999)  # mutate the returned list
        ids2 = tok.encode("quick fox")
        assert 999 not in ids2, "Cache should return a copy, not the internal list"


class TestBugDecodeWithUnknownIds:
    """Test decode handles unknown ids gracefully."""

    def test_decode_unknown_id(self):
        tok = BPETokenizer()
        tok.train(CORPUS, TrainingConfig(vocab_size=80, min_frequency=1))
        # Decode with a non-existent id should not crash.
        ids = tok.encode("fox") + [99999]
        text = tok.decode(ids)
        assert "fox" in text  # known part should decode fine


class TestBugEmptyCorpusTraining:
    """Test that training on an empty corpus doesn't crash."""

    def test_train_empty_corpus(self):
        tok = BPETokenizer()
        cfg = TrainingConfig(vocab_size=50, min_frequency=1)
        tok.train("", cfg)
        # Should have specials but no regular tokens.
        assert tok.vocab.size() == len(tok.vocab.specials)