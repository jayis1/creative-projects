"""Exception hierarchy for the earley-parser package."""
from __future__ import annotations

from typing import Set, Optional


class EarleyError(Exception):
    """Base exception for all earley-parser errors."""


class ParseError(EarleyError):
    """Raised when input cannot be parsed.

    Carries position, expected token set, and the unexpected token
    (or ``None`` for EOF) for structured error reporting.
    """

    def __init__(
        self,
        position: int,
        expected: Set[str],
        token: Optional[str] = None,
    ) -> None:
        self.position = position
        self.expected = expected
        self.token = token
        exp_str = ", ".join(sorted(expected)) if expected else "(nothing)"
        tok_str = repr(token) if token is not None else "EOF"
        super().__init__(
            f"Parse error at position {position}: unexpected {tok_str}; "
            f"expected one of: {exp_str}"
        )

    def to_dict(self) -> dict:
        """Serialize the error to a dictionary for programmatic use."""
        return {
            "position": self.position,
            "expected": sorted(self.expected),
            "token": self.token,
            "message": str(self),
        }


class GrammarError(EarleyError):
    """Raised when a grammar definition is invalid."""


class TokenizerError(EarleyError):
    """Raised when the tokenizer encounters input it cannot match."""

    def __init__(self, position: int, text: str, length: int = 20) -> None:
        self.position = position
        snippet = text[position : position + length]
        super().__init__(
            f"Tokenizer error at position {position}: "
            f"unexpected {snippet!r}"
        )