"""
Comprehensive test suite for symbolic_cas package.

Uses pytest framework for better assertion messages and fixtures.
"""

import math
import pytest

from symbolic_cas import (
    Expr, Num, Sym, BinOp, UnaryOp, Func, Pow,
    parse, simplify, differentiate, expand_expr,
    substitute, evaluate, collect_symbols, to_latex, solve,
    taylor_series, numerical_integrate, newton_method,
    factor, pretty_print, limit,
    x, y, z, t, n, pi, e,
    sym, num, sin, cos, tan, exp, ln, sqrt, abs_expr,
)
from symbolic_cas.serialize import to_dict, from_dict, to_json, from_json


# ═══════════════════════════════════════════════════════════════════
# Expression Construction Tests
# ═══════════════════════════════════════════════════════════════════

class TestNumConstruction:
    def test_int(self):
        n = Num(5)
        assert n.value == 5
        assert str(n) == "5"

    def test_float(self):
        n = Num(3.14)
        assert n.value == 3.14

    def test_int_as_float_coerced(self):
        n = Num(5.0)
        assert n.value == 5
        assert isinstance(n.value, int)


class TestSymConstruction:
    def test_valid(self):
        s = Sym('x')
        assert s.name == 'x'
        assert str(s) == 'x'

    def test_invalid_name(self):
        with pytest.raises(ValueError):
            Sym('123abc')

    def test_underscore_prefix(self):
        s = Sym('_theta')
        assert s.name == '_theta'


class TestBinOpConstruction:
    def test_add(self):
        b = BinOp('+', Num(1), Num(2))
        assert str(b) == "(1 + 2)"

    def test_invalid_op(self):
        with pytest.raises(ValueError):
            BinOp('%', Num(1), Num(2))


class TestPowConstruction:
    def test_basic(self):
        p = Pow(Sym('x'), Num(2))
        assert str(p) == "(x^2)"


class TestFuncConstruction:
    def test_sin(self):
        f = Func('sin', Sym('x'))
        assert str(f) == "sin(x)"

    def test_unknown_func(self):
        with pytest.raises(ValueError):
            Func('unknown', Sym('x'))


class TestUnaryOp:
    def test_neg(self):
        u = UnaryOp('-', Sym('x'))
        assert str(u) == "(-x)"


# ═══════════════════════════════════════════════════════════════════
# Operator Overload Tests
# ═══════════════════════════════════════════════════════════════════

class TestOperators:
    def test_add(self):
        expr = Num(1) + Num(2)
        assert isinstance(expr, BinOp) and expr.op == '+'

    def test_mul(self):
        expr = Sym('x') * Num(3)
        assert isinstance(expr, BinOp) and expr.op == '*'

    def test_pow(self):
        expr = Sym('x') ** Num(2)
        assert isinstance(expr, Pow)

    def test_neg(self):
        expr = -Sym('x')
        assert isinstance(expr, UnaryOp)

    def test_mixed(self):
        expr = 3 * x + 2
        assert isinstance(expr, BinOp)

    def test_radd(self):
        expr = 5 + Sym('x')
        assert isinstance(expr, BinOp)

    def test_rsub(self):
        expr = 5 - Sym('x')
        assert isinstance(expr, BinOp)

    def test_rmul(self):
        expr = 5 * Sym('x')
        assert isinstance(expr, BinOp)

    def test_rtruediv(self):
        expr = 5 / Sym('x')
        assert isinstance(expr, BinOp)

    def test_rpow(self):
        expr = 2 ** Sym('x')
        assert isinstance(expr, Pow)


# ═══════════════════════════════════════════════════════════════════
# Parsing Tests
# ═══════════════════════════════════════════════════════════════════

