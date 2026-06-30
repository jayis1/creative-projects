"""Text-based visualisation helpers for HMMs.

All functions produce ASCII/ANSI output — no external graphics libraries
required.
"""

from __future__ import annotations

import math
from typing import List, Optional, Sequence, Tuple

from .hmm import HMM
from .algorithms import forward, backward, viterbi, posterior_decode


# ---------------------------------------------------------------------------
# State-transition diagram (ASCII)
# ---------------------------------------------------------------------------

def transition_diagram(hmm: HMM, threshold: float = 0.01) -> str:
    """Render a simple ASCII state-transition diagram.

    Edges with probability < ``threshold`` are omitted for clarity.
    """
    lines: List[str] = []
    lines.append("State Transition Diagram")
    lines.append("=" * 40)
    n = hmm.n_states
    for i in range(n):
        edges = []
        for j in range(n):
            if hmm.A[i][j] >= threshold:
                arrow = "→" if i != j else "↻"
                edges.append(f"{arrow}{hmm.states[j]}({hmm.A[i][j]:.2f})")
        lines.append(f"  {hmm.states[i]:>10}: {'  '.join(edges)}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Viterbi path visualisation
# ---------------------------------------------------------------------------

def viterbi_path_visualization(hmm: HMM, obs_symbols: Sequence[str]) -> str:
    """Render the Viterbi-decoded path alongside the observations."""
    obs = hmm.observation_sequence(obs_symbols)
    path, logp = viterbi(hmm, obs)
    if not path:
        return "Impossible sequence — no valid path."
    lines: List[str] = []
    lines.append(f"Viterbi Path (log-prob = {logp:.4f})")
    lines.append("=" * 50)
    # Header
    n = hmm.n_states
    # Build a grid
    grid: List[List[str]] = []
    for state_idx in range(n):
        row: List[str] = []
        for t in range(len(obs)):
            if path[t] == state_idx:
                row.append(f"[{hmm.states[state_idx]:^3}]")
            else:
                row.append("  .  ")
        grid.append(row)
    # Print observations on top
    obs_line = "  ".join(f"{s:^5}" for s in obs_symbols)
    lines.append(f"  Obs:  {obs_line}")
    lines.append("")
    for i, state_idx in enumerate(range(n)):
        label = hmm.states[state_idx]
        row_str = "  ".join(grid[i])
        lines.append(f"  {label:>6}: {row_str}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Posterior heatmap (ASCII)
# ---------------------------------------------------------------------------

def posterior_heatmap(hmm: HMM, obs_symbols: Sequence[str]) -> str:
    """Render the posterior probability matrix as an ASCII heatmap.

    Uses a 10-level grey scale: ``█`` (≥0.9) down to ``·`` (<0.1).
    """
    obs = hmm.observation_sequence(obs_symbols)
    _, gamma = posterior_decode(hmm, obs)
    if not gamma:
        return "No posterior data (empty or impossible sequence)."
    lines: List[str] = []
    lines.append("Posterior Probability Heatmap")
    lines.append("=" * 50)
    # Legend
    lines.append("  Scale: █ ≥0.9  ▇ ≥0.8  ▆ ≥0.7  ▅ ≥0.6  ▄ ≥0.5  ▃ ≥0.4  ▂ ≥0.3  │ ≥0.2  . ≥0.1  ( <0.1")
    lines.append("")
    # Header with observations
    obs_header = "  t  obs  " + " ".join(f"{hmm.states[i]:>6}" for i in range(hmm.n_states))
    lines.append(obs_header)
    lines.append("  " + "-" * (len(obs_header) - 2))
    scale = "█▇▆▅▄▃▂│.("
    for t in range(len(gamma)):
        cells = []
        for p in gamma[t]:
            idx = min(int(p * 10), 9)
            idx = max(idx, 0)
            cells.append(f"{scale[idx]:>6}")
        lines.append(f"  {t:>2}  {obs_symbols[t]:>3}  " + " ".join(cells))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entropy sparkline
# ---------------------------------------------------------------------------

def entropy_sparkline(hmm: HMM, obs_symbols: Sequence[str]) -> str:
    """Render per-timestep posterior entropy as a Unicode sparkline."""
    from .analysis import state_entropy
    obs = hmm.observation_sequence(obs_symbols)
    entropies = state_entropy(hmm, obs)
    if not entropies:
        return "No entropy data."
    max_h = max(entropies) if entropies else 1.0
    if max_h <= 0:
        max_h = 1.0
    spark = "▁▂▃▄▅▆▇█"
    chars: List[str] = []
    for h in entropies:
        idx = min(int(h / max_h * 7), 7)
        idx = max(idx, 0)
        chars.append(spark[idx])
    lines: List[str] = []
    lines.append("Posterior Entropy Sparkline")
    lines.append("=" * 40)
    lines.append(f"  { ''.join(chars)}")
    lines.append(f"  max={max_h:.4f} nats")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Pretty-print model parameters
# ---------------------------------------------------------------------------

def format_model(hmm: HMM) -> str:
    """Pretty-print all model parameters as a formatted string."""
    lines: List[str] = []
    lines.append(f"HMM: {hmm.n_states} states, {hmm.n_symbols} symbols")
    lines.append("=" * 50)
    lines.append("\nStates:  " + ", ".join(hmm.states))
    lines.append("Symbols: " + ", ".join(hmm.symbols))
    # Transition matrix
    lines.append("\nTransition matrix A:")
    header = "       " + " ".join(f"{s:>10}" for s in hmm.states)
    lines.append(header)
    for i, s in enumerate(hmm.states):
        vals = " ".join(f"{v:>10.6f}" for v in hmm.A[i])
        lines.append(f"  {s:>4} {vals}")
    # Emission matrix
    lines.append("\nEmission matrix B:")
    header = "       " + " ".join(f"{s:>10}" for s in hmm.symbols)
    lines.append(header)
    for i, s in enumerate(hmm.states):
        vals = " ".join(f"{v:>10.6f}" for v in hmm.B[i])
        lines.append(f"  {s:>4} {vals}")
    # Initial distribution
    lines.append("\nInitial distribution π:")
    for s, p in zip(hmm.states, hmm.pi):
        bar = "█" * int(p * 40)
        lines.append(f"  {s:>4}: {p:.6f} {bar}")
    return "\n".join(lines)