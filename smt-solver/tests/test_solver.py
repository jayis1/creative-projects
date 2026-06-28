"""Comprehensive test suite for the SMT solver."""

import pytest
from smt_solver import Solver, Model, SolverStatistics
from smt_solver.ast import (
    Var, App, NumConst, BoolConst, StrConst,
    And, Or, Not, Implies, Eq, Lt, Le, Gt, Ge,
    Add, Sub, Mul, Neg, Ite,
    BOOL, REAL, INT, STRING,
    collect_vars, is_atom, pre_order,
)
from smt_solver.exceptions import SMTError, ParseError


# ---------------------------------------------------------------------------
# SAT solver tests
# ---------------------------------------------------------------------------

class TestSATSolver:
    """Tests for the CDCL SAT solver."""

    def test_trivially_sat(self):
        s = Solver()
        s.parse_and_assert('(declare-const a Bool) (assert a)')
        assert s.check() == 'sat'

    def test_trivially_unsat(self):
        s = Solver()
        s.parse_and_assert('(declare-const a Bool) (assert a) (assert (not a))')
        assert s.check() == 'unsat'

    def test_implication_chain(self):
        s = Solver()
        s.parse_and_assert("""
        (declare-const a Bool)
        (declare-const b Bool)
        (declare-const c Bool)
        (assert (=> a b))
        (assert (=> b c))
        (assert (=> a c))
        """)
        assert s.check() == 'sat'

    def test_implication_chain_unsat(self):
        s = Solver()
        s.parse_and_assert("""
        (declare-const a Bool)
        (declare-const b Bool)
        (declare-const c Bool)
        (assert (=> a b))
        (assert (=> b c))
        (assert (not (=> a c)))
        """)
        assert s.check() == 'unsat'

    def test_xor_sat(self):
        s = Solver()
        s.parse_and_assert("""
        (declare-const a Bool)
        (declare-const b Bool)
        (assert (xor a b))
        """)
        assert s.check() == 'sat'

    def test_xor_unsat(self):
        s = Solver()
        s.parse_and_assert("""
        (declare-const a Bool)
        (declare-const b Bool)
        (assert (xor a b))
        (assert (= a b))
        """)
        assert s.check() == 'unsat'

    def test_boolean_equality(self):
        s = Solver()
        s.parse_and_assert("""
        (declare-const a Bool)
        (declare-const b Bool)
        (assert (= a b))
        (assert (not a))
        """)
        assert s.check() == 'sat'
        model = s.get_model()
        assert model.bool_vars['a'] == False
        assert model.bool_vars['b'] == False

    def test_complex_boolean(self):
        s = Solver()
        s.parse_and_assert("""
        (declare-const a Bool)
        (declare-const b Bool)
        (declare-const c Bool)
        (declare-const d Bool)
        (assert (or (and a b) (and c d)))
        (assert (not (and a b)))
        (assert (not c))
        """)
        assert s.check() == 'unsat'

    def test_boolean_model_correct(self):
        """Verify that Boolean variables get correct model values."""
        s = Solver()
        s.parse_and_assert('(declare-const b Bool)')
        s.parse_and_assert('(assert b)')
        assert s.check() == 'sat'
        model = s.get_model()
        assert model.bool_vars['b'] == True

    def test_boolean_model_false(self):
        s = Solver()
        s.parse_and_assert('(declare-const b Bool)')
        s.parse_and_assert('(assert (not b))')
        assert s.check() == 'sat'
        model = s.get_model()
        assert model.bool_vars['b'] == False


# ---------------------------------------------------------------------------
# LRA theory tests
# ---------------------------------------------------------------------------

