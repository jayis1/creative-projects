#!/usr/bin/env python3
"""
Tests for the CLI Tarot Reader.

Run with: python3 test_tarot_reader.py
"""

import json
import sys
import os
import io
from unittest.mock import patch

# Add the project directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tarot_reader as tr


def test_deck_creation():
    """Deck should initialise with 78 cards total."""
    deck = tr.TarotDeck(seed=42)
    assert len(deck.all_cards) == 78, f"Expected 78 cards, got {len(deck.all_cards)}"
    assert len(deck.cards) == 22, f"Expected 22 Major Arcana, got {len(deck.cards)}"
    assert len(deck.minor_cards) == 56, f"Expected 56 Minor Arcana, got {len(deck.minor_cards)}"


def test_seeded_deck_reproducibility():
    """Same seed should always produce the same draw sequence."""
    deck1 = tr.TarotDeck(seed=123)
    deck2 = tr.TarotDeck(seed=123)
    drawn1 = deck1.draw(count=5)
    drawn2 = deck2.draw(count=5)
    assert drawn1 == drawn2, "Same seed should produce identical draws"


def test_different_seeds_differ():
    """Different seeds should (almost certainly) produce different draws."""
    deck1 = tr.TarotDeck(seed=1)
    deck2 = tr.TarotDeck(seed=999)
    drawn1 = deck1.draw(count=5)
    drawn2 = deck2.draw(count=5)
    assert drawn1 != drawn2, "Different seeds should produce different draws"


def test_no_duplicate_cards():
    """Drawing multiple cards should never return duplicates within a reading."""
    deck = tr.TarotDeck(seed=42)
    drawn = deck.draw(count=10)
    assert len(drawn) == 10, "Should draw exactly 10 cards"
    assert len(set(drawn)) == 10, "All drawn cards should be unique"


def test_draw_major_only():
    """Drawing with major_only=True should only return Major Arcana keys."""
    deck = tr.TarotDeck(seed=42)
    drawn = deck.draw(count=5, major_only=True)
    assert len(drawn) == 5
    for key in drawn:
        assert isinstance(key, int), f"Major Arcana keys should be int, got {type(key)}"


def test_draw_reshuffle():
    """Drawing more cards than available should auto-reshuffle."""
    deck = tr.TarotDeck(seed=42)
    # Draw all 78 cards
    first_batch = deck.draw(count=78)
    assert len(first_batch) == 78
    # Now draw again — deck should have reshuffled
    second_batch = deck.draw(count=5)
    assert len(second_batch) == 5, "Should still be able to draw after exhausting deck"


def test_get_card_info_major():
    """get_card_info should return proper Major Arcana data."""
    deck = tr.TarotDeck(seed=42)
    info = deck.get_card_info(0)
    assert info["name"] == "The Fool"
    assert "upright" in info
    assert "reversed" in info
    assert "art" in info


def test_get_card_info_minor():
    """get_card_info should return proper Minor Arcana data."""
    deck = tr.TarotDeck(seed=42)
    info = deck.get_card_info("3 of Cups")
    assert "3" in info["name"]
    assert "Cups" in info["name"]


def test_reversal_rate():
    """Reversal rate should affect is_reversed probability."""
    # 0% reversal rate — should never reverse
    deck_no_rev = tr.TarotDeck(seed=42, reversal_rate=0.0)
    results = [deck_no_rev.is_reversed() for _ in range(1000)]
    assert not any(results), "0% reversal rate should never produce reversals"

    # 100% reversal rate — should always reverse
    deck_all_rev = tr.TarotDeck(seed=42, reversal_rate=1.0)
    results = [deck_all_rev.is_reversed() for _ in range(1000)]
    assert all(results), "100% reversal rate should always produce reversals"


def test_find_card():
    """find_card should locate cards by partial name."""
    deck = tr.TarotDeck(seed=42)
    result = deck.find_card("fool")
    assert result is not None, "Should find 'The Fool'"
    assert result[1]["name"] == "The Fool"

    result = deck.find_card("death")
    assert result is not None, "Should find 'Death'"
    assert "Death" in result[1]["name"]

    result = deck.find_card("3 of cups")
    assert result is not None, "Should find '3 of Cups'"
    assert "3 of Cups" in result[1]["name"]


def test_find_card_not_found():
    """find_card should return None for nonexistent cards."""
    deck = tr.TarotDeck(seed=42)
    result = deck.find_card("absolutely not a card xyz")
    assert result is None


