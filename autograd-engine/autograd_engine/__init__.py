"""autograd-engine: a tiny reverse-mode automatic differentiation engine.

This package implements a computational graph of scalar ``Value`` nodes that
support backpropagation, plus a small multi-layer perceptron (``MLP``) built
on top of it, a set of optimizers (SGD, Adam), loss functions (MSE, BCE,
cross-entropy, hinge), and training utilities.

Example
-------
>>> from autograd_engine import Value, MLP
>>> from autograd_engine.train import train
>>> xs = [[0, 0], [0, 1], [1, 0], [1, 1]]
>>> ys = [0, 1, 1, 0]
>>> model = MLP(2, [4, 4, 1], activation="tanh")
>>> history = train(model, xs, ys, epochs=500, lr=0.1)
>>> assert history[-1] < 0.05
"""

from .engine import Value
from .nn import Neuron, Layer, MLP, Module
from .ops import (
    sum_values,
    mean,
    max_value,
    softmax,
    log_softmax,
    cross_entropy,
    dot,
    matvec,
)
from .train import (
    SGD,
    Adam,
    Optimizer,
    mean_squared_error,
    binary_cross_entropy_with_logits,
    cross_entropy_loss,
    hinge_loss,
    train,
    accuracy,
    numerical_grad_check,
)

__all__ = [
    # core
    "Value",
    # nn
    "Neuron",
    "Layer",
    "MLP",
    "Module",
    # ops
    "sum_values",
    "mean",
    "max_value",
    "softmax",
    "log_softmax",
    "cross_entropy",
    "dot",
    "matvec",
    # train
    "SGD",
    "Adam",
    "Optimizer",
    "mean_squared_error",
    "binary_cross_entropy_with_logits",
    "cross_entropy_loss",
    "hinge_loss",
    "train",
    "accuracy",
    "numerical_grad_check",
]
__version__ = "1.0.0"