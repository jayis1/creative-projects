"""Procedural character generator with traits, motivations, arcs, and relationships."""

from __future__ import annotations

import random
from dataclasses import dataclass, field


@dataclass
class Character:
    name: str
    role: str
    age: int
    traits: list[str]
    motivation: str
    flaw: str
    arc: str
    appearance: str
    background: str
    relationships: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "role": self.role,
            "age": self.age,
            "traits": self.traits,
            "motivation": self.motivation,
            "flaw": self.flaw,
            "arc": self.arc,
            "appearance": self.appearance,
            "background": self.background,
            "relationships": self.relationships,
        }

    def summary(self) -> str:
        lines = [
            f"Name: {self.name}",
            f"Role: {self.role}",
            f"Age: {self.age}",
            f"Traits: {', '.join(self.traits)}",
            f"Motivation: {self.motivation}",
            f"Flaw: {self.flaw}",
            f"Character Arc: {self.arc}",
            f"Appearance: {self.appearance}",
            f"Background: {self.background}",
        ]
        if self.relationships:
            lines.append("Relationships:")
            for person, relation in self.relationships.items():
                lines.append(f"  — {person}: {relation}")
        return "\n".join(lines)


# Data tables for procedural generation

FIRST_NAMES_M = ["Cael", "Brask", "Devren", "Othric", "Jorin", "Tamric", "Vael", "Kestrel", "Ryn", "Hadrian"]
FIRST_NAMES_F = ["Maren", "Tova", "Ysolde", "Naia", "Eliska", "Seren", "Wren", "Iona", "Linnis", "Amaranth"]
LAST_NAMES = ["Blackwood", "Ashford", "Thornvale", "Crowley", "Stormhaven", "Ironwell", "Marsh", "Vane", "Coldwater", "Brightmore"]

ROLES = [
    "reluctant hero", "fallen noble", "street thief", "warrior monk",
    "court physician", "exiled scholar", "merchant sailor", "arena fighter",
    "forest ranger", "underground informant", "temple oracle", "desert guide",
]

TRAIT_POOL = [
    "fiercely loyal", "pathologically curious", "haunted by the past",
    "incapable of lying", "addicted to danger", "coldly rational",
    "wildly empathetic", "obsessively neat", "socially invisible",
    "physically fearless", "emotionally brittle", "strategically brilliant",
    "quietly stubborn", "dangerously charming", "morally flexible",
    "endlessly patient", "quick to anger", "slow to trust",
]

MOTIVATIONS = [
    "to find the sibling who vanished without a trace",
    "to repay a debt that can never be settled in gold",
    "to prove they are more than their family's shame",
    "to protect the one person who still believes in them",
    "to unmake the mistake that cost a hundred lives",
    "to reach a place that may not exist anymore",
    "to earn a name worth carrying",
    "to destroy the thing that was once their greatest achievement",
    "to understand why they were spared when others were not",
    "to keep a promise made to someone who is dead",
]

FLAWS = [
    "incapable of asking for help",
    "cannot let go of a grudge even when it poisons everything",
    "trusts the wrong people instinctively",
    "addicted to a substance that is slowly killing them",
    "pathologically afraid of being forgotten",
    "compulsively self-sacrificing even when unnecessary",
    "cannot distinguish mercy from weakness",
    "haunted by prophetic dreams they cannot control",
    "refuses to believe they are wrong, even when the evidence is overwhelming",
    "loves someone who will always choose someone else",
]

ARCS = [
    "from isolation to belonging, at a cost they never expected",
    "from certainty to doubt, and finally to a harder, truer faith",
    "from selfishness to sacrifice, discovering they had more to give than they knew",
    "from vengeance to forgiveness, learning the difference between justice and pain",
    "from cowardice to courage, not by becoming fearless but by learning to act afraid",
    "from arrogance to humility, stripped of everything they thought defined them",
    "from obedience to rebellion, and the loneliness that follows",
    "from despair to purpose, finding meaning in the wreckage of everything they lost",
]

APPEARANCES = [
    "tall and angular, with a scar bisecting one eyebrow",
    "short and stocky, with calloused hands and a permanent squint",
    "lean and quick, moving like someone who has spent years running",
    "pale and hollow-eyed, with ink-stained fingers",
    "weathered and broad, with sun-creased eyes that miss nothing",
    "slight and unremarkable, the kind of face you forget immediately",
    "striking and severe, with bone-white hair that appeared before age thirty",
    "wiry and restless, always in motion even when standing still",
]

BACKGROUNDS = [
    "raised in a border town that was burned and rebuilt three times before they left",
    "apprenticed to a master who disappeared one night without explanation",
    "orphaned young and raised by a religious order they never fully believed in",
    "born to wealth, lost everything in a single catastrophic betrayal",
    "grew up on ships, learning to read the sea before they could read words",
    "trained as a soldier in a war that ended before they ever saw combat",
    "self-taught in the ruins of a library that had been abandoned for a century",
    "the youngest of seven, always overlooked, always underestimated",
]


class CharacterForge:
    """Procedural character generator."""

    def __init__(self, seed: int | None = None):
        self._rng = random.Random(seed)

    def _pick_name(self) -> str:
        if self._rng.random() < 0.5:
            first = self._rng.choice(FIRST_NAMES_M)
        else:
            first = self._rng.choice(FIRST_NAMES_F)
        last = self._rng.choice(LAST_NAMES)
        return f"{first} {last}"

    def generate(self, relationships: dict[str, str] | None = None) -> Character:
        name = self._pick_name()
        role = self._rng.choice(ROLES)
        age = self._rng.randint(18, 65)
        traits = self._rng.sample(TRAIT_POOL, k=self._rng.randint(2, 4))
        motivation = self._rng.choice(MOTIVATIONS)
        flaw = self._rng.choice(FLAWS)
        arc = self._rng.choice(ARCS)
        appearance = self._rng.choice(APPEARANCES)
        background = self._rng.choice(BACKGROUNDS)
        rels = relationships or {}
        return Character(
            name=name, role=role, age=age, traits=traits,
            motivation=motivation, flaw=flaw, arc=arc,
            appearance=appearance, background=background, relationships=rels,
        )

    def generate_cast(self, count: int = 3) -> list[Character]:
        """Generate a cast of characters with inter-relationships."""
        characters: list[Character] = []
        for _ in range(count):
            characters.append(self.generate())
        # Build relationships between them
        for i, char in enumerate(characters):
            for j, other in enumerate(characters):
                if i == j:
                    continue
                rel_type = self._rng.choice([
                    "rival", "ally", "estranged family", "former lover",
                    "mentor", "debtor", "old friend", "suspected traitor",
                ])
                char.relationships[other.name] = rel_type
        return characters