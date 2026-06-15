"""
Matcher — runs NFA simulation against input text using Thompson's algorithm.

State representation:
  - CHAR state: out1 = predicate (callable), out2 = target State on match
  - SPLIT state: out1, out2 = both States (epsilon transitions taken simultaneously)
  - MATCH state: accepting state (reached = match found)
  - ANCHOR_START state: out1 = target State (epsilon transition if at start/newline)
  - ANCHOR_END state: out1 = target State (epsilon transition if at end/newline)
  - GROUP_START state: out1 = target State, group_idx = capture group index
  - GROUP_END state: out1 = target State, group_idx = capture group index

The two-list algorithm guarantees O(nm) time where n = text length, m = NFA states.

Capture groups are tracked by recording the positions at which GROUP_START
and GROUP_END states are traversed during the greedy match. Since Thompson's
algorithm always finds the leftmost-longest match, the last occurrence of
each group marker at each step corresponds to the correct group boundary.

Supports:
  - Match, fullmatch, search, findall, finditer, sub, subn, split
  - Capture groups with group extraction
  - Greedy matching (longest match)
  - Anchors (^, $)
  - Input validation and error messages
"""

from __future__ import annotations

import logging
from typing import Optional, List, Tuple

from .nfa import State

logger = logging.getLogger(__name__)


class Match:
    """Represents a regex match result.

    Compatible with Python's re.Match interface (subset).

    Attributes:
        text: The original text that was searched.
        start: Start position of the match (None if no match).
        end: End position of the match (None if no match).
    """

    def __init__(self, text: str, start: int, end: int,
                 groups: Optional[List[Optional[Tuple[int, int]]]] = None):
        if not isinstance(text, str):
            raise TypeError(f"text must be str, got {type(text).__name__}")
        self.text = text
        self.start = start
        self.end = end
        self._groups = groups or []

    @property
    def matched(self) -> bool:
        """Return True if the match was successful."""
        return self.start is not None and self.end is not None

    def group(self, n: int = 0) -> Optional[str]:
        """Return matched group. Group 0 is the entire match.

        Args:
            n: Group number. 0 for the entire match, 1+ for capture groups.

        Returns:
            The matched string, or None if the group didn't participate.

        Raises:
            IndexError: If n is out of range.
        """
        if n < 0:
            raise IndexError(f"group number must be >= 0, got {n}")
        if n == 0:
            if self.start is not None and self.end is not None:
                return self.text[self.start:self.end]
            return None
        if 1 <= n <= len(self._groups) and self._groups[n - 1] is not None:
            s, e = self._groups[n - 1]
            return self.text[s:e]
        if n > len(self._groups):
            raise IndexError(f"no such group: group {n}")
        return None

    def groups(self, default: Optional[str] = None) -> tuple:
        """Return all captured groups as a tuple.

        Args:
            default: Value to use for groups that didn't participate in the match.

        Returns:
            Tuple of captured group strings (or default for unmatched groups).
        """
        result = []
        for g in self._groups:
            if g is not None:
                result.append(self.text[g[0]:g[1]])
            else:
                result.append(default)
        return tuple(result)

    def span(self, n: int = 0) -> Tuple[int, int]:
        """Return (start, end) of group n.

        Args:
            n: Group number. 0 for the entire match.

        Returns:
            Tuple of (start, end) positions.
        """
        if n < 0:
            raise IndexError(f"group number must be >= 0, got {n}")
        if n == 0:
            return (self.start, self.end)
        if 1 <= n <= len(self._groups) and self._groups[n - 1] is not None:
            return self._groups[n - 1]
        if n > len(self._groups):
            raise IndexError(f"no such group: group {n}")
        return (-1, -1)

    def lastindex(self) -> Optional[int]:
        """Return the last matched group index, or None if no groups."""
        for i in range(len(self._groups) - 1, -1, -1):
            if self._groups[i] is not None:
                return i + 1
        return None

    def __repr__(self) -> str:
        if self.start is not None and self.end is not None:
            matched_text = self.text[self.start:self.end]
            # Truncate long matches in repr
            if len(matched_text) > 40:
                matched_text = matched_text[:37] + "..."
            return f"Match(start={self.start}, end={self.end}, text='{matched_text}')"
        return "Match(None)"

    def __bool__(self) -> bool:
        return self.matched

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Match):
            return NotImplemented
        return (self.text == other.text and
                self.start == other.start and
                self.end == other.end and
                self._groups == other._groups)


