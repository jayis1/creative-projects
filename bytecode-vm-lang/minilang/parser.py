"""MiniLang parser — a recursive-descent / Pratt-parser hybrid.

Grammar (informal)::

    program     := stmt* EOF
    stmt        := var_decl | func_decl | if_stmt | while_stmt
                 | for_stmt | return_stmt | break_stmt | continue_stmt
                 | expr_stmt | block
    var_decl    := ('let' | 'const') IDENT [':' type] '=' expr ';'
    func_decl   := 'fn' IDENT '(' params ')' '-' '>' type block
    params      := (IDENT ':' type (',' IDENT ':' type)*)?
    if_stmt     := 'if' expr block ('else' (block | if_stmt))?
    while_stmt  := 'while' expr block
    for_stmt    := 'for' IDENT 'in' expr '..' expr block
    return_stmt := 'return' expr? ';'
    expr_stmt   := expr ';'
    block       := '{' stmt* '}'

    expr        := assignment
    assignment   := logic_or ( ('=' | comp: no) ) ...
    logic_or    := logic_and ('||' logic_and)*
    logic_and   := equality ('&&' equality)*
    equality    := comparison (('==' | '!=') comparison)*
    comparison  := addition (('<' | '<=' | '>' | '>=') addition)*
    addition    := mult (('+' | '-') mult)*
    mult        := unary (('*' | '/' | '%') unary)*
    unary       := ('!' | '-') unary | postfix
    postfix     := primary ( '(' args ')' | '[' expr ']' )*
    primary     := INT | STRING | 'true' | 'false' | 'nil'
                 | IDENT | '(' expr ')' | '[' elements ']'
    type        := 'int' | 'string' | 'bool' | 'unit'
                 | 'array' '<' type '>' | 'fn' '(' types? ')' '-' '>' type
"""

from __future__ import annotations

from .ast import (
    ArrayLit, ArrayType, Assign, BinOp, Block, BoolLit, BoolType, BreakStmt,
    CallExpr, ContinueStmt, Expr, ExprStmt, ForStmt, FuncDecl, FuncType,
    Ident, IfStmt, IndexAssign, IndexExpr, IntLit, IntType, NilLit, Program,
    ReturnStmt, Stmt, StringLit, StringType, TypeNode, UnaryOp, UnitType,
    VarDecl, WhileStmt,
)
from .errors import ParseError
from .lexer import KEYWORDS, Token, TokenKind, tokenize


