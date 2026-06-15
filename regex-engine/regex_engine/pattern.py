"""
Pattern — high-level regex pattern interface (re-like API).

Provides a compiled Pattern object similar to Python's re.Pattern,
with support for all matching operations and capture groups.
"""

from __future__ import annotations

import logging
from typing import Optional, List, Tuple

from .parser import Parser, ParseError
from .compiler import Compiler
from .nfa import State
from .matcher import Matcher, Match

logger = logging.getLogger(__name__)


class Pattern:
    """Compiled regex pattern object (similar to re.Pattern).

    A Pattern is created by parsing a regex string into an AST,
    compiling it into an NFA using Thompson's construction, and
    creating a Matcher for running simulations.

    Supports capture groups via GROUP_START/GROUP_END NFA states.

    Attributes:
        pattern: The original pattern string.
        flags: Match flags (reserved for future use).
        num_groups: Number of capture groups in the pattern.
    """

    def __init__(self, pattern: str, flags: int = 0):
        if not isinstance(pattern, str):
            raise TypeError(f"pattern must be str, got {type(pattern).__name__}")
        if not isinstance(flags, int):
            raise TypeError(f"flags must be int, got {type(flags).__name__}")
        self.pattern = pattern
        self.flags = flags
        self._start: Optional[State] = None
        self._matcher: Optional[Matcher] = None
        self.num_groups: int = 0
        self._compile()

    def _compile(self):
        """Parse and compile the pattern.

        Raises:
            ParseError: If the pattern has invalid syntax.
        """
        parser = Parser(self.pattern)
        ast = parser.parse()
        compiler = Compiler()
        self._start = compiler.compile(ast)
        self.num_groups = compiler.num_groups
        self._matcher = Matcher(self._start, self.pattern, self.num_groups)

    def match(self, text: str) -> Optional[Match]:
        """Match pattern at the beginning of string.

        Args:
            text: The text to match against.

        Returns:
            A Match object if the pattern matches, None otherwise.
        """
        return self._matcher.match(text)

    def fullmatch(self, text: str) -> Optional[Match]:
        """Match pattern against the entire string.

        Args:
            text: The text to match against.

        Returns:
            A Match object if the entire string matches, None otherwise.
        """
        return self._matcher.fullmatch(text)

    def search(self, text: str, start_pos: int = 0) -> Optional[Match]:
        """Search for the first match anywhere in the string.

        Args:
            text: The text to search in.
            start_pos: Starting position for the search.

        Returns:
            A Match object if found, None otherwise.
        """
        return self._matcher.search(text, start_pos)

    def findall(self, text: str) -> List[str]:
        """Find all non-overlapping matches.

        If the pattern contains capture groups, returns a list of
        group strings (or tuples of groups for multiple groups).

        Args:
            text: The text to search in.

        Returns:
            List of matched strings or tuples.
        """
        return self._matcher.findall(text)

    def finditer(self, text: str) -> List[Match]:
        """Find all matches as Match objects.

        Args:
            text: The text to search in.

        Returns:
            List of Match objects.
        """
        return self._matcher.finditer(text)

    def sub(self, repl: str, text: str, count: int = 0) -> str:
        """Replace occurrences of pattern in string.

        Supports backreferences like \\1, \\2, etc. in repl.

        Args:
            repl: Replacement string.
            text: The text to search in.
            count: Maximum number of replacements (0 = unlimited).

        Returns:
            The resulting string after replacements.
        """
        return self._matcher.sub(repl, text, count)

    def split(self, text: str, maxsplit: int = 0) -> List[str]:
        """Split string by pattern.

        Args:
            text: The text to split.
            maxsplit: Maximum number of splits (0 = unlimited).

        Returns:
            List of string segments.
        """
        return self._matcher.split(text, maxsplit)

    def subn(self, repl: str, text: str, count: int = 0) -> Tuple[str, int]:
        """Replace occurrences and return (new_string, number_of_subs).

        Args:
            repl: Replacement string.
            text: The text to search in.
            count: Maximum number of replacements (0 = unlimited).

        Returns:
            Tuple of (resulting_string, number_of_substitutions).
        """
        return self._matcher.subn(repl, text, count)

    @property
    def groups(self) -> int:
        """Return the number of capture groups in the pattern."""
        return self.num_groups

    def __repr__(self) -> str:
        return f"Pattern('{self.pattern}')"

    def __str__(self) -> str:
        return f"regex_engine.compile('{self.pattern}')"