class Matcher:
    """NFA-based regex matcher using Thompson's two-list algorithm.

    Supports greedy matching (finds the longest match), capture groups,
    and anchor states (^ and $).

    The matcher is created from a compiled NFA start state and provides
    a re-like interface for matching operations.

    Args:
        start: The NFA start state.
        pattern_str: The original pattern string (for error messages).
        num_groups: Number of capture groups in the pattern.
    """

    def __init__(self, start: State, pattern_str: str = "", num_groups: int = 0):
        if not isinstance(start, State):
            raise TypeError(f"start must be a State, got {type(start).__name__}")
        self.start = start
        self.pattern_str = pattern_str
        self.num_groups = num_groups

    def match(self, text: str) -> Optional[Match]:
        """Match pattern at the start of text (anchored at position 0).

        Args:
            text: The text to match against.

        Returns:
            A Match object if the pattern matches, None otherwise.
        """
        if not isinstance(text, str):
            raise TypeError(f"text must be str, got {type(text).__name__}")
        end = self._run_anchored(text, 0)
        if end is not None:
            groups = self._extract_groups(text, 0, end)
            return Match(text, 0, end, groups)
        return None

    def fullmatch(self, text: str) -> Optional[Match]:
        """Match pattern against the entire text (must consume all input).

        Args:
            text: The text to match against.

        Returns:
            A Match object if the entire text matches, None otherwise.
        """
        if not isinstance(text, str):
            raise TypeError(f"text must be str, got {type(text).__name__}")
        end = self._run_anchored(text, 0)
        if end is not None and end == len(text):
            groups = self._extract_groups(text, 0, end)
            return Match(text, 0, end, groups)
        return None

    def search(self, text: str, start_pos: int = 0) -> Optional[Match]:
        """Search for the first match anywhere in text.

        Tries each starting position until a match is found.
        Returns the leftmost-longest match.

        Args:
            text: The text to search in.
            start_pos: Starting position for the search.

        Returns:
            A Match object if found, None otherwise.

        Raises:
            ValueError: If start_pos is negative.
        """
        if not isinstance(text, str):
            raise TypeError(f"text must be str, got {type(text).__name__}")
        if start_pos < 0:
            raise ValueError(f"start_pos must be >= 0, got {start_pos}")
        start_pos = min(start_pos, len(text))
        for start in range(start_pos, len(text) + 1):
            end = self._run_anchored(text, start)
            if end is not None:
                groups = self._extract_groups(text, start, end)
                return Match(text, start, end, groups)
        return None

    def findall(self, text: str) -> List[str]:
        """Find all non-overlapping matches of pattern in text.

        If the pattern contains capture groups, returns a list of
        group strings (or tuples of groups for multiple groups).

        Args:
            text: The text to search in.

        Returns:
            List of matched strings (or tuples for capture groups).
        """
        if not isinstance(text, str):
            raise TypeError(f"text must be str, got {type(text).__name__}")
        results = []
        pos = 0
        while pos <= len(text):
            end = self._run_anchored(text, pos)
            if end is not None:
                groups = self._extract_groups(text, pos, end)
                if self.num_groups > 0 and groups:
                    # Return group contents per re.findall convention
                    if self.num_groups == 1:
                        g = groups[0]
                        results.append(text[g[0]:g[1]] if g else "")
                    else:
                        group_strs = []
                        for g in groups:
                            group_strs.append(text[g[0]:g[1]] if g else "")
                        results.append(tuple(group_strs))
                else:
                    results.append(text[pos:end])
                if end == pos:
                    pos += 1  # avoid infinite loop on zero-length matches
                else:
                    pos = end
            else:
                pos += 1
        return results

    def finditer(self, text: str) -> List[Match]:
        """Find all matches as Match objects.

        Args:
            text: The text to search in.

        Returns:
            List of Match objects.
        """
        if not isinstance(text, str):
            raise TypeError(f"text must be str, got {type(text).__name__}")
        results = []
        pos = 0
        while pos <= len(text):
            end = self._run_anchored(text, pos)
            if end is not None:
                groups = self._extract_groups(text, pos, end)
                results.append(Match(text, pos, end, groups))
                if end == pos:
                    pos += 1
                else:
                    pos = end
            else:
                pos += 1
        return results

    def sub(self, repl: str, text: str, count: int = 0) -> str:
        """Replace occurrences of pattern in text with repl.

        Supports backreferences like \\1, \\2, etc. in the replacement string.

        Args:
            repl: Replacement string. Can contain \\1, \\2, etc. for group refs.
            text: The text to search in.
            count: Maximum number of replacements (0 = unlimited).

        Returns:
            The resulting string after replacements.
        """
        if not isinstance(repl, str):
            raise TypeError(f"repl must be str, got {type(repl).__name__}")
        if not isinstance(text, str):
            raise TypeError(f"text must be str, got {type(text).__name__}")
        if count < 0:
            raise ValueError(f"count must be >= 0, got {count}")

        result = []
        pos = 0
        num_subs = 0
        while pos <= len(text):
            end = self._run_anchored(text, pos)
            if end is not None:
                groups = self._extract_groups(text, pos, end)
                expanded = self._expand_repl(repl, text, pos, end, groups)
                result.append(expanded)
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
        """Replace occurrences and return (new_string, number_of_subs).

        Args:
            repl: Replacement string.
            text: The text to search in.
            count: Maximum number of replacements (0 = unlimited).

        Returns:
            Tuple of (resulting_string, number_of_substitutions).
        """
        if not isinstance(repl, str):
            raise TypeError(f"repl must be str, got {type(repl).__name__}")
        if not isinstance(text, str):
            raise TypeError(f"text must be str, got {type(text).__name__}")
        if count < 0:
            raise ValueError(f"count must be >= 0, got {count}")

        result = []
        pos = 0
        num_subs = 0
        while pos <= len(text):
            end = self._run_anchored(text, pos)
            if end is not None:
                groups = self._extract_groups(text, pos, end)
                expanded = self._expand_repl(repl, text, pos, end, groups)
                result.append(expanded)
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
        """Split text by occurrences of pattern.

        Args:
            text: The text to split.
            maxsplit: Maximum number of splits (0 = unlimited).

        Returns:
            List of string segments.
        """
        if not isinstance(text, str):
            raise TypeError(f"text must be str, got {type(text).__name__}")
        if maxsplit < 0:
            raise ValueError(f"maxsplit must be >= 0, got {maxsplit}")

        result = []
        last_end = 0
        pos = 0
        num_splits = 0

        while pos <= len(text):
            end = self._run_anchored(text, pos)
            if end is not None:
                if end != pos:
                    # Non-zero-length match
                    result.append(text[last_end:pos])
                    last_end = end
                    pos = end
                else:
                    # Zero-length match: split at current position
                    result.append(text[last_end:pos])
                    last_end = pos
                    pos += 1
                num_splits += 1
                if maxsplit > 0 and num_splits >= maxsplit:
                    break
            else:
                pos += 1

        result.append(text[last_end:])
        return result

    def _expand_repl(self, repl: str, text: str, start: int,
                     end: int, groups: Optional[list]) -> str:
        """Expand backreferences in a replacement string.

        Supports \\1, \\2, etc. for group references and \\0 for the entire match.
        """
        result = []
        i = 0
        while i < len(repl):
            if repl[i] == '\\' and i + 1 < len(repl):
                next_ch = repl[i + 1]
                if next_ch.isdigit():
                    # \N backreference
                    j = i + 1
                    while j < len(repl) and repl[j].isdigit():
                        j += 1
                    group_num = int(repl[i + 1:j])
                    if group_num == 0:
                        result.append(text[start:end])
                    elif groups is not None and 1 <= group_num <= len(groups) and groups[group_num - 1] is not None:
                        gs, ge = groups[group_num - 1]
                        result.append(text[gs:ge])
                    else:
                        result.append(repl[i:j])
                    i = j
                    continue
                elif next_ch == '\\':
                    result.append('\\')
                    i += 2
                    continue
                elif next_ch == 'n':
                    result.append('\n')
                    i += 2
                    continue
                elif next_ch == 't':
                    result.append('\t')
                    i += 2
                    continue
            result.append(repl[i])
            i += 1
        return ''.join(result)

    def _run_anchored(self, text: str, start_pos: int) -> Optional[int]:
        """Run anchored NFA simulation starting at start_pos.

        Uses Thompson's two-list algorithm with anchor state support.
        ANCHOR_START states are only satisfied at position 0 or after newline.
        ANCHOR_END states are only satisfied at end of string or before newline.

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

        # After processing all characters, check anchor end transitions
        end_seen = set()
        end_states = []
        for s in current:
            if s.kind == State.ANCHOR_END:
                self._add_state_to(end_states, s.out1, end_seen, text, len(text))

        for s in end_states:
            if s.kind == State.MATCH:
                last_match = len(text)
                break

        return last_match

    def _extract_groups(self, text: str, start_pos: int, end_pos: int) -> Optional[list]:
        """Extract capture group boundaries by re-running the NFA with group tracking.

        This does a second pass through the NFA, tracking GROUP_START and GROUP_END
        states to determine the boundaries of each capture group.

        Returns:
            List of (start, end) tuples for each group, or None if no groups.
        """
        if self.num_groups == 0:
            return None

        # Initialize group tracking
        group_starts = [None] * self.num_groups  # position where each group starts
        group_ends = [None] * self.num_groups    # position where each group ends

        current = []
        self._add_state(current, self.start, text, start_pos)

        # Track group states in the current set
        # GROUP_START at position means group starts at this text position
        # GROUP_END at position means group ends at this text position
        for s in current:
            if s.kind == State.GROUP_START:
                group_starts[s.group_idx] = start_pos
            if s.kind == State.GROUP_END:
                group_ends[s.group_idx] = start_pos

        # Check initial match
        for s in current:
            if s.kind == State.MATCH:
                # Match at start - set any groups that haven't been set yet
                for i in range(self.num_groups):
                    if group_starts[i] is None:
                        pass  # group didn't participate
                    if group_ends[i] is None and group_starts[i] is not None:
                        group_ends[i] = start_pos

        for i in range(start_pos, min(end_pos, len(text))):
            ch = text[i]

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

            # Track group boundaries at this step
            for s in current:
                if s.kind == State.GROUP_START:
                    idx = s.group_idx
                    group_starts[idx] = i + 1
                if s.kind == State.GROUP_END:
                    idx = s.group_idx
                    group_ends[idx] = i + 1

            # Check for match
            for s in current:
                if s.kind == State.MATCH:
                    for idx in range(self.num_groups):
                        if group_starts[idx] is not None and group_ends[idx] is None:
                            group_ends[idx] = i + 1

        # Build result
        result = []
        for i in range(self.num_groups):
            if group_starts[i] is not None and group_ends[i] is not None:
                result.append((group_starts[i], group_ends[i]))
            else:
                result.append(None)

        return result

    def _add_state(self, state_list: list, state: State, text: str, pos: int):
        """Add a state and all epsilon-reachable states to the list.

        Handles SPLIT (unconditional epsilon) and ANCHOR states (conditional epsilon).
        ANCHOR_START is followed only if pos == 0 or preceded by newline.
        ANCHOR_END is followed only if pos == len(text) or next char is newline.
        """
        seen = set()
        self._add_state_to(state_list, state, seen, text, pos)

    def _add_state_to(self, state_list: list, state: State, seen: set,
                      text: str, pos: int):
        """Add a state and its epsilon closure to state_list, using seen set for dedup.

        Handles SPLIT, ANCHOR_START, ANCHOR_END, GROUP_START, and GROUP_END
        during epsilon closure computation.
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
            # ^ anchor: succeed at position 0 or after newline
            if pos == 0 or (pos > 0 and text[pos - 1] == '\n'):
                state_list.append(state)
                if state.out1 is not None:
                    self._add_state_to(state_list, state.out1, seen, text, pos)
        elif state.kind == State.ANCHOR_END:
            # $ anchor: succeed at end of string or before newline
            if pos == len(text) or (pos < len(text) and text[pos] == '\n'):
                state_list.append(state)
                if state.out1 is not None:
                    self._add_state_to(state_list, state.out1, seen, text, pos)
        elif state.kind == State.GROUP_START:
            state_list.append(state)
            if state.out1 is not None:
                self._add_state_to(state_list, state.out1, seen, text, pos)
        elif state.kind == State.GROUP_END:
            state_list.append(state)
            if state.out1 is not None:
                self._add_state_to(state_list, state.out1, seen, text, pos)
        else:
            # CHAR or MATCH: don't follow epsilon (not an epsilon state)
            state_list.append(state)