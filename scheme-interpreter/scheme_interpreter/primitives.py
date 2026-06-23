"""Primitive (built-in) procedures for the Scheme interpreter.

This module installs 100+ built-in procedures into a global environment.
All primitives are installed as ``Procedure`` objects wrapping Python callables.
"""

from __future__ import annotations

import math
import operator
import random
import sys
import os
from fractions import Fraction
from typing import Any

from .types import (
    Symbol, Pair, Nil, Bool, Char, Vector, Unspecified, EOF, EOFType,
    Procedure, Lambda, Continuation, Macro,
    TRUE, FALSE,
    is_true, to_python_bool, list_to_pairs, pairs_to_list,
    scheme_repr, scheme_display, is_list,
)
from .environment import Environment


def _to_bool(b: bool) -> Bool:
    return TRUE if b else FALSE


def _check_args(name, args, expected_min, expected_max=None):
    n = len(args)
    if n < expected_min or (expected_max is not None and n > expected_max):
        if expected_max is None:
            raise TypeError(f"{name}: expected at least {expected_min} args, got {n}")
        elif expected_min == expected_max:
            raise TypeError(f"{name}: expected {expected_min} args, got {n}")
        else:
            raise TypeError(f"{name}: expected {expected_min}-{expected_max} args, got {n}")


def _num(x):
    """Convert a Scheme number to a Python number."""
    if isinstance(x, bool):
        raise TypeError(f"not a number: {x}")
    if isinstance(x, (int, float, Fraction)):
        return x
    if isinstance(x, Bool):
        raise TypeError(f"not a number: {x}")
    raise TypeError(f"not a number: {scheme_repr(x)}")


def _exact_int(x):
    if isinstance(x, bool):
        raise TypeError("not an integer")
    if isinstance(x, int):
        return x
    if isinstance(x, float):
        if x == int(x):
            return int(x)
        raise TypeError("not an exact integer")
    if isinstance(x, Fraction):
        if x.denominator == 1:
            return x.numerator
        raise TypeError("not an integer")
    raise TypeError(f"not an integer: {scheme_repr(x)}")


def _real(x):
    n = _num(x)
    return float(n)


def _char_val(x):
    if isinstance(x, Char):
        return x.value
    raise TypeError(f"not a character: {scheme_repr(x)}")


def _str_val(x):
    if isinstance(x, str):
        return x
    raise TypeError(f"not a string: {scheme_repr(x)}")


