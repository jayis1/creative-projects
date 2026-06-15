"""
regex_engine — A regular expression engine built from scratch using Thompson's NFA construction.

Supports:
  - Literals, wildcards (.), escaped characters
  - Alternation (|), concatenation, grouping (())
  - Quantifiers: *, +, ?, {n}, {n,m}
  - Character classes: [abc], [a-z], [^0-9]
  - Shorthand classes: \\d, \\w, \\s, \\D, \\W, \\S
  - Anchors: ^, $
  - Non-greedy quantifiers: *?, +?, ??
  - Match, search, findall, sub, split operations
"""

from .pattern import Pattern
from .parser import ParseError

__version__ = "1.0.0"
__all__ = ["Pattern", "compile", "match", "search", "findall", "sub", "split", "ParseError"]


def compile(pattern: str, flags: int = 0) -> Pattern:
    """Compile a regex pattern into a reusable Pattern object."""
    return Pattern(pattern, flags)


def match(pattern: str, string: str, flags: int = 0):
    """Match pattern at the beginning of string."""
    return compile(pattern, flags).match(string)


def search(pattern: str, string: str, flags: int = 0):
    """Search for first occurrence of pattern in string."""
    return compile(pattern, flags).search(string)


def findall(pattern: str, string: str, flags: int = 0):
    """Find all non-overlapping matches of pattern in string."""
    return compile(pattern, flags).findall(string)


def sub(pattern: str, repl: str, string: str, count: int = 0, flags: int = 0):
    """Replace occurrences of pattern in string."""
    return compile(pattern, flags).sub(repl, string, count)


def split(pattern: str, string: str, maxsplit: int = 0, flags: int = 0):
    """Split string by occurrences of pattern."""
    return compile(pattern, flags).split(string, maxsplit)