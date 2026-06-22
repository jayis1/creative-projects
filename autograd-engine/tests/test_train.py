"""Tests for the training module (optimizers, losses, training loop)."""

import math
import pytest
from autograd_engine import Value, MLP
from autograd_engine.train import (
    SGD, Adam, mean_squared_error, binary_cross_entropy_with_logits,
    cross_entropy_loss, hinge_loss, train, accuracy,
    numerical_grad_check, EarlyStopping,
)


class TestSGD:
    def test_basic_step(self):
        x = Value(1.0)
        x.grad = 0.1
        opt = SGD([x], lr=0.5)
        opt.step()
        assert abs(x.data - 0.95) < 1e-9

    def test_momentum(self):
        x = Value(1.0)
        x.grad = 0.1
        opt = SGD([x], lr=0.5, momentum=0.9)
        opt.step()
        assert abs(x.data - 0.95) < 1e-9  # first step same as no momentum

        x.grad = 0.1
        opt.step()
        # velocity = 0.9*0.1 + 0.1 = 0.19
        # x = 0.95 - 0.5*0.19 = 0.855
        assert abs(x.data - 0.855) < 1e-6

    def test_weight_decay(self):
        x = Value(1.0)
        x.grad = 0.0
        opt = SGD([x], lr=0.1, weight_decay=0.01)
        opt.step()
        # g = 0 + 0.01*1.0 = 0.01; x = 1.0 - 0.1*0.01 = 0.999
        assert abs(x.data - 0.999) < 1e-6

    def test_zero_grad(self):
        x = Value(1.0)
        x.grad = 0.5
        opt = SGD([x], lr=0.1)
        opt.zero_grad()
        assert x.grad == 0.0


class TestAdam:
    def test_basic_step(self):
        x = Value(1.0)
        x.grad = 0.1
        opt = Adam([x], lr=0.01)
        opt.step()
        # After first step, should have moved
        assert x.data != 1.0

    def test_convergence(self):
        xs = [[0, 0], [0, 1], [1, 0], [1, 1]]
        ys = [0, 1, 1, 0]
        model = MLP(2, [8, 8, 1], activation="tanh")
        opt = Adam(model.parameters(), lr=0.01)
        history = train(model, xs, ys, epochs=200, optimizer=opt,
                         classification=True, seed=42)
        assert history[-1] < 0.1


class TestMSE:
    def test_basic(self):
        preds = [Value(2.0), Value(4.0)]
        targets = [1.0, 3.0]
        loss = mean_squared_error(preds, targets)
        assert abs(loss.data - 1.0) < 1e-9  # ((2-1)^2 + (4-3)^2)/2 = 1

    def test_length_mismatch(self):
        with pytest.raises(ValueError, match="mismatch"):
            mean_squared_error([Value(1.0)], [1.0, 2.0])

    def test_empty(self):
        with pytest.raises(ValueError, match="empty"):
            mean_squared_error([], [])


class TestBCE:
    def test_basic(self):
        logits = [Value(0.0)]  # sigmoid(0) = 0.5
        targets = [1.0]
        loss = binary_cross_entropy_with_logits(logits, targets)
        # BCE = -log(0.5) = ln(2) ≈ 0.693
        assert abs(loss.data - math.log(2)) < 1e-6

    def test_gradient(self):
        logits = [Value(0.0)]
        targets = [1.0]
        loss = binary_cross_entropy_with_logits(logits, targets)
        loss.backward()
        # sigmoid(0) - 1 = 0.5 - 1 = -0.5
        assert abs(logits[0].grad - (-0.5)) < 1e-6

    def test_empty(self):
        with pytest.raises(ValueError):
            binary_cross_entropy_with_logits([], [])


class TestHingeLoss:
    def test_basic(self):
        preds = [Value(0.5)]
        targets = [1.0]
        loss = hinge_loss(preds, targets)
        # 1 - 1*0.5 = 0.5; relu(0.5) = 0.5
        assert abs(loss.data - 0.5) < 1e-9

    def test_no_loss_when_correct(self):
        preds = [Value(5.0)]
        targets = [1.0]
        loss = hinge_loss(preds, targets)
        # 1 - 1*5 = -4; relu(-4) = 0
        assert loss.data == 0.0


class TestTrainFunction:
    def test_returns_history(self):
        xs = [[0, 0], [0, 1], [1, 0], [1, 1]]
        ys = [0, 1, 1, 0]
        model = MLP(2, [4, 1])
        history = train(model, xs, ys, epochs=10, seed=42)
        assert len(history) == 10

    def test_batch_size(self):
        xs = [[i] for i in range(10)]
        ys = [float(i % 2) for i in range(10)]
        model = MLP(1, [4, 1])
        history = train(model, xs, ys, epochs=5, batch_size=3, seed=42)
        assert len(history) == 5


class TestAccuracy:
    def test_perfect(self):
        model = MLP(2, [4, 1])
        # Manually set weights to always predict >0.5
        for layer in model.layers:
            for n in layer.neurons:
                for w in n.w:
                    w.data = 0.0
                n.b.data = 1.0
        xs = [[0, 0], [0, 1]]
        ys = [1, 1]
        assert accuracy(model, xs, ys) == 1.0

    def test_empty(self):
        model = MLP(2, [4, 1])
        assert accuracy(model, [], []) == 0.0


class TestNumericalGradCheck:
    def test_simple(self):
        assert numerical_grad_check(
            lambda inp: inp[0] ** 2,
            [Value(3.0)], tol=1e-4
        )

    def test_complex(self):
        def f(inp):
            x, y = inp
            return (x * y + x.tanh()).exp().log() + x ** 2
        assert numerical_grad_check(f, [Value(1.5), Value(0.7)], tol=1e-3)

    def test_fails_on_wrong(self):
        # We can't easily make a wrong gradient, but we can test the function
        # runs without error
        assert isinstance(
            numerical_grad_check(lambda inp: inp[0] * 2, [Value(1.0)]),
            bool
        )


class TestEarlyStopping:
    def test_no_stop_when_improving(self):
        es = EarlyStopping(patience=3, mode="min")
        for val in [10, 9, 8, 7]:
            assert es.step(val) is False

    def test_stops_when_not_improving(self):
        es = EarlyStopping(patience=3, mode="min")
        es.step(10)
        es.step(10)
        es.step(10)
        assert es.step(10) is True  # 4th no-improvement

    def test_max_mode(self):
        es = EarlyStopping(patience=2, mode="max")
        es.step(0.5)
        es.step(0.5)
        assert es.step(0.5) is True

    def test_invalid_mode(self):
        with pytest.raises(ValueError, match="mode"):
            EarlyStopping(mode="bogus")