class TestLRA:
    """Tests for Linear Real Arithmetic."""

    def test_simple_sat(self):
        s = Solver()
        s.parse_and_assert('(declare-const x Real)')
        s.parse_and_assert('(assert (> x 5.0))')
        s.parse_and_assert('(assert (< x 10.0))')
        assert s.check() == 'sat'

    def test_simple_unsat(self):
        s = Solver()
        s.parse_and_assert('(declare-const x Real)')
        s.parse_and_assert('(assert (> x 5.0))')
        s.parse_and_assert('(assert (< x 3.0))')
        assert s.check() == 'unsat'

    def test_equality_sat(self):
        s = Solver()
        s.parse_and_assert('(declare-const x Real)')
        s.parse_and_assert('(declare-const y Real)')
        s.parse_and_assert('(assert (= y (* 2.0 x)))')
        s.parse_and_assert('(assert (> x 5.0))')
        s.parse_and_assert('(assert (> y 12.0))')
        assert s.check() == 'sat'

    def test_model_values(self):
        s = Solver()
        s.parse_and_assert('(declare-const x Real)')
        s.parse_and_assert('(assert (> x 5.0))')
        s.parse_and_assert('(assert (< x 10.0))')
        assert s.check() == 'sat'
        model = s.get_model()
        x_val = model.real_vars['x']
        assert 5.0 < x_val < 10.0

    def test_multi_variable(self):
        s = Solver()
        s.parse_and_assert('(declare-const x Real)')
        s.parse_and_assert('(declare-const y Real)')
        s.parse_and_assert('(declare-const z Real)')
        s.parse_and_assert('(assert (>= (+ x y z) 10.0))')
        s.parse_and_assert('(assert (<= x 3.0))')
        s.parse_and_assert('(assert (<= y 4.0))')
        s.parse_and_assert('(assert (<= z 5.0))')
        s.parse_and_assert('(assert (>= x 0.0))')
        s.parse_and_assert('(assert (>= y 0.0))')
        s.parse_and_assert('(assert (>= z 0.0))')
        assert s.check() == 'sat'

    def test_multi_variable_unsat(self):
        s = Solver()
        s.parse_and_assert('(declare-const x Real)')
        s.parse_and_assert('(declare-const y Real)')
        s.parse_and_assert('(declare-const z Real)')
        s.parse_and_assert('(assert (>= (+ x y z) 100.0))')
        s.parse_and_assert('(assert (<= x 1.0))')
        s.parse_and_assert('(assert (<= y 1.0))')
        s.parse_and_assert('(assert (<= z 1.0))')
        assert s.check() == 'unsat'

    def test_disequality_sat(self):
        s = Solver()
        s.parse_and_assert('(declare-const a Real)')
        s.parse_and_assert('(declare-const b Real)')
        s.parse_and_assert('(assert (not (= a b)))')
        assert s.check() == 'sat'

    def test_three_disequalities(self):
        """Three disequalities between three unconstrained vars should be sat."""
        s = Solver()
        s.parse_and_assert('(declare-const a Real)')
        s.parse_and_assert('(declare-const b Real)')
        s.parse_and_assert('(declare-const c Real)')
        s.parse_and_assert('(assert (not (= a b)))')
        s.parse_and_assert('(assert (not (= a c)))')
        s.parse_and_assert('(assert (not (= b c)))')
        assert s.check() == 'sat'

    def test_distinct_sat(self):
        s = Solver()
        s.parse_and_assert('(declare-const a Real)')
        s.parse_and_assert('(declare-const b Real)')
        s.parse_and_assert('(declare-const c Real)')
        s.parse_and_assert('(assert (distinct a b c))')
        s.parse_and_assert('(assert (> a 0.0))')
        s.parse_and_assert('(assert (> b 0.0))')
        s.parse_and_assert('(assert (> c 0.0))')
        s.parse_and_assert('(assert (< a 10.0))')
        s.parse_and_assert('(assert (< b 10.0))')
        s.parse_and_assert('(assert (< c 10.0))')
        assert s.check() == 'sat'

    def test_distinct_model(self):
        """The model for distinct vars should actually satisfy it."""
        s = Solver()
        s.parse_and_assert('(declare-const a Real)')
        s.parse_and_assert('(declare-const b Real)')
        s.parse_and_assert('(declare-const c Real)')
        s.parse_and_assert('(assert (distinct a b c))')
        assert s.check() == 'sat'
        model = s.get_model()
        a, b, c = model.real_vars['a'], model.real_vars['b'], model.real_vars['c']
        assert a != b
        assert a != c
        assert b != c

    def test_division(self):
        s = Solver()
        s.parse_and_assert('(declare-const x Real)')
        s.parse_and_assert('(assert (= x (/ 10.0 2.0)))')
        s.parse_and_assert('(assert (> x 4.0))')
        assert s.check() == 'sat'


