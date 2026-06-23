"""Tests for standard library and new features added in v2.0.

Covers:
- Standard library functions (compose, negate, conjoin, disjoin, etc.)
- New special forms (rec, let-values, define-values)
- New builtins (load, trace/untrace, time, assert)
- Stream operations
- Set operations
- String utilities
- Bug fixes (if/cond with or, apply with various types)
- New primitives (zip, unfold, string-join, etc.)
"""

import pytest
import sys
from io import StringIO

from scheme_interpreter.interpreter import Interpreter, SchemeError, SchemeExit
from scheme_interpreter.primitives import set_global_interpreter
from scheme_interpreter.types import (
    Symbol, Pair, Nil, Bool, Char, Vector, Unspecified,
    TRUE, FALSE, scheme_repr,
    list_to_pairs, pairs_to_list,
)


@pytest.fixture
def interp():
    """Create a fresh interpreter with stdlib loaded."""
    i = Interpreter(load_stdlib=True)
    set_global_interpreter(i)
    return i


@pytest.fixture
def interp_no_stdlib():
    """Create a fresh interpreter without stdlib."""
    i = Interpreter(load_stdlib=False)
    set_global_interpreter(i)
    return i


# ---------------------------------------------------------------------------
# Standard library tests
# ---------------------------------------------------------------------------

class TestStdlib:
    def test_square(self, interp):
        assert interp.run("(square 5)") == 25
        assert interp.run("(square -3)") == 9

    def test_cube(self, interp):
        assert interp.run("(cube 3)") == 27

    def test_inc_dec(self, interp):
        assert interp.run("(inc 5)") == 6
        assert interp.run("(dec 5)") == 4

    def test_average(self, interp):
        assert interp.run("(average 1 2 3 4 5)") == 3

    def test_compose(self, interp):
        # compose applies right-to-left: (compose f g) = f(g(x))
        # (compose square inc) = square(inc(4)) = square(5) = 25
        assert interp.run("((compose square inc) 4)") == 25
        # (compose inc square) = inc(square(4)) = inc(16) = 17
        assert interp.run("((compose inc square) 4)") == 17

    def test_compose_identity(self, interp):
        result = interp.run("((compose) 42)")
        assert result == 42

    def test_negate(self, interp):
        assert interp.run("((negate odd?) 4)") is TRUE
        assert interp.run("((negate odd?) 3)") is FALSE

    def test_conjoin(self, interp):
        assert interp.run("((conjoin integer? positive?) 5)") is TRUE
        assert interp.run("((conjoin integer? positive?) -5)") is FALSE
        assert interp.run("((conjoin integer? positive?) 3.14)") is FALSE

    def test_disjoin(self, interp):
        assert interp.run("((disjoin zero? negative?) -1)") is TRUE
        assert interp.run("((disjoin zero? negative?) 5)") is FALSE

    def test_string_prefix(self, interp):
        assert interp.run('(string-prefix? "foo" "foobar")') is TRUE
        assert interp.run('(string-prefix? "bar" "foobar")') is FALSE

    def test_string_suffix(self, interp):
        assert interp.run('(string-suffix? "bar" "foobar")') is TRUE
        assert interp.run('(string-suffix? "foo" "foobar")') is FALSE

    def test_string_trim(self, interp):
        assert interp.run('(string-trim "  hello  ")') == "hello"

    def test_string_reverse(self, interp):
        assert interp.run('(string-reverse "hello")') == "olleh"

    def test_iota(self, interp):
        result = interp.run("(iota 5 0 1)")
        assert pairs_to_list(result) == [0, 1, 2, 3, 4]

    def test_iota_default(self, interp):
        result = interp.run("(iota 5)")
        assert pairs_to_list(result) == [0, 1, 2, 3, 4]

    def test_any(self, interp):
        assert interp.run("(any odd? '(2 4 6 7 8))") is TRUE
        assert interp.run("(any odd? '(2 4 6 8))") is FALSE

    def test_every(self, interp):
        assert interp.run("(every even? '(2 4 6 8))") is TRUE
        assert interp.run("(every even? '(2 4 5 8))") is FALSE

    def test_list_of(self, interp):
        assert interp.run("((list-of? integer?) '(1 2 3))") is TRUE
        assert interp.run("((list-of? integer?) '(1 2 \"a\"))") is FALSE

    def test_list_tabulate(self, interp):
        result = interp.run("(list-tabulate 5 (lambda (i) (* i i)))")
        assert pairs_to_list(result) == [0, 1, 4, 9, 16]


