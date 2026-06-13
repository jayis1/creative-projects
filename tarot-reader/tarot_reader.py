#!/usr/bin/env python3
"""
✨ CLI Tarot Reader ✨
A beautifully rendered terminal tarot card reader with ASCII art cards,
multiple spreads, full interpretations, and dramatic reveal animations.

Features:
  - Full 78-card Rider-Waite–style deck (22 Major + 56 Minor Arcana)
  - 5 spread types (Single, Three Card, Celtic Cross, Relationship, Decision)
  - ASCII art card rendering with reversed card flipping
  - Elemental synthesis and astrological associations
  - Interactive browsing, card lookup, JSON output, and save-to-file
  - Seeded RNG for reproducible readings
  - Non-interactive / pipe-friendly mode

Usage:
  python3 tarot_reader.py                  # Interactive mode
  python3 tarot_reader.py --quick          # Quick three-card reading
  python3 tarot_reader.py --daily          # Card of the day
  python3 tarot_reader.py --card "Death"   # Look up a specific card
  python3 tarot_reader.py --quick --json   # Machine-readable output
"""

import random
import sys
import time
import math
import os
import json
import unicodedata
from datetime import datetime


def _display_width(text):
    """Return the visual display width of *text* in terminal columns.

    East-Asian wide characters (including most emoji) count as 2 columns;
    combining marks and zero-width characters count as 0; everything else
    counts as 1.  This is a lightweight alternative to pulling in the
    ``wcwidth`` package.
    """
    width = 0
    for ch in text:
        cat = unicodedata.category(ch)
        # Combining marks, surrogates, control chars, zero-width joiners, etc.
        if cat.startswith(("M", "C")) or ch in ("\u200d", "\u200c", "\u200b", "\ufeff"):
            continue
        ea = unicodedata.east_asian_width(ch)
        width += 2 if ea in ("W", "F") else 1
    return width


def _pad_to_width(text, target_width, align="center"):
    """Pad *text* so its *display* width equals *target_width*.

    Because emoji/wide chars make ``len()`` unreliable, this calculates
    padding based on display width.  *align* can be ``"center"``,
    ``"left"``, or ``"right"``.
    """
    dw = _display_width(text)
    gap = target_width - dw
    if gap <= 0:
        return text[:len(text)]  # already fits (or overflow — caller truncates)
    if align == "center":
        left = gap // 2
        right = gap - left
        return " " * left + text + " " * right
    elif align == "left":
        return text + " " * gap
    elif align == "right":
        return " " * gap + text
    return text


def _truncate_to_display_width(text, max_width):
    """Truncate *text* so its display width does not exceed *max_width*.

    Returns the truncated string with ellipsis if truncation occurred.
    """
    if _display_width(text) <= max_width:
        return text
    result = ""
    for ch in text:
        if _display_width(result + ch) > max_width - 1:
            break
        result += ch
    return result + "…"

# Version follows semantic versioning — bump on releases
__version__ = "1.2.0"

# ═══════════════════════════════════════════════════════════
# TAROT DATA
# ═══════════════════════════════════════════════════════════

