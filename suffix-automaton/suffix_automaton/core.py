"""Core suffix automaton implementation and analytics."""

from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass, field
import json
from typing import Iterable, Iterator, Sequence


@dataclass(slots=True)
class MatchLocation:
    """Span where a substring occurs in the source text."""

    start: int
    end: int


@dataclass(slots=True)
class RepeatedSubstring:
    """Repeated substring summary."""

    substring: str
    occurrences: int
    length: int


@dataclass(slots=True)
class MinimalUniqueSubstring:
    """Shortest substring starting at a position that occurs exactly once."""

    start: int
    end: int
    substring: str


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
        self._terminal_states: list[int] = []
        self._substring_count_cache: list[int] | None = None
        if text:
            self.build(text)

    def build(self, text: str) -> "SuffixAutomaton":
        """Reset and build the automaton for *text*."""
        self._validate_text(text)
        self.text = ""
        self.states = [
            StateSummary(length=0, link=-1, next={}, first_pos=-1, is_clone=False)
        ]
        self.last = 0
        self._terminal_states = []
        self._substring_count_cache = None
        for character in text:
            self.extend(character)
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
        self._substring_count_cache = None
        self.text += character

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
        self._terminal_states.append(current)
        self._recompute_occurrence_counts()

    def contains(self, substring: str) -> bool:
        """Return True if *substring* occurs in the source text."""
        self._validate_query(substring)
        state = self.follow(substring)
        return state is not None

    def follow(self, substring: str) -> int | None:
        """Return the state index reached by *substring*, or None."""
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
        total = 0
        for state in self.states[1:]:
            total += state.length - self.states[state.link].length
        return total

    def occurrence_count(self, substring: str) -> int:
        """Count how many times *substring* occurs."""
        self._validate_non_empty_query(substring)
        state = self.follow(substring)
        if state is None:
            return 0
        return self.states[state].occ_count

    def longest_repeated_substring(self) -> tuple[str, int]:
        """Return the longest substring that appears at least twice."""
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

    def kth_distinct_substring(self, k: int) -> str:
        """Return the k-th distinct substring in lexicographic order."""
        if not isinstance(k, int):
            raise TypeError("k must be an integer")
        if k <= 0:
            raise ValueError("k must be positive")
        counts = self._distinct_path_counts()
        if k > counts[0] - 1:
            raise ValueError("k exceeds the number of distinct substrings")

        state = 0
        prefix: list[str] = []
        while k > 0:
            for character, target in sorted(self.states[state].next.items()):
                subtree = counts[target]
                if k == 1:
                    prefix.append(character)
                    return "".join(prefix)
                if k <= subtree:
                    prefix.append(character)
                    state = target
                    k -= 1
                    break
                k -= subtree
            else:
                raise RuntimeError("failed to resolve k-th substring")
        return "".join(prefix)

    def shortest_absent_substring(self, alphabet: Iterable[str] | None = None) -> str:
        """Return a shortest string over *alphabet* missing from the text."""
        if alphabet is None:
            symbols = sorted(set(self.text))
        else:
            symbols = sorted(dict.fromkeys(alphabet))
        if not symbols:
            return ""
        for symbol in symbols:
            if not isinstance(symbol, str) or len(symbol) != 1:
                raise ValueError("alphabet must contain single-character strings")

        queue: deque[str] = deque(symbols)
        while queue:
            candidate = queue.popleft()
            if not self.contains(candidate):
                return candidate
            for symbol in symbols:
                queue.append(candidate + symbol)
        raise RuntimeError("failed to find an absent substring")

    def top_repeated_substrings(self, *, limit: int = 10, min_length: int = 1) -> list[RepeatedSubstring]:
        """Return top repeated substrings ranked by length, frequency, then text.

        This implementation walks the automaton's substring DAG directly instead
        of resolving each distinct substring through repeated rank queries.
        """
        if not isinstance(limit, int) or limit <= 0:
            raise ValueError("limit must be a positive integer")
        if not isinstance(min_length, int) or min_length <= 0:
            raise ValueError("min_length must be a positive integer")

        repeated: list[RepeatedSubstring] = []
        for substring, state_index in self.iter_distinct_substrings():
            if len(substring) < min_length:
                continue
            occurrences = self.states[state_index].occ_count
            if occurrences < 2:
                continue
            repeated.append(
                RepeatedSubstring(
                    substring=substring,
                    occurrences=occurrences,
                    length=len(substring),
                )
            )
        repeated.sort(key=lambda item: (-item.length, -item.occurrences, item.substring))
        return repeated[:limit]

    def locate(self, substring: str, limit: int | None = None) -> list[MatchLocation]:
        """Find substring locations in the text.

        This uses Python's substring search after the automaton validates
        membership. The automaton remains the index used for the existence check.
        """
        self._validate_non_empty_query(substring)
        if limit is not None and (not isinstance(limit, int) or limit <= 0):
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

    def substring_complexity_by_length(self) -> dict[int, int]:
        """Return the number of distinct substrings for each length."""
        text_length = len(self.text)
        if text_length == 0:
            return {}
        difference = [0] * (text_length + 2)
        for state in self.states[1:]:
            lower = self.states[state.link].length + 1
            upper = state.length
            difference[lower] += 1
            difference[upper + 1] -= 1
        counts: dict[int, int] = {}
        running = 0
        for length in range(1, text_length + 1):
            running += difference[length]
            counts[length] = running
        return counts

    def minimal_unique_substrings(self) -> list[MinimalUniqueSubstring]:
        """Return minimal unique substrings for positions where one exists.

        Some starts cannot be distinguished by any in-text continuation alone.
        For example, the final ``a`` in ``banana`` never becomes unique without
        adding an external end marker. Those positions are skipped.
        """
        results: list[MinimalUniqueSubstring] = []
        for start in range(len(self.text)):
            state = 0
            for end in range(start, len(self.text)):
                character = self.text[end]
                next_state = self.states[state].next.get(character)
                if next_state is None:
                    raise RuntimeError("automaton is inconsistent with source text")
                state = next_state
                if self.states[state].occ_count == 1:
                    results.append(
                        MinimalUniqueSubstring(
                            start=start,
                            end=end + 1,
                            substring=self.text[start : end + 1],
                        )
                    )
                    break
            else:
                continue
        return results

    def iter_distinct_substrings(self) -> Iterator[tuple[str, int]]:
        """Yield distinct substrings in lexicographic order with state indices."""

        def walk(state_index: int, prefix: str) -> Iterator[tuple[str, int]]:
            for character, target in sorted(self.states[state_index].next.items()):
                substring = prefix + character
                yield substring, target
                yield from walk(target, substring)

        yield from walk(0, "")

    def to_graphviz(self) -> str:
        """Export the automaton as Graphviz DOT."""
        lines = ["digraph suffix_automaton {", "  rankdir=LR;", '  node [shape=circle];']
        for index, state in enumerate(self.states):
            suffix = f" / occ={state.occ_count}" if index != 0 else ""
            label = f"{index}: len={state.length}{suffix}"
            lines.append(f'  {index} [label="{label}"];')
            if state.link >= 0:
                lines.append(f"  {index} -> {state.link} [style=dashed, color=gray, label=\"link\"];")
            for character, target in sorted(state.next.items()):
                escaped = self._escape_graphviz_label(character)
                lines.append(f'  {index} -> {target} [label="{escaped}"];')
        lines.append("}")
        return "\n".join(lines)

    def analysis(self) -> AnalysisResult:
        """Compute aggregate statistics for the source text."""
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
        instance._terminal_states = []
        instance._substring_count_cache = None
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
                    next=dict(transitions),
                    first_pos=cls._coerce_int(entry.get("first_pos"), "state.first_pos"),
                    is_clone=cls._coerce_bool(entry.get("is_clone"), "state.is_clone"),
                    occ_count=cls._coerce_int(entry.get("occ_count", 0), "state.occ_count"),
                )
            )
        instance._validate_internal_structure()
        instance._rebuild_terminal_states_from_text()
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

    def _recompute_occurrence_counts(self) -> None:
        for state in self.states:
            state.occ_count = 0
        for terminal_state in self._terminal_states:
            self.states[terminal_state].occ_count += 1
        self._propagate_occurrence_counts()

    def _rebuild_terminal_states_from_text(self) -> None:
        self._terminal_states = []
        state = 0
        for character in self.text:
            next_state = self.states[state].next.get(character)
            if next_state is None:
                raise ValueError("serialized automaton is inconsistent with its text")
            state = next_state
            self._terminal_states.append(state)

    def _distinct_path_counts(self) -> list[int]:
        if self._substring_count_cache is not None:
            return self._substring_count_cache

        counts = [0] * len(self.states)

        def visit(state_index: int) -> int:
            if counts[state_index] != 0:
                return counts[state_index]
            total = 1
            for target in self.states[state_index].next.values():
                total += visit(target)
            counts[state_index] = total
            return total

        visit(0)
        self._substring_count_cache = counts
        return counts

    def _validate_internal_structure(self) -> None:
        if self.last < 0 or self.last >= len(self.states):
            raise ValueError("serialized automaton has invalid last state")
        if self.states[0].link != -1:
            raise ValueError("root state must link to -1")
        for index, state in enumerate(self.states):
            if state.length < 0:
                raise ValueError(f"state {index} has negative length")
            if state.link < -1 or state.link >= len(self.states):
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
    def _coerce_bool(value: object, field_name: str) -> bool:
        if not isinstance(value, bool):
            raise TypeError(f"{field_name} must be a boolean")
        return value

    @staticmethod
    def _escape_graphviz_label(value: str) -> str:
        return value.encode("unicode_escape").decode("ascii").replace('"', '\\"')

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


