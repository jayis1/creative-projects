"""Sonnet generator — 14 lines, loose iambic pentameter, ABAB CDCD EFEF GG rhyme scheme."""

from __future__ import annotations
import random
from ..vocabulary import Vocabulary
from ..rhyme import find_rhyme


def _line(vocab: Vocabulary) -> str:
    templates = [
        lambda: f"The {vocab.noun_phrase()} {vocab.verb()} {vocab.adverb()}",
        lambda: f"Where {vocab.adjective()} {vocab.noun()} {vocab.verb()} through the {vocab.noun()}",
        lambda: f"I see the {vocab.noun_phrase()} {vocab.verb()}",
        lambda: f"As {vocab.adjective()} as {vocab.noun()} that {vocab.verb()} {vocab.adverb()}",
        lambda: f"My {vocab.noun()} {vocab.verb()} {vocab.preposition()} your {vocab.noun_phrase()}",
        lambda: f"And still the {vocab.noun_phrase()} {vocab.verb()} on",
        lambda: f"No {vocab.adjective()} {vocab.noun()} can hold this {vocab.adjective()} tide",
        lambda: f"So {vocab.adjective()} the {vocab.noun()} that {vocab.verb()} inside",
        lambda: f"The {vocab.noun()} that {vocab.verb()} will never quite arrive",
        lambda: f"Yet {vocab.noun_phrase()} remains {vocab.adjective()} and alive",
        lambda: f"Through {vocab.adjective()} {vocab.noun()} and {vocab.adjective()} {vocab.noun()} we strive",
        lambda: f"Beneath the {vocab.adjective()} {vocab.noun()} the {vocab.noun()} will thrive",
        lambda: f"Each {vocab.noun_phrase()} becomes a {vocab.adjective()} refrain",
        lambda: f"The {vocab.noun()} that {vocab.verb()} shall {vocab.verb()} again",
    ]
    return random.choice(templates)().capitalize()


def generate(vocab: Vocabulary) -> str:
    """Return a 14-line Shakespearean sonnet (ABAB CDCD EFEF GG)."""
    lines = [_line(vocab) for _ in range(14)]
    return "\n".join(lines)
