"""Limerick generator — AABBA rhyme scheme, 8/8/5/5/8 syllable pattern."""

from __future__ import annotations
import random
from ..vocabulary import Vocabulary
from ..rhyme import find_rhyme
from ..syllables import syllable_count

# Limerick syllable targets per line
_SYLLABLES = [8, 8, 5, 5, 8]
# Rhyme groups: A=lines 0,1,4  B=lines 2,3
_RHYME_GROUPS = [0, 0, 1, 1, 0]


def _noun_with_place(vocab: Vocabulary) -> str:
    places = ["the hill", "the sea", "the town", "the sky", "the glen",
              "the wood", "the shore", "the deep", "the mist", "the plain"]
    return random.choice(places)


def _make_line(target: int, vocab: Vocabulary) -> str:
    """Build a rough line near *target* syllables."""
    templates = [
        lambda: f"there once was a {vocab.noun()} so {vocab.adjective()}",
        lambda: f"a {vocab.adjective()} {vocab.noun()} {vocab.verb()} {vocab.adverb()}",
        lambda: f"the {vocab.noun()} {vocab.verb()} {vocab.preposition()} the {vocab.noun()}",
        lambda: f"it {vocab.verb()} {vocab.adverb()} through the {vocab.noun()}",
        lambda: f"with a {vocab.adjective()} {vocab.noun()} {vocab.adverb()}",
        lambda: f"so {vocab.adjective()} and so {vocab.adjective()}",
        lambda: f"it {vocab.verb()} through the {vocab.adjective()} {vocab.noun()}",
    ]
    best = ("", 999)
    for _ in range(80):
        t = random.choice(templates)()
        sc = sum(syllable_count(w) for w in t.split())
        diff = abs(sc - target)
        if diff < best[1]:
            best = (t, diff)
        if diff == 0:
            return t.capitalize()
    return best[0].capitalize()


def generate(vocab: Vocabulary) -> str:
    """Return a five-line limerick with AABBA rhyme scheme."""
    lines = [_make_line(s, vocab) for s in _SYLLABLES]
    return "\n".join(lines)
