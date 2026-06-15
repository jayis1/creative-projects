"""
NFA (Nondeterministic Finite Automaton) for Thompson's construction.

State types:
  - MATCH: accepting state (matched!)
  - SPLIT: two epsilon transitions (out1, out2) — taken simultaneously
  - CHAR: transitions on a character that satisfies a predicate.
    For CHAR states:
      - out1 = the predicate function (callable) that tests if a char matches
      - out2 = the target State to transition to on match (dangling until patched)
  - ANCHOR_START: epsilon transition that only succeeds at position 0 (or after newline)
      - out1 = target State (epsilon transition on anchor match)
  - ANCHOR_END: epsilon transition that only succeeds at end of string (or before newline)
      - out1 = target State (epsilon transition on anchor match)
  - GROUP_START: marks the start of a capture group
      - out1 = target State, group_idx = capture group index
  - GROUP_END: marks the end of a capture group
      - out1 = target State, group_idx = capture group index

This is based on the Thompson NFA representation from Russ Cox's
"Regular Expression Matching Can Be Simple And Fast" paper, extended with
anchor states for ^ and $ support and group states for capture groups.

Performance guarantee:
  - O(m) states where m is the pattern length
  - O(nm) matching time where n is the text length
  - No exponential backtracking
"""

from __future__ import annotations

import logging
from typing import Optional, Callable, List, Set

logger = logging.getLogger(__name__)


class State:
    """An NFA state.

    Uses __slots__ for memory efficiency since many State objects
    are created during compilation.
    """
    MATCH = 'match'
    SPLIT = 'split'
    CHAR = 'char'
    ANCHOR_START = 'anchor_start'
    ANCHOR_END = 'anchor_end'
    GROUP_START = 'group_start'
    GROUP_END = 'group_end'

    __slots__ = ('kind', 'out1', 'out2', 'id', 'group_idx')
    _counter = 0

    def __init__(self, kind: str, out1=None, out2=None, group_idx: int = -1):
        if kind not in (State.MATCH, State.SPLIT, State.CHAR,
                        State.ANCHOR_START, State.ANCHOR_END,
                        State.GROUP_START, State.GROUP_END):
            raise ValueError(f"Invalid state kind: {kind!r}")
        self.kind = kind
        self.out1 = out1  # For SPLIT: State. For CHAR: predicate. For ANCHOR_*/GROUP_*: target State.
        self.out2 = out2  # For SPLIT: State. For CHAR: target State. For ANCHOR_*/GROUP_*: not used.
        self.id = State._counter
        self.group_idx = group_idx  # For GROUP_START/GROUP_END: capture group index
        State._counter += 1

    def __repr__(self) -> str:
        kind_names = {
            State.MATCH: 'MATCH', State.SPLIT: 'SPLIT', State.CHAR: 'CHAR',
            State.ANCHOR_START: 'ANCHOR_START', State.ANCHOR_END: 'ANCHOR_END',
            State.GROUP_START: 'GROUP_START', State.GROUP_END: 'GROUP_END',
        }
        name = kind_names.get(self.kind, self.kind)
        if self.kind in (State.GROUP_START, State.GROUP_END):
            return f"State({self.id}, {name}, group={self.group_idx})"
        return f"State({self.id}, {name})"

    @staticmethod
    def match_state() -> 'State':
        """Create a MATCH (accepting) state."""
        return State(State.MATCH)

    @staticmethod
    def split_state(out1: 'State', out2: 'State') -> 'State':
        """Create a SPLIT state with two epsilon transitions."""
        return State(State.SPLIT, out1, out2)

    @staticmethod
    def char_state(predicate: Callable) -> 'State':
        """Create a CHAR state with the given predicate.

        out1 = predicate (callable), out2 = None (dangling — to be patched).
        """
        if not callable(predicate):
            raise TypeError(f"CHAR state predicate must be callable, got {type(predicate)}")
        return State(State.CHAR, predicate, None)

    @staticmethod
    def anchor_start_state() -> 'State':
        """Create a ^ anchor state. out1 will be patched to target."""
        return State(State.ANCHOR_START, None, None)

    @staticmethod
    def anchor_end_state() -> 'State':
        """Create a $ anchor state. out1 will be patched to target."""
        return State(State.ANCHOR_END, None, None)

    @staticmethod
    def group_start_state(group_idx: int) -> 'State':
        """Create a GROUP_START state. out1 will be patched to target."""
        return State(State.GROUP_START, None, None, group_idx=group_idx)

    @staticmethod
    def group_end_state(group_idx: int) -> 'State':
        """Create a GROUP_END state. out1 will be patched to target."""
        return State(State.GROUP_END, None, None, group_idx=group_idx)


class Fragment:
    """An NFA fragment with a start state and unmatched out pointers.

    The 'outs' list contains (state, attr_name) tuples representing
    dangling arrows that need to be patched to a target state.
    """
    __slots__ = ('start', 'outs')

    def __init__(self, start: State, outs: list):
        self.start = start
        self.outs: list = outs  # list of (state, attr_name) to be patched

    def __repr__(self) -> str:
        return f"Fragment(start=State({self.start.id}), outs={len(self.outs)} dangling)"


def patch(outs: list, target: State) -> None:
    """Connect all dangling arrows to the target state.

    For each (state, attr_name) pair in outs, sets state.attr_name = target.
    This is the core wiring mechanism of Thompson's construction.
    """
    for state, attr in outs:
        setattr(state, attr, target)


def append_outs(list1: list, list2: list) -> list:
    """Concatenate two out lists. Modifies list1 in place and returns it."""
    list1.extend(list2)
    return list1


def count_states(start: State) -> int:
    """Count the total number of reachable NFA states from start.

    Useful for debugging and performance analysis.
    """
    visited: Set[int] = set()

    def _walk(s: Optional[State]) -> None:
        if s is None or id(s) in visited:
            return
        visited.add(id(s))
        if s.kind == State.CHAR:
            if callable(s.out1):
                _walk(s.out2)
            else:
                _walk(s.out1)
                _walk(s.out2)
        elif s.kind == State.SPLIT:
            _walk(s.out1)
            _walk(s.out2)
        elif s.kind in (State.ANCHOR_START, State.ANCHOR_END,
                        State.GROUP_START, State.GROUP_END):
            _walk(s.out1)
        # MATCH: no outgoing edges

    _walk(start)
    return len(visited)