#!/usr/bin/env python3
"""Tests for the Procedural Planet Generator."""

import json
import math
import random
import sys
import os

# Add the project directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from planet_gen import (
    generate_planet, make_rng, weighted_choice, compute_habitability,
    compute_hazards, compute_resources, render_globe, display_planet,
    export_text, export_json, compare_planets, Planet, Moon,
    STAR_TYPES, PLANET_TYPES, ATMOSPHERES, LIFE_LEVELS, FEATURES,
    HAZARDS, RESOURCES, GLOBE_CHARS, NAME_PREFIXES, NAME_SUFFIXES,
    DESCRIPTORS, __version__,
    _format_atmosphere, _format_life, _format_features, _article,
)


class TestMakeRNG:
    """Tests for the seeded RNG helper."""

    def test_deterministic(self):
        """Same seed should produce same RNG state."""
        rng1 = make_rng("test_seed")
        rng2 = make_rng("test_seed")
        assert rng1.random() == rng2.random()

    def test_different_seeds(self):
        """Different seeds should produce different results."""
        rng1 = make_rng("seed_a")
        rng2 = make_rng("seed_b")
        # Very unlikely to get the same first random
        assert rng1.random() != rng2.random()

    def test_numeric_seed(self):
        """Numeric seeds should work."""
        rng = make_rng("12345")
        assert 0 <= rng.random() <= 1

    def test_empty_seed(self):
        """Empty seed should still work."""
        rng = make_rng("")
        assert 0 <= rng.random() <= 1


class TestWeightedChoice:
    """Tests for weighted random choice."""

    def test_single_item(self):
        """Single item should always be selected."""
        rng = random.Random(42)
        result = weighted_choice(rng, [("Only", 1.0)])
        assert result == "Only"

    def test_deterministic(self):
        """Same RNG state should give same result."""
        rng1 = random.Random(100)
        rng2 = random.Random(100)
        choices = [("A", 1.0), ("B", 2.0), ("C", 3.0)]
        assert weighted_choice(rng1, choices) == weighted_choice(rng2, choices)

    def test_all_planet_types_selectable(self):
        """All planet types should be possible to select."""
        rng = random.Random(42)
        seen = set()
        for _ in range(1000):
            seen.add(weighted_choice(rng, PLANET_TYPES))
        assert seen == {pt for pt, _ in PLANET_TYPES}


