"""Tests for extended activation functions."""

import math
import pytest
from autograd_engine import Value
from autograd_engine.activations import (
    leaky_relu, elu, gelu, swish, softplus, mish, selu,
    hard_tanh, hard_sigmoid, get_activation, ACTIVATION_REGISTRY,
)
from autograd_engine.train import numerical_grad_check


class TestLeakyReLU:
    def test_positive(self):
        x = Value(3.0)
        y = leaky_relu(x)
        assert y.data == 3.0
        y.backward()
        assert x.grad == 1.0

    def test_negative(self):
        x = Value(-3.0)
        y = leaky_relu(x, slope=0.1)
        assert abs(y.data - (-0.3)) < 1e-9
        y.backward()
        assert abs(x.grad - 0.1) < 1e-9

    def test_gradient_check(self):
        def f(inp):
            return leaky_relu(inp[0])
        assert numerical_grad_check(f, [Value(2.0)], tol=1e-4)
        assert numerical_grad_check(f, [Value(-2.0)], tol=1e-4)


class TestELU:
    def test_positive(self):
        x = Value(3.0)
        y = elu(x)
        assert y.data == 3.0
        y.backward()
        assert x.grad == 1.0

    def test_negative(self):
        x = Value(-1.0)
        y = elu(x, alpha=1.0)
        assert abs(y.data - (math.exp(-1.0) - 1.0)) < 1e-9
        y.backward()
        assert abs(x.grad - math.exp(-1.0)) < 1e-6

    def test_gradient_check(self):
        def f(inp):
            return elu(inp[0])
        assert numerical_grad_check(f, [Value(2.0)], tol=1e-4)
        assert numerical_grad_check(f, [Value(-0.5)], tol=1e-4)


class TestGELU:
    def test_at_zero(self):
        x = Value(0.0)
        y = gelu(x)
        assert y.data == 0.0

    def test_gradient_check(self):
        def f(inp):
            return gelu(inp[0])
        assert numerical_grad_check(f, [Value(1.5)], tol=1e-3)
        assert numerical_grad_check(f, [Value(-0.5)], tol=1e-3)


class TestSwish:
    def test_at_zero(self):
        x = Value(0.0)
        y = swish(x)
        assert y.data == 0.0

    def test_gradient_check(self):
        def f(inp):
            return swish(inp[0])
        assert numerical_grad_check(f, [Value(1.0)], tol=1e-3)
        assert numerical_grad_check(f, [Value(-1.0)], tol=1e-3)


class TestSoftplus:
    def test_at_zero(self):
        x = Value(0.0)
        y = softplus(x)
        assert abs(y.data - math.log(2)) < 1e-9

    def test_gradient_check(self):
        def f(inp):
            return softplus(inp[0])
        assert numerical_grad_check(f, [Value(1.0)], tol=1e-3)
        assert numerical_grad_check(f, [Value(-2.0)], tol=1e-3)


class TestMish:
    def test_at_zero(self):
        x = Value(0.0)
        y = mish(x)
        assert y.data == 0.0

    def test_gradient_check(self):
        def f(inp):
            return mish(inp[0])
        assert numerical_grad_check(f, [Value(1.0)], tol=1e-3)


class TestSELU:
    def test_positive(self):
        x = Value(1.0)
        y = selu(x)
        assert abs(y.data - 1.0507) < 1e-4

    def test_gradient_check(self):
        def f(inp):
            return selu(inp[0])
        assert numerical_grad_check(f, [Value(1.0)], tol=1e-3)
        assert numerical_grad_check(f, [Value(-1.0)], tol=1e-3)


class TestHardTanh:
    def test_clamp(self):
        assert hard_tanh(Value(5.0)).data == 1.0
        assert hard_tanh(Value(-5.0)).data == -1.0
        assert hard_tanh(Value(0.5)).data == 0.5

    def test_gradient_inside(self):
        x = Value(0.5)
        y = hard_tanh(x)
        y.backward()
        assert x.grad == 1.0

    def test_gradient_outside(self):
        x = Value(5.0)
        y = hard_tanh(x)
        y.backward()
        assert x.grad == 0.0


class TestHardSigmoid:
    def test_clamp(self):
        assert hard_sigmoid(Value(5.0)).data == 1.0
        assert hard_sigmoid(Value(-5.0)).data == 0.0
        assert abs(hard_sigmoid(Value(0.0)).data - 0.5) < 1e-9

    def test_gradient_inside(self):
        x = Value(0.0)
        y = hard_sigmoid(x)
        y.backward()
        assert abs(x.grad - 0.2) < 1e-9


class TestActivationRegistry:
    def test_get_activation(self):
        fn = get_activation("relu")
        assert fn(Value(3.0)).data == 3.0

    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown activation"):
            get_activation("bogus")

    def test_registry_has_all(self):
        expected = {
            "tanh", "relu", "sigmoid", "linear", "none",
            "leaky_relu", "elu", "gelu", "swish", "softplus",
            "mish", "selu", "hard_tanh", "hard_sigmoid",
        }
        assert expected.issubset(set(ACTIVATION_REGISTRY.keys()))