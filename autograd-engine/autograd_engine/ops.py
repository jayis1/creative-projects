"""Higher-level operations over sequences of ``Value`` objects.

These functions build new ``Value`` nodes by composing the primitive ops
defined in :mod:`autograd_engine.engine`.  They are the building blocks for
loss functions and layer-level computations.
"""

from __future__ import annotations

import math
from typing import Iterable, List, Sequence

from .engine import Value


def sum_values(values: Iterable[Value]) -> Value:
    """Sum an iterable of ``Value`` objects into a single ``Value``."""
    values = list(values)
    if not values:
        return Value(0.0)
    out = values[0]
    for v in values[1:]:
        out = out + v
    return out


def mean(values: Iterable[Value]) -> Value:
    """Element-wise mean of a sequence of ``Value`` objects."""
    values = list(values)
    n = len(values)
    if n == 0:
        raise ValueError("mean of empty sequence")
    return sum_values(values) / n


def max_value(values: Iterable[Value]) -> Value:
    """Maximum of a sequence of ``Value`` objects (smooth-ish: the gradient
    flows only to the argmax, which is the standard subgradient)."""
    values = list(values)
    if not values:
        raise ValueError("max of empty sequence")
    if len(values) == 1:
        return values[0]
    best = values[0]
    best_idx = 0
    for i, v in enumerate(values):
        if v.data > best.data:
            best = v
            best_idx = i
    out = Value(best.data, tuple(values), "max")

    def _backward() -> None:
        for i, v in enumerate(values):
            if i == best_idx:
                v.grad += out.grad

    out._backward = _backward
    return out


def softmax(logits: Sequence[Value]) -> List[Value]:
    """Numerically-stable softmax over a list of logit ``Value`` objects."""
    if not logits:
        raise ValueError("softmax of empty sequence")
    # subtract max for numerical stability (doesn't affect the math)
    max_logit = max(v.data for v in logits)
    exps = [(v - max_logit).exp() for v in logits]
    total = sum_values(exps)
    return [e / total for e in exps]


def log_softmax(logits: Sequence[Value]) -> List[Value]:
    """Log-softmax — numerically stable version using the log-sum-exp trick."""
    if not logits:
        raise ValueError("log_softmax of empty sequence")
    max_logit = max(v.data for v in logits)
    shifted = [v - max_logit for v in logits]
    exps = [v.exp() for v in shifted]
    total = sum_values(exps)
    log_sum_exp = total.log()  # log(sum(exp(x_i - max)))
    return [v - log_sum_exp for v in shifted]


def cross_entropy(logits: Sequence[Value], target: int) -> Value:
    """Cross-entropy loss for a single example.

    Parameters
    ----------
    logits : list[Value]
        Raw (pre-softmax) logits from the model.
    target : int
        Index of the correct class.
    """
    if target < 0 or target >= len(logits):
        raise ValueError(
            f"target index {target} out of range for {len(logits)} logits"
        )
    log_sm = log_softmax(logits)
    # loss = -log_sm[target]
    return -log_sm[target]


def dot(a: Iterable[Value], b: Iterable[Value]) -> Value:
    """Dot product of two equal-length sequences of ``Value``."""
    a, b = list(a), list(b)
    if len(a) != len(b):
        raise ValueError(f"dot: length mismatch ({len(a)} vs {len(b)})")
    return sum_values(x * y for x, y in zip(a, b))


def matvec(W: Sequence[Sequence[Value]], x: Sequence[Value]) -> List[Value]:
    """Matrix-vector product W @ x where W is a list of rows (each a list of
    Values) and x is a list of Values.  Returns a list of Values."""
    return [dot(row, x) for row in W]