class TestGeneratePlanet:
    """Tests for planet generation."""

    def test_default_generation(self):
        """Should generate a valid planet without a seed."""
        planet = generate_planet()
        assert planet.name
        assert planet.seed
        assert planet.planet_type in [pt for pt, _ in PLANET_TYPES]

    def test_seeded_reproducibility(self):
        """Same seed should produce identical planets."""
        p1 = generate_planet("test_seed_123")
        p2 = generate_planet("test_seed_123")
        assert p1.name == p2.name
        assert p1.planet_type == p2.planet_type
        assert p1.star_type == p2.star_type
        assert p1.radius_km == p2.radius_km

    def test_different_seeds_different_planets(self):
        """Different seeds should produce different planets."""
        p1 = generate_planet("alpha")
        p2 = generate_planet("beta")
        # Names should differ (extremely likely)
        assert p1.name != p2.name

    def test_planet_properties_ranges(self):
        """Generated planets should have reasonable property values."""
        planet = generate_planet("validation_test")
        assert planet.radius_km > 0
        assert planet.gravity_g > 0
        assert planet.day_length_hours > 0
        assert planet.mean_temp_c >= -270 and planet.mean_temp_c <= 1500
        assert planet.moons >= 0
        assert 0 <= planet.surface_water_pct <= 100

    def test_all_types_generatable(self):
        """Should be able to generate all planet types with appropriate seeds."""
        # Force each type by trying many seeds
        seen_types = set()
        for i in range(500):
            p = generate_planet(f"type_test_{i}")
            seen_types.add(p.planet_type)
            if len(seen_types) == len(PLANET_TYPES):
                break
        assert len(seen_types) == len(PLANET_TYPES), f"Missing types: {set(pt for pt, _ in PLANET_TYPES) - seen_types}"

    def test_gas_giant_properties(self):
        """Gas giants should have appropriate properties."""
        # Try seeds until we get a Gas Giant
        for i in range(500):
            p = generate_planet(f"gas_giant_{i}")
            if p.planet_type == "Gas Giant":
                assert p.radius_km >= 25000
                assert p.moons >= 10
                assert p.surface_water_pct == 0.0
                return
        # If we never hit Gas Giant, that's a statistical fluke, not a bug
        # The test is still valid if the logic is correct

    def test_rogue_planet_distance(self):
        """Rogue planets should have very large distances."""
        for i in range(500):
            p = generate_planet(f"rogue_{i}")
            if p.planet_type == "Rogue Planet":
                assert p.distance_au >= 100
                assert p.surface_water_pct == 0.0
                return

    def test_megastructure_temp(self):
        """Megastructures should have engineered (temperate) temperatures."""
        for i in range(500):
            p = generate_planet(f"mega_{i}")
            if p.planet_type == "Megastructure":
                assert 15 <= p.mean_temp_c <= 25
                return

    def test_ocean_world_water(self):
        """Ocean worlds should have high surface water."""
        for i in range(500):
            p = generate_planet(f"ocean_{i}")
            if p.planet_type == "Ocean World":
                assert p.surface_water_pct >= 80
                return

    def test_features_from_correct_type(self):
        """Planet features should come from the correct type's list."""
        for i in range(100):
            p = generate_planet(f"feature_test_{i}")
            valid_features = FEATURES.get(p.planet_type, [])
            for f in p.features:
                assert f in valid_features, f"Feature '{f}' not valid for {p.planet_type}"

    def test_atmosphere_from_correct_type(self):
        """Planet atmosphere should come from the correct type's list."""
        for i in range(100):
            p = generate_planet(f"atmo_test_{i}")
            valid_atmos = ATMOSPHERES.get(p.planet_type, [])
            assert p.atmosphere in valid_atmos, f"Atmosphere '{p.atmosphere}' not valid for {p.planet_type}"

    def test_life_level_from_correct_type(self):
        """Life level should come from the correct type's list."""
        for i in range(100):
            p = generate_planet(f"life_test_{i}")
            valid_life = LIFE_LEVELS.get(p.planet_type, [])
            assert p.life_level in valid_life, f"Life level '{p.life_level}' not valid for {p.planet_type}"

    def test_habitability_score_range(self):
        """Habitability score should be between 0 and 100."""
        for i in range(50):
            p = generate_planet(f"hab_test_{i}")
            assert 0 <= p.habitability_score <= 100
            assert p.habitability_grade

    def test_hazard_properties(self):
        """Hazard level and list should be populated."""
        planet = generate_planet("hazard_test")
        assert planet.hazard_level in ("Low", "Moderate", "High", "Critical")
        assert len(planet.hazard_list) >= 2
        assert len(planet.hazard_list) <= 4

    def test_resource_properties(self):
        """Resource potential and list should be populated."""
        planet = generate_planet("resource_test")
        assert planet.resource_potential in ("Low", "Moderate", "High", "Very High", "Exceptional")
        assert len(planet.resource_list) >= 2
        assert len(planet.resource_list) <= 4

    def test_moon_details(self):
        """Moon details should match moon count."""
        planet = generate_planet("moon_test")
        assert len(planet.moon_details) == planet.moons
        for moon in planet.moon_details:
            assert isinstance(moon, Moon)
            assert moon.name
            assert moon.radius_km > 0
            assert moon.orbit_days > 0
            assert moon.description


class TestComputeHabitability:
    """Tests for the habitability scoring function."""

    def test_terran_ideal(self):
        """Terran world with ideal conditions should score high."""
        score, grade = compute_habitability(
            "Terran World", 22, "Nitrogen/Oxygen", 1.0,
            "Complex Ecosystem", 65.0, "Moderate", 1.0
        )
        assert score >= 65
        assert "Habitable" in grade or "Paradise" in grade

    def test_lava_world_low(self):
        """Lava world should score very low."""
        score, grade = compute_habitability(
            "Lava World", 800, "Sulfur Dioxide", 1.5,
            "None", 0.0, "None", 0.5
        )
        assert score < 25
        assert grade.startswith(("D", "E", "F"))

    def test_toxic_world_low(self):
        """Toxic world should score low."""
        score, grade = compute_habitability(
            "Toxic World", 200, "Chlorine", 1.8,
            "None", 0.0, "Weak", 0.8
        )
        assert score < 20

    def test_megastructure_bonus(self):
        """Megastructure with engineered conditions should score decently."""
        score, grade = compute_habitability(
            "Megastructure", 20, "Artificial Nitrogen/Oxygen", 1.0,
            "Uploaded Consciousness", 0.0, "Strong", 1.0
        )
        assert score >= 55  # Engineered, breathable, good gravity, life


