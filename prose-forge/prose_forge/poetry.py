"""Poetry generators: haiku, sonnet, free verse, and limerick with syllable counting."""

from __future__ import annotations

import random
import re


# --- Syllable counting ---

# Special cases: words where the heuristic fails
_SYLLABLE_EXCEPTIONS: dict[str, int] = {
    "the": 1, "a": 1, "an": 1, "and": 1, "but": 1, "or": 1, "nor": 1,
    "I": 1, "you": 1, "he": 1, "she": 1, "we": 1, "they": 1, "me": 1,
    "fire": 1, "hour": 1, "our": 1, "your": 1, "their": 1,
    "every": 3, "memory": 3, "beautiful": 3, "family": 3,
    "rhythm": 2, "algorithm": 4,
}

_SILENT_E_RE = re.compile(r"[^aeiouyl]e\b", re.IGNORECASE)
_VOWEL_GROUP_RE = re.compile(r"[aeiouy]+", re.IGNORECASE)


def count_syllables(word: str) -> int:
    """Estimate syllable count for an English word."""
    word = word.strip().lower().strip(".,;:!?\"'()-")
    if not word:
        return 0
    if word in _SYLLABLE_EXCEPTIONS:
        return _SYLLABLE_EXCEPTIONS[word]
    if word.isdigit():
        return len(word)  # each digit roughly one syllable
    groups = _VOWEL_GROUP_RE.findall(word)
    if not groups:
        return 1  # consonant-only words (e.g. "through") get 1
    count = len(groups)
    # Subtract silent trailing 'e' (consonant + e at end, e.g. "time", "like")
    if _SILENT_E_RE.search(word) and count > 1:
        count -= 1
    return max(count, 1)


def line_syllables(line: str) -> int:
    """Count total syllables in a line of text."""
    return sum(count_syllables(w) for w in line.split())


# --- Word pools for poetry ---

# 1-syllable words by category
MONO_NATURE = ["moon", "sun", "star", "sky", "rain", "wind", "snow", "leaf", "stone", "sea", "tide", "dawn", "dusk", "mist", "frost", "reed", "pine", "oak", "fern", "moss"]
MONO_ACTION = ["falls", "drifts", "sings", "breaks", "turns", "moves", "glows", "fades", "wakes", "sleeps", "walks", "stands", "lies", "lifts", "reaches", "parts"]
MONO_FEELING = ["cold", "warm", "still", "calm", "dark", "bright", "soft", "deep", "high", "low", "clear", "faint", "vast", "bare", "blank", "hushed"]
MONO_OBJECT = ["path", "door", "wall", "road", "bridge", "boat", "lamp", "bell", "cup", "book", "key", "ring", "cord", "thread", "bowl"]

# 2-syllable words
BI_NATURE = ["river", "shadow", "valley", "meadow", "twilight", "morning", "evening", "harbor", "forest", "garden", "thunder", "whisper", "petals", "willow", "autumn"]
BI_ACTION = ["lingers", "wandering", "flowing", "breaking", "rising", "fading", "calling", "waiting", "drifting", "falling", "turning", "gathering"]
BI_FEELING = ["silent", "gentle", "restless", "distant", "ancient", "empty", "peaceful", "solemn", "fragile", "hidden", "lonely", "timeless"]
BI_ABSTRACT = ["memory", "sorrow", "longing", "stillness", "echoes", "shadows", "seasons", "journeys", "dreaming", "whispers"]

# 3-syllable words
TRI_NATURE = ["canopy", "lullaby", "melody", "riverbed", "waterfall", "wilderness", "horizon", "overcast"]
TRI_ABSTRACT = ["mystery", "memory", "beautiful", "wandering", "reverie", "symphony", "ephemera", "solitude"]

# 4+ syllable words
POLY = ["ephemerally", "ineffable", "reminiscing", "luminous", "inexorable", "cacophony", "lullabies", "silhouette"]


