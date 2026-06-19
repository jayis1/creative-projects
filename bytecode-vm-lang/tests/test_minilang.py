"""Tests for MiniLang — lexer, parser, type checker, compiler, VM."""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from minilang.compiler import compile_program
from minilang.vm import VM
from minilang.lexer import Lexer, TokenKind, tokenize
from minilang.parser import Parser, parse
from minilang.types import TypeChecker, TypeError as MLTypeError
from minilang.errors import LexError, ParseError, MiniLangError
from minilang.optimizer import optimize, ConstantFolder
from minilang.bytecode import OpCode, Disassembler
from minilang.value import Value


def run_code(code: str) -> list[str]:
    """Compile and run *code*, returning the VM's output list."""
    program = compile_program(code)
    vm = VM(program)
    vm.run()
    return vm.output


# --------------------------------------------------------------------------- #
# Lexer tests                                                                  #
# --------------------------------------------------------------------------- #
class TestLexer:
    def test_integers(self):
        tokens = tokenize("42 0 123")
        assert tokens[0].kind == TokenKind.INT
        assert tokens[0].lexeme == "42"
        assert tokens[1].lexeme == "0"
        assert tokens[2].lexeme == "123"

    def test_strings(self):
        tokens = tokenize('"hello" "with\\nnewline"')
        assert tokens[0].kind == TokenKind.STRING
        assert tokens[0].lexeme == "hello"
        assert tokens[1].lexeme == "with\nnewline"

    def test_keywords(self):
        tokens = tokenize("let const fn if else while for return break continue true false nil")
        assert tokens[0].kind == TokenKind.LET
        assert tokens[1].kind == TokenKind.CONST
        assert tokens[2].kind == TokenKind.FN
        assert tokens[3].kind == TokenKind.IF

    def test_operators(self):
        tokens = tokenize("+ - * / % == != < <= > >= = && || ! ->")
        assert tokens[0].kind == TokenKind.PLUS
        assert tokens[5].kind == TokenKind.EQEQ
        assert tokens[6].kind == TokenKind.NEQ
        # Count: + - * / % == != < <= > >= = && || ! ->
        # indices: 0 1 2 3 4 5  6  7 8  9 10 11 12 13 14 15
        assert tokens[15].kind == TokenKind.ARROW

    def test_comments(self):
        tokens = tokenize("let x = 1; // this is a comment\nlet y = 2;")
        # Find the LET tokens
        lets = [t for t in tokens if t.kind == TokenKind.LET]
        assert len(lets) == 2

    def test_block_comments(self):
        tokens = tokenize("let x = 1; /* block comment */ let y = 2;")
        lets = [t for t in tokens if t.kind == TokenKind.LET]
        assert len(lets) == 2

    def test_invalid_char(self):
        with pytest.raises(LexError):
            tokenize("let x = @;")

    def test_unterminated_string(self):
        with pytest.raises(LexError):
            tokenize('"unterminated')

    def test_line_col_tracking(self):
        tokens = tokenize("let x = 1;\nlet y = 2;")
        # First token on line 1
        assert tokens[0].line == 1
        # Second line tokens
        let_y = [t for t in tokens if t.kind == TokenKind.LET][1]
        assert let_y.line == 2


# --------------------------------------------------------------------------- #
# Parser tests                                                                #
# --------------------------------------------------------------------------- #
class TestParser:
    def test_simple_expr(self):
        ast = parse("let x = 1 + 2;")
        assert len(ast.stmts) == 1

    def test_function_decl(self):
        ast = parse("fn add(a: int, b: int) -> int { return a + b; }")
        assert len(ast.stmts) == 1
        func = ast.stmts[0]
        assert func.name == "add"
        assert len(func.params) == 2

    def test_if_else(self):
        ast = parse("if x > 0 { print(1); } else { print(0); }")
        assert len(ast.stmts) == 1
        assert ast.stmts[0].else_branch is not None

    def test_while_loop(self):
        ast = parse("while x < 10 { x = x + 1; }")
        assert len(ast.stmts) == 1

    def test_for_loop(self):
        ast = parse("for i in 0..10 { print(i); }")
        assert len(ast.stmts) == 1
        assert ast.stmts[0].var == "i"

    def test_array_literal(self):
        ast = parse("let a = [1, 2, 3];")
        assert len(ast.stmts) == 1

    def test_index_expr(self):
        ast = parse("let x = a[0];")
        assert len(ast.stmts) == 1

    def test_parse_error(self):
        with pytest.raises(ParseError):
            parse("let = 1;")
        with pytest.raises(ParseError):
            parse("fn { }")


# --------------------------------------------------------------------------- #
# Type checker tests                                                           #
# --------------------------------------------------------------------------- #
class TestTypeChecker:
    def test_int_arithmetic(self):
        tc = TypeChecker()
        tc.check(parse("let x = 1 + 2;"))
        assert isinstance(tc.expr_types, dict)

    def test_type_mismatch(self):
        with pytest.raises(MLTypeError):
            tc = TypeChecker()
            tc.check(parse("let x = 1 + true;"))

    def test_undefined_variable(self):
        with pytest.raises(MLTypeError):
            tc = TypeChecker()
            tc.check(parse("let x = undefined_var;"))

    def test_const_assignment(self):
        with pytest.raises(MLTypeError):
            tc = TypeChecker()
            tc.check(parse("const x = 1; x = 2;"))

    def test_break_outside_loop(self):
        with pytest.raises(MLTypeError):
            tc = TypeChecker()
            tc.check(parse("break;"))

    def test_return_outside_function(self):
        with pytest.raises(MLTypeError):
            tc = TypeChecker()
            tc.check(parse("return 1;"))

    def test_array_type(self):
        tc = TypeChecker()
        tc.check(parse("let a = [1, 2, 3]; let x = a[0];"))

    def test_function_signature(self):
        tc = TypeChecker()
        tc.check(parse("fn f(x: int) -> int { return x + 1; }"))