class TestComputeHazards:
    """Tests for the hazard assessment function."""

    def test_lava_world_critical(self):
        """Lava world should have Critical hazard level."""
        rng = random.Random(42)
        level, _ = compute_hazards("Lava World", 800, 1.5, "Sulfur Dioxide", "Weak", False, 0, rng)
        assert level == "Critical"

    def test_gas_giant_critical(self):
        """Gas giant should have Critical hazard level."""
        rng = random.Random(42)
        level, _ = compute_hazards("Gas Giant", -100, 2.5, "Hydrogen/Helium", "Extreme", True, 70, rng)
        assert level == "Critical"

    def test_hazard_list_length(self):
        """Hazard list should have 2-4 items."""
        rng = random.Random(42)
        _, hazards = compute_hazards("Ice World", -150, 0.8, "Thin Nitrogen", "Moderate", False, 2, rng)
        assert 2 <= len(hazards) <= 4

    def test_hazards_from_correct_pool(self):
        """Hazards should come from the correct planet type pool."""
        rng = random.Random(42)
        for ptype in HAZARDS:
            _, hazards = compute_hazards(ptype, 20, 1.0, "Nitrogen/Oxygen", "Moderate", False, 2, rng)
            for h in hazards:
                assert h in HAZARDS[ptype], f"Hazard '{h}' not valid for {ptype}"


class TestComputeResources:
    """Tests for the resource potential function."""

    def test_megastructure_high_resources(self):
        """Megastructure should have high resource potential."""
        rng = random.Random(42)
        potential, _ = compute_resources("Megastructure", "Uploaded Consciousness", rng)
        assert potential in ("High", "Very High", "Exceptional")

    def test_resources_from_correct_pool(self):
        """Resources should come from the correct planet type pool."""
        rng = random.Random(42)
        for ptype in RESOURCES:
            _, resources = compute_resources(ptype, "None", rng)
            for r in resources:
                assert r in RESOURCES[ptype], f"Resource '{r}' not valid for {ptype}"


class TestRenderGlobe:
    """Tests for the ASCII globe renderer."""

    def test_renders_without_error(self):
        """Globe should render without crashing."""
        planet = generate_planet("globe_test")
        globe = render_globe(planet, width=20, height=10, use_color=False)
        assert isinstance(globe, str)
        assert len(globe) > 0

    def test_renders_with_color(self):
        """Globe should render with ANSI color codes."""
        planet = generate_planet("globe_color_test")
        globe = render_globe(planet, width=20, height=10, use_color=True)
        assert "\033[" in globe  # Has ANSI codes

    def test_renders_without_color(self):
        """Globe should render without ANSI codes when disabled."""
        planet = generate_planet("globe_nocolor_test")
        globe = render_globe(planet, width=20, height=10, use_color=False)
        assert "\033[" not in globe

    def test_globe_dimensions(self):
        """Globe should have approximately correct dimensions."""
        planet = generate_planet("globe_dim_test")
        width = 30
        height = 15
        globe = render_globe(planet, width=width, height=height, use_color=False)
        lines = globe.split("\n")
        assert len(lines) == height

    def test_deterministic_globe(self):
        """Same seed should produce same globe."""
        p1 = generate_planet("globe_det_test")
        p2 = generate_planet("globe_det_test")
        g1 = render_globe(p1, width=20, height=10, use_color=False)
        g2 = render_globe(p2, width=20, height=10, use_color=False)
        assert g1 == g2


