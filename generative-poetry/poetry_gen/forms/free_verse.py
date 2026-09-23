"""Free verse generator — no strict meter or rhyme, image-driven."""

from __future__ import annotations
import random
from ..vocabulary import Vocabulary


def _image_line(vocab: Vocabulary) -> str:
    templates = [
        lambda: f"The {vocab.noun_phrase()} {vocab.verb()} {vocab.adverb()}.",
        lambda: f"{vocab.adjective().capitalize()} {vocab.noun()} {vocab.verb()} {vocab.preposition()} the {vocab.noun()}.",
        lambda: f"I remember the {vocab.noun()} that {vocab.verb()} {vocab.adverb()}.",
        lambda: f"How {vocab.adjective()} the {vocab.noun_phrase()} becomes.",
        lambda: f"There is a {vocab.noun_phrase()} {vocab.verb_phrase(adv=True)}.",
        lambda: f"We do not speak of the {vocab.noun()}.",
        lambda: f"{vocab.noun_phrase().capitalize()} and {vocab.noun_phrase()}.",
        lambda: f"Under the {vocab.adjective()} {vocab.noun()}, {vocab.noun()} {vocab.verb()}.",
        lambda: f"Even the {vocab.noun()} {vocab.verb()} {vocab.adverb()}.",
        lambda: f"A {vocab.noun_phrase()} waits {vocab.preposition()} the {vocab.noun()}.",
    ]
    return random.choice(templates)()


def generate(vocab: Vocabulary, n_lines: int | None = None) -> str:
    """Return a free-verse poem of *n_lines* (default random 6–12)."""
    if n_lines is None:
        n_lines = random.randint(6, 12)
    return "\n".join(_image_line(vocab) for _ in range(n_lines))
