"""Simple SQL-like query parser for the B+ Tree database.

Supported queries:
    SELECT * FROM db
    SELECT * FROM db WHERE key = 'x'
    SELECT * FROM db WHERE key > 'a'
    SELECT * FROM db WHERE key < 'z'
    SELECT * FROM db WHERE key >= 'a' AND key <= 'z'
    INSERT INTO db KEY 'x' VALUE 'y'
    DELETE FROM db WHERE key = 'x'
    COUNT db
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class QueryAST:
    """Parsed representation of a query."""
    command: str
    conditions: List[dict] = field(default_factory=list)
    key: Optional[str] = None
    value: Optional[str] = None


class QueryParser:
    """Tokenize and parse simple SQL-like queries for the B+ Tree database."""

    TOKEN_PATTERNS = [
        ("KEYWORD", r"\b(SELECT|FROM|WHERE|INSERT|INTO|KEY|VALUE|DELETE|COUNT|AND|OR)\b"),
        ("OP", r"(>=|<=|!=|>|<|=)"),
        ("STRING", r"'([^']*)'"),
        ("NUMBER", r"-?\d+\.?\d*"),
        ("IDENT", r"[a-zA-Z_][a-zA-Z0-9_]*"),
        ("STAR", r"\*"),
        ("WS", r"\s+"),
    ]

    def __init__(self, query: str):
        self.query = query.strip()
        self.tokens: list[tuple[str, str]] = []
        self.pos = 0

    def _tokenize(self) -> None:
        """Tokenize the query string."""
        combined = "|".join(
            f"(?P<{name}>{pattern})" for name, pattern in self.TOKEN_PATTERNS
        )
        regex = re.compile(combined, re.IGNORECASE)
        self.tokens = []
        for match in regex.finditer(self.query):
            for name, _pattern in self.TOKEN_PATTERNS:
                group = match.group(name)
                if group is not None:
                    value = match.group()
                    if name != "WS":
                        # Keywords are case-insensitive; preserve original value
                        self.tokens.append((name, value))
                    break

    def _peek(self) -> Optional[tuple[str, str]]:
        """Look at the current token without consuming it."""
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def _advance(self) -> tuple[str, str]:
        """Consume and return the current token."""
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def _expect(self, token_type: str = None, value: str = None) -> tuple[str, str]:
        """Consume a token, optionally checking type and value."""
        tok = self._peek()
        if tok is None:
            raise SyntaxError(
                f"Unexpected end of query, expected {token_type} {value or ''}".strip()
            )
        if token_type and tok[0] != token_type:
            raise SyntaxError(
                f"Expected token type {token_type}, got {tok[0]} ({tok[1]!r})"
            )
        if value and tok[1].upper() != value.upper():
            raise SyntaxError(f"Expected {value!r}, got {tok[1]!r}")
        return self._advance()

    def _parse_value_literal(self) -> str:
        """Parse a string or number literal value."""
        tok = self._peek()
        if tok is None:
            raise SyntaxError("Expected a value")
        if tok[0] == "STRING":
            self._advance()
            # Strip quotes
            return tok[1][1:-1]
        elif tok[0] == "NUMBER":
            self._advance()
            return tok[1]
        elif tok[0] == "IDENT":
            self._advance()
            return tok[1]
        else:
            raise SyntaxError(f"Expected value, got {tok[0]} ({tok[1]!r})")

    def parse(self) -> QueryAST:
        """Parse the query string and return a QueryAST."""
        self._tokenize()
        if not self.tokens:
            raise SyntaxError("Empty query")

        first = self._peek()
        if first is None:
            raise SyntaxError("Empty query")

        cmd = first[1].upper()

        if cmd == "SELECT":
            return self._parse_select()
        elif cmd == "INSERT":
            return self._parse_insert()
        elif cmd == "DELETE":
            return self._parse_delete()
        elif cmd == "COUNT":
            return self._parse_count()
        else:
            raise SyntaxError(f"Unknown command: {cmd}")

    def _parse_select(self) -> QueryAST:
        """Parse a SELECT query."""
        self._expect(value="SELECT")
        self._expect("STAR", value="*")
        self._expect(value="FROM")
        self._expect("IDENT")  # table name (always 'db')

        conditions = []
        if self._peek() and self._peek()[1].upper() == "WHERE":
            self._advance()  # WHERE
            conditions = self._parse_conditions()

        return QueryAST(command="select", conditions=conditions)

    def _parse_insert(self) -> QueryAST:
        """Parse an INSERT query."""
        self._expect(value="INSERT")
        self._expect(value="INTO")
        self._expect("IDENT")  # 'db'
        self._expect(value="KEY")
        key = self._parse_value_literal()
        self._expect(value="VALUE")
        value = self._parse_value_literal()
        return QueryAST(command="insert", key=key, value=value)

    def _parse_delete(self) -> QueryAST:
        """Parse a DELETE query."""
        self._expect(value="DELETE")
        self._expect(value="FROM")
        self._expect("IDENT")  # 'db'
        self._expect(value="WHERE")
        self._expect(value="KEY")
        self._expect("OP", value="=")
        key = self._parse_value_literal()
        return QueryAST(command="delete", key=key)

    def _parse_count(self) -> QueryAST:
        """Parse a COUNT query."""
        self._expect(value="COUNT")
        self._expect("IDENT")  # 'db'
        return QueryAST(command="count")

    def _parse_conditions(self) -> list[dict]:
        """Parse WHERE conditions (key op value [AND key op value ...])."""
        conditions = []
        while True:
            self._expect(value="KEY")
            op_tok = self._expect("OP")
            value = self._parse_value_literal()
            conditions.append({"op": op_tok[1], "value": value})
            # Check for AND
            if self._peek() and self._peek()[1].upper() == "AND":
                self._advance()
            else:
                break
        return conditions