"""Rhyme detection based on phonetic suffix matching."""

import re


def _phonetic_tail(word: str, n: int = 3) -> str:
    """Return the last *n* characters of the vowel-onward suffix.

    E.g. "flying" -> "ing", "lake" -> "ake".
    """
    word = re.sub(r"[^a-z]", "", word.lower())
    # Find last vowel cluster start
    m = list(re.finditer(r"[aeiouy]", word))
    if not m:
        return word[-n:] if len(word) >= n else word
    start = m[-1].start()
    # Back up to include any consonant right before the last vowel group
    tail = word[max(0, start - 1):]
    return tail[-n:] if len(tail) >= n else tail


def rhymes(word_a: str, word_b: str) -> bool:
    """Return True if *word_a* and *word_b* rhyme (share phonetic tail)."""
    if word_a.lower() == word_b.lower():
        return False  # identical words don't count as a rhyme
    tail_a = _phonetic_tail(word_a)
    tail_b = _phonetic_tail(word_b)
    return tail_a == tail_b and len(tail_a) >= 2


def find_rhyme(target: str, candidates: list[str]) -> str | None:
    """Return the first word in *candidates* that rhymes with *target*, or None."""
    for c in candidates:
        if rhymes(target, c):
            return c
    return None