class Parser:
    """Recursive-descent / Pratt parser producing a :class:`Program` AST."""

    def __init__(self, tokens: list[Token], name: str = "<string>"):
        self._tokens = tokens
        self._pos = 0
        self._name = name

    # ------------------------------------------------------------------ #
    # public entry point                                                 #
    # ------------------------------------------------------------------ #
    def parse_program(self) -> Program:
        stmts: list[Stmt] = []
        while not self._check(TokenKind.EOF):
            stmts.append(self._declaration())
        return Program(tuple(stmts))

    # ------------------------------------------------------------------ #
    # statement-level productions                                        #
    # ------------------------------------------------------------------ #
    def _declaration(self) -> Stmt:
        if self._check(TokenKind.FN):
            return self._func_decl()
        if self._check(TokenKind.LET) or self._check(TokenKind.CONST):
            return self._var_decl()
        return self._statement()

    def _func_decl(self) -> FuncDecl:
        tok = self._advance()  # 'fn'
        name = self._consume(TokenKind.IDENT, "expected function name")
        self._consume(TokenKind.LPAREN, "expected '(' after function name")
        params: list[tuple[str, TypeNode]] = []
        while not self._check(TokenKind.RPAREN):
            pname = self._consume(TokenKind.IDENT, "expected parameter name")
            self._consume(TokenKind.COLON, "expected ':' after parameter name")
            ptype = self._type()
            params.append((pname.lexeme, ptype))
            if not self._match(TokenKind.COMMA):
                break
        self._consume(TokenKind.RPAREN, "expected ')' after parameters")
        self._consume(TokenKind.ARROW, "expected '->' before return type")
        ret = self._type()
        body = self._block()
        return FuncDecl(name.lexeme, tuple(params), ret, body,
                        tok.line, tok.col)

    def _var_decl(self) -> VarDecl:
        kw = self._advance()  # 'let' or 'const'
        name = self._consume(TokenKind.IDENT, "expected variable name")
        type_annot: TypeNode | None = None
        if self._match(TokenKind.COLON):
            type_annot = self._type()
        self._consume(TokenKind.EQ, "expected '=' in variable declaration")
        value = self._expression()
        self._consume(TokenKind.SEMI, "expected ';' after variable declaration")
        return VarDecl(name.lexeme, type_annot, value, kw.kind == TokenKind.CONST,
                       kw.line, kw.col)

    def _statement(self) -> Stmt:
        if self._check(TokenKind.IF):
            return self._if_stmt()
        if self._check(TokenKind.WHILE):
            return self._while_stmt()
        if self._check(TokenKind.FOR):
            return self._for_stmt()
        if self._check(TokenKind.RETURN):
            return self._return_stmt()
        if self._check(TokenKind.BREAK):
            t = self._advance()
            self._consume(TokenKind.SEMI, "expected ';' after 'break'")
            return BreakStmt(t.line, t.col)
        if self._check(TokenKind.CONTINUE):
            t = self._advance()
            self._consume(TokenKind.SEMI, "expected ';' after 'continue'")
            return ContinueStmt(t.line, t.col)
        if self._check(TokenKind.LBRACE):
            return self._block()
        # expression statement
        expr = self._expression()
        self._consume(TokenKind.SEMI, "expected ';' after expression")
        return ExprStmt(expr)

    def _if_stmt(self) -> IfStmt:
        tok = self._advance()  # 'if' or 'elif'
        cond = self._expression()
        then_branch = self._block()
        else_branch: Block | None = None
        if self._match(TokenKind.ELSE):
            if self._check(TokenKind.IF):
                # else if → wrap nested if in a block
                nested = self._if_stmt()
                else_branch = Block((nested,), tok.line, tok.col)
            elif self._check(TokenKind.ELIF):
                # elif chain → parse as nested if in a block
                nested = self._if_stmt()
                else_branch = Block((nested,), tok.line, tok.col)
            else:
                else_branch = self._block()
        elif self._check(TokenKind.ELIF):
            # elif without else: parse elif chain as else branch
            nested = self._if_stmt()
            else_branch = Block((nested,), tok.line, tok.col)
        return IfStmt(cond, then_branch, else_branch, tok.line, tok.col)

    def _while_stmt(self) -> WhileStmt:
        tok = self._advance()  # 'while'
        cond = self._expression()
        body = self._block()
        return WhileStmt(cond, body, tok.line, tok.col)

    def _for_stmt(self) -> ForStmt:
        tok = self._advance()  # 'for'
        var = self._consume(TokenKind.IDENT, "expected loop variable")
        self._consume(TokenKind.IN, "expected 'in' after for-loop variable")
        start = self._expression()
        self._consume(TokenKind.DOT, "expected '..' in for-loop range")
        self._consume(TokenKind.DOT, "expected '..' in for-loop range")
        end = self._expression()
        body = self._block()
        return ForStmt(var.lexeme, start, end, body, tok.line, tok.col)

    def _return_stmt(self) -> ReturnStmt:
        tok = self._advance()  # 'return'
        value: Expr | None = None
        if not self._check(TokenKind.SEMI):
            value = self._expression()
        self._consume(TokenKind.SEMI, "expected ';' after return")
        return ReturnStmt(value, tok.line, tok.col)

    def _block(self) -> Block:
        lb = self._consume(TokenKind.LBRACE, "expected '{'")
        stmts: list[Stmt] = []
        while not self._check(TokenKind.RBRACE) and not self._check(TokenKind.EOF):
            stmts.append(self._declaration())
        self._consume(TokenKind.RBRACE, "expected '}'")
        return Block(tuple(stmts), lb.line, lb.col)

    # ------------------------------------------------------------------ #
    # type productions                                                    #
    # ------------------------------------------------------------------ #
    def _type(self) -> TypeNode:
        if self._match(TokenKind.IDENT):
            name = self._previous().lexeme
            mapping: dict[str, TypeNode] = {
                "int": IntType(),
                "string": StringType(),
                "bool": BoolType(),
                "unit": UnitType(),
            }
            if name in mapping:
                return mapping[name]
            if name == "array":
                self._consume(TokenKind.LT, "expected '<' after 'array'")
                elem = self._type()
                self._consume(TokenKind.GT, "expected '>' after array type")
                return ArrayType(elem)
            if name == "fn":
                self._consume(TokenKind.LPAREN, "expected '(' after 'fn'")
                pts: list[TypeNode] = []
                while not self._check(TokenKind.RPAREN):
                    pts.append(self._type())
                    if not self._match(TokenKind.COMMA):
                        break
                self._consume(TokenKind.RPAREN, "expected ')' after fn params")
                self._consume(TokenKind.ARROW, "expected '->' in fn type")
                ret = self._type()
                return FuncType(tuple(pts), ret)
            raise ParseError(f"unknown type {name!r}", self._previous().line,
                             self._previous().col, self._name)
        raise ParseError("expected a type", self._peek().line, self._peek().col,
                         self._name)

    # ------------------------------------------------------------------ #
    # expression productions (Pratt-style precedence)                     #
    # ------------------------------------------------------------------ #
    def _expression(self) -> Expr:
        return self._assignment()

    def _assignment(self) -> Expr:
        expr = self._logic_or()
        if self._match(TokenKind.EQ):
            eq_tok = self._previous()
            rhs = self._assignment()  # right-associative
            if isinstance(expr, Ident):
                return Assign(expr.name, rhs, eq_tok.line, eq_tok.col)
            if isinstance(expr, IndexExpr):
                return IndexAssign(expr.array, expr.index, rhs,
                                   eq_tok.line, eq_tok.col)
            raise ParseError("invalid assignment target", eq_tok.line,
                             eq_tok.col, self._name)
        return expr

    def _logic_or(self) -> Expr:
        expr = self._logic_and()
        while self._match(TokenKind.PIPE_PIPE, TokenKind.OR):
            op_tok = self._previous()
            rhs = self._logic_and()
            expr = BinOp("||", expr, rhs, op_tok.line, op_tok.col)
        return expr

    def _logic_and(self) -> Expr:
        expr = self._equality()
        while self._match(TokenKind.AMP_AMP, TokenKind.AND):
            op_tok = self._previous()
            rhs = self._equality()
            expr = BinOp("&&", expr, rhs, op_tok.line, op_tok.col)
        return expr

    def _equality(self) -> Expr:
        expr = self._comparison()
        while self._match(TokenKind.EQEQ, TokenKind.NEQ):
            op_tok = self._previous()
            rhs = self._comparison()
            op = "==" if op_tok.kind == TokenKind.EQEQ else "!="
            expr = BinOp(op, expr, rhs, op_tok.line, op_tok.col)
        return expr

    def _comparison(self) -> Expr:
        expr = self._addition()
        while self._match(TokenKind.LT, TokenKind.LE, TokenKind.GT, TokenKind.GE):
            op_tok = self._previous()
            op_map = {TokenKind.LT: "<", TokenKind.LE: "<=",
                      TokenKind.GT: ">", TokenKind.GE: ">="}
            rhs = self._addition()
            expr = BinOp(op_map[op_tok.kind], expr, rhs, op_tok.line, op_tok.col)
        return expr

    def _addition(self) -> Expr:
        expr = self._multiplication()
        while self._match(TokenKind.PLUS, TokenKind.MINUS):
            op_tok = self._previous()
            rhs = self._multiplication()
            op = "+" if op_tok.kind == TokenKind.PLUS else "-"
            expr = BinOp(op, expr, rhs, op_tok.line, op_tok.col)
        return expr

    def _multiplication(self) -> Expr:
        expr = self._unary()
        while self._match(TokenKind.STAR, TokenKind.SLASH, TokenKind.PERCENT):
            op_tok = self._previous()
            rhs = self._unary()
            op_map = {TokenKind.STAR: "*", TokenKind.SLASH: "/",
                      TokenKind.PERCENT: "%"}
            expr = BinOp(op_map[op_tok.kind], expr, rhs, op_tok.line, op_tok.col)
        return expr

    def _unary(self) -> Expr:
        if self._match(TokenKind.BANG, TokenKind.MINUS):
            op_tok = self._previous()
            operand = self._unary()
            op = "!" if op_tok.kind == TokenKind.BANG else "-"
            return UnaryOp(op, operand, op_tok.line, op_tok.col)
        return self._postfix()

    def _postfix(self) -> Expr:
        expr = self._primary()
        while True:
            if self._match(TokenKind.LPAREN):
                lp = self._previous()
                args: list[Expr] = []
                while not self._check(TokenKind.RPAREN):
                    args.append(self._expression())
                    if not self._match(TokenKind.COMMA):
                        break
                self._consume(TokenKind.RPAREN, "expected ')' after arguments")
                expr = CallExpr(expr, tuple(args), lp.line, lp.col)
            elif self._match(TokenKind.LBRACKET):
                lb = self._previous()
                index = self._expression()
                self._consume(TokenKind.RBRACKET, "expected ']'")
                expr = IndexExpr(expr, index, lb.line, lb.col)
            else:
                break
        return expr

    def _primary(self) -> Expr:
        tok = self._peek()
        if self._match(TokenKind.INT):
            return IntLit(int(tok.lexeme), tok.line, tok.col)
        if self._match(TokenKind.STRING):
            return StringLit(tok.lexeme, tok.line, tok.col)
        if self._match(TokenKind.TRUE):
            return BoolLit(True, tok.line, tok.col)
        if self._match(TokenKind.FALSE):
            return BoolLit(False, tok.line, tok.col)
        if self._match(TokenKind.NIL):
            return NilLit(tok.line, tok.col)
        if self._match(TokenKind.IDENT):
            return Ident(tok.lexeme, tok.line, tok.col)
        if self._match(TokenKind.LPAREN):
            expr = self._expression()
            self._consume(TokenKind.RPAREN, "expected ')'")
            return expr
        if self._match(TokenKind.LBRACKET):
            elements: list[Expr] = []
            while not self._check(TokenKind.RBRACKET):
                elements.append(self._expression())
                if not self._match(TokenKind.COMMA):
                    break
            self._consume(TokenKind.RBRACKET, "expected ']'")
            return ArrayLit(tuple(elements), tok.line, tok.col)
        raise ParseError(f"unexpected token {tok.kind.name}", tok.line, tok.col,
                         self._name)

    # ------------------------------------------------------------------ #
    # cursor helpers                                                      #
    # ------------------------------------------------------------------ #
    def _check(self, kind: TokenKind) -> bool:
        return self._peek().kind == kind

    def _peek(self) -> Token:
        return self._tokens[self._pos]

    def _previous(self) -> Token:
        return self._tokens[self._pos - 1]

    def _advance(self) -> Token:
        if not self._check(TokenKind.EOF):
            self._pos += 1
        return self._tokens[self._pos - 1]

    def _match(self, *kinds: TokenKind) -> bool:
        for k in kinds:
            if self._check(k):
                self._advance()
                return True
        return False

    def _consume(self, kind: TokenKind, message: str) -> Token:
        if self._check(kind):
            return self._advance()
        tok = self._peek()
        raise ParseError(message, tok.line, tok.col, self._name)


def parse(source: str, name: str = "<string>") -> Program:
    """Lex + parse *source* into a :class:`Program` AST."""
    tokens = tokenize(source, name)
    return Parser(tokens, name).parse_program()