def install_primitives(env: Environment):
    """Install all primitive procedures into *env*."""

    def reg(name, fn):
        env.define(name, Procedure(name, fn))

    # ----- arithmetic -----
    def _add(*args):
        result: Any = 0
        for a in args:
            n = _num(a)
            result = result + n
        return result

    reg("+", _add)

    def _sub(*args):
        if not args:
            raise TypeError("-: expected at least 1 arg")
        if len(args) == 1:
            return -_num(args[0])
        result = _num(args[0])
        for a in args[1:]:
            result = result - _num(a)
        return result

    reg("-", _sub)

    def _mul(*args):
        result: Any = 1
        for a in args:
            result = result * _num(a)
        return result

    reg("*", _mul)

    def _div(*args):
        if not args:
            raise TypeError("/: expected at least 1 arg")
        if len(args) == 1:
            n = _num(args[0])
            if n == 0:
                raise ZeroDivisionError("division by zero")
            return 1 / n if isinstance(n, float) else (Fraction(1, n) if isinstance(n, int) else 1 / n)
        result = _num(args[0])
        for a in args[1:]:
            n = _num(a)
            if n == 0:
                raise ZeroDivisionError("division by zero")
            result = result / n if isinstance(result, float) or isinstance(n, float) else (
                Fraction(result, n) if isinstance(result, int) and isinstance(n, int) else result / n
            )
        return result

    reg("/", _div)

    def _modulo(a, b):
        a = _exact_int(a)
        b = _exact_int(b)
        if b == 0:
            raise ZeroDivisionError("modulo by zero")
        return a % b  # Python's % follows sign of divisor (same as Scheme modulo)

    reg("modulo", _modulo)

    def _remainder(a, b):
        a = _exact_int(a)
        b = _exact_int(b)
        if b == 0:
            raise ZeroDivisionError("remainder by zero")
        # Scheme remainder: sign follows dividend (like C)
        r = abs(a) % abs(b)
        return r if a >= 0 else -r

    reg("remainder", _remainder)

    def _quotient(a, b):
        a = _exact_int(a)
        b = _exact_int(b)
        if b == 0:
            raise ZeroDivisionError("quotient by zero")
        # Scheme quotient truncates toward zero
        q = abs(a) // abs(b)
        if (a < 0) != (b < 0):
            q = -q
        return q

    reg("quotient", _quotient)

    def _abs(x):
        return abs(_num(x))

    reg("abs", _abs)

    def _min(*args):
        if not args:
            raise TypeError("min: expected at least 1 arg")
        return min(_num(a) for a in args)

    reg("min", _min)

    def _max(*args):
        if not args:
            raise TypeError("max: expected at least 1 arg")
        return max(_num(a) for a in args)

    reg("max", _max)

    def _gcd(*args):
        if not args:
            return 0
        result = abs(_exact_int(args[0]))
        for a in args[1:]:
            result = math.gcd(result, abs(_exact_int(a)))
        return result

    reg("gcd", _gcd)

    def _lcm(*args):
        if not args:
            return 1
        result = abs(_exact_int(args[0]))
        for a in args[1:]:
            b = abs(_exact_int(a))
            if result == 0 or b == 0:
                result = 0
            else:
                result = abs(result * b) // math.gcd(result, b)
        return result

    reg("lcm", _lcm)

    def _expt(base, exp):
        b = _num(base)
        e = _num(exp)
        if isinstance(b, int) and isinstance(e, int) and e >= 0:
            return b ** e
        return math.pow(b, e)

    reg("expt", _expt)

    def _sqrt(x):
        n = _num(x)
        if isinstance(n, int) and n >= 0:
            s = math.isqrt(n)
            if s * s == n:
                return s
        return math.sqrt(n)

    reg("sqrt", _sqrt)

    # ----- comparisons -----
    def _make_cmp(op, name):
        def cmp(*args):
            if len(args) < 2:
                return TRUE
            for i in range(len(args) - 1):
                a, b = _num(args[i]), _num(args[i + 1])
                if not op(a, b):
                    return FALSE
            return TRUE
        return cmp

    reg("<", _make_cmp(operator.lt, "<"))
    reg(">", _make_cmp(operator.gt, ">"))
    reg("<=", _make_cmp(operator.le, "<="))
    reg(">=", _make_cmp(operator.ge, ">="))
    reg("=", _make_cmp(operator.eq, "="))

    # ----- predicates -----
    def _number_pred(x):
        return _to_bool(isinstance(x, (int, float, Fraction)) and not isinstance(x, bool))

    reg("number?", _number_pred)

    def _integer_pred(x):
        if isinstance(x, bool):
            return FALSE
        if isinstance(x, int):
            return TRUE
        if isinstance(x, float):
            return _to_bool(x == int(x) if not math.isinf(x) and not math.isnan(x) else False)
        if isinstance(x, Fraction):
            return _to_bool(x.denominator == 1)
        return FALSE

    reg("integer?", _integer_pred)

    def _rational_pred(x):
        return _to_bool(isinstance(x, Fraction) or (isinstance(x, int) and not isinstance(x, bool)))

    reg("rational?", _rational_pred)

    def _real_pred(x):
        return _to_bool(isinstance(x, (int, float, Fraction)) and not isinstance(x, bool))

    reg("real?", _real_pred)

    def _exact_pred(x):
        return _to_bool(isinstance(x, (int, Fraction)) and not isinstance(x, bool))

    reg("exact?", _exact_pred)

    def _inexact_pred(x):
        return _to_bool(isinstance(x, float))

    reg("inexact?", _inexact_pred)

    def _exact_to_inexact(x):
        return float(_num(x))

    reg("exact->inexact", _exact_to_inexact)

    def _inexact_to_exact(x):
        n = _num(x)
        if isinstance(n, float):
            if n == int(n):
                return int(n)
            return Fraction(n).limit_denominator(10**12)
        return n

    reg("inexact->exact", _inexact_to_exact)

    def _exact(x):
        n = _num(x)
        if isinstance(n, float):
            if n == int(n):
                return int(n)
            return Fraction(n).limit_denominator(10**12)
        return n

    reg("exact", _exact)

    def _inexact(x):
        return float(_num(x))

    reg("inexact", _inexact)

    def _zero_pred(x):
        return _to_bool(_num(x) == 0)

    reg("zero?", _zero_pred)

    def _positive_pred(x):
        return _to_bool(_num(x) > 0)

    reg("positive?", _positive_pred)

    def _negative_pred(x):
        return _to_bool(_num(x) < 0)

    reg("negative?", _negative_pred)

    def _odd_pred(x):
        return _to_bool(_exact_int(x) % 2 != 0)

    reg("odd?", _odd_pred)

    def _even_pred(x):
        return _to_bool(_exact_int(x) % 2 == 0)

    reg("even?", _even_pred)

    # ----- pair / list operations -----
    def _cons(a, b):
        return Pair(a, b)

    reg("cons", _cons)

    def _car(p):
        if not isinstance(p, Pair):
            raise TypeError(f"car: not a pair: {scheme_repr(p)}")
        return p.car

    reg("car", _car)

    def _cdr(p):
        if not isinstance(p, Pair):
            raise TypeError(f"cdr: not a pair: {scheme_repr(p)}")
        return p.cdr

    reg("cdr", _cdr)

    # caar, cadr, cdar, cddr, etc.
    def _make_cxr(spec):
        def cxr(p):
            for op in reversed(spec):
                if not isinstance(p, Pair):
                    raise TypeError(f"c{spec}r: not a pair: {scheme_repr(p)}")
                p = p.car if op == "a" else p.cdr
            return p
        return cxr

    for combos in ["aa", "ad", "da", "dd",
                   "aaa", "aad", "ada", "add", "daa", "dad", "dda", "ddd",
                   "aaaa", "aaad", "aada", "aadd", "adaa", "adad", "adda", "addd",
                   "daaa", "daad", "dada", "dadd", "ddaa", "ddad", "ddda", "dddd"]:
        name = "c" + combos + "r"
        reg(name, _make_cxr(combos))

    def _null_pred(x):
        return _to_bool(x is Nil or isinstance(x, type(Nil)))

    reg("null?", _null_pred)

    def _pair_pred(x):
        return _to_bool(isinstance(x, Pair))

    reg("pair?", _pair_pred)

    def _list_pred(x):
        return _to_bool(is_list(x))

    reg("list?", _list_pred)

    def _list(*args):
        return list_to_pairs(list(args))

    reg("list", _list)

    def _length(lst):
        if lst is Nil or isinstance(lst, type(Nil)):
            return 0
        if not isinstance(lst, Pair):
            raise TypeError(f"length: not a list: {scheme_repr(lst)}")
        n = 0
        node = lst
        while isinstance(node, Pair):
            n += 1
            node = node.cdr
        if node is not Nil and not isinstance(node, type(Nil)):
            raise TypeError("length: improper list")
        return n

    reg("length", _length)

    def _reverse(lst):
        result = Nil
        node = lst
        while isinstance(node, Pair):
            result = Pair(node.car, result)
            node = node.cdr
        return result

    reg("reverse", _reverse)

    def _append(*args):
        if not args:
            return Nil
        # All but last must be proper lists; last is appended as-is
        result = args[-1]
        for lst in reversed(args[:-1]):
            items = pairs_to_list(lst)
            for item in reversed(items):
                result = Pair(item, result)
        return result

    reg("append", _append)

    def _list_ref(lst, k):
        k = _exact_int(k)
        node = lst
        for _ in range(k):
            if not isinstance(node, Pair):
                raise IndexError("list-ref: index out of range")
            node = node.cdr
        if not isinstance(node, Pair):
            raise IndexError("list-ref: index out of range")
        return node.car

    reg("list-ref", _list_ref)

    def _list_tail(lst, k):
        k = _exact_int(k)
        node = lst
        for _ in range(k):
            if not isinstance(node, Pair):
                raise IndexError("list-tail: index out of range")
            node = node.cdr
        return node

    reg("list-tail", _list_tail)

    def _member(x, lst):
        from .interpreter import scheme_equal
        node = lst
        while isinstance(node, Pair):
            if scheme_equal(x, node.car):
                return node
            node = node.cdr
        return FALSE

    reg("member", _member)

    def _memv(x, lst):
        from .interpreter import scheme_eqv
        node = lst
        while isinstance(node, Pair):
            if scheme_eqv(x, node.car):
                return node
            node = node.cdr
        return FALSE

    reg("memv", _memv)

    def _memq(x, lst):
        from .interpreter import scheme_eq
        node = lst
        while isinstance(node, Pair):
            if scheme_eq(x, node.car):
                return node
            node = node.cdr
        return FALSE

    reg("memq", _memq)

    def _assoc(x, lst):
        from .interpreter import scheme_equal
        node = lst
        while isinstance(node, Pair):
            pair = node.car
            if isinstance(pair, Pair) and scheme_equal(x, pair.car):
                return pair
            node = node.cdr
        return FALSE

    reg("assoc", _assoc)

    def _assv(x, lst):
        from .interpreter import scheme_eqv
        node = lst
        while isinstance(node, Pair):
            pair = node.car
            if isinstance(pair, Pair) and scheme_eqv(x, pair.car):
                return pair
            node = node.cdr
        return FALSE

    reg("assv", _assv)

    def _assq(x, lst):
        from .interpreter import scheme_eq
        node = lst
        while isinstance(node, Pair):
            pair = node.car
            if isinstance(pair, Pair) and scheme_eq(x, pair.car):
                return pair
            node = node.cdr
        return FALSE

    reg("assq", _assq)

    # ----- vector operations -----
    def _make_vector(k, *fill):
        k = _exact_int(k)
        fill_val = fill[0] if fill else Unspecified
        return Vector([fill_val] * k)

    reg("make-vector", _make_vector)

    def _vector(*args):
        return Vector(list(args))

    reg("vector", _vector)

    def _vector_ref(v, k):
        if not isinstance(v, Vector):
            raise TypeError("vector-ref: not a vector")
        k = _exact_int(k)
        if k < 0 or k >= len(v):
            raise IndexError("vector-ref: index out of range")
        return v.items[k]

    reg("vector-ref", _vector_ref)

    def _vector_set(v, k, val):
        if not isinstance(v, Vector):
            raise TypeError("vector-set!: not a vector")
        k = _exact_int(k)
        if k < 0 or k >= len(v):
            raise IndexError("vector-set!: index out of range")
        v.items[k] = val
        return Unspecified

    reg("vector-set!", _vector_set)

    def _vector_length(v):
        if not isinstance(v, Vector):
            raise TypeError("vector-length: not a vector")
        return len(v)

    reg("vector-length", _vector_length)

    def _vector_to_list(v):
        if not isinstance(v, Vector):
            raise TypeError("vector->list: not a vector")
        return list_to_pairs(v.items)

    reg("vector->list", _vector_to_list)

    def _list_to_vector(lst):
        return Vector(pairs_to_list(lst))

    reg("list->vector", _list_to_vector)

    def _vector_fill(v, val):
        if not isinstance(v, Vector):
            raise TypeError("vector-fill!: not a vector")
        for i in range(len(v)):
            v.items[i] = val
        return Unspecified

    reg("vector-fill!", _vector_fill)

    def _vector_pred(x):
        return _to_bool(isinstance(x, Vector))

    reg("vector?", _vector_pred)

    # ----- string operations -----
    def _string_pred(x):
        return _to_bool(isinstance(x, str))

    reg("string?", _string_pred)

    def _make_string(k, *char_args):
        k = _exact_int(k)
        c = _char_val(char_args[0]) if char_args else " "
        return c * k

    reg("make-string", _make_string)

    def _string(*chars):
        return "".join(_char_val(c) for c in chars)

    reg("string", _string)

    def _string_length(s):
        return len(_str_val(s))

    reg("string-length", _string_length)

    def _string_ref(s, k):
        s = _str_val(s)
        k = _exact_int(k)
        if k < 0 or k >= len(s):
            raise IndexError("string-ref: index out of range")
        return Char(s[k])

    reg("string-ref", _string_ref)

    def _string_set(s, k, c):
        raise TypeError("string-set!: strings are immutable in this implementation")

    reg("string-set!", _string_set)

    def _substring(s, start, *end):
        s = _str_val(s)
        start = _exact_int(start)
        end_val = _exact_int(end[0]) if end else len(s)
        return s[start:end_val]

    reg("substring", _substring)

    def _string_append(*args):
        return "".join(_str_val(a) for a in args)

    reg("string-append", _string_append)

    def _string_to_list(s):
        return list_to_pairs([Char(c) for c in _str_val(s)])

    reg("string->list", _string_to_list)

    def _list_to_string(lst):
        return "".join(_char_val(c) for c in pairs_to_list(lst))

    reg("list->string", _list_to_string)

    def _string_to_number(s, *radix):
        s = _str_val(s)
        r = _exact_int(radix[0]) if radix else 10
        try:
            if r == 10:
                if "/" in s:
                    parts = s.split("/")
                    if len(parts) == 2:
                        return Fraction(int(parts[0]), int(parts[1]))
                if "." in s or "e" in s or "E" in s:
                    return float(s)
                return int(s)
            return int(s, r)
        except (ValueError, ZeroDivisionError):
            return FALSE

    reg("string->number", _string_to_number)

    def _number_to_string(n, *radix):
        n = _num(n)
        r = _exact_int(radix[0]) if radix else 10
        if r == 10:
            if isinstance(n, float):
                if n == int(n) and abs(n) < 1e16:
                    return f"{n:.1f}"
                return repr(n)
            return str(n)
        if isinstance(n, int):
            if r == 2:
                return bin(n)[2:] if n >= 0 else "-" + bin(-n)[2:]
            if r == 8:
                return oct(n)[2:] if n >= 0 else "-" + oct(-n)[2:]
            if r == 16:
                return hex(n)[2:] if n >= 0 else "-" + hex(-n)[2:]
        return str(n)

    reg("number->string", _number_to_string)

    def _string_to_symbol(s):
        return Symbol(_str_val(s))

    reg("string->symbol", _string_to_symbol)

    def _symbol_to_string(s):
        if not isinstance(s, Symbol):
            raise TypeError("symbol->string: not a symbol")
        return s.name

    reg("symbol->string", _symbol_to_string)

    def _symbol_pred(x):
        return _to_bool(isinstance(x, Symbol))

    reg("symbol?", _symbol_pred)

    def _string_eq(*args):
        for i in range(len(args) - 1):
            if _str_val(args[i]) != _str_val(args[i + 1]):
                return FALSE
        return TRUE

    reg("string=?", _string_eq)

    def _string_lt(*args):
        for i in range(len(args) - 1):
            if not (_str_val(args[i]) < _str_val(args[i + 1])):
                return FALSE
        return TRUE

    reg("string<?", _string_lt)

    def _string_gt(*args):
        for i in range(len(args) - 1):
            if not (_str_val(args[i]) > _str_val(args[i + 1])):
                return FALSE
        return TRUE

    reg("string>?", _string_gt)

    def _string_le(*args):
        for i in range(len(args) - 1):
            if not (_str_val(args[i]) <= _str_val(args[i + 1])):
                return FALSE
        return TRUE

    reg("string<=?", _string_le)

    def _string_ge(*args):
        for i in range(len(args) - 1):
            if not (_str_val(args[i]) >= _str_val(args[i + 1])):
                return FALSE
        return TRUE

    reg("string>=?", _string_ge)

    def _string_upcase(s):
        return _str_val(s).upper()

    reg("string-upcase", _string_upcase)

    def _string_downcase(s):
        return _str_val(s).lower()

    reg("string-downcase", _string_downcase)

    def _string_contains(s, sub):
        s = _str_val(s)
        sub = _str_val(sub)
        idx = s.find(sub)
        return idx if idx >= 0 else FALSE

    reg("string-contains", _string_contains)

    def _string_split(s, *sep):
        s = _str_val(s)
        if sep:
            sep_val = _str_val(sep[0])
            parts = s.split(sep_val)
        else:
            parts = s.split()
        return list_to_pairs(parts)

    reg("string-split", _string_split)

    # ----- character operations -----
    def _char_pred(x):
        return _to_bool(isinstance(x, Char))

    reg("char?", _char_pred)

    def _char_to_integer(c):
        return ord(_char_val(c))

    reg("char->integer", _char_to_integer)

    def _integer_to_char(n):
        return Char(chr(_exact_int(n)))  # Bug fix: was returning str, now returns Char

    reg("integer->char", _integer_to_char)

    def _char_eq(a, b):
        return _to_bool(_char_val(a) == _char_val(b))

    reg("char=?", _char_eq)

    def _char_lt(a, b):
        return _to_bool(_char_val(a) < _char_val(b))

    reg("char<?", _char_lt)

    def _char_gt(a, b):
        return _to_bool(_char_val(a) > _char_val(b))

    reg("char>?", _char_gt)

    def _char_le(a, b):
        return _to_bool(_char_val(a) <= _char_val(b))

    reg("char<=?", _char_le)

    def _char_ge(a, b):
        return _to_bool(_char_val(a) >= _char_val(b))

    reg("char>=?", _char_ge)

    def _char_upcase(c):
        return Char(_char_val(c).upper())

    reg("char-upcase", _char_upcase)

    def _char_downcase(c):
        return Char(_char_val(c).lower())

    reg("char-downcase", _char_downcase)

    def _char_alphabetic(c):
        return _to_bool(_char_val(c).isalpha())

    reg("char-alphabetic?", _char_alphabetic)

    def _char_numeric(c):
        return _to_bool(_char_val(c).isdigit())

    reg("char-numeric?", _char_numeric)

    def _char_whitespace(c):
        return _to_bool(_char_val(c).isspace())

    reg("char-whitespace?", _char_whitespace)

    def _char_upper_case(c):
        return _to_bool(_char_val(c).isupper())

    reg("char-upper-case?", _char_upper_case)

    def _char_lower_case(c):
        return _to_bool(_char_val(c).islower())

    reg("char-lower-case?", _char_lower_case)

    # ----- boolean operations -----
    def _boolean_pred(x):
        return _to_bool(isinstance(x, Bool))

    reg("boolean?", _boolean_pred)

    def _not(x):
        return _to_bool(not is_true(x))

    reg("not", _not)

    def _eq_pred(a, b):
        from .interpreter import scheme_eq
        return _to_bool(scheme_eq(a, b))

    reg("eq?", _eq_pred)

    def _eqv_pred(a, b):
        from .interpreter import scheme_eqv
        return _to_bool(scheme_eqv(a, b))

    reg("eqv?", _eqv_pred)

    def _equal_pred(a, b):
        from .interpreter import scheme_equal
        return _to_bool(scheme_equal(a, b))

    reg("equal?", _equal_pred)

    # ----- I/O -----
    def _display(x, *port):
        s = scheme_display(x)
        sys.stdout.write(s)
        return Unspecified

    reg("display", _display)

    def _write(x, *port):
        s = scheme_repr(x)
        sys.stdout.write(s)
        return Unspecified

    reg("write", _write)

    def _write_string(s, *port):
        sys.stdout.write(_str_val(s))
        return Unspecified

    reg("write-string", _write_string)

    def _newline(*port):
        sys.stdout.write("\n")
        return Unspecified

    reg("newline", _newline)

    def _write_char(c, *port):
        sys.stdout.write(_char_val(c))
        return Unspecified

    reg("write-char", _write_char)

    def _read_char(*port):
        c = sys.stdin.read(1)
        return Char(c) if c else EOF

    reg("read-char", _read_char)

    def _read(*port):
        line = sys.stdin.readline()
        if not line:
            return EOF
        from .parser import parse
        forms = parse(line)
        if forms:
            return forms[0]
        return EOF

    reg("read", _read)

    def _read_line(*port):
        line = sys.stdin.readline()
        if not line:
            return EOF
        return line.rstrip("\n")

    reg("read-line", _read_line)

    def _open_input_file(path):
        try:
            f = open(_str_val(path), "r")
            return f
        except OSError as e:
            raise TypeError(f"open-input-file: {e}")

    reg("open-input-file", _open_input_file)

    def _open_output_file(path):
        try:
            f = open(_str_val(path), "w")
            return f
        except OSError as e:
            raise TypeError(f"open-output-file: {e}")

    reg("open-output-file", _open_output_file)

    def _close_port(p):
        if hasattr(p, "close"):
            p.close()
        return Unspecified

    reg("close-port", _close_port)
    reg("close-input-port", _close_port)
    reg("close-output-port", _close_port)

    def _read_from_string(s):
        from .parser import parse
        forms = parse(_str_val(s))
        return forms[0] if forms else EOF

    reg("read-from-string", _read_from_string)

    # ----- transcoding -----
    def _list_to_string_2(lst):
        return "".join(_char_val(c) for c in pairs_to_list(lst))

    # ----- procedures -----
    def _procedure_pred(x):
        return _to_bool(isinstance(x, (Procedure, Lambda)) or callable(x))

    reg("procedure?", _procedure_pred)

    # ----- misc -----
    def _identity(x):
        return x

    reg("identity", _identity)

    def _void(*args):
        return Unspecified

    reg("void", _void)

    def _void_pred(x):
        return _to_bool(x is Unspecified)

    reg("unspecified?", _void_pred)

    def _random(*args):
        if len(args) == 0:
            return random.random()
        if len(args) == 1:
            return random.randint(0, _exact_int(args[0]) - 1)
        return random.randint(_exact_int(args[0]), _exact_int(args[1]) - 1)

    reg("random", _random)

    def _current_second():
        import time
        return time.time()

    reg("current-second", _current_second)

    def _current_jiffy():
        import time
        return int(time.time() * 1000)

    reg("current-jiffy", _current_jiffy)

    def _jiffies_per_second():
        return 1000

    reg("jiffies-per-second", _jiffies_per_second)

    # ----- math functions -----
    for fname in ["sin", "cos", "tan", "asin", "acos", "atan", "log", "exp"]:
        def _make_math(fn_name):
            fn = getattr(math, fn_name)
            def wrapper(*args):
                if len(args) == 1:
                    return fn(_real(args[0]))
                if fn_name == "atan":
                    return math.atan2(_real(args[0]), _real(args[1]))
                if fn_name == "log":
                    return math.log(_real(args[0]), _real(args[1]))
                raise TypeError(f"{fn_name}: wrong number of args")
            return wrapper
        reg(fname, _make_math(fname))

    def _floor(x):
        n = _num(x)
        if isinstance(n, float):
            return math.floor(n)
        return n

    reg("floor", _floor)

    def _ceiling(x):
        n = _num(x)
        if isinstance(n, float):
            return math.ceil(n)
        return n

    reg("ceiling", _ceiling)

    def _round(x):
        n = _num(x)
        if isinstance(n, float):
            return round(n)
        return n

    reg("round", _round)

    def _truncate(x):
        n = _num(x)
        if isinstance(n, float):
            return math.trunc(n)
        return n

    reg("truncate", _truncate)

    def _nan_pred(*args):
        if args:
            return _to_bool(math.isnan(_real(args[0])))
        return math.nan

    reg("nan?", _nan_pred)

    def _infinite_pred(x):
        return _to_bool(math.isinf(_real(x)))

    reg("infinite?", _infinite_pred)

    def _finite_pred(x):
        return _to_bool(math.isfinite(_real(x)))

    reg("finite?", _finite_pred)

    # ----- map / for-each -----
    def _map(proc, *lists):
        from .interpreter import Interpreter
        interp = Interpreter._current if hasattr(Interpreter, '_current') else None
        py_lists = [pairs_to_list(l) for l in lists]
        min_len = min(len(l) for l in py_lists)
        result = []
        for i in range(min_len):
            args = [l[i] for l in py_lists]
            # Find the interpreter to apply proc
            if isinstance(proc, Procedure):
                result.append(proc.fn(*args))
            else:
                # Need interpreter for Lambda — use a global hack
                result.append(_global_apply(proc, args))
        return list_to_pairs(result)

    reg("map", _map)

    def _for_each(proc, *lists):
        py_lists = [pairs_to_list(l) for l in lists]
        min_len = min(len(l) for l in py_lists)
        for i in range(min_len):
            args = [l[i] for l in py_lists]
            if isinstance(proc, Procedure):
                proc.fn(*args)
            else:
                _global_apply(proc, args)
        return Unspecified

    reg("for-each", _for_each)

    def _filter(pred, lst):
        items = pairs_to_list(lst)
        result = []
        for x in items:
            if is_true(_global_apply(pred, [x])):
                result.append(x)
        return list_to_pairs(result)

    reg("filter", _filter)

    def _reduce(proc, init, lst):
        items = pairs_to_list(lst)
        acc = init
        for x in items:
            acc = _global_apply(proc, [acc, x])
        return acc

    reg("reduce", _reduce)

    def _fold_left(proc, init, lst):
        items = pairs_to_list(lst)
        acc = init
        for x in items:
            acc = _global_apply(proc, [acc, x])
        return acc

    reg("fold-left", _fold_left)

    def _fold_right(proc, init, lst):
        items = pairs_to_list(lst)
        acc = init
        for x in reversed(items):
            acc = _global_apply(proc, [x, acc])
        return acc

    reg("fold-right", _fold_right)

    # ----- sort -----
    def _sort(proc, lst):
        from functools import cmp_to_key
        items = pairs_to_list(lst)
        def comparator(a, b):
            if is_true(_global_apply(proc, [a, b])):
                return -1
            elif is_true(_global_apply(proc, [b, a])):
                return 1
            return 0
        items.sort(key=cmp_to_key(comparator))
        return list_to_pairs(items)

    reg("sort", _sort)

    # ----- list operations -----
    def _list_copy(lst):
        if lst is Nil or isinstance(lst, type(Nil)):
            return Nil
        return list_to_pairs(pairs_to_list(lst))

    reg("list-copy", _list_copy)

    def _list_head(lst, k):
        k = _exact_int(k)
        items = pairs_to_list(lst)[:k]
        return list_to_pairs(items)

    reg("list-head", _list_head)

    # ----- eqv? helper -----
    def _eqv_helper(a, b):
        from .interpreter import scheme_eqv
        return _to_bool(scheme_eqv(a, b))

    # ----- environment -----
    def _interaction_environment(*args):
        return env

    reg("interaction-environment", _interaction_environment)

    def _null_environment(*args):
        return Environment()

    reg("null-environment", _null_environment)

    def _scheme_report_environment(*args):
        return env

    reg("scheme-report-environment", _scheme_report_environment)

    # ----- top-level -----
    def _bound_pred(x):
        if not isinstance(x, Symbol):
            return FALSE
        try:
            env.lookup(x.name)
            return TRUE
        except NameError:
            return FALSE

    reg("bound?", _bound_pred)

    def _symbol_to_string_internal(s):
        if isinstance(s, Symbol):
            return s.name
        raise TypeError("not a symbol")

    def _gensym(*args):
        prefix = _str_val(args[0]) if args else "g"
        return Symbol.Gensym(prefix)

    reg("gensym", _gensym)

    def _environment_pred(x):
        return _to_bool(isinstance(x, Environment))

    reg("environment?", _environment_pred)

    # ----- additional list operations -----
    def _list_position(pred, lst):
        """Return the index of the first element satisfying PRED, or #f."""
        idx = 0
        node = lst
        while isinstance(node, Pair):
            if is_true(_global_apply(pred, [node.car])):
                return idx
            idx += 1
            node = node.cdr
        return FALSE

    reg("list-position", _list_position)

    def _list_contains(x, lst):
        """Check if LST contains X (using equal?)."""
        from .interpreter import scheme_equal
        node = lst
        while isinstance(node, Pair):
            if scheme_equal(x, node.car):
                return TRUE
            node = node.cdr
        return FALSE

    reg("list-contains?", _list_contains)

    def _list_count(pred, lst):
        """Count elements in LST that satisfy PRED."""
        count = 0
        node = lst
        while isinstance(node, Pair):
            if is_true(_global_apply(pred, [node.car])):
                count += 1
            node = node.cdr
        return count

    reg("list-count", _list_count)

    def _list_min(pred, lst):
        """Find the minimum element in LST according to PRED (less-than)."""
        if not isinstance(lst, Pair):
            raise TypeError("list-min: empty list")
        best = lst.car
        node = lst.cdr
        while isinstance(node, Pair):
            if is_true(_global_apply(pred, [node.car, best])):
                best = node.car
            node = node.cdr
        return best

    reg("list-min", _list_min)

    def _list_max(pred, lst):
        """Find the maximum element in LST according to PRED (less-than)."""
        if not isinstance(lst, Pair):
            raise TypeError("list-max: empty list")
        best = lst.car
        node = lst.cdr
        while isinstance(node, Pair):
            if is_true(_global_apply(pred, [best, node.car])):
                best = node.car
            node = node.cdr
        return best

    reg("list-max", _list_max)

    def _for_all(pred, lst):
        """Return #t if all elements satisfy PRED."""
        node = lst
        while isinstance(node, Pair):
            if not is_true(_global_apply(pred, [node.car])):
                return FALSE
            node = node.cdr
        return TRUE

    reg("for-all", _for_all)

    def _exists(pred, lst):
        """Return #t if any element satisfies PRED."""
        node = lst
        while isinstance(node, Pair):
            if is_true(_global_apply(pred, [node.car])):
                return TRUE
            node = node.cdr
        return FALSE

    reg("exists", _exists)

    def _zip(*lists):
        """Zip multiple lists together, returning a list of lists."""
        py_lists = [pairs_to_list(l) for l in lists]
        min_len = min(len(l) for l in py_lists) if py_lists else 0
        result = []
        for i in range(min_len):
            result.append(list_to_pairs([l[i] for l in py_lists]))
        return list_to_pairs(result)

    reg("zip", _zip)

    def _unfold(pred, gen, init):
        """Unfold: (unfold pred gen init) builds a list.
        Repeatedly applies gen to init until pred(init) is true."""
        result = []
        val = init
        while not is_true(_global_apply(pred, [val])):
            result.append(val)
            val = _global_apply(gen, [val])
        return list_to_pairs(result)

    reg("unfold", _unfold)

    # ----- additional string operations -----
    def _string_join(lst, *sep):
        """Join a list of strings with SEP (default ' ')."""
        items = pairs_to_list(lst)
        sep_val = _str_val(sep[0]) if sep else " "
        return sep_val.join(_str_val(s) for s in items)

    reg("string-join", _string_join)

    def _string_repeat(s, n):
        """Repeat string S N times."""
        return _str_val(s) * _exact_int(n)

    reg("string-repeat", _string_repeat)

    def _string_starts_with(s, prefix):
        """Check if S starts with PREFIX."""
        return _to_bool(_str_val(s).startswith(_str_val(prefix)))

    reg("string-starts-with?", _string_starts_with)

    def _string_ends_with(s, suffix):
        """Check if S ends with SUFFIX."""
        return _to_bool(_str_val(s).endswith(_str_val(suffix)))

    reg("string-ends-with?", _string_ends_with)

    def _string_replace(s, old, new):
        """Replace all occurrences of OLD with NEW in S."""
        return _str_val(s).replace(_str_val(old), _str_val(new))

    reg("string-replace", _string_replace)

    # ----- additional math operations -----
    def _gcd_list(*args):
        if not args:
            return 0
        result = abs(_exact_int(args[0]))
        for a in args[1:]:
            result = math.gcd(result, abs(_exact_int(a)))
        return result

    # (gcd) already defined above, this is the variadic version

    def _sign(x):
        """Return -1, 0, or 1 based on the sign of X."""
        n = _num(x)
        if n > 0:
            return 1
        elif n < 0:
            return -1
        return 0

    reg("sign", _sign)

    def _degrees_to_radians(x):
        return math.radians(_real(x))

    reg("degrees->radians", _degrees_to_radians)

    def _radians_to_degrees(x):
        return math.degrees(_real(x))

    reg("radians->degrees", _radians_to_degrees)

    def _log2(x):
        return math.log2(_real(x))

    reg("log2", _log2)

    def _log10(x):
        return math.log10(_real(x))

    reg("log10", _log10)

    def _hypot(*args):
        return math.hypot(*[_real(a) for a in args])

    reg("hypot", _hypot)

    def _atan2(y, x):
        return math.atan2(_real(y), _real(x))

    reg("atan2", _atan2)

    # ----- type predicates -----
    def _eof_pred(x):
        return _to_bool(x is EOF or isinstance(x, EOFType))

    reg("eof-object?", _eof_pred)

    def _eof_object():
        return EOF

    reg("eof-object", _eof_object)


# Global reference for applying lambdas from primitives
_global_interpreter = None

def set_global_interpreter(interp):
    global _global_interpreter
    _global_interpreter = interp

def _global_apply(proc, args):
    """Apply a procedure using the global interpreter (if set)."""
    global _global_interpreter
    if isinstance(proc, Procedure):
        return proc.fn(*args)
    if _global_interpreter is not None:
        return _global_interpreter._apply(proc, args)
    raise RuntimeError("no interpreter available for applying lambda from primitive")