MAJOR_ARCANA = {
    0: {
        "name": "The Fool",
        "emoji": "🃏",
        "upright": "New beginnings, innocence, spontaneity, free spirit",
        "reversed": "Recklessness, risk-taking, naivety, foolishness",
        "story_up": "You stand at the edge of a cliff, the wind in your hair, ready to leap into the unknown. The universe whispers: trust the journey.",
        "story_rev": "You teeter on the edge, eyes closed to the danger below. Blind faith without grounding leads to a painful fall.",
        "art": [
            "     /\\     ",
            "    /  \\    ",
            "   / 🌞 \\   ",
            "  /  |   \\  ",
            " /  _|_   \\ ",
            "|   / \\    |",
            "|  |   |   |",
            "|   \\ /    |",
            " \\  ⛰⛰   / ",
            "  \\______/  ",
            "   ☆    ☆   ",
        ],
    },
    1: {
        "name": "The Magician",
        "emoji": "🎩",
        "upright": "Manifestation, resourcefulness, power, inspired action",
        "reversed": "Manipulation, poor planning, untapped talents, deception",
        "story_up": "With one hand to the sky and one to the earth, you channel the raw forces of the universe into tangible reality. You have everything you need.",
        "story_rev": "The tools lie scattered before you, but your hands are idle. Talent without focus becomes a trick — all illusion, no substance.",
        "art": [
            "    ╭──╮    ",
            "   │∞∞│    ",
            "    ╰──╯    ",
            "   ╭┤  ├╮   ",
            "   │║  ║│   ",
            "   │║  ║│   ",
            "   │╰──╯│   ",
            "   │ 🗡🗡 │   ",
            "   ╰─────╯  ",
            "    ⚡  ⚡   ",
            "   ╰────╯   ",
        ],
    },
    2: {
        "name": "The High Priestess",
        "emoji": "🌙",
        "upright": "Intuition, sacred knowledge, divine feminine, subconscious",
        "reversed": "Secrets, withdrawal, silence, disconnection from intuition",
        "story_up": "Between the pillars of light and dark, the veil parts. You sense what cannot be spoken — trust the knowing that lives beneath the surface.",
        "story_rev": "You turn away from the inner voice, drowning it in noise. The secrets you bury will sprout in darkness.",
        "art": [
            "   ☆╭──╮☆   ",
            "   ╭│🌙│╮   ",
            "  ╭╯╰──╯╰╮  ",
            "  │  ╰╯  │  ",
            "  │  ╭╮  │  ",
            "  ╰╮ │ │ ╭╯  ",
            "   │ │ │ │   ",
            "   │ │ │ │   ",
            "   ╰─╯ ╰─╯   ",
            "   📖    📖   ",
            "  ╰────────╯ ",
        ],
    },
    3: {
        "name": "The Empress",
        "emoji": "👑",
        "upright": "Femininity, beauty, nature, nurturing, abundance",
        "reversed": "Creative block, dependence, emptiness, smothering",
        "story_up": "The garden blooms at your touch. Life flows through you — creative, nurturing, abundant. You are the fertile earth itself.",
        "story_rev": "The garden withers. You give until you are empty, forgetting that the caretaker must also be cared for.",
        "art": [
            "   ╭────╮   ",
            "  ╭│ 👑 │╮  ",
            "  │╰────╯│  ",
            "  │ 🌿🌿 │  ",
            " ╭╯ 🌸🌸 ╰╮ ",
            " │  🌻🌻  │ ",
            " │ ╰────╯ │ ",
            " ╰╮      ╭╯ ",
            "  │ 🌿🌿 │  ",
            "  ╰──────╯  ",
            "   🌱  🌱    ",
        ],
    },
    4: {
        "name": "The Emperor",
        "emoji": "🏛",
        "upright": "Authority, structure, control, fatherhood, stability",
        "reversed": "Tyranny, rigidity, coldness, excessive control",
        "story_up": "Upon the throne of stone, you command with steady hand. Structure is not oppression — it is the framework upon which empires rise.",
        "story_rev": "The throne has become a cage of your own making. Authority without wisdom is merely domination.",
        "art": [
            "    👑      ",
            "   ╭┴┴╮    ",
            "  ╭│⚡│╮   ",
            "  │╰──╯│   ",
            "  │ 💪 │   ",
            " ╭╯    ╰╮  ",
            " │  🏛  │  ",
           " │  ║║  │  ",
            " ╰╮║║╭╯   ",
            "  │║║│    ",
            "  ╰╯╰╯    ",
        ],
    },
    5: {
        "name": "The Hierophant",
        "emoji": "📿",
        "upright": "Spiritual wisdom, tradition, conformity, morality",
        "reversed": "Personal beliefs, freedom, challenging status quo, nonconformity",
        "story_up": "The ancient texts hold more than rules — they hold the collected wisdom of those who walked before. Bow not to the person, but to the truth they carry.",
        "story_rev": "The old ways crumble because they cannot hold your truth. You must forge a path that honors the spirit, not just the letter.",
        "art": [
            "   ╭────╮   ",
            "  ╭│ 📿 │╮  ",
            "  │╰──╭╯│  ",
            "  │ ✝  │  ",
            " ╭╯    ╰╮  ",
            " │  👁  │  ",
            " │ ╰──╯ │  ",
            " ╰╮ 🔑 ╭╯  ",
            "  │    │   ",
            "  ╰────╯   ",
            "   ☩  ☩    ",
        ],
    },
    6: {
        "name": "The Lovers",
        "emoji": "💕",
        "upright": "Love, harmony, relationships, values alignment, choices",
        "reversed": "Disharmony, imbalance, misalignment, indecision",
        "story_up": "Two become one mirror, reflecting each other's light. The choice before you is not between paths, but between fear and love.",
        "story_rev": "You stand between two mirrors, seeing fractured reflections. The heart knows, but the mind refuses to choose.",
        "art": [
            "   💕  💕   ",
            "  ╭╯╰╮╭╯╰  ",
            "  │ 👤│👤 │  ",
            "  │  ╰╯  │  ",
            "  │  ╭╮  │  ",
            "  │  ││  │  ",
            "  ╰╮ ││ ╭╯  ",
            "   │ ││ │   ",
            "   │ 🏹 │   ",
            "   ╰────╯   ",
            "    🍎  🍎   ",
        ],
    },
    7: {
        "name": "The Chariot",
        "emoji": "⚡",
        "upright": "Control, willpower, success, determination, action",
        "reversed": "Lack of control, aggression, no direction, powerlessness",
        "story_up": "You grip the reins with iron will. Opposing forces obey your command because your resolve is unbreakable. Forward — always forward.",
        "story_rev": "The horses pull in different directions, and the chariot spins. Will without wisdom is merely force.",
        "art": [
            "   ╭────╮   ",
            "  ╭│ ⭐ │╮  ",
            "  │╰──╭╯│  ",
            "  │  ║  │  ",
            " ╭╯ ╰╯ ╰╮  ",
            " │ 🐴🐴 │  ",
            " │  ║║  │  ",
           " │  ╰╯  │  ",
            " ╰╮ ⚡ ╭╯  ",
            "  │    │   ",
            "  ╰────╯   ",
        ],
    },
    8: {
        "name": "Strength",
        "emoji": "🦁",
        "upright": "Inner strength, bravery, compassion, focus, self-control",
        "reversed": "Self-doubt, weakness, insecurity, raw emotion, vulnerability",
        "story_up": "The lion bows not to force, but to love. True strength is not domination — it is the gentle hand that calms the beast within.",
        "story_rev": "The beast roars uncontrolled, or perhaps it cowers in the corner. Either way, the balance of power has shifted against you.",
        "art": [
            "   ╭────╮   ",
            "  ╭│ ∞  │╮  ",
            "  │╰──╭╯│  ",
            "  │ 🙏 │  ",
            " ╭╯    ╰╮  ",
            " │  🦁  │  ",
            " │  🌿  │  ",
            " │ ╰──╯ │  ",
            " ╰╮    ╭╯  ",
            "  │ ⛰⛰ │  ",
            "  ╰────╯   ",
        ],
    },
    9: {
        "name": "The Hermit",
        "emoji": "🏔",
        "upright": "Soul-searching, introspection, solitude, inner guidance",
        "reversed": "Isolation, loneliness, withdrawal, lost your way",
        "story_up": "High on the mountain, the lantern casts just enough light for the next step. You seek not answers, but the right questions.",
        "story_rev": "The cave is warm, but you've stayed too long. Solitude becomes exile when the light within dims to darkness.",
        "art": [
            "      🏔    ",
            "     /  \\   ",
            "    / ⚫ \\  ",
            "   /      \\  ",
            "  │  🕯   │  ",
            "  │   👤   │  ",
            "  │  ╭╮   │  ",
            "  │  ││   │  ",
            "  ╰╮ ││  ╭╯  ",
            "   │ ││ │   ",
            "   ╰─╯╰─╯   ",
        ],
    },
    10: {
        "name": "Wheel of Fortune",
        "emoji": "🎡",
        "upright": "Good luck, karma, life cycles, destiny, turning point",
        "reversed": "Bad luck, resistance to change, breaking cycles, external forces",
        "story_up": "The great wheel turns, and what was down rises up. You stand at the axis of change — fortune favors those who flow with the turning.",
        "story_rev": "You grip the wheel, trying to stop its turning. But resistance only makes the spin more violent when it finally releases.",
        "art": [
            "   ╭────╮   ",
            "  ╭│ 🎡 │╮  ",
            "  │ │⟳│ │  ",
            "  │ │⚡│ │  ",
           "  │ ╰──╯ │  ",
           "  │  ✦  │  ",
           "  │ 🐍  │  ",
            "  │  ⚡  │  ",
            "  ╰╮  ╭╯   ",
            "   │ ✦ │    ",
            "   ╰───╯    ",
        ],
    },
    11: {
        "name": "Justice",
        "emoji": "⚖",
        "upright": "Justice, fairness, truth, cause and effect, law",
        "reversed": "Unfairness, lack of accountability, dishonesty, lawlessness",
        "story_up": "The scales balance with perfect precision. Every action has its weight, every choice its consequence. Truth cannot be argued away.",
        "story_rev": "The scales tip — someone has placed a thumb upon them. When justice is denied, imbalance festers until it erupts.",
        "art": [
            "   ╭────╮   ",
            "  ╭│ ⚖  │╮  ",
            "  │╰──╭╯│  ",
            "  │  👁  │  ",
            " ╭╯    ╰╮  ",
            " │  ══  │  ",
            " │  ║║  │  ",
           " │  ║║  │  ",
            " ╰╮ ║║ ╭╯  ",
            "  │ 🗡 │   ",
            "  ╰────╯   ",
        ],
    },
    12: {
        "name": "The Hanged Man",
        "emoji": "🙃",
        "upright": "Surrender, letting go, new perspectives, enlightenment",
        "reversed": "Delays, resistance, stalling, indecision, unnecessary sacrifice",
        "story_up": "Suspended between worlds, you see everything upside down — and finally, it makes sense. Surrender is not defeat; it is seeing with new eyes.",
        "story_rev": "You hang there by choice, afraid to come down. What was once enlightenment has become an excuse to avoid moving forward.",
        "art": [
            "      |      ",
            "     ╱╲     ",
            "    ╱  ╲    ",
            "   ╱ 👁  ╲   ",
            "  ╱  |   ╲  ",
            " ╱  ╱╲   ╲ ",
            "   ╱  ╲     ",
            "  ╱ ✦  ╲    ",
            " ╱  ✦   ╲   ",
            "╱___✦____╲  ",
            "    🌟      ",
        ],
    },
    13: {
        "name": "Death",
        "emoji": "💀",
        "upright": "Endings, change, transformation, transition, rebirth",
        "reversed": "Resistance to change, inability to move on, stagnation",
        "story_up": "The old self crumbles to make way for the new. Death is not the end — it is the most powerful beginning. What must die so you can live?",
        "story_rev": "You cling to the husk of what was, refusing the transformation that knocks. Stagnation is a death that offers no rebirth.",
        "art": [
            "   ╭────╮   ",
            "  ╭│ 💀 │╮  ",
            "  │╰──╭╯│  ",
            "  │  ║  │  ",
            "  │  ║  │  ",
           " ╭╯  ║  ╰╮  ",
            " │ 🌹  │  ",
           " │  🦋  │  ",
            " ╰╮  ╭╯   ",
            "  │🌱│    ",
            "  ╰─╯╰─╯   ",
        ],
    },
    14: {
        "name": "Temperance",
        "emoji": "🏺",
        "upright": "Balance, moderation, patience, purpose, harmony",
        "reversed": "Imbalance, excess, self-healing, realignment, re-evaluation",
        "story_up": "Water flows between vessels, mixing fire and ice, earth and air. The middle path is not compromise — it is alchemy.",
        "story_rev": "One vessel overflows while the other runs dry. Extremes call to you from both sides, and the middle way seems impossibly far.",
        "art": [
            "   ╭────╮   ",
            "  ╭│ 🏺 │╮  ",
            "  │╰──╭╯│  ",
            "  │  👤  │  ",
           " ╭╯    ╰╮  ",
            " │ 🏺→🏺 │  ",
            " │  ∿∿  │  ",
           " │  🌈  │  ",
            " ╰╮    ╭╯  ",
            "  │ ⛰⛰ │  ",
            "  ╰────╯   ",
        ],
    },
    15: {
        "name": "The Devil",
        "emoji": "😈",
        "upright": "Shadow self, attachment, addiction, restriction, sexuality",
        "reversed": "Releasing limiting beliefs, exploring dark thoughts, detachment",
        "story_up": "The chains are loose — you could slip free at any moment. But the devil's greatest trick is convincing you that you are powerless.",
        "story_rev": "You test the chain and find it rusted through. The cage door was open all along — it was your belief that held you captive.",
        "art": [
            "   ╭────╮   ",
            "  ╭│ 😈 │╮  ",
            "  │╰──╭╯│  ",
            "  │ 🔥  │  ",
            " ╭╯  ║  ╰╮  ",
            " │ ⛓⛓ │  ",
           " │  ▽  │  ",
            " │ ⛓⛓ │  ",
            " ╰╮    ╭╯  ",
            "  │ 👁 │   ",
            "  ╰────╯   ",
        ],
    },
    16: {
        "name": "The Tower",
        "emoji": "⚡",
        "upright": "Sudden upheaval, revelation, awakening, broken pride",
        "reversed": "Avoidance, delay, fear of change, averting disaster",
        "story_up": "Lightning strikes the tower of false certainty. What you built on illusion crumbles in a single moment — and in the rubble, truth.",
        "story_rev": "You see the storm gathering but refuse to leave the tower. The disaster you avoid today returns tomorrow with greater force.",
        "art": [
            "      ⚡     ",
            "   ╭──┴──╮  ",
            "   │ 🔥 │   ",
            "   │🔥🔥│   ",
            "   │ 🔥 │   ",
           "   │🔥🔥│   ",
            "   │ 🔥 │   ",
            "   │  ║ │   ",
            "  ╭╯  ║ ╰╮  ",
            "  👤   👤   ",
            "   🌟  🌟    ",
        ],
    },
    17: {
        "name": "The Star",
        "emoji": "⭐",
        "upright": "Hope, faith, purpose, renewal, spirituality, inspiration",
        "reversed": "Lack of faith, despair, distrust, discouragement, disconnect",
        "story_up": "After the tower falls, the stars emerge. You pour healing water upon the scorched earth. Hope is not naive — it is the deepest courage.",
        "story_rev": "The stars are still there, but you've stopped looking up. Despair is not the absence of light — it is the refusal to see it.",
        "art": [
            "  ⭐     ⭐  ",
            "   ╭────╮   ",
            "  ╭│ ✨ │╮  ",
            "  │╰──╭╯│  ",
            "  │  👤  │  ",
           " ╭╯    ╰╮  ",
            " │ 💧💧 │  ",
            " │  🌊  │  ",
            " │ 🌿🌿 │  ",
            " ╰╮    ╭╯  ",
            "  ╰────╯    ",
        ],
    },
    18: {
        "name": "The Moon",
        "emoji": "🌕",
        "upright": "Illusion, fear, anxiety, subconscious, intuition",
        "reversed": "Release of fear, repressed emotion, clarity emerging",
        "story_up": "The moonlight reveals and distorts. Trust the path through the shadows — the creatures you fear are often reflections of your own unspoken truths.",
        "story_rev": "The fog begins to lift. What terrified you in moonlight looks different under the sun. Clarity comes, slowly but surely.",
        "art": [
            "   🌕       ",
            "  ╭────╮   ",
            " ╭│ 🌙 │╮  ",
            " │╰────╯│  ",
            " │ 🐺🐺 │  ",
            " │  🔀  │  ",
           " │ 🦀🦀 │  ",
            " │  💧  │  ",
            " ╰╮ 🏰 ╭╯  ",
            "  │ 🏰 │   ",
            "  ╰────╯   ",
        ],
    },
    19: {
        "name": "The Sun",
        "emoji": "☀",
        "upright": "Joy, success, celebration, positivity, vitality",
        "reversed": "Inner child, feeling down, overly optimistic, temporary sadness",
        "story_up": "The sun breaks through every cloud. Joy is not the absence of sorrow — it is the light that makes even shadows beautiful. Celebrate.",
        "story_rev": "Even the sun sets sometimes. The child within you needs permission to not be okay. Brightness will return — it always does.",
        "art": [
            "   ☀☀☀     ",
            "  ╭────╮   ",
            " ╭│ 🌻 │╮  ",
            " │╰──╭╯│  ",
            " │  👶  │  ",
           " │  🐴  │  ",
            " │ 🌻🌻 │  ",
            " │  🌻  │  ",
            " ╰╮ 🌻 ╭╯  ",
            "  │ 🌻 │   ",
            "  ╰────╯   ",
        ],
    },
    20: {
        "name": "Judgement",
        "emoji": "📯",
        "upright": "Rebirth, inner calling, absolution, reflection, reckoning",
        "reversed": "Self-doubt, refusal to learn, self-judgement, ignoring the call",
        "story_up": "The trumpet sounds, calling you to rise from the grave of your past. This is not punishment — it is the most profound second chance.",
        "story_rev": "The call echoes but you pretend not to hear. Self-judgement keeps you in the ground when you were meant to rise.",
        "art": [
            "   ╭────╮   ",
            "  ╭│ 📯 │╮  ",
            "  │╰──╭╯│  ",
            "  │  ✝  │  ",
           " ╭╯    ╰╮  ",
            " │  👤  │  ",
            " │  👤  │  ",
            " │  👤  │  ",
            " ╰╮    ╭╯  ",
            "  │ ⚰ │   ",
            "  ╰────╯   ",
        ],
    },
    21: {
        "name": "The World",
        "emoji": "🌍",
        "upright": "Completion, integration, accomplishment, travel, wholeness",
        "reversed": "Seeking closure, shortcuts, incompletion, emptiness, delays",
        "story_up": "The dancer spins at the center of everything, one with all four corners. You have walked the full circle — now a new spiral begins.",
        "story_rev": "You rush to the finish line, skipping the lessons along the way. A journey incomplete is a cycle that will return to haunt you.",
        "art": [
            "   ╭────╮   ",
            "  ╭│ 🌍 │╮  ",
            "  │╰──╭╯│  ",
            "  │  💃  │  ",
           " ╭╯    ╰╮  ",
            " │ 🌿🌿 │  ",
            " │  🦁  │  ",
            " │ 🦅🐂 │  ",
            " ╰╮    ╭╯  ",
            "  │ 🌿 │   ",
            "  ╰────╯   ",
        ],
    },
}

