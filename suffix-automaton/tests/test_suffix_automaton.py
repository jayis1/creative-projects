from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from typing import cast

import pytest

from suffix_automaton.commands import analysis_payload, execute_batch_jobs
from suffix_automaton.config import load_config
from suffix_automaton.core import (
    MinimalUniqueSubstring,
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


def test_analysis_payload_contains_extended_reports(banana: SuffixAutomaton) -> None:
    payload = analysis_payload(banana)
    assert payload["substring_complexity_by_length"] == {1: 3, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1}
    assert payload["minimal_unique_substrings"][0]["substring"] == "b"
    assert len(payload["minimal_unique_substrings"]) == 3


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


def test_complexity_by_length() -> None:
    assert SuffixAutomaton("ababa").substring_complexity_by_length() == {1: 2, 2: 2, 3: 2, 4: 2, 5: 1}


def test_minimal_unique_substrings() -> None:
    items = SuffixAutomaton("banana").minimal_unique_substrings()
    assert items == [
        MinimalUniqueSubstring(start=0, end=1, substring="b"),
        MinimalUniqueSubstring(start=1, end=5, substring="anan"),
        MinimalUniqueSubstring(start=2, end=5, substring="nan"),
    ]


def test_graphviz_export_contains_edges() -> None:
    dot = SuffixAutomaton("aba").to_graphviz()
    assert "digraph suffix_automaton" in dot
    assert "label=\"a\"" in dot
    assert "style=dashed" in dot


def test_extend_updates_text_and_counts() -> None:
    automaton = SuffixAutomaton("ban")
    automaton.extend("a")
    automaton.extend("n")
    automaton.extend("a")
    assert automaton.text == "banana"
    assert automaton.occurrence_count("ana") == 2


def test_graphviz_escapes_control_characters() -> None:
    dot = SuffixAutomaton("a\n").to_graphviz()
    assert "label=\"\\n\"" in dot


def test_from_dict_rejects_non_boolean_is_clone() -> None:
    payload = SuffixAutomaton("ab").to_dict()
    states = cast(list[dict[str, object]], payload["states"])
    states[0]["is_clone"] = "false"
    with pytest.raises(TypeError):
        SuffixAutomaton.from_dict(payload)


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


def test_load_config_toml(tmp_path: Path) -> None:
    config_path = tmp_path / "jobs.toml"
    config_path.write_text(
        """
[[jobs]]
command = "analyze"
text = "banana"
json = true
""".strip(),
        encoding="utf-8",
    )
    loaded = load_config(config_path)
    assert loaded["jobs"][0]["command"] == "analyze"


def test_execute_batch_jobs_json(tmp_path: Path) -> None:
    output_path = tmp_path / "report.json"
    document = {
        "jobs": [
            {"command": "analyze", "text": "banana", "json": True},
            {"command": "mus", "text": "banana", "limit": 2, "output": str(output_path)},
            {"command": "lcs", "strings": ["banana", "bandana", "anagram"], "pairwise": True},
        ]
    }
    payload = execute_batch_jobs(document)
    assert payload["job_count"] == 3
    saved = json.loads(output_path.read_text(encoding="utf-8"))
    assert saved[0]["substring"] == "b"
    assert payload["results"][2]["payload"]["pairwise"]["0-1"] == "ana"


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
    assert payload["minimal_unique_substrings"][0]["substring"] == "b"


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        (["contains", "--text", "banana", "ana"], 'substring: ana\ncontains: True'),
        (["count", "--text", "banana", "ana"], 'substring: ana\noccurrences: 2'),
        (["kth", "--text", "banana", "3"], 'k: 3\nsubstring: ana'),
        (["absent", "--text", "banana"], 'substring: aa'),
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


def test_cli_complexity_json() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "suffix_automaton",
            "complexity",
            "--text",
            "banana",
            "--json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(completed.stdout)["6"] == 1


def test_cli_run_config(tmp_path: Path) -> None:
    config_path = tmp_path / "jobs.json"
    config_path.write_text(
        json.dumps(
            {
                "jobs": [
                    {"command": "analyze", "text": "banana", "json": True},
                    {"command": "lcs", "strings": ["banana", "bandana"], "pairwise": True},
                ]
            }
        ),
        encoding="utf-8",
    )
    completed = subprocess.run(
        [sys.executable, "-m", "suffix_automaton", "run-config", str(config_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    assert payload["job_count"] == 2
    assert payload["results"][1]["payload"]["longest_common_substring"] == "ana"
