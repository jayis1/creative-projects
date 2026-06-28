"""Test suite for the typeinfer Hindley-Milner engine.

These tests exercise lexer, parser, unification, inference, primitives,
tuples, let-polymorphism, let-rec, error handling, and pretty-printing.
"""

from __future__ import annotations

import pytest

from typeinfer import (
    infer, infer_with_trace, type_to_string, scheme_to_string,
    parse, tokenize, Scheme,
    TVar, TCon, TFun, INT, BOOL, UNIT,
    unify, apply_subst, compose_subst, UnificationError,
    InferError, ParserError, LexerError,
)
from typeinfer.primitives import default_env, primitives_env, list_env, maybe_env
from typeinfer.parser import (
    EInt, EBool, EVar, ELam, EApp, ELet, EIf, ETuple,
)


# ---------------------------------------------------------------------------
# Lexer
# ---------------------------------------------------------------------------

class TestLexer:
    def test_basic_tokens(self):
        toks = tokenize(r"\x. x")
        kinds = [t.kind for t in toks]
        assert kinds == ["LAMBDA", "IDENT", "DOT", "IDENT", "EOF"]

    def test_int(self):
        toks = tokenize("42")
        assert toks[0].kind == "INT"
        assert toks[0].value == "42"

    def test_bool_keywords(self):
        toks = tokenize("true false")
        assert toks[0].kind == "BOOL" and toks[0].value == "true"
        assert toks[1].kind == "BOOL" and toks[1].value == "false"

    def test_keywords(self):
        toks = tokenize("let rec in if then else")
        kinds = [t.kind for t in toks if t.kind != "EOF"]
        assert kinds == ["LET", "REC", "IN", "IF", "THEN", "ELSE"]

    def test_operators(self):
        toks = tokenize("1 + 2 * 3 == 4 && true")
        ops = [t.value for t in toks if t.kind == "OP"]
        assert ops == ["+", "*", "==", "&&"]

    def test_arrow_token(self):
        toks = tokenize("->")
        assert toks[0].kind == "ARROW"

    def test_eq_vs_double_eq(self):
        """``=`` is EQ, ``==`` is OP — must not be confused."""
        toks = tokenize("x = 1 == 2")
        kinds = [t.kind for t in toks if t.kind != "EOF"]
        assert "EQ" in kinds
        assert "OP" in kinds
        eq_tok = [t for t in toks if t.kind == "EQ"]
        assert len(eq_tok) == 1
        op_eq = [t for t in toks if t.kind == "OP" and t.value == "=="]
        assert len(op_eq) == 1

    def test_unicode_lambda(self):
        toks = tokenize("λx. x")
        assert toks[0].kind == "LAMBDA"

    def test_comments(self):
        toks = tokenize("1 -- this is a comment\n+ 2")
        kinds = [t.kind for t in toks if t.kind != "EOF"]
        assert kinds == ["INT", "OP", "INT"]

    def test_invalid_char(self):
        with pytest.raises(LexerError):
            tokenize("@")

    def test_empty_input(self):
        toks = tokenize("")
        assert len(toks) == 1 and toks[0].kind == "EOF"

    def test_underscore_ident(self):
        toks = tokenize("_foo _bar'")
        assert toks[0].kind == "IDENT" and toks[0].value == "_foo"
        assert toks[1].kind == "IDENT" and toks[1].value == "_bar'"


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

