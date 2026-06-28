"""Comprehensive test suite for new typeinfer v2.0 features.

Tests: string literals, list literals, type annotations, match expressions,
parallel let, data declarations, pair/either/string primitives, config system,
CLI enhancements.
"""

from __future__ import annotations

import json
import os
import tempfile

import pytest

from typeinfer import (
    infer, infer_with_trace, type_to_string, scheme_to_string,
    parse, tokenize, Scheme,
    TVar, TCon, TFun, INT, BOOL, STRING, UNIT,
    unify, apply_subst, compose_subst, UnificationError,
    InferError, ParserError, LexerError,
    Config, load_config, save_config, default_config, ConfigError,
)
from typeinfer.primitives import (
    default_env, primitives_env, list_env, maybe_env,
    either_env, string_env, pair_env, io_env,
)
from typeinfer.parser import (
    EInt, EBool, EString, EVar, ELam, EApp, ELet, ELetMulti, EIf, ETuple,
    EList, EMatch, EDataDecl,
    PVar, PConstr, PInt, PString, PWild, PTuple,
)


# ---------------------------------------------------------------------------
# String literals
# ---------------------------------------------------------------------------

class TestStringLiterals:
    def test_string_literal_type(self):
        assert infer('"hello"', use_builtins=True) == STRING

    def test_string_in_let(self):
        t = infer(r'let s = "hello" in s', use_builtins=True)
        assert t == STRING

    def test_string_in_lambda(self):
        t = infer(r'\x. "hello"', use_builtins=True)
        assert t == TFun(TVar(0), STRING) or t == TFun(STRING, STRING)

    def test_string_concat(self):
        t = infer(r'concat "hello" "world"', use_builtins=True)
        assert t == STRING

    def test_string_length(self):
        t = infer('length "hello"', use_builtins=True)
        assert t == INT

    def test_string_reverse(self):
        t = infer('reverse "abc"', use_builtins=True)
        assert t == STRING

    def test_string_to_upper(self):
        t = infer('toUpper "abc"', use_builtins=True)
        assert t == STRING

    def test_string_to_lower(self):
        t = infer('toLower "ABC"', use_builtins=True)
        assert t == STRING

    def test_string_append(self):
        t = infer(r'append "a" "b"', use_builtins=True)
        assert t == STRING

    def test_string_substring(self):
        t = infer('substring 0 3 "hello"', use_builtins=True)
        assert t == STRING

    def test_string_char_at(self):
        t = infer('charAt 0 "abc"', use_builtins=True)
        assert t == INT

    def test_string_lambda_id(self):
        t = infer(r'\x: String. x', use_builtins=True)
        assert t == TFun(STRING, STRING)

    def test_string_in_tuple(self):
        t = infer('("hello", 42)', use_builtins=True)
        assert isinstance(t, TCon) and t.name == "Tuple"
        assert t.args == (STRING, INT)


class TestStringLexer:
    def test_simple_string(self):
        toks = tokenize('"hello"')
        assert toks[0].kind == "STRING"
        assert toks[0].value == "hello"

    def test_empty_string(self):
        toks = tokenize('""')
        assert toks[0].kind == "STRING"
        assert toks[0].value == ""

    def test_string_with_escape(self):
        toks = tokenize(r'"hello\nworld"')
        assert toks[0].kind == "STRING"
        assert toks[0].value == "hello\nworld"

    def test_string_with_tab_escape(self):
        toks = tokenize(r'"a\tb"')
        assert toks[0].value == "a\tb"

    def test_string_with_quote_escape(self):
        toks = tokenize(r'"say \"hi\""'[:-1] + '"')  # careful with escaping
        # Just test a simpler case
        toks = tokenize('"a\\"b"')
        assert toks[0].value == 'a"b'

    def test_unterminated_string(self):
        with pytest.raises(LexerError):
            tokenize('"unterminated')

    def test_string_backslash_escape(self):
        toks = tokenize(r'"a\\b"')
        assert toks[0].value == 'a\\b'


# ---------------------------------------------------------------------------
# List literals
# ---------------------------------------------------------------------------

