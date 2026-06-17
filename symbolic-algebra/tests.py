"""
Test suite for symbolic algebra system.
"""

import math
from symbolic import (
    Expr, Num, Sym, BinOp, UnaryOp, Func, Pow,
    parse, simplify, differentiate, expand_expr,
    substitute, evaluate, collect_symbols, to_latex, solve,
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
    # Should parse without error
    assert isinstance(expr, Expr)

def test_parse_right_assoc_power():
    # x^2^3 should be x^(2^3)
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
    # d/dx(x^3) = 3*x^2
    val = simplified.evaluate({'x': 2})
    assert math.isclose(val, 12)  # 3*4 = 12

def test_diff_sum():
    result = differentiate(BinOp('+', Sym('x'), Num(1)), 'x')
    simplified = simplify(result)
    assert simplified == Num(1)

def test_diff_product():
    # d/dx(x * sin(x)) = sin(x) + x*cos(x)
    f = BinOp('*', Sym('x'), Func('sin', Sym('x')))
    df = differentiate(f, 'x')
    simplified = simplify(df)
    # Evaluate at x=1
    val = simplified.evaluate({'x': 1.0})
    expected = math.sin(1.0) + 1.0 * math.cos(1.0)
    assert math.isclose(val, expected, rel_tol=1e-9)

def test_diff_chain_rule():
    # d/dx(sin(x^2)) = cos(x^2) * 2x
    f = Func('sin', Pow(Sym('x'), Num(2)))
    df = differentiate(f, 'x')
    simplified = simplify(df)
    # Evaluate at x=1
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
    # d/dx(x / sin(x))
    f = BinOp('/', Sym('x'), Func('sin', Sym('x')))
    df = differentiate(f, 'x')
    simplified = simplify(df)
    # Numerical check at x=1
    val = simplified.evaluate({'x': 1.0})
    # d/dx(x/sin(x)) = (sin(x) - x*cos(x)) / sin(x)^2
    expected = (math.sin(1) - 1*math.cos(1)) / (math.sin(1)**2)
    assert math.isclose(val, expected, rel_tol=1e-6)

def test_diff_general_power():
    # d/dx(x^x) = x^x * (ln(x) + 1) — requires general power rule
    f = Pow(Sym('x'), Sym('x'))
    df = differentiate(f, 'x')
    simplified = simplify(df)
    # Evaluate at x=2: 2^2*(ln(2) + 1) = 4*(0.6931+1) = 6.7726
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
    # (2 + 3) * x → 5x
    expr = BinOp('*', BinOp('+', Num(2), Num(3)), Sym('x'))
    result = simplify(expr)
    # Should simplify to 5 * x or similar
    val = result.evaluate({'x': 1})
    assert math.isclose(val, 5)


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
    # x^2 with x → (y+1)
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
    # 3*4 + 2*2 - 5 = 12 + 4 - 5 = 11
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
    # 2x + 4 = 0 => x = -2
    expr = BinOp('+', BinOp('*', Num(2), Sym('x')), Num(4))
    roots = solve(expr, 'x')
    assert len(roots) == 1
    assert math.isclose(roots[0].value, -2)

def test_solve_quadratic():
    # x^2 - 5x + 6 = 0 => x = 2 or x = 3
    expr = parse("x^2 - 5*x + 6")
    roots = solve(expr, 'x')
    vals = sorted([r.value for r in roots])
    assert len(roots) == 2
    assert math.isclose(vals[0], 2)
    assert math.isclose(vals[1], 3)

def test_solve_quadratic_one_root():
    # x^2 - 2*x + 1 = 0 => x = 1
    expr = BinOp('-', BinOp('-', Pow(Sym('x'), Num(2)), BinOp('*', Num(2), Sym('x'))), Num(-1))
    # Simplify: x^2 - 2x + 1
    expr2 = parse("x^2 - 2*x + 1")
    roots = solve(expr2, 'x')
    assert len(roots) == 1
    assert math.isclose(roots[0].value, 1)

def test_solve_quadratic_no_real():
    # x^2 + 1 = 0 => no real roots
    expr = BinOp('+', Pow(Sym('x'), Num(2)), Num(1))
    roots = solve(expr, 'x')
    assert len(roots) == 0


# ──────────────── Expansion Tests ────────────────

def test_expand_simple():
    # a * (b + c) = a*b + a*c
    expr = BinOp('*', Sym('a'), BinOp('+', Sym('b'), Sym('c')))
    expanded = expand_expr(expr)
    # Should be a*b + a*c
    assert isinstance(expanded, BinOp)
    assert expanded.op == '+'

def test_expand_double():
    # (a + b) * (c + d)
    expr = BinOp('*', BinOp('+', Sym('a'), Sym('b')), BinOp('+', Sym('c'), Sym('d')))
    expanded = expand_expr(expr)
    # Should distribute fully
    assert isinstance(expanded, BinOp)


# ──────────────── Integration Tests ────────────────

def test_integration_diff_simplify_eval():
    """Differentiate, simplify, then evaluate."""
    f = parse("x^3 + 2*x^2 - x + 5")
    df = f.diff('x').simplify()
    val = df.evaluate({'x': 1.0})
    # d/dx(x^3 + 2x^2 - x + 5) = 3x^2 + 4x - 1
    # At x=1: 3 + 4 - 1 = 6
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
    # At x=1: cos(cos(1)) * (-sin(1))
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
    # d/dx(3x + 2y) = 3
    assert df_dx == Num(3)
    # d/dy(3x + 2y) = 2
    assert df_dy == Num(2)


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
        # Integration
        test_integration_diff_simplify_eval, test_parse_diff_simplify,
        test_chain_rule_complex, test_substitute_then_eval,
        test_partial_derivative,
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