# Astrological & numerological associations for Major Arcana
# Based on traditional Golden Dawn / Rider-Waite correspondences
MAJOR_ARCANA_ASSOC = {
    0:  {"zodiac": "—",        "planet": "Uranus",    "element": "Air",   "number": "0 (The Fool's leap)"},
    1:  {"zodiac": "—",        "planet": "Mercury",   "element": "Air",   "number": "1 (Unity, will)"},
    2:  {"zodiac": "—",        "planet": "Moon",      "element": "Water",  "number": "2 (Duality, intuition)"},
    3:  {"zodiac": "—",        "planet": "Venus",     "element": "Earth",  "number": "3 (Creation, growth)"},
    4:  {"zodiac": "Aries",    "planet": "—",         "element": "Fire",  "number": "4 (Stability, authority)"},
    5:  {"zodiac": "Taurus",   "planet": "—",         "element": "Earth",  "number": "5 (Conflict, teaching)"},
    6:  {"zodiac": "Gemini",   "planet": "—",         "element": "Air",   "number": "6 (Harmony, choice)"},
    7:  {"zodiac": "Cancer",   "planet": "—",         "element": "Water",  "number": "7 (Will, movement)"},
    8:  {"zodiac": "Leo",      "planet": "—",         "element": "Fire",  "number": "8 (Power, mastery)"},
    9:  {"zodiac": "Virgo",    "planet": "—",         "element": "Earth",  "number": "9 (Wisdom, solitude)"},
    10: {"zodiac": "—",        "planet": "Jupiter",   "element": "Fire",  "number": "10 (Cycles, fate)"},
    11: {"zodiac": "Libra",    "planet": "—",         "element": "Air",   "number": "11 (Justice, balance)"},
    12: {"zodiac": "—",        "planet": "Neptune",   "element": "Water", "number": "12 (Surrender, perspective)"},
    13: {"zodiac": "Scorpio",  "planet": "—",         "element": "Water",  "number": "13 (Transformation, rebirth)"},
    14: {"zodiac": "Sagittarius", "planet": "—",     "element": "Fire",  "number": "14 (Temperance, alchemy)"},
    15: {"zodiac": "Capricorn","planet": "—",         "element": "Earth",  "number": "15 (Shadow, material bond)"},
    16: {"zodiac": "—",        "planet": "Mars",      "element": "Fire",  "number": "16 (Upheaval, awakening)"},
    17: {"zodiac": "Aquarius", "planet": "—",         "element": "Air",   "number": "17 (Hope, inspiration)"},
    18: {"zodiac": "Pisces",   "planet": "—",         "element": "Water",  "number": "18 (Illusion, intuition)"},
    19: {"zodiac": "—",        "planet": "Sun",       "element": "Fire",  "number": "19 (Joy, vitality)"},
    20: {"zodiac": "—",        "planet": "Pluto",     "element": "Fire",  "number": "20 (Reckoning, rebirth)"},
    21: {"zodiac": "—",        "planet": "Saturn",    "element": "Earth",  "number": "21 (Completion, wholeness)"},
}

