"""Context-free grammar engine with weighted rules, variable binding, and conditional expansion."""

from __future__ import annotations

import random
import re
from typing import Any


class Grammar:
    """Weighted context-free grammar with variable binding and conditional rules.

    Rules are stored as a dict of symbol -> list of (weight, expansion, condition).
    Expansions use {var} for variable references and <symbol> for non-terminal references.
    """

    _VAR_RE = re.compile(r"\{(\w+)\}")
    _SYM_RE = re.compile(r"<(\w+)>")

    def __init__(self, rules: dict[str, list] | None = None, seed: int | None = None):
        self.rules: dict[str, list[tuple[float, str, str | None]]] = {}
        self.variables: dict[str, Any] = {}
        self._rng = random.Random(seed)
        if rules:
            for sym, expansions in rules.items():
                for entry in expansions:
                    self.add_rule(sym, entry)

    def add_rule(self, symbol: str, entry: tuple | str) -> None:
        """Add a rule. entry can be a bare string (weight=1, no condition),
        a (weight, expansion) tuple, or a (weight, expansion, condition) tuple."""
        if isinstance(entry, str):
            self.rules.setdefault(symbol, []).append((1.0, entry, None))
        elif len(entry) == 2:
            weight, expansion = entry
            self.rules.setdefault(symbol, []).append((float(weight), expansion, None))
        elif len(entry) == 3:
            weight, expansion, condition = entry
            self.rules.setdefault(symbol, []).append((float(weight), expansion, condition))

    def set_var(self, name: str, value: Any) -> None:
        self.variables[name] = value

    def _check_condition(self, condition: str | None) -> bool:
        if condition is None:
            return True
        try:
            return bool(eval(condition, {"__builtins__": {}}, dict(self.variables)))
        except Exception:
            return False

    def _weighted_choice(self, symbol: str) -> str | None:
        candidates = self.rules.get(symbol, [])
        if not candidates:
            return None
        eligible = [(w, e, c) for w, e, c in candidates if self._check_condition(c)]
        if not eligible:
            eligible = candidates
        weights = [w for w, _, _ in eligible]
        total = sum(weights)
        if total <= 0:
            return eligible[0][1]
        r = self._rng.random() * total
        cumulative = 0.0
        for w, expansion, _ in eligible:
            cumulative += w
            if r <= cumulative:
                return expansion
        return eligible[-1][1]

    def expand(self, symbol: str, max_depth: int = 50) -> str:
        """Expand a non-terminal symbol into terminal text."""
        return self._expand_symbol(symbol, 0, max_depth)

    def _expand_symbol(self, symbol: str, depth: int, max_depth: int) -> str:
        if depth > max_depth:
            return ""
        expansion = self._weighted_choice(symbol)
        if expansion is None:
            return f"<{symbol}>"  # leave unresolved symbols visible
        return self._expand_text(expansion, depth + 1, max_depth)

    def _expand_text(self, text: str, depth: int, max_depth: int) -> str:
        # First, resolve variable references
        def var_sub(m):
            key = m.group(1)
            if key in self.variables:
                return str(self.variables[key])
            return m.group(0)
        text = self._VAR_RE.sub(var_sub, text)

        # Then, recursively expand non-terminal references
        def sym_sub(m):
            return self._expand_symbol(m.group(1), depth, max_depth)
        # Iterate until no more symbols (with a safety limit)
        for _ in range(10):
            new_text = self._SYM_RE.sub(sym_sub, text)
            if new_text == text:
                break
            text = new_text
        return text

    def generate(self, start: str = "start", max_depth: int = 50) -> str:
        """Generate text from a start symbol. Cleans up extra whitespace."""
        result = self.expand(start, max_depth)
        # Collapse multiple spaces, fix spacing around punctuation
        result = re.sub(r"\s+", " ", result).strip()
        result = re.sub(r"\s+([,.;:!?])", r"\1", result)
        return result


