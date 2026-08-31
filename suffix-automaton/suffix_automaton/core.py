"""Core suffix automaton implementation and analytics."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass, field
import json
from typing import Iterable


@dataclass(slots=True)
class MatchLocation:
    """Span where a substring occurs in the source text."""

    start: int
    end: int


@dataclass(slots=True)
class StateSummary:
    """Serializable automaton state summary."""

    length: int
    link: int
    next: dict[str, int]
    first_pos: int
    is_clone: bool
    occ_count: int = 0


@dataclass(slots=True)
class AnalysisResult:
    """Aggregate statistics for a source string."""

    text_length: int
    state_count: int
    distinct_substrings: int
    longest_repeated_substring: str
    longest_repeated_count: int
    alphabet: list[str] = field(default_factory=list)


class SuffixAutomaton:
    """Suffix automaton for substring queries and analytics.

    The automaton stores end-position equivalence classes for every substring
    of an input text. Construction is O(n), and common queries are O(m)
    where m is the query length.
    """

    def __init__(self, text: str = "") -> None:
        self.text = ""
        self.states: list[StateSummary] = [
            StateSummary(length=0, link=-1, next={}, first_pos=-1, is_clone=False)
        ]
        self.last = 0
        if text:
            self.build(text)

    def build(self, text: str) -> "SuffixAutomaton":
        """Reset and build the automaton for *text*."""
        self._validate_text(text)
        self.text = text
        self.states = [
            StateSummary(length=0, link=-1, next={}, first_pos=-1, is_clone=False)
        ]
        self.last = 0
        for character in text:
            self.extend(character)
        self._propagate_occurrence_counts()
        return self

    def extend(self, character: str) -> None:
        """Append one character to the automaton."""
        if len(character) != 1:
            raise ValueError("extend() expects a single character")
        current = len(self.states)
        self.states.append(
            StateSummary(
                length=self.states[self.last].length + 1,
                link=0,
                next={},
                first_pos=self.states[self.last].length,
                is_clone=False,
                occ_count=1,
            )
        )
        parent = self.last
        while parent >= 0 and character not in self.states[parent].next:
            self.states[parent].next[character] = current
            parent = self.states[parent].link

        if parent == -1:
            self.states[current].link = 0
        else:
            candidate = self.states[parent].next[character]
            if self.states[parent].length + 1 == self.states[candidate].length:
                self.states[current].link = candidate
            else:
                clone = len(self.states)
                self.states.append(
                    StateSummary(
                        length=self.states[parent].length + 1,
                        link=self.states[candidate].link,
                        next=dict(self.states[candidate].next),
                        first_pos=self.states[candidate].first_pos,
                        is_clone=True,
                        occ_count=0,
                    )
                )
                while parent >= 0 and self.states[parent].next.get(character) == candidate:
                    self.states[parent].next[character] = clone
                    parent = self.states[parent].link
                self.states[candidate].link = clone
                self.states[current].link = clone
        self.last = current

    def contains(self, substring: str) -> bool:
        """Return True if *substring* occurs in the source text."""
        self._require_built()
        self._validate_query(substring)
        state = 0
        for character in substring:
            next_state = self.states[state].next.get(character)
            if next_state is None:
                return False
            state = next_state
        return True

    def follow(self, substring: str) -> int | None:
        """Return the state index reached by *substring*, or None."""
        self._require_built()
        self._validate_query(substring)
        state = 0
        for character in substring:
            next_state = self.states[state].next.get(character)
            if next_state is None:
                return None
            state = next_state
        return state

    def count_distinct_substrings(self) -> int:
        """Count distinct substrings of the source text."""
        self._require_built()
        total = 0
        for index, state in enumerate(self.states[1:], start=1):
            total += state.length - self.states[state.link].length
        return total

    def occurrence_count(self, substring: str) -> int:
        """Count how many times *substring* occurs."""
        self._require_built()
        self._validate_non_empty_query(substring)
        state = self.follow(substring)
        if state is None:
            return 0
        return self.states[state].occ_count

    def longest_repeated_substring(self) -> tuple[str, int]:
        """Return the longest substring that appears at least twice."""
        self._require_built()
        best_state = None
        best_length = 0
        for index, state in enumerate(self.states[1:], start=1):
            if state.occ_count >= 2 and state.length > best_length:
                best_length = state.length
                best_state = index
        if best_state is None:
            return "", 0
        state = self.states[best_state]
        end = state.first_pos + 1
        start = end - best_length
        return self.text[start:end], state.occ_count

    def locate(self, substring: str, limit: int | None = None) -> list[MatchLocation]:
        """Find substring locations in the text.

        This uses Python's fast substring search after the automaton validates
        membership. The automaton remains the index used for the existence check.
        """
        self._require_built()
        self._validate_non_empty_query(substring)
        if limit is not None and limit <= 0:
            raise ValueError("limit must be positive when provided")
        if not self.contains(substring):
            return []
        results: list[MatchLocation] = []
        start = 0
        while True:
            found = self.text.find(substring, start)
            if found == -1:
                break
            results.append(MatchLocation(found, found + len(substring)))
            if limit is not None and len(results) >= limit:
                break
            start = found + 1
        return results

    def analysis(self) -> AnalysisResult:
        """Compute aggregate statistics for the source text."""
        self._require_built()
        repeated, count = self.longest_repeated_substring()
        return AnalysisResult(
            text_length=len(self.text),
            state_count=len(self.states),
            distinct_substrings=self.count_distinct_substrings(),
            longest_repeated_substring=repeated,
            longest_repeated_count=count,
            alphabet=sorted(set(self.text)),
        )

    def to_dict(self) -> dict[str, object]:
        """Serialize the automaton."""
        self._require_built()
        return {
            "text": self.text,
            "last": self.last,
            "states": [asdict(state) for state in self.states],
        }

    def to_json(self, *, indent: int = 2) -> str:
        """Serialize the automaton as JSON."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "SuffixAutomaton":
        """Restore an automaton from serialized data."""
        if not isinstance(payload, dict):
            raise TypeError("payload must be a dictionary")
        text = payload.get("text")
        last = payload.get("last")
        raw_states = payload.get("states")
        if not isinstance(text, str):
            raise TypeError("payload['text'] must be a string")
        if not isinstance(last, int):
            raise TypeError("payload['last'] must be an integer")
        if not isinstance(raw_states, list) or not raw_states:
            raise TypeError("payload['states'] must be a non-empty list")
        instance = cls()
        instance.text = text
        instance.last = last
        instance.states = []
        for entry in raw_states:
            if not isinstance(entry, dict):
                raise TypeError("each state must be a dictionary")
            transitions = entry.get("next")
            if not isinstance(transitions, dict) or not all(
                isinstance(key, str) and len(key) == 1 and isinstance(value, int)
                for key, value in transitions.items()
            ):
                raise TypeError("state transitions must map single characters to ints")
            instance.states.append(
                StateSummary(
                    length=cls._coerce_int(entry.get("length"), "state.length"),
                    link=cls._coerce_int(entry.get("link"), "state.link"),
                    next=transitions,
                    first_pos=cls._coerce_int(entry.get("first_pos"), "state.first_pos"),
                    is_clone=bool(entry.get("is_clone")),
                    occ_count=cls._coerce_int(entry.get("occ_count", 0), "state.occ_count"),
                )
            )
        instance._validate_internal_structure()
        return instance

    @classmethod
    def from_json(cls, payload: str) -> "SuffixAutomaton":
        """Restore an automaton from JSON."""
        if not isinstance(payload, str):
            raise TypeError("payload must be a JSON string")
        return cls.from_dict(json.loads(payload))

    def _propagate_occurrence_counts(self) -> None:
        order = sorted(range(len(self.states)), key=lambda index: self.states[index].length, reverse=True)
        for index in order:
            link = self.states[index].link
            if link >= 0:
                self.states[link].occ_count += self.states[index].occ_count

    def _validate_internal_structure(self) -> None:
        if self.last < 0 or self.last >= len(self.states):
            raise ValueError("serialized automaton has invalid last state")
        if self.states[0].link != -1:
            raise ValueError("root state must link to -1")
        for index, state in enumerate(self.states):
            if state.length < 0:
                raise ValueError(f"state {index} has negative length")
            if state.link >= len(self.states):
                raise ValueError(f"state {index} has invalid suffix link")
            for target in state.next.values():
                if target < 0 or target >= len(self.states):
                    raise ValueError(f"state {index} points to invalid transition target")

    @staticmethod
    def _coerce_int(value: object, field_name: str) -> int:
        if not isinstance(value, int):
            raise TypeError(f"{field_name} must be an integer")
        return value

    @staticmethod
    def _validate_text(text: str) -> None:
        if not isinstance(text, str):
            raise TypeError("text must be a string")

    @staticmethod
    def _validate_query(substring: str) -> None:
        if not isinstance(substring, str):
            raise TypeError("substring must be a string")

    @staticmethod
    def _validate_non_empty_query(substring: str) -> None:
        if not isinstance(substring, str):
            raise TypeError("substring must be a string")
        if substring == "":
            raise ValueError("substring must not be empty")

    def _require_built(self) -> None:
        if self.text == "" and len(self.states) == 1:
            return


def longest_common_substring(strings: Iterable[str]) -> str:
    """Simple helper retained for future expansion."""
    items = list(strings)
    if not items:
        raise ValueError("expected at least one string")
    if any(not isinstance(item, str) for item in items):
        raise TypeError("all items must be strings")
    base = min(items, key=len)
    others = [item for item in items if item is not base]
    if not others:
        return base
    for size in range(len(base), 0, -1):
        seen = set()
        for start in range(0, len(base) - size + 1):
            candidate = base[start : start + size]
            if candidate in seen:
                continue
            seen.add(candidate)
            if all(candidate in other for other in others):
                return candidate
    return ""