# Zodiac compatibility for relationship spread analysis
ZODIAC_COMPAT = {
    ("Fire", "Fire"): "Both burn bright — passion and friction in equal measure.",
    ("Fire", "Air"):  "Air fans Fire's flame — intellectual spark fuels passion.",
    ("Fire", "Water"): "Steam and sizzle — creative tension, but may exhaust each other.",
    ("Fire", "Earth"): "Fire warms Earth, Earth grounds Fire — productive if patient.",
    ("Air", "Air"):   "Minds in flight — great communication, may lack emotional depth.",
    ("Air", "Water"): "Rain on the wind — imagination flows, but logic and feeling clash.",
    ("Air", "Earth"): "Wind over stone — ideas meet practicality, slow but solid.",
    ("Water", "Water"): "Deep ocean meeting deep ocean — emotional depth, risk of drowning.",
    ("Water", "Earth"): "Rain on fertile soil — nurturing, growth, slow and steady.",
    ("Earth", "Earth"): "Mountain meets mountain — rock-solid stability, risk of stagnation.",
}

SUIT_DATA = {
    "Wands": {
        "emoji": "🔥",
        "element": "Fire",
        "theme": "Passion, creativity, energy, action",
        "art_symbol": "🪵",
    },
    "Cups": {
        "emoji": "💧",
        "element": "Water",
        "theme": "Emotions, relationships, intuition, creativity",
        "art_symbol": "🏆",
    },
    "Swords": {
        "emoji": "🌬",
        "element": "Air",
        "theme": "Intellect, conflict, action, truth",
        "art_symbol": "⚔",
    },
    "Pentacles": {
        "emoji": "🌍",
        "element": "Earth",
        "theme": "Material, work, money, practical matters",
        "art_symbol": "🪙",
    },
}

COURT_MEANINGS = {
    "Page": {
        "upright": "New ideas, curiosity, exploration, message, youthfulness",
        "reversed": "Lack of direction, procrastination, learning block, immaturity",
    },
    "Knight": {
        "upright": "Action, drive, charge, idealism, impulsiveness",
        "reversed": "Restlessness, burnout, recklessness, unfocused energy",
    },
    "Queen": {
        "upright": "Maturity, nurturing, compassion, emotional security, inner power",
        "reversed": "Insecurity, jealousy, emotional manipulation, dependence",
    },
    "King": {
        "upright": "Authority, structure, control, power, responsibility, leadership",
        "reversed": "Tyranny, dictatorship, rigidity, abuse of power, manipulation",
    },
}

NUMBER_MEANINGS = {
    1: "New beginnings, opportunity, potential, raw energy",
    2: "Balance, duality, partnership, decision, waiting",
    3: "Creation, growth, manifestation, collaboration, joy",
    4: "Stability, structure, security, foundation, rest",
    5: "Conflict, change, instability, challenge, adaptation",
    6: "Harmony, balance, generosity, nostalgia, adjustment",
    7: "Reflection, assessment, spirituality, wisdom, patience",
    8: "Power, mastery, movement, transformation, progress",
    9: "Completion, fulfilment, reflection, wisdom, integration",
    10: "Completion, endings, transition, burden, culmination",
}


def generate_minor_arcana():
    """Generate all 56 Minor Arcana cards."""
    cards = {}
    for suit, suit_info in SUIT_DATA.items():
        # Ace through 10
        for num in range(1, 11):
            card_id = f"{num} of {suit}"
            symbols = suit_info["art_symbol"] * min(num, 5)
            if num > 5:
                symbols2 = suit_info["art_symbol"] * (num - 5)
            else:
                symbols2 = ""

            meaning = NUMBER_MEANINGS[num]
            suit_theme = suit_info["theme"]
            cards[card_id] = {
                "name": card_id,
                "emoji": suit_info["emoji"],
                "upright": f"{meaning} in the realm of {suit_theme.lower()}",
                "reversed": f"Blocked or distorted {meaning.lower().split(',')[0]} in the realm of {suit_theme.lower()}",
                "story_up": f"The energy of {meaning.lower().split(',')[0]} flows through the realm of {suit_theme.lower()}. A moment of {['emergence', 'duality', 'creation', 'stability', 'challenge', 'harmony', 'contemplation', 'power', 'near-completion', 'culmination'][num-1]} awaits.",
                "story_rev": f"The {meaning.lower().split(',')[0]} is blocked in the realm of {suit_theme.lower()}. Something must shift before this energy can flow freely again.",
                "art": _generate_minor_art(num, suit_info),
            }

        # Court cards
        for court, court_info in COURT_MEANINGS.items():
            card_id = f"{court} of {suit}"
            cards[card_id] = {
                "name": card_id,
                "emoji": suit_info["emoji"],
                "upright": f"{court_info['upright']} in the realm of {suit_info['theme'].lower()}",
                "reversed": f"{court_info['reversed']} in the realm of {suit_info['theme'].lower()}",
                "story_up": f"A figure of {court.lower()}ly authority enters the realm of {suit_info['theme'].lower()}. {court_info['upright'].split(',')[0]} defines their presence.",
                "story_rev": f"The {court.lower()} of {suit_info['theme'].lower()} arrives unbalanced. {court_info['reversed'].split(',')[0]} clouds their judgment.",
                "art": _generate_court_art(court, suit_info),
            }

    return cards


def _generate_minor_art(num, suit_info):
    """Generate ASCII art for numbered minor arcana cards."""
    sym = suit_info["art_symbol"]
    emoji = suit_info["emoji"]
    top = "   ╭────╮   "
    top2 = f"  ╭│{emoji}{emoji}{emoji}│╮  "
    top3 = "  │╰──╭╯│  "

    # Create visual based on number
    if num <= 3:
        symbols_line = f"  │ {sym * num}  │  "
        empty_line = "  │      │  "
        lines = [top, top2, top3, symbols_line]
        for _ in range(3):
            lines.append(empty_line)
    elif num <= 6:
        row1 = sym * 3
        row2 = sym * (num - 3) if num > 3 else ""
        pad2 = " " * (6 - len(row2)) if row2 else ""
        lines = [top, top2, top3, f"  │ {row1}  │  "]
        if row2:
            lines.append(f"  │ {row2}{pad2}│  ")
        else:
            lines.append("  │      │  ")
        lines.extend(["  │      │  "] * 3)
    else:
        row1 = sym * min(num, 5)
        remaining = num - 5
        row2 = sym * remaining if remaining > 0 else ""
        pad2 = " " * (5 - len(row2)) if row2 else ""
        lines = [top, top2, top3, f"  │{row1}  │  "]
        if row2:
            lines.append(f"  │ {row2}{pad2}│  ")
        else:
            lines.append("  │      │  ")
        lines.extend(["  │      │  "] * 3)

    lines.extend(["  ╰╮    ╭╯  ", "   ╰────╯   "])
    return lines[:11]  # Ensure exactly 11 lines