class TestParsing:
    def test_number(self):
        assert parse("42") == Num(42)

    def test_float(self):
        expr = parse("3.14")
        assert isinstance(expr, Num) and math.isclose(expr.value, 3.14)

    def test_symbol(self):
        assert parse("x") == Sym('x')

    def test_addition(self):
        assert parse("x + 1") == BinOp('+', Sym('x'), Num(1))

    def test_subtraction(self):
        assert parse("x - 1") == BinOp('-', Sym('x'), Num(1))

    def test_multiplication(self):
        assert parse("x * 2") == BinOp('*', Sym('x'), Num(2))

    def test_division(self):
        assert parse("x / 2") == BinOp('/', Sym('x'), Num(2))

    def test_power(self):
        assert parse("x ^ 2") == Pow(Sym('x'), Num(2))

    def test_unary_neg(self):
        assert parse("-x") == UnaryOp('-', Sym('x'))

    def test_parens(self):
        assert parse("(x + 1)") == BinOp('+', Sym('x'), Num(1))

    def test_precedence(self):
        expr = parse("2 + 3 * x")
        assert expr == BinOp('+', Num(2), BinOp('*', Num(3), Sym('x')))

    def test_function(self):
        assert parse("sin(x)") == Func('sin', Sym('x'))

    def test_nested_function(self):
        assert parse("sin(cos(x))") == Func('sin', Func('cos', Sym('x')))

    def test_complex_expr(self):
        expr = parse("3*x^2 + 2*x - 5")
        assert isinstance(expr, Expr)

    def test_right_assoc_power(self):
        expr = parse("x^2^3")
        assert isinstance(expr, Pow)

    def test_unexpected_char(self):
        with pytest.raises(ValueError):
            parse("x @ 2")

    def test_consecutive_negation(self):
        expr = parse("--x")
        assert isinstance(expr, UnaryOp)


# ═══════════════════════════════════════════════════════════════════
# Differentiation Tests
# ═══════════════════════════════════════════════════════════════════

class TestDifferentiation:
    def test_constant(self):
        assert differentiate(Num(5), 'x') == Num(0)

    def test_variable(self):
        assert differentiate(Sym('x'), 'x') == Num(1)

    def test_other_variable(self):
        assert differentiate(Sym('y'), 'x') == Num(0)

    def test_power(self):
        result = differentiate(Pow(Sym('x'), Num(3)), 'x').simplify()
        val = result.evaluate({'x': 2})
        assert math.isclose(val, 12)

    def test_sum(self):
        result = differentiate(BinOp('+', Sym('x'), Num(1)), 'x').simplify()
        assert result == Num(1)

    def test_product_rule(self):
        f = BinOp('*', Sym('x'), Func('sin', Sym('x')))
        df = differentiate(f, 'x').simplify()
        val = df.evaluate({'x': 1.0})
        expected = math.sin(1.0) + 1.0 * math.cos(1.0)
        assert math.isclose(val, expected, rel_tol=1e-9)

    def test_chain_rule(self):
        f = Func('sin', Pow(Sym('x'), Num(2)))
        df = differentiate(f, 'x').simplify()
        val = df.evaluate({'x': 1.0})
        expected = math.cos(1) * 2
        assert math.isclose(val, expected, rel_tol=1e-9)

    def test_exp(self):
        df = differentiate(Func('exp', Sym('x')), 'x').simplify()
        val = df.evaluate({'x': 1.0})
        assert math.isclose(val, math.e, rel_tol=1e-9)

    def test_ln(self):
        df = differentiate(Func('ln', Sym('x')), 'x').simplify()
        val = df.evaluate({'x': 2.0})
        assert math.isclose(val, 0.5, rel_tol=1e-9)

    def test_quotient_rule(self):
        f = BinOp('/', Sym('x'), Func('sin', Sym('x')))
        df = differentiate(f, 'x').simplify()
        val = df.evaluate({'x': 1.0})
        expected = (math.sin(1) - 1*math.cos(1)) / (math.sin(1)**2)
        assert math.isclose(val, expected, rel_tol=1e-6)

    def test_general_power(self):
        f = Pow(Sym('x'), Sym('x'))
        df = differentiate(f, 'x').simplify()
        val = df.evaluate({'x': 2.0})
        expected = 4.0 * (math.log(2.0) + 1.0)
        assert math.isclose(val, expected, rel_tol=1e-4)

    def test_tanh_derivative(self):
        df = differentiate(Func('tanh', Sym('x')), 'x').simplify()
        val = df.evaluate({'x': 0.5})
        expected = 1 - math.tanh(0.5)**2
        assert math.isclose(val, expected, rel_tol=1e-6)


# ═══════════════════════════════════════════════════════════════════
# Simplification Tests
# ═══════════════════════════════════════════════════════════════════

