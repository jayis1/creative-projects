#!/usr/bin/env python3
"""Bug hunt tests for autograd-engine.

Each test reproduces a specific bug, then (after the fix) verifies the fix works.
Run with: python3 test_bugs.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import math
from autograd_engine import Value, MLP
from autograd_engine.ops import softmax, cross_entropy, max_value
from autograd_engine.nn import _xavier, _he, Neuron, Layer
from autograd_engine.train import (
    SGD, Adam, train, mean_squared_error, numerical_grad_check,
    binary_cross_entropy_with_logits,
)


# --------------------------------------------------------------------------- #
# Bug A: Value(0.0) ** 0 crashes on backward
# --------------------------------------------------------------------------- #
def test_bug_a_pow_zero_base_zero_exp():
    """Value(0)**0 should not crash on backward.

    The gradient of x**0 = 1 wrt x is 0 everywhere, including x=0.
    Bug: the backward closure computes `0 * 0.0**(-1)` which raises
    ZeroDivisionError because Python evaluates 0.0**(-1) before
    multiplying by 0.
    """
    x = Value(0.0)
    y = x ** 0
    assert y.data == 1.0  # 0**0 = 1 by convention
    y.backward()  # this should not crash
    assert x.grad == 0.0  # d/dx(x**0) = 0
    print("  Bug A: PASS — Value(0)**0 backward works")


# --------------------------------------------------------------------------- #
# Bug B: Value(-2.0) ** 0.5 gives confusing error
# --------------------------------------------------------------------------- #
def test_bug_b_negative_base_fractional_exp():
    """Value(-2)**0.5 should raise a clear ValueError, not a confusing TypeError.

    Bug: Python computes (-2.0)**0.5 as a complex number, which then
    fails in Value.__init__ with a generic TypeError about data type.
    """
    x = Value(-2.0)
    try:
        y = x ** 0.5
        # If no error, the result should be a real number (or we should
        # have a clear ValueError)
        assert isinstance(y.data, (int, float))
        print("  Bug B: PASS — negative base fractional exp handled")
    except (ValueError, TypeError) as e:
        # A clear ValueError is acceptable (better than confusing TypeError)
        assert "negative" in str(e).lower() or "complex" in str(e).lower() or "positive" in str(e).lower(), \
            f"Error message should be clear, got: {e}"
        print(f"  Bug B: PASS — clear error raised: {e}")


# --------------------------------------------------------------------------- #
# Bug C: Xavier init uses wrong fan-out dimension
# --------------------------------------------------------------------------- #
def test_bug_c_xavier_fanout():
    """Xavier init should use the actual layer output size, not nin for both.

    Bug: Neuron calls _xavier(nin, nin) — using nin as both fan-in and
    fan-out. The correct Xavier/Glorot uniform uses (fan_in + fan_out).
    With the bug, a layer with nin=3, nout=10 gets init scale sqrt(6/6)=1.0
    instead of the correct sqrt(6/13)≈0.679.
    """
    # After fix, Neuron should accept nout and use it for Xavier scale
    n = Neuron(3, nonlin=True, activation="tanh", init="xavier", nout=10)
    # Check that weights are within Xavier bounds: sqrt(6/(3+10)) ≈ 0.679
    limit = math.sqrt(6.0 / (3 + 10))
    for w in n.w:
        assert abs(w.data) <= limit + 1e-10, \
            f"Weight {w.data} outside Xavier bound ±{limit}"
    print(f"  Bug C: PASS — Xavier uses correct fan-out (limit={limit:.4f})")


# --------------------------------------------------------------------------- #
# Bug D: __eq__/__hash__ contract violation
# --------------------------------------------------------------------------- #
def test_bug_d_eq_hash_contract():
    """Value objects that are __eq__ must have the same __hash__.

    Bug: __eq__ compared by .data but __hash__ returned id(self).
    Two different Value objects with the same data compared equal but
    hashed differently, violating Python's contract. This caused subtle
    bugs when Values were used in sets or dicts.

    Fix: __eq__ now uses identity (self is other), which is correct for
    mutable graph nodes and consistent with id-based __hash__.
    """
    a = Value(3.0)
    b = Value(3.0)

    # Different Value objects should not be equal (identity comparison)
    assert a != b, "Different Value objects should not be equal"
    assert hash(a) != hash(b), "Different objects should hash differently"

    # Same object should be equal to itself and hash consistently
    assert a == a, "Value should equal itself"
    assert hash(a) == hash(a), "Same object should hash consistently"
    print("  Bug D: PASS — identity-based eq (contract-safe)")


# --------------------------------------------------------------------------- #
# Additional edge case tests
# --------------------------------------------------------------------------- #
def test_edge_relu_at_zero_backward():
    """relu at exactly 0 should have a defined subgradient (0 is fine)."""
    x = Value(0.0)
    y = x.relu()
    assert y.data == 0.0
    y.backward()
    # subgradient at 0: 0 is a valid choice
    assert x.grad == 0.0
    print("  Edge: PASS — relu(0) backward = 0")


def test_edge_div_by_zero_clear_error():
    """Division by zero should give a clear ZeroDivisionError."""
    x = Value(5.0)
    try:
        y = x / 0
        assert False, "Should have raised ZeroDivisionError"
    except ZeroDivisionError:
        pass

    try:
        y = x / Value(0.0)
        assert False, "Should have raised ZeroDivisionError"
    except ZeroDivisionError:
        pass
    print("  Edge: PASS — division by zero raises clear error")


def test_edge_log_of_nonpositive():
    """log() of non-positive should raise ValueError."""
    try:
        Value(0.0).log()
        assert False, "Should have raised ValueError"
    except ValueError:
        pass
    try:
        Value(-1.0).log()
        assert False, "Should have raised ValueError"
    except ValueError:
        pass
    print("  Edge: PASS — log of non-positive raises ValueError")


def test_gradient_accumulation_reuse():
    """Gradients should accumulate when a node is used multiple times."""
    x = Value(3.0)
    y = x + x  # y = 2x, dy/dx = 2
    y.backward()
    assert abs(x.grad - 2.0) < 1e-10, f"Expected grad=2.0, got {x.grad}"
    print("  Edge: PASS — gradient accumulation for reused node")


def test_numerical_grad_check_complex():
    """Gradient check with a complex function."""
    def f(inputs):
        x, y, z = inputs
        return (x * y + z.tanh()).sigmoid() * x.exp()

    inputs = [Value(0.5), Value(-1.2), Value(0.8)]
    ok = numerical_grad_check(f, inputs, eps=1e-6, tol=1e-4)
    assert ok, "Numerical gradient check failed"
    print("  Edge: PASS — gradient check on complex function")


def test_pow_negative_integer_exponent():
    """Value ** -1 should work correctly for non-zero base."""
    x = Value(4.0)
    y = x ** -1  # 1/x = 0.25, dy/dx = -1/x^2 = -0.0625
    assert abs(y.data - 0.25) < 1e-10
    y.backward()
    assert abs(x.grad - (-1.0 / 16.0)) < 1e-10, f"Expected -0.0625, got {x.grad}"
    print("  Edge: PASS — negative integer exponent")


def test_pow_fractional_exponent_positive_base():
    """Value ** 0.5 should work for positive base."""
    x = Value(9.0)
    y = x ** 0.5  # sqrt(9) = 3, dy/dx = 0.5 * x^(-0.5) = 0.5/3 = 0.1667
    assert abs(y.data - 3.0) < 1e-10
    y.backward()
    expected = 0.5 * 9.0 ** (-0.5)
    assert abs(x.grad - expected) < 1e-6, f"Expected {expected}, got {x.grad}"
    print("  Edge: PASS — fractional exponent with positive base")


def test_mlp_input_length_validation():
    """MLP should validate input length."""
    model = MLP(3, [4, 1])
    try:
        model([1.0, 2.0])  # only 2 inputs, expects 3
        assert False, "Should have raised ValueError"
    except ValueError:
        pass
    print("  Edge: PASS — input length validation")


def test_softmax_sums_to_one():
    """Softmax outputs should sum to 1.0."""
    logits = [Value(v) for v in [1.0, 2.0, 3.0, -0.5, 0.0]]
    probs = softmax(logits)
    total = sum(p.data for p in probs)
    assert abs(total - 1.0) < 1e-10, f"Softmax sums to {total}, not 1.0"
    print("  Edge: PASS — softmax sums to 1.0")


def test_cross_entropy_gradient():
    """Cross-entropy gradient should match softmax - 1_hot."""
    logits = [Value(1.0), Value(2.0), Value(0.5)]
    target = 1  # class 1 is correct
    loss = cross_entropy(logits, target)
    loss.backward()
    # gradient of CE wrt logits = softmax - one_hot
    sm = [math.exp(l.data) for l in logits]
    total = sum(sm)
    sm = [s / total for s in sm]
    for i, (logit, expected_grad) in enumerate(zip(logits, sm)):
        expected = expected_grad - (1.0 if i == target else 0.0)
        assert abs(logit.grad - expected) < 1e-6, \
            f"Logit {i} grad: expected {expected}, got {logit.grad}"
    print("  Edge: PASS — cross-entropy gradient correct")


def test_bce_with_logits_gradient():
    """BCE with logits gradient should be sigmoid(x) - target."""
    logit = Value(1.5)
    target = 1.0
    loss = binary_cross_entropy_with_logits([logit], [target])
    loss.backward()
    expected = 1.0 / (1.0 + math.exp(-1.5)) - target  # sigmoid(1.5) - 1
    assert abs(logit.grad - expected) < 1e-6, \
        f"BCE grad: expected {expected}, got {logit.grad}"
    print("  Edge: PASS — BCE gradient correct")


def test_adam_converges():
    """Adam should converge on a simple problem."""
    xs = [[0, 0], [0, 1], [1, 0], [1, 1]]
    ys = [0, 1, 1, 0]
    model = MLP(2, [8, 8, 1], activation="tanh")
    opt = Adam(model.parameters(), lr=0.01)
    hist = train(model, xs, ys, epochs=200, optimizer=opt)
    assert hist[-1] < 0.1, f"Adam didn't converge: loss={hist[-1]}"
    print(f"  Edge: PASS — Adam converged (final loss: {hist[-1]:.6f})")


def test_sgd_momentum_converges():
    """SGD with momentum should converge."""
    xs = [[0, 0], [0, 1], [1, 0], [1, 1]]
    ys = [0, 1, 1, 0]
    model = MLP(2, [8, 8, 1], activation="tanh")
    opt = SGD(model.parameters(), lr=0.1, momentum=0.9)
    hist = train(model, xs, ys, epochs=200, optimizer=opt)
    assert hist[-1] < 0.1, f"SGD+momentum didn't converge: loss={hist[-1]}"
    print(f"  Edge: PASS — SGD+momentum converged (final loss: {hist[-1]:.6f})")


def test_max_value_gradient():
    """max_value should route gradient to the max element only."""
    a, b, c = Value(1.0), Value(3.0), Value(2.0)
    m = max_value([a, b, c])
    assert m.data == 3.0
    m.backward()
    assert b.grad == 1.0, f"Expected b.grad=1.0, got {b.grad}"
    assert a.grad == 0.0, f"Expected a.grad=0.0, got {a.grad}"
    assert c.grad == 0.0, f"Expected c.grad=0.0, got {c.grad}"
    print("  Edge: PASS — max_value gradient routing")


def test_backward_zeros_previous_grads():
    """backward() should zero all gradients before computing new ones."""
    x = Value(2.0)
    y = x ** 2
    y.backward()
    first_grad = x.grad
    # call backward again on a new graph
    x.grad = 99.0  # manually set a bad grad
    z = x ** 3
    z.backward()
    assert x.grad != 99.0, "backward() should have zeroed the stale grad"
    assert abs(x.grad - 12.0) < 1e-10, f"Expected 12.0, got {x.grad}"  # d/dx(x^3) = 3x^2 = 12
    print("  Edge: PASS — backward() zeros stale gradients")


def run_all_tests():
    """Run all bug and edge case tests."""
    tests = [
        ("Bug A: pow(0, 0) backward", test_bug_a_pow_zero_base_zero_exp),
        ("Bug B: negative base fractional exp", test_bug_b_negative_base_fractional_exp),
        ("Bug C: Xavier fan-out", test_bug_c_xavier_fanout),
        ("Bug D: eq/hash contract", test_bug_d_eq_hash_contract),
        ("Edge: relu at zero", test_edge_relu_at_zero_backward),
        ("Edge: div by zero", test_edge_div_by_zero_clear_error),
        ("Edge: log non-positive", test_edge_log_of_nonpositive),
        ("Edge: gradient accumulation", test_gradient_accumulation_reuse),
        ("Edge: numerical grad check", test_numerical_grad_check_complex),
        ("Edge: negative int exponent", test_pow_negative_integer_exponent),
        ("Edge: fractional exponent", test_pow_fractional_exponent_positive_base),
        ("Edge: MLP input validation", test_mlp_input_length_validation),
        ("Edge: softmax sums to 1", test_softmax_sums_to_one),
        ("Edge: cross-entropy gradient", test_cross_entropy_gradient),
        ("Edge: BCE gradient", test_bce_with_logits_gradient),
        ("Edge: Adam converges", test_adam_converges),
        ("Edge: SGD+momentum converges", test_sgd_momentum_converges),
        ("Edge: max_value gradient", test_max_value_gradient),
        ("Edge: backward zeros grads", test_backward_zeros_previous_grads),
    ]

    passed = 0
    failed = 0
    for name, fn in tests:
        try:
            print(f"Running: {name}")
            fn()
            passed += 1
        except Exception as e:
            print(f"  FAIL: {name}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print(f"\n{'='*60}")
    print(f"Results: {passed} passed, {failed} failed")
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    raise SystemExit(0 if success else 1)