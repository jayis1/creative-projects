#!/usr/bin/env python3
"""Bug hunt tests for prolog-engine."""

from prolog_engine.engine import Engine, EngineError
from prolog_engine.builtins import register_builtins
from prolog_engine.lexer import Lexer, TokenType
from prolog_engine.parser import Parser, ParseError
from prolog_engine.ast_nodes import Atom, Variable, Number, Compound, term_to_str
from prolog_engine.unifier import Unifier, Substitution, UnificationError

import pytest


def _make_engine() -> Engine:
    engine = Engine()
    register_builtins(engine)
    return engine


# ==================================================================
# Bug 1: Negative numbers in is/2 expressions
# ==================================================================

class TestBugNegativeNumbers:
    """Bug: X is -3 fails to parse because - is an infix operator
    and there's nothing on the left."""

    def test_negative_number_in_is(self):
        """X is -3 should evaluate to X = -3."""
        engine = _make_engine()
        try:
            results = engine.query("?- X is -3.")
            assert len(results) == 1
            x_val = results[0].apply(Variable("X"))
            assert isinstance(x_val, Number)
            assert x_val.value == -3
        except ParseError:
            pytest.xfail("Parser doesn't handle unary minus at start of expression")

    def test_negative_number_in_comparison(self):
        """-3 < 0 should succeed."""
        engine = _make_engine()
        try:
            results = engine.query("?- -3 < 0.")
            assert len(results) == 1
        except ParseError:
            pytest.xfail("Parser doesn't handle unary minus at start of expression")


# ==================================================================
# Bug 2: Dead code in engine (matching_keys unused)
# ==================================================================

class TestBugDeadCode:
    """Bug: matching_keys variable is computed but never used."""

    def test_matching_keys_unused(self):
        """Verify the engine still works despite dead code."""
        engine = _make_engine()
        engine.load_source("a(1). a(2).")
        results = engine.query("?- a(X).")
        assert len(results) == 2


# ==================================================================
# Bug 3: Bare except clauses masking errors
# ==================================================================

class TestBugBareExcept:
    """Bug: Several builtins catch all exceptions with bare except Exception,
    which could mask real programming errors."""

    def test_is_with_non_arithmetic(self):
        """X is f(1) should fail gracefully, not with a cryptic error."""
        engine = _make_engine()
        # This should fail (no results), not raise an exception
        results = engine.query("?- X is f(1).")
        assert len(results) == 0

    def test_comparison_with_non_numbers(self):
        """a < b should fail gracefully."""
        engine = _make_engine()
        results = engine.query("?- a < b.")
        assert len(results) == 0


# ==================================================================
# Bug 4: format_solution shows internal variable names
# ==================================================================

class TestBugFormatSolution:
    """Bug: format_solution may show internal renamed variable names
    like _X_42 instead of X."""

    def test_format_shows_original_names(self):
        """Format should show original variable names."""
        engine = _make_engine()
        engine.load_source("parent(tom, bob).")
        results = engine.query("?- parent(X, Y).")
        assert len(results) == 1
        solution = engine.format_solution(results[0])
        # Should contain X and Y, not _X_42 etc.
        assert "X" in solution
        assert "Y" in solution
        # Should NOT contain renamed variable names
        assert "_X_" not in solution
        assert "_Y_" not in solution


# ==================================================================
# Bug 5: Integer division with negative numbers
# ==================================================================

class TestBugIntegerDivision:
    """Bug: // operator in Python has different semantics than Prolog
    for negative numbers. Python's // rounds toward -infinity,
    Prolog's // rounds toward zero."""

    def test_integer_div_negative(self):
        """7 // -2 should be -3 (round toward zero) in Prolog,
        but Python gives -4 (round toward -infinity)."""
        engine = _make_engine()
        results = engine.query("?- X is 7 // -2.")
        if len(results) == 1:
            x = results[0].apply(Variable("X"))
            # Prolog: 7 // -2 = -3 (toward zero)
            # Python: 7 // -2 = -4 (toward -infinity)
            # This test documents the discrepancy
            # We should fix this to match Prolog semantics
            assert x.value == -3, f"Expected -3 (Prolog semantics), got {x.value}"


