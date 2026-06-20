"""Datalog parser — tokenizer + recursive-descent parser.

Grammar (simplified)
--------------------
program     := statement*
statement   := fact | rule | query
fact        := atom '.'
rule        := atom ':-' literal (',' literal)* '.'
query       := '?-' atom '.'
atom        := IDENT '(' term (',' term)* ')' | IDENT
literal     := 'not' atom | atom
term        := VARIABLE | constant
constant    := STRING | INT | FLOAT | 'true' | 'false'
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional, Tuple

from .ast import (
    Atom,
    Constant,
    Fact,
    Literal,
    Query,
    Program,
    Rule,
    Term,
    Variable,
)


# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------


class TokenType(Enum):
    IDENT = auto()       # lowercase identifier (predicate or constant)
    VARIABLE = auto()    # uppercase identifier or underscore
    STRING = auto()      # "..." string literal
    INT = auto()
    FLOAT = auto()
    TRUE = auto()
    FALSE = auto()
    LPAREN = auto()      # (
    RPAREN = auto()      # )
    COMMA = auto()
    DOT = auto()
    COLON_DASH = auto()  # :-
    QUESTION = auto()    # ?-
    NOT = auto()
    OP = auto()          # comparison operator: < > <= >= != ==
    EOF = auto()


@dataclass
class Token:
    type: TokenType
    value: str
    line: int
    col: int

    def __repr__(self) -> str:
        return f"Token({self.type.name}, {self.value!r}, line={self.line})"


class LexError(Exception):
    pass


class ParseError(Exception):
    pass


_SYMBOLS = {
    "(": TokenType.LPAREN,
    ")": TokenType.RPAREN,
    ",": TokenType.COMMA,
    ".": TokenType.DOT,
}


def _is_ident_start(c: str) -> bool:
    return c.isalpha() or c == "_"


def _is_ident_cont(c: str) -> bool:
    return c.isalnum() or c == "_"


class Lexer:
    """Turn a Datalog source string into a list of tokens."""

    def __init__(self, src: str) -> None:
        self.src = src
        self.pos = 0
        self.line = 1
        self.col = 1

    def error(self, msg: str) -> None:
        raise LexError(f"Lex error at line {self.line}, col {self.col}: {msg}")

    def peek(self) -> str:
        return self.src[self.pos] if self.pos < len(self.src) else ""

    def advance(self) -> str:
        c = self.src[self.pos]
        self.pos += 1
        if c == "\n":
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return c

    def tokenize(self) -> List[Token]:
        tokens: List[Token] = []
        while True:
            self._skip_ws_and_comments()
            if self.pos >= len(self.src):
                break
            c = self.peek()
            line, col = self.line, self.col
            if c in _SYMBOLS:
                self.advance()
                tokens.append(Token(_SYMBOLS[c], c, line, col))
            elif c == ":":
                # expect :-
                self.advance()
                if self.peek() != "-":
                    self.error("expected ':-'")
                self.advance()
                tokens.append(Token(TokenType.COLON_DASH, ":-", line, col))
            elif c == "?":
                self.advance()
                if self.peek() != "-":
                    self.error("expected '?-'")
                self.advance()
                tokens.append(Token(TokenType.QUESTION, "?-", line, col))
            elif c in "<>=!":
                tokens.append(self._read_op(line, col))
            elif c == '"':
                tokens.append(self._read_string(line, col))
            elif c.isdigit() or (c == "-" and self._peek_next_isdigit()):
                tokens.append(self._read_number(line, col))
            elif _is_ident_start(c):
                tokens.append(self._read_ident(line, col))
            else:
                self.error(f"unexpected character {c!r}")
        tokens.append(Token(TokenType.EOF, "", self.line, self.col))
        return tokens

    def _peek_next_isdigit(self) -> bool:
        return self.pos + 1 < len(self.src) and self.src[self.pos + 1].isdigit()

    def _skip_ws_and_comments(self) -> None:
        while self.pos < len(self.src):
            c = self.peek()
            if c in " \t\r\n":
                self.advance()
            elif c == "%":
                # line comment
                while self.pos < len(self.src) and self.peek() != "\n":
                    self.advance()
            elif c == "/" and self.pos + 1 < len(self.src) and self.src[self.pos + 1] == "*":
                # block comment
                self.advance()
                self.advance()
                while self.pos < len(self.src):
                    if self.peek() == "*" and self.pos + 1 < len(self.src) and self.src[self.pos + 1] == "/":
                        self.advance()
                        self.advance()
                        break
                    self.advance()
            else:
                break

    def _read_op(self, line: int, col: int) -> Token:
        """Read a comparison operator: < > <= >= != =="""
        c = self.advance()
        nxt = self.peek()
        if c == "<" and nxt == "=":
            self.advance()
            return Token(TokenType.OP, "<=", line, col)
        if c == ">" and nxt == "=":
            self.advance()
            return Token(TokenType.OP, ">=", line, col)
        if c == "!" and nxt == "=":
            self.advance()
            return Token(TokenType.OP, "!=", line, col)
        if c == "=" and nxt == "=":
            self.advance()
            return Token(TokenType.OP, "==", line, col)
        if c in ("<", ">"):
            return Token(TokenType.OP, c, line, col)
        self.error(f"unexpected character {c!r}")
        raise AssertionError("unreachable")  # self.error always raises

    def _read_string(self, line: int, col: int) -> Token:
        self.advance()  # opening quote
        chars: List[str] = []
        while True:
            if self.pos >= len(self.src):
                self.error("unterminated string")
            c = self.advance()
            if c == '"':
                break
            if c == "\\":
                esc = self.advance()
                mapping = {"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\"}
                chars.append(mapping.get(esc, esc))
            else:
                chars.append(c)
        return Token(TokenType.STRING, "".join(chars), line, col)

    def _read_number(self, line: int, col: int) -> Token:
        start = self.pos
        if self.peek() == "-":
            self.advance()
        while self.pos < len(self.src) and self.peek().isdigit():
            self.advance()
        is_float = False
        if self.peek() == "." and self.pos + 1 < len(self.src) and self.src[self.pos + 1].isdigit():
            is_float = True
            self.advance()  # .
            while self.pos < len(self.src) and self.peek().isdigit():
                self.advance()
        # exponent
        if self.peek() in ("e", "E"):
            is_float = True
            self.advance()
            if self.peek() in ("+", "-"):
                self.advance()
            while self.pos < len(self.src) and self.peek().isdigit():
                self.advance()
        text = self.src[start:self.pos]
        if is_float:
            return Token(TokenType.FLOAT, text, line, col)
        return Token(TokenType.INT, text, line, col)

    def _read_ident(self, line: int, col: int) -> Token:
        start = self.pos
        while self.pos < len(self.src) and _is_ident_cont(self.peek()):
            self.advance()
        text = self.src[start:self.pos]
        if text == "not":
            return Token(TokenType.NOT, text, line, col)
        if text == "true":
            return Token(TokenType.TRUE, text, line, col)
        if text == "false":
            return Token(TokenType.FALSE, text, line, col)
        if text[0].isupper() or text[0] == "_":
            return Token(TokenType.VARIABLE, text, line, col)
        return Token(TokenType.IDENT, text, line, col)


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


class Parser:
    """Recursive-descent parser producing a :class:`Program`."""

    def __init__(self, tokens: List[Token]) -> None:
        self.tokens = tokens
        self.pos = 0

    @classmethod
    def from_source(cls, src: str) -> "Parser":
        return cls(Lexer(src).tokenize())

    def error(self, msg: str) -> None:
        tok = self.tokens[self.pos] if self.pos < len(self.tokens) else self.tokens[-1]
        raise ParseError(f"Parse error at line {tok.line}, col {tok.col}: {msg} (got {tok.type.name} {tok.value!r})")

    def peek(self) -> Token:
        return self.tokens[self.pos]

    def at(self, t: TokenType) -> bool:
        return self.peek().type == t

    def advance(self) -> Token:
        tok = self.tokens[self.pos]
        if tok.type != TokenType.EOF:
            self.pos += 1
        return tok

    def expect(self, t: TokenType, what: Optional[str] = None) -> Token:
        if not self.at(t):
            self.error(f"expected {what or t.name}")
        return self.advance()

    # --- grammar ---

    def parse_program(self) -> Program:
        prog = Program()
        while not self.at(TokenType.EOF):
            self.parse_statement(prog)
        return prog

    def parse_statement(self, prog: Program) -> None:
        if self.at(TokenType.QUESTION):
            self.advance()
            atom = self.parse_atom()
            # Trailing '.' is optional for queries (user-friendly).
            if self.at(TokenType.DOT):
                self.advance()
            prog.queries.append(Query(atom))
            return
        atom = self.parse_atom()
        if self.at(TokenType.COLON_DASH):
            self.advance()
            body = [self.parse_literal()]
            while self.at(TokenType.COMMA):
                self.advance()
                body.append(self.parse_literal())
            self.expect(TokenType.DOT, "'.'")
            rule = Rule(atom, body)
            prog.rules.append(rule)
            return
        # fact
        self.expect(TokenType.DOT, "'.'")
        if not atom.is_ground():
            raise ParseError(f"fact {atom} is not ground (contains variables)")
        prog.facts.append(Fact(atom))

    def parse_literal(self) -> Literal:
        if self.at(TokenType.NOT):
            self.advance()
            atom = self.parse_atom_or_infix()
            return Literal(atom, positive=False)
        return Literal(self.parse_atom_or_infix(), positive=True)

    def parse_atom_or_infix(self) -> Atom:
        """Parse an atom, or an infix comparison ``term OP term``.

        Datalog syntax allows infix comparison operators in rule bodies,
        e.g. ``X > 3`` which is sugar for ``>(X, 3)``."""
        # Prefix form: op(term, term)
        if self.at(TokenType.OP):
            tok = self.advance()
            self.expect(TokenType.LPAREN, "'('")
            terms = [self.parse_term()]
            while self.at(TokenType.COMMA):
                self.advance()
                terms.append(self.parse_term())
            self.expect(TokenType.RPAREN, "')'")
            return Atom(tok.value, terms)
        # Infix form: the first token is a term (VARIABLE, INT, FLOAT,
        # STRING, or IDENT-as-constant) followed by an OP.
        if self.peek().type in (TokenType.VARIABLE, TokenType.INT,
                                TokenType.FLOAT, TokenType.STRING):
            left = self.parse_term()
            if self.at(TokenType.OP):
                op_tok = self.advance()
                right = self.parse_term()
                return Atom(op_tok.value, [left, right])
            # Not infix — it's a malformed atom (a bare term where an
            # atom was expected).
            self.error("expected atom or infix comparison")
        # Regular atom (IDENT predicate, possibly with args)
        atom = self.parse_atom()
        # Infix where left side is a bare IDENT constant: foo > 3
        if self.at(TokenType.OP) and atom.arity == 0:
            op_tok = self.advance()
            right = self.parse_term()
            left = Constant(atom.predicate)
            return Atom(op_tok.value, [left, right])
        return atom

    def parse_atom(self) -> Atom:
        tok = self.expect(TokenType.IDENT, "predicate identifier")
        pred = tok.value
        if self.at(TokenType.LPAREN):
            self.advance()
            terms: List[Term] = [self.parse_term()]
            while self.at(TokenType.COMMA):
                self.advance()
                terms.append(self.parse_term())
            self.expect(TokenType.RPAREN, "')'")
        else:
            terms = []
        return Atom(pred, terms)

    def parse_term(self) -> Term:
        tok = self.peek()
        if tok.type == TokenType.VARIABLE:
            self.advance()
            # Anonymous variable _ gets a unique name so multiple _ in one
            # atom don't bind to each other.
            if tok.value == "_":
                return Variable(f"_{tok.line}_{tok.col}")
            return Variable(tok.value)
        if tok.type == TokenType.STRING:
            self.advance()
            return Constant(tok.value)
        if tok.type == TokenType.INT:
            self.advance()
            return Constant(int(tok.value))
        if tok.type == TokenType.FLOAT:
            self.advance()
            return Constant(float(tok.value))
        if tok.type == TokenType.TRUE:
            self.advance()
            return Constant(True)
        if tok.type == TokenType.FALSE:
            self.advance()
            return Constant(False)
        if tok.type == TokenType.IDENT:
            # bare identifier as a constant (e.g. foo with no parens)
            self.advance()
            return Constant(tok.value)
        self.error("expected term")
        raise AssertionError("unreachable")  # self.error always raises


# ---------------------------------------------------------------------------
# Convenience
# ---------------------------------------------------------------------------


def parse(src: str) -> Program:
    """Parse a Datalog source string and return a :class:`Program`."""
    return Parser.from_source(src).parse_program()