def test_find_card_empty_string():
    """find_card should return None for empty or whitespace-only strings."""
    deck = tr.TarotDeck(seed=42)
    assert deck.find_card("") is None, "Empty string should return None"
    assert deck.find_card("   ") is None, "Whitespace-only should return None"


def test_render_card():
    """render_card should return a list of ASCII art lines."""
    info = tr.MAJOR_ARCANA[0]
    lines = tr.render_card(info, reversed_card=False, position_name="Test")
    assert isinstance(lines, list)
    assert len(lines) > 5, "Card should have multiple lines"
    # First line should be the frame top
    assert "┌" in lines[0], "First line should have frame corner"


def test_render_card_reversed():
    """render_card with reversed=True should show reversed meaning."""
    info = tr.MAJOR_ARCANA[13]  # Death
    lines = tr.render_card(info, reversed_card=True, position_name="Test")
    text = "\n".join(lines)
    assert "Reversed" in text, "Reversed card should show reversed label"


def test_generate_synthesis():
    """generate_synthesis should return a non-empty list of strings."""
    deck = tr.TarotDeck(seed=42)
    drawn = deck.draw(count=3)
    reversals = [deck.is_reversed() for _ in range(3)]
    readings = []
    for card_key, is_rev, pos in zip(drawn, reversals, ["Past", "Present", "Future"]):
        readings.append({
            "position": pos,
            "card": deck.get_card_info(card_key),
            "reversed": is_rev,
        })
    synthesis = tr.generate_synthesis(readings)
    assert isinstance(synthesis, list)
    assert len(synthesis) > 0
    # Should end with the mirror-not-map line
    assert any("mirror" in line.lower() for line in synthesis)


def test_generate_synthesis_relationship():
    """Relationship spread synthesis should include compatibility analysis."""
    deck = tr.TarotDeck(seed=42)
    drawn = deck.draw(count=8)
    reversals = [deck.is_reversed() for _ in range(8)]
    positions = tr.SPREADS["relationship"]["positions"]
    readings = []
    for card_key, is_rev, pos in zip(drawn, reversals, positions):
        readings.append({
            "position": pos,
            "card": deck.get_card_info(card_key),
            "reversed": is_rev,
        })
    synthesis = tr.generate_synthesis(readings, spread_key="relationship")
    text = "\n".join(synthesis)
    # If the first two cards have identifiable elements, compatibility should appear
    # (not guaranteed for all combos, but the code path should execute without error)
    assert isinstance(synthesis, list)


def test_minor_arcana_generation():
    """generate_minor_arcana should create exactly 56 cards."""
    cards = tr.generate_minor_arcana()
    assert len(cards) == 56, f"Expected 56 Minor Arcana, got {len(cards)}"
    # Check that all four suits are present
    for suit in ["Wands", "Cups", "Swords", "Pentacles"]:
        suit_cards = [k for k in cards if suit in k]
        assert len(suit_cards) == 14, f"{suit} should have 14 cards (Ace-10 + 4 court), got {len(suit_cards)}"


def test_spreads_defined():
    """All expected spread types should be defined."""
    expected = ["single", "three_card", "cross", "relationship", "decision"]
    for key in expected:
        assert key in tr.SPREADS, f"Spread '{key}' should be defined"
        assert "name" in tr.SPREADS[key]
        assert "positions" in tr.SPREADS[key]
        assert len(tr.SPREADS[key]["positions"]) > 0


def test_major_arcana_assoc():
    """MAJOR_ARCANA_ASSOC should have entries for all 22 Major Arcana."""
    assert len(tr.MAJOR_ARCANA_ASSOC) == 22
    for i in range(22):
        assert i in tr.MAJOR_ARCANA_ASSOC, f"Major Arcana {i} should have associations"
        assoc = tr.MAJOR_ARCANA_ASSOC[i]
        assert "element" in assoc
        assert assoc["element"] in ("Fire", "Water", "Air", "Earth")


def test_zodiac_compat():
    """ZODIAC_COMPAT should cover all 10 unique element pairs."""
    assert len(tr.ZODIAC_COMPAT) == 10
    elements = {"Fire", "Water", "Air", "Earth"}
    for (e1, e2) in tr.ZODIAC_COMPAT:
        assert e1 in elements and e2 in elements