# --------------------------------------------------------------------------- #
# VM / end-to-end tests                                                        #
# --------------------------------------------------------------------------- #
class TestVM:
    def test_arithmetic(self):
        assert run_code("print(1 + 2 * 3);") == ["7"]
        assert run_code("print(10 - 4);") == ["6"]
        assert run_code("print(20 / 4);") == ["5"]
        assert run_code("print(17 % 5);") == ["2"]
        assert run_code("print(-(5));") == ["-5"]

    def test_variables(self):
        assert run_code("let x = 10; let y = 20; print(x + y);") == ["30"]

    def test_const(self):
        assert run_code("const x = 42; print(x);") == ["42"]

    def test_comparison(self):
        assert run_code("print(5 < 10);") == ["true"]
        assert run_code("print(5 > 10);") == ["false"]
        assert run_code("print(5 == 5);") == ["true"]
        assert run_code("print(5 != 5);") == ["false"]
        assert run_code("print(5 <= 5);") == ["true"]
        assert run_code("print(5 >= 6);") == ["false"]

    def test_logical(self):
        assert run_code("print(true && false);") == ["false"]
        assert run_code("print(true || false);") == ["true"]
        assert run_code("print(!false);") == ["true"]
        assert run_code("print(!true);") == ["false"]

    def test_short_circuit(self):
        # If && short-circuits, the second expression isn't evaluated.
        # We can't easily test side-effects, but we can check the result.
        assert run_code("print(false && true);") == ["false"]
        assert run_code("print(false || true);") == ["true"]

    def test_if_else(self):
        assert run_code("let x = 10; if x > 5 { print(1); } else { print(0); }") == ["1"]
        assert run_code("let x = 3; if x > 5 { print(1); } else { print(0); }") == ["0"]

    def test_while_loop(self):
        assert run_code("let i = 0; while i < 5 { i = i + 1; } print(i);") == ["5"]

    def test_for_loop(self):
        assert run_code("let s = 0; for i in 0..10 { s = s + i; } print(s);") == ["45"]

    def test_break(self):
        result = run_code("let s = 0; for i in 0..100 { if i == 5 { break; } s = s + i; } print(s);")
        assert result == ["10"]  # 0+1+2+3+4 = 10

    def test_continue(self):
        result = run_code("let s = 0; for i in 0..5 { if i == 2 { continue; } s = s + i; } print(s);")
        assert result == ["8"]  # 0+1+3+4 = 8

    def test_arrays(self):
        assert run_code("let a = [1, 2, 3]; print(a[0]); print(a[2]);") == ["1", "3"]
        assert run_code("let a = [10, 20]; a[0] = 99; print(a[0]);") == ["99"]
        assert run_code("let a = [1, 2, 3]; print(len(a));") == ["3"]
        assert run_code("let a = []; push(a, 42); print(a[0]);") == ["42"]

    def test_strings(self):
        assert run_code('print("hello");') == ["hello"]
        assert run_code('let s = "world"; print(len(s));') == ["5"]
        assert run_code('print(str(42));') == ["42"]

    def test_functions(self):
        assert run_code("fn f(x: int) -> int { return x * 2; } print(f(21));") == ["42"]

    def test_recursion(self):
        assert run_code("fn fact(n: int) -> int { if n <= 1 { return 1; } return n * fact(n - 1); } print(fact(5));") == ["120"]
        assert run_code("fn fib(n: int) -> int { if n < 2 { return n; } return fib(n - 1) + fib(n - 2); } print(fib(10));") == ["55"]

    def test_nested_calls(self):
        assert run_code("fn double(x: int) -> int { return x * 2; } print(double(double(5)));") == ["20"]

    def test_division_by_zero(self):
        with pytest.raises(MiniLangError):
            run_code("print(10 / 0);")

    def test_modulo_by_zero(self):
        with pytest.raises(MiniLangError):
            run_code("print(10 % 0);")

    def test_array_index_out_of_bounds(self):
        with pytest.raises(MiniLangError):
            run_code("let a = [1, 2]; print(a[5]);")

    def test_negative_array_index(self):
        with pytest.raises(MiniLangError):
            run_code("let a = [1, 2]; print(a[-1]);")

    def test_nil(self):
        assert run_code("print(nil);") == ["nil"]


# --------------------------------------------------------------------------- #
# Optimizer tests                                                              #
# --------------------------------------------------------------------------- #
class TestOptimizer:
    def test_constant_folding(self):
        folder = ConstantFolder()
        from minilang.ast import IntLit, BinOp
        ast = parse("let x = 2 + 3;")
        optimized = optimize(ast)
        decl = optimized.stmts[0]
        assert isinstance(decl.value, IntLit)
        assert decl.value.value == 5

    def test_dead_code_elimination(self):
        ast = parse("fn f() -> int { return 1; print(2); }")
        optimized = optimize(ast)
        func = optimized.stmts[0]
        # The print(2) after return should be eliminated.
        assert len(func.body.stmts) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])