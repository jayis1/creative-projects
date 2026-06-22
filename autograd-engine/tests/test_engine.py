"""Tests for the core autodiff engine (Value class)."""

import math
import pytest
from autograd_engine import Value
from autograd_engine.train import numerical_grad_check


class TestValueConstruction:
    def test_basic_construction(self):
        v = Value(5.0)
        assert v.data == 5.0
        assert v.grad == 0.0
        assert v._op == ""
        assert v._prev == ()

    def test_label(self):
        v = Value(3.0, label="x")
        assert v.label == "x"

    def test_int_input(self):
        v = Value(42)
        assert v.data == 42.0
        assert isinstance(v.data, float)

    def test_non_number_raises(self):
        with pytest.raises(TypeError, match="must be a number"):
            Value("hello")

    def test_repr(self):
        v = Value(3.14)
        assert "Value(data=3.14" in repr(v)

    def test_float_conversion(self):
        v = Value(3.0)
        assert float(v) == 3.0


class TestArithmetic:
    def test_add(self):
        a, b = Value(2.0), Value(3.0)
        c = a + b
        assert c.data == 5.0
        c.backward()
        assert a.grad == 1.0
        assert b.grad == 1.0

    def test_add_scalar(self):
        a = Value(2.0)
        c = a + 3.0
        assert c.data == 5.0
        c.backward()
        assert a.grad == 1.0

    def test_radd(self):
        a = Value(2.0)
        c = 3.0 + a
        assert c.data == 5.0

    def test_mul(self):
        a, b = Value(2.0), Value(3.0)
        c = a * b
        assert c.data == 6.0
        c.backward()
        assert a.grad == 3.0
        assert b.grad == 2.0

    def test_mul_scalar(self):
        a = Value(2.0)
        c = a * 3.0
        assert c.data == 6.0
        c.backward()
        assert a.grad == 3.0

    def test_rmul(self):
        a = Value(2.0)
        c = 3.0 * a
        assert c.data == 6.0

    def test_sub(self):
        a, b = Value(5.0), Value(3.0)
        assert (a - b).data == 2.0

    def test_rsub(self):
        a = Value(3.0)
        assert (5.0 - a).data == 2.0

    def test_neg(self):
        a = Value(3.0)
        assert (-a).data == -3.0

    def test_div(self):
        a, b = Value(6.0), Value(3.0)
        assert (a / b).data == 2.0

    def test_div_scalar(self):
        a = Value(6.0)
        assert (a / 3.0).data == 2.0

    def test_rtruediv(self):
        a = Value(2.0)
        assert (6.0 / a).data == 3.0

    def test_div_by_zero_value(self):
        a = Value(6.0)
        with pytest.raises(ZeroDivisionError):
            a / Value(0.0)

    def test_div_by_zero_scalar(self):
        a = Value(6.0)
        with pytest.raises(ZeroDivisionError):
            a / 0


class TestPow:
    def test_integer_pow(self):
        a = Value(3.0)
        c = a ** 2
        assert c.data == 9.0
        c.backward()
        assert a.grad == 6.0  # 2*3

    def test_fractional_pow_positive(self):
        a = Value(4.0)
        c = a ** 0.5
        assert abs(c.data - 2.0) < 1e-9
        c.backward()
        assert abs(a.grad - 0.25) < 1e-6  # 0.5 * 4^(-0.5) = 0.25

    def test_negative_integer_pow(self):
        a = Value(4.0)
        c = a ** -1
        assert abs(c.data - 0.25) < 1e-9
        c.backward()
        assert abs(a.grad - (-0.0625)) < 1e-6  # -1 * 4^(-2)

    def test_value_exponent(self):
        a = Value(2.0)
        b = Value(3.0)
        c = a ** b
        assert c.data == 8.0
        c.backward()
        assert abs(a.grad - 12.0) < 1e-6  # 3 * 2^2 = 12
        assert abs(b.grad - (8.0 * math.log(2.0))) < 1e-6  # 8 * ln(2)

    def test_zero_pow_zero_backward(self):
        a = Value(0.0)
        c = a ** 0
        assert c.data == 1.0
        c.backward()
        assert a.grad == 0.0

    def test_negative_base_fractional_raises(self):
        a = Value(-2.0)
        with pytest.raises(ValueError, match="negative base"):
            a ** 0.5


