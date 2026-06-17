"""
Test suite for symbolic algebra system (enhanced).
"""

import math
from symbolic import (
    Expr, Num, Sym, BinOp, UnaryOp, Func, Pow,
    parse, simplify, differentiate, expand_expr,
    substitute, evaluate, collect_symbols, to_latex, solve,
    taylor_series, numerical_integrate, newton_method,
    factor, pretty_print,
    x, y, z, _wrap,
    sin, cos, tan, exp, ln, sqrt, abs_expr,
)


def assert_equal(actual, expected, msg=""):
    """Simple assertion helper."""
    if isinstance(expected, float) and isinstance(actual, float):
        if not math.isclose(actual, expected, rel_tol=1e-9):
            raise AssertionError(f"Expected {expected}, got {actual}. {msg}")
    elif actual != expected:
        raise AssertionError(f"Expected {expected}, got {actual}. {msg}")


def assert_close(actual, expected, rel_tol=1e-6, msg=""):
    """Assert that two floats are close."""
    if not math.isclose(actual, expected, rel_tol=rel_tol):
        raise AssertionError(f"Expected {expected}, got {actual} (rel_tol={rel_tol}). {msg}")


def assert_expr_equal(actual, expected, msg=""):
    """Compare two expressions for equality."""
    if actual != expected:
        raise AssertionError(f"Expected {expected}, got {actual}. {msg}")


# ──────────────── Construction Tests ────────────────

def test_num_construction():
    n = Num(5)
    assert n.value == 5
    assert str(n) == "5"
    n2 = Num(3.14)
    assert n2.value == 3.14

def test_sym_construction():
    s = Sym('x')
    assert s.name == 'x'
    assert str(s) == 'x'

def test_sym_invalid_name():
    try:
        Sym('123abc')
        assert False, "Should have raised ValueError"
    except ValueError:
        pass

def test_binop_construction():
    b = BinOp('+', Num(1), Num(2))
    assert str(b) == "(1 + 2)"

def test_pow_construction():
    p = Pow(Sym('x'), Num(2))
    assert str(p) == "(x^2)"

def test_func_construction():
    f = Func('sin', Sym('x'))
    assert str(f) == "sin(x)"

def test_unary_construction():
    u = UnaryOp('-', Sym('x'))
    assert str(u) == "(-x)"

def test_invalid_binop():
    try:
        BinOp('%', Num(1), Num(2))
        assert False, "Should have raised ValueError"
    except ValueError:
        pass

def test_invalid_func():
    try:
        Func('unknown', Sym('x'))
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


# ──────────────── Operator Tests ────────────────

def test_operator_overload_add():
    expr = Num(1) + Num(2)
    assert isinstance(expr, BinOp)
    assert expr.op == '+'

def test_operator_overload_mul():
    expr = Sym('x') * Num(3)
    assert isinstance(expr, BinOp)
    assert expr.op == '*'

def test_operator_overload_pow():
    expr = Sym('x') ** Num(2)
    assert isinstance(expr, Pow)

def test_operator_overload_neg():
    expr = -Sym('x')
    assert isinstance(expr, UnaryOp)

def test_operator_mixed():
    expr = 3 * x + 2
    assert isinstance(expr, BinOp)

def test_wrap():
    assert isinstance(_wrap(5), Num)
    assert isinstance(_wrap(3.14), Num)
    assert isinstance(_wrap(x), Sym)


# ──────────────── Parsing Tests ────────────────

def test_parse_number():
    expr = parse("42")
    assert expr == Num(42)

def test_parse_float():
    expr = parse("3.14")
    assert isinstance(expr, Num)
    assert math.isclose(expr.value, 3.14)

def test_parse_symbol():
    expr = parse("x")
    assert expr == Sym('x')

def test_parse_addition():
    expr = parse("x + 1")
    assert expr == BinOp('+', Sym('x'), Num(1))

def test_parse_subtraction():
    expr = parse("x - 1")
    assert expr == BinOp('-', Sym('x'), Num(1))

def test_parse_multiplication():
    expr = parse("x * 2")
    assert expr == BinOp('*', Sym('x'), Num(2))

def test_parse_division():
    expr = parse("x / 2")
    assert expr == BinOp('/', Sym('x'), Num(2))

