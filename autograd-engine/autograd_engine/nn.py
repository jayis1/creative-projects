"""Minimal neural-network library built on top of :class:`autograd_engine.Value`.

Implements ``Neuron``, ``Layer`` and ``MLP`` — enough to train a small
multi-layer perceptron with gradient descent on the autograd engine.
"""

from __future__ import annotations

import random
from typing import Iterable, List

from .engine import Value


class Module:
    """Base class providing parameter collection and grad zeroing."""

    def parameters(self) -> List[Value]:
        return []

    def zero_grad(self) -> None:
        for p in self.parameters():
            p.grad = 0.0

    def __call__(self, *args):
        return self.forward(*args)


class Neuron(Module):
    """A single linear+activation unit."""

    def __init__(self, nin: int, nonlin: bool = True, activation: str = "tanh") -> None:
        self.w: List[Value] = [
            Value(random.uniform(-1, 1), label=f"w{i}") for i in range(nin)
        ]
        self.b = Value(0.0, label="b")
        self.nonlin = nonlin
        self.activation = activation

    def forward(self, x: Iterable[Value | float]) -> Value:
        out = sum((wi * xi for wi, xi in zip(self.w, x)), self.b)
        if not self.nonlin:
            return out
        if self.activation == "tanh":
            return out.tanh()
        if self.activation == "relu":
            return out.relu()
        raise ValueError(f"unknown activation '{self.activation}'")

    def parameters(self) -> List[Value]:
        return self.w + [self.b]

    def __repr__(self) -> str:
        act = self.activation if self.nonlin else "linear"
        return f"Neuron(nin={len(self.w)}, act={act})"


class Layer(Module):
    """A fully-connected layer of ``Neuron`` objects."""

    def __init__(self, nin: int, nout: int, **kwargs) -> None:
        self.neurons = [Neuron(nin, **kwargs) for _ in range(nout)]

    def forward(self, x: Iterable[Value | float]) -> List[Value]:
        return [n(x) for n in self.neurons]

    def parameters(self) -> List[Value]:
        return [p for n in self.neurons for p in n.parameters()]

    def __repr__(self) -> str:
        return f"Layer({', '.join(str(n) for n in self.neurons)})"


class MLP(Module):
    """A multi-layer perceptron.

    Parameters
    ----------
    nin : int
        Number of inputs.
    nouts : list[int]
        Width of each hidden layer and the output layer.
    """

    def __init__(self, nin: int, nouts: List[int], activation: str = "tanh") -> None:
        sz = [nin] + nouts
        self.layers: List[Layer] = []
        for i in range(len(nouts)):
            last = i == len(nouts) - 1
            self.layers.append(
                Layer(sz[i], sz[i + 1], nonlin=not last, activation=activation)
            )

    def forward(self, x: Iterable[Value | float]) -> List[Value]:
        for layer in self.layers:
            x = layer(x)
        return x

    def parameters(self) -> List[Value]:
        return [p for layer in self.layers for p in layer.parameters()]

    def __repr__(self) -> str:
        return f"MLP([{', '.join(str(layer) for layer in self.layers)}])"