# ---------------------------------------------------------------------------
# EUF theory tests
# ---------------------------------------------------------------------------

class TestEUF:
    """Tests for Uninterpreted Functions with Equality."""

    def test_basic_unsat(self):
        """a=b, f(a)=c, f(b)!=c should be unsat."""
        s = Solver()
        s.parse_and_assert("""
        (declare-fun f (Real) Real)
        (declare-const a Real)
        (declare-const b Real)
        (declare-const c Real)
        (assert (= a b))
        (assert (= (f a) c))
        (assert (not (= (f b) c)))
        """)
        assert s.check() == 'unsat'

    def test_congruence(self):
        """If a=b, then f(a)=f(b) by congruence."""
        s = Solver()
        s.parse_and_assert("""
        (declare-fun f (Real) Real)
        (declare-const a Real)
        (declare-const b Real)
        (assert (= a b))
        (assert (not (= (f a) (f b))))
        """)
        assert s.check() == 'unsat'

    def test_euf_sat(self):
        s = Solver()
        s.parse_and_assert("""
        (declare-fun f (Real) Real)
        (declare-fun g (Real) Real)
        (declare-const a Real)
        (declare-const b Real)
        (assert (= a b))
        (assert (= (f a) (g b)))
        (assert (= (f (g a)) (g (f b))))
        """)
        assert s.check() == 'sat'

    def test_nested_congruence(self):
        """Nested congruence: a=b implies f(g(a))=f(g(b))."""
        s = Solver()
        s.parse_and_assert("""
        (declare-fun f (Real) Real)
        (declare-fun g (Real) Real)
        (declare-const a Real)
        (declare-const b Real)
        (assert (= a b))
        (assert (not (= (f (g a)) (f (g b)))))
        """)
        assert s.check() == 'unsat'


# ---------------------------------------------------------------------------
# ITE tests
# ---------------------------------------------------------------------------

class TestITE:
    """Tests for if-then-else."""

    def test_ite_boolean(self):
        s = Solver()
        s.parse_and_assert("""
        (declare-const b Bool)
        (declare-const c Bool)
        (assert (= c (ite b true false)))
        (assert b)
        """)
        assert s.check() == 'sat'
        model = s.get_model()
        assert model.bool_vars['b'] == True
        assert model.bool_vars['c'] == True

    def test_ite_arithmetic(self):
        """ITE in arithmetic context should produce correct models."""
        s = Solver()
        s.parse_and_assert("""
        (declare-const y Real)
        (declare-const b Bool)
        (assert (= y (ite b 1.0 2.0)))
        (assert b)
        """)
        assert s.check() == 'sat'
        model = s.get_model()
        assert model.bool_vars['b'] == True
        assert abs(model.real_vars['y'] - 1.0) < 1e-9

    def test_ite_arithmetic_else(self):
        s = Solver()
        s.parse_and_assert("""
        (declare-const y Real)
        (declare-const b Bool)
        (assert (= y (ite b 1.0 2.0)))
        (assert (not b))
        """)
        assert s.check() == 'sat'
        model = s.get_model()
        assert model.bool_vars['b'] == False
        assert abs(model.real_vars['y'] - 2.0) < 1e-9

    def test_ite_arithmetic_unsat(self):
        s = Solver()
        s.parse_and_assert("""
        (declare-const y Real)
        (declare-const b Bool)
        (assert (= y (ite b 1.0 2.0)))
        (assert b)
        (assert (> y 1.5))
        """)
        assert s.check() == 'unsat'


# ---------------------------------------------------------------------------
# Parser tests
# ---------------------------------------------------------------------------