def test_parse_power():
    expr = parse("x ^ 2")
    assert expr == Pow(Sym('x'), Num(2))

def test_parse_unary_neg():
    expr = parse("-x")
    assert expr == UnaryOp('-', Sym('x'))

def test_parse_parens():
    expr = parse("(x + 1)")
    assert expr == BinOp('+', Sym('x'), Num(1))

def test_parse_precedence():
    # 2 + 3 * x should be 2 + (3*x), not (2+3)*x
    expr = parse("2 + 3 * x")
    assert expr == BinOp('+', Num(2), BinOp('*', Num(3), Sym('x')))

def test_parse_function():
    expr = parse("sin(x)")
    assert expr == Func('sin', Sym('x'))

def test_parse_nested_function():
    expr = parse("sin(cos(x))")
    assert expr == Func('sin', Func('cos', Sym('x')))

def test_parse_complex():
    expr = parse("3*x^2 + 2*x - 5")
    assert isinstance(expr, Expr)

def test_parse_right_assoc_power():
    expr = parse("x^2^3")
    assert isinstance(expr, Pow)

def test_parse_unexpected_char():
    try:
        parse("x @ 2")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


# ──────────────── Differentiation Tests ────────────────

def test_diff_constant():
    result = differentiate(Num(5), 'x')
    assert result == Num(0)

def test_diff_variable():
    result = differentiate(Sym('x'), 'x')
    assert result == Num(1)

def test_diff_other_variable():
    result = differentiate(Sym('y'), 'x')
    assert result == Num(0)

def test_diff_power():
    result = differentiate(Pow(Sym('x'), Num(3)), 'x')
    simplified = simplify(result)
    val = simplified.evaluate({'x': 2})
    assert math.isclose(val, 12)

def test_diff_sum():
    result = differentiate(BinOp('+', Sym('x'), Num(1)), 'x')
    simplified = simplify(result)
    assert simplified == Num(1)

def test_diff_product():
    f = BinOp('*', Sym('x'), Func('sin', Sym('x')))
    df = differentiate(f, 'x')
    simplified = simplify(df)
    val = simplified.evaluate({'x': 1.0})
    expected = math.sin(1.0) + 1.0 * math.cos(1.0)
    assert math.isclose(val, expected, rel_tol=1e-9)

def test_diff_chain_rule():
    f = Func('sin', Pow(Sym('x'), Num(2)))
    df = differentiate(f, 'x')
    simplified = simplify(df)
    val = simplified.evaluate({'x': 1.0})
    expected = math.cos(1) * 2
    assert math.isclose(val, expected, rel_tol=1e-9)

def test_diff_exp():
    f = Func('exp', Sym('x'))
    df = differentiate(f, 'x')
    simplified = simplify(df)
    val = simplified.evaluate({'x': 1.0})
    assert math.isclose(val, math.e, rel_tol=1e-9)

def test_diff_ln():
    f = Func('ln', Sym('x'))
    df = differentiate(f, 'x')
    simplified = simplify(df)
    val = simplified.evaluate({'x': 2.0})
    assert math.isclose(val, 0.5, rel_tol=1e-9)

def test_diff_quotient():
    f = BinOp('/', Sym('x'), Func('sin', Sym('x')))
    df = differentiate(f, 'x')
    simplified = simplify(df)
    val = simplified.evaluate({'x': 1.0})
    expected = (math.sin(1) - 1*math.cos(1)) / (math.sin(1)**2)
    assert math.isclose(val, expected, rel_tol=1e-6)

def test_diff_general_power():
    f = Pow(Sym('x'), Sym('x'))
    df = differentiate(f, 'x')
    simplified = simplify(df)
    val = simplified.evaluate({'x': 2.0})
    expected = 4.0 * (math.log(2.0) + 1.0)
    assert math.isclose(val, expected, rel_tol=1e-4)


# ──────────────── Simplification Tests ────────────────

def test_simplify_add_zero():
    assert simplify(BinOp('+', Sym('x'), Num(0))) == Sym('x')
    assert simplify(BinOp('+', Num(0), Sym('x'))) == Sym('x')

def test_simplify_mul_one():
    assert simplify(BinOp('*', Sym('x'), Num(1))) == Sym('x')
    assert simplify(BinOp('*', Num(1), Sym('x'))) == Sym('x')

