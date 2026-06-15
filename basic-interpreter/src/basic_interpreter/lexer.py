"""Token types and lexer for the BASIC interpreter."""

from __future__ import annotations

from enum import Enum, auto
from dataclasses import dataclass
from typing import Any, List


class TokenType(Enum):
    """Enumeration of all BASIC token types."""
    NUMBER = auto()
    STRING = auto()
    IDENT = auto()
    # Keywords
    LET = auto()
    PRINT = auto()
    INPUT = auto()
    IF = auto()
    THEN = auto()
    ELSE = auto()
    FOR = auto()
    TO = auto()
    STEP = auto()
    NEXT = auto()
    WHILE = auto()
    WEND = auto()
    DO = auto()
    LOOP = auto()
    UNTIL = auto()
    GOTO = auto()
    GOSUB = auto()
    RETURN = auto()
    DIM = auto()
    ERASE = auto()
    READ = auto()
    DATA = auto()
    RESTORE = auto()
    DEF = auto()
    FN = auto()
    REM = auto()
    END = auto()
    STOP = auto()
    ON = auto()
    SWAP = auto()
    CLS = auto()
    COLOR = auto()
    LOCATE = auto()
    SELECT = auto()
    CASE = auto()
    IS = auto()
    OPEN = auto()
    CLOSE = auto()
    BEEP = auto()
    LINE = auto()
    USING = auto()
    ERROR = auto()
    RESUME = auto()
    XOR = auto()
    EQV = auto()
    IMP = auto()
    EXIT = auto()
    # Operators
    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    CARET = auto()
    BACKSLASH = auto()
    MOD = auto()
    EQ = auto()
    NE = auto()
    LT = auto()
    GT = auto()
    LE = auto()
    GE = auto()
    AND = auto()
    OR = auto()
    NOT = auto()
    LPAREN = auto()
    RPAREN = auto()
    COMMA = auto()
    SEMI = auto()
    COLON = auto()
    HASH = auto()
    # Line number (only at start of line)
    LINENUM = auto()
    # EOF
    EOF = auto()


# Mapping from keyword strings to token types
KEYWORDS: dict[str, TokenType] = {
    "LET": TokenType.LET, "PRINT": TokenType.PRINT, "INPUT": TokenType.INPUT,
    "IF": TokenType.IF, "THEN": TokenType.THEN, "ELSE": TokenType.ELSE,
    "FOR": TokenType.FOR, "TO": TokenType.TO, "STEP": TokenType.STEP,
    "NEXT": TokenType.NEXT, "WHILE": TokenType.WHILE, "WEND": TokenType.WEND,
    "DO": TokenType.DO, "LOOP": TokenType.LOOP, "UNTIL": TokenType.UNTIL,
    "GOTO": TokenType.GOTO, "GOSUB": TokenType.GOSUB, "RETURN": TokenType.RETURN,
    "DIM": TokenType.DIM, "ERASE": TokenType.ERASE, "READ": TokenType.READ,
    "DATA": TokenType.DATA, "RESTORE": TokenType.RESTORE, "DEF": TokenType.DEF,
    "FN": TokenType.FN, "REM": TokenType.REM, "END": TokenType.END,
    "STOP": TokenType.STOP, "ON": TokenType.ON, "SWAP": TokenType.SWAP,
    "CLS": TokenType.CLS, "COLOR": TokenType.COLOR, "LOCATE": TokenType.LOCATE,
    "SELECT": TokenType.SELECT, "CASE": TokenType.CASE, "IS": TokenType.IS,
    "OPEN": TokenType.OPEN, "CLOSE": TokenType.CLOSE, "BEEP": TokenType.BEEP,
    "LINE": TokenType.LINE, "USING": TokenType.USING,
    "ERROR": TokenType.ERROR, "RESUME": TokenType.RESUME,
    "AND": TokenType.AND, "OR": TokenType.OR, "NOT": TokenType.NOT,
    "MOD": TokenType.MOD, "XOR": TokenType.XOR, "EQV": TokenType.EQV,
    "IMP": TokenType.IMP, "EXIT": TokenType.EXIT,
}


@dataclass
class Token:
    """Represents a lexical token with type, value, and source position."""
    type: TokenType
    value: Any
    line: int = 0
    col: int = 0

    def __repr__(self) -> str:
        return f"Token({self.type.name}, {self.value!r}, line={self.line}, col={self.col})"


