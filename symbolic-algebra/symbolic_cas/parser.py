"""Expression parser: parse infix math expression strings into AST nodes."""

from __future__ import annotations

from typing import List

from symbolic_cas.expr import Expr, Num, Sym, BinOp, UnaryOp, Func, Pow


# Token types
_TOK_NUM = 'NUM'
_TOK_SYM = 'SYM'
_TOK_OP = 'OP'
_TOK_LPAREN = 'LPAREN'
_TOK_RPAREN = 'RPAREN'
_TOK_COMMA = 'COMMA'
_TOK_CARET = 'CARET'
_TOK_EOF = 'EOF'


class _Token:
    def __init__(self, typ: str, value: str):
        self.typ = typ
        self.value = value

    def __repr__(self):
        return f"Token({self.typ}, {self.value!r})"


def _tokenize(expr_str: str) -> List[_Token]:
    """Tokenize an expression string."""
    tokens = []
    i = 0
    while i < len(expr_str):
        ch = expr_str[i]
        if ch.isspace():
            i += 1
            continue
        if ch in '+-':
            tokens.append(_Token(_TOK_OP, ch))
            i += 1
        elif ch in '*/':
            tokens.append(_Token(_TOK_OP, ch))
            i += 1
        elif ch == '^':
            tokens.append(_Token(_TOK_CARET, '^'))
            i += 1
        elif ch == '(':
            tokens.append(_Token(_TOK_LPAREN, '('))
            i += 1
        elif ch == ')':
            tokens.append(_Token(_TOK_RPAREN, ')'))
            i += 1
        elif ch == ',':
            tokens.append(_Token(_TOK_COMMA, ','))
            i += 1
        elif ch.isdigit() or ch == '.':
            j = i
            has_dot = False
            while j < len(expr_str) and (expr_str[j].isdigit() or (expr_str[j] == '.' and not has_dot)):
                if expr_str[j] == '.':
                    has_dot = True
                j += 1
            tokens.append(_Token(_TOK_NUM, expr_str[i:j]))
            i = j
        elif ch.isalpha() or ch == '_':
            j = i
            while j < len(expr_str) and (expr_str[j].isalnum() or expr_str[j] == '_'):
                j += 1
            name = expr_str[i:j]
            tokens.append(_Token(_TOK_SYM, name))
            i = j
        else:
            raise ValueError(f"Unexpected character: {ch!r} at position {i}")

    tokens.append(_Token(_TOK_EOF, ''))
    return tokens


class _Parser:
    """Recursive descent parser with proper operator precedence."""

    def __init__(self, tokens: List[_Token]):
        self.tokens = tokens
        self.pos = 0

    def peek(self) -> _Token:
        return self.tokens[self.pos]

    def advance(self) -> _Token:
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def expect(self, typ: str) -> _Token:
        tok = self.advance()
        if tok.typ != typ:
            raise ValueError(f"Expected {typ}, got {tok.typ} ({tok.value!r})")
        return tok

    def parse(self) -> Expr:
        result = self.parse_expr()
        if self.peek().typ != _TOK_EOF:
            raise ValueError(f"Unexpected token after expression: {self.peek()}")
        return result

    def parse_expr(self) -> Expr:
        return self.parse_additive()

    def parse_additive(self) -> Expr:
        left = self.parse_multiplicative()
        while self.peek().typ == _TOK_OP and self.peek().value in ('+', '-'):
            op = self.advance().value
            right = self.parse_multiplicative()
            left = BinOp(op, left, right)
        return left

    def parse_multiplicative(self) -> Expr:
        left = self.parse_unary()
        while self.peek().typ == _TOK_OP and self.peek().value in ('*', '/'):
            op = self.advance().value
            right = self.parse_unary()
            left = BinOp(op, left, right)
        return left

    def parse_unary(self) -> Expr:
        if self.peek().typ == _TOK_OP and self.peek().value == '-':
            self.advance()
            operand = self.parse_unary()
            return UnaryOp('-', operand)
        if self.peek().typ == _TOK_OP and self.peek().value == '+':
            self.advance()
            return self.parse_unary()
        return self.parse_power()

    def parse_power(self) -> Expr:
        base = self.parse_atom()
        if self.peek().typ == _TOK_CARET:
            self.advance()
            exp = self.parse_unary()  # right-associative
            return Pow(base, exp)
        return base

    def parse_atom(self) -> Expr:
        tok = self.peek()

        if tok.typ == _TOK_NUM:
            self.advance()
            val = float(tok.value)
            if val == int(val) and '.' not in tok.value:
                val = int(val)
            return Num(val)

        if tok.typ == _TOK_SYM:
            name = tok.value
            self.advance()
            # Check if it's a function call
            if self.peek().typ == _TOK_LPAREN and name in Func.KNOWN_FUNCS:
                self.advance()  # consume '('
                arg = self.parse_expr()
                self.expect(_TOK_RPAREN)
                return Func(name, arg)
            return Sym(name)

        if tok.typ == _TOK_LPAREN:
            self.advance()
            expr = self.parse_expr()
            self.expect(_TOK_RPAREN)
            return expr

        raise ValueError(f"Unexpected token: {tok}")


def parse(expr_str: str) -> Expr:
    """Parse a mathematical expression string into an Expr AST."""
    tokens = _tokenize(expr_str)
    parser = _Parser(tokens)
    return parser.parse()