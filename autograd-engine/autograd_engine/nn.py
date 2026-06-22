"""Minimal neural-network library built on top of :class:`autograd_engine.Value`.

Implements ``Neuron``, ``Layer`` and ``MLP`` — enough to train small
multi-layer perceptrons with gradient descent on the autograd engine.

Enhanced features:
    - Xavier/Glorot and He weight initialization
    - Configurable activation per layer (tanh / relu / sigmoid / linear)
    - Dropout (training-time only)
    - ``train()`` / ``eval()`` mode toggling
    - L2 weight decay via the optimizer
"""

from __future__ import annotations

import math
import random
from typing import Iterable, List, Optional, Sequence, Tuple

from .engine import Value
from .ops import dot
from .activations import ACTIVATION_REGISTRY, get_activation


# --------------------------------------------------------------------------- #
# activation registry
# --------------------------------------------------------------------------- #
def _apply_activation(v: Value, name: str) -> Value:
    """Apply a named activation function to a ``Value``.

    Uses the centralized activation registry so all activations (built-in
    and extended) are available to the neural-network modules.
    """
    return get_activation(name)(v)


_ACTIVATIONS = set(ACTIVATION_REGISTRY.keys())


# --------------------------------------------------------------------------- #
# weight init helpers
# --------------------------------------------------------------------------- #
def _xavier(n_in: int, n_out: int) -> float:
    """Xavier/Glorot uniform init."""
    limit = math.sqrt(6.0 / (n_in + n_out))
    return random.uniform(-limit, limit)


def _he(n_in: int) -> float:
    """He normal-ish init (uniform variant) for ReLU-based nets."""
    limit = math.sqrt(2.0 / n_in)
    return random.uniform(-limit, limit)


# --------------------------------------------------------------------------- #
# module base
# --------------------------------------------------------------------------- #
class Module:
    """Base class providing parameter collection, mode toggling, and grad zeroing."""

    def __init__(self) -> None:
        self.training: bool = True

    def parameters(self) -> List[Value]:
        return []

    def zero_grad(self) -> None:
        for p in self.parameters():
            p.grad = 0.0

    def train(self) -> None:
        self.training = True
        for m in self._children_modules():
            m.train()

    def eval(self) -> None:
        self.training = False
        for m in self._children_modules():
            m.eval()

    def _children_modules(self) -> List["Module"]:
        return []

    def __call__(self, *args):
        return self.forward(*args)


# --------------------------------------------------------------------------- #
# Neuron
# --------------------------------------------------------------------------- #
class Neuron(Module):
    """A single linear+activation unit.

    Parameters
    ----------
    nin : int
        Number of inputs.
    nonlin : bool
        Whether to apply a non-linear activation.
    activation : str
        One of ``tanh``, ``relu``, ``sigmoid``, ``linear``.
    init : str
        Weight initialization: ``xavier`` (default) or ``he`` (for ReLU).
    """

    def __init__(
        self,
        nin: int,
        nonlin: bool = True,
        activation: str = "tanh",
        init: str = "xavier",
        nout: Optional[int] = None,
    ) -> None:
        if nin <= 0:
            raise ValueError(f"nin must be positive, got {nin}")
        if init == "he":
            self.w: List[Value] = [Value(_he(nin)) for _ in range(nin)]
        else:
            # Xavier/Glorot uniform uses (fan_in + fan_out) for the scale.
            # When nout is not provided (e.g. standalone Neuron), default
            # fan_out to nin so the init is still reasonable.
            fan_out = nout if nout is not None else nin
            self.w = [Value(_xavier(nin, fan_out)) for _ in range(nin)]
        self.b = Value(0.0)
        self.nonlin = nonlin
        self.activation = activation if nonlin else "linear"
        super().__init__()

    def forward(self, x: Iterable[Value | float]) -> Value:
        x = list(x)
        if len(x) != len(self.w):
            raise ValueError(
                f"input length {len(x)} != neuron input size {len(self.w)}"
            )
        out = dot(self.w, x) + self.b
        return _apply_activation(out, self.activation)

    def parameters(self) -> List[Value]:
        return self.w + [self.b]

    def __repr__(self) -> str:
        return f"Neuron(nin={len(self.w)}, act={self.activation})"


# --------------------------------------------------------------------------- #
# Layer
# --------------------------------------------------------------------------- #
class Layer(Module):
    """A fully-connected layer of ``Neuron`` objects with optional dropout."""

    def __init__(
        self,
        nin: int,
        nout: int,
        nonlin: bool = True,
        activation: str = "tanh",
        init: str = "xavier",
        dropout: float = 0.0,
    ) -> None:
        self.neurons: List[Neuron] = [
            Neuron(nin, nonlin=nonlin, activation=activation, init=init, nout=nout)
            for _ in range(nout)
        ]
        self.dropout = dropout
        super().__init__()

    def forward(self, x: Iterable[Value | float]) -> List[Value]:
        x = list(x)
        outs = [n(x) for n in self.neurons]
        if self.training and self.dropout > 0.0:
            outs = [self._apply_dropout(o) for o in outs]
        return outs

    def _apply_dropout(self, v: Value) -> Value:
        """Inverted dropout: scale by 1/(1-p) during training."""
        keep = 1.0 - self.dropout
        if random.random() < self.dropout:
            return Value(0.0)
        return v * (1.0 / keep)

    def parameters(self) -> List[Value]:
        return [p for n in self.neurons for p in n.parameters()]

    def _children_modules(self) -> List[Module]:
        return list(self.neurons)

    def __repr__(self) -> str:
        return f"Layer({', '.join(str(n) for n in self.neurons)})"


# --------------------------------------------------------------------------- #
# MLP
# --------------------------------------------------------------------------- #
class MLP(Module):
    """A multi-layer perceptron.

    Parameters
    ----------
    nin : int
        Number of inputs.
    nouts : list[int]
        Width of each hidden layer and the output layer.
    activation : str
        Activation for hidden layers (output layer is always linear).
    init : str
        Weight init strategy: ``xavier`` (default) or ``he``.
    dropout : float
        Dropout probability for hidden layers (default 0.0 = no dropout).
    """

    def __init__(
        self,
        nin: int,
        nouts: List[int],
        activation: str = "tanh",
        init: str = "xavier",
        dropout: float = 0.0,
    ) -> None:
        if activation not in _ACTIVATIONS:
            raise ValueError(f"unknown activation '{activation}'")
        sz = [nin] + nouts
        self.layers: List[Layer] = []
        for i in range(len(nouts)):
            last = i == len(nouts) - 1
            self.layers.append(
                Layer(
                    sz[i],
                    sz[i + 1],
                    nonlin=not last,
                    activation=activation if not last else "linear",
                    init=init,
                    dropout=0.0 if last else dropout,
                )
            )
        super().__init__()

    def forward(self, x: Iterable[Value | float]) -> List[Value]:
        x = list(x)
        for layer in self.layers:
            x = layer(x)
        return x

    def parameters(self) -> List[Value]:
        return [p for layer in self.layers for p in layer.parameters()]

    def num_parameters(self) -> int:
        return len(self.parameters())

    def _children_modules(self) -> List[Module]:
        return list(self.layers)

    def __repr__(self) -> str:
        return f"MLP([{', '.join(str(layer) for layer in self.layers)}])"