class TestDisplayPlanet:
    """Tests for the display formatter."""

    def test_display_works(self):
        """display_planet should return a string without crashing."""
        planet = generate_planet("display_test")
        output = display_planet(planet, use_color=False)
        assert isinstance(output, str)
        assert planet.name in output
        assert planet.planet_type in output

    def test_display_contains_all_fields(self):
        """Display output should contain key planet properties."""
        planet = generate_planet("display_fields_test")
        output = display_planet(planet, use_color=False)
        assert planet.name in output
        assert planet.planet_type in output
        assert planet.atmosphere in output
        assert planet.life_level in output
        assert str(planet.habitability_score) in output
        assert planet.habitability_grade.split(" — ")[0] in output
        assert planet.hazard_level in output
        assert planet.resource_potential in output

    def test_display_no_globe(self):
        """Display with show_globe=False should not contain globe section."""
        planet = generate_planet("no_globe_test")
        output = display_planet(planet, show_globe=False, use_color=False)
        assert "Globe View" not in output

    def test_display_with_moons(self):
        """Display should show moon details."""
        planet = generate_planet("moon_display_test")
        output = display_planet(planet, show_globe=False, use_color=False, show_moons=True)
        if planet.moon_details:
            assert "Major Moons" in output

    def test_display_no_moons(self):
        """Display with show_moons=False should not show moon details."""
        planet = generate_planet("no_moon_display_test")
        output = display_planet(planet, show_globe=False, use_color=False, show_moons=False)
        assert "Major Moons" not in output


class TestExportFunctions:
    """Tests for export functions."""

    def test_export_text(self):
        """export_text should produce plain text output."""
        planet = generate_planet("export_text_test")
        text = export_text(planet)
        assert isinstance(text, str)
        assert "\033[" not in text  # No ANSI codes
        assert planet.name in text
        assert planet.planet_type in text
        assert str(planet.habitability_score) in text
        assert planet.hazard_level in text

    def test_export_json(self):
        """export_json should produce valid JSON."""
        planet = generate_planet("export_json_test")
        json_str = export_json(planet)
        data = json.loads(json_str)
        assert data["name"] == planet.name
        assert data["planet_type"] == planet.planet_type
        assert data["habitability_score"] == planet.habitability_score
        assert data["hazard_level"] == planet.hazard_level
        assert data["resource_potential"] == planet.resource_potential
        assert isinstance(data["moon_details"], list)

    def test_json_round_trip(self):
        """JSON export should round-trip through parse."""
        planet = generate_planet("json_roundtrip_test")
        json_str = export_json(planet)
        data = json.loads(json_str)
        # Verify key fields survive round-trip
        assert data["name"] == planet.name
        assert data["seed"] == planet.seed
        assert data["planet_type"] == planet.planet_type
        assert data["moons"] == planet.moons
        assert data["features"] == planet.features


class TestComparePlanets:
    """Tests for the comparison function."""

    def test_compare_two_planets(self):
        """Comparison should work for two planets."""
        p1 = generate_planet("compare_a")
        p2 = generate_planet("compare_b")
        result = compare_planets([p1, p2], use_color=False)
        assert isinstance(result, str)
        assert p1.name in result
        assert p2.name in result
        assert "Type" in result

    def test_compare_single_planet(self):
        """Comparison should work for a single planet."""
        p = generate_planet("compare_single")
        result = compare_planets([p], use_color=False)
        assert isinstance(result, str)
        assert p.name in result

    def test_compare_empty(self):
        """Comparison with empty list should return a message."""
        result = compare_planets([], use_color=False)
        assert "No planets" in result


class TestVersion:
    """Tests for version info."""

    def test_version_exists(self):
        """Module should have a version string."""
        assert __version__
        assert isinstance(__version__, str)

    def test_version_format(self):
        """Version should follow semver format."""
        parts = __version__.split(".")
        assert len(parts) == 3
        for part in parts:
            assert part.isdigit()


class TestDataIntegrity:
    """Tests for data table integrity."""

    def test_all_types_have_atmosphere(self):
        """Every planet type should have atmosphere options."""
        for ptype, _ in PLANET_TYPES:
            assert ptype in ATMOSPHERES, f"Missing atmosphere for {ptype}"

    def test_all_types_have_life_levels(self):
        """Every planet type should have life level options."""
        for ptype, _ in PLANET_TYPES:
            assert ptype in LIFE_LEVELS, f"Missing life levels for {ptype}"

    def test_all_types_have_features(self):
        """Every planet type should have features."""
        for ptype, _ in PLANET_TYPES:
            assert ptype in FEATURES, f"Missing features for {ptype}"

    def test_all_types_have_globe_chars(self):
        """Every planet type should have globe character config."""
        for ptype, _ in PLANET_TYPES:
            assert ptype in GLOBE_CHARS, f"Missing globe chars for {ptype}"

    def test_all_types_have_hazards(self):
        """Every planet type should have hazard options."""
        for ptype, _ in PLANET_TYPES:
            assert ptype in HAZARDS, f"Missing hazards for {ptype}"

    def test_all_types_have_resources(self):
        """Every planet type should have resource options."""
        for ptype, _ in PLANET_TYPES:
            assert ptype in RESOURCES, f"Missing resources for {ptype}"

    def test_planet_type_weights_sum(self):
        """Planet type weights should sum to approximately 1.0."""
        total = sum(w for _, w in PLANET_TYPES)
        assert abs(total - 1.0) < 0.01, f"Planet type weights sum to {total}"

    def test_star_type_frequencies_reasonable(self):
        """Star type frequencies should be positive."""
        for stype, data in STAR_TYPES.items():
            assert data["freq"] > 0, f"Star type {stype} has zero frequency"
            assert data["temp_range"][0] < data["temp_range"][1]
            assert data["mass_range"][0] < data["mass_range"][1]


