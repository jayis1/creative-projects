"""Haiku generator — 5/7/5 syllable structure."""

from __future__ import annotations
import random
from ..syllables import syllable_count, line_syllables
from ..vocabulary import Vocabulary


def _fill_line(target: int, vocab: Vocabulary, max_attempts: int = 200) -> str:
    """Build a phrase with exactly *target* syllables from vocab."""
    templates = [
        lambda: f"the {vocab.noun_phrase()}",
        lambda: f"{vocab.adjective()} {vocab.noun()}",
        lambda: f"{vocab.noun()} {vocab.verb()}",
        lambda: f"{vocab.noun()} {vocab.preposition()} the {vocab.noun()}",
        lambda: f"{vocab.verb()} the {vocab.noun()}",
        lambda: f"{vocab.adjective()} {vocab.noun()} {vocab.verb()}",
        lambda: f"{vocab.adverb()} {vocab.verb()}",
        lambda: f"{vocab.noun_phrase()} {vocab.verb()}",
    ]

    for _ in range(max_attempts):
        candidate = random.choice(templates)()
        if line_syllables(candidate) == target:
            return candidate.capitalize()

    # Fallback: just build word by word
    words: list[str] = []
    used = 0
    pools = vocab.nouns + vocab.adjectives + vocab.verbs + vocab.adverbs
    for _ in range(max_attempts):
        w = random.choice(pools)
        sc = syllable_count(w)
        if used + sc <= target:
            words.append(w)
            used += sc
        if used == target:
            return " ".join(words).capitalize()
    # Give up and return closest
    return (" ".join(words) or vocab.noun()).capitalize()


def generate(vocab: Vocabulary) -> str:
    """Return a haiku (5-7-5) as a three-line string."""
    lines = [_fill_line(5, vocab), _fill_line(7, vocab), _fill_line(5, vocab)]
    return "\n".join(lines)
