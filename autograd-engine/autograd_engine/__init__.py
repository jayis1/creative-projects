"""autograd-engine: a tiny reverse-mode automatic differentiation engine.

This package implements a computational graph of scalar ``Value`` nodes that
support backpropagation, plus a small multi-layer perceptron (``MLP``) built
on top of it, a set of optimizers (SGD, Adam), loss functions (MSE, BCE,
cross-entropy, hinge), training utilities, learning-rate schedulers,
additional activation functions, model serialization, graph visualization,
evaluation metrics, and configuration management.

Example
-------
>>> from autograd_engine import Value, MLP
>>> from autograd_engine.train import train
>>> xs = [[0, 0], [0, 1], [1, 0], [1, 1]]
>>> ys = [0, 1, 1, 0]
>>> model = MLP(2, [4, 4, 1], activation="tanh")
>>> history = train(model, xs, ys, epochs=500, lr=0.1, classification=True)
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
    EarlyStopping,
)
from .activations import (
    leaky_relu,
    elu,
    gelu,
    swish,
    softplus,
    mish,
    selu,
    hard_tanh,
    hard_sigmoid,
    get_activation,
    ACTIVATION_REGISTRY,
)
from .schedulers import (
    LRScheduler,
    StepLR,
    ExponentialLR,
    CosineAnnealingLR,
    LinearLR,
    WarmupLR,
    ReduceOnPlateauLR,
    get_scheduler,
)
from .serialization import save_model, load_model
from .viz import to_dot, draw_dot, ascii_loss_chart
from .metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report,
    mean_absolute_error,
    root_mean_squared_error,
    r2_score,
)
from .config import Config, ModelConfig, OptimizerConfig, TrainingConfig, default_config

__all__ = [
    # core
    "Value",
    # nn
    "Neuron", "Layer", "MLP", "Module",
    # ops
    "sum_values", "mean", "max_value", "softmax", "log_softmax",
    "cross_entropy", "dot", "matvec",
    # train
    "SGD", "Adam", "Optimizer", "mean_squared_error",
    "binary_cross_entropy_with_logits", "cross_entropy_loss", "hinge_loss",
    "train", "accuracy", "numerical_grad_check", "EarlyStopping",
    # activations
    "leaky_relu", "elu", "gelu", "swish", "softplus", "mish", "selu",
    "hard_tanh", "hard_sigmoid", "get_activation", "ACTIVATION_REGISTRY",
    # schedulers
    "LRScheduler", "StepLR", "ExponentialLR", "CosineAnnealingLR",
    "LinearLR", "WarmupLR", "ReduceOnPlateauLR", "get_scheduler",
    # serialization
    "save_model", "load_model",
    # viz
    "to_dot", "draw_dot", "ascii_loss_chart",
    # metrics
    "accuracy_score", "precision_score", "recall_score", "f1_score",
    "confusion_matrix", "classification_report",
    "mean_absolute_error", "root_mean_squared_error", "r2_score",
    # config
    "Config", "ModelConfig", "OptimizerConfig", "TrainingConfig", "default_config",
]
__version__ = "2.0.0"