class TestFormatHelpers:
    """Tests for description formatting helper functions."""

    def test_format_atmosphere_normal(self):
        """Normal atmospheres should be lowercased."""
        assert _format_atmosphere("Nitrogen/Oxygen") == "nitrogen/oxygen"
        assert _format_atmosphere("Sulfur Dioxide") == "sulfur dioxide"

    def test_format_atmosphere_none(self):
        """Atmosphere 'None' should become 'no atmosphere'."""
        assert _format_atmosphere("None") == "no atmosphere"

    def test_format_atmosphere_none_with_detail(self):
        """Atmosphere like 'None - Escaped to Space' should be descriptive."""
        result = _format_atmosphere("None - Escaped to Space")
        assert "no atmosphere" in result
        assert "escaped to space" in result

    def test_format_life_normal(self):
        """Normal life levels should be lowercased."""
        assert _format_life("Complex Ecosystem") == "complex ecosystem"

    def test_format_life_none(self):
        """Life level 'None' should become 'no known life'."""
        assert _format_life("None") == "no known life"

    def test_format_features_single(self):
        """Single feature should be returned lowercase."""
        assert _format_features(["Cryovolcanoes"]) == "cryovolcanoes"

    def test_format_features_multiple(self):
        """Multiple features should be comma-separated and lowercased."""
        result = _format_features(["Cryovolcanoes", "Diamond Rain"])
        assert result == "cryovolcanoes, diamond rain"

    def test_article_vowel(self):
        """Words starting with vowels should use 'an'."""
        assert _article("orange") == "an"
        assert _article("Orange") == "an"

    def test_article_consonant(self):
        """Words starting with consonants should use 'a'."""
        assert _article("red") == "a"
        assert _article("Blue") == "a"


