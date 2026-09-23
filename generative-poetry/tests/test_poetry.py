"""Tests for the generative poetry engine."""

import pytest
import random
from poetry_gen import PoetryEngine, syllable_count, rhymes
from poetry_gen.vocabulary import Vocabulary
from poetry_gen.syllables import line_syllables
from poetry_gen.rhyme import find_rhyme, _phonetic_tail
from poetry_gen import forms


# ─────────────────────────────────────────────
# syllable_count
# ─────────────────────────────────────────────

class TestSyllableCount:
    def test_single_vowel(self):
        assert syllable_count("a") == 1

    def test_simple_words(self):
        assert syllable_count("cat") == 1
        assert syllable_count("wind") == 1

    def test_two_syllables(self):
        result = syllable_count("mountain")
        assert 2 <= result <= 3  # heuristics aren't perfect

    def test_silent_e(self):
        # "lake" should count less than "lakers"
        assert syllable_count("lake") <= syllable_count("laker")

    def test_punctuation_stripped(self):
        assert syllable_count("wind,") == syllable_count("wind")

    def test_empty(self):
        assert syllable_count("") == 0

    def test_at_least_one(self):
        assert syllable_count("hmm") >= 1

    def test_long_word(self):
        # "constellation" has 5 syllables
        result = syllable_count("constellation")
        assert 3 <= result <= 6  # heuristic range


class TestLineSyllables:
    def test_simple(self):
        assert line_syllables("cat sat") == line_syllables("cat") + line_syllables("sat")

    def test_empty(self):
        assert line_syllables("") == 0


# ─────────────────────────────────────────────
# rhyme
# ─────────────────────────────────────────────

class TestRhymes:
    def test_obvious_rhymes(self):
        assert rhymes("lake", "cake")
        assert rhymes("rain", "plain")
        assert rhymes("stone", "bone")

    def test_identical_not_rhyme(self):
        assert not rhymes("lake", "lake")

    def test_non_rhymes(self):
        assert not rhymes("mountain", "river")
        assert not rhymes("cloud", "stone")

    def test_case_insensitive(self):
        assert rhymes("RAIN", "plain")


class TestFindRhyme:
    def test_finds_match(self):
        result = find_rhyme("rain", ["cloud", "plain", "storm"])
        assert result == "plain"

    def test_no_match(self):
        assert find_rhyme("mountain", ["river", "cloud"]) is None


# ─────────────────────────────────────────────
# Vocabulary
# ─────────────────────────────────────────────

class TestVocabulary:
    def test_default_theme(self):
        v = Vocabulary()
        assert v.theme == "nature"
        assert len(v.nouns) > 0
        assert len(v.verbs) > 0

    def test_all_themes(self):
        for theme in Vocabulary.themes():
            v = Vocabulary(theme=theme)
            assert v.nouns and v.verbs and v.adjectives

    def test_pick(self):
        v = Vocabulary()
        result = v.noun()
        assert result in v.nouns

    def test_noun_phrase(self):
        v = Vocabulary()
        phrase = v.noun_phrase()
        assert len(phrase.split()) == 2

    def test_custom_nouns(self):
        v = Vocabulary(nouns=["robot", "laser"], verbs=["fires"], adjectives=["cool"],
                       adverbs=["quickly"])
        assert v.noun() in {"robot", "laser"}

    def test_themes_list(self):
        themes = Vocabulary.themes()
        assert "nature" in themes
        assert "city" in themes
        assert len(themes) >= 4


# ─────────────────────────────────────────────
# Forms
# ─────────────────────────────────────────────

class TestHaiku:
    def test_three_lines(self):
        v = Vocabulary()
        poem = forms.haiku(v)
        assert poem.count("\n") == 2

    def test_non_empty(self):
        v = Vocabulary()
        poem = forms.haiku(v)
        for line in poem.splitlines():
            assert len(line.strip()) > 0

    def test_reproducible_with_seed(self):
        random.seed(42)
        v = Vocabulary(theme="nature")
        p1 = forms.haiku(v)
        random.seed(42)
        v2 = Vocabulary(theme="nature")
        p2 = forms.haiku(v2)
        assert p1 == p2


class TestLimerick:
    def test_five_lines(self):
        v = Vocabulary()
        poem = forms.limerick(v)
        assert poem.count("\n") == 4

    def test_non_empty(self):
        v = Vocabulary()
        poem = forms.limerick(v)
        for line in poem.splitlines():
            assert len(line.strip()) > 0


class TestFreeVerse:
    def test_default_line_count(self):
        v = Vocabulary()
        poem = forms.free_verse(v)
        lines = poem.splitlines()
        assert 6 <= len(lines) <= 12

    def test_custom_line_count(self):
        v = Vocabulary()
        poem = forms.free_verse(v, n_lines=4)
        assert poem.count("\n") == 3

    def test_non_empty_lines(self):
        v = Vocabulary()
        poem = forms.free_verse(v, n_lines=8)
        for line in poem.splitlines():
            assert len(line.strip()) > 0


