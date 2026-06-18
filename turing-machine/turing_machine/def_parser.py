"""
turing_machine.def_parser
=========================

A small definition language for declaring Turing machines in a human-readable
text format.  Example::

    # binary incrementer
    blank: _
    start: s0
    halt:  halt

    # transitions:  state  read  ->  write  move  new_state
    s0  0 -> 0 R s0
    s0  1 -> 1 R s0
    s0  _ -> 1 L s1
    s1  0 -> 1 L halt
    s1  1 -> 0 L s1
    s1  _ -> 1 R halt

The parser produces a :class:`MachineDef` which can be converted to a
:class:`Program` and :class:`TuringMachine`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, Hashable, List, Optional, Tuple

from .machine import Program, TMDirection, Transition


class ParseError(Exception):
    """Raised when the definition language cannot be parsed."""


@dataclass
class MachineDef:
    """A parsed machine definition."""
    blank: Hashable = "_"
    start_state: str = "q0"
    halt_states: set = field(default_factory=lambda: {"halt"})
    transitions: List[Transition] = field(default_factory=list)
    num_tapes: int = 1
    comment: str = ""

    def to_program(self) -> Program:
        return Program(self.transitions)

    def to_machine(self, tape=None, max_steps: int = 1_000_000):
        from .machine import TuringMachine
        return TuringMachine(
            self.to_program(),
            initial_state=self.start_state,
            tape=tape,
            blank=self.blank,
            halt_states=self.halt_states,
            max_steps=max_steps,
            num_tapes=self.num_tapes,
        )


class Parser:
    """Parse the Turing machine definition language.

    Grammar (one rule per line)::

        <directive>  ::= blank ':' <symbol>
                       | start ':' <state>
                       | halt  ':' <state-list>
                       | tapes ':' <int>
                       | comment ':' <text>
        <transition> ::= <state> <read> '->' <write> <move> <new_state>

    Multi-tape transitions use parenthesized tuples for read/write/move::

        q0 (0 _) -> (1 0) (R S) q1
    """

    _DIRECTIVE_RE = re.compile(r"^\s*(blank|start|halt|tapes|comment)\s*:\s*(.+)$", re.IGNORECASE)
    _COMMENT_RE = re.compile(r"^\s*(#|//)")

    def parse(self, text: str) -> MachineDef:
        lines = text.splitlines()
        md = MachineDef()
        for lineno, raw in enumerate(lines, 1):
            line = raw.strip()
            if not line:
                continue
            # Strip inline comments
            if "#" in line:
                line = line.split("#", 1)[0].strip()
                if not line:
                    continue
            elif line.startswith("//"):
                continue
            if not line:
                continue

            m = self._DIRECTIVE_RE.match(line)
            if m:
                key = m.group(1).lower()
                val = m.group(2).strip()
                self._apply_directive(md, key, val, lineno)
                continue

            # Try transition
            try:
                t = self._parse_transition(line, md.num_tapes, lineno)
                md.transitions.append(t)
            except ParseError:
                raise
            except Exception as exc:
                raise ParseError(f"line {lineno}: {exc}") from exc
        return md

    def _apply_directive(self, md: MachineDef, key: str, val: str, lineno: int) -> None:
        if key == "blank":
            md.blank = self._parse_symbol(val)
        elif key == "start":
            md.start_state = val.split()[0]
        elif key == "halt":
            md.halt_states = set(v.strip() for v in val.replace(",", " ").split())
        elif key == "tapes":
            try:
                md.num_tapes = int(val)
            except ValueError:
                raise ParseError(f"line {lineno}: 'tapes' requires an integer, got {val!r}")
        elif key == "comment":
            md.comment = val

    @staticmethod
    def _parse_symbol(s: str) -> Hashable:
        s = s.strip()
        if s == "":
            return "_"
        # Support quoted symbols
        if (s.startswith("'") and s.endswith("'")) or (s.startswith('"') and s.endswith('"')):
            return s[1:-1]
        # Treat as bare token
        return s

    def _parse_symbol_list(self, s: str) -> List[Hashable]:
        s = s.strip()
        if s.startswith("(") and s.endswith(")"):
            s = s[1:-1].strip()
            if not s:
                return []
            parts = self._split_symbols(s)
        else:
            parts = s.split()
        return [self._parse_symbol(p) for p in parts]

    @staticmethod
    def _split_symbols(s: str) -> List[str]:
        """Split a tuple body on whitespace, respecting quoted strings."""
        parts = []
        cur = ""
        in_quote = None
        for ch in s:
            if in_quote:
                cur += ch
                if ch == in_quote:
                    in_quote = None
            elif ch in ("'", '"'):
                in_quote = ch
                cur += ch
            elif ch.isspace():
                if cur:
                    parts.append(cur)
                    cur = ""
            else:
                cur += ch
        if cur:
            parts.append(cur)
        return parts

    def _parse_direction(self, s: str) -> TMDirection:
        return TMDirection.parse(s)

    def _parse_direction_list(self, s: str) -> Tuple[TMDirection, ...]:
        s = s.strip()
        if s.startswith("(") and s.endswith(")"):
            s = s[1:-1].strip()
            if not s:
                return tuple()
            parts = s.split()
        else:
            parts = s.split()
        return tuple(TMDirection.parse(p) for p in parts)

    def _parse_transition(self, line: str, num_tapes: int, lineno: int) -> Transition:
        if "->" not in line:
            raise ParseError(f"line {lineno}: expected '->' in transition: {line!r}")
        left, right = line.split("->", 1)
        left = left.strip()
        right = right.strip()
        # Left: state read   (read may be parenthesized tuple for multi-tape)
        if num_tapes > 1:
            # Expect: STATE (s1 s2 ...)
            # Find first '(' or first space
            if "(" in left:
                state_part, read_part = left.split("(", 1)
                state = state_part.strip()
                read_str = "(" + read_part.strip()
                # Ensure balanced
                if not read_str.endswith(")"):
                    raise ParseError(f"line {lineno}: unbalanced parenthesis in read: {line!r}")
                reads = tuple(self._parse_symbol_list(read_str))
            else:
                parts = left.split()
                if len(parts) < 2:
                    raise ParseError(f"line {lineno}: multi-tape transition needs (read...) tuple: {line!r}")
                state = parts[0]
                reads = tuple(self._parse_symbol(p) for p in parts[1:])
        else:
            parts = left.split()
            if len(parts) != 2:
                raise ParseError(f"line {lineno}: single-tape transition needs 'state read -> ...': {line!r}")
            state, read_str = parts
            reads = self._parse_symbol(read_str)
        # Right: write move new_state  (write/move may be tuples)
        if num_tapes > 1:
            # Expect: (w1 w2 ...) (m1 m2 ...) new_state
            rparts = self._split_symbols(right)
            # Reconstruct tuples
            i = 0
            writes = None
            moves = None
            # First token may start with '('
            tokens = self._tokenize(right)
            if len(tokens) < 3:
                raise ParseError(f"line {lineno}: multi-tape transition RHS too short: {line!r}")
            # writes
            if tokens[0].startswith("("):
                wt = tokens[0]
                writes = tuple(self._parse_symbol_list(wt))
            else:
                raise ParseError(f"line {lineno}: multi-tape transition needs (write...) tuple: {line!r}")
            # moves
            if tokens[1].startswith("("):
                mt = tokens[1]
                moves = self._parse_direction_list(mt)
            else:
                raise ParseError(f"line {lineno}: multi-tape transition needs (move...) tuple: {line!r}")
            new_state = " ".join(tokens[2:]).strip() or tokens[2]
        else:
            rparts = right.split()
            if len(rparts) < 3:
                raise ParseError(f"line {lineno}: transition RHS needs 'write move new_state': {line!r}")
            writes = self._parse_symbol(rparts[0])
            moves = self._parse_direction(rparts[1])
            new_state = " ".join(rparts[2:]).strip()
        # Transition signature: Transition(state, read, write, direction, new_state)
        return Transition(state, reads, writes, moves, new_state)

    @staticmethod
    def _tokenize(s: str) -> List[str]:
        """Tokenize a RHS string, keeping parenthesized groups as one token."""
        tokens = []
        cur = ""
        depth = 0
        in_quote = None
        for ch in s:
            if in_quote:
                cur += ch
                if ch == in_quote:
                    in_quote = None
            elif ch in ("'", '"'):
                in_quote = ch
                cur += ch
            elif ch == "(":
                depth += 1
                cur += ch
            elif ch == ")":
                depth -= 1
                cur += ch
                if depth == 0:
                    tokens.append(cur)
                    cur = ""
            elif ch.isspace() and depth == 0:
                if cur:
                    tokens.append(cur)
                    cur = ""
            else:
                cur += ch
        if cur:
            tokens.append(cur)
        return tokens


def parse(text: str) -> MachineDef:
    """Convenience: parse a machine definition string."""
    return Parser().parse(text)


def parse_file(path: str) -> MachineDef:
    """Parse a machine definition file."""
    with open(path, "r", encoding="utf-8") as f:
        return Parser().parse(f.read())