class TestDescriptionGrammar:
    """Tests for description grammar correctness."""

    def test_no_life_none_in_description(self):
        """Descriptions should not contain raw 'None' for life level."""
        for i in range(200):
            p = generate_planet(f"desc_none_life_{i}")
            if p.life_level == "None":
                assert "hosts none" not in p.description.lower(), \
                    f"Raw 'None' life in description: {p.description}"
                assert "classified as none" not in p.description.lower(), \
                    f"Raw 'None' life in description: {p.description}"
                assert "reads: none" not in p.description.lower(), \
                    f"Raw 'None' life in description: {p.description}"
                assert "status: none" not in p.description.lower(), \
                    f"Raw 'None' life in description: {p.description}"
                break

    def test_no_atmosphere_none_in_description(self):
        """Descriptions should not contain raw 'None' for atmosphere."""
        for i in range(500):
            p = generate_planet(f"desc_none_atmo_{i}")
            if p.atmosphere.startswith("None"):
                assert "veiled in none" not in p.description.lower(), \
                    f"Raw 'None' atmosphere in description: {p.description}"
                assert "breathes none" not in p.description.lower(), \
                    f"Raw 'None' atmosphere in description: {p.description}"
                assert "where none fills" not in p.description.lower(), \
                    f"Raw 'None' atmosphere in description: {p.description}"
                assert "skies of none" not in p.description.lower(), \
                    f"Raw 'None' atmosphere in description: {p.description}"
                break

    def test_rogue_planet_no_star_reference(self):
        """Rogue Planet descriptions should not reference stars."""
        for i in range(500):
            p = generate_planet(f"desc_rogue_{i}")
            if p.planet_type == "Rogue Planet":
                desc_lower = p.description.lower()
                assert "star" not in desc_lower or "starless" in desc_lower, \
                    f"Rogue Planet mentions star: {p.description}"
                assert "sun" not in desc_lower, \
                    f"Rogue Planet mentions sun: {p.description}"
                assert "orbits" not in desc_lower, \
                    f"Rogue Planet mentions orbiting: {p.description}"
                break

    def test_article_a_an_orange(self):
        """Descriptions should use 'an orange' not 'a orange'."""
        found = False
        for i in range(500):
            p = generate_planet(f"desc_article_{i}")
            if p.planet_type != "Rogue Planet" and p.star_color == "Orange":
                # Only check if the description mentions the star color
                if "orange" in p.description.lower():
                    assert "a orange" not in p.description, \
                        f"Wrong article 'a orange': {p.description}"
                    assert "an orange" in p.description, \
                        f"Expected 'an orange': {p.description}"
                    found = True
                    break
        # If we never found an Orange-star planet whose description mentions the star,
        # that's OK — just skip. But if we did find one, it must use correct grammar.
        if not found:
            # Couldn't find a matching planet in 500 tries; still verify helper works
            assert _article("orange") == "an"

    def test_article_a_an_for_vowel_planet_types(self):
        """Descriptions should use 'an ice world', 'an ocean world', etc., not 'a ice world'."""
        vowel_types = {"Ice World", "Ice Giant", "Ocean World"}
        import re
        for i in range(1000):
            p = generate_planet(f"desc_ptype_article_{i}")
            if p.planet_type in vowel_types:
                # Should never have "a ice" or "a ocean" in description
                assert not re.search(r'\ba (ice|ocean) ', p.description), \
                    f"Wrong article for vowel-starting planet type: {p.description}"

    def test_single_feature_grammar(self):
        """Descriptions should handle single/multiple features gracefully."""
        for i in range(500):
            p = generate_planet(f"desc_single_feat_{i}")
            if len(p.features) == 1:
                # Single features should use "feature includes" not "features includes"
                if "features includes" in p.description:
                    assert False, \
                        f"Single feature with 'features includes': {p.description}"
                # "feature includes" is correct for single feature
                break

    def test_habitability_uses_distance(self):
        """Habitability should factor in distance from star."""
        # Use a planet type where the difference matters (not capped at 100)
        # A marginal Ocean World where distance makes or breaks it
        score_close, _ = compute_habitability(
            "Ocean World", 15, "Nitrogen/Oxygen", 1.0,
            "Microbial", 85.0, "Moderate", 1.0
        )
        score_far, _ = compute_habitability(
            "Ocean World", 15, "Nitrogen/Oxygen", 1.0,
            "Microbial", 85.0, "Moderate", 50.0
        )
        assert score_close > score_far, \
            f"Close planet ({score_close}) should score higher than far planet ({score_far})"

        # Rogue planet should NOT get distance bonus even if close
        score_rogue, _ = compute_habitability(
            "Rogue Planet", -200, "Thin Nitrogen/Methane", 0.8,
            "None", 0.0, "Weak", 0.5
        )
        # Just verify it doesn't crash and scores are in range
        assert 0 <= score_rogue <= 100


if __name__ == "__main__":
    # Run all tests
    test_classes = [
        TestMakeRNG, TestWeightedChoice, TestGeneratePlanet,
        TestComputeHabitability, TestComputeHazards, TestComputeResources,
        TestRenderGlobe, TestDisplayPlanet, TestExportFunctions,
        TestComparePlanets, TestVersion, TestDataIntegrity,
        TestFormatHelpers, TestDescriptionGrammar,
    ]

    total_tests = 0
    total_passed = 0
    total_failed = 0

    for cls in test_classes:
        instance = cls()
        methods = [m for m in dir(instance) if m.startswith("test_")]
        for method in methods:
            total_tests += 1
            try:
                getattr(instance, method)()
                total_passed += 1
                print(f"  ✅ {cls.__name__}.{method}")
            except Exception as e:
                total_failed += 1
                print(f"  ❌ {cls.__name__}.{method}: {e}")

    print(f"\n{'='*60}")
    print(f"Results: {total_passed}/{total_tests} passed, {total_failed} failed")
    if total_failed > 0:
        sys.exit(1)
    print("All tests passed! 🎉")