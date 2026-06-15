"""
Matcher — runs NFA simulation against input text using Thompson's algorithm.

State representation:
  - CHAR state: out1 is a predicate function (matches a character), out2 is
    the target State to transition to on match.
  - SPLIT state: out1 and out2 are both States (epsilon transitions taken
    simultaneously).
  - MATCH state: accepting state (reached = match found).

The two-list algorithm guarantees O(nm) time.
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
        if n == 0:
            if self.start is not None and self.end is not None:
                return self.text[self.start:self.end]
            return None
        if 1 <= n <= len(self._groups) and self._groups[n - 1] is not None:
            s, e = self._groups[n - 1]
            return self.text[s:e]
        return None

    def groups(self) -> tuple:
        result = []
        for g in self._groups:
            if g is not None:
                result.append(self.text[g[0]:g[1]])
            else:
                result.append(None)
        return tuple(result)

    def span(self, n: int = 0) -> Tuple[int, int]:
        if n == 0:
            return (self.start, self.end)
        if 1 <= n <= len(self._groups) and self._groups[n - 1] is not None:
            return self._groups[n - 1]
        return (-1, -1)

    def __repr__(self):
        if self.start is not None and self.end is not None:
            return f"Match(start={self.start}, end={self.end}, text='{self.text[self.start:self.end]}')"
        return "Match(None)"


class Matcher:
    """NFA-based regex matcher using Thompson's two-list algorithm."""

    def __init__(self, start: State, pattern_str: str = ""):
        self.start = start
        self.pattern_str = pattern_str

    def match(self, text: str) -> Optional[Match]:
        """Match pattern at the start of text."""
        end = self._run_anchored(text, 0)
        if end is not None:
            return Match(text, 0, end)
        return None

    def fullmatch(self, text: str) -> Optional[Match]:
        """Match the entire text."""
        end = self._run_anchored(text, 0)
        if end is not None and end == len(text):
            return Match(text, 0, end)
        return None

    def search(self, text: str, start_pos: int = 0) -> Optional[Match]:
        """Search for the first match anywhere in text."""
        for start in range(start_pos, len(text) + 1):
            end = self._run_anchored(text, start)
            if end is not None:
                return Match(text, start, end)
        return None

    def findall(self, text: str) -> List[str]:
        """Find all non-overlapping matches."""
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
        """Replace matches with repl."""
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
                    # Append remaining text after last substitution
                    result.append(text[pos:])
                    break
            else:
                if pos < len(text):
                    result.append(text[pos])
                pos += 1
        return ''.join(result)

    def split(self, text: str, maxsplit: int = 0) -> List[str]:
        """Split text by pattern."""
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

        Uses Thompson's two-list algorithm:
          1. Start with epsilon closure of start state
          2. For each character, step all CHAR states whose predicates match
          3. Take epsilon closure of resulting states
          4. If any state is MATCH, record the position

        Returns the end position of the longest match, or None.
        """
        # Build initial state list from epsilon closure of start state
        current = []  # list of State objects
        self._add_state(current, self.start)

        last_match = None

        # Check if start state is already a match
        for s in current:
            if s.kind == State.MATCH:
                last_match = start_pos

        for i in range(start_pos, len(text)):
            ch = text[i]

            # Step: for each CHAR state, check if the character matches
            next_states = []
            for s in current:
                if s.kind == State.CHAR and callable(s.out1):
                    if s.out1(ch):
                        # Transition to the target state (stored in out2)
                        target = s.out2
                        if target is not None:
                            self._add_state(next_states, target)

            if not next_states:
                break

            current = next_states

            # Check for match
            for s in current:
                if s.kind == State.MATCH:
                    last_match = i + 1
                    break

        return last_match

    def _add_state(self, state_list: list, state: State):
        """Add a state and all epsilon-reachable states to the list.

        Uses object identity (id()) to avoid duplicates.
        """
        seen = set()

        def _walk(s):
            if s is None or id(s) in seen:
                return
            seen.add(id(s))
            state_list.append(s)

            if s.kind == State.SPLIT:
                # Epsilon transitions — follow both branches
                if s.out1 is not None:
                    _walk(s.out1)
                if s.out2 is not None:
                    _walk(s.out2)
            # CHAR and MATCH states are terminal for epsilon closure

        _walk(state)