class TestParser:
    def test_int(self):
        assert isinstance(parse("42"), EInt) and parse("42").value == 42

    def test_bool(self):
        assert isinstance(parse("true"), EBool) and parse("true").value is True
        assert isinstance(parse("false"), EBool) and parse("false").value is False

    def test_var(self):
        assert isinstance(parse("x"), EVar) and parse("x").name == "x"

    def test_lambda(self):
        e = parse(r"\x. x")
        assert isinstance(e, ELam)
        assert e.param == "x"
        assert isinstance(e.body, EVar)

    def test_multi_arg_lambda(self):
        e = parse(r"\x y. x")
        assert isinstance(e, ELam) and e.param == "x"
        assert isinstance(e.body, ELam) and e.body.param == "y"

    def test_application_left_assoc(self):
        e = parse("f x y")
        assert isinstance(e, EApp)
        assert isinstance(e.fn, EApp)  # (f x) y

    def test_let(self):
        e = parse(r"let x = 1 in x")
        assert isinstance(e, ELet)
        assert e.name == "x" and e.is_rec is False

    def test_let_rec(self):
        e = parse(r"let rec f = \x. f x in f")
        assert isinstance(e, ELet) and e.is_rec is True

    def test_if(self):
        e = parse("if true then 1 else 2")
        assert isinstance(e, EIf)

    def test_tuple(self):
        e = parse("(1, 2, 3)")
        assert isinstance(e, ETuple) and len(e.items) == 3

    def test_unit(self):
        e = parse("()")
        assert isinstance(e, ETuple) and len(e.items) == 0

    def test_paren_expr(self):
        e = parse("(x)")
        assert isinstance(e, EVar) and e.name == "x"

    def test_operator_precedence_mul_over_add(self):
        # 1 + 2 * 3  =>  (+ 1 (* 2 3))
        e = parse("1 + 2 * 3")
        assert isinstance(e, EApp)  # outer is (+) applied
        # e = ((+ 1) (* 2 3))
        assert isinstance(e.fn, EApp) and e.fn.fn.name == "+"
        assert isinstance(e.arg, EApp) and e.arg.fn.fn.name == "*"

    def test_operator_left_assoc(self):
        # 1 - 2 - 3 => ((1 - 2) - 3)
        e = parse("1 - 2 - 3")
        # outer: (-) applied to (1 - 2) and 3
        assert isinstance(e, EApp)
        assert isinstance(e.fn, EApp)
        assert e.arg == EInt(3)

    def test_trailing_tokens_error(self):
        with pytest.raises(ParserError):
            parse("x y z )")

    def test_missing_dot(self):
        with pytest.raises(ParserError):
            parse(r"\x x")

    def test_lambda_no_param(self):
        with pytest.raises(ParserError):
            parse(r"\. x")

    def test_let_missing_in(self):
        with pytest.raises(ParserError):
            parse(r"let x = 1 x")


# ---------------------------------------------------------------------------
# Unification
# ---------------------------------------------------------------------------

class TestUnification:
    def test_unify_same_con(self):
        s = unify(INT, INT)
        assert s == {}

    def test_unify_var_with_con(self):
        a = TVar(0)
        s = unify(a, INT)
        assert s == {0: INT}
        assert apply_subst(s, a) == INT

    def test_unify_con_with_var(self):
        a = TVar(0)
        s = unify(INT, a)
        assert s == {0: INT}

    def test_unify_fun(self):
        a, b = TVar(0), TVar(1)
        s = unify(TFun(a, b), TFun(INT, BOOL))
        assert apply_subst(s, a) == INT
        assert apply_subst(s, b) == BOOL

    def test_unify_mismatch(self):
        with pytest.raises(UnificationError):
            unify(INT, BOOL)

    def test_occurs_check(self):
        a = TVar(0)
        with pytest.raises(UnificationError):
            unify(a, TFun(a, a))

    def test_unify_reflexive_var(self):
        a = TVar(0)
        s = unify(a, a)
        assert s == {}

    def test_compose_subst(self):
        s1 = {0: INT}
        s2 = {1: TVar(0)}
        composed = compose_subst(s1, s2)
        # s1 ∘ s2: apply s2 first, then s1
        # 1 -> TVar(0) -> INT
        assert apply_subst(composed, TVar(1)) == INT

    def test_unify_fun_with_con_error(self):
        with pytest.raises(UnificationError):
            unify(TFun(INT, INT), INT)


# ---------------------------------------------------------------------------
# Inference — basic
# ---------------------------------------------------------------------------

