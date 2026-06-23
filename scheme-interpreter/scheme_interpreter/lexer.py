r"""Lexer for Scheme source code.

Tokenizes Scheme source into a stream of Token objects.  Supports:
- Integers, floats, and exact rational literals (e.g. ``3/4``)
- Strings with escape sequences
- Symbols (including extended symbol characters)
- Booleans ``#t`` / ``#f``
- Character literals ``#\\a``, ``#\\space``, ``#\\newline``
- Semicolon line comments and block comments ``#| ... |#`` + datum comments ``#;``
- ``'`` (quote), ```` `` ```` (quasiquote), ``,`` (unquote), ``,@`` (unquote-splicing)
- Vectors ``#(``
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional


class LexError(Exception):
    """Raised when the lexer encounters malformed input."""

    def __init__(self, message: str, line: int = 0, col: int = 0):
        super().__init__(f"LexError at line {line}, col {col}: {message}")
        self.line = line
        self.col = col


@dataclass
class Token:
    """A single token produced by the lexer."""

    type: str
    value: object
    line: int
    col: int

    def __repr__(self) -> str:
        return f"Token({self.type!r}, {self.value!r}, line={self.line}, col={self.col})"


# Characters that may appear unescaped inside a symbol.
_SYMBOL_CHARS = set("!$%&*+-./:<=>?@^_~")
_SYMBOL_START = set("!$%&*+-./:<=>?@^_~") | set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")

# Escape sequences inside string literals.
_STRING_ESCAPES = {
    "n": "\n",
    "t": "\t",
    "r": "\r",
    "\\": "\\",
    '"': '"',
    "0": "\0",
    "a": "\a",
    "b": "\b",
    "f": "\f",
    "v": "\v",
}

# Named character literals.
_CHAR_NAMES = {
    "space": " ",
    "newline": "\n",
    "tab": "\t",
    "return": "\r",
    "null": "\0",
    "nul": "\0",
    "delete": "\x7f",
    "escape": "\x1b",
    "esc": "\x1b",
    "alarm": "\a",
    "backspace": "\b",
}


class Lexer:
    """Turns a string of Scheme source into a list of tokens."""

    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.line = 1
        self.col = 1
        self.tokens: List[Token] = []

    # ------------------------------------------------------------------
    # helpers

    def _peek(self, offset: int = 0) -> str:
        p = self.pos + offset
        return self.source[p] if p < len(self.source) else ""

    def _advance(self) -> str:
        ch = self.source[self.pos]
        self.pos += 1
        if ch == "\n":
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def _error(self, msg: str) -> "LexError":
        return LexError(msg, self.line, self.col)

    # ------------------------------------------------------------------
    # main loop

    def tokenize(self) -> List[Token]:
        source = self.source
        length = len(source)
        while self.pos < length:
            ch = source[self.pos]
            if ch in " \t\r\n":
                self._advance()
            elif ch == ";":
                self._line_comment()
            elif ch == "#" and self._peek(1) == "|":
                self._block_comment()
            elif ch == "#" and self._peek(1) == ";":
                self._datum_comment()
            elif ch == "(":
                self.tokens.append(Token("LPAREN", "(", self.line, self.col))
                self._advance()
            elif ch == ")":
                self.tokens.append(Token("RPAREN", ")", self.line, self.col))
                self._advance()
            elif ch == "[":
                self.tokens.append(Token("LBRACKET", "[", self.line, self.col))
                self._advance()
            elif ch == "]":
                self.tokens.append(Token("RBRACKET", "]", self.line, self.col))
                self._advance()
            elif ch == "{":
                self.tokens.append(Token("LPAREN", "(", self.line, self.col))
                self._advance()
            elif ch == "}":
                self.tokens.append(Token("RPAREN", ")", self.line, self.col))
                self._advance()
            elif ch == "'":
                self.tokens.append(Token("QUOTE", "'", self.line, self.col))
                self._advance()
            elif ch == "`":
                self.tokens.append(Token("QUASIQUOTE", "`", self.line, self.col))
                self._advance()
            elif ch == ",":
                if self._peek(1) == "@":
                    self.tokens.append(Token("UNQUOTE_SPLICING", ",@", self.line, self.col))
                    self._advance()
                    self._advance()
                else:
                    self.tokens.append(Token("UNQUOTE", ",", self.line, self.col))
                    self._advance()
            elif ch == '"':
                self.tokens.append(self._string_literal())
            elif ch == "#":
                self._hash_token()
            else:
                self._atom()
        self.tokens.append(Token("EOF", None, self.line, self.col))
        return self.tokens

    # ------------------------------------------------------------------
    # comment handling

    def _line_comment(self) -> None:
        while self.pos < len(self.source) and self.source[self.pos] != "\n":
            self._advance()

    def _block_comment(self) -> None:
        # #| ... |#  (nestable)
        self._advance()  # '#'
        self._advance()  # '|'
        depth = 1
        while self.pos < len(self.source):
            if self._peek() == "#" and self._peek(1) == "|":
                depth += 1
                self._advance()
                self._advance()
            elif self._peek() == "|" and self._peek(1) == "#":
                depth -= 1
                self._advance()
                self._advance()
                if depth == 0:
                    return
            else:
                self._advance()
        raise self._error("unterminated block comment")

    def _datum_comment(self) -> None:
        # #;  -- skip the next datum; the parser handles this, but
        # we emit a token so the parser knows to drop the next form.
        self.tokens.append(Token("DATUM_COMMENT", "#;", self.line, self.col))
        self._advance()
        self._advance()

    # ------------------------------------------------------------------
    # string literals

    def _string_literal(self) -> Token:
        start_line, start_col = self.line, self.col
        self._advance()  # opening quote
        chars: list[str] = []
        while self.pos < len(self.source):
            ch = self._advance()
            if ch == '"':
                return Token("STRING", "".join(chars), start_line, start_col)
            if ch == "\\":
                esc = self._advance()
                if esc == "":
                    raise self._error("unterminated string escape")
                if esc == "x":
                    hex_digits = ""
                    while self._peek() in "0123456789abcdefABCDEF":
                        hex_digits += self._advance()
                    if self._peek() == ";":
                        self._advance()
                    if not hex_digits:
                        raise self._error("empty \\x escape")
                    chars.append(chr(int(hex_digits, 16)))
                elif esc in _STRING_ESCAPES:
                    chars.append(_STRING_ESCAPES[esc])
                else:
                    chars.append(esc)
            else:
                chars.append(ch)
        raise self._error("unterminated string literal")

    # ------------------------------------------------------------------
    # # tokens

    def _hash_token(self) -> None:
        # Dispatch on the character following '#'
        next_ch = self._peek(1)
        if next_ch == "t":
            self._bool_literal(True)
        elif next_ch == "f":
            self._bool_literal(False)
        elif next_ch == "\\":
            self.tokens.append(self._char_literal())
        elif next_ch == "(":
            self.tokens.append(Token("VECTOR_PAREN", "#(", self.line, self.col))
            self._advance()
            self._advance()
        elif next_ch == "b" or next_ch == "o" or next_ch == "d" or next_ch == "x" or next_ch == "e" or next_ch == "i":
            self._number_prefixed()
        elif next_ch.isdigit():
            self._number_prefixed()
        else:
            raise self._error(f"unknown # syntax: #{next_ch}")

    def _bool_literal(self, value: bool) -> None:
        # Accept #t, #true, #f, #false
        start_line, start_col = self.line, self.col
        self._advance()  # '#'
        if value:
            self._advance()  # 't'
            if self._peek() in ("r", "R") and self._peek(1) in ("u", "U") and self._peek(2) in ("e", "E"):
                self._advance(); self._advance(); self._advance()
        else:
            self._advance()  # 'f'
            if self._peek() in ("a", "A") and self._peek(1) in ("l", "L") and self._peek(2) in ("s", "S") and self._peek(3) in ("e", "E"):
                self._advance(); self._advance(); self._advance(); self._advance()
        self.tokens.append(Token("BOOLEAN", value, start_line, start_col))

    def _char_literal(self) -> Token:
        start_line, start_col = self.line, self.col
        self._advance()  # '#'
        self._advance()  # '\'
        if self.pos >= len(self.source):
            raise self._error("unterminated character literal")
        first = self._advance()
        # Check for named characters
        if first.isalpha() and self._peek().isalpha():
            name = first
            while self._peek().isalpha():
                name += self._advance()
            low = name.lower()
            if low in _CHAR_NAMES:
                return Token("CHAR", _CHAR_NAMES[low], start_line, start_col)
            if len(name) > 1:
                raise self._error(f"unknown character name: #\\{name}")
            return Token("CHAR", first, start_line, start_col)
        return Token("CHAR", first, start_line, start_col)

    def _number_prefixed(self) -> None:
        # Handles #b, #o, #d, #x, #e, #i prefixes and exact/inexact
        start_line, start_col = self.line, self.col
        self._advance()  # '#'
        radix = 10
        exactness = None  # None, 'e' (exact), 'i' (inexact)
        consumed_prefix = ""
        while self.pos < len(self.source):
            ch = self.source[self.pos]
            if ch in "bBoOdDxX":
                c = ch.lower()
                if c == "b":
                    radix = 2
                elif c == "o":
                    radix = 8
                elif c == "d":
                    radix = 10
                elif c == "x":
                    radix = 16
                consumed_prefix += ch
                self._advance()
            elif ch in "eE":
                exactness = "e"
                consumed_prefix += ch
                self._advance()
            elif ch in "iI":
                exactness = "i"
                consumed_prefix += ch
                self._advance()
            else:
                break
        # Now read the number body
        text = self._read_number_body(radix)
        val = self._parse_number(text, radix, exactness)
        tok_type = "INT" if isinstance(val, int) else "FLOAT" if isinstance(val, float) else "RATIONAL"
        self.tokens.append(Token(tok_type, val, start_line, start_col))

    def _read_number_body(self, radix: int) -> str:
        digits = {
            2: "01",
            8: "01234567",
            10: "0123456789",
            16: "0123456789abcdefABCDEF",
        }[radix]
        text = ""
        while self.pos < len(self.source):
            ch = self.source[self.pos]
            if ch in digits or ch in "+-.eE/":
                text += ch
                self._advance()
            else:
                break
        return text

    def _parse_number(self, text: str, radix: int, exactness):
        # Handle rationals (e.g. "3/4")
        if "/" in text and radix == 10:
            parts = text.split("/")
            if len(parts) == 2:
                try:
                    num = int(parts[0])
                    den = int(parts[1])
                except ValueError:
                    raise self._error(f"bad rational: {text}")
                if den == 0:
                    raise self._error("division by zero in rational literal")
                from fractions import Fraction
                val = Fraction(num, den)
                if exactness == "i":
                    return float(val)
                return val
        if radix == 10:
            if "." in text or "e" in text or "E" in text:
                val = float(text)
                if exactness == "e":
                    val = int(val) if val == int(val) else val
                return val
            try:
                val = int(text, radix)
            except ValueError:
                raise self._error(f"bad number: {text}")
            if exactness == "i":
                return float(val)
            return val
        try:
            val = int(text, radix)
        except ValueError:
            raise self._error(f"bad number (radix {radix}): {text}")
        if exactness == "i":
            return float(val)
        return val

    # ------------------------------------------------------------------
    # atoms (symbols and numbers)

    def _atom(self) -> None:
        start_line, start_col = self.line, self.col
        ch = self.source[self.pos]
        # Try to read a number: starts with digit, +, -, or . followed by digit
        if ch.isdigit() or (ch == "." and self._peek(1).isdigit()):
            self._number(start_line, start_col)
            return
        if ch in "+-" and (self._peek(1).isdigit() or (self._peek(1) == "." and self._peek(2).isdigit())):
            self._number(start_line, start_col)
            return
        if ch in "+-." and self._peek(1) in "+-." and self._peek(2) in _SYMBOL_START:
            # e.g. +-, ..., -> but also symbols like +-foo
            self._symbol(start_line, start_col)
            return
        self._symbol(start_line, start_col)

    def _number(self, start_line: int, start_col: int) -> None:
        text = ""
        while self.pos < len(self.source):
            ch = self.source[self.pos]
            if ch in "0123456789+-." or ch in "eE/" or ch == "i" and False:  # 'i' not part of numbers here
                text += ch
                self._advance()
            elif ch == "/" :
                text += ch
                self._advance()
            else:
                break
        val = self._parse_number(text, 10, None)
        tok_type = "INT" if isinstance(val, int) else "FLOAT" if isinstance(val, float) else "RATIONAL"
        self.tokens.append(Token(tok_type, val, start_line, start_col))

    def _symbol(self, start_line: int, start_col: int) -> None:
        text = ""
        while self.pos < len(self.source):
            ch = self.source[self.pos]
            if ch in _SYMBOL_CHARS or ch.isalnum():
                text += ch
                self._advance()
            else:
                break
        if not text:
            raise self._error(f"unexpected character: {self.source[self.pos]!r}")
        self.tokens.append(Token("SYMBOL", text, start_line, start_col))


def tokenize(source: str) -> List[Token]:
    """Tokenize Scheme source and return a list of tokens (excluding the trailing EOF)."""
    toks = Lexer(source).tokenize()
    return [t for t in toks if t.type != "EOF"] or toks