# ---------------------------------------------------------------------------
# Stream tests
# ---------------------------------------------------------------------------

class TestStreams:
    def test_stream_basic(self, interp):
        interp.run("(define (integers-from n) (cons-stream n (integers-from (+ n 1))))")
        interp.run("(define naturals (integers-from 1))")
        assert interp.run("(stream-car naturals)") == 1
        assert interp.run("(stream-car (stream-cdr naturals))") == 2
        assert interp.run("(stream-ref naturals 5)") == 6

    def test_stream_take(self, interp):
        interp.run("(define (integers-from n) (cons-stream n (integers-from (+ n 1))))")
        interp.run("(define naturals (integers-from 1))")
        result = interp.run("(stream-take naturals 5)")
        assert pairs_to_list(result) == [1, 2, 3, 4, 5]

    def test_stream_map(self, interp):
        interp.run("(define (integers-from n) (cons-stream n (integers-from (+ n 1))))")
        interp.run("(define naturals (integers-from 1))")
        interp.run("(define squares (stream-map (lambda (x) (* x x)) naturals))")
        result = interp.run("(stream-take squares 5)")
        assert pairs_to_list(result) == [1, 4, 9, 16, 25]

    def test_stream_filter(self, interp):
        interp.run("(define (integers-from n) (cons-stream n (integers-from (+ n 1))))")
        interp.run("(define naturals (integers-from 1))")
        interp.run("(define evens (stream-filter even? naturals))")
        result = interp.run("(stream-take evens 5)")
        assert pairs_to_list(result) == [2, 4, 6, 8, 10]

    def test_stream_empty(self, interp):
        assert interp.run("(stream-take '() 5)") is Nil or \
               len(pairs_to_list(interp.run("(stream-take '() 5)"))) == 0


# ---------------------------------------------------------------------------
# Set operations tests
# ---------------------------------------------------------------------------

class TestSetOps:
    def test_set_member(self, interp):
        assert interp.run("(set-member 3 '(1 2 3 4))") is TRUE
        assert interp.run("(set-member 5 '(1 2 3 4))") is FALSE

    def test_set_adjoin(self, interp):
        result = interp.run("(set-adjoin 3 '(1 2 3 4))")
        assert pairs_to_list(result) == [1, 2, 3, 4]
        result = interp.run("(set-adjoin 5 '(1 2 3 4))")
        assert pairs_to_list(result) == [5, 1, 2, 3, 4]

    def test_set_union(self, interp):
        result = interp.run("(set-union '(1 2 3) '(3 4 5))")
        assert set(pairs_to_list(result)) == {1, 2, 3, 4, 5}

    def test_set_intersection(self, interp):
        result = interp.run("(set-intersection '(1 2 3 4 5) '(3 4 5 6 7))")
        assert set(pairs_to_list(result)) == {3, 4, 5}

    def test_set_difference(self, interp):
        result = interp.run("(set-difference '(1 2 3 4 5) '(3 4))")
        assert set(pairs_to_list(result)) == {1, 2, 5}


# ---------------------------------------------------------------------------
# New special forms tests
# ---------------------------------------------------------------------------

