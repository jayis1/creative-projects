"""Tests for the ops module."""

import math
import pytest
from autograd_engine import Value
from autograd_engine.ops import (
    sum_values, mean, max_value, softmax, log_softmax,
    cross_entropy, dot, matvec,
)


class TestSumValues:
    def test_basic(self):
        vals = [Value(1.0), Value(2.0), Value(3.0)]
        s = sum_values(vals)
        assert s.data == 6.0

    def test_empty(self):
        s = sum_values([])
        assert s.data == 0.0

    def test_single(self):
        s = sum_values([Value(5.0)])
        assert s.data == 5.0

    def test_gradient(self):
        vals = [Value(1.0), Value(2.0)]
        s = sum_values(vals)
        s.backward()
        assert vals[0].grad == 1.0
        assert vals[1].grad == 1.0


class TestMean:
    def test_basic(self):
        vals = [Value(2.0), Value(4.0)]
        m = mean(vals)
        assert m.data == 3.0

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="empty sequence"):
            mean([])


class TestMaxValue:
    def test_basic(self):
        vals = [Value(1.0), Value(3.0), Value(2.0)]
        m = max_value(vals)
        assert m.data == 3.0

    def test_gradient_to_argmax(self):
        vals = [Value(1.0), Value(3.0), Value(2.0)]
        m = max_value(vals)
        m.backward()
        assert vals[0].grad == 0.0
        assert vals[1].grad == 1.0
        assert vals[2].grad == 0.0

    def test_single(self):
        m = max_value([Value(5.0)])
        assert m.data == 5.0

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            max_value([])


class TestSoftmax:
    def test_basic(self):
        logits = [Value(1.0), Value(2.0), Value(3.0)]
        probs = softmax(logits)
        assert len(probs) == 3
        total = sum(p.data for p in probs)
        assert abs(total - 1.0) < 1e-9

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            softmax([])

    def test_numerical_stability(self):
        # Very large logits shouldn't overflow
        logits = [Value(1000.0), Value(1001.0)]
        probs = softmax(logits)
        assert abs(probs[1].data - math.exp(1) / (1 + math.exp(1))) < 1e-6


class TestLogSoftmax:
    def test_basic(self):
        logits = [Value(1.0), Value(2.0)]
        ls = log_softmax(logits)
        assert len(ls) == 2
        # log_softmax should be <= 0
        for v in ls:
            assert v.data <= 0.0

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            log_softmax([])


class TestCrossEntropy:
    def test_basic(self):
        logits = [Value(2.0), Value(1.0), Value(0.1)]
        loss = cross_entropy(logits, target=0)
        assert loss.data > 0
        loss.backward()
        # Gradient should flow
        assert logits[0].grad != 0

    def test_invalid_target(self):
        logits = [Value(1.0), Value(2.0)]
        with pytest.raises(ValueError, match="out of range"):
            cross_entropy(logits, target=5)
        with pytest.raises(ValueError, match="out of range"):
            cross_entropy(logits, target=-1)


class TestDot:
    def test_basic(self):
        a = [Value(1.0), Value(2.0), Value(3.0)]
        b = [Value(4.0), Value(5.0), Value(6.0)]
        d = dot(a, b)
        assert d.data == 32.0  # 4+10+18

    def test_length_mismatch(self):
        with pytest.raises(ValueError, match="length mismatch"):
            dot([Value(1.0)], [Value(1.0), Value(2.0)])


class TestMatvec:
    def test_basic(self):
        W = [[Value(1.0), Value(2.0)], [Value(3.0), Value(4.0)]]
        x = [Value(5.0), Value(6.0)]
        out = matvec(W, x)
        assert len(out) == 2
        assert out[0].data == 17.0  # 1*5 + 2*6
        assert out[1].data == 39.0  # 3*5 + 4*6