"""Culture-aware name generator for fantasy, sci-fi, and historical settings."""

from __future__ import annotations

import random


class NameGenerator:
    """Procedural name generator with culture-specific phoneme sets."""

    CULTURES = {
        "fantasy": {
            "prefixes": ["Aer", "Bel", "Cor", "Dae", "El", "Fen", "Gor", "Hel", "Ith", "Jor", "Kael", "Lyr", "Mor", "Nyx", "Or", "Pel", "Quel", "Rha", "Sil", "Tor", "Ul", "Vor", "Wyn", "Xan", "Yth", "Zar"],
            "middles": ["a", "e", "i", "o", "u", "an", "en", "ir", "or", "ul", "al", "el", "il", "ol"],
            "suffixes": ["dor", "wyn", "thas", "ric", "ion", "iel", "an", "ess", "or", "ix", "ya", "eth", "im", "as", "wyn", "ael"],
            "family": ["Blackwood", "Ironwell", "Stormhaven", "Thornvale", "Ashford", "Crowley", "Coldwater", "Brightmore", "Marsh", "Vane", "Grimward", "Silvermark", "Hollowell", "Ravencrest"],
        },
        "sci_fi": {
            "prefixes": ["Kry", "Vex", "Zer", "Nex", "Qua", "Tho", "Pri", "Oct", "Sep", "Hex", "Nov", "Tau", "Rho", "Pyr", "Lyr", "Cyb", "Met", "Dyn", "Sol", "Vel"],
            "middles": ["a", "e", "i", "o", "u", "an", "en", "ix", "or", "ax", "el", "on"],
            "suffixes": ["ix", "on", "us", "ar", "is", "ex", "or", "an", "os", "ax", "ium", "yx", "ion", "eer"],
            "family": ["Voss", "Krell", "Drax", "Niven", "Corvex", "Pyren", "Thalix", "Velkar", "Soryn", "Quen", "Malstrom", "Cyrene"],
        },
        "norse": {
            "prefixes": ["Al", "Bjor", "Ein", "Fro", "Gunn", "Hall", "Ing", "Jo", "Ket", "Lief", "Magn", "Ol", "Rag", "Sig", "Thor", "Ulf", "Val", "Yng"],
            "middles": ["a", "e", "i", "or", "il", "ar", "el"],
            "suffixes": ["ar", "ir", "in", "vid", "run", "bjorn", "mar", "ketil", "fast", "gard", "frid", "mod", "dis", "veig"],
            "family": ["StorHAUg", "Skullsplitter", "Ironjaw", "Frostbeard", "Shieldbreaker", "Ravenwing", "Stormrider", "Wolfsbane", "Oakheart", "Sea-King"],
        },
        "japanese": {
            "prefixes": ["Aki", "Hiro", "Kazu", "Masa", "Nobu", "Ryo", "Taka", "Yuki", "Haru", "Ken", "Sato", "Yoshi", "Tomo", "Iwa"],
            "middles": ["", "mi", "ko", "shi", "ka", "na", "ya"],
            "suffixes": ["ko", "to", "shi", "hiro", "aki", "ru", "mi", "ya", "ji", "o", "e", "ka"],
            "family": ["Tanaka", "Suzuki", "Watanabe", "Ito", "Yamamoto", "Nakamura", "Kobayashi", "Sato", "Takahashi", "Mori", "Ishikawa", "Kato"],
        },
        "arabic": {
            "prefixes": ["Abd", "Ah", "Az", "Ba", "Fa", "Ha", "Ib", "Ka", "Ma", "Ra", "Sa", "Ta", "Ya", "Za"],
            "middles": ["du", "ra", "ma", "la", "na", "sa", "ya", "ba"],
            "suffixes": ["lah", "im", "ad", "ar", "id", "iz", "an", "al", "din", "man", "ullah", "ullah"],
            "family": ["Al-Rashid", "Ibn-Sina", "Al-Farabi", "Al-Ghazali", "Ibn-Khaldun", "Al-Tusi", "Al-Kindi", "Al-Biruni", "Al-Masudi"],
        },
    }

    def __init__(self, seed: int | None = None):
        self._rng = random.Random(seed)

    def _generate_first(self, culture: str) -> str:
        data = self.CULTURES.get(culture, self.CULTURES["fantasy"])
        prefix = self._rng.choice(data["prefixes"])
        middle = self._rng.choice(data["middles"])
        suffix = self._rng.choice(data["suffixes"])
        # Sometimes skip the middle
        if self._rng.random() < 0.3 or not middle:
            return prefix + suffix
        return prefix + middle + suffix

    def _generate_family(self, culture: str) -> str:
        data = self.CULTURES.get(culture, self.CULTURES["fantasy"])
        return self._rng.choice(data["family"])

    def generate(self, culture: str = "fantasy", with_family: bool = True) -> str:
        """Generate a single name."""
        if culture not in self.CULTURES:
            raise ValueError(f"Unknown culture: {culture}. Available: {list(self.CULTURES)}")
        first = self._generate_first(culture)
        if with_family:
            family = self._generate_family(culture)
            if culture == "japanese":
                return f"{family} {first}"
            return f"{first} {family}"
        return first

    def generate_many(self, culture: str = "fantasy", count: int = 5, with_family: bool = True) -> list[str]:
        """Generate multiple unique names."""
        names: set[str] = set()
        attempts = 0
        while len(names) < count and attempts < count * 10:
            names.add(self.generate(culture, with_family))
            attempts += 1
        return list(names)[:count]

    @property
    def available_cultures(self) -> list[str]:
        return list(self.CULTURES)