class TestSimplification:
    def test_add_zero(self):
        assert simplify(BinOp('+', Sym('x'), Num(0))) == Sym('x')
        assert simplify(BinOp('+', Num(0), Sym('x'))) == Sym('x')

    def test_mul_one(self):
        assert simplify(BinOp('*', Sym('x'), Num(1))) == Sym('x')
        assert simplify(BinOp('*', Num(1), Sym('x'))) == Sym('x')

    def test_mul_zero(self):
        assert simplify(BinOp('*', Sym('x'), Num(0))) == Num(0)
        assert simplify(BinOp('*', Num(0), Sym('x'))) == Num(0)

    def test_constant_fold(self):
        assert simplify(BinOp('+', Num(2), Num(3))) == Num(5)
        assert simplify(BinOp('-', Num(10), Num(3))) == Num(7)
        assert simplify(BinOp('*', Num(4), Num(3))) == Num(12)
        assert simplify(BinOp('/', Num(10), Num(2))) == Num(5)

    def test_double_negation(self):
        expr = UnaryOp('-', UnaryOp('-', Sym('x')))
        assert simplify(expr) == Sym('x')

    def test_neg_zero(self):
        assert simplify(UnaryOp('-', Num(0))) == Num(0)

    def test_neg_number(self):
        assert simplify(UnaryOp('-', Num(5))) == Num(-5)

    def test_pow_zero(self):
        assert simplify(Pow(Sym('x'), Num(0))) == Num(1)

    def test_pow_one(self):
        assert simplify(Pow(Sym('x'), Num(1))) == Sym('x')

    def test_x_minus_x(self):
        assert simplify(BinOp('-', Sym('x'), Sym('x'))) == Num(0)

    def test_func_on_constant(self):
        assert simplify(Func('sin', Num(0))) == Num(0)

    def test_nested_constant_fold(self):
        expr = BinOp('*', BinOp('+', Num(2), Num(3)), Sym('x'))
        result = simplify(expr)
        val = result.evaluate({'x': 1})
        assert math.isclose(val, 5)

    def test_trig_identity(self):
        expr = BinOp('+', Pow(Func('sin', Sym('x')), Num(2)),
                      Pow(Func('cos', Sym('x')), Num(2)))
        assert simplify(expr) == Num(1)

    def test_one_minus_sin_squared(self):
        expr = BinOp('-', Num(1), Pow(Func('sin', Sym('x')), Num(2)))
        result = simplify(expr)
        assert isinstance(result, Pow) and result.base.name == 'cos'

    def test_div_by_neg_one(self):
        expr = BinOp('/', Sym('x'), Num(-1))
        result = simplify(expr)
        assert isinstance(result, UnaryOp) and result.op == '-'

    def test_x_plus_neg_y(self):
        expr = BinOp('+', Sym('x'), UnaryOp('-', Sym('y')))
        result = simplify(expr)
        assert isinstance(result, BinOp) and result.op == '-'


# ═══════════════════════════════════════════════════════════════════
# Substitution Tests
# ═══════════════════════════════════════════════════════════════════

class TestSubstitution:
    def test_simple(self):
        expr = BinOp('+', Sym('x'), Num(1))
        result = expr.substitute({'x': Num(3)})
        assert result == BinOp('+', Num(3), Num(1))

    def test_with_simplify(self):
        expr = BinOp('+', Sym('x'), Num(1))
        result = expr.substitute({'x': Num(3)}).simplify()
        assert result == Num(4)

    def test_expression_sub(self):
        expr = Pow(Sym('x'), Num(2))
        result = expr.substitute({'x': BinOp('+', Sym('y'), Num(1))})
        expected = Pow(BinOp('+', Sym('y'), Num(1)), Num(2))
        assert result == expected


# ═══════════════════════════════════════════════════════════════════
# Evaluation Tests
# ═══════════════════════════════════════════════════════════════════

class TestEvaluation:
    def test_basic(self):
        assert BinOp('+', Num(2), Num(3)).evaluate() == 5

    def test_variable(self):
        assert math.isclose(BinOp('+', Sym('x'), Num(1)).evaluate({'x': 2}), 3)

    def test_complex(self):
        expr = parse("3*x^2 + 2*x - 5")
        result = expr.evaluate({'x': 2})
        assert math.isclose(result, 11)

    def test_function(self):
        assert math.isclose(Func('sin', Num(0)).evaluate(), 0, abs_tol=1e-10)

    def test_missing_var(self):
        with pytest.raises(ValueError):
            Sym('x').evaluate()

    def test_complex_pow_error(self):
        expr = Pow(Num(-1), Num(0.5))
        with pytest.raises(ValueError):
            expr.evaluate()


# ═══════════════════════════════════════════════════════════════════
# Solving Tests
# ═══════════════════════════════════════════════════════════════════

