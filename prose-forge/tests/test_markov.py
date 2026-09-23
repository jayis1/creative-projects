"""Tests for the Markov chain text synthesizer."""

import pytest

from prose_forge.markov import MarkovChain


CORPUS = (
    "The quick brown fox jumps over the lazy dog. "
    "The lazy dog sleeps while the quick fox runs. "
    "A brown fox and a lazy dog are good friends. "
    "The fox is quick and the dog is lazy."
)


class TestMarkovBasics:
    def test_train_and_generate(self):
        chain = MarkovChain(order=2, seed=42)
        chain.train(CORPUS)
        text = chain.generate(length=20)
        assert len(text) > 0
        assert isinstance(text, str)

    def test_untrained_raises(self):
        chain = MarkovChain(order=2)
        with pytest.raises(RuntimeError, match="not trained"):
            chain.generate()

    def test_short_corpus_raises(self):
        chain = MarkovChain(order=5)
        with pytest.raises(ValueError, match="too short"):
            chain.train("hello")

    def test_invalid_order(self):
        with pytest.raises(ValueError, match="order"):
            MarkovChain(order=0)

    def test_invalid_level(self):
        with pytest.raises(ValueError, match="level"):
            MarkovChain(level="sentence")


class TestMarkovReproducibility:
    def test_same_seed_same_output(self):
        c1 = MarkovChain(order=2, seed=100)
        c1.train(CORPUS)
        c2 = MarkovChain(order=2, seed=100)
        c2.train(CORPUS)
        assert c1.generate(length=30) == c2.generate(length=30)

    def test_different_seed_different_output(self):
        c1 = MarkovChain(order=2, seed=1)
        c1.train(CORPUS)
        c2 = MarkovChain(order=2, seed=2)
        c2.train(CORPUS)
        # Very likely different
        assert c1.generate(length=50) != c2.generate(length=50)


class TestMarkovWordLevel:
    def test_word_level_output(self):
        chain = MarkovChain(order=2, level="word", seed=42)
        chain.train(CORPUS)
        text = chain.generate(length=10)
        words = text.split()
        assert len(words) <= 10
        # All words should come from the corpus
        corpus_words = set(CORPUS.split())
        for w in words:
            # Remove punctuation for comparison
            clean = w.strip(".,;:!?")
            assert clean in corpus_words or w in corpus_words

    def test_generate_sentence(self):
        chain = MarkovChain(order=2, level="word", seed=42)
        chain.train(CORPUS)
        sentence = chain.generate_sentence(min_words=3)
        assert sentence.endswith((".", "!", "?"))
        assert len(sentence.split()) >= 3

    def test_sentence_char_level_raises(self):
        chain = MarkovChain(order=2, level="char", seed=42)
        chain.train(CORPUS)
        with pytest.raises(ValueError, match="word-level"):
            chain.generate_sentence()


class TestMarkovCharLevel:
    def test_char_level_output(self):
        chain = MarkovChain(order=3, level="char", seed=42)
        chain.train(CORPUS)
        text = chain.generate(length=50)
        assert len(text) == 50
        # Output characters should come from corpus
        corpus_chars = set(CORPUS)
        for ch in text:
            assert ch in corpus_chars


class TestMarkovProperties:
    def test_chain_size(self):
        chain = MarkovChain(order=2, seed=42)
        assert chain.chain_size == 0
        assert not chain.is_trained
        chain.train(CORPUS)
        assert chain.chain_size > 0
        assert chain.is_trained