# Built-in grammar for general story fragments
BUILTIN_GRAMMAR: dict[str, list] = {
    "start": [
        "<setting_opener>. <character_intro>. <inciting_event>. <rising_action>. <climax_moment>. <resolution_line>."
    ],
    "setting_opener": [
        "In the <setting_place> of <setting_name>, where <atmosphere>",
        "The <setting_place> known as <setting_name> lay <atmosphere>",
        "Beyond the <terrain>, <setting_name> <atmosphere>",
    ],
    "setting_place": ["city", "valley", "kingdom", "forest", "desert", "archipelago", "citadel", "wasteland"],
    "setting_name": ["Aelmont", "Vespera", "Korith", "Driftwood Hollow", "the Shattered Spire", "Thornfield", "Emberfall", "the Quiet Expanse"],
    "atmosphere": [
        "shadows whispered of forgotten things",
        "the air hummed with ancient tension",
        "time moved differently than elsewhere",
        "every stone held a memory",
        "the sky burned in colors without names",
    ],
    "terrain": ["misty mountains", "glass plains", "frozen marshes", "cinder dunes", "ironwood forests"],
    "character_intro": [
        "<char_name>, a <char_role> with <char_trait>,",
        "A <char_role> named <char_name>, known for <char_trait>,",
        "<char_name> the <char_role>, bearing <char_trait>,",
    ],
    "char_name": ["Maren", "Cael", "Tova", "Brask", "Ysolde", "Devren", "Naia", "Othric"],
    "char_role": ["scholar", "wanderer", "blacksmith", "healer", "mercenary", "cartographer", "thief", "diplomat"],
    "char_trait": ["a scar that mapped a forgotten war", "eyes the color of storm light", "a voice that could calm wolves", "hands that never stopped shaking", "a map tattooed across their back"],
    "inciting_event": [
        "Then <char_name> found <found_object>, and nothing was the same",
        "The discovery of <found_object> shattered the ordinary rhythm of life",
        "Everything changed when <found_object> surfaced from the deep",
        "It began with <found_object> — unremarkable to most, devastating to <char_name>",
    ],
    "found_object": ["a letter sealed with black wax", "a compass that pointed nowhere", "a mirror showing a different room", "a key rusted shut", "a journal in their own handwriting they had never written"],
    "rising_action": [
        "<char_name> followed the trail into <danger_place>, where <danger_desc>",
        "The path led through <danger_place>, and <danger_desc>",
        "Step by step, <char_name> descended into <danger_place>, where <danger_desc>",
    ],
    "danger_place": ["the Underway", "the Flooded Library", "the Glass Maze", "the Hollow Cathedral", "the Salt Flats", "the Whispering Catacombs"],
    "danger_desc": [
        "every reflection hid a watcher",
        "the walls rearranged themselves when no one looked",
        "the silence was louder than any scream",
        "the ground remembered footsteps that were not theirs",
    ],
    "climax_moment": [
        "At the heart of it all, <char_name> faced <antagonist>, and <confrontation>",
        "<antagonist> waited at the center, and the confrontation was <confrontation>",
        "Then came the reckoning: <antagonist> and <char_name>, and <confrontation>",
    ],
    "antagonist": ["the Hollow King", "the Collector of Names", "the Mirror-self", "the Last Cartomancer", "the thing wearing their father's face"],
    "confrontation": [
        "a single choice that could not be unmade",
        "a bargain paid in memories",
        "a truth that cracked the world open",
        "a silence that finally spoke back",
    ],
    "resolution_line": [
        "In the end, <char_name> <resolution_verb>, and the <setting_place> of <setting_name> <resolution_aftermath>",
        "<char_name> <resolution_verb>, and <setting_name> would never be the same",
        "And so <char_name> <resolution_verb>, leaving <setting_name> to <resolution_aftermath>",
    ],
    "resolution_verb": ["walked away with nothing but the truth", "buried the key where no one would find it", "chose to forget on purpose", "burned the map and started again"],
    "resolution_aftermath": ["slept a little easier", "learned to live with the echo", "forgot it had ever happened", "built something new from the ruins"],
}