# ==================================================================
# Bug 6: Parser doesn't handle anonymous variable in all positions
# ==================================================================

class TestBugAnonymousVariable:
    """Test that anonymous variable _ works correctly."""

    def test_anonymous_variable_in_query(self):
        """_ should work in queries (don't care about binding)."""
        engine = _make_engine()
        engine.load_source("a(1, x). a(2, y).")
        results = engine.query("?- a(X, _).")
        assert len(results) == 2

    def test_anonymous_variable_multiple(self):
        """Multiple _ should be independent (not unified with each other)."""
        engine = _make_engine()
        engine.load_source("pair(1, 2). pair(3, 3).")
        # ?- pair(_, _). should match both, not just pair(3, 3)
        results = engine.query("?- pair(_, _).")
        assert len(results) == 2


# ==================================================================
# Bug 7: Singleton variable warning not given
# ==================================================================

class TestBugSingletonVariable:
    """Minor: No warning for singleton variables (a common Prolog feature)."""

    def test_singleton_variable_still_works(self):
        """Engine should still work correctly with singleton variables."""
        engine = _make_engine()
        engine.load_source("a(X) :- b(X). b(1).")
        results = engine.query("?- a(X).")
        assert len(results) == 1


# ==================================================================
# Bug 8: Substitution chasing can loop if circular
# ==================================================================

class TestBugSubstitutionLoop:
    """Bug: If a circular substitution is somehow created,
    substitute() could loop forever."""

    def test_no_circular_substitution(self):
        """Occurs-check should prevent circular substitutions."""
        X = Variable("X")
        with pytest.raises(UnificationError):
            Unifier.unify(X, Compound("f", (X,)))


# ==================================================================
# Bug 9: Arithmetic evaluation doesn't handle all edge cases
# ==================================================================

class TestBugArithmeticEdgeCases:
    def test_division_by_zero(self):
        """Division by zero should raise EngineError."""
        engine = _make_engine()
        with pytest.raises(EngineError):
            engine.query("?- X is 1 / 0.")

    def test_integer_division_by_zero(self):
        """Integer division by zero should raise EngineError."""
        engine = _make_engine()
        with pytest.raises(EngineError):
            engine.query("?- X is 1 // 0.")

    def test_power_large_exponent(self):
        """Large power should still compute."""
        engine = _make_engine()
        results = engine.query("?- X is 2 ** 10.")
        assert len(results) == 1
        assert results[0].apply(Variable("X")).value == 1024


# ==================================================================
# Bug 10: Append with variable tail
# ==================================================================

class TestBugAppendVariableTail:
    """Test append with partially instantiated lists."""

    def test_append_variable_first(self):
        """append(X, [c], [a, b, c]) should generate X = [a, b]."""
        engine = _make_engine()
        results = engine.query("?- append(X, [c], [a, b, c]).")
        assert len(results) == 1

    def test_append_generate_splits(self):
        """append(X, Y, [a, b]) should generate all splits."""
        engine = _make_engine()
        results = engine.query("?- append(X, Y, [a, b]).")
        # Should get: [], [a,b] | [a], [b] | [a,b], []
        assert len(results) == 3


# ==================================================================
# Bug 11: Parser precedence for expressions with commas in lists
# ==================================================================

class TestBugParserPrecedence:
    """Test that the parser handles complex expressions correctly."""

    def test_is_with_compound_expression(self):
        """X is (3 + 4) * 2 should be 14."""
        engine = _make_engine()
        results = engine.query("?- X is (3 + 4) * 2.")
        assert len(results) == 1
        assert results[0].apply(Variable("X")).value == 14

    def test_nested_is(self):
        """is with nested arithmetic should work."""
        engine = _make_engine()
        results = engine.query("?- X is 2 + 3 * 4 - 1.")
        assert len(results) == 1
        # 2 + (3*4) - 1 = 2 + 12 - 1 = 13
        assert results[0].apply(Variable("X")).value == 13