class TestParser:
    """Tests for the SMT-LIB parser."""

    def test_declare_const(self):
        s = Solver()
        s.parse_and_assert('(declare-const x Real)')
        assert 'x' in s._declared
        assert s._declared['x'][0] == REAL

    def test_declare_fun(self):
        s = Solver()
        s.parse_and_assert('(declare-fun f (Real) Real)')
        assert 'f' in s._declared

    def test_let_binding(self):
        s = Solver()
        s.parse_and_assert("""
        (declare-const x Real)
        (assert (let ((y (+ x 1.0))) (> y 5.0)))
        """)
        assert s.check() == 'sat'

    def test_chained_equality(self):
        s = Solver()
        s.parse_and_assert("""
        (declare-const a Real)
        (declare-const b Real)
        (declare-const c Real)
        (assert (= a b c))
        (assert (not (= a c)))
        """)
        assert s.check() == 'unsat'

    def test_nary_comparison(self):
        s = Solver()
        s.parse_and_assert("""
        (declare-const a Real)
        (declare-const b Real)
        (declare-const c Real)
        (assert (< a b c))
        """)
        assert s.check() == 'sat'

    def test_parse_error(self):
        with pytest.raises(ParseError):
            s = Solver()
            s.parse_and_assert('(declare-const x)')  # missing sort

    def test_undeclared_symbol(self):
        with pytest.raises(ParseError):
            s = Solver()
            s.parse_and_assert('(assert (> x 5.0))')  # x not declared

    def test_string_literal(self):
        s = Solver()
        s.parse_and_assert('(declare-const s String)')
        s.parse_and_assert('(assert (= (str.len s) 5))')
        result = s.check()
        # String theory is limited; just verify it doesn't crash
        assert result in ('sat', 'unknown')

    def test_named_assertion(self):
        s = Solver()
        s.parse_and_assert('(declare-const x Real)')
        s.parse_and_assert('(assert (! (> x 0.0) :named pos))')
        assert s.check() == 'sat'
        assert 'pos' in s._named_assertions


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------

class TestModel:
    """Tests for model generation."""

    def test_model_to_smt(self):
        m = Model()
        m.bool_vars['a'] = True
        m.real_vars['x'] = 5.0
        smt = m.to_smt()
        assert '(define-fun a () Bool true)' in smt
        assert '(define-fun x () Real 5.0)' in smt

    def test_model_to_dict(self):
        m = Model()
        m.bool_vars['b'] = False
        m.real_vars['y'] = 3.14
        d = m.to_dict()
        assert d['bool']['b'] == False
        assert d['real']['y'] == 3.14

    def test_model_str(self):
        m = Model()
        m.bool_vars['flag'] = True
        m.real_vars['val'] = 42.0
        s = str(m)
        assert 'flag -> true' in s
        assert 'val -> 42.0' in s


# ---------------------------------------------------------------------------
# Push/pop tests
# ---------------------------------------------------------------------------

class TestPushPop:
    """Tests for incremental push/pop."""

    def test_push_pop_basic(self):
        s = Solver()
        s.parse_and_assert('(declare-const x Real)')
        s.parse_and_assert('(assert (> x 0.0))')
        s.push()
        s.parse_and_assert('(assert (> x 100.0))')
        assert s.check() == 'sat'
        s.pop()
        s.parse_and_assert('(assert (< x 50.0))')
        assert s.check() == 'sat'


# ---------------------------------------------------------------------------
# Theory combination tests
# ---------------------------------------------------------------------------

class TestTheoryCombination:
    """Tests for combined theories."""

    def test_euf_lra(self):
        s = Solver()
        s.parse_and_assert("""
        (declare-fun f (Real) Real)
        (declare-const a Real)
        (declare-const b Real)
        (declare-const c Real)
        (assert (= a b))
        (assert (> a 5.0))
        (assert (< b 10.0))
        (assert (= (f a) c))
        (assert (= (f b) c))
        """)
        assert s.check() == 'sat'


# ---------------------------------------------------------------------------
# AST tests
# ---------------------------------------------------------------------------

