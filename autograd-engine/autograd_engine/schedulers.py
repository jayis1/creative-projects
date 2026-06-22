"""Learning-rate schedulers for the training loop.

Each scheduler receives the current epoch (starting from 0) and returns the
learning rate to use for that epoch.  They can be used with the CLI, the
``train`` function (via the ``lr_scheduler`` argument), or standalone.

Schedulers provided
-------------------
``StepLR``        — multiply LR by ``gamma`` every ``step_size`` epochs
``ExponentialLR`` — multiply LR by ``gamma`` every epoch
``CosineAnnealingLR`` — cosine annealing to ``eta_min`` over ``T_max`` epochs
``LinearLR``     — linearly interpolate from ``start_lr`` to ``end_lr``
``WarmupLR``     — linear warmup for ``warmup_epochs`` then a base scheduler
``ReduceOnPlateauLR`` — reduce LR when a metric stops improving
"""

from __future__ import annotations

from typing import Callable, List, Optional


class LRScheduler:
    """Base class — subclasses implement ``get_lr(epoch)``."""

    def get_lr(self, epoch: int) -> float:
        raise NotImplementedError

    def __call__(self, epoch: int) -> float:
        return self.get_lr(epoch)


class StepLR(LRScheduler):
    """Multiply LR by ``gamma`` every ``step_size`` epochs."""

    def __init__(self, base_lr: float, step_size: int, gamma: float = 0.1) -> None:
        if step_size <= 0:
            raise ValueError("step_size must be positive")
        self.base_lr = base_lr
        self.step_size = step_size
        self.gamma = gamma

    def get_lr(self, epoch: int) -> float:
        return self.base_lr * (self.gamma ** (epoch // self.step_size))


class ExponentialLR(LRScheduler):
    """Multiply LR by ``gamma`` every epoch."""

    def __init__(self, base_lr: float, gamma: float = 0.99) -> None:
        self.base_lr = base_lr
        self.gamma = gamma

    def get_lr(self, epoch: int) -> float:
        return self.base_lr * (self.gamma ** epoch)


class CosineAnnealingLR(LRScheduler):
    """Cosine annealing from ``base_lr`` to ``eta_min`` over ``T_max`` epochs."""

    def __init__(self, base_lr: float, T_max: int, eta_min: float = 0.0) -> None:
        import math
        self.base_lr = base_lr
        self.T_max = T_max
        self.eta_min = eta_min
        self._math = math

    def get_lr(self, epoch: int) -> float:
        if epoch >= self.T_max:
            return self.eta_min
        return self.eta_min + 0.5 * (self.base_lr - self.eta_min) * (
            1.0 + self._math.cos(self._math.pi * epoch / self.T_max)
        )


class LinearLR(LRScheduler):
    """Linearly interpolate from ``start_lr`` to ``end_lr`` over ``total_epochs``."""

    def __init__(self, start_lr: float, end_lr: float, total_epochs: int) -> None:
        self.start_lr = start_lr
        self.end_lr = end_lr
        self.total_epochs = total_epochs

    def get_lr(self, epoch: int) -> float:
        if epoch >= self.total_epochs:
            return self.end_lr
        frac = epoch / self.total_epochs
        return self.start_lr + (self.end_lr - self.start_lr) * frac


class WarmupLR(LRScheduler):
    """Linear warmup for ``warmup_epochs`` then hand off to a base scheduler."""

    def __init__(self, base_scheduler: LRScheduler, warmup_epochs: int,
                 warmup_start_lr: float = 0.0) -> None:
        self.base_scheduler = base_scheduler
        self.warmup_epochs = warmup_epochs
        self.warmup_start_lr = warmup_start_lr

    def get_lr(self, epoch: int) -> float:
        if epoch < self.warmup_epochs:
            frac = (epoch + 1) / self.warmup_epochs
            base_lr = self.base_scheduler.get_lr(0)
            return self.warmup_start_lr + (base_lr - self.warmup_start_lr) * frac
        return self.base_scheduler.get_lr(epoch - self.warmup_epochs)


class ReduceOnPlateauLR(LRScheduler):
    """Reduce LR when a monitored metric stops improving.

    Call ``step(metric)`` after each epoch with the validation metric.
    If the metric does not improve for ``patience`` epochs, the LR is
    multiplied by ``factor``.
    """

    def __init__(
        self,
        base_lr: float,
        factor: float = 0.5,
        patience: int = 5,
        min_lr: float = 1e-8,
        mode: str = "min",
    ) -> None:
        self.base_lr = base_lr
        self.factor = factor
        self.patience = patience
        self.min_lr = min_lr
        self.mode = mode
        self._current_lr = base_lr
        self._best: Optional[float] = None
        self._wait = 0

    def get_lr(self, epoch: int) -> float:
        return self._current_lr

    def step_metric(self, metric: float) -> None:
        """Update internal state based on a new metric value."""
        improved = (
            self._best is None
            or (self.mode == "min" and metric < self._best)
            or (self.mode == "max" and metric > self._best)
        )
        if improved:
            self._best = metric
            self._wait = 0
        else:
            self._wait += 1
            if self._wait >= self.patience:
                self._current_lr = max(self._current_lr * self.factor, self.min_lr)
                self._wait = 0


def get_scheduler(name: str, **kwargs) -> LRScheduler:
    """Factory: build a scheduler by name from config."""
    registry = {
        "step": StepLR,
        "exponential": ExponentialLR,
        "cosine": CosineAnnealingLR,
        "linear": LinearLR,
    }
    if name == "warmup":
        # warmup needs a base scheduler
        base_name = kwargs.pop("base_scheduler", "cosine")
        base = registry.get(base_name, CosineAnnealingLR)(**kwargs)
        warmup_epochs = kwargs.pop("warmup_epochs", 5)
        warmup_start = kwargs.pop("warmup_start_lr", 0.0)
        return WarmupLR(base, warmup_epochs, warmup_start)
    if name == "plateau":
        return ReduceOnPlateauLR(**kwargs)
    cls = registry.get(name)
    if cls is None:
        raise ValueError(f"Unknown scheduler '{name}'. Available: {sorted(registry)}")
    return cls(**kwargs)