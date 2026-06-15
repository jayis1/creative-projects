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

This is based on the Thompson NFA representation from Russ Cox's
"Regular Expression Matching Can Be Simple And Fast" paper, extended with
anchor states for ^ and $ support.
"""

from __future__ import annotations
from typing import Optional, Callable, List, Set


class State:
    """An NFA state."""
    MATCH = 'match'
    SPLIT = 'split'
    CHAR = 'char'
    ANCHOR_START = 'anchor_start'
    ANCHOR_END = 'anchor_end'

    __slots__ = ('kind', 'out1', 'out2', 'id')
    _counter = 0

    def __init__(self, kind: str, out1=None, out2=None):
        self.kind = kind
        self.out1 = out1  # For SPLIT: State. For CHAR: predicate. For ANCHOR_*: target State.
        self.out2 = out2  # For SPLIT: State. For CHAR: target State. For ANCHOR_*: not used.
        self.id = State._counter
        State._counter += 1

    def __repr__(self):
        kind_names = {
            State.MATCH: 'MATCH', State.SPLIT: 'SPLIT', State.CHAR: 'CHAR',
            State.ANCHOR_START: 'ANCHOR_START', State.ANCHOR_END: 'ANCHOR_END',
        }
        return f"State({self.id}, {kind_names.get(self.kind, self.kind)})"

    @staticmethod
    def match_state() -> 'State':
        return State(State.MATCH)

    @staticmethod
    def split_state(out1: 'State', out2: 'State') -> 'State':
        return State(State.SPLIT, out1, out2)

    @staticmethod
    def char_state(predicate: Callable) -> 'State':
        """Create a CHAR state with the given predicate.

        out1 = predicate (callable), out2 = None (dangling — to be patched).
        """
        return State(State.CHAR, predicate, None)

    @staticmethod
    def anchor_start_state() -> 'State':
        """Create a ^ anchor state. out1 will be patched to target."""
        return State(State.ANCHOR_START, None, None)

    @staticmethod
    def anchor_end_state() -> 'State':
        """Create a $ anchor state. out1 will be patched to target."""
        return State(State.ANCHOR_END, None, None)


class Fragment:
    """An NFA fragment with a start state and unmatched out pointers."""

    __slots__ = ('start', 'outs')

    def __init__(self, start: State, outs: list):
        self.start = start
        self.outs: list = outs  # list of (state, attr_name) to be patched


def patch(outs: list, target: State):
    """Connect all dangling arrows to the target state."""
    for state, attr in outs:
        setattr(state, attr, target)


def append_outs(list1: list, list2: list) -> list:
    """Concatenate two out lists."""
    list1.extend(list2)
    return list1