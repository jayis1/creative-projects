"""Three-act story architect: generates structured plot outlines."""

from __future__ import annotations

import random
from dataclasses import dataclass, field


@dataclass
class StoryBeat:
    act: int
    beat_name: str
    description: str

    def __str__(self) -> str:
        return f"[Act {self.act}] {self.beat_name}: {self.description}"


@dataclass
class Story:
    title: str
    genre: str
    premise: str
    theme: str
    beats: list[StoryBeat] = field(default_factory=list)
    protagonist: str = ""
    antagonist: str = ""

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "genre": self.genre,
            "premise": self.premise,
            "theme": self.theme,
            "protagonist": self.protagonist,
            "antagonist": self.antagonist,
            "beats": [
                {"act": b.act, "beat_name": b.beat_name, "description": b.description}
                for b in self.beats
            ],
        }

    def outline(self) -> str:
        lines = [
            f"Title: {self.title}",
            f"Genre: {self.genre}",
            f"Theme: {self.theme}",
            f"Premise: {self.premise}",
            f"Protagonist: {self.protagonist}",
            f"Antagonist: {self.antagonist}",
            "",
            "Story Beats:",
        ]
        for beat in self.beats:
            lines.append(f"  {beat}")
        return "\n".join(lines)


GENRES = [
    ("dark fantasy", "In a world where memories can be stolen and sold"),
    ("space opera", "Across a fractured interstellar civilization"),
    ("gothic mystery", "In a decaying estate where the dead refuse to stay buried"),
    ("post-apocalyptic", "In the ruins of a world that remembered too much"),
    ("steampunk adventure", "In an empire powered by clockwork and suppressed secrets"),
    ("mythic retelling", "In a land where the old gods are not dead, only sleeping"),
    ("cyberpunk thriller", "In a city where identity is currency and truth is contraband"),
    ("historical fantasy", "In an age of revolution where magic is the last forbidden weapon"),
]

THEMES = [
    "the cost of mercy in a merciless world",
    "the impossibility of going home after transformation",
    "the weight of inherited guilt",
    "the thin line between justice and vengeance",
    "the danger of getting exactly what you wished for",
    "the persistence of hope in the absence of evidence",
    "the fragility of identity under pressure",
    "the tension between freedom and responsibility",
]

# Act 1 beats — setup
ACT1_BEATS = [
    ("Opening Image", "the world in its ordinary state, before everything changes"),
    ("Inciting Incident", "the event that disrupts the protagonist's status quo and sets the story in motion"),
    ("Refusal of the Call", "the protagonist resists the change, fearing what it will cost"),
    ("Meeting the Mentor", "a guide or catalyst appears, offering wisdom, tools, or a push"),
    ("Crossing the Threshold", "the protagonist commits to the journey, leaving the old world behind"),
]

# Act 2 beats — confrontation
ACT2_BEATS = [
    ("Tests, Allies, Enemies", "the protagonist navigates the new world, forming bonds and facing challenges"),
    ("Approaching the Cave", "the protagonist nears the central ordeal, tension escalates"),
    ("The Ordeal", "the protagonist confronts their greatest fear or the story's central conflict"),
    ("Reward", "the protagonist seizes something valuable — a truth, a weapon, a reconciliation"),
    ("The Road Back", "the protagonist begins the return, but the consequences of the ordeal follow"),
]

# Act 3 beats — resolution
ACT3_BEATS = [
    ("Resurrection", "the protagonist faces a final test that demands everything they've learned"),
    ("Climax", "the decisive confrontation where the central conflict is resolved or tragically fails"),
    ("Denouement", "the aftermath: the world settles into its new shape, the cost is reckoned"),
    ("Final Image", "a closing image that mirrors the opening but transformed by the journey"),
]

TITLE_TEMPLATES = [
    "The {noun} of {place}",
    "{adjective} {noun}",
    "The Last {role}",
    "Where {things} Go to Die",
    "The Weight of {abstract}",
    "A Litany of {things}",
    "The {role}'s {abstract}",
    "Beneath the {adjective} {noun}",
]

TITLE_NOUNS = ["Ash", "Glass", "Echo", "Thorn", "Bone", "Iron", "Salt", "Ember", "Memory", "Silence", "Hollow", "Ruin"]
TITLE_PLACES = ["Vespera", "the Shattered Spire", "Emberfall", "Thornvale", "the Underway", "Driftwood Hollow", "the Quiet Expanse", "the Hollow Cathedral"]
TITLE_ADJECTIVES = ["Broken", "Forgotten", "Silent", "Hollow", "Burning", "Drowning", "Ashen", "Falling"]
TITLE_ROLES = ["Cartomancer", "Healer", "Cartographer", "Blacksmith", "Thief", "Scholar", "Wanderer", "Oracle"]
TITLE_THINGS = ["Names", "Maps", "Lanterns", "Promises", "Keys", "Mirrors", "Ghosts", "Songs"]
TITLE_ABSTRACTS = ["Mercy", "Memory", "Dust", "Silence", "Fire", "Grief", "Light", "Debt"]


class StoryArchitect:
    """Generates structured three-act story outlines."""

    def __init__(self, seed: int | None = None):
        self._rng = random.Random(seed)

    def _generate_title(self) -> str:
        template = self._rng.choice(TITLE_TEMPLATES)
        return template.format(
            noun=self._rng.choice(TITLE_NOUNS),
            place=self._rng.choice(TITLE_PLACES),
            adjective=self._rng.choice(TITLE_ADJECTIVES),
            role=self._rng.choice(TITLE_ROLES),
            things=self._rng.choice(TITLE_THINGS),
            abstract=self._rng.choice(TITLE_ABSTRACTS),
        )

    def generate(self) -> Story:
        genre_pair = self._rng.choice(GENRES)
        genre, premise_prefix = genre_pair
        theme = self._rng.choice(THEMES)
        title = self._generate_title()

        # Build premise
        premise = f"{premise_prefix}, {theme}."

        beats: list[StoryBeat] = []
        for beat_name, desc in ACT1_BEATS:
            beats.append(StoryBeat(act=1, beat_name=beat_name, description=desc))
        for beat_name, desc in ACT2_BEATS:
            beats.append(StoryBeat(act=2, beat_name=beat_name, description=desc))
        for beat_name, desc in ACT3_BEATS:
            beats.append(StoryBeat(act=3, beat_name=beat_name, description=desc))

        return Story(
            title=title,
            genre=genre,
            premise=premise,
            theme=theme,
            beats=beats,
            protagonist="",
            antagonist="",
        )