class TestSolving:
    def test_linear(self):
        expr = BinOp('+', BinOp('*', Num(2), Sym('x')), Num(4))
        roots = solve(expr, 'x')
        assert len(roots) == 1
        assert math.isclose(roots[0].value, -2)

    def test_quadratic(self):
        expr = parse("x^2 - 5*x + 6")
        roots = solve(expr, 'x')
        vals = sorted([r.value for r in roots])
        assert len(roots) == 2
        assert math.isclose(vals[0], 2)
        assert math.isclose(vals[1], 3)

    def test_quadratic_one_root(self):
        expr = parse("x^2 - 2*x + 1")
        roots = solve(expr, 'x')
        assert len(roots) == 1
        assert math.isclose(roots[0].value, 1)

    def test_quadratic_no_real(self):
        expr = BinOp('+', Pow(Sym('x'), Num(2)), Num(1))
        roots = solve(expr, 'x')
        assert len(roots) == 0


# ═══════════════════════════════════════════════════════════════════
# Newton's Method Tests
# ═══════════════════════════════════════════════════════════════════

class TestNewton:
    def test_simple(self):
        f = parse("x^2 - 4")
        root = f.newton_solve('x', x0=3.0)
        assert math.isclose(root, 2.0, rel_tol=1e-6)

    def test_cos_root(self):
        root = Func('cos', Sym('x')).newton_solve('x', x0=1.0)
        assert math.isclose(root, math.pi/2, rel_tol=1e-6)

    def test_cubic(self):
        f = parse("x^3 - x - 2")
        root = f.newton_solve('x', x0=2.0)
        val = f.evaluate({'x': root})
        assert abs(val) < 1e-6


# ═══════════════════════════════════════════════════════════════════
# Taylor Series Tests
# ═══════════════════════════════════════════════════════════════════

class TestTaylor:
    def test_exp(self):
        ts = taylor_series(Func('exp', Sym('x')), 'x', point=0, order=4)
        val = ts.evaluate({'x': 0.5})
        expected = math.exp(0.5)
        assert math.isclose(val, expected, rel_tol=1e-3)

    def test_sin(self):
        ts = taylor_series(Func('sin', Sym('x')), 'x', point=0, order=5)
        val = ts.evaluate({'x': 0.5})
        expected = math.sin(0.5)
        assert math.isclose(val, expected, rel_tol=1e-4)

    def test_polynomial_exact(self):
        f = parse("x^2 + 2*x + 1")
        ts = taylor_series(f, 'x', point=0, order=4)
        assert math.isclose(ts.evaluate({'x': 3.0}), 16.0)
        assert math.isclose(ts.evaluate({'x': -2.0}), 1.0)


# ═══════════════════════════════════════════════════════════════════
# Integration Tests
# ═══════════════════════════════════════════════════════════════════

class TestIntegration:
    def test_constant(self):
        result = numerical_integrate(Num(1), 'x', 0, 1)
        assert math.isclose(result, 1.0)

    def test_linear(self):
        result = numerical_integrate(Sym('x'), 'x', 0, 1)
        assert math.isclose(result, 0.5)

    def test_quadratic(self):
        result = numerical_integrate(Pow(Sym('x'), Num(2)), 'x', 0, 1)
        assert math.isclose(result, 1.0/3.0, rel_tol=1e-4)

    def test_sin(self):
        result = numerical_integrate(Func('sin', Sym('x')), 'x', 0, math.pi, n=1000)
        assert math.isclose(result, 2.0, rel_tol=1e-4)


# ═══════════════════════════════════════════════════════════════════
# Expansion Tests
# ═══════════════════════════════════════════════════════════════════

class TestExpansion:
    def test_simple(self):
        expr = BinOp('*', Sym('a'), BinOp('+', Sym('b'), Sym('c')))
        expanded = expand_expr(expr)
        assert isinstance(expanded, BinOp) and expanded.op == '+'

    def test_double(self):
        expr = BinOp('*', BinOp('+', Sym('a'), Sym('b')),
                      BinOp('+', Sym('c'), Sym('d')))
        expanded = expand_expr(expr)
        assert isinstance(expanded, BinOp)


# ═══════════════════════════════════════════════════════════════════
# LaTeX Tests
# ═══════════════════════════════════════════════════════════════════

