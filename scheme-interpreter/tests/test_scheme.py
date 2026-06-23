"""Comprehensive test suite for the Scheme interpreter."""

import pytest
from scheme_interpreter.interpreter import Interpreter, SchemeError
from scheme_interpreter.primitives import set_global_interpreter
from scheme_interpreter.types import (
    Symbol, Pair, Nil, Bool, Char, Vector, Unspecified,
    TRUE, FALSE, scheme_repr, scheme_display,
    list_to_pairs, pairs_to_list, is_list,
)
from scheme_interpreter.lexer import tokenize, LexError
from scheme_interpreter.parser import parse, ParseError


@pytest.fixture
def interp():
    i = Interpreter()
    set_global_interpreter(i)
    return i


class TestLexer:
    def test_integers(self):
        toks = tokenize("42 0 -7 +100")
        assert toks[0].value == 42
        assert toks[1].value == 0
        assert toks[2].value == -7
        assert toks[3].value == 100

    def test_floats(self):
        toks = tokenize("3.14 -0.5 1e10")
        assert toks[0].value == 3.14
        assert toks[1].value == -0.5
        assert toks[2].value == 1e10

    def test_strings(self):
        toks = tokenize('"hello world"')
        assert toks[0].value == "hello world"

    def test_escaped_strings(self):
        toks = tokenize(r'"hello\nworld\t"')
        assert toks[0].value == "hello\nworld\t"

    def test_booleans(self):
        toks = tokenize("#t #f #true #false")
        assert toks[0].value == True
        assert toks[1].value == False
        assert toks[2].value == True
        assert toks[3].value == False

    def test_chars(self):
        toks = tokenize("#\\a #\\space #\\newline")
        assert toks[0].value == "a"
        assert toks[1].value == " "
        assert toks[2].value == "\n"

    def test_symbols(self):
        toks = tokenize("foo bar + - * / -> foo?")
        assert all(t.type == "SYMBOL" for t in toks)

    def test_quote(self):
        toks = tokenize("'x")
        assert toks[0].type == "QUOTE"

    def test_quasiquote(self):
        toks = tokenize("`x ,x ,@x")
        assert toks[0].type == "QUASIQUOTE"
        assert toks[2].type == "UNQUOTE"
        assert toks[4].type == "UNQUOTE_SPLICING"

    def test_comments(self):
        toks = tokenize("; this is a comment\n42")
        assert toks[0].value == 42

    def test_block_comments(self):
        toks = tokenize("#| block comment |# 42")
        assert toks[0].value == 42

    def test_rationals(self):
        toks = tokenize("3/4")
        from fractions import Fraction
        assert toks[0].value == Fraction(3, 4)

    def test_binary_numbers(self):
        toks = tokenize("#b1010")
        assert toks[0].value == 10

    def test_hex_numbers(self):
        toks = tokenize("#xff")
        assert toks[0].value == 255

    def test_octal_numbers(self):
        toks = tokenize("#o17")
        assert toks[0].value == 15


class TestParser:
    def test_parse_atom(self):
        forms = parse("42")
        assert forms == [42]

    def test_parse_list(self):
        forms = parse("(1 2 3)")
        assert isinstance(forms[0], Pair)
        assert pairs_to_list(forms[0]) == [1, 2, 3]

    def test_parse_nested(self):
        forms = parse("(1 (2 3) 4)")
        items = pairs_to_list(forms[0])
        assert items[0] == 1
        assert pairs_to_list(items[1]) == [2, 3]
        assert items[2] == 4

    def test_parse_quote(self):
        forms = parse("'x")
        items = pairs_to_list(forms[0])
        assert items[0] == Symbol("quote")
        assert items[1] == Symbol("x")

    def test_parse_dotted(self):
        forms = parse("(1 2 . 3)")
        p = forms[0]
        assert p.car == 1
        assert p.cdr.car == 2
        assert p.cdr.cdr == 3

    def test_parse_string(self):
        forms = parse('"hello"')
        assert forms[0] == "hello"

    def test_parse_vector(self):
        forms = parse("#(1 2 3)")
        assert isinstance(forms[0], Vector)
        assert forms[0].items == [1, 2, 3]

    def test_parse_multiple_forms(self):
        forms = parse("1 2 3")
        assert len(forms) == 3


