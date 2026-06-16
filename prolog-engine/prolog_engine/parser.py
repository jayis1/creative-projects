"""Parser for the mini-Prolog engine.

Handles infix operators (=, \\=, is, <, >, =<, >=, ==, \\==) and
standard Prolog syntax for clauses, queries, lists, and terms.
"""

from __future__ import annotations

from prolog_engine.lexer import Token, TokenType, Lexer
from prolog_engine.ast_nodes import (
    Atom, Variable, Number, String, Compound, Clause, Query, Program, Term,
)

# Operator precedence table (lower number = binds tighter)
# Format: name -> (precedence, associativity)
INFIX_OPS = {
    "is": (700, "xfx"),
    "=": (700, "xfx"),
    "\\=": (700, "xfx"),
    "==": (700, "xfx"),
    "\\==": (700, "xfx"),
    "<": (700, "xfx"),
    ">": (700, "xfx"),
    "=<": (700, "xfx"),
    ">=": (700, "xfx"),
    # Arithmetic operators (used in is/2 expressions)
    "+": (500, "yfx"),
    "-": (500, "yfx"),
    "*": (400, "yfx"),
    "/": (400, "yfx"),
    "//": (400, "yfx"),
    "mod": (400, "yfx"),
    "rem": (400, "yfx"),
    "**": (200, "xfx"),
    "^": (200, "xfx"),
}


class ParseError(Exception):
    """Raised when the parser encounters unexpected tokens."""

    def __init__(self, message: str, token: Token | None = None):
        if token:
            super().__init__(f"{message} at line {token.line}, column {token.col}")
        else:
            super().__init__(message)
        self.token = token


class Parser:
    """Recursive-descent parser for Prolog programs."""

    def __init__(self, tokens: list[Token]):
        self._tokens = tokens
        self._pos = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @classmethod
    def from_source(cls, source: str) -> "Parser":
        """Create a parser from raw Prolog source text."""
        lexer = Lexer(source)
        return cls(lexer.tokens)

    def parse_program(self) -> Program:
        """Parse a complete program (zero or more clauses)."""
        program = Program()
        while not self._at_end():
            if self._current().type == TokenType.DOT:
                self._advance()
                continue
            if self._current().type == TokenType.QUERY:
                self._advance()
                goals = self._parse_body()
                self._expect(TokenType.DOT)
                continue
            clause = self._parse_clause()
            program.add_clause(clause)
        return program

    def parse_query(self) -> Query:
        """Parse a query string (e.g., '?- father(X, Y).')."""
        if self._current().type == TokenType.QUERY:
            self._advance()
        goals = self._parse_body()
        self._expect(TokenType.DOT)
        return Query(goals)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _current(self) -> Token:
        if self._pos < len(self._tokens):
            return self._tokens[self._pos]
        return self._tokens[-1]

    def _peek(self, offset: int = 1) -> Token | None:
        idx = self._pos + offset
        if idx < len(self._tokens):
            return self._tokens[idx]
        return None

    def _advance(self) -> Token:
        tok = self._current()
        if self._pos < len(self._tokens) - 1:
            self._pos += 1
        return tok

    def _at_end(self) -> bool:
        return self._current().type == TokenType.EOF

    def _expect(self, tt: TokenType) -> Token:
        tok = self._current()
        if tok.type != tt:
            raise ParseError(f"Expected {tt.name}, got {tok.type.name} ({tok.value!r})", tok)
        self._advance()
        return tok

    def _is_infix_op(self) -> bool:
        """Check if current token is an infix operator."""
        tok = self._current()
        if tok.type == TokenType.ATOM and tok.value in INFIX_OPS:
            return True
        return False

    def _parse_clause(self) -> Clause:
        head = self._parse_term()
        # Wrap bare atoms/numbers into compound terms for clause heads
        if isinstance(head, Atom):
            head = Compound(head.name, ())
        elif isinstance(head, Number):
            raise ParseError("Clause head cannot be a number")
        elif isinstance(head, Variable):
            raise ParseError("Clause head cannot be a variable")

        if not isinstance(head, Compound):
            raise ParseError(f"Clause head must be a compound term, got {type(head).__name__}")

        if self._current().type == TokenType.NECK:
            self._advance()  # :-
            body = self._parse_body()
            return Clause(head, body)
        else:
            return Clause(head)  # fact

    def _parse_body(self) -> list:
        goals = [self._parse_goal()]
        while self._current().type == TokenType.COMMA:
            self._advance()
            goals.append(self._parse_goal())
        return goals

    def _parse_goal(self) -> Term:
        """Parse a goal, which is a term possibly with infix operators."""
        return self._parse_infix(700)

    def _parse_infix(self, max_prec: int) -> Term:
        """Parse a term with possible infix operators (precedence climbing)."""
        left = self._parse_primary()

        while self._is_infix_op():
            op_name = self._current().value
            op_prec, op_assoc = INFIX_OPS[op_name]
            if op_prec > max_prec:
                break
            self._advance()  # consume operator

            # For xfx: right operand must have strictly lower precedence
            # For yfx: right operand can have same or lower precedence
            if op_assoc == "xfx":
                right = self._parse_infix(op_prec - 1)
            elif op_assoc == "yfx":
                right = self._parse_infix(op_prec)
            else:
                right = self._parse_infix(op_prec - 1)

            left = Compound(op_name, (left, right))

        return left

    def _parse_term(self) -> Term:
        """Parse a term (for clause heads, arguments, etc.)."""
        return self._parse_infix(700)

    def _parse_primary(self) -> Term:
        """Parse a primary term (atom, variable, number, compound, list, parens)."""
        tok = self._current()

        if tok.type == TokenType.NUMBER:
            self._advance()
            val = float(tok.value)
            return Number(val)

        if tok.type == TokenType.STRING:
            self._advance()
            return String(tok.value)

        if tok.type == TokenType.VARIABLE:
            self._advance()
            return Variable(tok.value)

        if tok.type == TokenType.ATOM:
            self._advance()
            # Check for compound term: atom(args...)
            if self._current().type == TokenType.LPAREN:
                self._advance()  # (
                args = self._parse_arglist()
                self._expect(TokenType.RPAREN)
                return Compound(tok.value, tuple(args))
            # Check for infix operator
            if tok.value in INFIX_OPS:
                # This is an infix operator used in prefix position? No, return as atom
                pass
            return Atom(tok.value)

        if tok.type == TokenType.LBRACKET:
            return self._parse_list()

        if tok.type == TokenType.LPAREN:
            self._advance()
            term = self._parse_term()
            self._expect(TokenType.RPAREN)
            return term

        raise ParseError(f"Unexpected token {tok.type.name} ({tok.value!r})", tok)

    def _parse_arglist(self) -> list[Term]:
        if self._current().type == TokenType.RPAREN:
            return []
        args = [self._parse_term()]
        while self._current().type == TokenType.COMMA:
            self._advance()
            args.append(self._parse_term())
        return args

    def _parse_list(self) -> Term:
        """Parse a list: [], [a, b], [a|B], [a, b|T]."""
        self._expect(TokenType.LBRACKET)
        if self._current().type == TokenType.RBRACKET:
            self._advance()
            return Atom("[]")

        elements = [self._parse_term()]
        while self._current().type == TokenType.COMMA:
            self._advance()
            elements.append(self._parse_term())

        tail: Term = Atom("[]")
        if self._current().type == TokenType.PIPE:
            self._advance()
            tail = self._parse_term()

        self._expect(TokenType.RBRACKET)

        # Build the list from right to left using '.'/2
        result = tail
        for elem in reversed(elements):
            result = Compound(".", (elem, result))
        return result