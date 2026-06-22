"""autograd-engine: a tiny reverse-mode automatic differentiation engine.

This package implements a computational graph of scalar ``Value`` nodes that
support backpropagation, plus a small multi-layer perceptron (``MLP``) built
on top of it.  The design is inspired by Andrej Karpathy's ``micrograd``.

Example
-------
>>> from autograd_engine import Value, MLP
>>> xs = [[2.0, 3.0, -1.0]]
>>> ys = [1.0]
>>> model = MLP(3, [4, 4, 1])
>>> for k in range(50):
...     ypred = [model(x) for x in xs]
...     loss = sum((yp - yt) ** 2 for yp, yt in zip(ypred, ys)) / len(xs)
...     model.zero_grad()
...     loss.backward()
...     for p in model.parameters():
...         p.data -= 0.05 * p.grad
>>> assert loss.data < 0.1
"""

from .engine import Value
from .nn import Neuron, Layer, MLP

__all__ = ["Value", "Neuron", "Layer", "MLP"]
__version__ = "0.1.0"