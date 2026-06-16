#!/usr/bin/env python3
"""Tests for the comprehensive improvements to the mini-Prolog engine.

Tests cover:
- Configuration module
- Error hierarchy
- New built-in predicates (atom_length, atom_concat, sub_atom, char_code,
  max_list, min_list, sum_list, variables, numbervars, halt)
- Enhanced CLI
- Engine statistics and properties
"""

import pytest
import os
import tempfile

from prolog_engine.engine import Engine, EngineError, EvaluationError
from prolog_engine.builtins import register_builtins
from prolog_engine.lexer import Lexer, TokenType
from prolog_engine.parser import Parser, ParseError
from prolog_engine.ast_nodes import (
    Atom, Variable, Number, String, Compound, Clause, Query, Program,
    term_to_str, variables_in,
)
from prolog_engine.unifier import Unifier, Substitution, UnificationError
from prolog_engine.config import EngineConfig, find_config, load_config
from prolog_engine.errors import (
    PrologError, LexerError, ParseError as ErrorsParseError,
    UnificationError as ErrorsUnificationError,
    EngineError as ErrorsEngineError,
    EvaluationError as ErrorsEvaluationError,
    InstantiationError, TypeError as PrologTypeError,
    ExistenceError, PermissionError,
)


def _make_engine(**kwargs) -> Engine:
    """Create an engine with builtins registered."""
    engine = Engine(**kwargs)
    register_builtins(engine)
    return engine


# ==================================================================
# Configuration tests
# ==================================================================

class TestConfig:
    """Tests for the EngineConfig module."""

    def test_default_config(self):
        config = EngineConfig()
        assert config.max_depth == 1000
        assert config.max_solutions == 10000
        assert config.trace is False

    def test_custom_config(self):
        config = EngineConfig(max_depth=500, max_solutions=5000, trace=True)
        assert config.max_depth == 500
        assert config.max_solutions == 5000
        assert config.trace is True

    def test_config_to_dict(self):
        config = EngineConfig()
        d = config.to_dict()
        assert "max_depth" in d
        assert "max_solutions" in d
        assert "trace" in d

    def test_config_from_dict(self):
        d = {"max_depth": 200, "max_solutions": 2000}
        config = EngineConfig.from_dict(d)
        assert config.max_depth == 200
        assert config.max_solutions == 2000

    def test_config_from_dict_ignores_unknown_keys(self):
        d = {"max_depth": 200, "unknown_key": "ignored"}
        config = EngineConfig.from_dict(d)
        assert config.max_depth == 200

    def test_config_apply_to_engine(self):
        config = EngineConfig(max_depth=42, trace=True)
        engine = Engine()
        config.apply_to_engine(engine)
        assert engine._max_depth == 42
        assert engine._trace is True

    def test_config_save_and_load_json(self):
        config = EngineConfig(max_depth=999, max_solutions=888, trace=True)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            filepath = f.name
        try:
            config.save(filepath)
            loaded = EngineConfig.from_file(filepath)
            assert loaded.max_depth == 999
            assert loaded.max_solutions == 888
            assert loaded.trace is True
        finally:
            os.unlink(filepath)

    def test_find_config_returns_none_when_no_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = find_config(tmpdir)
            assert result is None

    def test_load_config_default(self):
        config = load_config()
        assert isinstance(config, EngineConfig)
        assert config.max_depth == 1000


# ==================================================================
# Error hierarchy tests
# ==================================================================

class TestErrors:
    """Tests for the error hierarchy module."""

    def test_prolog_error(self):
        err = PrologError("test error")
        assert str(err) == "test error"

    def test_prolog_error_with_detail(self):
        err = PrologError("test error", detail="extra info")
        assert "extra info" in str(err)

    def test_lexer_error(self):
        err = LexerError("bad char", line=5, col=10)
        assert err.line == 5
        assert err.col == 10
        assert "5" in str(err)

    def test_parse_error(self):
        err = ErrorsParseError("unexpected token")
        assert "unexpected token" in str(err)

    def test_unification_error(self):
        err = ErrorsUnificationError("cannot unify")
        assert "cannot unify" in str(err)

    def test_engine_error(self):
        err = ErrorsEngineError("depth exceeded")
        assert "depth exceeded" in str(err)

    def test_evaluation_error(self):
        err = ErrorsEvaluationError("unknown function")
        assert "unknown function" in str(err)

    def test_instantiation_error(self):
        err = InstantiationError()
        assert "Instantiation error" in str(err)

    def test_type_error(self):
        err = PrologTypeError(expected="number", got="atom")
        assert "number" in str(err)

    def test_existence_error(self):
        err = ExistenceError(procedure="foo/2")
        assert "foo/2" in str(err)

    def test_permission_error(self):
        err = PermissionError(operation="modify static")
        assert "modify static" in str(err)

    def test_error_inheritance(self):
        assert issubclass(ErrorsEngineError, PrologError)
        assert issubclass(ErrorsEvaluationError, PrologError)
        assert issubclass(ErrorsUnificationError, PrologError)


