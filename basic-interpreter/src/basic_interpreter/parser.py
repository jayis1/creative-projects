"""Parser for the BASIC interpreter.

Implements a recursive-descent parser that converts a token stream
into an abstract syntax tree (AST) of BASIC statements and expressions.
"""

from __future__ import annotations

from typing import Any, List, Optional

from basic_interpreter.lexer import Token, TokenType, KEYWORDS
from basic_interpreter.ast_nodes import (
    NumberLit, StringLit, VarRef, ArrayRef, FnCall, UnaryOp, BinOp,
    LetStmt, PrintStmt, InputStmt, LineInputStmt, IfStmt, ForStmt,
    NextStmt, WhileStmt, WendStmt, DoStmt, LoopStmt, GotoStmt,
    GosubStmt, ReturnStmt, DimStmt, EraseStmt, ReadStmt, DataStmt,
    RestoreStmt, DefFnStmt, EndStmt, StopStmt, RemStmt, OnGotoStmt,
    OnGosubStmt, SwapStmt, ClsStmt, ColorStmt, LocateStmt, BeepStmt,
    SelectCaseStmt, CaseStmt, CaseElseStmt, EndSelectStmt,
    CaseCondition, OpenStmt, CloseStmt, PrintFileStmt, InputFileStmt,
    OnErrorStmt, ResumeStmt, ExitDoStmt,
)
from basic_interpreter.errors import BasicSyntaxError