def _generate_court_art(court, suit_info):
    """Generate ASCII art for court cards."""
    sym = suit_info["art_symbol"]
    emoji = suit_info["emoji"]
    symbols = {
        "Page": "📖",
        "Knight": "🐎",
        "Queen": "👸",
        "King": "🤴",
    }
    court_sym = symbols[court]

    return [
        f"   ╭────╮   ",
        f"  ╭│{emoji}{emoji}{emoji}│╮  ",
        f"  │╰──╭╯│  ",
        f"  │  {court_sym}  │  ",
        f" ╭╯ {sym}{sym} ╰╮  ",
        f" │  {sym}{sym}  │  ",
        f" │ {court_sym}   │  ",
        f" │  {sym}{sym}  │  ",
        f" ╰╮    ╭╯  ",
        f"  │ {sym}{sym} │   ",
        f"  ╰────╯   ",
    ]


MINOR_ARCANA = generate_minor_arcana()

# ═══════════════════════════════════════════════════════════
# SPREADS
# ═══════════════════════════════════════════════════════════

SPREADS = {
    "single": {
        "name": "Single Card",
        "description": "A quick answer or daily reflection",
        "positions": ["The Card"],
    },
    "three_card": {
        "name": "Three Card Spread",
        "description": "Past / Present / Future",
        "positions": ["Past", "Present", "Future"],
    },
    "cross": {
        "name": "Celtic Cross",
        "description": "The classic 10-card deep reading",
        "positions": [
            "Present Situation",
            "Challenge / Obstacle",
            "Foundation / Past",
            "Recent Past",
            "Possible Outcome",
            "Near Future",
            "Your Approach",
            "External Influences",
            "Hopes & Fears",
            "Final Outcome",
        ],
    },
    "relationship": {
        "name": "Relationship Spread",
        "description": "Insight into a relationship dynamic",
        "positions": [
            "You",
            "The Other",
            "Foundation of the bond",
            "What connects you",
            "What separates you",
            "Strengths to draw on",
            "Challenges to face",
            "Where this is heading",
        ],
    },
    "decision": {
        "name": "Decision Spread",
        "description": "Weigh two paths to make a choice",
        "positions": [
            "The question at hand",
            "Option A — what it offers",
            "Option A — what it costs",
            "Option B — what it offers",
            "Option B — what it costs",
            "What you're not seeing",
            "The best path forward",
        ],
    },
}


# ═══════════════════════════════════════════════════════════
# CARD DRAWING & DISPLAY
# ═══════════════════════════════════════════════════════════

class TarotDeck:
    """A complete 78-card tarot deck with shuffling, drawing, and reversal logic.

    Args:
        seed: Optional RNG seed for reproducible readings. If None, uses
              time-based seed so each run is unique.
        reversal_rate: Probability (0.0–1.0) that a drawn card is reversed.
              Defaults to 0.3 (30%).
    """

    def __init__(self, seed=None, reversal_rate=0.3):
        if seed is None:
            seed = int(time.time() * 1000) % (2**32)
        self.seed = seed
        self.rng = random.Random(seed)
        self.reversal_rate = max(0.0, min(1.0, reversal_rate))
        self.cards = list(MAJOR_ARCANA.keys())
        self.minor_cards = list(MINOR_ARCANA.keys())
        self.all_cards = self.cards + self.minor_cards
        self.drawn = []

    def shuffle(self):
        """Reset the deck, clearing all drawn cards so they can be drawn again."""
        self.drawn = []

    def draw(self, count=1, major_only=False):
        """Draw *count* unique cards from the deck.

        If fewer cards remain than requested, the deck is reshuffled
        automatically so all draws are possible.

        Args:
            count: Number of cards to draw.
            major_only: If True, draw only from the 22 Major Arcana.

        Returns:
            List of card keys (int for Major, str for Minor).
        """
        pool = self.cards if major_only else self.all_cards
        available = [c for c in pool if c not in self.drawn]

        if len(available) < count:
            # Not enough unique cards left — reshuffle
            self.drawn = []
            available = pool[:]

        drawn = []
        for _ in range(count):
            if not available:
                # Edge case: pool smaller than count even after reshuffle
                break
            card = self.rng.choice(available)
            available.remove(card)
            self.drawn.append(card)
            drawn.append(card)

        return drawn

    def get_card_info(self, card_key):
        """Get card info dict by key (int for Major Arcana, str for Minor)."""
        if isinstance(card_key, int) or (isinstance(card_key, str) and card_key.isdigit()):
            return MAJOR_ARCANA[int(card_key)]
        else:
            return MINOR_ARCANA[card_key]

    def is_reversed(self):
        """Randomly determine if a card is reversed based on reversal_rate."""
        return self.rng.random() < self.reversal_rate

    def find_card(self, name_fragment):
        """Look up a card by partial name match (case-insensitive).

        Returns (card_key, card_info) for the first match, or None.
        Empty or whitespace-only strings return None.
        """
        needle = name_fragment.strip().lower()
        if not needle:
            return None
        # Check Major Arcana first
        for k, info in MAJOR_ARCANA.items():
            if needle in info["name"].lower():
                return k, info
        # Then Minor Arcana
        for k, info in MINOR_ARCANA.items():
            if needle in info["name"].lower():
                return k, info
        return None


def render_card(card_info, reversed_card=False, position_name="", width=44):
    """Render a single tarot card as ASCII art with border.

    Uses display-width-aware alignment so emoji and wide characters
    don't break the frame borders.
    """
    lines = []
    art = card_info["art"]

    # Build card frame
    frame_top = "┌" + "─" * (width - 2) + "┐"
    frame_bot = "└" + "─" * (width - 2) + "┘"
    divider = "├" + "─" * (width - 2) + "┤"

    lines.append(frame_top)

    # Position name (truncated if too long, display-width-aware centering)
    if position_name:
        inner_w = width - 4  # space between │ borders
        pos_text = _truncate_to_display_width(position_name, inner_w)
        pos_text = _pad_to_width(pos_text, inner_w, align="center")
        lines.append(f"│ {pos_text} │")
        lines.append(divider)

    # Card name — display-width-aware centering to keep frame intact
    name = card_info["name"]
    if reversed_card:
        name += " (Reversed)"
    emoji = card_info["emoji"]
    inner_name = f"{emoji} {_pad_to_width(name, width - 6 - _display_width(emoji) * 2, align='center')} {emoji}"
    # Final safety: truncate if still too wide
    if _display_width(inner_name) > width - 4:
        inner_name = _truncate_to_display_width(inner_name, width - 4)
    inner_name = _pad_to_width(inner_name, width - 4, align="center")
    lines.append(f"│ {inner_name} │")
    lines.append(divider)

    # ASCII Art — display-width-aware centering
    for art_line in art:
        if reversed_card:
            # Reverse the art visually (flip characters approximately)
            art_line = art_line[::-1]
        inner_w = width - 4
        padded = _pad_to_width(art_line, inner_w, align="center")
        # Truncate anything that still overflows (safety net)
        if _display_width(padded) > inner_w:
            padded = _truncate_to_display_width(padded, inner_w)
        padded = _pad_to_width(padded, inner_w, align="center")
        lines.append(f"│ {padded} │")

    lines.append(divider)

    # Meaning label (left-aligned, display-width-aware)
    meaning = card_info["reversed"] if reversed_card else card_info["upright"]
    meaning_label = "Reversed:" if reversed_card else "Upright:"
    label_inner = _pad_to_width(meaning_label, width - 4, align="left")
    lines.append(f"│ {label_inner} │")

    # Word-wrap the meaning — display-width-aware
    words = meaning.split()
    current_line = "│  "
    for word in words:
        test_line = current_line + (" " if current_line != "│  " else "") + word
        if _display_width(test_line) > width - 2:
            # Current line is full — pad and emit it
            # Total line = current_line + padding + "│", display width = width
            padding = width - _display_width(current_line) - 1  # -1 for the closing │
            if padding < 0:
                padding = 0
            lines.append(current_line + " " * padding + "│")
            current_line = "│  " + word
        else:
            current_line = test_line
    if current_line.strip():
        padding = width - _display_width(current_line) - 1
        if padding < 0:
            padding = 0
        lines.append(current_line + " " * padding + "│")

    lines.append(divider)

    # Story — display-width-aware word-wrap
    story = card_info["story_rev"] if reversed_card else card_info["story_up"]
    story_words = story.split()
    current_line = "│  "
    for word in story_words:
        test_line = current_line + (" " if current_line != "│  " else "") + word
        if _display_width(test_line) > width - 2:
            padding = width - _display_width(current_line) - 1
            if padding < 0:
                padding = 0
            lines.append(current_line + " " * padding + "│")
            current_line = "│  " + word
        else:
            current_line = test_line
    if current_line.strip():
        padding = width - _display_width(current_line) - 1
        if padding < 0:
            padding = 0
        lines.append(current_line + " " * padding + "│")

    lines.append(frame_bot)
    return lines