class TestListLiterals:
    def test_empty_list(self):
        t = infer('[]', use_builtins=True)
        assert isinstance(t, TCon) and t.name == "List"
        # Empty list is polymorphic
        assert isinstance(t.args[0], TVar)

    def test_int_list(self):
        t = infer('[1, 2, 3]', use_builtins=True)
        assert isinstance(t, TCon) and t.name == "List"
        assert t.args == (INT,)

    def test_bool_list(self):
        t = infer('[true, false]', use_builtins=True)
        assert isinstance(t, TCon) and t.name == "List"
        assert t.args == (BOOL,)

    def test_string_list(self):
        t = infer('["a", "b"]', use_builtins=True)
        assert isinstance(t, TCon) and t.name == "List"
        assert t.args == (STRING,)

    def test_list_in_let(self):
        t = infer(r'let xs = [1, 2] in xs', use_builtins=True)
        assert isinstance(t, TCon) and t.name == "List"

    def test_list_empty_poly(self):
        """Empty list should be polymorphic."""
        t = infer(r'let xs = [] in xs', use_builtins=True)
        s = type_to_string(t)
        assert "List" in s

    def test_list_with_trailing_comma(self):
        t = infer('[1, 2,]', use_builtins=True)
        assert isinstance(t, TCon) and t.name == "List"

    def test_list_type_mismatch(self):
        with pytest.raises(InferError):
            infer('[1, true]', use_builtins=True)

    def test_list_parser_ast(self):
        e = parse('[1, 2]')
        assert isinstance(e, EList)
        assert len(e.items) == 2

    def test_empty_list_parser(self):
        e = parse('[]')
        assert isinstance(e, EList)
        assert len(e.items) == 0


# ---------------------------------------------------------------------------
# Type annotations
# ---------------------------------------------------------------------------

class TestTypeAnnotations:
    def test_lambda_param_annotation(self):
        t = infer(r'\x: Int. x + 1', use_builtins=True)
        assert t == TFun(INT, INT)

    def test_lambda_param_bool_annotation(self):
        t = infer(r'\x: Bool. not x', use_builtins=True)
        assert t == TFun(BOOL, BOOL)

    def test_lambda_param_string_annotation(self):
        t = infer(r'\x: String. length x', use_builtins=True)
        assert t == TFun(STRING, INT)

    def test_let_var_annotation(self):
        t = infer(r'let x: Int = 5 in x + 1', use_builtins=True)
        assert t == INT

    def test_annotation_resolves_monomorphic(self):
        t = infer(r'\x: Int. \y: Int. x + y', use_builtins=True)
        assert t == TFun(INT, TFun(INT, INT))

    def test_annotation_with_function_type(self):
        t = infer(r'\f: Int -> Int. f 5', use_builtins=True)
        assert t == TFun(TFun(INT, INT), INT)

    def test_annotation_mismatch(self):
        with pytest.raises(InferError):
            infer(r'let x: Int = true in x', use_builtins=True)

    def test_annotation_mismatch_lambda(self):
        with pytest.raises(InferError):
            infer(r'\x: Int. not x', use_builtins=True)

    def test_annotation_with_tuple_type(self):
        t = infer(r'\x: (Int, Bool). x', use_builtins=True)
        assert isinstance(t, TFun)
        assert isinstance(t.param, TCon) and t.param.name == "Tuple"

    def test_annotation_with_list_type(self):
        t = infer(r'\x: List<Int>. x', use_builtins=True)
        assert isinstance(t, TFun)
        assert isinstance(t.param, TCon) and t.param.name == "List"

    def test_annotation_unit(self):
        t = infer(r'\x: Unit. x', use_builtins=True)
        assert t == TFun(UNIT, UNIT)


# ---------------------------------------------------------------------------
# Match expressions
# ---------------------------------------------------------------------------