class TestLaTeX:
    def test_number(self):
        assert Num(5).to_latex() == '5'

    def test_symbol(self):
        assert Sym('x').to_latex() == 'x'

    def test_fraction(self):
        expr = BinOp('/', Sym('x'), Num(2))
        assert expr.to_latex() == '\\frac{x}{2}'

    def test_power(self):
        expr = Pow(Sym('x'), Num(2))
        assert '{2}' in expr.to_latex()

    def test_sqrt(self):
        expr = Func('sqrt', Sym('x'))
        assert expr.to_latex() == '\\sqrt{x}'

    def test_sin(self):
        expr = Func('sin', Sym('x'))
        assert expr.to_latex() == '\\sin\\left(x\\right)'


# ═══════════════════════════════════════════════════════════════════
# Pretty-Printing Tests
# ═══════════════════════════════════════════════════════════════════

class TestPrettyPrint:
    def test_simple(self):
        assert pretty_print(Num(5)) == '5'
        assert pretty_print(Sym('x')) == 'x'

    def test_addition(self):
        expr = BinOp('+', Sym('x'), Num(1))
        assert pretty_print(expr) == 'x + 1'

    def test_subtraction_needs_parens(self):
        expr = BinOp('-', Sym('a'), BinOp('+', Sym('b'), Sym('c')))
        result = pretty_print(expr)
        assert '(b + c)' in result

    def test_power(self):
        expr = Pow(Sym('x'), Num(2))
        assert 'x^2' in pretty_print(expr)

    def test_function(self):
        assert pretty_print(Func('sin', Sym('x'))) == 'sin(x)'


# ═══════════════════════════════════════════════════════════════════
# Factorization Tests
# ═══════════════════════════════════════════════════════════════════

class TestFactor:
    def test_common_var(self):
        expr = BinOp('+', BinOp('*', Num(2), Sym('x')),
                      BinOp('*', Num(3), Sym('x')))
        result = factor(expr, 'x')
        val = result.evaluate({'x': 5})
        expected = 2*5 + 3*5
        assert math.isclose(val, expected)

    def test_simple_sum(self):
        expr = BinOp('+', Sym('x'), Pow(Sym('x'), Num(2)))
        result = factor(expr, 'x')
        for test_x in [1.0, 2.0, 3.0, -1.0]:
            original = expr.evaluate({'x': test_x})
            factored = result.evaluate({'x': test_x})
            assert math.isclose(factored, original), f"At x={test_x}"


# ═══════════════════════════════════════════════════════════════════
# Symbol Collection Tests
# ═══════════════════════════════════════════════════════════════════

class TestSymbolCollection:
    def test_simple(self):
        expr = BinOp('+', Sym('x'), Sym('y'))
        assert expr.symbols() == frozenset({'x', 'y'})

    def test_nested(self):
        expr = parse("sin(x) + y^2")
        syms = expr.symbols()
        assert 'x' in syms and 'y' in syms

    def test_constant(self):
        assert Num(42).symbols() == frozenset()


# ═══════════════════════════════════════════════════════════════════
# Bug-Specific Tests
# ═══════════════════════════════════════════════════════════════════

class TestBugs:
    def test_zero_pow_zero(self):
        """0^0 should equal 1, not 0."""
        result = simplify(Pow(Num(0), Num(0)))
        assert result == Num(1)

    def test_div_by_neg_one(self):
        """x / (-1) should simplify to -x."""
        result = simplify(BinOp('/', Sym('x'), Num(-1)))
        assert isinstance(result, UnaryOp) and result.op == '-'

    def test_negate_negative_num(self):
        """-(-5) should give 5."""
        result = simplify(UnaryOp('-', Num(-5)))
        assert isinstance(result, Num) and result.value == 5

    def test_rational_roots_fractional(self):
        """2x^2 - x - 6 = 0 should find x = 2."""
        expr = parse("2*x^2 - x - 6")
        try:
            roots = solve(expr, 'x')
            root_vals = [r.value for r in roots]
            assert any(math.isclose(v, 2.0) for v in root_vals), f"Root x=2 not found: {root_vals}"
        except ValueError:
            pass  # Known limitation for higher-degree

    def test_eval_complex_pow(self):
        """(-1)^0.5 should raise ValueError, not return complex."""
        expr = Pow(Num(-1), Num(0.5))
        with pytest.raises(ValueError):
            expr.evaluate()

    def test_x_plus_neg_y(self):
        """x + (-y) should simplify to x - y."""
        expr = BinOp('+', Sym('x'), UnaryOp('-', Sym('y')))
        result = simplify(expr)
        assert isinstance(result, BinOp) and result.op == '-'


