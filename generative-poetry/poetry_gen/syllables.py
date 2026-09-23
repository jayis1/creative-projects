"""Syllable counting via CMU-inspired heuristics."""

import re

# Vowel groups that count as one syllable
_VOWEL_RE = re.compile(r"[aeiouy]+", re.IGNORECASE)

# Silent-e endings (single silent e after a consonant)
_SILENT_E = re.compile(r"[^aeiouy]e$", re.IGNORECASE)

# Diphthongs and special digraphs that collapse to one syllable
_COLLAPSE = re.compile(r"(tion|sion|cial|tial|ious|uous|ia|io|ii)", re.IGNORECASE)

# Two vowels that form one sound
_DOUBLE_V = re.compile(r"(aa|ae|ai|ao|au|ea|ee|ei|eo|eu|ia|ie|ii|io|oa|oe|oi|oo|ou|ua|ue|ui|uo|uu)", re.IGNORECASE)


def syllable_count(word: str) -> int:
    """Estimate number of syllables in *word* using rule-based heuristics.

    Returns at least 1 for any non-empty word.
    """
    word = word.strip().lower()
    if not word:
        return 0
    # Strip punctuation
    word = re.sub(r"[^a-z]", "", word)
    if not word:
        return 1

    count = len(_VOWEL_RE.findall(word))

    # Subtract silent trailing e
    if count > 1 and _SILENT_E.search(word):
        count -= 1

    # Ensure at least 1
    return max(1, count)


def line_syllables(line: str) -> int:
    """Count total syllables across all words in a line."""
    return sum(syllable_count(w) for w in line.split())
