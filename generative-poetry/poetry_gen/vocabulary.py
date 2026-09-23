"""Themed vocabulary pools used by the poem generators."""

from __future__ import annotations
import random
from dataclasses import dataclass, field
from typing import Sequence


@dataclass
class Vocabulary:
    """A collection of thematic word lists."""

    theme: str = "nature"

    # Each list can be overridden at construction time
    nouns: list[str] = field(default_factory=list)
    verbs: list[str] = field(default_factory=list)
    adjectives: list[str] = field(default_factory=list)
    adverbs: list[str] = field(default_factory=list)
    prepositions: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.nouns:
            self.nouns = list(_THEMES.get(self.theme, _THEMES["nature"])["nouns"])
        if not self.verbs:
            self.verbs = list(_THEMES.get(self.theme, _THEMES["nature"])["verbs"])
        if not self.adjectives:
            self.adjectives = list(_THEMES.get(self.theme, _THEMES["nature"])["adjectives"])
        if not self.adverbs:
            self.adverbs = list(_THEMES.get(self.theme, _THEMES["nature"])["adverbs"])
        if not self.prepositions:
            self.prepositions = ["above", "below", "beyond", "through", "within",
                                  "beside", "beneath", "around", "across", "upon"]

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    def pick(self, pool: Sequence[str]) -> str:
        return random.choice(pool)

    def noun(self) -> str:
        return self.pick(self.nouns)

    def verb(self) -> str:
        return self.pick(self.verbs)

    def adjective(self) -> str:
        return self.pick(self.adjectives)

    def adverb(self) -> str:
        return self.pick(self.adverbs)

    def preposition(self) -> str:
        return self.pick(self.prepositions)

    # ------------------------------------------------------------------ #
    # Word-form helpers                                                    #
    # ------------------------------------------------------------------ #

    def noun_phrase(self, adj: bool = True) -> str:
        n = self.noun()
        if adj:
            return f"{self.adjective()} {n}"
        return n

    def verb_phrase(self, adv: bool = False) -> str:
        v = self.verb()
        if adv:
            return f"{v} {self.adverb()}"
        return v

    @classmethod
    def themes(cls) -> list[str]:
        return list(_THEMES.keys())


# ------------------------------------------------------------------ #
# Built-in theme data                                                  #
# ------------------------------------------------------------------ #

_THEMES: dict[str, dict[str, list[str]]] = {
    "nature": {
        "nouns": [
            "mountain", "river", "forest", "ocean", "meadow", "cloud", "dawn",
            "dusk", "storm", "petal", "leaf", "stone", "wind", "rain", "flame",
            "shadow", "moonlight", "sunbeam", "thunder", "blossom", "fog",
            "brook", "canopy", "glacier", "tide", "horizon", "snowflake",
        ],
        "verbs": [
            "whispers", "dances", "roars", "glimmers", "fades", "blooms",
            "flows", "rises", "falls", "drifts", "shimmers", "echoes",
            "trembles", "soars", "lingers", "cascades", "wanders", "breathes",
        ],
        "adjectives": [
            "ancient", "silent", "silver", "golden", "wild", "gentle",
            "vast", "fragile", "eternal", "verdant", "crimson", "pale",
            "dark", "bright", "misty", "frozen", "tender", "mighty",
        ],
        "adverbs": [
            "softly", "slowly", "endlessly", "quietly", "gently",
            "fiercely", "briefly", "deeply", "freely", "swiftly",
        ],
    },
    "city": {
        "nouns": [
            "street", "tower", "alley", "bridge", "window", "crowd", "light",
            "neon", "subway", "rooftop", "pavement", "fog", "siren", "clock",
            "billboard", "café", "shadow", "headlight", "skyline", "doorway",
        ],
        "verbs": [
            "rushes", "glows", "fades", "echoes", "flickers", "roars",
            "hums", "drifts", "crowds", "moves", "shifts", "pulses",
            "lingers", "vanishes", "awakens", "sleeps",
        ],
        "adjectives": [
            "grey", "electric", "crowded", "lonely", "neon", "damp",
            "cold", "bright", "narrow", "towering", "distant", "frantic",
            "sleepless", "hurried", "forgotten", "glass",
        ],
        "adverbs": [
            "endlessly", "relentlessly", "quietly", "loudly", "swiftly",
            "suddenly", "anonymously", "brightly", "darkly", "urgently",
        ],
    },
    "space": {
        "nouns": [
            "star", "nebula", "void", "comet", "planet", "cosmos", "orbit",
            "eclipse", "photon", "quasar", "pulsar", "gravity", "supernova",
            "asteroid", "constellation", "dark matter", "singularity",
        ],
        "verbs": [
            "expands", "collapses", "drifts", "ignites", "spirals",
            "radiates", "dims", "bursts", "curves", "fuses", "travels",
            "bends", "scatters", "resonates", "pulses",
        ],
        "adjectives": [
            "infinite", "dark", "luminous", "cold", "ancient", "cosmic",
            "distant", "silent", "radiant", "vast", "primordial", "burning",
            "hollow", "weightless", "timeless",
        ],
        "adverbs": [
            "infinitely", "silently", "eternally", "endlessly", "radically",
            "coldly", "brilliantly", "softly", "slowly", "violently",
        ],
    },
    "autumn": {
        "nouns": [
            "leaf", "harvest", "mist", "bonfire", "acorn", "bramble", "rust",
            "cobweb", "orchard", "scarecrow", "frost", "cider", "twilight",
            "mushroom", "lantern", "hawthorn", "pumpkin",
        ],
        "verbs": [
            "falls", "decays", "burns", "gathers", "drifts", "crunches",
            "fades", "darkens", "ripens", "withers", "glows", "settles",
            "shivers", "smolders", "lingers",
        ],
        "adjectives": [
            "amber", "russet", "bare", "chilled", "golden", "brittle",
            "smoky", "faded", "earthy", "rotting", "fiery", "pale",
            "somber", "warm", "harvest",
        ],
        "adverbs": [
            "slowly", "quietly", "gently", "dimly", "crisply", "warmly",
            "softly", "reluctantly", "silently", "inevitably",
        ],
    },
    "sea": {
        "nouns": [
            "wave", "shore", "anchor", "sail", "lighthouse", "reef", "current",
            "depth", "horizon", "vessel", "gull", "salt", "tide", "wreck",
            "foam", "mast", "kelp", "pearl",
        ],
        "verbs": [
            "crashes", "swells", "recedes", "churns", "drifts", "pulls",
            "surges", "glitters", "roars", "whispers", "rises", "sinks",
            "clings", "breaks", "carries",
        ],
        "adjectives": [
            "deep", "briny", "restless", "grey", "foamy", "cold",
            "vast", "turbulent", "ancient", "dark", "battered", "weathered",
            "tidal", "drowned", "endless",
        ],
        "adverbs": [
            "endlessly", "deeply", "restlessly", "rhythmically", "relentlessly",
            "quietly", "powerfully", "darkly", "swiftly", "ceaselessly",
        ],
    },
}
