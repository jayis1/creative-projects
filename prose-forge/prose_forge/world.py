"""World-building generators: settings, biomes, settlements, weather moods, time periods."""

from __future__ import annotations

import random
from dataclasses import dataclass, field


@dataclass
class WorldSetting:
    name: str
    biome: str
    settlement: str
    time_period: str
    weather: str
    atmosphere: str
    notable_features: list[str]
    tension: str

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "biome": self.biome,
            "settlement": self.settlement,
            "time_period": self.time_period,
            "weather": self.weather,
            "atmosphere": self.atmosphere,
            "notable_features": self.notable_features,
            "tension": self.tension,
        }

    def description(self) -> str:
        lines = [
            f"World: {self.name}",
            f"Biome: {self.biome}",
            f"Settlement: {self.settlement}",
            f"Time Period: {self.time_period}",
            f"Weather: {self.weather}",
            f"Atmosphere: {self.atmosphere}",
            f"Notable Features: {', '.join(self.notable_features)}",
            f"Tension: {self.tension}",
        ]
        return "\n".join(lines)


BIOMES = [
    "frozen tundra", "scorched desert", "dense temperate rainforest", "floating archipelago",
    "underground cavern network", "volcanic highlands", "drowned coastal lowlands",
    "endless grassland", "crystalline salt flats", "bioluminescent deep-sea trench",
    "ash-choked wasteland", "perpetual twilight marsh",
]

SETTLEMENTS = [
    "a sprawling cliffside city carved into the rock",
    "a nomadic caravan camp that never stays in one place for long",
    "a fortress-monastery perched above the clouds",
    "a trading post built on the ruins of something older",
    "a fishing village where the boats are made from bones",
    "an underground city lit by phosphorescent fungi",
    "a floating market on lashed-together rafts",
    "a frontier town built around a single ancient well",
    "a scholarly retreat cut off from the world by design",
    "a war camp that has become permanent by accident",
]

TIME_PERIODS = [
    "a fading iron-age empire", "a renaissance of rediscovered magic",
    "a post-collapse reconstruction era", "a golden age on the edge of cracking",
    "the end of a long peace", "a period of exploration and first contact",
    "a time of plague and quarantine", "an age of revolution and upheaval",
    "a slow industrial transformation", "a period of religious schism",
]

WEATHERS = [
    "perpetual drizzle that never quite becomes rain",
    "sudden violent storms that strike without warning",
    "a constant wind that wears down everything it touches",
    "thick fog that rolls in every evening and burns off by noon",
    "long droughts broken by catastrophic floods",
    "unnatural stillness, as if the air is holding its breath",
    "ashfall from a distant volcano that never stops",
    "seasons that have lost their rhythm, winter in summer, spring in autumn",
]

ATMOSPHERES = [
    "the weight of unspoken history presses on every street corner",
    "there is a current of fear beneath the surface of daily life",
    "the people are proud but exhausted, holding together through habit",
    "strangers are watched carefully and never fully welcomed",
    "there is a manic energy, as if everyone is trying to forget something",
    "the atmosphere is one of patient endurance, of waiting for something to break",
    "beneath the routine, there is a quiet current of defiance",
    "the mood is one of cautious hope, fragile and new",
]

FEATURES = [
    "a massive monolith no one remembers building",
    "a library where the books rearrange themselves at night",
    "a market that only appears during the new moon",
    "a well that speaks in the voices of the dead",
    "a road that is longer when you walk it alone",
    "a tower with no doors that hums during storms",
    "a field of glass formed by lightning strikes",
    "a cave system that maps itself differently for each visitor",
    "a statue that weeps real salt during droughts",
    "a bridge that only appears when you're not looking for it",
    "a forest where the trees grow in perfect circles",
    "a river that flows uphill for one day each year",
    "an observatory with lenses that show the past",
    "a graveyard where the headstones face the sea, not the sun",
]

TENSIONS = [
    "a succession crisis is brewing, and every faction is choosing sides",
    "a religious schism has split the community into two armed camps",
    "a resource is running out, and no one wants to be the first to say it",
    "an old treaty is about to expire, and no one trusts the other side to renew it",
    "a series of unexplained disappearances has everyone looking at their neighbors",
    "a new discovery threatens to overturn everything the community believes about itself",
    "a foreign power is circling, and the defenses are not what they once were",
    "a prophecy is circulating, and people are starting to act on it",
    "a debt is coming due that cannot be paid",
    "the old ways are dying, and the new ways are not yet strong enough to replace them",
]

WORLD_NAMES = [
    "Aelmont", "Vespera", "Korith", "Emberfall", "Driftwood Hollow",
    "the Shattered Spire", "Thornfield", "the Quiet Expanse",
    "Hollow Reach", "Saltmere", "Greyveil", "the Cauldron",
    "Ashenmoor", "Farhaven", "the Nether Marches", "Sunderlands",
]


class WorldSeeder:
    """Generates procedural world settings for story contexts."""

    def __init__(self, seed: int | None = None):
        self._rng = random.Random(seed)

    def generate(self) -> WorldSetting:
        return WorldSetting(
            name=self._rng.choice(WORLD_NAMES),
            biome=self._rng.choice(BIOMES),
            settlement=self._rng.choice(SETTLEMENTS),
            time_period=self._rng.choice(TIME_PERIODS),
            weather=self._rng.choice(WEATHERS),
            atmosphere=self._rng.choice(ATMOSPHERES),
            notable_features=self._rng.sample(FEATURES, k=self._rng.randint(2, 4)),
            tension=self._rng.choice(TENSIONS),
        )