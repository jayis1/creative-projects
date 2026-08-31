from __future__ import annotations

import json
import subprocess
import sys

import pytest

from suffix_automaton.core import (
    SuffixAutomaton,
    longest_common_substring,
    longest_common_substring_by_pairs,
)


@pytest.fixture
def banana() -> SuffixAutomaton:
    return SuffixAutomaton("banana")


def test_contains_and_occurrences(banana: SuffixAutomaton) -> None:
    assert banana.contains("ana")
    assert banana.contains("")
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


def test_kth_distinct_substring(banana: SuffixAutomaton) -> None:
    expected = [
        "a",
        "an",
        "ana",
        "anan",
        "anana",
        "b",
        "ba",
        "ban",
        "bana",
        "banan",
        "banana",
        "n",
        "na",
        "nan",
        "nana",
    ]
    assert [banana.kth_distinct_substring(index) for index in range(1, 16)] == expected


def test_shortest_absent_substring() -> None:
    automaton = SuffixAutomaton("banana")
    assert automaton.shortest_absent_substring() == "aa"
    assert automaton.shortest_absent_substring(alphabet="ab") == "aa"


def test_top_repeated_substrings() -> None:
    repeated = SuffixAutomaton("banana").top_repeated_substrings(limit=3, min_length=2)
    assert [(item.substring, item.occurrences) for item in repeated] == [
        ("ana", 2),
        ("an", 2),
        ("na", 2),
    ]


def test_graphviz_export_contains_edges() -> None:
    dot = SuffixAutomaton("aba").to_graphviz()
    assert "digraph suffix_automaton" in dot
    assert "label=\"a\"" in dot
    assert "style=dashed" in dot


def test_lcs_helper() -> None:
    assert longest_common_substring(["abracadabra", "cadabrac", "dabracad"]) == "abrac"


def test_pairwise_lcs_helper() -> None:
    result = longest_common_substring_by_pairs(["banana", "bandana", "anagram"])
    assert result[(0, 1)] == "ana"
    assert result[(0, 2)] == "ana"


def test_invalid_queries() -> None:
    automaton = SuffixAutomaton("abc")
    with pytest.raises(ValueError):
        automaton.occurrence_count("")
    with pytest.raises(ValueError):
        automaton.locate("", limit=1)
    with pytest.raises(ValueError):
        automaton.locate("a", limit=0)
    with pytest.raises(ValueError):
        automaton.kth_distinct_substring(0)


def test_cli_analyze_json() -> None:
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
        (["kth", "--text", "banana", "3"], "ana"),
        (["absent", "--text", "banana"], "aa"),
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


def test_cli_repeats_json() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "suffix_automaton",
            "repeats",
            "--text",
            "banana",
            "--limit",
            "2",
            "--json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    assert payload[0]["substring"] == "ana"