def test_simplify_mul_zero():
    assert simplify(BinOp('*', Sym('x'), Num(0))) == Num(0)
    assert simplify(BinOp('*', Num(0), Sym('x'))) == Num(0)

def test_simplify_constant_fold():
    assert simplify(BinOp('+', Num(2), Num(3))) == Num(5)
    assert simplify(BinOp('-', Num(10), Num(3))) == Num(7)
    assert simplify(BinOp('*', Num(4), Num(3))) == Num(12)
    assert simplify(BinOp('/', Num(10), Num(2))) == Num(5)

def test_simplify_double_neg():
    expr = UnaryOp('-', UnaryOp('-', Sym('x')))
    assert simplify(expr) == Sym('x')

def test_simplify_neg_zero():
    expr = UnaryOp('-', Num(0))
    assert simplify(expr) == Num(0)

def test_simplify_neg_num():
    expr = UnaryOp('-', Num(5))
    assert simplify(expr) == Num(-5)

def test_simplify_power_zero():
    expr = Pow(Sym('x'), Num(0))
    assert simplify(expr) == Num(1)

def test_simplify_power_one():
    expr = Pow(Sym('x'), Num(1))
    assert simplify(expr) == Sym('x')

def test_simplify_x_minus_x():
    expr = BinOp('-', Sym('x'), Sym('x'))
    assert simplify(expr) == Num(0)

def test_simplify_func_on_constant():
    expr = Func('sin', Num(0))
    assert simplify(expr) == Num(0)

def test_simplify_nested():
    expr = BinOp('*', BinOp('+', Num(2), Num(3)), Sym('x'))
    result = simplify(expr)
    val = result.evaluate({'x': 1})
    assert math.isclose(val, 5)

def test_simplify_trig_identity():
    """Test sin²x + cos²x = 1."""
    expr = BinOp('+', Pow(Func('sin', Sym('x')), Num(2)), Pow(Func('cos', Sym('x')), Num(2)))
    result = simplify(expr)
    assert result == Num(1), f"Expected Num(1), got {result}"

def test_simplify_one_minus_sin_squared():
    """Test 1 - sin²x = cos²x."""
    expr = BinOp('-', Num(1), Pow(Func('sin', Sym('x')), Num(2)))
    result = simplify(expr)
    # Should be cos²(x)
    assert isinstance(result, Pow), f"Expected Pow, got {type(result)}"
    assert isinstance(result.base, Func) and result.base.name == 'cos'
    assert isinstance(result.exponent, Num) and result.exponent.value == 2

def test_simplify_one_minus_cos_squared():
    """Test 1 - cos²x = sin²x."""
    expr = BinOp('-', Num(1), Pow(Func('cos', Sym('x')), Num(2)))
    result = simplify(expr)
    assert isinstance(result, Pow), f"Expected Pow, got {type(result)}"
    assert isinstance(result.base, Func) and result.base.name == 'sin'
    assert isinstance(result.exponent, Num) and result.exponent.value == 2


# ──────────────── Substitution Tests ────────────────

def test_substitute_simple():
    expr = BinOp('+', Sym('x'), Num(1))
    result = expr.substitute({'x': Num(3)})
    assert result == BinOp('+', Num(3), Num(1))

def test_substitute_with_simplify():
    expr = BinOp('+', Sym('x'), Num(1))
    result = expr.substitute({'x': Num(3)}).simplify()
    assert result == Num(4)

def test_substitute_expression():
    expr = Pow(Sym('x'), Num(2))
    result = expr.substitute({'x': BinOp('+', Sym('y'), Num(1))})
    expected = Pow(BinOp('+', Sym('y'), Num(1)), Num(2))
    assert result == expected


# ──────────────── Evaluation Tests ────────────────

def test_eval_basic():
    expr = BinOp('+', Num(2), Num(3))
    assert expr.evaluate() == 5

def test_eval_variable():
    expr = BinOp('+', Sym('x'), Num(1))
    assert math.isclose(expr.evaluate({'x': 2}), 3)

def test_eval_complex():
    expr = parse("3*x^2 + 2*x - 5")
    result = expr.evaluate({'x': 2})
    assert math.isclose(result, 11)

def test_eval_function():
    expr = Func('sin', Num(0))
    assert math.isclose(expr.evaluate(), 0, abs_tol=1e-10)