class TestAST:
    """Tests for AST construction and traversal."""

    def test_collect_vars(self):
        x = Var('x', REAL)
        y = Var('y', REAL)
        term = Add(x, y)
        vars = collect_vars(term)
        assert x in vars
        assert y in vars

    def test_is_atom(self):
        x = Var('x', REAL)
        atom = Gt(x, NumConst(5.0))
        non_atom = And(atom, atom)
        assert is_atom(atom)
        assert not is_atom(non_atom)

    def test_pre_order(self):
        x = Var('x', REAL)
        y = Var('y', REAL)
        atom = Gt(x, NumConst(5.0))
        formula = And(atom, Lt(y, NumConst(10.0)))
        subs = list(pre_order(formula))
        assert formula in subs
        assert atom in subs

    def test_str_const(self):
        s = StrConst("hello")
        assert s.value == "hello"
        assert str(s) == '"hello"'
        assert s.sort == STRING

    def test_num_const_int(self):
        n = NumConst(5, is_int=True)
        assert str(n) == '5'

    def test_num_const_real(self):
        n = NumConst(5.0, is_int=False)
        assert str(n) == '5.0'


# ---------------------------------------------------------------------------
# Statistics tests
# ---------------------------------------------------------------------------

class TestStatistics:
    """Tests for solver statistics."""

    def test_stats_after_check(self):
        s = Solver()
        s.parse_and_assert('(declare-const x Real)')
        s.parse_and_assert('(assert (> x 5.0))')
        s.parse_and_assert('(assert (< x 10.0))')
        s.check()
        stats = s.get_statistics()
        assert stats.assertions == 2
        assert stats.check_time >= 0

    def test_stats_str(self):
        stats = SolverStatistics()
        stats.assertions = 5
        stats.atoms = 3
        s = str(stats)
        assert "Assertions:" in s
        assert "5" in s


# ---------------------------------------------------------------------------
# Evaluate tests
# ---------------------------------------------------------------------------

class TestEvaluate:
    """Tests for term evaluation under a model."""

    def test_evaluate_var(self):
        s = Solver()
        s.parse_and_assert('(declare-const x Real)')
        s.parse_and_assert('(assert (= x 5.0))')
        s.check()
        val = s.evaluate(Var('x', REAL))
        assert val == 5.0

    def test_evaluate_add(self):
        s = Solver()
        s.parse_and_assert('(declare-const x Real)')
        s.parse_and_assert('(declare-const y Real)')
        s.parse_and_assert('(assert (= x 3.0))')
        s.parse_and_assert('(assert (= y 4.0))')
        s.check()
        val = s.evaluate(Add(Var('x', REAL), Var('y', REAL)))
        assert val == 7.0


# ---------------------------------------------------------------------------
# LRA LinearExpr tests
# ---------------------------------------------------------------------------

class TestLinearExpr:
    """Tests for the LinearExpr data structure."""

    def test_constant(self):
        from smt_solver.theory_lra import LinearExpr
        e = LinearExpr.constant(5.0)
        assert e.is_constant()
        assert e.const == 5.0

    def test_variable(self):
        from smt_solver.theory_lra import LinearExpr
        e = LinearExpr.variable('x')
        assert not e.is_constant()
        assert 'x' in e.vars

    def test_addition(self):
        from smt_solver.theory_lra import LinearExpr
        a = LinearExpr.variable('x', 2.0)
        b = LinearExpr.variable('y', 3.0)
        c = a + b
        assert c.coeffs['x'] == 2.0
        assert c.coeffs['y'] == 3.0

    def test_subtraction(self):
        from smt_solver.theory_lra import LinearExpr
        a = LinearExpr.variable('x', 5.0)
        b = LinearExpr.variable('y', 2.0)
        c = a - b
        assert c.coeffs['x'] == 5.0
        assert c.coeffs['y'] == -2.0

    def test_scale(self):
        from smt_solver.theory_lra import LinearExpr
        a = LinearExpr.variable('x', 2.0)
        c = a.scale(3.0)
        assert c.coeffs['x'] == 6.0

    def test_evaluate(self):
        from smt_solver.theory_lra import LinearExpr
        e = LinearExpr(coeffs={'x': 2.0, 'y': 3.0}, const=1.0)
        assert e.evaluate({'x': 1.0, 'y': 2.0}) == 9.0


# ---------------------------------------------------------------------------
# Congruence closure tests
# ---------------------------------------------------------------------------

