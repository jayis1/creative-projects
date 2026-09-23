"""Acrostic poem generator — first letters of lines spell a word."""

from __future__ import annotations
import random
from ..vocabulary import Vocabulary


def _line_starting_with(letter: str, vocab: Vocabulary) -> str:
    """Generate a poetic line whose first word starts with *letter*."""
    letter = letter.upper()
    all_words = vocab.nouns + vocab.adjectives + vocab.verbs + vocab.adverbs

    starters = [w for w in all_words if w.upper().startswith(letter)]
    if not starters:
        # Fallback: generic words for common letters
        fallbacks = {
            "A": ["ancient", "above"], "B": ["bright", "beneath"],
            "C": ["cold", "calm"], "D": ["dark", "deep"], "E": ["eternal", "endless"],
            "F": ["frozen", "faint"], "G": ["gentle", "golden"], "H": ["hollow", "high"],
            "I": ["infinite", "inner"], "J": ["just", "joined"], "K": ["keen", "kind"],
            "L": ["lonely", "lost"], "M": ["misty", "mighty"], "N": ["narrow", "near"],
            "O": ["open", "onward"], "P": ["pale", "pure"], "Q": ["quiet", "quick"],
            "R": ["restless", "rising"], "S": ["silent", "silver"], "T": ["tender", "tired"],
            "U": ["under", "unyielding"], "V": ["vast", "vivid"], "W": ["wild", "worn"],
            "X": ["xenial"], "Y": ["yearning"], "Z": ["zealous"],
        }
        starters = fallbacks.get(letter, [letter.lower() + "ound"])

    word = random.choice(starters)

    # Wrap it in a line
    templates = [
        lambda w: f"{w.capitalize()} {vocab.noun()} {vocab.verb()} {vocab.adverb()}",
        lambda w: f"{w.capitalize()} as the {vocab.noun_phrase()}",
        lambda w: f"{w.capitalize()} {vocab.verb()} {vocab.preposition()} the {vocab.noun()}",
        lambda w: f"{w.capitalize()} like a {vocab.noun_phrase()}",
        lambda w: f"{w.capitalize()} {vocab.adverb()} through the {vocab.adjective()} {vocab.noun()}",
    ]
    return random.choice(templates)(word)


def generate(vocab: Vocabulary, keyword: str | None = None) -> str:
    """Return an acrostic poem where line initials spell *keyword*.

    If *keyword* is None, a random word from the vocabulary is chosen.
    """
    if keyword is None:
        keyword = random.choice(vocab.nouns)
    keyword = keyword.upper()
    lines = [_line_starting_with(ch, vocab) for ch in keyword if ch.isalpha()]
    return "\n".join(lines)
