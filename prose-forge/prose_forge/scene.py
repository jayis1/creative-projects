"""Narrative scene assembler: chains generated elements into coherent multi-paragraph scenes."""

from __future__ import annotations

import random
from dataclasses import dataclass

from .character import CharacterForge
from .grammar import Grammar, BUILTIN_GRAMMAR
from .story import StoryArchitect
from .world import WorldSeeder


@dataclass
class NarrativeScene:
    title: str
    setting_description: str
    characters: list[dict]
    paragraphs: list[str]

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "setting": self.setting_description,
            "characters": self.characters,
            "paragraphs": self.paragraphs,
        }

    def text(self) -> str:
        parts = [f"# {self.title}", "", f"**Setting:** {self.setting_description}", ""]
        if self.characters:
            parts.append("**Characters:**")
            for c in self.characters:
                parts.append(f"  — {c['name']}, {c['role']} ({c['motivation']})")
            parts.append("")
        for p in self.paragraphs:
            parts.append(p)
            parts.append("")
        return "\n".join(parts).strip()


class SceneAssembler:
    """Assembles a complete narrative scene from generated components."""

    def __init__(self, seed: int | None = None):
        self._rng = random.Random(seed)
        self.grammar = Grammar(BUILTIN_GRAMMAR, seed=seed)
        self.forge = CharacterForge(seed=seed)
        self.architect = StoryArchitect(seed=seed)
        self.world_seeder = WorldSeeder(seed=seed)

    def _paragraph_from_grammar(self, start_symbol: str) -> str:
        """Generate a paragraph from the grammar, splitting into sentences."""
        text = self.grammar.generate(start=start_symbol)
        # Split into sentences and rejoin with proper spacing
        sentences = [s.strip() for s in text.replace(". ", ".\n").split("\n") if s.strip()]
        return " ".join(sentences)

    def _atmosphere_paragraph(self) -> str:
        world = self.world_seeder.generate()
        return (
            f"The {world.biome} stretched out under a sky of {world.weather}. "
            f"{world.atmosphere.capitalize()}. "
            f"This was {world.name} — {world.settlement}, in {world.time_period}."
        )

    def _character_paragraph(self, characters: list[dict]) -> str:
        if not characters:
            return ""
        main = characters[0]
        return (
            f"{main['name']} stood at the center of it all — a {main['role']}, "
            f"{' and '.join(main['traits'])}. They were here because they wanted "
            f"{main['motivation']}. But {main['flaw']}, and that would cost them."
        )

    def generate(self, num_paragraphs: int = 5) -> NarrativeScene:
        """Generate a complete narrative scene."""
        story = self.architect.generate()
        cast = self.forge.generate_cast(count=self._rng.randint(2, 4))
        char_dicts = [c.to_dict() for c in cast]

        # Bind protagonist/antagonist names to grammar variables
        if char_dicts:
            self.grammar.set_var("protagonist_name", char_dicts[0]["name"])
            if len(char_dicts) > 1:
                self.grammar.set_var("antagonist_name", char_dicts[1]["name"])

        paragraphs: list[str] = []
        paragraphs.append(self._atmosphere_paragraph())
        paragraphs.append(self._character_paragraph(char_dicts))
        paragraphs.append(self._paragraph_from_grammar("inciting_event"))
        paragraphs.append(self._paragraph_from_grammar("rising_action"))
        paragraphs.append(self._paragraph_from_grammar("climax_moment"))

        # Add extra paragraphs if requested
        extra_starts = ["setting_opener", "resolution_line", "inciting_event", "rising_action"]
        while len(paragraphs) < num_paragraphs:
            sym = self._rng.choice(extra_starts)
            paragraphs.append(self._paragraph_from_grammar(sym))

        paragraphs = paragraphs[:num_paragraphs]

        world = self.world_seeder.generate()
        setting_desc = f"{world.name}, {world.biome} — {world.settlement}"

        return NarrativeScene(
            title=story.title,
            setting_description=setting_desc,
            characters=char_dicts,
            paragraphs=paragraphs,
        )