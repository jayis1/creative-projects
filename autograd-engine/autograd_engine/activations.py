"""Additional activation functions for ``Value`` nodes.

These are implemented as free functions returning new ``Value`` nodes so they
can be used in custom models or composed with the built-in methods on
``Value`` (``tanh``, ``relu``, ``sigmoid``, ``exp``, ``log``).

Activations provided
--------------------
``leaky_relu``  — Leaky ReLU with configurable slope
``elu``         — Exponential Linear Unit
``gelu``        — Gaussian Error Linear Unit (tanh approximation)
``swish``       — Swish / SiLU (x * sigmoid(x))
``softplus``    — log(1 + exp(x))  (numerically stable)
``mish``        — x * tanh(softplus(x))
``selu``        — Scaled Exponential Linear Unit
``hard_tanh``   — clamped to [-1, 1]
``hard_sigmoid`` — piecewise linear approximation of sigmoid
"""

from __future__ import annotations

import math
from typing import Optional

from .engine import Value


def leaky_relu(v: Value, slope: float = 0.01) -> Value:
    """Leaky ReLU: ``max(x, slope*x)`` with gradient flowing through both branches."""
    if v.data >= 0:
        out = Value(v.data, (v,), "leaky_relu")
        def _backward() -> None:
            v.grad += 1.0 * out.grad
        out._backward = _backward
    else:
        out = Value(slope * v.data, (v,), "leaky_relu")
        def _backward() -> None:
            v.grad += slope * out.grad
        out._backward = _backward
    return out


def elu(v: Value, alpha: float = 1.0) -> Value:
    """Exponential Linear Unit: ``x`` if ``x > 0`` else ``alpha * (exp(x) - 1)``."""
    if v.data >= 0:
        out = Value(v.data, (v,), "elu")
        def _backward() -> None:
            v.grad += 1.0 * out.grad
        out._backward = _backward
    else:
        e = math.exp(v.data)
        out = Value(alpha * (e - 1.0), (v,), "elu")
        def _backward() -> None:
            v.grad += (alpha * e) * out.grad
        out._backward = _backward
    return out


def gelu(v: Value) -> Value:
    """GELU (tanh approximation): ``0.5 * x * (1 + tanh(sqrt(2/pi) * (x + 0.044715 * x^3)))``."""
    c = math.sqrt(2.0 / math.pi)
    inner = c * (v.data + 0.044715 * v.data ** 3)
    t = math.tanh(inner)
    fwd = 0.5 * v.data * (1.0 + t)
    out = Value(fwd, (v,), "gelu")
    # derivative of gelu approximation
    dt_di = 1.0 - t * t
    di_dx = c * (1.0 + 3.0 * 0.044715 * v.data ** 2)
    grad = 0.5 * (1.0 + t) + 0.5 * v.data * dt_di * di_dx
    def _backward() -> None:
        v.grad += grad * out.grad
    out._backward = _backward
    return out


def swish(v: Value, beta: float = 1.0) -> Value:
    """Swish / SiLU: ``x * sigmoid(beta * x)``."""
    bx = beta * v.data
    if bx >= 0:
        s = 1.0 / (1.0 + math.exp(-bx))
    else:
        e = math.exp(bx)
        s = e / (1.0 + e)
    fwd = v.data * s
    out = Value(fwd, (v,), "swish")
    grad = s + v.data * beta * s * (1.0 - s)
    def _backward() -> None:
        v.grad += grad * out.grad
    out._backward = _backward
    return out


def softplus(v: Value) -> Value:
    """Numerically stable softplus: ``log(1 + exp(x))``."""
    x = v.data
    if x >= 0:
        fwd = x + math.log1p(math.exp(-x))
    else:
        fwd = math.log1p(math.exp(x))
    out = Value(fwd, (v,), "softplus")
    # gradient = sigmoid(x)
    if x >= 0:
        s = 1.0 / (1.0 + math.exp(-x))
    else:
        e = math.exp(x)
        s = e / (1.0 + e)
    def _backward() -> None:
        v.grad += s * out.grad
    out._backward = _backward
    return out


def mish(v: Value) -> Value:
    """Mish: ``x * tanh(softplus(x))``."""
    x = v.data
    if x >= 0:
        sp = x + math.log1p(math.exp(-x))
    else:
        sp = math.log1p(math.exp(x))
    t = math.tanh(sp)
    fwd = x * t
    out = Value(fwd, (v,), "mish")
    # gradient: tanh(sp) + x * (1 - tanh^2(sp)) * sigmoid(x)
    if x >= 0:
        sig = 1.0 / (1.0 + math.exp(-x))
    else:
        e = math.exp(x)
        sig = e / (1.0 + e)
    grad = t + x * (1.0 - t * t) * sig
    def _backward() -> None:
        v.grad += grad * out.grad
    out._backward = _backward
    return out


def selu(v: Value) -> Value:
    """Scaled Exponential Linear Unit (Klambauer et al., 2017)."""
    alpha = 1.6732632423543772
    scale = 1.0507009873554805
    if v.data >= 0:
        out = Value(scale * v.data, (v,), "selu")
        def _backward() -> None:
            v.grad += scale * out.grad
        out._backward = _backward
    else:
        e = math.exp(v.data)
        out = Value(scale * alpha * (e - 1.0), (v,), "selu")
        def _backward() -> None:
            v.grad += scale * alpha * e * out.grad
        out._backward = _backward
    return out


def hard_tanh(v: Value) -> Value:
    """Hard tanh: clamped to [-1, 1]."""
    if v.data > 1:
        out = Value(1.0, (v,), "hard_tanh")
    elif v.data < -1:
        out = Value(-1.0, (v,), "hard_tanh")
    else:
        out = Value(v.data, (v,), "hard_tanh")
    def _backward() -> None:
        if -1.0 <= v.data <= 1.0:
            v.grad += 1.0 * out.grad
    out._backward = _backward
    return out


def hard_sigmoid(v: Value) -> Value:
    """Hard sigmoid: piecewise linear approximation."""
    if v.data >= 2.5:
        out = Value(1.0, (v,), "hard_sigmoid")
    elif v.data <= -2.5:
        out = Value(0.0, (v,), "hard_sigmoid")
    else:
        out = Value(0.2 * v.data + 0.5, (v,), "hard_sigmoid")
    def _backward() -> None:
        if -2.5 < v.data < 2.5:
            v.grad += 0.2 * out.grad
    out._backward = _backward
    return out


# Registry for config-based activation selection
ACTIVATION_REGISTRY = {
    "tanh": lambda v: v.tanh(),
    "relu": lambda v: v.relu(),
    "sigmoid": lambda v: v.sigmoid(),
    "linear": lambda v: v,
    "none": lambda v: v,
    "leaky_relu": leaky_relu,
    "elu": elu,
    "gelu": gelu,
    "swish": swish,
    "softplus": softplus,
    "mish": mish,
    "selu": selu,
    "hard_tanh": hard_tanh,
    "hard_sigmoid": hard_sigmoid,
}


def get_activation(name: str):
    """Look up an activation function by name.

    Returns a callable ``(Value) -> Value``.
    """
    if name not in ACTIVATION_REGISTRY:
        raise ValueError(
            f"Unknown activation '{name}'. Available: {sorted(ACTIVATION_REGISTRY)}"
        )
    return ACTIVATION_REGISTRY[name]