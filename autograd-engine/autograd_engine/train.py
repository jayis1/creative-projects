"""Training utilities: loss functions, optimizers, and a training loop.

Enhanced features:
    - SGD with optional momentum and L2 weight decay
    - Adam optimizer
    - Mean squared error, binary cross-entropy, and cross-entropy losses
    - Numerical gradient checking utility
    - Mini-batch training loop with loss history and accuracy reporting
"""

from __future__ import annotations

import math
import random
from typing import Callable, List, Optional, Sequence, Tuple

from .engine import Value
from .nn import MLP, Module
from .ops import sum_values, cross_entropy, log_softmax, softmax


# --------------------------------------------------------------------------- #
# loss functions
# --------------------------------------------------------------------------- #
def mean_squared_error(ypred: Sequence[Value], ytrue: Sequence[float]) -> Value:
    """Return the mean squared error as a ``Value`` graph node."""
    if len(ypred) != len(ytrue):
        raise ValueError(
            f"prediction/target length mismatch: {len(ypred)} vs {len(ytrue)}"
        )
    if not ypred:
        raise ValueError("cannot compute MSE on empty sequences")
    return sum_values((yp - yt) ** 2 for yp, yt in zip(ypred, ytrue)) / len(ypred)


def binary_cross_entropy_with_logits(
    logits: Sequence[Value], targets: Sequence[float]
) -> Value:
    """Numerically-stable binary cross-entropy.

    Takes raw logits (pre-sigmoid) and binary targets (0/1), internally
    applying the log-sum-exp trick to avoid log(0).  This is the preferred
    way to compute BCE in this engine.
    """
    if len(logits) != len(targets):
        raise ValueError("logits/targets length mismatch")
    if not logits:
        raise ValueError("BCE on empty sequences")
    total = Value(0.0)
    for logit, t in zip(logits, targets):
        # log(1 + exp(x)) computed stably:
        #   if x >= 0: x + log(1 + exp(-x))
        #   else:      log(1 + exp(x))
        x = logit.data
        if x >= 0:
            softplus = x + math.log1p(math.exp(-x))
        else:
            softplus = math.log1p(math.exp(x))
        # loss = softplus - t * x  (graph form)
        # We build the graph: softplus_val - t * logit
        # softplus needs graph: we approximate by using (1+exp(-x)).log() + max(x,0)
        # Cleaner: BCE = max(x,0) - x*t + log(1 + exp(-|x|))
        # Build graph:
        # term = log(1 + exp(-|x|))  — but this constant has no gradient to logit
        # Actually the gradient of softplus wrt x is sigmoid(x), so:
        # d/dx [softplus - t*x] = sigmoid(x) - t
        # We can build this as a custom Value op:
        loss_val = softplus - t * x
        grad = 1.0 / (1.0 + math.exp(-x)) - t  # sigmoid(x) - t
        node = Value(loss_val, (logit,), "bce")
        # capture grad per-closure
        _g = grad

        def _backward(_logit=logit, _g=_g) -> None:
            _logit.grad += _g * node.grad

        node._backward = _backward
        total = total + node
    return total / len(logits)


def cross_entropy_loss(
    logits: Sequence[Value], target: int
) -> Value:
    """Cross-entropy loss for multi-class classification.

    Parameters
    ----------
    logits : list[Value]
        Raw (pre-softmax) logits.
    target : int
        Index of the correct class.
    """
    return cross_entropy(logits, target)


def hinge_loss(ypred: Sequence[Value], ytrue: Sequence[float]) -> Value:
    """Hinge loss for binary classification (targets in {-1, +1})."""
    if len(ypred) != len(ytrue):
        raise ValueError("prediction/target length mismatch")
    total = Value(0.0)
    for yp, yt in zip(ypred, ytrue):
        margin = (1.0 - yt * yp)
        # relu(margin)
        total = total + margin.relu()
    return total / len(ypred)


# --------------------------------------------------------------------------- #
# optimizers
# --------------------------------------------------------------------------- #
class Optimizer:
    """Base optimizer interface."""

    def __init__(self, params: List[Value], lr: float) -> None:
        self.params = params
        self.lr = lr

    def step(self) -> None:
        raise NotImplementedError

    def zero_grad(self) -> None:
        for p in self.params:
            p.grad = 0.0


class SGD(Optimizer):
    """Stochastic gradient descent with optional momentum and L2 weight decay.

    Parameters
    ----------
    params : list[Value]
        Model parameters to optimize.
    lr : float
        Learning rate.
    momentum : float
        Momentum coefficient (0 = vanilla SGD). Default 0.0.
    weight_decay : float
        L2 regularization strength. Default 0.0.
    """

    def __init__(
        self,
        params: List[Value],
        lr: float = 0.01,
        momentum: float = 0.0,
        weight_decay: float = 0.0,
    ) -> None:
        super().__init__(params, lr)
        self.momentum = momentum
        self.weight_decay = weight_decay
        self._velocities: List[float] = [0.0] * len(params)

    def step(self) -> None:
        for i, p in enumerate(self.params):
            g = p.grad
            if self.weight_decay > 0:
                g = g + self.weight_decay * p.data
            if self.momentum > 0:
                self._velocities[i] = self.momentum * self._velocities[i] + g
                g = self._velocities[i]
            p.data -= self.lr * g