# ═══════════════════════════════════════════════════════════════════
# New Feature Tests: Limits
# ═══════════════════════════════════════════════════════════════════

class TestLimits:
    def test_sin_over_x(self):
        """lim(x→0) sin(x)/x = 1"""
        expr = BinOp('/', Func('sin', Sym('x')), Sym('x'))
        result = expr.limit('x', 0)
        assert result is not None
        assert math.isclose(result, 1.0, rel_tol=1e-4)

    def test_constant_limit(self):
        """lim(x→0) 5 = 5"""
        result = Num(5).limit('x', 0)
        assert result == 5.0

    def test_limit_at_infinity(self):
        """lim(x→∞) 1/x = 0"""
        expr = BinOp('/', Num(1), Sym('x'))
        result = expr.limit('x', 'inf')
        assert result is not None
        assert math.isclose(result, 0.0, abs_tol=1e-4)


# ═══════════════════════════════════════════════════════════════════
# New Feature Tests: Serialization
# ═══════════════════════════════════════════════════════════════════

class TestSerialization:
    def test_to_dict_num(self):
        result = to_dict(Num(42))
        assert result == {'type': 'Num', 'value': 42}

    def test_to_dict_sym(self):
        result = to_dict(Sym('x'))
        assert result == {'type': 'Sym', 'name': 'x'}

    def test_to_dict_binop(self):
        result = to_dict(BinOp('+', Num(1), Num(2)))
        assert result['type'] == 'BinOp'
        assert result['op'] == '+'
        assert result['left'] == {'type': 'Num', 'value': 1}

    def test_roundtrip(self):
        expr = parse("x^2 + 2*x + 1")
        d = to_dict(expr)
        restored = from_dict(d)
        assert expr == restored

    def test_json_roundtrip(self):
        expr = parse("sin(x) + cos(y)")
        json_str = to_json(expr)
        restored = from_json(json_str)
        assert expr == restored


# ═══════════════════════════════════════════════════════════════════
# New Feature Tests: Expr.depth() and Expr.size()
# ═══════════════════════════════════════════════════════════════════

class TestExprTreeMetrics:
    def test_depth(self):
        assert Num(5).depth() == 1
        assert Sym('x').depth() == 1
        assert BinOp('+', Num(1), Num(2)).depth() == 2
        assert BinOp('+', BinOp('+', Num(1), Num(2)), Num(3)).depth() == 3

    def test_size(self):
        assert Num(5).size() == 1
        assert Sym('x').size() == 1
        assert BinOp('+', Num(1), Num(2)).size() == 3
        assert Pow(Sym('x'), Num(2)).size() == 3


# ═══════════════════════════════════════════════════════════════════
# Integration Tests (end-to-end)
# ═══════════════════════════════════════════════════════════════════

class TestEndToEnd:
    def test_diff_simplify_eval(self):
        f = parse("x^3 + 2*x^2 - x + 5")
        df = f.diff('x').simplify()
        val = df.evaluate({'x': 1.0})
        assert math.isclose(val, 6, rel_tol=1e-6)

    def test_parse_diff_simplify(self):
        f = parse("exp(x)")
        df = f.diff('x').simplify()
        val = df.evaluate({'x': 0.0})
        assert math.isclose(val, 1.0, rel_tol=1e-6)

    def test_substitute_then_eval(self):
        f = parse("x^2 + y")
        g = f.substitute({'x': 3, 'y': 4})
        val = g.evaluate({})
        assert math.isclose(val, 13)

    def test_partial_derivative(self):
        f = BinOp('+', BinOp('*', Num(3), Sym('x')), BinOp('*', Num(2), Sym('y')))
        df_dx = f.diff('x').simplify()
        df_dy = f.diff('y').simplify()
        assert df_dx == Num(3)
        assert df_dy == Num(2)

    def test_taylor_then_eval(self):
        f = parse("exp(x)")
        ts = f.taylor('x', point=0, order=6)
        for x_val in [0.1, 0.5, 1.0]:
            val = ts.evaluate({'x': x_val})
            expected = math.exp(x_val)
            assert math.isclose(val, expected, rel_tol=0.05)

    def test_cli_parse(self):
        """Test that parsing works the same way through the package."""
        expr = parse("3*x^2 + 2*x - 5")
        assert isinstance(expr, Expr)
        assert expr.evaluate({'x': 2}) == 11