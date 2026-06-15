"""
Matcher — runs NFA simulation against input text using Thompson's algorithm.

State representation:
  - CHAR state: out1 = predicate (callable), out2 = target State on match
  - SPLIT state: out1, out2 = both States (epsilon transitions taken simultaneously)
  - MATCH state: accepting state (reached = match found)
  - ANCHOR_START state: out1 = target State (epsilon transition if at start/newline)
  - ANCHOR_END state: out1 = target State (epsilon transition if at end/newline)

The two-list algorithm guarantees O(nm) time where n = text length, m = NFA states.

Supports:
  - Match, fullmatch, search, findall, finditer, sub, subn, split
  - Greedy matching (longest match)
  - Anchors (^, $)
"""

from __future__ import annotations
from typing import Optional, List, Tuple
from .nfa import State


class Match:
    """Represents a regex match result."""

    def __init__(self, text: str, start: int, end: int,
                 groups: Optional[List[Optional[Tuple[int, int]]]] = None):
        self.text = text
        self.start = start
        self.end = end
        self._groups = groups or []

    @property
    def matched(self) -> bool:
        return self.start is not None and self.end is not None

    def group(self, n: int = 0) -> Optional[str]:
        """Return matched group. Group 0 is the entire match."""
        if n == 0:
            if self.start is not None and self.end is not None:
                return self.text[self.start:self.end]
            return None
        if 1 <= n <= len(self._groups) and self._groups[n - 1] is not None:
            s, e = self._groups[n - 1]
            return self.text[s:e]
        return None

    def groups(self) -> tuple:
        """Return all captured groups as a tuple."""
        result = []
        for g in self._groups:
            if g is not None:
                result.append(self.text[g[0]:g[1]])
            else:
                result.append(None)
        return tuple(result)

    def span(self, n: int = 0) -> Tuple[int, int]:
        """Return (start, end) of group n."""
        if n == 0:
            return (self.start, self.end)
        if 1 <= n <= len(self._groups) and self._groups[n - 1] is not None:
            return self._groups[n - 1]
        return (-1, -1)

    def __repr__(self):
        if self.start is not None and self.end is not None:
            return f"Match(start={self.start}, end={self.end}, text='{self.text[self.start:self.end]}')"
        return "Match(None)"

    def __bool__(self):
        return self.matched