class TestArithmetic:
    def test_add(self, interp):
        assert interp.run("(+ 1 2 3)") == 6

    def test_sub(self, interp):
        assert interp.run("(- 10 3)") == 7
        assert interp.run("(- 5)") == -5

    def test_mul(self, interp):
        assert interp.run("(* 2 3 4)") == 24

    def test_div(self, interp):
        assert interp.run("(/ 12 4)") == 3

    def test_rational_div(self, interp):
        from fractions import Fraction
        assert interp.run("(/ 1 3)") == Fraction(1, 3)

    def test_modulo(self, interp):
        assert interp.run("(modulo 7 3)") == 1
        assert interp.run("(modulo -7 3)") == 2

    def test_remainder(self, interp):
        assert interp.run("(remainder 7 3)") == 1
        assert interp.run("(remainder -7 3)") == -1

    def test_quotient(self, interp):
        assert interp.run("(quotient 7 3)") == 2
        assert interp.run("(quotient -7 3)") == -2

    def test_abs(self, interp):
        assert interp.run("(abs -5)") == 5

    def test_min_max(self, interp):
        assert interp.run("(min 3 1 2)") == 1
        assert interp.run("(max 3 1 2)") == 3

    def test_expt(self, interp):
        assert interp.run("(expt 2 10)") == 1024

    def test_sqrt(self, interp):
        assert interp.run("(sqrt 16)") == 4
        assert abs(interp.run("(sqrt 2)") - 1.4142135623730951) < 1e-10

    def test_gcd_lcm(self, interp):
        assert interp.run("(gcd 12 18)") == 6
        assert interp.run("(lcm 4 6)") == 12

    def test_comparisons(self, interp):
        assert interp.run("(< 1 2 3)") is TRUE
        assert interp.run("(< 1 3 2)") is FALSE
        assert interp.run("(> 3 2 1)") is TRUE
        assert interp.run("(<= 1 1 2)") is TRUE
        assert interp.run("(>= 3 3 2)") is TRUE
        assert interp.run("(= 1 1 1)") is TRUE


class TestPredicates:
    def test_number_pred(self, interp):
        assert interp.run("(number? 42)") is TRUE
        assert interp.run("(number? 'foo)") is FALSE

    def test_integer_pred(self, interp):
        assert interp.run("(integer? 42)") is TRUE
        assert interp.run("(integer? 3.14)") is FALSE

    def test_zero_pred(self, interp):
        assert interp.run("(zero? 0)") is TRUE
        assert interp.run("(zero? 1)") is FALSE

    def test_odd_even(self, interp):
        assert interp.run("(odd? 3)") is TRUE
        assert interp.run("(even? 4)") is TRUE

    def test_null_pred(self, interp):
        assert interp.run("(null? '())") is TRUE
        assert interp.run("(null? '(1))") is FALSE

    def test_pair_pred(self, interp):
        assert interp.run("(pair? '(1))") is TRUE
        assert interp.run("(pair? '())") is FALSE

    def test_boolean_pred(self, interp):
        assert interp.run("(boolean? #t)") is TRUE
        assert interp.run("(boolean? 1)") is FALSE

    def test_procedure_pred(self, interp):
        assert interp.run("(procedure? car)") is TRUE
        assert interp.run("(procedure? (lambda (x) x))") is TRUE