def print_slow(text, delay=0.02):
    """Print text character by character for dramatic effect."""
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    print()


def print_centered(text, width=80):
    """Print text centered in terminal."""
    print(text.center(width))


def clear_screen():
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')


def display_splash():
    """Display the tarot reader splash screen."""
    clear_screen()
    width = 60
    print()
    print_centered("╔══════════════════════════════════════════════════════════╗", width)
    print_centered("║                                                          ║", width)
    print_centered("║         ✨  C L I  T A R O T  R E A D E R  ✨              ║", width)
    print_centered("║                                                          ║", width)
    print_centered("║        The cards hold no power over you.                 ║", width)
    print_centered("║        You hold all the power over the cards.            ║", width)
    print_centered("║                                                          ║", width)
    print_centered("╚══════════════════════════════════════════════════════════╝", width)
    print()

    # Animated stars
    stars = ["✨", "⭐", "🌟", "💫", "✦", "⚝"]
    star_line = "  ".join(stars)
    print_centered(star_line, width)
    print()
    print_centered(f"  Today: {datetime.now().strftime('%A, %B %d, %Y')}", width)
    print()


def choose_spread():
    """Let user choose a spread type."""
    print_centered("Choose your spread:", 60)
    print()
    keys = list(SPREADS.keys())
    for i, key in enumerate(keys, 1):
        spread = SPREADS[key]
        card_count = len(spread["positions"])
        print(f"  {i}. {spread['name']} ({card_count} cards) — {spread['description']}")
    print(f"  {len(keys)+1}. Random Card (surprise me!)")
    print()

    while True:
        try:
            choice = input("  Your choice [1-6]: ").strip()
            if not choice:
                choice = "1"
            idx = int(choice) - 1
            if 0 <= idx < len(keys):
                return keys[idx]
            elif idx == len(keys):
                return "single"
            else:
                print("  Invalid choice. Try again.")
        except (ValueError, EOFError):
            return "three_card"


def perform_reading(spread_key, deck):
    """Perform a full tarot reading."""
    spread = SPREADS[spread_key]
    positions = spread["positions"]
    num_cards = len(positions)

    print()
    print_slow(f"  Shuffling the deck...", 0.03)
    time.sleep(0.5)
    print_slow(f"  Drawing {num_cards} card{'s' if num_cards > 1 else ''}...", 0.03)
    time.sleep(0.5)
    print_slow(f"  The {spread['name']} reveals itself...", 0.03)
    print()
    time.sleep(0.8)

    # Draw cards
    drawn_keys = deck.draw(count=num_cards)
    reversals = [deck.is_reversed() for _ in range(num_cards)]

    # Display each card
    readings = []
    for i, (card_key, is_reversed, position) in enumerate(
        zip(drawn_keys, reversals, positions)
    ):
        card_info = deck.get_card_info(card_key)

        print()
        pos_header = f"━━━ Position {i+1}: {position} ━━━"
        print_centered(pos_header, 60)
        print()

        # Dramatic pause
        print_slow(f"  Drawing for '{position}'...", 0.04)
        time.sleep(0.4)

        # Reveal
        orientation = "reversed" if is_reversed else "upright"
        print_slow(f"  The card is: {card_info['emoji']} {card_info['name']} ({orientation})", 0.03)
        print()

        # Render the card
        card_lines = render_card(card_info, is_reversed, position)
        for line in card_lines:
            print(f"  {line}")
        print()

        readings.append({
            "position": position,
            "card": card_info,
            "reversed": is_reversed,
        })

    # Summary
    print()
    print_centered("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", 60)
    print_centered("        ✨ R E A D I N G  S U M M A R Y ✨", 60)
    print_centered("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", 60)
    print()

    for r in readings:
        orient = "(Reversed)" if r["reversed"] else "(Upright)"
        print(f"  {r['position']}: {r['card']['emoji']} {r['card']['name']} {orient}")
        meaning = r["card"]["reversed"] if r["reversed"] else r["card"]["upright"]
        print(f"    → {meaning}")
        print()

    # Synthesis
    print_centered("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", 60)
    print()
    print_slow("  The cards whisper their synthesis...", 0.03)
    print()
    synthesis = generate_synthesis(readings, spread_key)
    for line in synthesis:
        print_slow(f"  {line}", 0.02)
    print()
    print_centered("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", 60)
    print()
    print_centered("  🔮 The reading is complete. 🔮", 60)
    print()

    return readings


def generate_synthesis(readings, spread_key=None):
    """Generate a synthesis interpretation of the reading.

    Includes orientation analysis, Major Arcana presence, elemental balance,
    astrological associations, and (for relationship spreads) zodiac compatibility.
    """
    lines = []

    # Handle empty readings gracefully
    if not readings:
        lines.append("No cards were drawn — the reading is empty.")
        lines.append("Shuffle the deck and try again when you're ready.")
        lines.append("")
        lines.append("Remember: the tarot is a mirror, not a map. It reflects")
        lines.append("what you already know on some level. Trust yourself first,")
        lines.append("and let the cards illuminate what was hidden in shadow.")
        return lines

    # Count orientations
    num_reversed = sum(1 for r in readings if r["reversed"])
    num_upright = len(readings) - num_reversed

    # Energy assessment
    if num_reversed > num_upright:
        lines.append("The reading carries a weight of inner blocks and energies")
        lines.append("seeking resolution. The reversals suggest that now is a time")
        lines.append("for introspection — look within before acting without.")
    elif num_upright > num_reversed and num_reversed == 0:
        lines.append("Every card stands upright — the energies flow freely and")
        lines.append("powerfully. This is a moment of clarity and alignment.")
    else:
        lines.append("A balance of upright and reversed cards speaks to a time")
        lines.append("of transition. Some aspects flow, others resist.")

    lines.append("")

    # Check for major arcana presence
    major_names = {MAJOR_ARCANA[k]["name"] for k in MAJOR_ARCANA}
    major_count = sum(1 for r in readings if r["card"]["name"] in major_names)

    if major_count >= len(readings) // 2:
        lines.append("The presence of Major Arcana cards signals that this reading")
        lines.append("touches on archetypal, fated energies — forces larger than")
        lines.append("daily concerns are at work in your life right now.")

    lines.append("")

    # Elemental balance — using MAJOR_ARCANA_ASSOC for Major Arcana cards
    elements: dict[str, float] = {"Fire": 0.0, "Water": 0.0, "Air": 0.0, "Earth": 0.0}
    for r in readings:
        name = r["card"]["name"]
        # Minor Arcana: derive element from suit
        for suit, info in SUIT_DATA.items():
            if suit in name:
                elements[info["element"]] += 1.0
        # Major Arcana: use astrological associations
        for k, info in MAJOR_ARCANA.items():
            if info["name"] == name and k in MAJOR_ARCANA_ASSOC:
                assoc = MAJOR_ARCANA_ASSOC[k]
                if assoc["element"] in elements:
                    elements[assoc["element"]] += 1.0
                break

    dominant = max(elements, key=lambda k: elements[k])
    element_vibes = {
        "Fire": "passion, urgency, and transformative energy",
        "Water": "emotion, intuition, and deep feeling",
        "Air": "intellect, communication, and mental clarity",
        "Earth": "stability, material concerns, and grounded action",
    }
    if any(v > 0 for v in elements.values()):
        lines.append(f"The dominant element is {dominant}, suggesting that")
        lines.append(f"{element_vibes[dominant]} is the current theme")

    # Astrological note for Major Arcana cards drawn
    astro_notes = []
    for r in readings:
        name = r["card"]["name"]
        for k, info in MAJOR_ARCANA.items():
            if info["name"] == name and k in MAJOR_ARCANA_ASSOC:
                assoc = MAJOR_ARCANA_ASSOC[k]
                parts = []
                if assoc["zodiac"] != "—":
                    parts.append(f"Zodiac: {assoc['zodiac']}")
                if assoc["planet"] != "—":
                    parts.append(f"Planet: {assoc['planet']}")
                if parts:
                    astro_notes.append(f"{name} — {'; '.join(parts)}")
                break

    if astro_notes:
        lines.append("")
        lines.append("Astrological influences at play:")
        for note in astro_notes:
            lines.append(f"  ✦ {note}")

    # Relationship spread compatibility analysis
    if spread_key == "relationship" and len(readings) >= 2:
        you_elem = _card_element(readings[0])
        other_elem = _card_element(readings[1])
        if you_elem and other_elem:
            key = (you_elem, other_elem)
            compat = ZODIAC_COMPAT.get(key) or ZODIAC_COMPAT.get((other_elem, you_elem))
            if compat:
                lines.append("")
                lines.append("Elemental compatibility:")
                lines.append(f"  {you_elem} meets {other_elem} — {compat}")

    lines.append("")
    lines.append("Remember: the tarot is a mirror, not a map. It reflects")
    lines.append("what you already know on some level. Trust yourself first,")
    lines.append("and let the cards illuminate what was hidden in shadow.")

    return lines