# ==================================================================
# Engine property tests
# ==================================================================

class TestEngineProperties:
    """Tests for engine configuration properties."""

    def test_max_depth_property(self):
        engine = Engine()
        assert engine.max_depth == 1000
        engine.max_depth = 500
        assert engine.max_depth == 500

    def test_max_depth_validation(self):
        engine = Engine()
        with pytest.raises(ValueError):
            engine.max_depth = 0

    def test_max_solutions_property(self):
        engine = Engine()
        assert engine.max_solutions == 10000
        engine.max_solutions = 5000
        assert engine.max_solutions == 5000

    def test_max_solutions_validation(self):
        engine = Engine()
        with pytest.raises(ValueError):
            engine.max_solutions = 0

    def test_statistics(self):
        engine = _make_engine()
        stats = engine.statistics()
        assert "clauses" in stats
        assert "predicates" in stats
        assert "builtins" in stats
        assert "max_depth" in stats

    def test_load_file(self):
        engine = _make_engine()
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.pl', delete=False
        ) as f:
            f.write("parent(tom, bob).\nparent(tom, liz).\n")
            filepath = f.name
        try:
            engine.load_file(filepath)
            assert len(engine.clauses) == 2
        finally:
            os.unlink(filepath)

    def test_load_file_not_found(self):
        engine = _make_engine()
        with pytest.raises(FileNotFoundError):
            engine.load_file("/nonexistent/file.pl")

    def test_get_builtins(self):
        engine = _make_engine()
        builtins = engine.get_builtins()
        assert isinstance(builtins, dict)
        assert "is/2" in builtins
        assert "=/2" in builtins


# ==================================================================
# New built-in predicate tests
# ==================================================================

class TestAtomLength:
    """Tests for atom_length/2."""

    def test_atom_length_known(self):
        engine = _make_engine()
        results = engine.query("?- atom_length(hello, N).")
        assert len(results) == 1
        n = results[0].apply(Variable("N"))
        assert n.value == 5

    def test_atom_length_check(self):
        engine = _make_engine()
        results = engine.query("?- atom_length(hello, 5).")
        assert len(results) == 1

    def test_atom_length_wrong(self):
        engine = _make_engine()
        results = engine.query("?- atom_length(hello, 3).")
        assert len(results) == 0


class TestAtomConcat:
    """Tests for atom_concat/3."""

    def test_atom_concat_forward(self):
        engine = _make_engine()
        results = engine.query("?- atom_concat(hello, world, X).")
        assert len(results) == 1
        x = results[0].apply(Variable("X"))
        assert x.name == "helloworld"

    def test_atom_concat_backward(self):
        engine = _make_engine()
        results = engine.query("?- atom_concat(X, world, helloworld).")
        assert len(results) == 1
        x = results[0].apply(Variable("X"))
        assert x.name == "hello"

    def test_atom_concat_all_splits(self):
        engine = _make_engine()
        results = engine.query("?- atom_concat(X, Y, ab).")
        assert len(results) == 3  # '', 'ab'; 'a', 'b'; 'ab', ''


class TestCharCode:
    """Tests for char_code/2."""

    def test_char_to_code(self):
        engine = _make_engine()
        results = engine.query("?- char_code(a, X).")
        assert len(results) == 1
        x = results[0].apply(Variable("X"))
        assert x.value == ord('a')

    def test_code_to_char(self):
        engine = _make_engine()
        results = engine.query(f"?- char_code(X, {ord('Z')}).")
        assert len(results) == 1
        x = results[0].apply(Variable("X"))
        assert x.name == "Z"


class TestMaxList:
    """Tests for max_list/2."""

    def test_max_list(self):
        engine = _make_engine()
        engine.load_source("nums([3, 1, 4, 1, 5]).")
        results = engine.query("?- nums(L), max_list(L, M).")
        assert len(results) == 1
        m = results[0].apply(Variable("M"))
        assert m.value == 5


class TestMinList:
    """Tests for min_list/2."""

    def test_min_list(self):
        engine = _make_engine()
        engine.load_source("nums([3, 1, 4, 1, 5]).")
        results = engine.query("?- nums(L), min_list(L, M).")
        assert len(results) == 1
        m = results[0].apply(Variable("M"))
        assert m.value == 1


class TestSumList:
    """Tests for sum_list/2."""

    def test_sum_list(self):
        engine = _make_engine()
        engine.load_source("nums([1, 2, 3, 4]).")
        results = engine.query("?- nums(L), sum_list(L, S).")
        assert len(results) == 1
        s = results[0].apply(Variable("S"))
        assert s.value == 10