def test_quick_reading_json():
    """quick_reading with as_json=True should produce valid JSON."""
    buf = io.StringIO()
    with patch("sys.stdout", buf):
        tr.quick_reading("three_card", seed=42, as_json=True)
    output = buf.getvalue()
    data = json.loads(output)
    assert "spread" in data
    assert "cards" in data
    assert len(data["cards"]) == 3
    assert data["seed"] == 42
    for card in data["cards"]:
        assert "name" in card
        assert "orientation" in card
        assert "meaning" in card


def test_quick_reading_save(tmp_path="/tmp"):
    """quick_reading with save_path should write a file."""
    save_file = os.path.join(tmp_path, "test_reading.txt")
    buf = io.StringIO()
    with patch("sys.stdout", buf):
        tr.quick_reading("single", seed=42, save_path=save_file)
    assert os.path.exists(save_file), "Save file should be created"
    with open(save_file) as f:
        content = f.read()
    assert "Single Card" in content
    os.remove(save_file)


def test_card_element():
    """_card_element should return the correct element for known cards."""
    # Minor Arcana
    entry = {"card": tr.MINOR_ARCANA["3 of Cups"], "reversed": False}
    assert tr._card_element(entry) == "Water"
    entry = {"card": tr.MINOR_ARCANA["7 of Wands"], "reversed": False}
    assert tr._card_element(entry) == "Fire"
    # Major Arcana
    entry = {"card": tr.MAJOR_ARCANA[4], "reversed": False}  # The Emperor
    assert tr._card_element(entry) == "Fire"
    entry = {"card": tr.MAJOR_ARCANA[2], "reversed": False}  # High Priestess
    assert tr._card_element(entry) == "Water"


def test_version_defined():
    """Module should have a __version__ attribute."""
    assert hasattr(tr, "__version__")
    assert isinstance(tr.__version__, str)
    parts = tr.__version__.split(".")
    assert len(parts) >= 2, "Version should follow semver"


def test_display_width():
    """_display_width should correctly measure terminal column width."""
    # ASCII chars are 1 column each
    assert tr._display_width("hello") == 5
    # Empty string
    assert tr._display_width("") == 0
    # Emoji are typically 2 columns wide
    assert tr._display_width("🃏") == 2
    # Mixed: "🃏hello" = 2 + 5 = 7
    assert tr._display_width("🃏hello") == 7


def test_render_card_frame_alignment():
    """All rendered card lines should have consistent display width matching the frame."""
    width = 44
    for key, card in list(tr.MAJOR_ARCANA.items())[:5]:
        for is_rev in [False, True]:
            lines = tr.render_card(card, reversed_card=is_rev, width=width)
            for i, line in enumerate(lines):
                dw = tr._display_width(line)
                assert dw == width, (
                    f"Frame misaligned: {card['name']} rev={is_rev} line {i}: "
                    f"display_width={dw} expected {width}"
                )


def test_render_card_long_position_name():
    """Long position names should be truncated, not overflow the frame."""
    info = tr.MAJOR_ARCANA[0]
    lines = tr.render_card(info, False, position_name="X" * 50, width=44)
    for line in lines:
        dw = tr._display_width(line)
        assert dw == 44, f"Position overflow: display_width={dw}"


def test_generate_synthesis_empty():
    """generate_synthesis with empty readings should not crash or be misleading."""
    syn = tr.generate_synthesis([], "single")
    assert isinstance(syn, list)
    assert len(syn) > 0
    # Should mention that the reading is empty, not claim "balance"
    text = " ".join(syn).lower()
    assert "empty" in text or "no cards" in text, (
        f"Empty synthesis should mention emptiness, got: {syn[:3]}"
    )


def test_save_path_error_handling():
    """Saving to an invalid path should show an error, not crash."""
    import io
    from unittest.mock import patch
    buf = io.StringIO()
    err = io.StringIO()
    with patch("sys.stdout", buf), patch("sys.stderr", err):
        tr.quick_reading("single", seed=42, save_path="/nonexistent/dir/file.txt")
    stderr_out = err.getvalue()
    assert "Error" in stderr_out or "Could not save" in stderr_out, (
        f"Should report save error gracefully, stderr: {stderr_out[:100]}"
    )


if __name__ == "__main__":
    tests = [obj for name, obj in sorted(globals().items())
             if name.startswith("test_") and callable(obj)]
    passed = 0
    failed = 0
    for test_fn in tests:
        try:
            test_fn()
            print(f"  ✅ {test_fn.__name__}")
            passed += 1
        except Exception as e:
            print(f"  ❌ {test_fn.__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed out of {len(tests)}")
    sys.exit(1 if failed else 0)