class TestTranscendentals:
    def test_relu_positive(self):
        a = Value(3.0)
        b = a.relu()
        assert b.data == 3.0
        b.backward()
        assert a.grad == 1.0

    def test_relu_negative(self):
        a = Value(-3.0)
        b = a.relu()
        assert b.data == 0.0
        b.backward()
        assert a.grad == 0.0

    def test_relu_zero(self):
        a = Value(0.0)
        b = a.relu()
        assert b.data == 0.0
        b.backward()
        assert a.grad == 0.0  # subgradient at 0

    def test_tanh(self):
        a = Value(0.0)
        b = a.tanh()
        assert b.data == 0.0
        b.backward()
        assert a.grad == 1.0  # 1 - tanh(0)^2 = 1

    def test_sigmoid(self):
        a = Value(0.0)
        b = a.sigmoid()
        assert abs(b.data - 0.5) < 1e-9
        b.backward()
        assert abs(a.grad - 0.25) < 1e-9  # s*(1-s) = 0.5*0.5

    def test_sigmoid_stable_large(self):
        a = Value(100.0)
        b = a.sigmoid()
        assert abs(b.data - 1.0) < 1e-9
        b.backward()
        # s*(1-s) ≈ 0 for large x
        assert abs(a.grad) < 1e-9

    def test_sigmoid_stable_large_negative(self):
        a = Value(-100.0)
        b = a.sigmoid()
        assert abs(b.data) < 1e-9
        b.backward()
        assert abs(a.grad) < 1e-9

    def test_exp(self):
        a = Value(0.0)
        b = a.exp()
        assert abs(b.data - 1.0) < 1e-9
        b.backward()
        assert abs(a.grad - 1.0) < 1e-9

    def test_log(self):
        a = Value(math.e)
        b = a.log()
        assert abs(b.data - 1.0) < 1e-9
        b.backward()
        assert abs(a.grad - 1.0 / math.e) < 1e-9

    def test_log_non_positive_raises(self):
        with pytest.raises(ValueError, match="positive data"):
            Value(0.0).log()
        with pytest.raises(ValueError, match="positive data"):
            Value(-1.0).log()


class TestBackprop:
    def test_gradient_accumulation(self):
        x = Value(3.0)
        y = x + x
        y.backward()
        assert y.data == 6.0
        assert x.grad == 2.0

    def test_backward_zeros_grads(self):
        x = Value(2.0)
        y = x ** 2
        y.backward()
        assert x.grad == 4.0
        # Second backward should zero first
        y2 = x ** 2
        y2.backward()
        assert x.grad == 4.0  # not 8.0

    def test_complex_graph(self):
        x = Value(1.0)
        y = Value(2.0)
        z = (x * y + x.tanh()).exp().log() + x ** 2
        z.backward()
        # Verify with numerical gradient check
        assert numerical_grad_check(
            lambda inp: (inp[0] * inp[1] + inp[0].tanh()).exp().log() + inp[0] ** 2,
            [Value(1.0), Value(2.0)], tol=1e-4
        )


class TestEquality:
    def test_identity_equality(self):
        a = Value(3.0)
        assert a == a

    def test_distinct_not_equal(self):
        a = Value(3.0)
        b = Value(3.0)
        assert a != b  # identity comparison

    def test_hash_consistent(self):
        a = Value(3.0)
        assert hash(a) == id(a)

    def test_not_iterable(self):
        a = Value(3.0)
        with pytest.raises(TypeError, match="not iterable"):
            list(a)