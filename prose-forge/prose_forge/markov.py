"""N-gram Markov chain text synthesizer."""

from __future__ import annotations

import random
import re
from collections import defaultdict


class MarkovChain:
    """N-gram Markov chain for text generation.

    Supports character-level and word-level chains, adjustable order,
    and seeded generation for reproducibility.
    """

    def __init__(self, order: int = 2, level: str = "word", seed: int | None = None):
        if order < 1:
            raise ValueError("order must be >= 1")
        if level not in ("word", "char"):
            raise ValueError("level must be 'word' or 'char'")
        self.order = order
        self.level = level
        self._rng = random.Random(seed)
        self.chain: dict[tuple, list[str]] = defaultdict(list)
        self._starts: list[tuple] = []
        self._trained = False

    def _tokenize(self, text: str) -> list[str]:
        if self.level == "word":
            # Keep punctuation attached to words for natural prose
            return re.findall(r"\S+", text)
        else:
            return list(text)

    def _detokenize(self, tokens: list[str]) -> str:
        if self.level == "word":
            return " ".join(tokens)
        else:
            return "".join(tokens)

    def train(self, text: str) -> None:
        """Train the chain on a corpus string."""
        tokens = self._tokenize(text)
        if len(tokens) < self.order + 1:
            raise ValueError(
                f"Corpus too short: need at least {self.order + 1} tokens, got {len(tokens)}"
            )
        # Record start states (beginnings of sentences or lines)
        if self.level == "word":
            # Use sentence starts
            sentences = re.split(r"[.!?]+", text)
            for sent in sentences:
                sent_tokens = self._tokenize(sent.strip())
                if len(sent_tokens) >= self.order:
                    self._starts.append(tuple(sent_tokens[: self.order]))
        else:
            # Use line starts
            for line in text.split("\n"):
                line_tokens = self._tokenize(line.strip())
                if len(line_tokens) >= self.order:
                    self._starts.append(tuple(line_tokens[: self.order]))
        if not self._starts:
            self._starts.append(tuple(tokens[: self.order]))

        # Build the chain
        for i in range(len(tokens) - self.order):
            state = tuple(tokens[i : i + self.order])
            next_token = tokens[i + self.order]
            self.chain[state].append(next_token)

        self._trained = True

    def generate(self, length: int = 100, start: tuple | None = None) -> str:
        """Generate text of approximately `length` tokens."""
        if not self._trained:
            raise RuntimeError("Chain not trained. Call train() first.")
        if not self.chain:
            return ""

        # Choose starting state
        if start is not None:
            current = start
        elif self._starts:
            current = self._rng.choice(self._starts)
        else:
            current = self._rng.choice(list(self.chain.keys()))

        if len(current) != self.order:
            raise ValueError(f"start tuple must have length {self.order}")

        result = list(current)

        for _ in range(length - len(current)):
            followers = self.chain.get(current)
            if not followers:
                # Dead end: pick a random new start
                if self._starts:
                    current = self._rng.choice(self._starts)
                else:
                    current = self._rng.choice(list(self.chain.keys()))
                result.extend(current)
                continue
            next_token = self._rng.choice(followers)
            result.append(next_token)
            current = tuple(result[-self.order :])

        return self._detokenize(result[:length])

    def generate_sentence(self, min_words: int = 8, max_attempts: int = 20) -> str:
        """Generate a single sentence with at least min_words words (word-level only)."""
        if self.level != "word":
            raise ValueError("generate_sentence requires word-level chain")
        for _ in range(max_attempts):
            text = self.generate(length=max(min_words * 3, 30))
            # Extract the first complete sentence
            match = re.match(r"(.+?[.!?])", text)
            if match:
                sentence = match.group(1).strip()
                words = sentence.split()
                if len(words) >= min_words:
                    return sentence
        # Fallback: return what we have
        return text.strip()

    @property
    def chain_size(self) -> int:
        return len(self.chain)

    @property
    def is_trained(self) -> bool:
        return self._trained