class TestNewSpecialForms:
    def test_rec(self, interp):
        """rec creates a self-referential value. The name is bound
        within the expression, not in the outer environment."""
        result = interp.run("""
            ((rec fact (lambda (n)
              (if (= n 0) 1 (* n (fact (- n 1))))))
             5)
        """)
        assert result == 120

    def test_rec_with_define(self, interp):
        """rec can be used with define to create recursive functions."""
        result = interp.run("""
            (define fact
              (rec f (lambda (n)
                (if (= n 0) 1 (* n (f (- n 1)))))))
            (fact 5)
        """)
        assert result == 120

    def test_rec_non_function(self, interp):
        result = interp.run("(rec x 42)")
        assert result == 42

    def test_let_values(self, interp):
        result = interp.run("""
            (let-values (((a b) (values 1 2)))
              (+ a b))
        """)
        assert result == 3

    def test_let_values_multiple(self, interp):
        result = interp.run("""
            (let-values (((a b) (values 1 2))
                         ((c d) (values 3 4)))
              (+ a b c d))
        """)
        assert result == 10

    def test_define_values(self, interp):
        interp.run("(define-values (a b c) (values 1 2 3))")
        assert interp.run("a") == 1
        assert interp.run("b") == 2
        assert interp.run("c") == 3

    def test_let_values_single(self, interp):
        """If producer returns a single value, bind it to the first variable."""
        result = interp.run("""
            (let-values (((a) 42))
              a)
        """)
        assert result == 42


# ---------------------------------------------------------------------------
# New builtins tests
# ---------------------------------------------------------------------------

class TestNewBuiltins:
    def test_assert_true(self, interp):
        """Assert with true condition should not raise."""
        assert interp.run("(assert #t)") is Unspecified

    def test_assert_false(self, interp):
        """Assert with false condition should raise."""
        with pytest.raises(SchemeError):
            interp.run("(assert #f)")

    def test_assert_with_message(self, interp):
        """Assert with false condition and message should raise with message."""
        with pytest.raises(SchemeError, match="x must be positive"):
            interp.run('(assert (> -1 0) "x must be positive")')

    def test_time(self, interp):
        """time should evaluate the quoted expression and return its value."""
        result = interp.run("(time '(+ 1 2 3))")
        assert result == 6

    def test_load(self, tmp_path, interp):
        """load should load and evaluate a Scheme file."""
        test_file = tmp_path / "test_load.scm"
        test_file.write_text("(define loaded-value 42)\n")
        interp.run(f'(load "{test_file}")')
        assert interp.run("loaded-value") == 42

    def test_trace(self, interp, capsys):
        """trace should print entry/exit messages."""
        interp.run("(define (f x) (* x 2))")
        interp.run("(trace 'f)")
        result = interp.run("(f 21)")
        captured = capsys.readouterr()
        assert "TRACE:" in captured.err
        assert result == 42

    def test_untrace(self, interp, capsys):
        """untrace should remove tracing."""
        interp.run("(define (f x) (* x 2))")
        interp.run("(trace 'f)")
        interp.run("(f 1)")
        capsys.readouterr()  # clear
        interp.run("(untrace 'f)")
        result = interp.run("(f 21)")
        captured = capsys.readouterr()
        assert "TRACE:" not in captured.err
        assert result == 42

    def test_untrace_not_traced(self, interp):
        """untrace on a non-traced procedure should raise an error."""
        interp.run("(define (f x) x)")
        with pytest.raises(SchemeError):
            interp.run("(untrace 'f)")


# ---------------------------------------------------------------------------
# New primitives tests
# ---------------------------------------------------------------------------