class TestSpecialForms:
    def test_define(self, interp):
        interp.run("(define x 42)")
        assert interp.run("x") == 42

    def test_define_function(self, interp):
        interp.run("(define (f x) (* x x))")
        assert interp.run("(f 5)") == 25

    def test_lambda(self, interp):
        assert interp.run("((lambda (x y) (+ x y)) 3 4)") == 7

    def test_variadic_lambda(self, interp):
        assert interp.run("((lambda args args) 1 2 3)") == list_to_pairs([1, 2, 3])

    def test_if_true(self, interp):
        assert interp.run("(if #t 1 2)") == 1

    def test_if_false(self, interp):
        assert interp.run("(if #f 1 2)") == 2

    def test_begin(self, interp):
        assert interp.run("(begin 1 2 3)") == 3

    def test_let(self, interp):
        assert interp.run("(let ((a 1) (b 2)) (+ a b))") == 3

    def test_let_star(self, interp):
        assert interp.run("(let* ((a 1) (b (+ a 1))) (+ a b))") == 3

    def test_letrec(self, interp):
        result = interp.run("(letrec ((f (lambda (n) (if (= n 0) 1 (* n (f (- n 1))))))) (f 5))")
        assert result == 120

    def test_named_let(self, interp):
        assert interp.run("(let loop ((i 0) (acc 0)) (if (= i 10) acc (loop (+ i 1) (+ acc i))))") == 45

    def test_cond(self, interp):
        assert interp.run("(cond (#f 1) (#t 2) (else 3))") == 2
        assert interp.run("(cond (#f 1) (#f 2) (else 3))") == 3

    def test_cond_with_arrow(self, interp):
        assert interp.run("(cond (#t => (lambda (x) x)))") is TRUE

    def test_case(self, interp):
        assert interp.run("(case 2 ((1) 'one) ((2) 'two) (else 'other))") == Symbol("two")

    def test_and(self, interp):
        assert interp.run("(and 1 2 3)") == 3
        assert interp.run("(and 1 #f 3)") is FALSE

    def test_or(self, interp):
        assert interp.run("(or #f 42)") == 42
        assert interp.run("(or #f #f)") is FALSE

    def test_when(self, interp):
        assert interp.run("(when #t 42)") == 42
        assert interp.run("(when #f 42)") is Unspecified

    def test_unless(self, interp):
        assert interp.run("(unless #f 42)") == 42
        assert interp.run("(unless #t 42)") is Unspecified

    def test_do(self, interp):
        assert interp.run("(do ((i 0 (+ i 1)) (s 0 (+ s i))) ((= i 5) s))") == 10

    def test_set_bang(self, interp):
        interp.run("(define x 1) (set! x 42)")
        assert interp.run("x") == 42

    def test_quasiquote(self, interp):
        result = interp.run("`(1 2 ,(+ 1 2))")
        assert pairs_to_list(result) == [1, 2, 3]

    def test_quasiquote_splicing(self, interp):
        result = interp.run("`(1 ,@(list 2 3) 4)")
        assert pairs_to_list(result) == [1, 2, 3, 4]

    def test_delay_force(self, interp):
        assert interp.run("(force (delay (+ 1 2)))") == 3


class TestTCO:
    def test_deep_tail_recursion(self, interp):
        assert interp.run("(define (loop n acc) (if (= n 0) acc (loop (- n 1) (+ acc 1)))) (loop 100000 0)") == 100000

    def test_deep_tail_recursion_1m(self, interp):
        assert interp.run("(define (loop n acc) (if (= n 0) acc (loop (- n 1) (+ acc 1)))) (loop 1000000 0)") == 1000000

    def test_mutual_tail_recursion(self, interp):
        result = interp.run("""
            (letrec ((even? (lambda (n) (if (= n 0) #t (odd? (- n 1)))))
                     (odd? (lambda (n) (if (= n 0) #f (even? (- n 1))))))
              (even? 10000))
        """)
        assert result is TRUE

    def test_named_let_tco(self, interp):
        assert interp.run("(let loop ((i 0)) (if (= i 100000) 'done (loop (+ i 1))))") == Symbol("done")


class TestCallCC:
    def test_basic_callcc(self, interp):
        assert interp.run("(call/cc (lambda (k) (+ 1 (k 42))))") == 42

    def test_callcc_no_escape(self, interp):
        assert interp.run("(call/cc (lambda (k) 42))") == 42

    def test_callcc_addition(self, interp):
        assert interp.run("(+ 1 (call/cc (lambda (k) (+ 2 (k 10)))))") == 11

    def test_callcc_early_return(self, interp):
        result = interp.run("""
            (define (find pred lst)
              (call/cc
                (lambda (k)
                  (for-each (lambda (x) (if (pred x) (k x) #f)) lst)
                  #f)))
            (find even? '(1 3 5 6 7))
        """)
        assert result == 6

    def test_callcc_nested(self, interp):
        assert interp.run("(call/cc (lambda (k) (call/cc (lambda (j) (k 42)))))") == 42