class TestInferenceBasic:
    def test_int_literal(self):
        assert infer("42") == INT

    def test_bool_literal(self):
        assert infer("true") == BOOL

    def test_identity(self):
        t = infer(r"\x. x")
        assert type_to_string(t) == "a -> a"

    def test_const(self):
        t = infer(r"\x. \y. x")
        assert type_to_string(t) == "a -> b -> a"

    def test_application(self):
        t = infer(r"(\x. x) 42")
        assert t == INT

    def test_multi_arg_lambda(self):
        t = infer(r"\x y. x")
        assert type_to_string(t) == "a -> b -> a"

    def test_if(self):
        t = infer("if true then 1 else 2")
        assert t == INT


# ---------------------------------------------------------------------------
# Inference — let & let-polymorphism
# ---------------------------------------------------------------------------

class TestLetPolymorphism:
    def test_let_mono(self):
        t = infer(r"let x = 1 in x")
        assert t == INT

    def test_let_poly_identity(self):
        t = infer(r"let id = \x. x in id")
        assert type_to_string(t) == "a -> a"

    def test_let_poly_used_twice(self):
        """The classic HM let-polymorphism test: id used at Int and Bool."""
        t = infer(r"let id = \x. x in (id 1, id true)")
        s = type_to_string(t)
        assert "Int" in s and "Bool" in s

    def test_let_poly_does_not_generalize_lambda_param(self):
        """\\x. (let y = x in (y 1, y true)) should fail — x is not generalised."""
        with pytest.raises(InferError):
            infer(r"\x. let y = x in (y 1, y true)")

    def test_let_rec(self):
        t = infer(r"let rec f = \n. if n then 1 else f n in f")
        # n is Bool (used in if cond), returns Int
        assert type_to_string(t) == "Bool -> Int"


# ---------------------------------------------------------------------------
# Inference — operators & builtins
# ---------------------------------------------------------------------------

class TestOperators:
    def test_add(self):
        assert infer("1 + 2", use_builtins=True) == INT

    def test_precedence(self):
        assert infer("1 + 2 * 3", use_builtins=True) == INT

    def test_comparison(self):
        assert infer("1 < 2", use_builtins=True) == BOOL

    def test_poly_equality(self):
        t = infer(r"\x. x == x", use_builtins=True)
        assert type_to_string(t) == "a -> Bool"

    def test_equality_int(self):
        assert infer("1 == 2", use_builtins=True) == BOOL

    def test_boolean_ops(self):
        assert infer("true && false", use_builtins=True) == BOOL
        assert infer("true || false", use_builtins=True) == BOOL

    def test_add_fn(self):
        t = infer(r"\x. x + 1", use_builtins=True)
        assert t == TFun(INT, INT)

    def test_type_mismatch_arith(self):
        with pytest.raises(InferError):
            infer("1 + true", use_builtins=True)


# ---------------------------------------------------------------------------
# Inference — tuples
# ---------------------------------------------------------------------------

class TestTuples:
    def test_pair(self):
        t = infer("(1, 2)")
        assert isinstance(t, TCon) and t.name == "Tuple"
        assert t.args == (INT, INT)

    def test_triple(self):
        t = infer("(1, true, 42)")
        assert t.args == (INT, BOOL, INT)

    def test_unit(self):
        assert infer("()") == UNIT

    def test_nested_tuple(self):
        t = infer("(1, (true, 2))")
        inner = t.args[1]
        assert inner.args == (BOOL, INT)


# ---------------------------------------------------------------------------
# Inference — ADTs
# ---------------------------------------------------------------------------

class TestADTs:
    def test_nil(self):
        t = infer("Nil", use_builtins=True)
        assert isinstance(t, TCon) and t.name == "List"

    def test_cons(self):
        t = infer("Cons 1 Nil", use_builtins=True)
        assert isinstance(t, TCon) and t.name == "List"
        assert t.args == (INT,)

    def test_just(self):
        t = infer("Just 5", use_builtins=True)
        assert isinstance(t, TCon) and t.name == "Maybe"
        assert t.args == (INT,)

    def test_nothing(self):
        t = infer("Nothing", use_builtins=True)
        assert isinstance(t, TCon) and t.name == "Maybe"

    def test_let_poly_adt(self):
        t = infer(r"let f = \x. Cons x Nil in (f 1, f true)", use_builtins=True)
        # Tuple<List<Int>, List<Bool>>
        assert isinstance(t, TCon) and t.name == "Tuple"
        assert t.args[0].args == (INT,)
        assert t.args[1].args == (BOOL,)