class Parser:
    """Recursive-descent parser for BASIC.

    Takes a list of Token objects produced by the Lexer and produces
    statement AST nodes through recursive-descent parsing with
    precedence climbing for expressions.
    """

    def __init__(self, tokens: List[Token]) -> None:
        self.tokens = tokens
        self.pos = 0

    def _peek(self) -> Token:
        """Look at the current token without consuming it."""
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return Token(TokenType.EOF, None)

    def _advance(self) -> Token:
        """Consume and return the current token."""
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def _expect(self, tt: TokenType) -> Token:
        """Consume a token of the expected type, raising an error if it doesn't match."""
        tok = self._advance()
        if tok.type != tt:
            raise BasicSyntaxError(f"Expected {tt.name}, got {tok.type.name} ({tok.value!r})")
        return tok

    def _match(self, *types: TokenType) -> Optional[Token]:
        """If the current token matches one of the given types, consume and return it."""
        if self._peek().type in types:
            return self._advance()
        return None

    def _parse_stmts(self) -> list:
        """Parse multiple colon-separated statements."""
        stmts = [self._parse_stmt()]
        while self._match(TokenType.COLON):
            if self._peek().type == TokenType.EOF:
                break
            stmts.append(self._parse_stmt())
        return stmts

    def _parse_stmt(self) -> Any:
        """Parse a single statement based on the current token."""
        tok = self._peek()

        if tok.type == TokenType.LET:
            return self._parse_let()
        if tok.type == TokenType.PRINT:
            return self._parse_print()
        if tok.type == TokenType.INPUT:
            return self._parse_input()
        if tok.type == TokenType.LINE:
            return self._parse_line_input()
        if tok.type == TokenType.IF:
            return self._parse_if()
        if tok.type == TokenType.FOR:
            return self._parse_for()
        if tok.type == TokenType.NEXT:
            return self._parse_next()
        if tok.type == TokenType.WHILE:
            return self._parse_while()
        if tok.type == TokenType.WEND:
            self._advance()
            return WendStmt()
        if tok.type == TokenType.DO:
            return self._parse_do()
        if tok.type == TokenType.LOOP:
            return self._parse_loop()
        if tok.type == TokenType.GOTO:
            return self._parse_goto()
        if tok.type == TokenType.GOSUB:
            return self._parse_gosub()
        if tok.type == TokenType.RETURN:
            self._advance()
            return ReturnStmt()
        if tok.type == TokenType.DIM:
            return self._parse_dim()
        if tok.type == TokenType.ERASE:
            return self._parse_erase()
        if tok.type == TokenType.READ:
            return self._parse_read()
        if tok.type == TokenType.DATA:
            return self._parse_data()
        if tok.type == TokenType.RESTORE:
            return self._parse_restore()
        if tok.type == TokenType.DEF:
            return self._parse_def_fn()
        if tok.type == TokenType.END:
            self._advance()
            if self._peek().type == TokenType.SELECT:
                self._advance()
                return EndSelectStmt()
            if self._peek().type == TokenType.IF:
                self._advance()
                return RemStmt("END IF")
            return EndStmt()
        if tok.type == TokenType.STOP:
            self._advance()
            return StopStmt()
        if tok.type == TokenType.ON:
            return self._parse_on()
        if tok.type == TokenType.SWAP:
            return self._parse_swap()
        if tok.type == TokenType.CLS:
            self._advance()
            return ClsStmt()
        if tok.type == TokenType.COLOR:
            return self._parse_color()
        if tok.type == TokenType.LOCATE:
            return self._parse_locate()
        if tok.type == TokenType.BEEP:
            self._advance()
            return BeepStmt()
        if tok.type == TokenType.REM:
            self._advance()
            return RemStmt(tok.value or "")
        if tok.type == TokenType.SELECT:
            return self._parse_select_case()
        if tok.type == TokenType.CASE:
            return self._parse_case()
        if tok.type == TokenType.OPEN:
            return self._parse_open()
        if tok.type == TokenType.CLOSE:
            return self._parse_close()
        if tok.type == TokenType.ERROR:
            return self._parse_error_stmt()
        if tok.type == TokenType.RESUME:
            return self._parse_resume()
        if tok.type == TokenType.EXIT:
            self._advance()
            if self._peek().type == TokenType.DO:
                self._advance()
                return ExitDoStmt()
            raise BasicSyntaxError("EXIT without DO")

        # Implicit LET (assignment without LET keyword)
        if tok.type == TokenType.IDENT:
            next_pos = self.pos + 1
            while next_pos < len(self.tokens) and self.tokens[next_pos].type in (TokenType.LPAREN,):
                depth = 0
                while next_pos < len(self.tokens):
                    if self.tokens[next_pos].type == TokenType.LPAREN:
                        depth += 1
                    elif self.tokens[next_pos].type == TokenType.RPAREN:
                        depth -= 1
                        if depth == 0:
                            next_pos += 1
                            break
                    next_pos += 1
            if next_pos < len(self.tokens) and self.tokens[next_pos].type == TokenType.EQ:
                return self._parse_let(implicit=True)

        # Hash followed by number = file reference (PRINT# shorthand)
        if tok.type == TokenType.HASH:
            return self._parse_file_print()

        expr = self._parse_expr()
        return expr

    def _parse_let(self, implicit: bool = False) -> LetStmt:
        """Parse LET assignment (explicit or implicit)."""
        if not implicit:
            self._expect(TokenType.LET)
        target = self._parse_lvalue()
        self._expect(TokenType.EQ)
        value = self._parse_expr()
        return LetStmt(target, value)

    def _parse_lvalue(self):
        """Parse an lvalue (variable or array element for assignment)."""
        name_tok = self._expect(TokenType.IDENT)
        name = self._normalize_var(name_tok.value)
        if self._peek().type == TokenType.LPAREN:
            self._advance()
            indices = [self._parse_expr()]
            while self._match(TokenType.COMMA):
                indices.append(self._parse_expr())
            self._expect(TokenType.RPAREN)
            return ArrayRef(name, indices)
        return VarRef(name)

    def _parse_print(self):
        """Parse PRINT [USING] statement."""
        self._expect(TokenType.PRINT)
        using = None
        if self._peek().type == TokenType.USING:
            self._advance()
            using = self._parse_expr()
            if self._match(TokenType.SEMI):
                pass
        if self._peek().type == TokenType.HASH:
            self._advance()
            file_num = self._parse_expr()
            if self._match(TokenType.COMMA):
                pass
            items = self._parse_print_items()
            return PrintFileStmt(file_num, items)
        items = self._parse_print_items()
        return PrintStmt(items, using)

    def _parse_print_items(self) -> list:
        """Parse the items list in a PRINT statement."""
        items: list = []
        if self._peek().type in (TokenType.EOF, TokenType.COLON):
            return [(None, None)]

        while True:
            if self._peek().type in (TokenType.SEMI, TokenType.COMMA):
                sep = self._advance()
                items.append((None, sep.value))
                if self._peek().type in (TokenType.EOF, TokenType.COLON):
                    break
                continue

            expr = self._parse_expr()
            sep_tok = self._match(TokenType.SEMI, TokenType.COMMA)
            if sep_tok:
                items.append((expr, sep_tok.value))
                if self._peek().type in (TokenType.EOF, TokenType.COLON):
                    break
            else:
                items.append((expr, None))
                break
        return items

    def _parse_input(self):
        """Parse INPUT statement."""
        self._expect(TokenType.INPUT)
        if self._peek().type == TokenType.HASH:
            self._advance()
            file_num = self._parse_expr()
            self._match(TokenType.COMMA)
            vars_ = [self._parse_lvalue()]
            while self._match(TokenType.COMMA):
                vars_.append(self._parse_lvalue())
            return InputFileStmt(file_num, vars_)

        prompt = None
        if self._peek().type == TokenType.STRING:
            prompt = StringLit(self._advance().value)
            if self._match(TokenType.SEMI):
                pass
            elif self._match(TokenType.COMMA):
                pass
        vars_: list = []
        vars_.append(self._parse_lvalue())
        while self._match(TokenType.COMMA):
            vars_.append(self._parse_lvalue())
        return InputStmt(prompt, vars_)

    def _parse_line_input(self):
        """Parse LINE INPUT statement."""
        self._expect(TokenType.LINE)
        self._expect(TokenType.INPUT)
        file_num = None
        if self._peek().type == TokenType.HASH:
            self._advance()
            file_num = self._parse_expr()
            self._match(TokenType.COMMA)
        prompt = None
        if self._peek().type == TokenType.STRING:
            prompt = StringLit(self._advance().value)
            self._match(TokenType.SEMI)
        var = self._parse_lvalue()
        return LineInputStmt(prompt, var, file_num)

    def _parse_if(self):
        """Parse IF...THEN...ELSE statement."""
        self._expect(TokenType.IF)
        condition = self._parse_expr()
        self._expect(TokenType.THEN)
        if self._peek().type == TokenType.NUMBER:
            line_num = int(self._advance().value)
            then_part: list = [GotoStmt(line_num)]
        else:
            then_part = self._parse_stmts()
        else_part: list = []
        if self._peek().type == TokenType.ELSE:
            self._advance()
            if self._peek().type == TokenType.NUMBER:
                line_num = int(self._advance().value)
                else_part = [GotoStmt(line_num)]
            else:
                else_part = self._parse_stmts()
        return IfStmt(condition, then_part, else_part)

    def _parse_for(self):
        """Parse FOR...NEXT loop initialization."""
        self._expect(TokenType.FOR)
        var_tok = self._expect(TokenType.IDENT)
        var = VarRef(self._normalize_var(var_tok.value))
        self._expect(TokenType.EQ)
        start = self._parse_expr()
        self._expect(TokenType.TO)
        stop = self._parse_expr()
        step = None
        if self._match(TokenType.STEP):
            step = self._parse_expr()
        return ForStmt(var, start, stop, step)

    def _parse_next(self):
        """Parse NEXT statement."""
        self._expect(TokenType.NEXT)
        var = None
        if self._peek().type == TokenType.IDENT:
            var = VarRef(self._normalize_var(self._advance().value))
        return NextStmt(var)

    def _parse_while(self):
        """Parse WHILE statement."""
        self._expect(TokenType.WHILE)
        condition = self._parse_expr()
        return WhileStmt(condition, [])

    def _parse_do(self):
        """Parse DO [WHILE|UNTIL] statement."""
        self._expect(TokenType.DO)
        pre_condition = None
        pre_until = False
        if self._match(TokenType.WHILE):
            pre_condition = self._parse_expr()
        elif self._match(TokenType.UNTIL):
            pre_condition = self._parse_expr()
            pre_until = True
        return DoStmt(pre_condition, pre_until)

    def _parse_loop(self):
        """Parse LOOP [WHILE|UNTIL] statement."""
        self._expect(TokenType.LOOP)
        post_condition = None
        post_until = False
        if self._match(TokenType.WHILE):
            post_condition = self._parse_expr()
        elif self._match(TokenType.UNTIL):
            post_condition = self._parse_expr()
            post_until = True
        return LoopStmt(post_condition, post_until)

    def _parse_goto(self):
        """Parse GOTO line_number statement."""
        self._expect(TokenType.GOTO)
        line = int(self._expect(TokenType.NUMBER).value)
        return GotoStmt(line)

    def _parse_gosub(self):
        """Parse GOSUB line_number statement."""
        self._expect(TokenType.GOSUB)
        line = int(self._expect(TokenType.NUMBER).value)
        return GosubStmt(line)

    def _parse_dim(self):
        """Parse DIM statement for array declarations."""
        self._expect(TokenType.DIM)
        decls: list = []
        name_tok = self._expect(TokenType.IDENT)
        self._expect(TokenType.LPAREN)
        dims = [int(self._expect(TokenType.NUMBER).value)]
        while self._match(TokenType.COMMA):
            dims.append(int(self._expect(TokenType.NUMBER).value))
        self._expect(TokenType.RPAREN)
        decls.append((self._normalize_var(name_tok.value), dims))
        while self._match(TokenType.COMMA):
            name_tok = self._expect(TokenType.IDENT)
            self._expect(TokenType.LPAREN)
            dims = [int(self._expect(TokenType.NUMBER).value)]
            while self._match(TokenType.COMMA):
                dims.append(int(self._expect(TokenType.NUMBER).value))
            self._expect(TokenType.RPAREN)
            decls.append((self._normalize_var(name_tok.value), dims))
        return DimStmt(decls)

    def _parse_erase(self):
        """Parse ERASE statement."""
        self._expect(TokenType.ERASE)
        names = [self._normalize_var(self._expect(TokenType.IDENT).value)]
        while self._match(TokenType.COMMA):
            names.append(self._normalize_var(self._expect(TokenType.IDENT).value))
        return EraseStmt(names)

    def _parse_read(self):
        """Parse READ statement."""
        self._expect(TokenType.READ)
        vars_ = [self._parse_lvalue()]
        while self._match(TokenType.COMMA):
            vars_.append(self._parse_lvalue())
        return ReadStmt(vars_)

    def _parse_data(self):
        """Parse DATA statement."""
        self._expect(TokenType.DATA)
        values = [self._parse_data_value()]
        while self._match(TokenType.COMMA):
            values.append(self._parse_data_value())
        return DataStmt(values)

    def _parse_data_value(self):
        """Parse a single value in a DATA statement."""
        tok = self._peek()
        if tok.type == TokenType.STRING:
            self._advance()
            return tok.value
        if tok.type == TokenType.MINUS:
            self._advance()
            n = self._expect(TokenType.NUMBER).value
            return -n
        if tok.type == TokenType.NUMBER:
            self._advance()
            return tok.value
        if tok.type == TokenType.IDENT:
            self._advance()
            return tok.value
        raise BasicSyntaxError(f"Unexpected token in DATA: {tok}")

    def _parse_restore(self):
        """Parse RESTORE [line] statement."""
        self._expect(TokenType.RESTORE)
        line_num = None
        if self._peek().type == TokenType.NUMBER:
            line_num = int(self._advance().value)
        return RestoreStmt(line_num)

    def _parse_def_fn(self):
        """Parse DEF FN statement for user-defined functions."""
        self._expect(TokenType.DEF)
        self._expect(TokenType.FN)
        name_tok = self._expect(TokenType.IDENT)
        name = name_tok.value.upper()
        params: list = []
        if self._match(TokenType.LPAREN):
            if self._peek().type != TokenType.RPAREN:
                params.append(self._normalize_var(self._expect(TokenType.IDENT).value))
                while self._match(TokenType.COMMA):
                    params.append(self._normalize_var(self._expect(TokenType.IDENT).value))
            self._expect(TokenType.RPAREN)
        self._expect(TokenType.EQ)
        body = self._parse_expr()
        return DefFnStmt(name, params, body)

    def _parse_on(self):
        """Parse ON...GOTO/GOSUB and ON ERROR GOTO statements."""
        self._expect(TokenType.ON)
        if self._peek().type == TokenType.ERROR:
            self._advance()
            self._expect(TokenType.GOTO)
            if self._peek().type == TokenType.NUMBER:
                line = int(self._advance().value)
                return OnErrorStmt(line)
            raise BasicSyntaxError("Expected line number after ON ERROR GOTO")
        expr = self._parse_expr()
        if self._match(TokenType.GOTO):
            targets = [int(self._expect(TokenType.NUMBER).value)]
            while self._match(TokenType.COMMA):
                targets.append(int(self._expect(TokenType.NUMBER).value))
            return OnGotoStmt(expr, targets)
        self._expect(TokenType.GOSUB)
        targets = [int(self._expect(TokenType.NUMBER).value)]
        while self._match(TokenType.COMMA):
            targets.append(int(self._expect(TokenType.NUMBER).value))
        return OnGosubStmt(expr, targets)

    def _parse_swap(self):
        """Parse SWAP var1, var2 statement."""
        self._expect(TokenType.SWAP)
        v1 = self._parse_lvalue()
        self._expect(TokenType.COMMA)
        v2 = self._parse_lvalue()
        return SwapStmt(v1, v2)

    def _parse_color(self):
        """Parse COLOR fg[, bg] statement."""
        self._expect(TokenType.COLOR)
        fg = self._parse_expr()
        bg = None
        if self._match(TokenType.COMMA):
            bg = self._parse_expr()
        return ColorStmt(fg, bg)

    def _parse_locate(self):
        """Parse LOCATE row, col statement."""
        self._expect(TokenType.LOCATE)
        row = self._parse_expr()
        col = None
        if self._match(TokenType.COMMA):
            col = self._parse_expr()
        return LocateStmt(row, col)

    def _parse_select_case(self):
        """Parse SELECT CASE expr statement."""
        self._expect(TokenType.SELECT)
        self._expect(TokenType.CASE)
        test_expr = self._parse_expr()
        return SelectCaseStmt(test_expr)

    def _parse_case(self):
        """Parse CASE conditions or CASE ELSE."""
        self._expect(TokenType.CASE)
        if self._peek().type == TokenType.ELSE:
            self._advance()
            return CaseElseStmt()
        conditions = [self._parse_case_condition()]
        while self._match(TokenType.COMMA):
            conditions.append(self._parse_case_condition())
        return CaseStmt(conditions)

    def _parse_case_condition(self) -> CaseCondition:
        """Parse a single CASE condition."""
        if self._peek().type == TokenType.IS:
            self._advance()
            comp_types = {TokenType.EQ: "=", TokenType.NE: "<>",
                          TokenType.LT: "<", TokenType.GT: ">",
                          TokenType.LE: "<=", TokenType.GE: ">="}
            if self._peek().type in comp_types:
                op = comp_types[self._peek().type]
                self._advance()
                val = self._parse_expr()
                return CaseCondition(is_op=op, is_val=val)
            raise BasicSyntaxError("Expected comparison after IS")

        expr1 = self._parse_expr()
        if self._match(TokenType.TO):
            expr2 = self._parse_expr()
            return CaseCondition(low=expr1, high=expr2)
        return CaseCondition(low=expr1)

    def _parse_open(self):
        """Parse OPEN statement for file I/O."""
        self._expect(TokenType.OPEN)
        filename = self._parse_expr()
        if self._peek().type == TokenType.FOR:
            self._advance()
            mode_tok = self._peek()
            if mode_tok.type == TokenType.IDENT:
                mode = self._advance().value.upper()
            elif mode_tok.type == TokenType.INPUT:
                mode = "INPUT"
                self._advance()
            else:
                raise BasicSyntaxError(f"Expected file mode after FOR, got {mode_tok}")
            if mode not in ("INPUT", "OUTPUT", "APPEND", "I", "O", "A"):
                raise BasicSyntaxError(f"Invalid file mode: {mode}")
            mode_map = {"INPUT": "I", "OUTPUT": "O", "APPEND": "A"}
            mode = mode_map.get(mode, mode)
            if self._peek().type == TokenType.IDENT and self._peek().value.upper() == "AS":
                self._advance()
            self._expect(TokenType.HASH)
            file_num = self._parse_expr()
            return OpenStmt(filename, mode, file_num)
        else:
            mode_expr = self._parse_expr()
            mode = str(self._eval_const(mode_expr)).upper() if isinstance(mode_expr, StringLit) else "I"
            self._expect(TokenType.COMMA)
            self._expect(TokenType.HASH)
            file_num = self._parse_expr()
            return OpenStmt(filename, mode, file_num)

    def _eval_const(self, expr):
        """Evaluate a constant expression at parse time."""
        if isinstance(expr, StringLit):
            return expr.value
        if isinstance(expr, NumberLit):
            return expr.value
        return None

    def _parse_close(self):
        """Parse CLOSE [#n] statement."""
        self._expect(TokenType.CLOSE)
        file_num = None
        if self._peek().type == TokenType.HASH:
            self._advance()
            file_num = self._parse_expr()
        elif self._peek().type == TokenType.NUMBER:
            file_num = self._parse_expr()
        return CloseStmt(file_num)

    def _parse_file_print(self):
        """Parse #n, items (PRINT# shorthand)."""
        self._expect(TokenType.HASH)
        file_num = self._parse_expr()
        if self._match(TokenType.COMMA):
            pass
        items = self._parse_print_items()
        return PrintFileStmt(file_num, items)

    def _parse_error_stmt(self):
        """Parse ERROR statement (standalone, not ON ERROR)."""
        self._expect(TokenType.ERROR)
        expr = self._parse_expr()
        return expr

    def _parse_resume(self):
        """Parse RESUME [line|NEXT] statement."""
        self._expect(TokenType.RESUME)
        line = None
        if self._peek().type == TokenType.NUMBER:
            line = int(self._advance().value)
        elif self._peek().type == TokenType.NEXT:
            self._advance()
            line = -1  # RESUME NEXT
        return ResumeStmt(line)

    # ── Expression parsing (precedence climbing) ──

    def _parse_expr(self) -> Any:
        """Parse an expression (lowest precedence: IMP)."""
        return self._parse_imp()

    def _parse_imp(self) -> Any:
        """Parse IMP (implication) operator."""
        left = self._parse_eqv()
        while self._peek().type == TokenType.IMP:
            self._advance()
            right = self._parse_eqv()
            left = BinOp("IMP", left, right)
        return left

    def _parse_eqv(self) -> Any:
        """Parse EQV (equivalence) operator."""
        left = self._parse_xor()
        while self._peek().type == TokenType.EQV:
            self._advance()
            right = self._parse_xor()
            left = BinOp("EQV", left, right)
        return left

    def _parse_xor(self) -> Any:
        """Parse XOR operator."""
        left = self._parse_or()
        while self._peek().type == TokenType.XOR:
            self._advance()
            right = self._parse_or()
            left = BinOp("XOR", left, right)
        return left

    def _parse_or(self) -> Any:
        """Parse OR operator."""
        left = self._parse_and()
        while self._peek().type == TokenType.OR:
            self._advance()
            right = self._parse_and()
            left = BinOp("OR", left, right)
        return left

    def _parse_and(self) -> Any:
        """Parse AND operator."""
        left = self._parse_not()
        while self._peek().type == TokenType.AND:
            self._advance()
            right = self._parse_not()
            left = BinOp("AND", left, right)
        return left

    def _parse_not(self) -> Any:
        """Parse NOT (unary logical negation)."""
        if self._peek().type == TokenType.NOT:
            self._advance()
            operand = self._parse_not()
            return UnaryOp("NOT", operand)
        return self._parse_comparison()

    def _parse_comparison(self) -> Any:
        """Parse comparison operators."""
        left = self._parse_add()
        comp_types = {TokenType.EQ: "=", TokenType.NE: "<>",
                      TokenType.LT: "<", TokenType.GT: ">",
                      TokenType.LE: "<=", TokenType.GE: ">="}
        if self._peek().type in comp_types:
            op = comp_types[self._peek().type]
            self._advance()
            right = self._parse_add()
            return BinOp(op, left, right)
        return left

    def _parse_add(self) -> Any:
        """Parse addition and subtraction."""
        left = self._parse_mul()
        while self._peek().type in (TokenType.PLUS, TokenType.MINUS):
            op = "+" if self._peek().type == TokenType.PLUS else "-"
            self._advance()
            right = self._parse_mul()
            left = BinOp(op, left, right)
        return left

    def _parse_mul(self) -> Any:
        """Parse multiplication and division."""
        left = self._parse_intdiv()
        while self._peek().type in (TokenType.STAR, TokenType.SLASH):
            op = "*" if self._peek().type == TokenType.STAR else "/"
            self._advance()
            right = self._parse_intdiv()
            left = BinOp(op, left, right)
        return left

    def _parse_intdiv(self) -> Any:
        """Parse integer division (\\)."""
        left = self._parse_mod()
        while self._peek().type == TokenType.BACKSLASH:
            self._advance()
            right = self._parse_mod()
            left = BinOp("\\", left, right)
        return left

    def _parse_mod(self) -> Any:
        """Parse MOD operator."""
        left = self._parse_power()
        while self._peek().type == TokenType.MOD:
            self._advance()
            right = self._parse_power()
            left = BinOp("MOD", left, right)
        return left

    def _parse_power(self) -> Any:
        """Parse exponentiation (^), right-associative."""
        base = self._parse_unary()
        if self._peek().type == TokenType.CARET:
            self._advance()
            exp = self._parse_power()
            return BinOp("^", base, exp)
        return base

    def _parse_unary(self) -> Any:
        """Parse unary minus and plus."""
        if self._peek().type == TokenType.MINUS:
            self._advance()
            operand = self._parse_unary()
            return UnaryOp("-", operand)
        if self._peek().type == TokenType.PLUS:
            self._advance()
            return self._parse_unary()
        return self._parse_primary()

    def _parse_primary(self) -> Any:
        """Parse primary expressions (literals, variables, function calls, parenthesized exprs)."""
        tok = self._peek()

        if tok.type == TokenType.NUMBER:
            self._advance()
            return NumberLit(tok.value)

        if tok.type == TokenType.STRING:
            self._advance()
            return StringLit(tok.value)

        if tok.type == TokenType.LPAREN:
            self._advance()
            expr = self._parse_expr()
            self._expect(TokenType.RPAREN)
            return expr

        if tok.type == TokenType.FN:
            self._advance()
            name_tok = self._expect(TokenType.IDENT)
            name = "FN" + name_tok.value.upper()
            self._expect(TokenType.LPAREN)
            args: list = []
            if self._peek().type != TokenType.RPAREN:
                args.append(self._parse_expr())
                while self._match(TokenType.COMMA):
                    args.append(self._parse_expr())
            self._expect(TokenType.RPAREN)
            return FnCall(name, args)

        if tok.type == TokenType.IDENT:
            name = tok.value
            upper = name.upper()
            builtin_funcs = {
                "ABS", "INT", "RND", "SQR", "SIN", "COS", "TAN", "ATN",
                "LOG", "EXP", "LEN", "LEFT$", "RIGHT$", "MID$",
                "CHR$", "ASC", "STR$", "VAL", "TAB", "SPC",
                "STRING$", "INSTR", "TIMER", "PEEK",
                "DATE$", "TIME$", "INKEY$", "FRE", "ENVIRON$",
                "LCASE$", "UCASE$", "LTRIM$", "RTRIM$",
                "FIX", "SGN", "CSNG", "CDBL", "CINT",
            }
            if upper in builtin_funcs and self.pos + 1 < len(self.tokens) and self.tokens[self.pos + 1].type == TokenType.LPAREN:
                self._advance()
                self._expect(TokenType.LPAREN)
                args = []
                if self._peek().type != TokenType.RPAREN:
                    args.append(self._parse_expr())
                    while self._match(TokenType.COMMA):
                        args.append(self._parse_expr())
                self._expect(TokenType.RPAREN)
                return FnCall(upper, args)

            self._advance()
            norm = self._normalize_var(name)
            if self._peek().type == TokenType.LPAREN:
                self._advance()
                indices = [self._parse_expr()]
                while self._match(TokenType.COMMA):
                    indices.append(self._parse_expr())
                self._expect(TokenType.RPAREN)
                return ArrayRef(norm, indices)
            return VarRef(norm)

        raise BasicSyntaxError(f"Unexpected token: {tok.type.name} ({tok.value!r})")

    @staticmethod
    def _normalize_var(name: str) -> str:
        """Normalize a variable name to uppercase."""
        return name.upper()