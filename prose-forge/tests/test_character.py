"""Tests for the character generator."""

from prose_forge.character import CharacterForge, Character


class TestCharacterForge:
    def test_generate_single(self):
        forge = CharacterForge(seed=42)
        char = forge.generate()
        assert isinstance(char, Character)
        assert len(char.name) > 3
        assert char.role
        assert 18 <= char.age <= 65
        assert len(char.traits) >= 2
        assert char.motivation
        assert char.flaw
        assert char.arc
        assert char.appearance
        assert char.background

    def test_reproducible(self):
        f1 = CharacterForge(seed=99)
        f2 = CharacterForge(seed=99)
        c1 = f1.generate()
        c2 = f2.generate()
        assert c1.name == c2.name
        assert c1.traits == c2.traits

    def test_traits_unique(self):
        forge = CharacterForge(seed=42)
        char = forge.generate()
        assert len(char.traits) == len(set(char.traits))

    def test_generate_cast(self):
        forge = CharacterForge(seed=42)
        cast = forge.generate_cast(count=4)
        assert len(cast) == 4
        names = [c.name for c in cast]
        assert len(set(names)) == 4  # all unique
        # Each character should have relationships to the others
        for char in cast:
            assert len(char.relationships) == 3

    def test_relationships_reference_real_names(self):
        forge = CharacterForge(seed=42)
        cast = forge.generate_cast(count=3)
        all_names = {c.name for c in cast}
        for char in cast:
            for rel_name in char.relationships:
                assert rel_name in all_names

    def test_to_dict(self):
        forge = CharacterForge(seed=42)
        char = forge.generate()
        d = char.to_dict()
        assert d["name"] == char.name
        assert d["age"] == char.age
        assert isinstance(d["traits"], list)

    def test_summary(self):
        forge = CharacterForge(seed=42)
        char = forge.generate()
        summary = char.summary()
        assert "Name:" in summary
        assert "Role:" in summary
        assert char.name in summary