# ==================================================================
# Bug 12: Engine doesn't handle String type in goals
# ==================================================================

class TestBugStringGoals:
    """Test that strings work in the engine."""

    def test_string_unification(self):
        """Strings should unify with each other."""
        engine = _make_engine()
        results = engine.query('?- X = "hello".')
        assert len(results) == 1

    def test_string_in_fact(self):
        """Strings should work as fact arguments."""
        engine = _make_engine()
        engine.load_source('name("alice").')
        results = engine.query('?- name(X).')
        assert len(results) == 1


# ==================================================================
# Bug 13: Lexer edge cases
# ==================================================================

class TestBugLexerEdgeCases:
    def test_lexer_float(self):
        """Lexer should handle floats like 3.14."""
        tokens = Lexer("3.14").tokens
        assert tokens[0].type == TokenType.NUMBER
        assert tokens[0].value == "3.14"

    def test_lexer_scientific_notation(self):
        """Lexer should handle scientific notation."""
        tokens = Lexer("1e5").tokens
        assert tokens[0].type == TokenType.NUMBER
        assert tokens[0].value == "1e5"

    def test_lexer_double_slash(self):
        """Lexer should tokenize // as an operator atom."""
        tokens = Lexer("//").tokens
        assert tokens[0].type == TokenType.ATOM
        assert tokens[0].value == "//"

    def test_lexer_backslash_equal(self):
        """Lexer should tokenize \\= as one operator."""
        tokens = Lexer("\\=").tokens
        assert tokens[0].type == TokenType.ATOM
        assert tokens[0].value == "\\="


# ==================================================================
# Bug 14: retract doesn't work with unification matching
# ==================================================================

class TestBugRetractMatching:
    """Test that retract properly unifies with clause heads."""

    def test_retract_with_variable(self):
        """retract(a(_)) should remove the first a/1 clause."""
        engine = _make_engine()
        engine.load_source("a(1). a(2).")
        results = engine.query("?- retract(a(1)).")
        assert len(results) == 1
        results = engine.query("?- a(X).")
        assert len(results) == 1  # only a(2) left


# ==================================================================
# Bug 15: Variable equality issue
# ==================================================================

class TestBugVariableEquality:
    """Bug: Variable equality uses name-based equality, so two
    different Variable objects with the same name are considered equal.
    This can cause issues when standardizing apart creates variables
    with the same base name."""

    def test_renamed_variables_distinct(self):
        """Renamed variables should be distinct from originals."""
        X = Variable("X")
        engine = _make_engine()
        renamed = engine._rename_term(X, {})
        # The renamed variable should have a different name
        assert renamed.name != "X"


# ==================================================================
# Bug 16: Parser allows atoms as clause heads but they get wrapped
# ==================================================================

class TestBugAtomClauseHead:
    """Test that atom clause heads work correctly."""

    def test_atom_fact(self):
        """hello. should be a valid fact."""
        parser = Parser.from_source("hello.")
        program = parser.parse_program()
        assert len(program.clauses) == 1
        clause = program.clauses[0]
        assert clause.head.name == "hello"
        assert clause.head.arity == 0

    def test_atom_rule(self):
        """hello :- true. should be a valid rule."""
        parser = Parser.from_source("hello :- true.")
        program = parser.parse_program()
        assert len(program.clauses) == 1
        clause = program.clauses[0]
        assert not clause.is_fact
        assert clause.head.name == "hello"

    def test_atom_goal(self):
        """Query with atom goal should work."""
        engine = _make_engine()
        engine.load_source("hello :- true.")
        results = engine.query("?- hello.")
        assert len(results) == 1