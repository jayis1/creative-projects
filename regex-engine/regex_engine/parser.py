"""
Regex parser — converts a regex pattern string into an Abstract Syntax Tree (AST).

Supports:
  - Literals, wildcards (.), escaped characters
  - Alternation (|), concatenation, grouping (())
  - Quantifiers: *, +, ?, {n}, {n,m}, {n,}
  - Character classes: [abc], [a-z], [^0-9]
  - Shorthand classes: \\d, \\w, \\s, \\D, \\W, \\S
  - Anchors: ^, $
  - Non-greedy quantifiers: *?, +?, ??
  - Hex escapes: \\xNN
  - Capture groups: (...) with group indexing
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional, List, Union

logger = logging.getLogger(__name__)


class ParseError(Exception):
    """Error encountered while parsing a regex pattern.

    Attributes:
        position: The position in the pattern where the error occurred.
    """
    def __init__(self, message: str, position: int = -1):
        self.position = position
        super().__init__(f"Parse error at position {position}: {message}" if position >= 0 else message)


# AST Node types

@dataclass
class Literal:
    """Match a specific character."""
    char: str
    position: int = -1

@dataclass
class Dot:
    """Match any character (except newline by default)."""
    position: int = -1

@dataclass
class AnchorStart:
    """^ anchor — match at start of string or after newline."""
    position: int = -1

@dataclass
class AnchorEnd:
    """$ anchor — match at end of string or before newline."""
    position: int = -1

@dataclass
class CharClass:
    """Character class like [a-z] or [^0-9]."""
    ranges: list = field(default_factory=list)
    chars: list = field(default_factory=list)
    shorthands: list = field(default_factory=list)  # list of (kind, positive) tuples
    negated: bool = False
    position: int = -1

@dataclass
class Shorthand:
    """Shorthand class: \\d, \\w, \\s, \\D, \\W, \\S."""
    kind: str
    position: int = -1

@dataclass
class Concat:
    """Concatenation of nodes."""
    children: list = field(default_factory=list)

@dataclass
class Alternation:
    """Alternation (|) of nodes."""
    children: list = field(default_factory=list)

@dataclass
class Quantified:
    """A node with a quantifier applied."""
    child: 'ASTNode'
    min: int = 0
    max: Optional[int] = None  # None means unbounded
    greedy: bool = True
    position: int = -1

@dataclass
class Group:
    """A captured group (...)."""
    child: 'ASTNode'
    index: int = -1
    position: int = -1


ASTNode = Union[Literal, Dot, AnchorStart, AnchorEnd, CharClass,
                Shorthand, Concat, Alternation, Quantified, Group]


class Parser:
    """Recursive descent parser for regular expressions.

    The parser converts a regex pattern string into an AST (Abstract Syntax Tree)
    that can be compiled into an NFA by the Compiler.

    The grammar (simplified):
        alternation := concat ('|' concat)*
        concat := quantified+
        quantified := atom ('*' | '+' | '?' | '{n,m}') '?'?
        atom := '(' alternation ')' | '[' charclass ']' | '.' | '^' | '$' | escape | literal

    Args:
        pattern: The regex pattern string to parse.

    Raises:
        ParseError: If the pattern has invalid syntax.
    """

    def __init__(self, pattern: str):
        if not isinstance(pattern, str):
            raise TypeError(f"pattern must be str, got {type(pattern).__name__}")
        self.pattern = pattern
        self.pos = 0
        self.group_count = 0

    def parse(self) -> ASTNode:
        """Parse the entire pattern and return an AST.

        Returns:
            The root AST node.

        Raises:
            ParseError: If the pattern has invalid syntax.
        """
        node = self._parse_alternation()
        if self.pos < len(self.pattern):
            raise ParseError(f"Unexpected character '{self.pattern[self.pos]}'", self.pos)
        return node

    def _peek(self) -> Optional[str]:
        """Look at the current character without advancing."""
        if self.pos < len(self.pattern):
            return self.pattern[self.pos]
        return None

    def _advance(self) -> Optional[str]:
        """Consume and return the current character."""
        if self.pos < len(self.pattern):
            ch = self.pattern[self.pos]
            self.pos += 1
            return ch
        return None

    def _parse_alternation(self) -> ASTNode:
        """Parse: concat ('|' concat)*"""
        children = [self._parse_concat()]
        while self._peek() == '|':
            self._advance()
            children.append(self._parse_concat())
        if len(children) == 1:
            return children[0]
        return Alternation(children=children)

    def _parse_concat(self) -> ASTNode:
        """Parse: quantified+"""
        children = []
        while self._peek() is not None and self._peek() not in (')', '|'):
            children.append(self._parse_quantified())
        if len(children) == 0:
            return Concat(children=[])
        if len(children) == 1:
            return children[0]
        return Concat(children=children)

    def _parse_quantified(self) -> ASTNode:
        """Parse an atom with an optional quantifier."""
        atom = self._parse_atom()
        return self._parse_quantifier(atom)

    def _parse_quantifier(self, atom: ASTNode) -> ASTNode:
        """Parse quantifier: (*, +, ?, {n}, {n,}, {n,m}) with optional '?'."""
        if isinstance(atom, (AnchorStart, AnchorEnd)):
            return atom

        ch = self._peek()
        if ch in ('*', '+', '?'):
            pos = self.pos
            self._advance()
            greedy = True
            if self._peek() == '?':
                self._advance()
                greedy = False

            if ch == '*':
                return Quantified(child=atom, min=0, max=None, greedy=greedy, position=pos)
            elif ch == '+':
                return Quantified(child=atom, min=1, max=None, greedy=greedy, position=pos)
            else:
                return Quantified(child=atom, min=0, max=1, greedy=greedy, position=pos)

        if ch == '{':
            return self._parse_brace_quantifier(atom)

        return atom

    def _parse_brace_quantifier(self, atom: ASTNode) -> ASTNode:
        """Parse brace quantifier: {n}, {n,}, {n,m}."""
        pos = self.pos
        self._advance()  # consume '{'

        min_str = self._parse_int()
        if min_str is None:
            raise ParseError("Expected integer after '{'", self.pos)
        min_val = int(min_str)

        if self._peek() == '}':
            self._advance()
            greedy = self._parse_greedy()
            return Quantified(child=atom, min=min_val, max=min_val, greedy=greedy, position=pos)

        if self._peek() == ',':
            self._advance()
            if self._peek() == '}':
                self._advance()
                greedy = self._parse_greedy()
                return Quantified(child=atom, min=min_val, max=None, greedy=greedy, position=pos)

            max_str = self._parse_int()
            if max_str is None:
                raise ParseError("Expected integer after ',' in quantifier", self.pos)
            max_val = int(max_str)
            if max_val < min_val:
                raise ParseError(f"Max must be >= min", self.pos)
            if self._peek() != '}':
                raise ParseError("Expected '}'", self.pos)
            self._advance()
            greedy = self._parse_greedy()
            return Quantified(child=atom, min=min_val, max=max_val, greedy=greedy, position=pos)

        raise ParseError("Invalid quantifier syntax", self.pos)

    def _parse_int(self) -> Optional[str]:
        """Parse a sequence of digits."""
        start = self.pos
        while self.pos < len(self.pattern) and self.pattern[self.pos].isdigit():
            self.pos += 1
        if self.pos == start:
            return None
        return self.pattern[start:self.pos]

    def _parse_greedy(self) -> bool:
        """Parse optional '?' non-greedy modifier."""
        if self._peek() == '?':
            self._advance()
            return False
        return True

    def _parse_atom(self) -> ASTNode:
        """Parse a single atom: group, charclass, anchor, dot, escape, or literal."""
        ch = self._peek()
        if ch is None:
            raise ParseError("Unexpected end of pattern", self.pos)

        if ch == '(':
            return self._parse_group()
        if ch == '[':
            return self._parse_char_class()
        if ch == '^':
            pos = self.pos
            self._advance()
            return AnchorStart(position=pos)
        if ch == '$':
            pos = self.pos
            self._advance()
            return AnchorEnd(position=pos)
        if ch == '.':
            pos = self.pos
            self._advance()
            return Dot(position=pos)
        if ch == '\\':
            return self._parse_escape()
        if ch in ('*', '+', '?', '{', '|', ')'):
            raise ParseError(f"Unexpected '{ch}'", self.pos)

        pos = self.pos
        self._advance()
        return Literal(char=ch, position=pos)

    def _parse_escape(self) -> ASTNode:
        """Parse an escape sequence: \\d, \\w, \\s, \\n, \\t, \\xNN, etc."""
        pos = self.pos
        self._advance()  # consume '\\'

        if self.pos >= len(self.pattern):
            raise ParseError("Unexpected end of pattern after '\\'", pos)

        ch = self.pattern[self.pos]
        self.pos += 1

        if ch in ('d', 'D', 'w', 'W', 's', 'S'):
            return Shorthand(kind=ch, position=pos)

        escape_map = {'n': '\n', 't': '\t', 'r': '\r', 'f': '\f', 'v': '\v', '0': '\0'}
        if ch in escape_map:
            return Literal(char=escape_map[ch], position=pos)

        # Hex escape \\xNN
        if ch == 'x':
            hex_str = self.pattern[self.pos:self.pos + 2]
            if len(hex_str) == 2:
                try:
                    self.pos += 2
                    return Literal(char=chr(int(hex_str, 16)), position=pos)
                except ValueError:
                    raise ParseError(f"Invalid hex escape", pos)

        # Escaped metachar or literal
        return Literal(char=ch, position=pos)

    def _parse_group(self) -> ASTNode:
        """Parse a capture group: (alternation)."""
        pos = self.pos
        self._advance()  # consume '('
        group_index = self.group_count
        self.group_count += 1

        child = self._parse_alternation()

        if self.pos >= len(self.pattern) or self.pattern[self.pos] != ')':
            raise ParseError("Unterminated group — expected ')'", self.pos)
        self._advance()

        return Group(child=child, index=group_index, position=pos)

    def _parse_char_class(self) -> ASTNode:
        """Parse a character class: [abc], [a-z], [^0-9], etc."""
        pos = self.pos
        self._advance()  # consume '['

        negated = False
        if self._peek() == '^':
            negated = True
            self._advance()

        ranges = []
        chars = []
        shorthands = []
        first = True

        while self.pos < len(self.pattern):
            ch = self.pattern[self.pos]

            if ch == ']' and not first:
                break

            first = False

            if ch == '\\':
                self._advance()
                if self.pos >= len(self.pattern):
                    raise ParseError("Unexpected end in character class", self.pos)
                escaped = self.pattern[self.pos]
                self._advance()

                shorthand_map = {
                    'd': ('digit', True), 'D': ('digit', False),
                    'w': ('word', True), 'W': ('word', False),
                    's': ('space', True), 'S': ('space', False),
                }
                if escaped in shorthand_map:
                    shorthands.append(shorthand_map[escaped])
                    continue

                escape_map = {'n': '\n', 't': '\t', 'r': '\r'}
                ch_val = escape_map.get(escaped, escaped)
            else:
                ch_val = ch
                self._advance()

            # Check for range
            if (self.pos + 1 < len(self.pattern) and
                self.pattern[self.pos] == '-' and
                self.pattern[self.pos + 1] != ']'):
                self._advance()  # consume '-'
                end_val = self._parse_char_class_atom()
                ranges.append((ch_val, end_val))
            else:
                chars.append(ch_val)

        if self.pos >= len(self.pattern):
            raise ParseError("Unterminated character class", pos)
        self._advance()  # consume ']'

        return CharClass(ranges=ranges, chars=chars, shorthands=shorthands,
                        negated=negated, position=pos)

    def _parse_char_class_atom(self) -> str:
        """Parse a single character inside a character class (for range endpoints)."""
        if self.pattern[self.pos] == '\\':
            self._advance()
            if self.pos >= len(self.pattern):
                raise ParseError("Unexpected end in character class", self.pos)
            escaped = self.pattern[self.pos]
            self._advance()
            escape_map = {'n': '\n', 't': '\t', 'r': '\r'}
            return escape_map.get(escaped, escaped)
        else:
            ch = self.pattern[self.pos]
            self._advance()
            return ch