class TestNewPrimitives:
    def test_zip(self, interp):
        result = interp.run("(zip '(1 2 3) '(a b c))")
        items = pairs_to_list(result)
        assert pairs_to_list(items[0]) == [1, Symbol("a")]
        assert pairs_to_list(items[1]) == [2, Symbol("b")]
        assert pairs_to_list(items[2]) == [3, Symbol("c")]

    def test_list_position(self, interp):
        assert interp.run("(list-position odd? '(2 4 6 7 8))") == 3
        assert interp.run("(list-position even? '(1 3 5 7))") is FALSE

    def test_list_count(self, interp):
        assert interp.run("(list-count even? '(1 2 3 4 5 6))") == 3

    def test_for_all(self, interp):
        assert interp.run("(for-all even? '(2 4 6 8))") is TRUE
        assert interp.run("(for-all even? '(2 4 5 8))") is FALSE

    def test_exists(self, interp):
        assert interp.run("(exists odd? '(2 4 6 7 8))") is TRUE
        assert interp.run("(exists odd? '(2 4 6 8))") is FALSE

    def test_string_join(self, interp):
        assert interp.run('(string-join (list "foo" "bar" "baz") ", ")') == "foo, bar, baz"

    def test_string_join_default(self, interp):
        assert interp.run('(string-join (list "foo" "bar"))') == "foo bar"

    def test_string_repeat(self, interp):
        assert interp.run('(string-repeat "ab" 3)') == "ababab"

    def test_string_starts_with(self, interp):
        assert interp.run('(string-starts-with? "foobar" "foo")') is TRUE
        assert interp.run('(string-starts-with? "foobar" "bar")') is FALSE

    def test_string_ends_with(self, interp):
        assert interp.run('(string-ends-with? "foobar" "bar")') is TRUE
        assert interp.run('(string-ends-with? "foobar" "foo")') is FALSE

    def test_string_replace(self, interp):
        assert interp.run('(string-replace "hello world" "world" "scheme")') == "hello scheme"

    def test_sign(self, interp):
        assert interp.run("(sign 5)") == 1
        assert interp.run("(sign -5)") == -1
        assert interp.run("(sign 0)") == 0

    def test_log2(self, interp):
        assert abs(interp.run("(log2 8)") - 3.0) < 1e-10

    def test_log10(self, interp):
        assert abs(interp.run("(log10 1000)") - 3.0) < 1e-10

    def test_hypot(self, interp):
        assert abs(interp.run("(hypot 3 4)") - 5.0) < 1e-10

    def test_eof_object(self, interp):
        result = interp.run("(eof-object)")
        assert interp.run("(eof-object? (eof-object))") is TRUE

    def test_unfold(self, interp):
        result = interp.run("(unfold (lambda (n) (> n 5)) (lambda (n) (+ n 1)) 0)")
        assert pairs_to_list(result) == [0, 1, 2, 3, 4, 5]

    def test_alist_cons(self, interp):
        result = interp.run("(alist-cons 'key 'val '((a . 1)))")
        assert pairs_to_list(result)[0] == Pair(Symbol("key"), Symbol("val"))

    def test_alist_delete(self, interp):
        result = interp.run("(alist-delete 'a '((a . 1) (b . 2) (a . 3)))")
        items = pairs_to_list(result)
        assert len(items) == 1
        assert items[0].car == Symbol("b")


# ---------------------------------------------------------------------------
# Bug fix tests
# ---------------------------------------------------------------------------

