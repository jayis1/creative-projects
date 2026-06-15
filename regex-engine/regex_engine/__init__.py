"""
regex_engine — A regular expression engine built from scratch using Thompson's NFA construction.

A high-performance regex engine that guarantees O(nm) matching time,
avoiding the exponential backtracking that plagues many regex implementations.

Supports:
  - Literals, wildcards (.), escaped characters
  - Alternation (|), concatenation, grouping (())
  - Quantifiers: *, +, ?, {n}, {n,m}, {n,}
  - Character classes: [abc], [a-z], [^0-9]
  - Shorthand classes: \\d, \\w, \\s, \\D, \\W, \\S
  - Anchors: ^, $
  - Non-greedy quantifiers: *?, +?, ??
  - Capture groups: (...) with group extraction
  - Match, fullmatch, search, findall, finditer, sub, subn, split operations

Example usage::

    from regex_engine import compile, search

    # Compile a pattern
    p = compile(r'\\d+')
    m = p.match('123abc')
    print(m.group(0))  # '123'

    # Module-level convenience functions
    m = search(r'\\d+', 'abc123def')
    print(m.group(0))  # '123'

    # Capture groups
    p = compile(r'(\\w+)@(\\w+)')
    m = p.search('user@example.com')
    print(m.groups())  # ('user', 'example')
"""

from .pattern import Pattern
from .parser import ParseError

__version__ = "2.0.0"
__author__ = "Creative Projects Pipeline"
__all__ = [
    "Pattern", "ParseError",
    "compile", "match", "search", "findall", "sub", "split",
]


def compile(pattern: str, flags: int = 0) -> Pattern:
    """Compile a regex pattern into a reusable Pattern object.

    Args:
        pattern: The regex pattern string.
        flags: Match flags (reserved for future use).

    Returns:
        A compiled Pattern object.

    Raises:
        ParseError: If the pattern has invalid syntax.
        TypeError: If pattern is not a string.
    """
    return Pattern(pattern, flags)


def match(pattern: str, string: str, flags: int = 0):
    """Match pattern at the beginning of string.

    Args:
        pattern: The regex pattern string.
        string: The text to match against.
        flags: Match flags (reserved for future use).

    Returns:
        A Match object if the pattern matches, None otherwise.
    """
    return compile(pattern, flags).match(string)


def search(pattern: str, string: str, flags: int = 0):
    """Search for first occurrence of pattern in string.

    Args:
        pattern: The regex pattern string.
        string: The text to search in.
        flags: Match flags (reserved for future use).

    Returns:
        A Match object if found, None otherwise.
    """
    return compile(pattern, flags).search(string)


def findall(pattern: str, string: str, flags: int = 0):
    """Find all non-overlapping matches of pattern in string.

    Args:
        pattern: The regex pattern string.
        string: The text to search in.
        flags: Match flags (reserved for future use).

    Returns:
        List of matched strings (or tuples for capture groups).
    """
    return compile(pattern, flags).findall(string)


def sub(pattern: str, repl: str, string: str, count: int = 0, flags: int = 0):
    """Replace occurrences of pattern in string.

    Args:
        pattern: The regex pattern string.
        repl: Replacement string.
        string: The text to search in.
        count: Maximum number of replacements (0 = unlimited).
        flags: Match flags (reserved for future use).

    Returns:
        The resulting string after replacements.
    """
    return compile(pattern, flags).sub(repl, string, count)


def split(pattern: str, string: str, maxsplit: int = 0, flags: int = 0):
    """Split string by occurrences of pattern.

    Args:
        pattern: The regex pattern string.
        string: The text to split.
        maxsplit: Maximum number of splits (0 = unlimited).
        flags: Match flags (reserved for future use).

    Returns:
        List of string segments.
    """
    return compile(pattern, flags).split(string, maxsplit)