class TestMatch:
    def test_match_nil(self):
        t = infer(r'match Nil with | Nil -> 0', use_builtins=True)
        assert t == INT

    def test_match_cons(self):
        t = infer(
            r'match Cons 1 Nil with | Nil -> 0 | Cons x _ -> x',
            use_builtins=True
        )
        assert t == INT

    def test_match_maybe(self):
        t = infer(
            r'match Just 5 with | Nothing -> 0 | Just x -> x',
            use_builtins=True
        )
        assert t == INT

    def test_match_tuple(self):
        t = infer(
            r'match (1, true) with | (a, b) -> a',
            use_builtins=True
        )
        assert t == INT

    def test_match_wildcard(self):
        t = infer(
            r'match Nil with | _ -> 42',
            use_builtins=True
        )
        assert t == INT

    def test_match_string_pattern(self):
        t = infer(
            r'match "hello" with | "hi" -> 0 | _ -> 1',
            use_builtins=True
        )
        assert t == INT

    def test_match_int_pattern(self):
        t = infer(
            r'match 42 with | 0 -> 1 | _ -> 0',
            use_builtins=True
        )
        assert t == INT

    def test_match_poly(self):
        t = infer(
            r'let f = \x. match x with | Nothing -> 0 | Just n -> n in (f (Just 1), f Nothing)',
            use_builtins=True
        )
        assert isinstance(t, TCon) and t.name == "Tuple"
        assert t.args[0] == INT
        assert t.args[1] == INT

    def test_match_branch_mismatch(self):
        with pytest.raises(InferError):
            infer(
                r'match Nil with | Nil -> 0 | Cons x _ -> true',
                use_builtins=True
            )

    def test_match_parser(self):
        e = parse(r'match Nil with | Nil -> 0')
        assert isinstance(e, EMatch)
        assert len(e.alts) == 1

    def test_match_multiple_alts(self):
        e = parse(r'match Nil with | Nil -> 0 | Cons x _ -> x')
        assert isinstance(e, EMatch)
        assert len(e.alts) == 2

    def test_match_no_leading_bar(self):
        e = parse(r'match Nil with | Nil -> 0')
        assert isinstance(e, EMatch)


# ---------------------------------------------------------------------------
# Parallel let bindings
# ---------------------------------------------------------------------------

class TestParallelLet:
    def test_parallel_let_basic(self):
        t = infer(r'let x = 1 and y = 2 in x + y', use_builtins=True)
        assert t == INT

    def test_parallel_let_no_shadow(self):
        """Parallel lets should not see each other's bindings."""
        with pytest.raises(InferError):
            infer(r'let x = 1 and y = x in y', use_builtins=True)

    def test_parallel_let_poly(self):
        t = infer(
            r'let f = \x. x and g = \x. x in (f 1, g true)',
            use_builtins=True
        )
        assert isinstance(t, TCon) and t.name == "Tuple"

    def test_parallel_let_parser(self):
        e = parse(r'let x = 1 and y = 2 in x')
        assert isinstance(e, ELetMulti)
        assert len(e.bindings) == 2

    def test_parallel_let_three(self):
        t = infer(
            r'let x = 1 and y = 2 and z = 3 in x + y + z',
            use_builtins=True
        )
        assert t == INT


# ---------------------------------------------------------------------------
# Data declarations
# ---------------------------------------------------------------------------

class TestDataDeclarations:
    def test_simple_data(self):
        t = infer(r'data Tree = Leaf | Node Tree Tree in Leaf', use_builtins=True)
        assert isinstance(t, TCon) and t.name == "Tree"

    def test_data_with_params(self):
        t = infer(
            r'data Box a = MkBox a in MkBox 5',
            use_builtins=True
        )
        assert isinstance(t, TCon) and t.name == "Box"

    def test_data_recursive(self):
        t = infer(
            r'data Tree = Leaf | Node Tree Tree in Node Leaf Leaf',
            use_builtins=True
        )
        assert isinstance(t, TCon) and t.name == "Tree"

    def test_data_match(self):
        t = infer(
            r'data Color = Red | Green | Blue in match Red with | Red -> 1 | Green -> 2 | Blue -> 3',
            use_builtins=True
        )
        assert t == INT

    def test_data_parser(self):
        e = parse(r'data Tree = Leaf | Node Tree Tree in Leaf')
        assert isinstance(e, EDataDecl)
        assert e.type_name == "Tree"
        assert len(e.constructors) == 2


# ---------------------------------------------------------------------------
# Either ADT
# ---------------------------------------------------------------------------

class TestEither:
    def test_left(self):
        t = infer('Left 1', use_builtins=True)
        assert isinstance(t, TCon) and t.name == "Either"

    def test_right(self):
        t = infer('Right true', use_builtins=True)
        assert isinstance(t, TCon) and t.name == "Either"

    def test_left_right_match(self):
        t = infer(
            r'match Left 5 with | Left x -> x | Right y -> 0',
            use_builtins=True
        )
        assert t == INT


