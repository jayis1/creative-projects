"""Lexer / tokenizer for the mini-Prolog engine."""

from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import List


class TokenType(enum.Enum):
    ATOM = "ATOM"
    VARIABLE = "VARIABLE"
    NUMBER = "NUMBER"
    STRING = "STRING"
    LPAREN = "LPAREN"        # (
    RPAREN = "RPAREN"        # )
    LBRACKET = "LBRACKET"    # [
    RBRACKET = "RBRACKET"    # ]
    COMMA = "COMMA"          # ,
    DOT = "DOT"              # .
    SEMICOLON = "SEMICOLON"  # ;
    PIPE = "PIPE"            # |
    NECK = "NECK"            # :-
    QUERY = "QUERY"          # ?-
    EOF = "EOF"


@dataclass(frozen=True)
class Token:
    type: TokenType
    value: str
    line: int
    col: int

    def __repr__(self) -> str:
        return f"Token({self.type.name}, {self.value!r}, {self.line}:{self.col})"


class LexerError(Exception):
    """Raised when the lexer encounters an invalid character."""

    def __init__(self, message: str, line: int, col: int):
        super().__init__(f"{message} at line {line}, column {col}")
        self.line = line
        self.col = col


class Lexer:
    """Tokenize a Prolog source string into a stream of Tokens."""

    def __init__(self, source: str):
        self._source = source
        self._pos = 0
        self._line = 1
        self._col = 1
        self._tokens: List[Token] = []
        self._tokenize()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def tokens(self) -> List[Token]:
        return list(self._tokens)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _peek(self) -> str | None:
        if self._pos < len(self._source):
            return self._source[self._pos]
        return None

    def _advance(self) -> str:
        ch = self._source[self._pos]
        self._pos += 1
        if ch == "\n":
            self._line += 1
            self._col = 1
        else:
            self._col += 1
        return ch

    def _current_pos(self) -> tuple[int, int]:
        return self._line, self._col

    def _skip_whitespace_and_comments(self) -> None:
        while self._pos < len(self._source):
            ch = self._source[self._pos]
            if ch in " \t\r\n":
                self._advance()
            elif ch == "%":
                # Line comment
                while self._pos < len(self._source) and self._source[self._pos] != "\n":
                    self._pos += 1
            elif ch == "/" and self._pos + 1 < len(self._source) and self._source[self._pos + 1] == "*":
                # Block comment /* ... */
                self._advance()  # /
                self._advance()  # *
                while self._pos + 1 < len(self._source):
                    if self._source[self._pos] == "*" and self._source[self._pos + 1] == "/":
                        self._advance()  # *
                        self._advance()  # /
                        break
                    self._advance()
                else:
                    if self._pos < len(self._source):
                        self._advance()  # consume trailing *
            else:
                break

    def _tokenize(self) -> None:
        while True:
            self._skip_whitespace_and_comments()
            if self._pos >= len(self._source):
                self._tokens.append(Token(TokenType.EOF, "", self._line, self._col))
                break

            line, col = self._current_pos()
            ch = self._source[self._pos]

            # Strings
            if ch == '"':
                self._read_string(line, col)
                continue

            # Special multi-char tokens
            if ch == ":" and self._pos + 1 < len(self._source) and self._source[self._pos + 1] == "-":
                self._advance()
                self._advance()
                self._tokens.append(Token(TokenType.NECK, ":-", line, col))
                continue
            if ch == "?" and self._pos + 1 < len(self._source) and self._source[self._pos + 1] == "-":
                self._advance()
                self._advance()
                self._tokens.append(Token(TokenType.QUERY, "?-", line, col))
                continue

            # Single-char tokens
            if ch == "(":
                self._advance()
                self._tokens.append(Token(TokenType.LPAREN, "(", line, col))
                continue
            if ch == ")":
                self._advance()
                self._tokens.append(Token(TokenType.RPAREN, ")", line, col))
                continue
            if ch == "[":
                self._advance()
                self._tokens.append(Token(TokenType.LBRACKET, "[", line, col))
                continue
            if ch == "]":
                self._advance()
                self._tokens.append(Token(TokenType.RBRACKET, "]", line, col))
                continue
            if ch == ",":
                self._advance()
                self._tokens.append(Token(TokenType.COMMA, ",", line, col))
                continue
            if ch == ".":
                # Could be clause-terminating dot or start of a float
                # Prolog uses '.' as clause terminator when followed by whitespace or EOF
                # and as part of a float like 3.14
                # Check if it's part of a number (preceded by digits)
                if self._tokens and self._tokens[-1].type == TokenType.NUMBER:
                    # Check if next char is a digit (float continuation)
                    if self._pos + 1 < len(self._source) and self._source[self._pos + 1].isdigit():
                        self._read_number(line, col, self._tokens.pop().value)
                        continue
                self._advance()
                self._tokens.append(Token(TokenType.DOT, ".", line, col))
                continue
            if ch == ";":
                self._advance()
                self._tokens.append(Token(TokenType.SEMICOLON, ";", line, col))
                continue
            if ch == "|":
                self._advance()
                self._tokens.append(Token(TokenType.PIPE, "|", line, col))
                continue

            # Numbers
            if ch.isdigit():
                self._read_number(line, col)
                continue

            # Identifiers (atoms / variables)
            if ch.isalpha() or ch == "_":
                self._read_identifier(line, col)
                continue

            # Quoted atoms
            if ch == "'":
                self._read_quoted_atom(line, col)
                continue

            # Operator atoms
            if ch in "+-*/\\^<>=~!@#&?":
                self._read_operator_atom(line, col)
                continue

            raise LexerError(f"Unexpected character {ch!r}", line, col)

    def _read_string(self, start_line: int, start_col: int) -> None:
        self._advance()  # opening "
        chars: list[str] = []
        while self._pos < len(self._source):
            ch = self._source[self._pos]
            if ch == "\\":
                self._advance()
                esc = self._advance()
                escape_map = {"n": "\n", "t": "\t", "r": "\r", "\\": "\\", '"': '"'}
                chars.append(escape_map.get(esc, esc))
            elif ch == '"':
                self._advance()
                self._tokens.append(Token(TokenType.STRING, "".join(chars), start_line, start_col))
                return
            else:
                chars.append(self._advance())
        raise LexerError("Unterminated string", start_line, start_col)

    def _read_number(self, start_line: int, start_col: int, prefix: str = "") -> None:
        digits = list(prefix)
        while self._pos < len(self._source) and self._source[self._pos].isdigit():
            digits.append(self._advance())
        # Check for decimal point
        if self._pos < len(self._source) and self._source[self._pos] == ".":
            next_pos = self._pos + 1
            # Only treat as float if digit follows the dot
            if next_pos < len(self._source) and self._source[next_pos].isdigit():
                digits.append(self._advance())  # .
                while self._pos < len(self._source) and self._source[self._pos].isdigit():
                    digits.append(self._advance())
                # Check for exponent
                if self._pos < len(self._source) and self._source[self._pos] in "eE":
                    digits.append(self._advance())
                    if self._pos < len(self._source) and self._source[self._pos] in "+-":
                        digits.append(self._advance())
                    while self._pos < len(self._source) and self._source[self._pos].isdigit():
                        digits.append(self._advance())
        # Check for exponent without decimal (e.g. 1e5)
        elif self._pos < len(self._source) and self._source[self._pos] in "eE":
            digits.append(self._advance())
            if self._pos < len(self._source) and self._source[self._pos] in "+-":
                digits.append(self._advance())
            while self._pos < len(self._source) and self._source[self._pos].isdigit():
                digits.append(self._advance())
        self._tokens.append(Token(TokenType.NUMBER, "".join(digits), start_line, start_col))

    def _read_identifier(self, start_line: int, start_col: int) -> None:
        chars: list[str] = []
        while self._pos < len(self._source) and (self._source[self._pos].isalnum() or self._source[self._pos] == "_"):
            chars.append(self._advance())
        name = "".join(chars)
        if name and name[0].isupper() or name[0] == "_":
            self._tokens.append(Token(TokenType.VARIABLE, name, start_line, start_col))
        else:
            self._tokens.append(Token(TokenType.ATOM, name, start_line, start_col))

    def _read_quoted_atom(self, start_line: int, start_col: int) -> None:
        self._advance()  # opening '
        chars: list[str] = []
        while self._pos < len(self._source):
            ch = self._source[self._pos]
            if ch == "\\":
                self._advance()
                esc = self._advance()
                escape_map = {"n": "\n", "t": "\t", "r": "\r", "\\": "\\", "'": "'"}
                chars.append(escape_map.get(esc, esc))
            elif ch == "'":
                self._advance()
                self._tokens.append(Token(TokenType.ATOM, "".join(chars), start_line, start_col))
                return
            else:
                chars.append(self._advance())
        raise LexerError("Unterminated quoted atom", start_line, start_col)

    def _read_operator_atom(self, start_line: int, start_col: int) -> None:
        chars: list[str] = []
        while self._pos < len(self._source) and self._source[self._pos] in "+-*/\\^<>=~!@#&?":
            chars.append(self._advance())
        self._tokens.append(Token(TokenType.ATOM, "".join(chars), start_line, start_col))