def longest_common_substring(strings: Iterable[str]) -> str:
    """Return the longest common substring across two or more strings.

    This builds a suffix automaton for the shortest string, then scans each other
    string to maintain the best match length per state. The final answer is
    reconstructed from the best state.
    """
    items = list(strings)
    if not items:
        raise ValueError("expected at least one string")
    if any(not isinstance(item, str) for item in items):
        raise TypeError("all items must be strings")
    if len(items) == 1:
        return items[0]

    base = min(items, key=len)
    automaton = SuffixAutomaton(base)
    best_per_state = [state.length for state in automaton.states]

    for text in items:
        if text == base:
            continue
        current_state = 0
        current_length = 0
        seen = [0] * len(automaton.states)

        for character in text:
            while current_state != 0 and character not in automaton.states[current_state].next:
                current_state = automaton.states[current_state].link
                current_length = automaton.states[current_state].length
            if character in automaton.states[current_state].next:
                current_state = automaton.states[current_state].next[character]
                current_length += 1
            else:
                current_state = 0
                current_length = 0

            if current_length > seen[current_state]:
                seen[current_state] = current_length

        for state_index in sorted(range(len(automaton.states)), key=lambda idx: automaton.states[idx].length, reverse=True):
            link = automaton.states[state_index].link
            if link >= 0:
                seen[link] = max(seen[link], min(seen[state_index], automaton.states[link].length))

        best_per_state = [min(previous, current) for previous, current in zip(best_per_state, seen)]

    best_state = max(
        range(len(automaton.states)),
        key=lambda index: (best_per_state[index], automaton.states[index].first_pos),
    )
    best_length = best_per_state[best_state]
    if best_length == 0:
        return ""
    end = automaton.states[best_state].first_pos + 1
    start = end - best_length
    return base[start:end]


def longest_common_substring_by_pairs(strings: Sequence[str]) -> dict[tuple[int, int], str]:
    """Compute pairwise longest common substrings for reporting."""
    if any(not isinstance(item, str) for item in strings):
        raise TypeError("all items must be strings")
    results: dict[tuple[int, int], str] = {}
    for left in range(len(strings)):
        for right in range(left + 1, len(strings)):
            results[(left, right)] = longest_common_substring([strings[left], strings[right]])
    return results