class TestCongruenceClosure:
    """Tests for the EUF congruence closure algorithm."""

    def test_basic_eq(self):
        from smt_solver.theory_euf import CongruenceClosure
        cc = CongruenceClosure()
        a = Var('a', REAL)
        b = Var('b', REAL)
        cc.assert_eq(a, b)
        assert cc.are_equal(a, b)

    def test_basic_diseq(self):
        from smt_solver.theory_euf import CongruenceClosure
        cc = CongruenceClosure()
        a = Var('a', REAL)
        b = Var('b', REAL)
        assert not cc.are_equal(a, b)

    def test_congruence(self):
        from smt_solver.theory_euf import CongruenceClosure
        cc = CongruenceClosure()
        a = Var('a', REAL)
        b = Var('b', REAL)
        fa = App('f', (a,), REAL)
        fb = App('f', (b,), REAL)
        cc.assert_eq(a, b)
        assert cc.are_equal(fa, fb)

    def test_equivalence_classes(self):
        from smt_solver.theory_euf import CongruenceClosure
        cc = CongruenceClosure()
        a = Var('a', REAL)
        b = Var('b', REAL)
        cc.assert_eq(a, b)
        classes = cc.equivalence_classes()
        assert len(classes) >= 1


# ---------------------------------------------------------------------------
# Programmatic API tests
# ---------------------------------------------------------------------------

class TestProgrammaticAPI:
    """Tests for the programmatic Python API."""

    def test_declare_and_assert(self):
        s = Solver()
        x = s.declare_const('x', REAL)
        s.assert_term(Gt(x, NumConst(5.0)))
        s.assert_term(Lt(x, NumConst(10.0)))
        assert s.check() == 'sat'

    def test_reset(self):
        s = Solver()
        s.parse_and_assert('(declare-const x Real)')
        s.parse_and_assert('(assert (> x 5.0))')
        assert s.check() == 'sat'
        s.reset()
        s.parse_and_assert('(declare-const x Real)')
        s.parse_and_assert('(assert (< x 0.0))')
        assert s.check() == 'sat'

    def test_check_sat_convenience(self):
        from smt_solver.solver import check_sat
        x = Var('x', REAL)
        result = check_sat(And(Gt(x, NumConst(5.0)), Lt(x, NumConst(10.0))))
        assert result == 'sat'


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_no_assertions(self):
        s = Solver()
        assert s.check() == 'sat'

    def test_empty_model(self):
        s = Solver()
        s.check()
        m = s.get_model()
        assert m is not None

    def test_multiple_declarations_same_name(self):
        s = Solver()
        s.parse_and_assert('(declare-const x Real)')
        s.parse_and_assert('(declare-const x Real)')  # should not crash
        s.parse_and_assert('(assert (> x 0.0))')
        assert s.check() == 'sat'

    def test_nested_let(self):
        s = Solver()
        s.parse_and_assert("""
        (declare-const x Real)
        (assert (let ((y (+ x 1.0)))
                  (let ((z (+ y 1.0)))
                    (> z 5.0))))
        """)
        assert s.check() == 'sat'

    def test_large_system(self):
        """Test with a moderately large system."""
        s = Solver()
        for i in range(10):
            s.parse_and_assert(f'(declare-const x{i} Real)')
            s.parse_and_assert(f'(assert (> x{i} {i}.0))')
            s.parse_and_assert(f'(assert (< x{i} {i+2}.0))')
        assert s.check() == 'sat'

    def test_unary_minus(self):
        s = Solver()
        s.parse_and_assert('(declare-const x Real)')
        s.parse_and_assert('(assert (= x (- 5.0)))')
        s.parse_and_assert('(assert (< x 0.0))')
        assert s.check() == 'sat'

    def test_nested_arithmetic(self):
        s = Solver()
        s.parse_and_assert('(declare-const x Real)')
        s.parse_and_assert('(assert (= (+ (* 2.0 x) 3.0) 11.0))')
        result = s.check()
        assert result == 'sat'
        if result == 'sat':
            model = s.get_model()
            x = model.real_vars.get('x', 0.0)
            assert abs(2.0 * x + 3.0 - 11.0) < 1e-6