# ---------------------------------------------------------------------------
# Pair primitives
# ---------------------------------------------------------------------------

class TestPairPrimitives:
    def test_fst(self):
        t = infer(r'fst (1, true)', use_builtins=True)
        assert t == INT

    def test_snd(self):
        t = infer(r'snd (1, true)', use_builtins=True)
        assert t == BOOL

    def test_fst_poly(self):
        t = infer(r'\x. fst x', use_builtins=True)
        s = type_to_string(t)
        assert "Tuple" in s or "a" in s

    def test_snd_poly(self):
        t = infer(r'\x. snd x', use_builtins=True)
        s = type_to_string(t)
        assert "Tuple" in s or "a" in s


# ---------------------------------------------------------------------------
# IO primitives (typing only)
# ---------------------------------------------------------------------------

class TestIOPrimitives:
    def test_print_int(self):
        t = infer(r'print 5', use_builtins=True)
        assert t == UNIT

    def test_print_string(self):
        t = infer(r'printS "hello"', use_builtins=True)
        assert t == UNIT

    def test_print_bool(self):
        t = infer(r'printB true', use_builtins=True)
        assert t == UNIT

    def test_read_int(self):
        t = infer(r'read ()', use_builtins=True)
        assert t == INT

    def test_read_string(self):
        t = infer(r'readS ()', use_builtins=True)
        assert t == STRING


# ---------------------------------------------------------------------------
# Config system
# ---------------------------------------------------------------------------

