"""
Pattern — high-level regex pattern interface (re-like API).
"""

from __future__ import annotations
from typing import Optional, List
from .parser import Parser, ParseError
from .compiler import Compiler
from .nfa import State
from .matcher import Matcher, Match


class Pattern:
    """Compiled regex pattern object (similar to re.Pattern)."""

    def __init__(self, pattern: str, flags: int = 0):
        self.pattern = pattern
        self.flags = flags
        self._start: Optional[State] = None
        self._matcher: Optional[Matcher] = None
        self._compile()

    def _compile(self):
        """Parse and compile the pattern."""
        parser = Parser(self.pattern)
        ast = parser.parse()
        compiler = Compiler()
        self._start = compiler.compile(ast)
        self._matcher = Matcher(self._start, self.pattern)

    def match(self, text: str) -> Optional[Match]:
        """Match pattern at the beginning of string."""
        return self._matcher.match(text)

    def fullmatch(self, text: str) -> Optional[Match]:
        """Match pattern against the entire string."""
        return self._matcher.fullmatch(text)

    def search(self, text: str, start_pos: int = 0) -> Optional[Match]:
        """Search for the first match anywhere in the string."""
        return self._matcher.search(text, start_pos)

    def findall(self, text: str) -> List[str]:
        """Find all non-overlapping matches."""
        return self._matcher.findall(text)

    def finditer(self, text: str) -> List[Match]:
        """Find all matches as Match objects."""
        return self._matcher.finditer(text)

    def sub(self, repl: str, text: str, count: int = 0) -> str:
        """Replace occurrences of pattern in string."""
        return self._matcher.sub(repl, text, count)

    def split(self, text: str, maxsplit: int = 0) -> List[str]:
        """Split string by pattern."""
        return self._matcher.split(text, maxsplit)

    def __repr__(self):
        return f"Pattern('{self.pattern}')"