class Lexer:
    """Tokenize a BASIC source line into a list of Token objects.

    The lexer handles:
    - Line numbers at the start of lines
    - Keywords (case-insensitive)
    - Numeric literals (including scientific notation)
    - String literals with escaped quotes
    - Operators and punctuation
    - Comments (REM statements)
    """

    def __init__(self, text: str, line_num: int = 0) -> None:
        self.text = text
        self.pos = 0
        self.line_num = line_num
        self.tokens: List[Token] = []

    def _peek(self) -> str:
        """Return the current character without advancing."""
        if self.pos < len(self.text):
            return self.text[self.pos]
        return "\0"

    def _advance(self) -> str:
        """Advance position and return the current character."""
        ch = self.text[self.pos]
        self.pos += 1
        return ch

    def _skip_spaces(self) -> None:
        """Skip whitespace characters (spaces and tabs)."""
        while self.pos < len(self.text) and self.text[self.pos] in " \t":
            self.pos += 1

    def _read_number(self) -> float:
        """Read a numeric literal, including scientific notation."""
        start = self.pos
        while self.pos < len(self.text) and (self.text[self.pos].isdigit() or self.text[self.pos] == "."):
            self.pos += 1
        if self.pos < len(self.text) and self.text[self.pos] in "eE":
            self.pos += 1
            if self.pos < len(self.text) and self.text[self.pos] in "+-":
                self.pos += 1
            while self.pos < len(self.text) and self.text[self.pos].isdigit():
                self.pos += 1
        return float(self.text[start:self.pos])

    def _read_string(self) -> str:
        """Read a string literal, handling escaped quotes (double-quote)."""
        self._advance()  # skip opening quote
        result: list[str] = []
        while self.pos < len(self.text):
            ch = self.text[self.pos]
            if ch == '"':
                self._advance()
                if self.pos < len(self.text) and self.text[self.pos] == '"':
                    result.append('"')
                    self._advance()
                    continue
                return "".join(result)
            result.append(ch)
            self._advance()
        return "".join(result)

    def _read_ident(self) -> str:
        """Read an identifier (variable name or keyword candidate)."""
        start = self.pos
        while self.pos < len(self.text) and (self.text[self.pos].isalnum() or self.text[self.pos] in "._$"):
            self.pos += 1
        return self.text[start:self.pos]

    def tokenize(self) -> List[Token]:
        """Tokenize the source line and return a list of Token objects.

        Returns:
            List of Token objects representing the lexical tokens in the source line.
            The last token is always an EOF token.
        """
        # Check for line number at the start
        self._skip_spaces()
        if self.pos < len(self.text) and self.text[self.pos].isdigit():
            start = self.pos
            while self.pos < len(self.text) and self.text[self.pos].isdigit():
                self.pos += 1
            num_str = self.text[start:self.pos]
            self._skip_spaces()
            self.tokens.append(Token(TokenType.LINENUM, int(num_str), self.line_num, start))

        while self.pos < len(self.text):
            self._skip_spaces()
            if self.pos >= len(self.text):
                break

            ch = self.text[self.pos]
            col = self.pos

            if ch == '"':
                s = self._read_string()
                self.tokens.append(Token(TokenType.STRING, s, self.line_num, col))
                continue

            if ch.isdigit() or (ch == "." and self.pos + 1 < len(self.text) and self.text[self.pos + 1].isdigit()):
                n = self._read_number()
                self.tokens.append(Token(TokenType.NUMBER, n, self.line_num, col))
                continue

            if ch.isalpha() or ch == "_":
                ident = self._read_ident()
                upper = ident.upper()
                if upper in KEYWORDS:
                    tok_type = KEYWORDS[upper]
                    if tok_type == TokenType.REM:
                        self.tokens.append(Token(TokenType.REM, self.text[self.pos:], self.line_num, col))
                        break
                    self.tokens.append(Token(tok_type, upper, self.line_num, col))
                else:
                    self.tokens.append(Token(TokenType.IDENT, ident, self.line_num, col))
                continue

            if ch == "<":
                self._advance()
                if self._peek() == ">":
                    self._advance()
                    self.tokens.append(Token(TokenType.NE, "<>", self.line_num, col))
                elif self._peek() == "=":
                    self._advance()
                    self.tokens.append(Token(TokenType.LE, "<=", self.line_num, col))
                else:
                    self.tokens.append(Token(TokenType.LT, "<", self.line_num, col))
                continue
            if ch == ">":
                self._advance()
                if self._peek() == "=":
                    self._advance()
                    self.tokens.append(Token(TokenType.GE, ">=", self.line_num, col))
                else:
                    self.tokens.append(Token(TokenType.GT, ">", self.line_num, col))
                continue

            simple: dict[str, TokenType] = {
                "+": TokenType.PLUS, "-": TokenType.MINUS,
                "*": TokenType.STAR, "/": TokenType.SLASH,
                "^": TokenType.CARET, "\\": TokenType.BACKSLASH,
                "(": TokenType.LPAREN, ")": TokenType.RPAREN,
                ",": TokenType.COMMA, ";": TokenType.SEMI,
                ":": TokenType.COLON, "=": TokenType.EQ,
                "#": TokenType.HASH,
            }
            if ch in simple:
                self._advance()
                self.tokens.append(Token(simple[ch], ch, self.line_num, col))
                continue

            self._advance()

        self.tokens.append(Token(TokenType.EOF, None, self.line_num, self.pos))
        return self.tokens