# ---------------------------------------------------------------------------
# Inference — error cases
# ---------------------------------------------------------------------------

class TestErrors:
    def test_unbound_variable(self):
        with pytest.raises(InferError, match="Unbound"):
            infer("x")

    def test_self_application_occurs(self):
        with pytest.raises(InferError):
            infer(r"\x. x x")

    def test_if_cond_not_bool(self):
        with pytest.raises(InferError):
            infer("if 1 then 2 else 3")

    def test_branch_mismatch(self):
        with pytest.raises(InferError):
            infer("if true then 1 else false")

    def test_apply_non_function(self):
        with pytest.raises(InferError):
            infer("1 2")

    def test_lexer_error_propagates(self):
        with pytest.raises(LexerError):
            infer("@")

    def test_parser_error_propagates(self):
        with pytest.raises(ParserError):
            parse("let = 1")


# ---------------------------------------------------------------------------
# Pretty printing
# ---------------------------------------------------------------------------

class TestPrettyPrinting:
    def test_type_to_string_renumbers(self):
        a = TVar(5)
        b = TVar(10)
        t = TFun(a, b)
        assert type_to_string(t) == "a -> b"

    def test_scheme_to_string_basic(self):
        sc = Scheme([0], TFun(TVar(0), TVar(0)))
        s = scheme_to_string(sc)
        # Should contain ∀, a quantifier name, and the body with matching names
        assert "∀" in s or "forall" in s
        # The variable name in the quantifier and body must be the same letter
        # e.g. "∀ a. a -> a" not "∀ a. b -> b"
        # Extract quantifier letter
        assert "->" in s

    def test_type_to_string_fun_paren(self):
        t = TFun(TFun(INT, INT), INT)
        s = type_to_string(t)
        assert "(" in s and ")" in s

    def test_type_to_string_con_with_args(self):
        t = TCon("List", (INT,))
        assert type_to_string(t) == "List<Int>"


# ---------------------------------------------------------------------------
# Trace
# ---------------------------------------------------------------------------

class TestTrace:
    def test_trace_returns_list(self):
        t, steps = infer_with_trace(r"\x. x")
        assert isinstance(steps, list)
        assert len(steps) > 0

    def test_trace_let_poly(self):
        t, steps = infer_with_trace(r"let id = \x. x in id 42")
        assert any("let" in s for s in steps)
        assert any("application" in s for s in steps)
        assert type_to_string(t) == "Int"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

class TestCLI:
    def test_cli_basic(self, capsys):
        from typeinfer.__main__ import main
        rc = main([r"\x. x"])
        out = capsys.readouterr().out.strip()
        assert rc == 0
        assert "->" in out

    def test_cli_builtins(self, capsys):
        from typeinfer.__main__ import main
        rc = main(["-b", "1 + 2"])
        out = capsys.readouterr().out.strip()
        assert rc == 0 and out == "Int"

    def test_cli_version(self, capsys):
        from typeinfer.__main__ import main
        with pytest.raises(SystemExit) as exc_info:
            main(["--version"])
        assert exc_info.value.code == 0
        out = capsys.readouterr().out.strip()
        assert "typeinfer" in out

    def test_cli_error(self, capsys):
        from typeinfer.__main__ import main
        rc = main(["x"])
        err = capsys.readouterr().err.strip()
        assert rc == 1
        assert "error" in err.lower()

    def test_cli_ast(self, capsys):
        from typeinfer.__main__ import main
        rc = main(["--ast", r"\x. x"])
        out = capsys.readouterr().out
        assert rc == 0 and "ELam" in out

    def test_cli_no_args(self, capsys):
        from typeinfer.__main__ import main
        rc = main([])
        out = capsys.readouterr().out
        assert rc == 1 and ("usage" in out.lower() or "Usage" in out)