def _card_element(reading_entry):
    """Determine the element associated with a card in a reading dict."""
    name = reading_entry["card"]["name"]
    # Minor Arcana via suit
    for suit, info in SUIT_DATA.items():
        if suit in name:
            return info["element"]
    # Major Arcana via association table
    for k, info in MAJOR_ARCANA.items():
        if info["name"] == name and k in MAJOR_ARCANA_ASSOC:
            return MAJOR_ARCANA_ASSOC[k]["element"]
    return None


def daily_card(deck):
    """Draw and display a single daily card."""
    drawn = deck.draw(count=1)
    is_reversed = deck.is_reversed()
    card_info = deck.get_card_info(drawn[0])

    print()
    print_slow("  Drawing your card of the day...", 0.03)
    time.sleep(0.8)

    orient = "(Reversed)" if is_reversed else "(Upright)"
    print_slow(f"  Today's card: {card_info['emoji']} {card_info['name']} {orient}", 0.03)
    print()

    card_lines = render_card(card_info, is_reversed, "Card of the Day")
    for line in card_lines:
        print(f"  {line}")
    print()

    story = card_info["story_rev"] if is_reversed else card_info["story_up"]
    print_slow(f"  {story}", 0.02)
    print()
    print()

    return card_info


def browse_cards(deck):
    """Interactive card browser."""
    print()
    print_centered("━━━ Card Browser ━━━", 60)
    print()
    print("  1. Browse Major Arcana (22 cards)")
    print("  2. Browse Wands (14 cards)")
    print("  3. Browse Cups (14 cards)")
    print("  4. Browse Swords (14 cards)")
    print("  5. Browse Pentacles (14 cards)")
    print("  6. Draw a random card")
    print("  0. Back to main menu")
    print()

    while True:
        try:
            choice = input("  Choose [0-6]: ").strip()
        except EOFError:
            return

        if choice == "0":
            return
        elif choice == "1":
            _browse_major()
        elif choice in ("2", "3", "4", "5"):
            suits = {"2": "Wands", "3": "Cups", "4": "Swords", "5": "Pentacles"}
            _browse_suit(suits[choice])
        elif choice == "6":
            drawn = deck.draw(count=1)
            is_reversed = deck.is_reversed()
            card_info = deck.get_card_info(drawn[0])
            orient = "(Reversed)" if is_reversed else "(Upright)"
            print(f"\n  Random card: {card_info['emoji']} {card_info['name']} {orient}\n")
            for line in render_card(card_info, is_reversed, "Random Draw"):
                print(f"  {line}")
            print()
        else:
            print("  Invalid choice.")


def _browse_major():
    """Browse Major Arcana."""
    print("\n  Major Arcana:\n")
    for i in range(22):
        card = MAJOR_ARCANA[i]
        print(f"    {i:2d}. {card['emoji']} {card['name']}")
    print()

    while True:
        try:
            choice = input("  View card number [0-21] or Enter to go back: ").strip()
        except EOFError:
            return
        if not choice:
            return
        try:
            idx = int(choice)
            if 0 <= idx <= 21:
                card = MAJOR_ARCANA[idx]
                print()
                for line in render_card(card, False, "Major Arcana"):
                    print(f"  {line}")
                print()
                # Show both upright and reversed
                print_slow(f"  Upright: {card['upright']}", 0.01)
                print_slow(f"  Reversed: {card['reversed']}", 0.01)
                print()
            else:
                print("  Number out of range.")
        except ValueError:
            return


def _browse_suit(suit_name):
    """Browse a Minor Arcana suit."""
    print(f"\n  {suit_name} ({SUIT_DATA[suit_name]['emoji']} {SUIT_DATA[suit_name]['element']}): {SUIT_DATA[suit_name]['theme']}\n")

    # Ace through 10
    for i in range(1, 11):
        card = MINOR_ARCANA[f"{i} of {suit_name}"]
        print(f"    {i:2d}. {card['emoji']} {i} of {suit_name}")
    # Court cards
    for court in ["Page", "Knight", "Queen", "King"]:
        card = MINOR_ARCANA[f"{court} of {suit_name}"]
        print(f"     {court:7s} {card['emoji']} {court} of {suit_name}")
    print()

    while True:
        try:
            choice = input("  View card (e.g. '3' or 'Queen') or Enter to go back: ").strip()
        except EOFError:
            return
        if not choice:
            return
        if choice.title() in ["Page", "Knight", "Queen", "King"]:
            key = f"{choice.title()} of {suit_name}"
        elif choice.isdigit():
            num = int(choice)
            if 1 <= num <= 10:
                key = f"{num} of {suit_name}"
            else:
                print("  Number out of range (1-10).")
                continue
        else:
            return

        card = MINOR_ARCANA[key]
        print()
        for line in render_card(card, False, suit_name):
            print(f"  {line}")
        print()
        print_slow(f"  Upright: {card['upright']}", 0.01)
        print_slow(f"  Reversed: {card['reversed']}", 0.01)
        print()


def interactive_mode():
    """Main interactive loop."""
    deck = TarotDeck()

    while True:
        display_splash()

        print("  What would you like to do?")
        print()
        print("  1. 🔮 Get a reading (choose your spread)")
        print("  2. 🌟 Draw your card of the day")
        print("  3. 📖 Browse the deck")
        print("  4. 🚪 Exit")
        print()

        try:
            choice = input("  Your choice [1-4]: ").strip()
        except EOFError:
            choice = "4"

        if choice == "1":
            clear_screen()
            print_centered("✨ C H O O S E  Y O U R  S P R E A D ✨", 60)
            print()
            spread_key = choose_spread()
            clear_screen()
            readings = perform_reading(spread_key, deck)
            input("\n  Press Enter to continue...")

        elif choice == "2":
            clear_screen()
            print_centered("✨ C A R D  O F  T H E  D A Y ✨", 60)
            daily_card(deck)
            input("  Press Enter to continue...")

        elif choice == "3":
            clear_screen()
            browse_cards(deck)
            input("\n  Press Enter to continue...")

        elif choice == "4":
            print()
            print_centered("✨ May the cards illuminate your path. ✨", 60)
            print()
            break
        else:
            print("  Invalid choice.")
            time.sleep(1)