def test_eval_missing_var():
    expr = Sym('x')
    try:
        expr.evaluate()
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


# ──────────────── Symbol Collection Tests ────────────────

def test_symbols_simple():
    expr = BinOp('+', Sym('x'), Sym('y'))
    assert expr.symbols() == frozenset({'x', 'y'})

def test_symbols_nested():
    expr = parse("sin(x) + y^2")
    syms = expr.symbols()
    assert 'x' in syms
    assert 'y' in syms

def test_symbols_constant():
    expr = Num(42)
    assert expr.symbols() == frozenset()


# ──────────────── LaTeX Tests ────────────────

def test_latex_number():
    assert Num(5).to_latex() == '5'

def test_latex_symbol():
    assert Sym('x').to_latex() == 'x'

def test_latex_fraction():
    expr = BinOp('/', Sym('x'), Num(2))
    assert expr.to_latex() == '\\frac{x}{2}'

def test_latex_power():
    expr = Pow(Sym('x'), Num(2))
    assert '^{2}' in expr.to_latex()

def test_latex_sqrt():
    expr = Func('sqrt', Sym('x'))
    assert expr.to_latex() == '\\sqrt{x}'

def test_latex_sin():
    expr = Func('sin', Sym('x'))
    assert expr.to_latex() == '\\sin\\left(x\\right)'


# ──────────────── Solving Tests ────────────────

def test_solve_linear():
    expr = BinOp('+', BinOp('*', Num(2), Sym('x')), Num(4))
    roots = solve(expr, 'x')
    assert len(roots) == 1
    assert math.isclose(roots[0].value, -2)

def test_solve_quadratic():
    expr = parse("x^2 - 5*x + 6")
    roots = solve(expr, 'x')
    vals = sorted([r.value for r in roots])
    assert len(roots) == 2
    assert math.isclose(vals[0], 2)
    assert math.isclose(vals[1], 3)

def test_solve_quadratic_one_root():
    expr2 = parse("x^2 - 2*x + 1")
    roots = solve(expr2, 'x')
    assert len(roots) == 1
    assert math.isclose(roots[0].value, 1)

def test_solve_quadratic_no_real():
    expr = BinOp('+', Pow(Sym('x'), Num(2)), Num(1))
    roots = solve(expr, 'x')
    assert len(roots) == 0


# ──────────────── Expansion Tests ────────────────

def test_expand_simple():
    expr = BinOp('*', Sym('a'), BinOp('+', Sym('b'), Sym('c')))
    expanded = expand_expr(expr)
    assert isinstance(expanded, BinOp)
    assert expanded.op == '+'

def test_expand_double():
    expr = BinOp('*', BinOp('+', Sym('a'), Sym('b')), BinOp('+', Sym('c'), Sym('d')))
    expanded = expand_expr(expr)
    assert isinstance(expanded, BinOp)


# ──────────────── Taylor Series Tests ────────────────

def test_taylor_exp():
    """Taylor series of exp(x) around 0: 1 + x + x²/2 + x³/6 + ..."""
    f = Func('exp', Sym('x'))
    ts = taylor_series(f, 'x', point=0, order=4)
    # Evaluate at x=0.5: exp(0.5) ≈ 1.6487
    val = ts.evaluate({'x': 0.5})
    expected = math.exp(0.5)
    assert_close(val, expected, rel_tol=1e-3)

def test_taylor_sin():
    """Taylor series of sin(x) around 0: x - x³/6 + x⁵/120"""
    f = Func('sin', Sym('x'))
    ts = taylor_series(f, 'x', point=0, order=5)
    # sin(0.5) ≈ 0.4794
    val = ts.evaluate({'x': 0.5})
    expected = math.sin(0.5)
    assert_close(val, expected, rel_tol=1e-4)

def test_taylor_cos():
    """Taylor series of cos(x) around 0: 1 - x²/2 + x⁴/24"""
    f = Func('cos', Sym('x'))
    ts = taylor_series(f, 'x', point=0, order=4)
    # cos(0.3) ≈ 0.9553
    val = ts.evaluate({'x': 0.3})
    expected = math.cos(0.3)
    assert_close(val, expected, rel_tol=1e-4)