class TestVariables:
    """Tests for variables/2."""

    def test_variables_simple(self):
        engine = _make_engine()
        results = engine.query("?- variables(f(X, Y), V).")
        assert len(results) == 1


class TestNumbervars:
    """Tests for numbervars/3."""

    def test_numbervars(self):
        engine = _make_engine()
        results = engine.query("?- numbervars(f(X, Y), 0, N).")
        assert len(results) == 1
        n = results[0].apply(Variable("N"))
        assert n.value == 2


# ==================================================================
# create_engine convenience function tests
# ==================================================================

class TestCreateEngine:
    """Tests for the create_engine convenience function."""

    def test_create_engine_default(self):
        from prolog_engine import create_engine
        engine = create_engine()
        assert isinstance(engine, Engine)
        assert len(engine.get_builtins()) > 0

    def test_create_engine_with_config(self):
        from prolog_engine import create_engine, EngineConfig
        config = EngineConfig(max_depth=500)
        engine = create_engine(config=config)
        assert engine.max_depth == 500

    def test_create_engine_with_params(self):
        from prolog_engine import create_engine
        engine = create_engine(max_depth=200, trace=True)
        assert engine.max_depth == 200
        assert engine.trace is True


# ==================================================================
# CLI module tests
# ==================================================================

class TestCLI:
    """Tests for CLI helper functions."""

    def test_run_file(self):
        from prolog_engine.cli import run_file
        engine = _make_engine()
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.pl', delete=False
        ) as f:
            f.write("hello(world).\n")
            filepath = f.name
        try:
            run_file(engine, filepath)
            assert len(engine.clauses) == 1
        finally:
            os.unlink(filepath)

    def test_run_query(self, capsys):
        from prolog_engine.cli import run_query
        engine = _make_engine()
        engine.load_source("parent(tom, bob).")
        run_query(engine, "?- parent(tom, X).")
        captured = capsys.readouterr()
        assert "bob" in captured.out


# ==================================================================
# Integration tests for new features
# ==================================================================

class TestIntegrationNewFeatures:
    """Integration tests for new built-in predicates."""

    def test_atom_length_with_variables(self):
        engine = _make_engine()
        engine.load_source("word(hello). word(hi). word(greetings).")
        results = engine.query("?- word(W), atom_length(W, L), L > 3.")
        words = [r.apply(Variable("W")).name for r in results]
        assert "hello" in words
        assert "greetings" in words
        assert "hi" not in words

    def test_atom_concat_composition(self):
        engine = _make_engine()
        results = engine.query("?- atom_concat(hello, world, X), atom_length(X, L).")
        assert len(results) == 1
        assert results[0].apply(Variable("X")).name == "helloworld"
        assert results[0].apply(Variable("L")).value == 10

    def test_char_code_roundtrip(self):
        engine = _make_engine()
        results = engine.query("?- char_code(a, C), char_code(X, C).")
        assert len(results) == 1
        assert results[0].apply(Variable("X")).name == "a"

    def test_sum_list_aggregation(self):
        engine = _make_engine()
        engine.load_source("scores([85, 90, 78, 92]).")
        results = engine.query("?- scores(L), sum_list(L, Total), min_list(L, Min), max_list(L, Max).")
        assert len(results) == 1
        total = results[0].apply(Variable("Total"))
        assert total.value == 345

    def test_halt_builtin_registered(self):
        engine = _make_engine()
        builtins = engine.get_builtins()
        assert "halt/0" in builtins

    def test_statistics_method(self):
        engine = _make_engine()
        engine.load_source("parent(tom, bob). parent(tom, liz).")
        stats = engine.statistics()
        assert stats["clauses"] == 2
        assert stats["builtins"] > 50

    def test_engine_clear(self):
        engine = _make_engine()
        engine.load_source("parent(tom, bob).")
        assert len(engine.clauses) == 1
        engine.clear()
        assert len(engine.clauses) == 0

    def test_load_source_method(self):
        engine = _make_engine()
        engine.load_source("parent(tom, bob). parent(tom, liz).")
        results = engine.query("?- parent(tom, X).")
        assert len(results) == 2

    def test_version(self):
        from prolog_engine import __version__
        assert __version__ == "2.0.0"

    def test_all_new_builtins_registered(self):
        """Verify all new builtins are registered."""
        engine = _make_engine()
        builtins = engine.get_builtins()
        new_predicates = [
            "atom_length/2", "atom_concat/3", "sub_atom/5",
            "char_code/2", "max_list/2", "min_list/2", "sum_list/2",
            "variables/2", "numbervars/3", "halt/0",
        ]
        for pred in new_predicates:
            assert pred in builtins, f"Missing builtin: {pred}"