def quick_reading(spread_type="three_card", seed=None, as_json=False, save_path=None):
    """Non-interactive quick reading for scripts/pipes.

    Args:
        spread_type: Key from SPREADS dict.
        seed: Optional RNG seed for reproducibility.
        as_json: If True, output the reading as JSON.
        save_path: If set, write the reading text to this file.
    """
    deck = TarotDeck(seed=seed)
    spread = SPREADS.get(spread_type, SPREADS["three_card"])
    positions = spread["positions"]
    drawn_keys = deck.draw(count=len(positions))
    reversals = [deck.is_reversed() for _ in range(len(positions))]

    if as_json:
        cards_data = []
        for card_key, is_reversed, position in zip(drawn_keys, reversals, positions):
            card_info = deck.get_card_info(card_key)
            orient = "Reversed" if is_reversed else "Upright"
            entry = {
                "position": position,
                "name": card_info["name"],
                "emoji": card_info["emoji"],
                "orientation": orient,
                "meaning": card_info["reversed"] if is_reversed else card_info["upright"],
                "story": card_info["story_rev"] if is_reversed else card_info["story_up"],
            }
            # Add astrological data for Major Arcana
            for k, info in MAJOR_ARCANA.items():
                if info["name"] == card_info["name"] and k in MAJOR_ARCANA_ASSOC:
                    entry["astrology"] = MAJOR_ARCANA_ASSOC[k]
                    break
            cards_data.append(entry)
        output = {
            "spread": spread["name"],
            "date": datetime.now().isoformat(),
            "seed": deck.seed,
            "cards": cards_data,
        }
        json_str = json.dumps(output, indent=2, ensure_ascii=False)
        print(json_str)
        if save_path:
            try:
                with open(save_path, "w", encoding="utf-8") as f:
                    f.write(json_str)
            except OSError as e:
                print(f"Error: Could not save to '{save_path}': {e}", file=sys.stderr)
        return

    # Human-readable output
    text_lines = []
    text_lines.append(f"✨ {spread['name']} ✨")
    text_lines.append(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    text_lines.append("")

    for card_key, is_reversed, position in zip(drawn_keys, reversals, positions):
        card_info = deck.get_card_info(card_key)
        orient = "Reversed" if is_reversed else "Upright"
        meaning = card_info["reversed"] if is_reversed else card_info["upright"]
        text_lines.append(f"{position}: {card_info['emoji']} {card_info['name']} ({orient})")
        text_lines.append(f"  → {meaning}")
        story = card_info["story_rev"] if is_reversed else card_info["story_up"]
        text_lines.append(f"  {story}")
        text_lines.append("")

    full_text = "\n".join(text_lines)
    print(full_text)

    if save_path:
        try:
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(full_text)
        except OSError as e:
            print(f"Error: Could not save to '{save_path}': {e}", file=sys.stderr)


def lookup_card(name_fragment, as_json=False):
    """Look up and display a card by partial name match.

    Args:
        name_fragment: Partial or full card name to search for.
        as_json: If True, output as JSON instead of formatted text.
    """
    deck = TarotDeck()
    result = deck.find_card(name_fragment)
    if result is None:
        print(f"Card not found matching '{name_fragment}'.", file=sys.stderr)
        print("Try partial names like 'fool', 'death', '3 of cups', 'queen of wands'.", file=sys.stderr)
        sys.exit(1)

    card_key, card_info = result

    if as_json:
        entry = {
            "name": card_info["name"],
            "emoji": card_info["emoji"],
            "upright": card_info["upright"],
            "reversed": card_info["reversed"],
            "story_up": card_info["story_up"],
            "story_rev": card_info["story_rev"],
        }
        # Add astrological data for Major Arcana
        for k, info in MAJOR_ARCANA.items():
            if info["name"] == card_info["name"] and k in MAJOR_ARCANA_ASSOC:
                entry["astrology"] = MAJOR_ARCANA_ASSOC[k]
                break
        print(json.dumps(entry, indent=2, ensure_ascii=False))
        return

    print(f"\n✨ {card_info['emoji']} {card_info['name']} ✨\n")
    for line in render_card(card_info, False, "Upright"):
        print(f"  {line}")
    print()
    print(f"  Upright: {card_info['upright']}")
    print(f"  Reversed: {card_info['reversed']}")
    print()
    print(f"  Story (Upright): {card_info['story_up']}")
    print(f"  Story (Reversed): {card_info['story_rev']}")

    # Show astrological associations for Major Arcana
    for k, info in MAJOR_ARCANA.items():
        if info["name"] == card_info["name"] and k in MAJOR_ARCANA_ASSOC:
            assoc = MAJOR_ARCANA_ASSOC[k]
            print()
            print(f"  ✦ Astrology:")
            if assoc["zodiac"] != "—":
                print(f"    Zodiac: {assoc['zodiac']}")
            if assoc["planet"] != "—":
                print(f"    Planet: {assoc['planet']}")
            print(f"    Element: {assoc['element']}")
            print(f"    Numerology: {assoc['number']}")
            break
    print()


# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="✨ CLI Tarot Reader — Mystical card readings in your terminal ✨"
    )
    parser.add_argument(
        "--quick", "-q",
        action="store_true",
        help="Non-interactive mode: print a quick reading to stdout",
    )
    parser.add_argument(
        "--spread", "-s",
        choices=list(SPREADS.keys()),
        default="three_card",
        help="Spread type for quick mode (default: three_card)",
    )
    parser.add_argument(
        "--daily", "-d",
        action="store_true",
        help="Draw a single card of the day (non-interactive)",
    )
    parser.add_argument(
        "--major-only",
        action="store_true",
        help="Only draw from the Major Arcana",
    )
    parser.add_argument(
        "--version", "-V",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Show version and exit",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="RNG seed for reproducible readings (e.g. 42)",
    )
    parser.add_argument(
        "--json", "-j",
        action="store_true",
        dest="as_json",
        help="Output reading as JSON (works with --quick and --daily)",
    )
    parser.add_argument(
        "--card", "-c",
        type=str,
        default=None,
        metavar="NAME",
        help="Look up a specific card by name (e.g. 'Death', '3 of Cups')",
    )
    parser.add_argument(
        "--save",
        type=str,
        default=None,
        metavar="FILE",
        help="Save the reading text to a file",
    )
    parser.add_argument(
        "--reversal-rate",
        type=float,
        default=0.3,
        metavar="RATE",
        help="Probability of reversed cards, 0.0–1.0 (default: 0.3)",
    )

    args = parser.parse_args()

    # Card lookup mode
    if args.card:
        lookup_card(args.card, as_json=args.as_json)
        return

    if args.daily:
        deck = TarotDeck(seed=args.seed, reversal_rate=args.reversal_rate)
        drawn = deck.draw(count=1, major_only=args.major_only)
        if not drawn:
            print("Error: Could not draw a card.", file=sys.stderr)
            sys.exit(1)
        is_reversed = deck.is_reversed()
        card_info = deck.get_card_info(drawn[0])
        orient = "Reversed" if is_reversed else "Upright"
        meaning = card_info["reversed"] if is_reversed else card_info["upright"]
        story = card_info["story_rev"] if is_reversed else card_info["story_up"]

        if args.as_json:
            entry = {
                "spread": "Card of the Day",
                "date": datetime.now().isoformat(),
                "seed": deck.seed,
                "cards": [{
                    "position": "Card of the Day",
                    "name": card_info["name"],
                    "emoji": card_info["emoji"],
                    "orientation": orient,
                    "meaning": meaning,
                    "story": story,
                }],
            }
            # Add astrology for Major Arcana
            for k, info in MAJOR_ARCANA.items():
                if info["name"] == card_info["name"] and k in MAJOR_ARCANA_ASSOC:
                    entry["cards"][0]["astrology"] = MAJOR_ARCANA_ASSOC[k]
                    break
            json_str = json.dumps(entry, indent=2, ensure_ascii=False)
            print(json_str)
            if args.save:
                try:
                    with open(args.save, "w", encoding="utf-8") as f:
                        f.write(json_str)
                except OSError as e:
                    print(f"Error: Could not save to '{args.save}': {e}", file=sys.stderr)
        else:
            text = f"✨ Card of the Day ✨\n"
            text += f"{card_info['emoji']} {card_info['name']} ({orient})\n"
            text += f"  Keywords: {meaning}\n"
            text += f"  {story}\n"
            print(text)
            if args.save:
                try:
                    with open(args.save, "w", encoding="utf-8") as f:
                        f.write(text)
                except OSError as e:
                    print(f"Error: Could not save to '{args.save}': {e}", file=sys.stderr)
    elif args.quick:
        quick_reading(args.spread, seed=args.seed, as_json=args.as_json, save_path=args.save)
    else:
        interactive_mode()


if __name__ == "__main__":
    main()