class TestBugFixes:
    def test_if_with_or_false(self, interp):
        """Bug: (if (or #f #f) ...) was returning the then-branch because
        _eval_step returned a TailCall which is truthy."""
        result = interp.run("(if (or #f #f) 'then 'else)")
        assert result == Symbol("else")

    def test_if_with_or_true(self, interp):
        result = interp.run("(if (or #f #t) 'then 'else)")
        assert result == Symbol("then")

    def test_if_with_and(self, interp):
        result = interp.run("(if (and #t #t) 'then 'else)")
        assert result == Symbol("then")

    def test_cond_with_or(self, interp):
        result = interp.run("(cond ((or #f #f) 'a) (else 'b))")
        assert result == Symbol("b")

    def test_cond_with_and_true(self, interp):
        result = interp.run("(cond ((and #t #t) 'a) (else 'b))")
        assert result == Symbol("a")

    def test_apply_with_list(self, interp):
        """Bug: apply with a non-Pair last arg was crashing."""
        assert interp.run("(apply + '(1 2 3))") == 6

    def test_apply_with_vector(self, interp):
        result = interp.run("(apply + (vector 1 2 3))")
        assert result == 6

    def test_apply_with_extra_args(self, interp):
        assert interp.run("(apply + 1 2 '(3 4))") == 10

    def test_integer_to_char_returns_char(self, interp):
        """Bug: integer->char was returning str instead of Char in some versions."""
        result = interp.run("(integer->char 65)")
        assert isinstance(result, Char)
        assert result.value == "A"

    def test_eqv_excludes_python_bools(self, interp):
        """Bug: Python bools were being treated as Scheme numbers in eqv?."""
        # This is a regression test — (eqv? #t 1) should be #f
        assert interp.run("(eqv? #t 1)") is FALSE

    def test_equal_cross_type_numeric(self, interp):
        """equal? should handle cross-type numeric comparisons."""
        from fractions import Fraction
        result = interp.run("(equal? 1/1 1)")
        assert result is TRUE


# ---------------------------------------------------------------------------
# No-stdlib tests
# ---------------------------------------------------------------------------

class TestNoStdlib:
    def test_basic_arithmetic_without_stdlib(self, interp_no_stdlib):
        assert interp_no_stdlib.run("(+ 1 2 3)") == 6

    def test_no_stdlib_missing_compose(self, interp_no_stdlib):
        """Without stdlib, compose should not be defined."""
        with pytest.raises(NameError):
            interp_no_stdlib.run("(compose + -)")

    def test_stdlib_loaded_by_default(self, interp):
        """With stdlib loaded, compose should be available."""
        result = interp.run("((compose inc) 5)")
        assert result == 6


# ---------------------------------------------------------------------------
# CLI tests
# ---------------------------------------------------------------------------

class TestCLI:
    def test_cli_eval(self, capsys):
        from scheme_interpreter.cli import main
        ret = main(["-e", "(+ 1 2 3)"])
        captured = capsys.readouterr()
        assert ret == 0
        assert captured.out.strip() == "6"

    def test_cli_version(self, capsys):
        from scheme_interpreter.cli import main
        ret = main(["--version"])
        captured = capsys.readouterr()
        assert ret == 0
        assert "scheme-interpreter" in captured.out

    def test_cli_no_stdlib(self, capsys):
        from scheme_interpreter.cli import main
        ret = main(["--no-stdlib", "-e", "(+ 1 2)"])
        captured = capsys.readouterr()
        assert ret == 0
        assert captured.out.strip() == "3"

    def test_cli_config(self, tmp_path, capsys):
        import json
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({"log_level": "ERROR"}))
        from scheme_interpreter.cli import main
        ret = main(["--config", str(config_file), "-e", "(* 6 7)"])
        captured = capsys.readouterr()
        assert ret == 0
        assert captured.out.strip() == "42"


# ---------------------------------------------------------------------------
# TCO tests with stdlib
# ---------------------------------------------------------------------------

class TestTCOWithStdlib:
    def test_deep_tail_recursion_with_stdlib(self, interp):
        assert interp.run("""
            (define (loop n acc)
              (if (= n 0) acc (loop (- n 1) (+ acc 1))))
            (loop 100000 0)
        """) == 100000

    def test_mutual_recursion_with_stdlib(self, interp):
        result = interp.run("""
            (letrec ((even? (lambda (n) (if (= n 0) #t (odd? (- n 1)))))
                     (odd? (lambda (n) (if (= n 0) #f (even? (- n 1))))))
              (even? 10000))
        """)
        assert result is TRUE


if __name__ == "__main__":
    pytest.main([__file__, "-v"])