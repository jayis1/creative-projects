"""Training utilities: loss functions, optimizers, and a simple training loop."""

from __future__ import annotations

import random
from typing import Callable, List, Sequence, Tuple

from .engine import Value
from .nn import MLP


def mean_squared_error(ypred: Sequence[Value], ytrue: Sequence[float]) -> Value:
    """Return the mean squared error as a ``Value`` graph node."""
    assert len(ypred) == len(ytrue), "prediction/target length mismatch"
    if not ypred:
        raise ValueError("cannot compute MSE on empty sequences")
    return sum((yp - yt) ** 2 for yp, yt in zip(ypred, ytrue)) / len(ytrue)


class SGD:
    """Vanilla stochastic gradient-descent optimizer."""

    def __init__(self, params: List[Value], lr: float = 0.01) -> None:
        self.params = params
        self.lr = lr

    def step(self) -> None:
        for p in self.params:
            p.data -= self.lr * p.grad

    def zero_grad(self) -> None:
        for p in self.params:
            p.grad = 0.0


def train(
    model: MLP,
    xs: Sequence[Sequence[float]],
    ys: Sequence[float],
    *,
    epochs: int = 100,
    lr: float = 0.05,
    seed: int = 42,
    verbose: bool = False,
) -> List[float]:
    """Train a regression MLP and return the per-epoch loss history."""
    random.seed(seed)
    optim = SGD(model.parameters(), lr=lr)
    history: List[float] = []
    for epoch in range(epochs):
        ypred = [model(x)[0] if isinstance(model(x), list) else model(x) for x in xs]
        # re-run forward once (model(x) returns a list for an MLP)
        preds: List[Value] = []
        for x in xs:
            out = model(x)
            preds.append(out[0] if isinstance(out, list) else out)
        loss = mean_squared_error(preds, ys)
        optim.zero_grad()
        loss.backward()
        optim.step()
        history.append(loss.data)
        if verbose and epoch % max(1, epochs // 10) == 0:
            print(f"epoch {epoch:4d}  loss={loss.data:.6f}")
    return history