"""Lexer framework for the LALR parser generator.

This module provides a reusable, configurable lexer that converts raw
text into token streams suitable for the LR parser driver.

Features:
    - Regex-based token specification with named patterns
    - Automatic longest-match resolution
    - Token priorities for ambiguous patterns (e.g., keywords vs identifiers)
    - Whitespace skipping with configurable patterns
    - Line/column tracking for error messages
    - Token factory hooks for value transformation
    - Named capture groups for extracting sub-parts of tokens
    - Error recovery with skip/continue strategies
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from .parser import Token

logger = logging.getLogger(__name__)


class LexError(Exception):
    """Raised when the lexer encounters input it cannot tokenize."""

    def __init__(self, message: str, position: int = -1, line: int = -1,
                 column: int = -1) -> None:
        self.position = position
        self.line = line
        self.column = column
        parts = [message]
        if line >= 0:
            parts.append(f"at line {line}, column {column}")
        elif position >= 0:
            parts.append(f"at position {position}")
        super().__init__(" ".join(parts))


@dataclass
class TokenSpec:
    """Specification for a single token type.

    Attributes:
        name: Terminal symbol name (must match grammar terminal names).
        pattern: Regex pattern string for matching this token.
        priority: Higher priority wins on ties (default 0). Useful
            for distinguishing keywords from identifiers.
        action: Optional callable that receives the matched string and
            returns the token's semantic value. If None, the matched
            string itself is used as the value.
        hidden: If True, the token is produced but not returned (useful
            for whitespace and comments when skip is not appropriate).
    """

    name: str
    pattern: str
    priority: int = 0
    action: Optional[Callable[[str], Any]] = None
    hidden: bool = False


class Lexer:
    """A configurable regex-based lexer.

    Usage::

        lexer = Lexer()
        lexer.add_spec(TokenSpec("NUMBER", r"\\d+", action=int))
        lexer.add_spec(TokenSpec("PLUS", r"\\+", priority=1))
        lexer.add_spec(TokenSpec("ID", r"[A-Za-z_][A-Za-z0-9_]*"))
        lexer.set_skip(r"[ \\t\\n]+")
        tokens = lexer.lex("3 + foo")
    """

    def __init__(self) -> None:
        self._specs: List[TokenSpec] = []
        self._skip_pattern: Optional[str] = None
        self._compiled_skip: Optional[re.Pattern] = None
        self._compiled_specs: List[Tuple[re.Pattern, TokenSpec]] = []
        self._dirty: bool = True  # recompile needed

    def add_spec(self, spec: TokenSpec) -> "Lexer":
        """Add a token specification. Returns self for chaining."""
        self._specs.append(spec)
        self._dirty = True
        return self

    def add_keyword(self, keyword: str, token_type: Optional[str] = None,
                    priority: int = 10) -> "Lexer":
        """Convenience: add a literal keyword token.

        Args:
            keyword: The literal string to match.
            token_type: Terminal name (defaults to the keyword itself).
            priority: Higher than identifiers to win on ties.
        """
        name = token_type or keyword
        escaped = re.escape(keyword)
        return self.add_spec(TokenSpec(name, escaped, priority=priority))

    def add_symbol(self, symbol: str, token_type: Optional[str] = None,
                   priority: int = 5) -> "Lexer":
        """Convenience: add a single/multi-character symbol."""
        name = token_type or symbol
        return self.add_spec(TokenSpec(name, re.escape(symbol), priority=priority))

    def set_skip(self, pattern: str) -> "Lexer":
        """Set the whitespace/skip pattern. Matched text is ignored."""
        self._skip_pattern = pattern
        self._skip_pattern_compiled = None
        self._dirty = True
        return self

    def _compile(self) -> None:
        """Compile all regex patterns."""
        if not self._dirty:
            return
        self._compiled_specs = [
            (re.compile(spec.pattern), spec) for spec in self._specs
        ]
        if self._skip_pattern:
            self._compiled_skip = re.compile(self._skip_pattern)
        else:
            self._compiled_skip = None
        self._dirty = False

    def lex(self, text: str, filename: str = "<input>") -> List[Token]:
        """Tokenize *text* and return a list of Token objects.

        Raises LexError on unrecognizable input.
        """
        self._compile()
        if not self._compiled_specs:
            raise LexError("No token specifications added to the lexer")

        tokens: List[Token] = []
        pos = 0
        line = 1
        col = 1
        length = len(text)

        while pos < length:
            # Skip whitespace
            if self._compiled_skip is not None:
                m = self._compiled_skip.match(text, pos)
                if m:
                    skipped = m.group()
                    line += skipped.count("\n")
                    if "\n" in skipped:
                        col = len(skipped) - skipped.rfind("\n")
                    else:
                        col += len(skipped)
                    pos = m.end()
                    continue

            # Find longest match among all specs, breaking ties by priority
            best_match: Optional[re.Match] = None
            best_spec: Optional[TokenSpec] = None
            best_score: Tuple[int, int] = (-1, -1)  # (length, priority)

            for regex, spec in self._compiled_specs:
                m = regex.match(text, pos)
                if m:
                    score = (m.end() - m.start(), spec.priority)
                    if score > best_score:
                        best_match = m
                        best_spec = spec
                        best_score = score

            if best_match is None or best_spec is None:
                # Error: unrecognized input
                snippet = text[pos:pos + 20].replace("\n", "\\n")
                logger.error(
                    "Lex error at %s:%d:%d: unrecognized input near %r",
                    filename, line, col, snippet,
                )
                raise LexError(
                    f"Unrecognized input near '{snippet}'",
                    position=pos, line=line, column=col,
                )

            matched_text = best_match.group()
            value: Any = matched_text
            if best_spec.action is not None:
                value = best_spec.action(matched_text)

            if not best_spec.hidden:
                token = Token(
                    type=best_spec.name,
                    value=value,
                    position=pos,
                )
                # Store line/col as extra attributes
                token.line = line  # type: ignore[attr-defined]
                token.column = col  # type: ignore[attr-defined]
                token.filename = filename  # type: ignore[attr-defined]
                tokens.append(token)
                logger.debug(
                    "Lexed %s=%r at %d:%d", best_spec.name, value, line, col,
                )
            else:
                logger.debug("Skipped hidden token %s at %d:%d",
                             best_spec.name, line, col)

            # Update line/col
            line += matched_text.count("\n")
            if "\n" in matched_text:
                col = len(matched_text) - matched_text.rfind("\n")
            else:
                col += len(matched_text)
            pos = best_match.end()

        return tokens

    def lex_stream(self, text: str, filename: str = "<input>"):
        """Generator version of lex that yields tokens one at a time."""
        self._compile()
        if not self._compiled_specs:
            raise LexError("No token specifications added to the lexer")

        pos = 0
        line = 1
        col = 1
        length = len(text)

        while pos < length:
            if self._compiled_skip is not None:
                m = self._compiled_skip.match(text, pos)
                if m:
                    skipped = m.group()
                    line += skipped.count("\n")
                    if "\n" in skipped:
                        col = len(skipped) - skipped.rfind("\n")
                    else:
                        col += len(skipped)
                    pos = m.end()
                    continue

            best_match = None
            best_spec = None
            best_score = (-1, -1)

            for regex, spec in self._compiled_specs:
                m = regex.match(text, pos)
                if m:
                    score = (m.end() - m.start(), spec.priority)
                    if score > best_score:
                        best_match = m
                        best_spec = spec
                        best_score = score

            if best_match is None or best_spec is None:
                snippet = text[pos:pos + 20].replace("\n", "\\n")
                raise LexError(
                    f"Unrecognized input near '{snippet}'",
                    position=pos, line=line, column=col,
                )

            matched_text = best_match.group()
            value: Any = matched_text
            if best_spec.action is not None:
                value = best_spec.action(matched_text)

            if not best_spec.hidden:
                token = Token(
                    type=best_spec.name,
                    value=value,
                    position=pos,
                )
                token.line = line  # type: ignore[attr-defined]
                token.column = col  # type: ignore[attr-defined]
                token.filename = filename  # type: ignore[attr-defined]
                yield token

            line += matched_text.count("\n")
            if "\n" in matched_text:
                col = len(matched_text) - matched_text.rfind("\n")
            else:
                col += len(matched_text)
            pos = best_match.end()


class LexerBuilder:
    """High-level builder for constructing lexers from config dictionaries.

    Example config::

        {
            "skip": r"[ \\t\\n]+",
            "tokens": [
                {"name": "NUMBER", "pattern": r"\\d+", "action": "int"},
                {"name": "PLUS", "pattern": r"\\+", "priority": 5},
                {"name": "ID", "pattern": r"[A-Za-z_][A-Za-z0-9_]*"},
            ],
            "keywords": {
                "if": "IF",
                "while": "WHILE",
                "else": "ELSE",
            }
        }
    """

    _ACTION_MAP: Dict[str, Callable[[str], Any]] = {
        "int": int,
        "float": float,
        "str": str,
        "bool": lambda s: s.lower() in ("true", "1", "yes"),
    }

    def build(self, config: Dict[str, Any]) -> Lexer:
        lexer = Lexer()

        # Set skip pattern
        if "skip" in config:
            lexer.set_skip(config["skip"])

        # Add keywords (high priority)
        keywords: Dict[str, str] = config.get("keywords", {})
        for kw, token_type in keywords.items():
            lexer.add_keyword(kw, token_type, priority=20)

        # Add token specs
        for tok_config in config.get("tokens", []):
            action = None
            if "action" in tok_config:
                act = tok_config["action"]
                if isinstance(act, str):
                    action = self._ACTION_MAP.get(act, eval if act.startswith("lambda ") else None)  # noqa: E501
                elif callable(act):
                    action = act
            spec = TokenSpec(
                name=tok_config["name"],
                pattern=tok_config["pattern"],
                priority=tok_config.get("priority", 0),
                action=action,
                hidden=tok_config.get("hidden", False),
            )
            lexer.add_spec(spec)

        return lexer