class TestAcrostic:
    def test_keyword_initials(self):
        v = Vocabulary()
        keyword = "RAIN"
        poem = forms.acrostic(v, keyword=keyword)
        lines = poem.splitlines()
        assert len(lines) == 4
        for letter, line in zip(keyword, lines):
            # First letter of first word should match
            first_word = line.split()[0] if line.split() else ""
            assert first_word.upper().startswith(letter.upper()), \
                f"Expected line starting with '{letter}', got: {line}"

    def test_default_keyword(self):
        v = Vocabulary(theme="nature")
        poem = forms.acrostic(v)
        assert len(poem.splitlines()) > 0

    def test_non_alpha_in_keyword_skipped(self):
        v = Vocabulary()
        poem = forms.acrostic(v, keyword="A-B")
        lines = poem.splitlines()
        assert len(lines) == 2  # only 'A' and 'B'


class TestSonnet:
    def test_fourteen_lines(self):
        v = Vocabulary()
        poem = forms.sonnet(v)
        assert len(poem.splitlines()) == 14

    def test_non_empty(self):
        v = Vocabulary()
        poem = forms.sonnet(v)
        for line in poem.splitlines():
            assert len(line.strip()) > 0


# ─────────────────────────────────────────────
# PoetryEngine
# ─────────────────────────────────────────────

class TestPoetryEngine:
    def test_haiku(self):
        e = PoetryEngine(theme="nature")
        poem = e.haiku()
        assert poem.form == "haiku"
        assert poem.theme == "nature"
        assert "\n" in poem.text  # at least two lines

    def test_limerick(self):
        e = PoetryEngine(theme="city")
        poem = e.limerick()
        assert poem.form == "limerick"

    def test_free_verse(self):
        e = PoetryEngine(theme="space")
        poem = e.free_verse(n_lines=7)
        assert len(poem.text.splitlines()) == 7

    def test_acrostic_keyword(self):
        e = PoetryEngine(theme="sea")
        poem = e.acrostic(keyword="WAVE")
        assert poem.keyword == "WAVE"
        assert len(poem.text.splitlines()) == 4

    def test_sonnet(self):
        e = PoetryEngine(theme="autumn")
        poem = e.sonnet()
        assert len(poem.text.splitlines()) == 14

    def test_random_poem(self):
        e = PoetryEngine(seed=7)
        poem = e.random_poem()
        assert poem.form in ["haiku", "limerick", "free_verse", "acrostic", "sonnet"]

    def test_collection(self):
        e = PoetryEngine(seed=99)
        poems = e.collection(n=5)
        assert len(poems) == 5
        for poem in poems:
            assert poem.text

    def test_unknown_form_raises(self):
        e = PoetryEngine()
        with pytest.raises(ValueError, match="Unknown form"):
            e.random_poem(form="villanelle")

    def test_str_representation(self):
        e = PoetryEngine(theme="nature")
        poem = e.haiku()
        s = str(poem)
        assert "HAIKU" in s
        assert "nature" in s

    def test_random_theme(self):
        e = PoetryEngine(seed=1)
        assert e.theme in Vocabulary.themes()

    def test_seed_reproducibility(self):
        e1 = PoetryEngine(theme="nature", seed=42)
        p1 = e1.haiku().text
        e2 = PoetryEngine(theme="nature", seed=42)
        p2 = e2.haiku().text
        assert p1 == p2

    def test_collection_form_filter(self):
        e = PoetryEngine(seed=5)
        poems = e.collection(n=3, form="haiku")
        assert all(p.form == "haiku" for p in poems)


# ─────────────────────────────────────────────
# CLI smoke test
# ─────────────────────────────────────────────

class TestCLI:
    def test_list_themes(self, capsys):
        from cli import main
        ret = main(["--themes"])
        assert ret == 0
        out = capsys.readouterr().out
        assert "nature" in out

    def test_haiku(self, capsys):
        from cli import main
        ret = main(["haiku", "--theme", "nature", "--seed", "1"])
        assert ret == 0
        out = capsys.readouterr().out
        assert len(out.strip()) > 0

    def test_multiple_poems(self, capsys):
        from cli import main
        ret = main(["haiku", "--count", "3", "--theme", "city", "--seed", "2"])
        assert ret == 0
        out = capsys.readouterr().out
        assert out.count("HAIKU") == 3

    def test_free_verse_lines(self, capsys):
        from cli import main
        ret = main(["free_verse", "--lines", "5", "--theme", "space", "--seed", "3"])
        assert ret == 0
        out = capsys.readouterr().out
        # Look for 5 content lines in the output
        content_lines = [l for l in out.splitlines() if l.strip() and not l.startswith("[")]
        assert len(content_lines) == 5

    def test_acrostic_keyword(self, capsys):
        from cli import main
        ret = main(["acrostic", "--keyword", "SEA", "--theme", "sea", "--seed", "4"])
        assert ret == 0
        out = capsys.readouterr().out
        assert len(out.strip()) > 0