class TestListOperations:
    def test_cons(self, interp):
        result = interp.run("(cons 1 2)")
        assert result.car == 1
        assert result.cdr == 2

    def test_car_cdr(self, interp):
        assert interp.run("(car '(1 2 3))") == 1
        assert interp.run("(cdr '(1 2 3))") is not Nil

    def test_cadr(self, interp):
        assert interp.run("(cadr '(1 2 3))") == 2

    def test_caddr(self, interp):
        assert interp.run("(caddr '(1 2 3))") == 3

    def test_list(self, interp):
        assert pairs_to_list(interp.run("(list 1 2 3)")) == [1, 2, 3]

    def test_length(self, interp):
        assert interp.run("(length '(1 2 3 4))") == 4
        assert interp.run("(length '())") == 0

    def test_reverse(self, interp):
        assert pairs_to_list(interp.run("(reverse '(1 2 3))")) == [3, 2, 1]

    def test_append(self, interp):
        assert pairs_to_list(interp.run("(append '(1 2) '(3 4))")) == [1, 2, 3, 4]

    def test_list_ref(self, interp):
        assert interp.run("(list-ref '(a b c d) 2)") == Symbol("c")

    def test_member(self, interp):
        result = interp.run("(member 3 '(1 2 3 4))")
        assert isinstance(result, Pair)

    def test_assoc(self, interp):
        result = interp.run("(assoc 'b '((a 1) (b 2) (c 3)))")
        assert pairs_to_list(result) == [Symbol("b"), 2]

    def test_map(self, interp):
        result = interp.run("(map (lambda (x) (* x x)) '(1 2 3 4))")
        assert pairs_to_list(result) == [1, 4, 9, 16]

    def test_for_each(self, interp):
        # for-each returns unspecified, just make sure it runs
        assert interp.run("(for-each display '())") is Unspecified

    def test_filter(self, interp):
        result = interp.run("(filter (lambda (x) (> x 2)) '(1 2 3 4 5))")
        assert pairs_to_list(result) == [3, 4, 5]

    def test_fold_right(self, interp):
        assert interp.run("(fold-right + 0 '(1 2 3 4 5))") == 15


class TestStringOperations:
    def test_string_length(self, interp):
        assert interp.run('(string-length "hello")') == 5

    def test_string_append(self, interp):
        assert interp.run('(string-append "foo" "bar")') == "foobar"

    def test_substring(self, interp):
        assert interp.run('(substring "hello world" 0 5)') == "hello"

    def test_string_to_number(self, interp):
        assert interp.run('(string->number "42")') == 42
        assert interp.run('(string->number "3.14")') == 3.14

    def test_number_to_string(self, interp):
        assert interp.run('(number->string 42)') == "42"

    def test_string_to_symbol(self, interp):
        assert interp.run('(string->symbol "foo")') == Symbol("foo")

    def test_symbol_to_string(self, interp):
        assert interp.run("(symbol->string 'foo)") == "foo"

    def test_string_eq(self, interp):
        assert interp.run('(string=? "abc" "abc")') is TRUE
        assert interp.run('(string=? "abc" "abd")') is FALSE


class TestCharOperations:
    def test_char_to_integer(self, interp):
        assert interp.run("(char->integer #\\A)") == 65

    def test_integer_to_char(self, interp):
        assert interp.run("(integer->char 65)") == Char("A")

    def test_char_eq(self, interp):
        assert interp.run("(char=? #\\a #\\a)") is TRUE

    def test_char_lt(self, interp):
        assert interp.run("(char<? #\\a #\\b)") is TRUE

    def test_char_alphabetic(self, interp):
        assert interp.run("(char-alphabetic? #\\a)") is TRUE
        assert interp.run("(char-alphabetic? #\\1)") is FALSE


class TestVectorOperations:
    def test_make_vector(self, interp):
        result = interp.run("(make-vector 3 0)")
        assert isinstance(result, Vector)
        assert result.items == [0, 0, 0]

    def test_vector_ref(self, interp):
        assert interp.run("(vector-ref (vector 1 2 3) 1)") == 2

    def test_vector_length(self, interp):
        assert interp.run("(vector-length (vector 1 2 3))") == 3

    def test_vector_to_list(self, interp):
        assert pairs_to_list(interp.run("(vector->list (vector 1 2 3))")) == [1, 2, 3]

    def test_list_to_vector(self, interp):
        result = interp.run("(list->vector '(1 2 3))")
        assert result.items == [1, 2, 3]