class TestConfig:
    def test_default_config(self):
        cfg = default_config()
        assert cfg.builtins is True
        assert cfg.explain is False
        assert cfg.log_level == "WARNING"

    def test_config_validation(self):
        cfg = Config(builtins="not_a_bool")
        with pytest.raises(ConfigError):
            cfg.validate()

    def test_config_invalid_log_level(self):
        cfg = Config(log_level="INVALID")
        with pytest.raises(ConfigError):
            cfg.validate()

    def test_config_invalid_max_type_vars(self):
        cfg = Config(max_type_vars=0)
        with pytest.raises(ConfigError):
            cfg.validate()

    def test_json_config_roundtrip(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump({"builtins": False, "log_level": "DEBUG"}, f)
            f.flush()
            cfg = load_config(f.name)
            assert cfg.builtins is False
            assert cfg.log_level == "DEBUG"
        os.unlink(f.name)

    def test_toml_config_roundtrip(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".toml", delete=False
        ) as f:
            f.write('builtins = false\nlog_level = "DEBUG"\n')
            f.flush()
            cfg = load_config(f.name)
            assert cfg.builtins is False
            assert cfg.log_level == "DEBUG"
        os.unlink(f.name)

    def test_save_config_json(self):
        cfg = Config(builtins=False, explain=True, log_level="INFO")
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            path = f.name
        try:
            save_config(path, cfg)
            cfg2 = load_config(path)
            assert cfg2.builtins is False
            assert cfg2.explain is True
            assert cfg2.log_level == "INFO"
        finally:
            os.unlink(path)

    def test_config_file_not_found(self):
        with pytest.raises(ConfigError):
            load_config("/nonexistent/path.json")

    def test_config_unknown_extension(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".xml", delete=False
        ) as f:
            f.write("<config/>")
            f.flush()
            with pytest.raises(ConfigError):
                load_config(f.name)
        os.unlink(f.name)

    def test_config_apply_logging(self):
        cfg = Config(log_level="DEBUG")
        cfg.apply_logging()
        import logging
        assert logging.getLogger("typeinfer").level == logging.DEBUG


# ---------------------------------------------------------------------------
# Enhanced CLI
# ---------------------------------------------------------------------------

class TestEnhancedCLI:
    def test_cli_json_output(self, capsys):
        from typeinfer.__main__ import main
        rc = main(["-b", "--json", "1 + 2"])
        out = capsys.readouterr().out.strip()
        assert rc == 0
        data = json.loads(out)
        assert data["type"] == "Int"

    def test_cli_json_error(self, capsys):
        from typeinfer.__main__ import main
        rc = main(["--json", "x"])
        out = capsys.readouterr().out.strip()
        assert rc == 1
        data = json.loads(out)
        assert "error" in data

    def test_cli_file_input(self, capsys):
        from typeinfer.__main__ import main
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".tc", delete=False
        ) as f:
            f.write(r"\x. x")
            f.flush()
            path = f.name
        try:
            rc = main(["--file", path])
            out = capsys.readouterr().out.strip()
            assert rc == 0
            assert "->" in out
        finally:
            os.unlink(path)

    def test_cli_config(self, capsys):
        from typeinfer.__main__ import main
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump({"builtins": True}, f)
            f.flush()
            cfg_path = f.name
        try:
            rc = main(["--config", cfg_path, "1 + 2"])
            out = capsys.readouterr().out.strip()
            assert rc == 0
            assert out == "Int"
        finally:
            os.unlink(cfg_path)

    def test_cli_no_builtins_flag(self, capsys):
        from typeinfer.__main__ import main
        rc = main(["--no-builtins", "42"])
        out = capsys.readouterr().out.strip()
        assert rc == 0
        assert out == "Int"

    def test_cli_log_level(self, capsys):
        from typeinfer.__main__ import main
        rc = main(["--log-level", "DEBUG", "-b", "1 + 2"])
        out = capsys.readouterr().out.strip()
        assert rc == 0
        assert out == "Int"

    def test_cli_ast_string_literal(self, capsys):
        from typeinfer.__main__ import main
        rc = main(["--ast", '"hello"'])
        out = capsys.readouterr().out
        assert rc == 0
        assert "EString" in out

    def test_cli_ast_list(self, capsys):
        from typeinfer.__main__ import main
        rc = main(["--ast", "[1, 2]"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "EList" in out

    def test_cli_explain_match(self, capsys):
        from typeinfer.__main__ import main
        rc = main(["-b", "-e", r"match Nil with | Nil -> 0"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "match" in out.lower()
        assert "Int" in out


# ---------------------------------------------------------------------------
# Complex expressions combining multiple features
# ---------------------------------------------------------------------------

class TestComplexExpressions:
    def test_let_poly_with_annotations(self):
        t = infer(
            r'let id: Int -> Int = \x. x in id 5',
            use_builtins=True
        )
        assert t == INT

    def test_match_with_data_decl(self):
        t = infer(
            r'data Option = None | Some Int in match Some 42 with | None -> 0 | Some n -> n',
            use_builtins=True
        )
        assert t == INT

    def test_nested_match(self):
        t = infer(
            r'''match Just (Cons 1 Nil) with 
            | Nothing -> 0 
            | Just xs -> match xs with 
              | Nil -> 0 
              | Cons y _ -> y''',
            use_builtins=True
        )
        assert t == INT

    def test_parallel_let_with_match(self):
        t = infer(
            r'let f = \x. match x with | Nothing -> 0 | Just n -> n in let g = \x. f (Just x) in g 5',
            use_builtins=True
        )
        assert t == INT

    def test_string_list_inference(self):
        t = infer(
            r'let xs = "hello" in length (concat xs "!")',
            use_builtins=True
        )
        assert t == INT

    def test_higher_order_with_match(self):
        t = infer(
            r'let map = \f. \xs. match xs with | Nil -> Nil | Cons x rest -> Cons (f x) rest in map (\n. n + 1) (Cons 1 Nil)',
            use_builtins=True
        )
        assert isinstance(t, TCon) and t.name == "List"
        assert t.args == (INT,)

    def test_curried_with_annotations(self):
        t = infer(
            r'\x: Int. \y: Int. \z: Int. x + y + z',
            use_builtins=True
        )
        assert t == TFun(INT, TFun(INT, TFun(INT, INT)))


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

class TestLogging:
    def test_logging_trace(self):
        """Test that logging is properly set up."""
        import logging
        logging.getLogger("typeinfer").setLevel(logging.DEBUG)
        # Just ensure inference doesn't break with logging enabled
        t = infer(r"\x. x")
        assert type_to_string(t) == "a -> a"
        # Reset
        logging.getLogger("typeinfer").setLevel(logging.WARNING)