"""Tests for the poetry generators and syllable counter."""

from prose_forge.poetry import Poet, count_syllables, line_syllables


class TestSyllableCounter:
    def test_single_syllable(self):
        assert count_syllables("cat") == 1
        assert count_syllables("the") == 1
        assert count_syllables("dog") == 1

    def test_two_syllables(self):
        assert count_syllables("apple") == 2
        assert count_syllables("river") == 2

    def test_three_syllables(self):
        assert count_syllables("beautiful") == 3
        assert count_syllables("memory") == 3

    def test_silent_e(self):
        assert count_syllables("fire") == 1
        assert count_syllables("time") == 1

    def test_empty(self):
        assert count_syllables("") == 0
        assert count_syllables("...") == 0

    def test_line_syllables(self):
        assert line_syllables("the cat sat") == 3

    def test_punctuation_handled(self):
        assert count_syllables("river.") == count_syllables("river")
        assert count_syllables("beautiful,") == count_syllables("beautiful")


class TestHaiku:
    def test_haiku_three_lines(self):
        poet = Poet(seed=42)
        haiku = poet.haiku()
        lines = haiku.split("\n")
        assert len(lines) == 3

    def test_haiku_syllable_counts(self):
        poet = Poet(seed=42)
        haiku = poet.haiku()
        lines = haiku.split("\n")
        assert line_syllables(lines[0]) == 5
        assert line_syllables(lines[1]) == 7
        assert line_syllables(lines[2]) == 5


class TestTanka:
    def test_tanka_five_lines(self):
        poet = Poet(seed=42)
        tanka = poet.tanka()
        lines = tanka.split("\n")
        assert len(lines) == 5
        assert line_syllables(lines[0]) == 5
        assert line_syllables(lines[1]) == 7
        assert line_syllables(lines[2]) == 5
        assert line_syllables(lines[3]) == 7
        assert line_syllables(lines[4]) == 7


class TestLimerick:
    def test_limerick_five_lines(self):
        poet = Poet(seed=42)
        limerick = poet.limerick()
        lines = limerick.split("\n")
        assert len(lines) == 5


class TestSonnet:
    def test_sonnet_fourteen_lines(self):
        poet = Poet(seed=42)
        sonnet = poet.sonnet()
        lines = sonnet.split("\n")
        assert len(lines) == 14


class TestFreeVerse:
    def test_free_verse_variable_lines(self):
        poet = Poet(seed=42)
        poem = poet.free_verse(lines=7)
        lines = poem.split("\n")
        assert len(lines) == 7

    def test_free_verse_nonempty(self):
        poet = Poet(seed=42)
        poem = poet.free_verse(lines=4)
        assert len(poem.strip()) > 0