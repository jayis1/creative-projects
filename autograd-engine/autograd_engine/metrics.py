"""Evaluation metrics for classification and regression.

All functions accept plain Python floats (model predictions and ground-truth
labels) — call ``.data`` on ``Value`` objects before passing them in.
"""

from __future__ import annotations

import math
from typing import Sequence


def accuracy_score(y_true: Sequence[int], y_pred: Sequence[int]) -> float:
    """Classification accuracy (fraction correct)."""
    if len(y_true) != len(y_pred):
        raise ValueError("length mismatch")
    if not y_true:
        return 0.0
    return sum(t == p for t, p in zip(y_true, y_pred)) / len(y_true)


def precision_score(y_true: Sequence[int], y_pred: Sequence[int],
                    positive: int = 1) -> float:
    """Precision = TP / (TP + FP)."""
    tp = sum(t == positive and p == positive for t, p in zip(y_true, y_pred))
    fp = sum(t != positive and p == positive for t, p in zip(y_true, y_pred))
    if tp + fp == 0:
        return 0.0
    return tp / (tp + fp)


def recall_score(y_true: Sequence[int], y_pred: Sequence[int],
                 positive: int = 1) -> float:
    """Recall = TP / (TP + FN)."""
    tp = sum(t == positive and p == positive for t, p in zip(y_true, y_pred))
    fn = sum(t == positive and p != positive for t, p in zip(y_true, y_pred))
    if tp + fn == 0:
        return 0.0
    return tp / (tp + fn)


def f1_score(y_true: Sequence[int], y_pred: Sequence[int],
             positive: int = 1) -> float:
    """F1 = 2 * (precision * recall) / (precision + recall)."""
    p = precision_score(y_true, y_pred, positive)
    r = recall_score(y_true, y_pred, positive)
    if p + r == 0:
        return 0.0
    return 2 * p * r / (p + r)


def confusion_matrix(y_true: Sequence[int], y_pred: Sequence[int],
                     n_classes: int = 2) -> list[list[int]]:
    """Build a confusion matrix as a list of lists."""
    cm = [[0] * n_classes for _ in range(n_classes)]
    for t, p in zip(y_true, y_pred):
        if 0 <= t < n_classes and 0 <= p < n_classes:
            cm[t][p] += 1
    return cm


def mean_squared_error(y_true: Sequence[float], y_pred: Sequence[float]) -> float:
    """MSE (plain-float version, not the graph version)."""
    if len(y_true) != len(y_pred):
        raise ValueError("length mismatch")
    if not y_true:
        raise ValueError("empty sequences")
    return sum((t - p) ** 2 for t, p in zip(y_true, y_pred)) / len(y_true)


def root_mean_squared_error(y_true: Sequence[float], y_pred: Sequence[float]) -> float:
    """RMSE."""
    return math.sqrt(mean_squared_error(y_true, y_pred))


def mean_absolute_error(y_true: Sequence[float], y_pred: Sequence[float]) -> float:
    """MAE."""
    if len(y_true) != len(y_pred):
        raise ValueError("length mismatch")
    if not y_true:
        raise ValueError("empty sequences")
    return sum(abs(t - p) for t, p in zip(y_true, y_pred)) / len(y_true)


def r2_score(y_true: Sequence[float], y_pred: Sequence[float]) -> float:
    """R² coefficient of determination."""
    if len(y_true) != len(y_pred):
        raise ValueError("length mismatch")
    if not y_true:
        raise ValueError("empty sequences")
    mean_t = sum(y_true) / len(y_true)
    ss_res = sum((t - p) ** 2 for t, p in zip(y_true, y_pred))
    ss_tot = sum((t - mean_t) ** 2 for t in y_true)
    if ss_tot == 0:
        return 1.0 if ss_res == 0 else 0.0
    return 1.0 - ss_res / ss_tot


def classification_report(y_true: Sequence[int], y_pred: Sequence[int],
                          n_classes: int = 2) -> str:
    """Generate a human-readable classification report."""
    lines = []
    lines.append(f"{'Class':>8} {'Precision':>10} {'Recall':>10} {'F1':>10} {'Support':>10}")
    lines.append("-" * 52)
    for c in range(n_classes):
        p = precision_score(y_true, y_pred, positive=c)
        r = recall_score(y_true, y_pred, positive=c)
        f1 = f1_score(y_true, y_pred, positive=c)
        support = sum(t == c for t in y_true)
        lines.append(f"{c:>8} {p:>10.4f} {r:>10.4f} {f1:>10.4f} {support:>10}")
    acc = accuracy_score(y_true, y_pred)
    lines.append("-" * 52)
    lines.append(f"{'Accuracy':>8} {'':>10} {'':>10} {'':>10} {len(y_true):>10}")
    lines.append(f"{'':>8} {acc:>38.4f}")
    return "\n".join(lines)