class Poet:
    """Procedural poetry generator supporting multiple forms."""

    def __init__(self, seed: int | None = None):
        self._rng = random.Random(seed)

    def _fill_syllables(self, target: int, pools: list[list[str]]) -> str:
        """Fill a line to exactly `target` syllables by picking from pools."""
        words: list[str] = []
        remaining = target
        attempts = 0
        while remaining > 0 and attempts < 200:
            pool = self._rng.choice(pools)
            word = self._rng.choice(pool)
            syl = count_syllables(word)
            if syl <= remaining:
                words.append(word)
                remaining -= syl
            attempts += 1
        if remaining > 0:
            # Pad with monosyllabic words
            while remaining > 0:
                words.append(self._rng.choice(MONO_NATURE + MONO_FEELING))
                remaining -= 1
        return " ".join(words)

    def haiku(self) -> str:
        """Generate a 5-7-5 haiku."""
        all_pools = [MONO_NATURE, MONO_ACTION, MONO_FEELING, MONO_OBJECT,
                      BI_NATURE, BI_ACTION, BI_FEELING, BI_ABSTRACT, TRI_NATURE]
        line1 = self._fill_syllables(5, all_pools)
        line2 = self._fill_syllables(7, all_pools)
        line3 = self._fill_syllables(5, all_pools)
        # Capitalize first letters
        lines = [line1, line2, line3]
        lines = [l[0].upper() + l[1:] if l else l for l in lines]
        return "\n".join(lines)

    def tanka(self) -> str:
        """Generate a 5-7-5-7-7 tanka."""
        all_pools = [MONO_NATURE, MONO_ACTION, MONO_FEELING, MONO_OBJECT,
                      BI_NATURE, BI_ACTION, BI_FEELING, BI_ABSTRACT, TRI_NATURE]
        lines = []
        for count in [5, 7, 5, 7, 7]:
            line = self._fill_syllables(count, all_pools)
            lines.append(line[0].upper() + line[1:] if line else line)
        return "\n".join(lines)

    def limerick(self) -> str:
        """Generate a limerick (AABBA rhyme scheme, roughly correct meter)."""
        # Simple approach: use templates with rhyme
        place_a = self._rng.choice([
            "a scholar from Vespera fair",
            "a cartographer lost in the mist",
            "a blacksmith who lived by the sea",
            "a thief with a marvelous plan",
            "a healer who wandered too far",
            "a traveler lacking a map",
            "a poet who couldn't quite rhyme",
            "a sailor afraid of the dark",
        ])
        # A lines are longer (anapestic), B lines shorter
        a_lines = [
            f"There once was {place_a},",
            f"who searched for a mythical lair.",
        ]
        b_lines = [
            "they stumbled, they fell,",
            "they tripped on a spell,",
        ]
        final = f"and rose with their boots in the air."
        # Pick random endings for variety
        endings_a = [
            "who searched for a mythical lair.",
            "who traveled without any care.",
            "with wind in their untangled hair.",
            "who faced every dragon that's there.",
        ]
        endings_b = [
            "they stumbled, they fell,",
            "they tripped on a spell,",
            "they whispered, 'Oh well,'",
            "they rang a small bell,",
        ]
        line1 = f"There once was {place_a}"
        if not line1.rstrip().endswith(("fair", "mist", "sea", "plan", "far", "map", "rhyme", "dark")):
            line1 += ","
        a2 = self._rng.choice(endings_a)
        b1 = self._rng.choice(endings_b)
        b2 = self._rng.choice(endings_b)
        # Ensure b1 != b2
        while b2 == b1 and len(endings_b) > 1:
            b2 = self._rng.choice(endings_b)
        a5 = self._rng.choice(endings_a)
        lines = [
            line1[0].upper() + line1[1:],
            a2[0].upper() + a2[1:],
            b1[0].upper() + b1[1:],
            b2[0].upper() + b2[1:],
            a5[0].upper() + a5[1:],
        ]
        return "\n".join(lines)

    def free_verse(self, lines: int = 6) -> str:
        """Generate free verse poetry with variable line lengths."""
        all_pools = [MONO_NATURE, MONO_ACTION, MONO_FEELING, MONO_OBJECT,
                      BI_NATURE, BI_ACTION, BI_FEELING, BI_ABSTRACT,
                      TRI_NATURE, TRI_ABSTRACT, POLY]
        result: list[str] = []
        for _ in range(lines):
            target = self._rng.randint(3, 9)
            line = self._fill_syllables(target, all_pools)
            line = line[0].upper() + line[1:] if line else line
            result.append(line)
        return "\n".join(result)

    def sonnet(self) -> str:
        """Generate a rough 14-line sonnet (ABAB CDCD EFEF GG)."""
        all_pools = [MONO_NATURE, MONO_ACTION, MONO_FEELING, MONO_OBJECT,
                      BI_NATURE, BI_ACTION, BI_FEELING, BI_ABSTRACT, TRI_NATURE]
        lines = []
        for _ in range(14):
            # Aim for ~10 syllables per line (iambic pentameter-ish)
            line = self._fill_syllables(10, all_pools)
            line = line[0].upper() + line[1:] if line else line
            lines.append(line)
        # Group into quatrains + couplet
        return "\n".join(lines)