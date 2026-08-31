from __future__ import annotations

import json
import subprocess
import sys

import pytest

from suffix_automaton.core import SuffixAutomaton, longest_common_substring


@pytest.fixture
def banana() -> SuffixAutomaton:
    return SuffixAutomaton("banana")


def test_contains_and_occurrences(banana: SuffixAutomaton) -> None:
    assert banana.contains("ana")
    assert not banana.contains("apple")
    assert banana.occurrence_count("ana") == 2
    assert banana.occurrence_count("na") == 2


def test_distinct_substring_count(banana: SuffixAutomaton) -> None:
    assert banana.count_distinct_substrings() == 15


def test_longest_repeated_substring(banana: SuffixAutomaton) -> None:
    substring, count = banana.longest_repeated_substring()
    assert substring == "ana"
    assert count == 2


def test_locate_matches(banana: SuffixAutomaton) -> None:
    locations = banana.locate("ana")
    assert [(location.start, location.end) for location in locations] == [(1, 4), (3, 6)]


def test_json_roundtrip(banana: SuffixAutomaton) -> None:
    restored = SuffixAutomaton.from_json(banana.to_json())
    assert restored.text == "banana"
    assert restored.count_distinct_substrings() == 15
    assert restored.occurrence_count("ana") == 2


def test_analysis() -> None:
    result = SuffixAutomaton("mississippi").analysis()
    assert result.text_length == 11
    assert result.longest_repeated_substring == "issi"
    assert result.longest_repeated_count == 2


def test_lcs_helper() -> None:
    assert longest_common_substring(["abracadabra", "cadabrac", "dabracad"]) == "dabra"


def test_invalid_queries() -> None:
    automaton = SuffixAutomaton("abc")
    with pytest.raises(ValueError):
        automaton.occurrence_count("")
    with pytest.raises(ValueError):
        automaton.locate("", limit=1)
    with pytest.raises(ValueError):
        automaton.locate("a", limit=0)


def test_cli_analyze_json(tmp_path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "suffix_automaton",
            "analyze",
            "--text",
            "banana",
            "--json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    assert payload["distinct_substrings"] == 15


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        (["contains", "--text", "banana", "ana"], "yes"),
        (["count", "--text", "banana", "ana"], "2"),
    ],
)
def test_cli_commands(command: list[str], expected: str) -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "suffix_automaton", *command],
        check=True,
        capture_output=True,
        text=True,
    )
    assert completed.stdout.strip() == expected