class Matcher:
    """NFA-based regex matcher using Thompson's two-list algorithm.

    Supports greedy matching (finds the longest match). Anchor states (^ and $)
    are handled during epsilon closure computation with position context.
    """

    def __init__(self, start: State, pattern_str: str = ""):
        self.start = start
        self.pattern_str = pattern_str

    def match(self, text: str) -> Optional[Match]:
        """Match pattern at the start of text (anchored at position 0)."""
        end = self._run_anchored(text, 0)
        if end is not None:
            return Match(text, 0, end)
        return None

    def fullmatch(self, text: str) -> Optional[Match]:
        """Match pattern against the entire text (must consume all input)."""
        end = self._run_anchored(text, 0)
        if end is not None and end == len(text):
            return Match(text, 0, end)
        return None

    def search(self, text: str, start_pos: int = 0) -> Optional[Match]:
        """Search for the first match anywhere in text.

        Tries each starting position until a match is found.
        Returns the leftmost-longest match.
        """
        for start in range(start_pos, len(text) + 1):
            end = self._run_anchored(text, start)
            if end is not None:
                return Match(text, start, end)
        return None

    def findall(self, text: str) -> List[str]:
        """Find all non-overlapping matches of pattern in text."""
        results = []
        pos = 0
        while pos <= len(text):
            end = self._run_anchored(text, pos)
            if end is not None:
                results.append(text[pos:end])
                if end == pos:
                    pos += 1  # avoid infinite loop on zero-length matches
                else:
                    pos = end
            else:
                pos += 1
        return results

    def finditer(self, text: str) -> List[Match]:
        """Find all matches as Match objects."""
        results = []
        pos = 0
        while pos <= len(text):
            end = self._run_anchored(text, pos)
            if end is not None:
                results.append(Match(text, pos, end))
                if end == pos:
                    pos += 1
                else:
                    pos = end
            else:
                pos += 1
        return results

    def sub(self, repl: str, text: str, count: int = 0) -> str:
        """Replace occurrences of pattern in text with repl."""
        result = []
        pos = 0
        num_subs = 0
        while pos <= len(text):
            end = self._run_anchored(text, pos)
            if end is not None:
                result.append(repl)
                if end == pos:
                    if pos < len(text):
                        result.append(text[pos])
                    pos = end + 1
                else:
                    pos = end
                num_subs += 1
                if count > 0 and num_subs >= count:
                    result.append(text[pos:])
                    break
            else:
                if pos < len(text):
                    result.append(text[pos])
                pos += 1
        return ''.join(result)

    def subn(self, repl: str, text: str, count: int = 0) -> Tuple[str, int]:
        """Replace occurrences and return (new_string, number_of_subs)."""
        result = []
        pos = 0
        num_subs = 0
        while pos <= len(text):
            end = self._run_anchored(text, pos)
            if end is not None:
                result.append(repl)
                if end == pos:
                    if pos < len(text):
                        result.append(text[pos])
                    pos = end + 1
                else:
                    pos = end
                num_subs += 1
                if count > 0 and num_subs >= count:
                    result.append(text[pos:])
                    break
            else:
                if pos < len(text):
                    result.append(text[pos])
                pos += 1
        return (''.join(result), num_subs)

    def split(self, text: str, maxsplit: int = 0) -> List[str]:
        """Split text by occurrences of pattern."""
        result = []
        last_end = 0
        pos = 0
        num_splits = 0

        while pos <= len(text):
            end = self._run_anchored(text, pos)
            if end is not None and end != pos:
                result.append(text[last_end:pos])
                last_end = end
                pos = end
                num_splits += 1
                if maxsplit > 0 and num_splits >= maxsplit:
                    break
            elif end is not None and end == pos:
                pos += 1
            else:
                pos += 1

        result.append(text[last_end:])
        return result

    def _run_anchored(self, text: str, start_pos: int) -> Optional[int]:
        """Run anchored NFA simulation starting at start_pos.

        Uses Thompson's two-list algorithm with anchor state support.
        ANCHOR_START states are only satisfied at position 0 (or after newline).
        ANCHOR_END states are only satisfied at the end of string (or before newline).

        Returns the end position of the longest match, or None.
        """
        # Compute initial state set (epsilon closure from start, with position context)
        current = []
        self._add_state(current, self.start, text, start_pos)

        last_match = None

        # Check if we start in a match state (e.g., empty pattern or a*)
        for s in current:
            if s.kind == State.MATCH:
                last_match = start_pos

        # Process each character
        for i in range(start_pos, len(text)):
            ch = text[i]

            # Step: for each CHAR state, try the character
            next_states = []
            seen = set()
            for s in current:
                if s.kind == State.CHAR and callable(s.out1):
                    if s.out1(ch):
                        target = s.out2
                        if target is not None:
                            self._add_state_to(next_states, target, seen, text, i + 1)

            if not next_states:
                break

            current = next_states

            # Check for match (greedy: record but keep going)
            for s in current:
                if s.kind == State.MATCH:
                    last_match = i + 1
                    break

        return last_match

    def _add_state(self, state_list: list, state: State, text: str, pos: int):
        """Add a state and all epsilon-reachable states to the list.

        Handles SPLIT (unconditional epsilon) and ANCHOR states (conditional epsilon).
        ANCHOR_START is followed only if pos == 0 or preceded by newline.
        ANCHOR_END is followed only if pos == len(text) or next char is newline.
        """
        seen = set()

        def _walk(s):
            if s is None or id(s) in seen:
                return
            seen.add(id(s))

            if s.kind == State.SPLIT:
                state_list.append(s)
                if s.out1 is not None:
                    _walk(s.out1)
                if s.out2 is not None:
                    _walk(s.out2)
            elif s.kind == State.ANCHOR_START:
                # ^ anchor: succeed at position 0 or after newline
                if pos == 0 or (pos > 0 and text[pos - 1] == '\n'):
                    state_list.append(s)
                    if s.out1 is not None:
                        _walk(s.out1)
                # else: this anchor doesn't match at this position, skip it
            elif s.kind == State.ANCHOR_END:
                # $ anchor: succeed at end of string or before newline
                if pos == len(text) or (pos < len(text) and text[pos] == '\n'):
                    state_list.append(s)
                    if s.out1 is not None:
                        _walk(s.out1)
                # else: this anchor doesn't match at this position, skip it
            else:
                # CHAR or MATCH: don't follow epsilon (not an epsilon state)
                state_list.append(s)

        _walk(state)

    def _add_state_to(self, state_list: list, state: State, seen: set,
                      text: str, pos: int):
        """Add a state and its epsilon closure to state_list, using seen set for dedup.

        Handles ANCHOR_START and ANCHOR_END during epsilon closure.
        """
        if state is None or id(state) in seen:
            return
        seen.add(id(state))

        if state.kind == State.SPLIT:
            state_list.append(state)
            if state.out1 is not None:
                self._add_state_to(state_list, state.out1, seen, text, pos)
            if state.out2 is not None:
                self._add_state_to(state_list, state.out2, seen, text, pos)
        elif state.kind == State.ANCHOR_START:
            if pos == 0 or (pos > 0 and text[pos - 1] == '\n'):
                state_list.append(state)
                if state.out1 is not None:
                    self._add_state_to(state_list, state.out1, seen, text, pos)
        elif state.kind == State.ANCHOR_END:
            if pos == len(text) or (pos < len(text) and text[pos] == '\n'):
                state_list.append(state)
                if state.out1 is not None:
                    self._add_state_to(state_list, state.out1, seen, text, pos)
        else:
            state_list.append(state)