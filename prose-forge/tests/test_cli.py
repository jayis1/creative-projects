"""Tests for the CLI."""

import json
import subprocess
import sys


def run_cli(*args) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "prose_forge", *args],
        capture_output=True, text=True, timeout=30,
    )


class TestCLI:
    def test_version(self):
        result = run_cli("--version")
        assert result.returncode == 0
        assert "prose-forge" in result.stdout

    def test_no_command_shows_help(self):
        result = run_cli()
        assert result.returncode == 1
        # Should print usage info
        assert "usage" in result.stdout.lower() or "usage" in result.stderr.lower()

    def test_story(self):
        result = run_cli("story", "--seed", "42")
        assert result.returncode == 0
        assert "Title:" in result.stdout
        assert "Story Beats:" in result.stdout

    def test_story_json(self):
        result = run_cli("story", "--seed", "42", "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "title" in data
        assert "beats" in data
        assert len(data["beats"]) == 14

    def test_character(self):
        result = run_cli("character", "--seed", "42")
        assert result.returncode == 0
        assert "Name:" in result.stdout

    def test_character_multiple(self):
        result = run_cli("character", "--seed", "42", "--count", "3")
        assert result.returncode == 0
        # Should have 3 Name: lines
        assert result.stdout.count("Name:") == 3

    def test_poem_haiku(self):
        result = run_cli("poem", "--form", "haiku", "--seed", "3")
        assert result.returncode == 0
        lines = result.stdout.strip().split("\n")
        assert len(lines) == 3

    def test_poem_sonnet(self):
        result = run_cli("poem", "--form", "sonnet", "--seed", "3")
        assert result.returncode == 0
        lines = result.stdout.strip().split("\n")
        assert len(lines) == 14

    def test_poem_limerick(self):
        result = run_cli("poem", "--form", "limerick", "--seed", "3")
        assert result.returncode == 0
        lines = result.stdout.strip().split("\n")
        assert len(lines) == 5

    def test_names(self):
        result = run_cli("names", "--culture", "fantasy", "--count", "5", "--seed", "42")
        assert result.returncode == 0
        names = result.stdout.strip().split("\n")
        assert len(names) == 5

    def test_names_first_only(self):
        result = run_cli("names", "--culture", "norse", "--count", "3", "--first-only", "--seed", "42")
        assert result.returncode == 0
        names = result.stdout.strip().split("\n")
        for name in names:
            assert " " not in name

    def test_names_all_cultures(self):
        for culture in ["fantasy", "sci_fi", "norse", "japanese", "arabic"]:
            result = run_cli("names", "--culture", culture, "--count", "2", "--seed", "42")
            assert result.returncode == 0, f"Failed for {culture}: {result.stderr}"

    def test_world(self):
        result = run_cli("world", "--seed", "11")
        assert result.returncode == 0
        assert "World:" in result.stdout
        assert "Biome:" in result.stdout

    def test_scene(self):
        result = run_cli("scene", "--seed", "99")
        assert result.returncode == 0
        assert result.stdout.startswith("#")

    def test_scene_json(self):
        result = run_cli("scene", "--seed", "99", "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "title" in data
        assert "paragraphs" in data

    def test_grammar(self):
        result = run_cli("grammar", "--seed", "42")
        assert result.returncode == 0
        assert len(result.stdout.strip()) > 50

    def test_markov_requires_train(self):
        result = run_cli("markov")
        assert result.returncode != 0
        assert "train" in result.stderr.lower()