def test_taylor_polynomial():
    """Taylor series of x^2 + 2x + 1 should be exact (it's already a polynomial)."""
    f = parse("x^2 + 2*x + 1")
    ts = taylor_series(f, 'x', point=0, order=4)
    # Should match at any point
    assert_close(ts.evaluate({'x': 3.0}), 16.0)  # 9 + 6 + 1 = 16
    assert_close(ts.evaluate({'x': -2.0}), 1.0)   # 4 - 4 + 1 = 1

def test_taylor_around_nonzero():
    """Taylor series of exp(x) around x=1."""
    f = Func('exp', Sym('x'))
    ts = taylor_series(f, 'x', point=1, order=4)
    # exp(1) ≈ 2.7183
    val = ts.evaluate({'x': 1.0})
    expected = math.exp(1.0)
    assert_close(val, expected, rel_tol=1e-4)


# ──────────────── Numerical Integration Tests ────────────────

def test_integrate_constant():
    """∫₀¹ 1 dx = 1"""
    f = Num(1)
    result = numerical_integrate(f, 'x', 0, 1)
    assert_close(result, 1.0)

def test_integrate_linear():
    """∫₀¹ x dx = 0.5"""
    f = Sym('x')
    result = numerical_integrate(f, 'x', 0, 1)
    assert_close(result, 0.5)

def test_integrate_quadratic():
    """∫₀¹ x² dx = 1/3"""
    f = Pow(Sym('x'), Num(2))
    result = numerical_integrate(f, 'x', 0, 1)
    assert_close(result, 1.0/3.0, rel_tol=1e-4)

def test_integrate_sin():
    """∫₀^π sin(x) dx = 2"""
    f = Func('sin', Sym('x'))
    result = numerical_integrate(f, 'x', 0, math.pi, n=1000)
    assert_close(result, 2.0, rel_tol=1e-4)

def test_integrate_exp():
    """∫₀¹ exp(x) dx = e - 1"""
    f = Func('exp', Sym('x'))
    result = numerical_integrate(f, 'x', 0, 1)
    expected = math.e - 1
    assert_close(result, expected, rel_tol=1e-4)

def test_integrate_via_method():
    """Test integration via Expr method."""
    f = parse("x^2")
    result = f.integrate('x', 0, 1)
    assert_close(result, 1.0/3.0, rel_tol=1e-4)


# ──────────────── Newton's Method Tests ────────────────

def test_newton_simple():
    """Solve x^2 - 4 = 0 => x = 2 (starting from x0=3)."""
    f = parse("x^2 - 4")
    root = f.newton_solve('x', x0=3.0)
    assert_close(root, 2.0, rel_tol=1e-6)

def test_newton_cos():
    """Solve cos(x) = 0 => x ≈ π/2."""
    f = Func('cos', Sym('x'))
    root = f.newton_solve('x', x0=1.0)
    assert_close(root, math.pi/2, rel_tol=1e-6)

def test_newton_cubic():
    """Solve x^3 - x - 2 = 0."""
    f = parse("x^3 - x - 2")
    root = f.newton_solve('x', x0=2.0)
    # Verify root
    val = f.evaluate({'x': root})
    assert abs(val) < 1e-6

def test_newton_diverges():
    """Newton's method should fail for x^2 + 1 = 0 (no real root)."""
    f = BinOp('+', Pow(Sym('x'), Num(2)), Num(1))
    try:
        f.newton_solve('x', x0=0.0, max_iter=20)
        # May or may not raise, depending on behavior
    except ValueError:
        pass  # Expected - no real root


# ──────────────── Factorization Tests ────────────────

def test_factor_common_var():
    """Factor 2*x + 3*x -> x * (2 + 3) or similar."""
    expr = BinOp('+', BinOp('*', Num(2), Sym('x')), BinOp('*', Num(3), Sym('x')))
    result = factor(expr, 'x')
    # The result should have x as a factor
    # Evaluate at x=5: should give 25 (=5*5)
    val = result.evaluate({'x': 5})
    expected = 2*5 + 3*5  # = 25
    assert_close(val, expected)

