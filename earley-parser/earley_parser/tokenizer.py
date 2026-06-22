"""Regex-based tokenizer for the earley-parser package.

Provides:
- ``TokenSpec``: a named regex pattern with optional skip flag.
- ``Token``: a typed token with name, value, and position.
- ``Tokenizer``: a configurable regex tokenizer.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Tuple, Optional

from .errors import TokenizerError


@dataclass
class TokenSpec:
    """A regex-based token specification.

    Attributes
    ----------
    name : str
        The token type name (e.g. ``"NUM"``, ``"PLUS"``).
    pattern : str
        A Python regex pattern string.
    skip : bool
        If ``True``, matched text is discarded (e.g. whitespace, comments).
    """

    name: str
    pattern: str
    skip: bool = False


@dataclass
class Token:
    """A token produced by :class:`Tokenizer`.

    Attributes
    ----------
    name : str
        The token type name.
    value : str
        The matched text.
    position : int
        The start position in the source text.
    """

    name: str
    value: str
    position: int

    def __repr__(self) -> str:
        return f"Token({self.name!r}, {self.value!r}, pos={self.position})"

    def __str__(self) -> str:
        return f"{self.name}({self.value!r})"


class Tokenizer:
    """A regex-based tokenizer.

    Given a list of :class:`TokenSpec`, produces token lists suitable for
    feeding into :class:`~earley_parser.parser.EarleyParser`.

    Token specs are tried in order; the first matching spec at each
    position wins. A zero-length match is skipped to prevent infinite
    loops.

    Examples
    --------
    >>> tok = Tokenizer([
    ...     TokenSpec("NUM", r"[0-9]+"),
    ...     TokenSpec("PLUS", r"\\+"),
    ...     TokenSpec("WS", r"\\s+", skip=True),
    ... ])
    >>> tok.tokenize("12 + 34")
    ['NUM', 'PLUS', 'NUM']
    """

    def __init__(self, specs: List[TokenSpec]) -> None:
        if not specs:
            raise ValueError("Tokenizer requires at least one TokenSpec.")
        self.specs = specs
        self._compiled: List[Tuple[TokenSpec, re.Pattern]] = [
            (spec, re.compile(spec.pattern)) for spec in specs
        ]
        self._ws_fallback = re.compile(r"\s+")

    def tokenize_with_text(self, text: str) -> List[Tuple[str, str]]:
        """Tokenize *text* and return ``(name, matched_text)`` pairs.

        Raises
        ------
        TokenizerError
            On unmatched input.
        """
        result: List[Tuple[str, str]] = []
        i = 0
        while i < len(text):
            matched = False
            for spec, regex in self._compiled:
                m = regex.match(text, i)
                if m:
                    # Guard against zero-length matches.
                    if m.end() == i:
                        continue
                    if not spec.skip:
                        result.append((spec.name, m.group()))
                    i = m.end()
                    matched = True
                    break
            if not matched:
                ws = self._ws_fallback.match(text, i)
                if ws:
                    i = ws.end()
                    continue
                raise TokenizerError(i, text)
        return result

    def tokenize(self, text: str) -> List[str]:
        """Tokenize *text* and return just the token type names."""
        return [name for name, _ in self.tokenize_with_text(text)]

    def tokenize_full(self, text: str) -> List[Token]:
        """Tokenize *text* and return :class:`Token` objects with positions.

        Skipped tokens (whitespace, etc.) are not included in the result.
        """
        result: List[Token] = []
        i = 0
        while i < len(text):
            matched = False
            for spec, regex in self._compiled:
                m = regex.match(text, i)
                if m:
                    if m.end() == i:
                        continue
                    if not spec.skip:
                        result.append(Token(spec.name, m.group(), i))
                    i = m.end()
                    matched = True
                    break
            if not matched:
                ws = self._ws_fallback.match(text, i)
                if ws:
                    i = ws.end()
                    continue
                raise TokenizerError(i, text)
        return result

    @staticmethod
    def from_spec_pairs(
        specs: List[Tuple[str, str]],
        skip_names: Optional[set] = None,
    ) -> "Tokenizer":
        """Convenience constructor from ``(name, pattern)`` pairs.

        Names in *skip_names* are treated as skip tokens.
        """
        skip = skip_names or set()
        return Tokenizer([
            TokenSpec(name, pat, skip=(name in skip))
            for name, pat in specs
        ])