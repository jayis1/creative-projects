"""MiniLang lexer — a hand-written scanner that produces a token stream.

Token kinds
-----------
* literals: ``INT``, ``STRING``, ``TRUE``, ``FALSE``, ``NIL``
* identifiers / keywords: ``IDENT``, then a fixed set of keyword tokens
* operators: ``+ - * / % < <= > >= == != = && || !``
* punctuation: ``( ) { } [ ] ; , . :``
* ``EOF``

The lexer also tracks line / column for every token so that errors can
point to the exact source location.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Iterator

from .errors import LexError


class TokenKind(Enum):
    # literals
    INT = auto()
    STRING = auto()
    # keywords
    LET = auto()
    CONST = auto()
    FN = auto()
    IF = auto()
    ELSE = auto()
    WHILE = auto()
    FOR = auto()
    IN = auto()
    RETURN = auto()
    BREAK = auto()
    CONTINUE = auto()
    TRUE = auto()
    FALSE = auto()
    NIL = auto()
    PRINT = auto()
    AND = auto()      # keyword form of &&
    OR = auto()       # keyword form of ||

    # identifiers
    IDENT = auto()

    # operators
    PLUS = auto()       # +
    MINUS = auto()      # -
    STAR = auto()       # *
    SLASH = auto()      # /
    PERCENT = auto()    # %
    EQ = auto()         # =
    EQEQ = auto()       # ==
    NEQ = auto()        # !=
    LT = auto()         # <
    LE = auto()         # <=
    GT = auto()         # >
    GE = auto()         # >=
    BANG = auto()       # !
    AMP_AMP = auto()    # &&
    PIPE_PIPE = auto()  # ||

    # punctuation
    LPAREN = auto()
    RPAREN = auto()
    LBRACE = auto()
    RBRACE = auto()
    LBRACKET = auto()
    RBRACKET = auto()
    SEMI = auto()
    COMMA = auto()
    DOT = auto()
    COLON = auto()
    ARROW = auto()   # ->

    EOF = auto()


KEYWORDS: dict[str, TokenKind] = {
    "let": TokenKind.LET,
    "const": TokenKind.CONST,
    "fn": TokenKind.FN,
    "if": TokenKind.IF,
    "else": TokenKind.ELSE,
    "while": TokenKind.WHILE,
    "for": TokenKind.FOR,
    "in": TokenKind.IN,
    "return": TokenKind.RETURN,
    "break": TokenKind.BREAK,
    "continue": TokenKind.CONTINUE,
    "true": TokenKind.TRUE,
    "false": TokenKind.FALSE,
    "nil": TokenKind.NIL,
    "and": TokenKind.AND,
    "or": TokenKind.OR,
}


@dataclass(slots=True)
class Token:
    kind: TokenKind
    lexeme: str
    line: int
    col: int

    def __repr__(self) -> str:
        return f"Token({self.kind.name}, {self.lexeme!r}, {self.line}:{self.col})"


# --------------------------------------------------------------------------- #
# multi-character operator lookup (sorted by length-descending so that        #
# the lexer tries the longest match first)                                    #
# --------------------------------------------------------------------------- #
_TWO_CHAR_OPS: dict[str, TokenKind] = {
    "==": TokenKind.EQEQ,
    "!=": TokenKind.NEQ,
    "<=": TokenKind.LE,
    ">=": TokenKind.GE,
    "&&": TokenKind.AMP_AMP,
    "||": TokenKind.PIPE_PIPE,
    "->": TokenKind.ARROW,
}
_ONE_CHAR_OPS: dict[str, TokenKind] = {
    "+": TokenKind.PLUS,
    "-": TokenKind.MINUS,
    "*": TokenKind.STAR,
    "/": TokenKind.SLASH,
    "%": TokenKind.PERCENT,
    "=": TokenKind.EQ,
    "<": TokenKind.LT,
    ">": TokenKind.GT,
    "!": TokenKind.BANG,
    "(": TokenKind.LPAREN,
    ")": TokenKind.RPAREN,
    "{": TokenKind.LBRACE,
    "}": TokenKind.RBRACE,
    "[": TokenKind.LBRACKET,
    "]": TokenKind.RBRACKET,
    ";": TokenKind.SEMI,
    ",": TokenKind.COMMA,
    ".": TokenKind.DOT,
    ":": TokenKind.COLON,
}


class Lexer:
    """Turn a MiniLang source string into a list of :class:`Token` objects."""

    def __init__(self, source: str, name: str = "<string>"):
        self.source = source
        self.name = name
        self._pos = 0
        self._line = 1
        self._col = 1
        self._tokens: list[Token] = []

    # -- public API --------------------------------------------------------- #
    def tokenize(self) -> list[Token]:
        while not self._at_end():
            ch = self._peek()
            if ch in (" ", "\t", "\r"):
                self._advance()
            elif ch == "\n":
                self._advance()
            elif ch == "/" and self._peek_next() == "/":
                # line comment
                while not self._at_end() and self._peek() != "\n":
                    self._advance()
            elif ch == "/" and self._peek_next() == "*":
                self._block_comment()
            elif ch == '"':
                self._string()
            elif ch.isdigit():
                self._number()
            elif ch == "_" or ch.isalpha():
                self._identifier()
            else:
                self._operator()
        self._tokens.append(Token(TokenKind.EOF, "", self._line, self._col))
        return self._tokens

    # -- helpers ----------------------------------------------------------- #
    def _peek(self, offset: int = 0) -> str:
        i = self._pos + offset
        if i >= len(self.source):
            return "\0"
        return self.source[i]

    def _peek_next(self) -> str:
        return self._peek(1)

    def _advance(self) -> str:
        ch = self.source[self._pos]
        self._pos += 1
        if ch == "\n":
            self._line += 1
            self._col = 1
        else:
            self._col += 1
        return ch

    def _at_end(self) -> bool:
        return self._pos >= len(self.source)

    # -- tokenisers -------------------------------------------------------- #
    def _number(self) -> None:
        start_line, start_col = self._line, self._col
        start = self._pos
        while not self._at_end() and self._peek().isdigit():
            self._advance()
        lexeme = self.source[start:self._pos]
        self._tokens.append(Token(TokenKind.INT, lexeme, start_line, start_col))

    def _string(self) -> None:
        start_line, start_col = self._line, self._col
        self._advance()  # opening quote
        chars: list[str] = []
        while not self._at_end() and self._peek() != '"':
            ch = self._advance()
            if ch == "\\":
                esc = self._advance()
                chars.append(self._decode_escape(esc, start_line, start_col))
            else:
                chars.append(ch)
        if self._at_end():
            raise LexError("unterminated string literal",
                           start_line, start_col, self.name)
        self._advance()  # closing quote
        self._tokens.append(Token(TokenKind.STRING, "".join(chars),
                                  start_line, start_col))

    def _decode_escape(self, esc: str, line: int, col: int) -> str:
        table = {
            "n": "\n", "t": "\t", "r": "\r", "\\": "\\",
            '"': '"', "0": "\0",
        }
        if esc in table:
            return table[esc]
        raise LexError(f"invalid escape sequence \\{esc}", line, col, self.name)

    def _identifier(self) -> None:
        start_line, start_col = self._line, self._col
        start = self._pos
        while not self._at_end() and (self._peek() == "_" or self._peek().isalnum()):
            self._advance()
        lexeme = self.source[start:self._pos]
        kind = KEYWORDS.get(lexeme, TokenKind.IDENT)
        self._tokens.append(Token(kind, lexeme, start_line, start_col))

    def _block_comment(self) -> None:
        self._advance()  # /
        self._advance()  # *
        while not self._at_end():
            if self._peek() == "*" and self._peek_next() == "/":
                self._advance()
                self._advance()
                return
            self._advance()
        raise LexError("unterminated block comment", self._line, self._col, self.name)

    def _operator(self) -> None:
        start_line, start_col = self._line, self._col
        two = self._peek() + self._peek_next()
        if two in _TWO_CHAR_OPS:
            self._advance(); self._advance()
            self._tokens.append(Token(_TWO_CHAR_OPS[two], two, start_line, start_col))
            return
        one = self._peek()
        if one in _ONE_CHAR_OPS:
            self._advance()
            self._tokens.append(Token(_ONE_CHAR_OPS[one], one, start_line, start_col))
            return
        raise LexError(f"unexpected character {one!r}", start_line, start_col, self.name)


def tokenize(source: str, name: str = "<string>") -> list[Token]:
    """Convenience function: lex *source* and return the token list."""
    return Lexer(source, name).tokenize()


def token_stream(source: str, name: str = "<string>") -> Iterator[Token]:
    """Streaming wrapper around :func:`tokenize` (fully buffers internally)."""
    yield from Lexer(source, name).tokenize()