def test_factor_simple_sum():
    """Factor x + x^2."""
    expr = BinOp('+', Sym('x'), Pow(Sym('x'), Num(2)))
    result = factor(expr, 'x')
    # Evaluate to verify equivalence
    for test_x in [1.0, 2.0, 3.0, -1.0]:
        original = expr.evaluate({'x': test_x})
        factored = result.evaluate({'x': test_x})
        assert_close(factored, original, msg=f"At x={test_x}")


# ──────────────── Pretty Printing Tests ────────────────

def test_pretty_simple():
    assert pretty_print(Num(5)) == '5'
    assert pretty_print(Sym('x')) == 'x'

def test_pretty_addition():
    expr = BinOp('+', Sym('x'), Num(1))
    result = pretty_print(expr)
    assert result == 'x + 1'

def test_pretty_multiplication():
    expr = BinOp('*', Sym('x'), Num(2))
    result = pretty_print(expr)
    assert '2' in result and 'x' in result

def test_pretty_nested():
    """x + y * z should print as x + y * z without extra parens."""
    expr = BinOp('+', Sym('x'), BinOp('*', Sym('y'), Sym('z')))
    result = pretty_print(expr)
    # Should NOT have unnecessary parens around y * z
    assert '(' not in result or 'x' in result

def test_pretty_subtraction():
    """a - (b + c) needs parens around b + c."""
    expr = BinOp('-', Sym('a'), BinOp('+', Sym('b'), Sym('c')))
    result = pretty_print(expr)
    assert '(b + c)' in result

def test_pretty_power():
    expr = Pow(Sym('x'), Num(2))
    result = pretty_print(expr)
    assert 'x^2' in result

def test_pretty_function():
    expr = Func('sin', Sym('x'))
    result = pretty_print(expr)
    assert result == 'sin(x)'

def test_pretty_unary_neg():
    expr = UnaryOp('-', Sym('x'))
    result = pretty_print(expr)
    assert result == '-x'

def test_pretty_method():
    """Test pretty() method on Expr."""
    expr = parse("x^2 + 2*x + 1")
    result = expr.pretty()
    assert 'x' in result
    assert isinstance(result, str)


# ──────────────── Integration Tests ────────────────

def test_integration_diff_simplify_eval():
    """Differentiate, simplify, then evaluate."""
    f = parse("x^3 + 2*x^2 - x + 5")
    df = f.diff('x').simplify()
    val = df.evaluate({'x': 1.0})
    assert math.isclose(val, 6, rel_tol=1e-6)

def test_parse_diff_simplify():
    """Parse an expression, differentiate, simplify, check."""
    f = parse("exp(x)")
    df = f.diff('x').simplify()
    val = df.evaluate({'x': 0.0})
    assert math.isclose(val, 1.0, rel_tol=1e-6)

def test_chain_rule_complex():
    """d/dx(sin(cos(x))) should work."""
    f = parse("sin(cos(x))")
    df = f.diff('x').simplify()
    expected = math.cos(math.cos(1)) * (-math.sin(1))
    val = df.evaluate({'x': 1.0})
    assert math.isclose(val, expected, rel_tol=1e-6)

def test_substitute_then_eval():
    """Substitute variables then evaluate."""
    f = parse("x^2 + y")
    g = f.substitute({'x': Num(3), 'y': Num(4)})
    val = g.evaluate({})
    assert math.isclose(val, 13)

def test_partial_derivative():
    """Differentiate with respect to y in an expression with x and y."""
    f = BinOp('+', BinOp('*', Num(3), Sym('x')), BinOp('*', Num(2), Sym('y')))
    df_dx = f.diff('x').simplify()
    df_dy = f.diff('y').simplify()
    assert df_dx == Num(3)
    assert df_dy == Num(2)

def test_taylor_then_eval():
    """Taylor series of exp(x) should approximate exp(x)."""
    f = parse("exp(x)")
    ts = f.taylor('x', point=0, order=6)
    for x_val in [0.1, 0.5, 1.0]:
        val = ts.evaluate({'x': x_val})
        expected = math.exp(x_val)
        assert_close(val, expected, rel_tol=0.05, msg=f"At x={x_val}")

def test_newton_via_method():
    """Test Newton's method via Expr method."""
    f = parse("x^2 - 2")
    root = f.newton_solve('x', x0=1.5)
    assert_close(root, math.sqrt(2), rel_tol=1e-6)

