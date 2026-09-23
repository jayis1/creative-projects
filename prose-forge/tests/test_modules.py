"""Tests for the name generator, story architect, world seeder, and scene assembler."""

import pytest

from prose_forge.names import NameGenerator
from prose_forge.story import StoryArchitect, Story
from prose_forge.world import WorldSeeder, WorldSetting
from prose_forge.scene import SceneAssembler, NarrativeScene


class TestNameGenerator:
    def test_generate_fantasy(self):
        gen = NameGenerator(seed=42)
        name = gen.generate("fantasy")
        assert " " in name  # has family name
        assert len(name) > 3

    def test_generate_without_family(self):
        gen = NameGenerator(seed=42)
        name = gen.generate("fantasy", with_family=False)
        assert " " not in name

    def test_generate_many(self):
        gen = NameGenerator(seed=42)
        names = gen.generate_many("sci_fi", count=5)
        assert len(names) == 5
        assert len(set(names)) == 5  # all unique

    def test_all_cultures(self):
        gen = NameGenerator(seed=42)
        for culture in gen.available_cultures:
            name = gen.generate(culture)
            assert len(name) > 2

    def test_invalid_culture(self):
        gen = NameGenerator(seed=42)
        with pytest.raises(ValueError, match="Unknown culture"):
            gen.generate("elvish")

    def test_japanese_family_first(self):
        gen = NameGenerator(seed=42)
        name = gen.generate("japanese")
        # Japanese names: family first
        parts = name.split()
        assert len(parts) == 2

    def test_reproducible(self):
        g1 = NameGenerator(seed=50)
        g2 = NameGenerator(seed=50)
        assert g1.generate("fantasy") == g2.generate("fantasy")


class TestStoryArchitect:
    def test_generate_story(self):
        arch = StoryArchitect(seed=42)
        story = arch.generate()
        assert isinstance(story, Story)
        assert story.title
        assert story.genre
        assert story.premise
        assert story.theme
        assert len(story.beats) == 14  # 5 + 5 + 4

    def test_beat_acts(self):
        arch = StoryArchitect(seed=42)
        story = arch.generate()
        acts = [b.act for b in story.beats]
        assert acts.count(1) == 5
        assert acts.count(2) == 5
        assert acts.count(3) == 4

    def test_outline_format(self):
        arch = StoryArchitect(seed=42)
        story = arch.generate()
        outline = story.outline()
        assert "Title:" in outline
        assert "Story Beats:" in outline

    def test_reproducible(self):
        a1 = StoryArchitect(seed=77)
        a2 = StoryArchitect(seed=77)
        assert a1.generate().title == a2.generate().title


class TestWorldSeeder:
    def test_generate(self):
        seeder = WorldSeeder(seed=42)
        world = seeder.generate()
        assert isinstance(world, WorldSetting)
        assert world.name
        assert world.biome
        assert world.settlement
        assert len(world.notable_features) >= 2

    def test_description(self):
        seeder = WorldSeeder(seed=42)
        world = seeder.generate()
        desc = world.description()
        assert "World:" in desc
        assert world.name in desc

    def test_reproducible(self):
        s1 = WorldSeeder(seed=88)
        s2 = WorldSeeder(seed=88)
        assert s1.generate().name == s2.generate().name


class TestSceneAssembler:
    def test_generate_scene(self):
        assembler = SceneAssembler(seed=42)
        scene = assembler.generate(num_paragraphs=5)
        assert isinstance(scene, NarrativeScene)
        assert scene.title
        assert scene.setting_description
        assert len(scene.paragraphs) == 5
        assert len(scene.characters) >= 2

    def test_scene_text(self):
        assembler = SceneAssembler(seed=42)
        scene = assembler.generate()
        text = scene.text()
        assert scene.title in text
        assert "Setting:" in text
        assert "Characters:" in text

    def test_paragraphs_nonempty(self):
        assembler = SceneAssembler(seed=42)
        scene = assembler.generate(num_paragraphs=3)
        for p in scene.paragraphs:
            assert len(p) > 10

    def test_custom_paragraph_count(self):
        assembler = SceneAssembler(seed=42)
        scene = assembler.generate(num_paragraphs=7)
        assert len(scene.paragraphs) == 7

    def test_to_dict(self):
        assembler = SceneAssembler(seed=42)
        scene = assembler.generate()
        d = scene.to_dict()
        assert "title" in d
        assert "paragraphs" in d
        assert "characters" in d

    def test_reproducible(self):
        a1 = SceneAssembler(seed=55)
        a2 = SceneAssembler(seed=55)
        s1 = a1.generate()
        s2 = a2.generate()
        assert s1.title == s2.title
        assert s1.paragraphs == s2.paragraphs