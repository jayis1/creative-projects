"""
ASCII visualization for MCMC traces — trace plots, histograms, and
autocorrelation plots rendered as text for terminal-friendly output.
"""

from __future__ import annotations

import math
from typing import List, Optional

import numpy as np

from .diagnostics import autocorrelation
from .trace import Trace


def ascii_histogram(x: np.ndarray, bins: int = 30, width: int = 60,
                    height: int = 15) -> str:
    """Render a 1-D histogram as ASCII art."""
    x = np.asarray(x, dtype=float).ravel()
    if x.shape[0] < 2:
        return "(not enough samples)"
    counts, edges = np.histogram(x, bins=bins, density=True)
    max_c = counts.max() if counts.max() > 0 else 1
    lines = []
    for row in range(height, 0, -1):
        threshold = max_c * row / height
        bar = ""
        for c in counts:
            bar += "█" if c >= threshold else ("▄" if c >= threshold - max_c / height / 2 else " ")
        lines.append(bar)
    # x-axis labels
    lo, hi = edges[0], edges[-1]
    axis = f"{lo:8.3f}" + " " * (bins - 16) + f"{hi:8.3f}"
    lines.append(axis)
    return "\n".join(lines)


def ascii_trace(x: np.ndarray, width: int = 70, height: int = 12) -> str:
    """Render a trace plot (value vs. iteration) as ASCII art."""
    x = np.asarray(x, dtype=float).ravel()
    n = x.shape[0]
    if n < 2:
        return "(not enough samples)"
    lo, hi = x.min(), x.max()
    if hi == lo:
        hi = lo + 1.0
    # downsample to width
    idx = np.linspace(0, n - 1, width).astype(int)
    xs = x[idx]
    grid = [[" "] * width for _ in range(height)]
    for col, val in enumerate(xs):
        norm = (val - lo) / (hi - lo)
        row = int((1 - norm) * (height - 1))
        row = max(0, min(height - 1, row))
        grid[row][col] = "●"
    lines = ["".join(r) for r in grid]
    label_lo = f"{lo:8.3f} |"
    label_hi = f"{hi:8.3f} |"
    label_mid = f"{(lo+hi)/2:8.3f} |"
    out = []
    out.append(label_hi + lines[0])
    out.append("         |" + lines[height // 2])
    out.append(label_lo + lines[-1])
    out.append("         " + "-" * width)
    out.append(f"  iter 0" + " " * (width - 14) + f"iter {n}")
    return "\n".join(out)


def ascii_acf(x: np.ndarray, max_lag: int = 30, width: int = 50) -> str:
    """Render autocorrelation function as ASCII bar chart."""
    acf = autocorrelation(x, max_lag=max_lag)
    lines = []
    for k, v in enumerate(acf):
        bar_len = int(abs(v) * width)
        if v >= 0:
            lines.append(f"lag {k:3d} |{'█' * bar_len} {v:.3f}")
        else:
            lines.append(f"lag {k:3d} |{'░' * bar_len} {v:.3f}")
    return "\n".join(lines)


def visualize_trace(trace: Trace, param: Optional[int] = None) -> str:
    """Full ASCII report for a trace (or single parameter)."""
    out = []
    if param is not None:
        col = trace.samples[:, param]
        nm = trace.names[param]
        out.append(f"=== {nm} ===")
        out.append("\n--- Trace ---")
        out.append(ascii_trace(col))
        out.append("\n--- Histogram ---")
        out.append(ascii_histogram(col))
        out.append("\n--- Autocorrelation ---")
        out.append(ascii_acf(col))
        return "\n".join(out)
    for i in range(trace.dim):
        out.append(visualize_trace(trace, param=i))
        out.append("")
    return "\n".join(out)