class TestClosures:
    def test_counter(self, interp):
        result = interp.run("""
            (define (make-counter)
              (let ((c 0))
                (lambda () (set! c (+ c 1)) c)))
            (define c (make-counter))
            (c) (c) (c)
        """)
        assert result == 3

    def test_adder(self, interp):
        result = interp.run("""
            (define (make-adder n)
              (lambda (x) (+ x n)))
            (define add5 (make-adder 5))
            (add5 10)
        """)
        assert result == 15


class TestMacros:
    def test_simple_macro(self, interp):
        assert interp.run("(define-syntax my-if (syntax-rules () ((my-if t a b) (if t a b)))) (my-if #t 42 99)") == 42

    def test_swap_macro(self, interp):
        result = interp.run("""
            (define-syntax swap!
              (syntax-rules ()
                ((swap! a b) (let ((tmp a)) (set! a b) (set! b tmp)))))
            (define x 1) (define y 2) (swap! x y) (list x y)
        """)
        assert pairs_to_list(result) == [2, 1]

    def test_ellipsis_macro(self, interp):
        result = interp.run("""
            (define-syntax my-list
              (syntax-rules ()
                ((my-list x ...) (list x ...))))
            (my-list 1 2 3 4)
        """)
        assert pairs_to_list(result) == [1, 2, 3, 4]

    def test_while_macro(self, interp):
        result = interp.run("""
            (define-syntax while
              (syntax-rules ()
                ((while test body ...)
                 (let loop () (if test (begin body ... (loop)) #f)))))
            (define i 0) (define s 0)
            (while (< i 5) (set! s (+ s i)) (set! i (+ i 1)))
            s
        """)
        assert result == 10

    def test_macro_with_literals(self, interp):
        result = interp.run("""
            (define-syntax for
              (syntax-rules (in)
                ((for var in lst body ...)
                 (for-each (lambda (var) body ...) lst))))
            (let ((result '()))
              (for x in (list 1 2 3) (set! result (cons x result)))
              (reverse result))
        """)
        assert pairs_to_list(result) == [1, 2, 3]


class TestErrorHandling:
    def test_error_procedure(self, interp):
        with pytest.raises(SchemeError):
            interp.run("(error \"something went wrong\")")

    def test_unbound_variable(self, interp):
        with pytest.raises(NameError):
            interp.run("undefined-variable")

    def test_car_of_non_pair(self, interp):
        with pytest.raises(TypeError):
            interp.run("(car 42)")

    def test_division_by_zero(self, interp):
        with pytest.raises(ZeroDivisionError):
            interp.run("(/ 1 0)")


class TestEqPredicates:
    def test_eqv(self, interp):
        assert interp.run("(eqv? 1 1)") is TRUE
        assert interp.run("(eqv? 1 2)") is FALSE
        assert interp.run("(eqv? 'a 'a)") is TRUE

    def test_eq(self, interp):
        assert interp.run("(eq? 'a 'a)") is TRUE
        assert interp.run("(eq? '() '())") is TRUE

    def test_equal(self, interp):
        assert interp.run("(equal? '(1 2 3) '(1 2 3))") is TRUE
        assert interp.run("(equal? \"abc\" \"abc\")") is TRUE
        assert interp.run("(equal? '(1 2) '(1 3))") is FALSE


class TestTypes:
    def test_symbol_interning(self):
        a = Symbol("foo")
        b = Symbol("foo")
        assert a is b

    def test_nil_singleton(self):
        from scheme_interpreter.types import Nil
        assert Nil is Nil

    def test_scheme_repr(self):
        assert scheme_repr(42) == "42"
        assert scheme_repr("hello") == '"hello"'
        assert scheme_repr(Symbol("foo")) == "foo"
        assert scheme_repr(TRUE) == "#t"
        assert scheme_repr(FALSE) == "#f"

    def test_scheme_display(self):
        assert scheme_display("hello") == "hello"
        assert scheme_display(42) == "42"

    def test_is_list(self):
        assert is_list(Nil) is True
        assert is_list(list_to_pairs([1, 2, 3])) is True
        assert is_list(42) is False


class TestIO:
    def test_display(self, interp, capsys):
        interp.run('(display "hello")')
        captured = capsys.readouterr()
        assert captured.out == "hello"

    def test_newline(self, interp, capsys):
        interp.run("(newline)")
        captured = capsys.readouterr()
        assert captured.out == "\n"

    def test_write(self, interp, capsys):
        interp.run('(write "hello")')
        captured = capsys.readouterr()
        assert captured.out == '"hello"'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])