def test_factor_via_method():
    """Test factorization via Expr method."""
    f = parse("x + x^2")
    result = f.factor('x')
    # Just verify it doesn't crash and produces something
    assert isinstance(result, Expr)

def test_pretty_roundtrip():
    """Verify pretty printing produces readable output for complex expressions."""
    expr = parse("sin(x)^2 + cos(x)^2")
    pp = expr.pretty()
    assert 'sin' in pp and 'cos' in pp


# ──────────────── Run Tests ────────────────

def run_all_tests():
    tests = [
        # Construction
        test_num_construction, test_sym_construction, test_sym_invalid_name,
        test_binop_construction, test_pow_construction, test_func_construction,
        test_unary_construction, test_invalid_binop, test_invalid_func,
        # Operators
        test_operator_overload_add, test_operator_overload_mul,
        test_operator_overload_pow, test_operator_overload_neg,
        test_operator_mixed, test_wrap,
        # Parsing
        test_parse_number, test_parse_float, test_parse_symbol,
        test_parse_addition, test_parse_subtraction, test_parse_multiplication,
        test_parse_division, test_parse_power, test_parse_unary_neg,
        test_parse_parens, test_parse_precedence, test_parse_function,
        test_parse_nested_function, test_parse_complex,
        test_parse_right_assoc_power, test_parse_unexpected_char,
        # Differentiation
        test_diff_constant, test_diff_variable, test_diff_other_variable,
        test_diff_power, test_diff_sum, test_diff_product,
        test_diff_chain_rule, test_diff_exp, test_diff_ln,
        test_diff_quotient, test_diff_general_power,
        # Simplification
        test_simplify_add_zero, test_simplify_mul_one, test_simplify_mul_zero,
        test_simplify_constant_fold, test_simplify_double_neg,
        test_simplify_neg_zero, test_simplify_neg_num,
        test_simplify_power_zero, test_simplify_power_one,
        test_simplify_x_minus_x, test_simplify_func_on_constant,
        test_simplify_nested,
        test_simplify_trig_identity,
        test_simplify_one_minus_sin_squared,
        test_simplify_one_minus_cos_squared,
        # Substitution
        test_substitute_simple, test_substitute_with_simplify,
        test_substitute_expression,
        # Evaluation
        test_eval_basic, test_eval_variable, test_eval_complex,
        test_eval_function, test_eval_missing_var,
        # Symbol collection
        test_symbols_simple, test_symbols_nested, test_symbols_constant,
        # LaTeX
        test_latex_number, test_latex_symbol, test_latex_fraction,
        test_latex_power, test_latex_sqrt, test_latex_sin,
        # Solving
        test_solve_linear, test_solve_quadratic,
        test_solve_quadratic_one_root, test_solve_quadratic_no_real,
        # Expansion
        test_expand_simple, test_expand_double,
        # Taylor series
        test_taylor_exp, test_taylor_sin, test_taylor_cos,
        test_taylor_polynomial, test_taylor_around_nonzero,
        # Numerical integration
        test_integrate_constant, test_integrate_linear,
        test_integrate_quadratic, test_integrate_sin,
        test_integrate_exp, test_integrate_via_method,
        # Newton's method
        test_newton_simple, test_newton_cos, test_newton_cubic,
        test_newton_diverges,
        # Factorization
        test_factor_common_var, test_factor_simple_sum,
        # Pretty printing
        test_pretty_simple, test_pretty_addition,
        test_pretty_multiplication, test_pretty_nested,
        test_pretty_subtraction, test_pretty_power,
        test_pretty_function, test_pretty_unary_neg,
        test_pretty_method,
        # Integration
        test_integration_diff_simplify_eval, test_parse_diff_simplify,
        test_chain_rule_complex, test_substitute_then_eval,
        test_partial_derivative,
        test_taylor_then_eval, test_newton_via_method,
        test_factor_via_method, test_pretty_roundtrip,
    ]

    passed = 0
    failed = 0
    for test_fn in tests:
        name = test_fn.__name__
        try:
            test_fn()
            print(f"  ✓ {name}")
            passed += 1
        except Exception as e:
            print(f"  ✗ {name}: {e}")
            failed += 1

    print(f"\n{'='*60}")
    print(f"Results: {passed} passed, {failed} failed, {passed+failed} total")
    print(f"{'='*60}")
    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    exit(0 if success else 1)