class Adam(Optimizer):
    """Adam optimizer (Kingma & Ba, 2014).

    Parameters
    ----------
    params : list[Value]
        Model parameters.
    lr : float
        Learning rate (default 0.001).
    betas : tuple[float, float]
        Coefficients for first and second moment estimates.
    eps : float
        Numerical stability constant.
    weight_decay : float
        L2 regularization strength.
    """

    def __init__(
        self,
        params: List[Value],
        lr: float = 0.001,
        betas: Tuple[float, float] = (0.9, 0.999),
        eps: float = 1e-8,
        weight_decay: float = 0.0,
    ) -> None:
        super().__init__(params, lr)
        self.beta1, self.beta2 = betas
        self.eps = eps
        self.weight_decay = weight_decay
        self._m: List[float] = [0.0] * len(params)
        self._v: List[float] = [0.0] * len(params)
        self._t: int = 0

    def step(self) -> None:
        self._t += 1
        b1, b2 = self.beta1, self.beta2
        bias1 = 1.0 - b1 ** self._t
        bias2 = 1.0 - b2 ** self._t
        for i, p in enumerate(self.params):
            g = p.grad
            if self.weight_decay > 0:
                g = g + self.weight_decay * p.data
            self._m[i] = b1 * self._m[i] + (1 - b1) * g
            self._v[i] = b2 * self._v[i] + (1 - b2) * g * g
            m_hat = self._m[i] / bias1
            v_hat = self._v[i] / bias2
            p.data -= self.lr * m_hat / (math.sqrt(v_hat) + self.eps)


# --------------------------------------------------------------------------- #
# gradient checking
# --------------------------------------------------------------------------- #
def numerical_grad_check(
    fn: Callable[[List[Value]], Value],
    inputs: List[Value],
    eps: float = 1e-6,
    tol: float = 1e-4,
) -> bool:
    """Verify analytic gradients against central-difference numerical gradients.

    Parameters
    ----------
    fn : callable
        Function taking a list of ``Value`` objects and returning a scalar
        ``Value`` (the loss).
    inputs : list[Value]
        Input leaf nodes to check gradients for.
    eps : float
        Finite-difference step size.
    tol : float
        Absolute tolerance for matching analytic vs numeric gradient.

    Returns
    -------
    bool
        True if all gradients match within ``tol``.
    """
    # compute analytic gradients
    out = fn(inputs)
    out.backward()
    analytic = [v.grad for v in inputs]

    # compute numerical gradients via central difference
    numeric: List[float] = []
    for v in inputs:
        orig = v.data
        v.data = orig + eps
        f_plus = fn(inputs).data
        v.data = orig - eps
        f_minus = fn(inputs).data
        v.data = orig  # restore
        numeric.append((f_plus - f_minus) / (2 * eps))

    # compare
    for i, (a, n) in enumerate(zip(analytic, numeric)):
        if abs(a - n) > tol:
            return False
    return True


# --------------------------------------------------------------------------- #
# training loop
# --------------------------------------------------------------------------- #
def train(
    model: MLP,
    xs: Sequence[Sequence[float]],
    ys: Sequence[float],
    *,
    epochs: int = 100,
    lr: float = 0.05,
    batch_size: Optional[int] = None,
    optimizer: Optional[Optimizer] = None,
    loss_fn: Optional[Callable[[Sequence[Value], Sequence[float]], Value]] = None,
    seed: int = 42,
    verbose: bool = False,
) -> List[float]:
    """Train a regression MLP and return the per-epoch loss history.

    Parameters
    ----------
    model : MLP
        The model to train.
    xs, ys : training inputs and targets.
    epochs : int
    lr : float
        Learning rate (used only if ``optimizer`` is None).
    batch_size : int or None
        If set, use mini-batches of this size (last batch may be smaller).
    optimizer : Optimizer or None
        If None, a plain SGD is created.  Otherwise the provided optimizer is
        used (its ``params`` must match ``model.parameters()``).
    loss_fn : callable or None
        Loss function ``(ypred, ytrue) -> Value``.  Defaults to MSE.
    seed : int
    verbose : bool
    """
    if loss_fn is None:
        loss_fn = mean_squared_error
    random.seed(seed)
    model.train()

    if optimizer is None:
        optimizer = SGD(model.parameters(), lr=lr)
    history: List[float] = []
    n = len(xs)
    for epoch in range(epochs):
        # shuffle indices for mini-batching
        indices = list(range(n))
        random.shuffle(indices)
        if batch_size is None:
            batch_size = n
        epoch_loss = 0.0
        n_batches = 0
        for start in range(0, n, batch_size):
            batch_idx = indices[start : start + batch_size]
            preds: List[Value] = []
            targets: List[float] = []
            for idx in batch_idx:
                out = model(xs[idx])
                preds.append(out[0] if isinstance(out, list) else out)
                targets.append(ys[idx])
            loss = loss_fn(preds, targets)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            epoch_loss += loss.data
            n_batches += 1
        avg_loss = epoch_loss / n_batches
        history.append(avg_loss)
        if verbose and (epoch % max(1, epochs // 10) == 0 or epoch == epochs - 1):
            print(f"epoch {epoch:4d}  loss={avg_loss:.6f}")
    return history


def accuracy(model: MLP, xs: Sequence[Sequence[float]], ys: Sequence[int]) -> float:
    """Classification accuracy for a model outputting a single value."""
    model.eval()
    correct = 0
    for x, y in zip(xs, ys):
        out = model(x)
        pred = out[0].data if isinstance(out, list) else out.data
        pred_label = 1 if pred > 0.5 else 0
        if pred_label == y:
            correct += 1
    model.train()
    return correct / len(xs) if xs else 0.0