"""Analysis and metrics for cellular automata.

This module provides tools for analysing CA behaviour:

* **Wolfram classification** — classify 1D elementary rules into the four
  Wolfram classes (I: uniform, II: periodic, III: chaotic, IV: complex).
* **Shannon entropy** — measure the information content of a CA grid or
  spacetime diagram.
* **Density analysis** — track live-cell density over time.
* **Parameter sweep** — run a CA across a range of parameters and collect
  statistics for each configuration.
* **Diversity index** — count distinct local neighbourhoods (a proxy for
  complexity).
* **Hamming distance** — measure the rate of divergence between two CAs
  started from slightly different initial conditions (Lyapunov exponent proxy).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np


# ---------------------------------------------------------------------------
# Wolfram classification
# ---------------------------------------------------------------------------


@dataclass
class WolframClassification:
    """Result of classifying a 1D elementary rule.

    Wolfram's four classes:
        I   — Homogeneous: evolves to a uniform state.
        II  — Periodic: evolves to simple periodic structures.
        III — Chaotic: evolves to aperiodic, random-looking patterns.
        IV  — Complex: evolves to localised, interacting structures.
    """
    rule_number: int
    classification: str  # "I", "II", "III", or "IV"
    description: str
    entropy: float
    density: float
    stability: float  # fraction of steps with no change at edges
    period: Optional[int]  # detected period (for class II)


def classify_elementary_rule(
    rule_number: int,
    width: int = 101,
    steps: int = 200,
    boundary: str = "periodic",
) -> WolframClassification:
    """Classify an elementary 1D rule using empirical heuristics.

    The classification uses entropy, density, and edge stability to
    distinguish the four Wolfram classes.  This is a heuristic method —
    true classification is undecidable in general.
    """
    from .engine import CellularAutomaton
    from .rules import ElementaryRule

    ca = CellularAutomaton(ElementaryRule(rule_number), width=width, boundary=boundary)
    ca.center_seed()
    ca.step(steps)
    spacetime = ca.get_spacetime_array()

    # Compute entropy of the final state (row distribution of 1s).
    final_row = spacetime[-1]
    density = float(final_row.mean())

    # Shannon entropy of block frequencies in the last 50 rows.
    last_rows = spacetime[-50:] if len(spacetime) >= 50 else spacetime
    # Use 4-bit blocks as symbols.
    symbols: Dict[int, int] = {}
    for row in last_rows:
        for i in range(0, len(row) - 3):
            val = int(row[i]) * 8 + int(row[i+1]) * 4 + int(row[i+2]) * 2 + int(row[i+3])
            symbols[val] = symbols.get(val, 0) + 1
    total = sum(symbols.values())
    if total > 0:
        entropy = -sum((c / total) * math.log2(c / total) for c in symbols.values() if c > 0)
    else:
        entropy = 0.0

    # Edge stability: fraction of steps where the leftmost/rightmost cells
    # don't change.
    edge_changes = 0
    for i in range(1, len(spacetime)):
        if spacetime[i, 0] != spacetime[i-1, 0]:
            edge_changes += 1
        if spacetime[i, -1] != spacetime[i-1, -1]:
            edge_changes += 1
    stability = 1.0 - (edge_changes / (2 * max(len(spacetime) - 1, 1)))

    # Detect period in the final 20 rows.
    period = _detect_period(spacetime[-20:] if len(spacetime) >= 20 else spacetime)

    # Classify based on heuristics.
    if density == 0.0 or density == 1.0 or stability > 0.95:
        classification = "I"
        description = "Homogeneous — settles to a uniform state"
    elif period is not None and period <= 20:
        classification = "II"
        description = f"Periodic — stable periodic structure (period {period})"
    elif entropy > 3.5:
        classification = "III"
        description = f"Chaotic — high entropy ({entropy:.2f}), aperiodic behaviour"
    else:
        classification = "IV"
        description = f"Complex — interacting localised structures (entropy {entropy:.2f})"

    return WolframClassification(
        rule_number=rule_number,
        classification=classification,
        description=description,
        entropy=entropy,
        density=density,
        stability=stability,
        period=period,
    )


def _detect_period(rows: np.ndarray, max_period: int = 20) -> Optional[int]:
    """Detect the period of the last row in the sequence."""
    if len(rows) < 2:
        return None
    target = rows[-1]
    for p in range(1, min(max_period, len(rows) - 1)):
        if np.array_equal(rows[-1 - p], target):
            return p
    return None


# ---------------------------------------------------------------------------
# Shannon entropy
# ---------------------------------------------------------------------------


def shannon_entropy(grid: np.ndarray, base: int = 2, block_size: int = 1) -> float:
    """Compute the Shannon entropy of a CA grid.

    If ``block_size > 1`` the grid is divided into blocks of that size and
    the entropy of block frequencies is computed.

    Parameters
    ----------
    grid : np.ndarray
        1D or 2D grid.
    base : int
        Logarithm base (2 = bits, math.e = nats).
    block_size : int
        Size of blocks to use as symbols.
    """
    if grid.ndim == 1:
        grid = grid.reshape(1, -1)
    h, w = grid.shape

    _log = (lambda x: math.log(x, base)) if base != 2 else math.log2

    if block_size == 1:
        # Simple per-cell entropy.
        values, counts = np.unique(grid, return_counts=True)
        probs = counts / counts.sum()
        return -sum(p * _log(p) for p in probs if p > 0)

    # Block entropy.
    symbols: Dict[bytes, int] = {}
    for y in range(h):
        for x in range(0, w - block_size + 1):
            block = grid[y, x:x+block_size].tobytes()
            symbols[block] = symbols.get(block, 0) + 1
    total = sum(symbols.values())
    if total == 0:
        return 0.0
    return -sum((c / total) * _log(c / total) for c in symbols.values() if c > 0)


def spacetime_entropy(spacetime: np.ndarray) -> float:
    """Compute the average per-row Shannon entropy of a spacetime diagram.

    This measures the information content of each timestep, averaged over
    the entire evolution.
    """
    if spacetime.ndim == 1:
        spacetime = spacetime.reshape(1, -1)
    entropies = []
    for row in spacetime:
        values, counts = np.unique(row, return_counts=True)
        if len(counts) < 2:
            entropies.append(0.0)
            continue
        probs = counts / counts.sum()
        entropies.append(-sum(p * math.log2(p) for p in probs if p > 0))
    return float(np.mean(entropies))


# ---------------------------------------------------------------------------
# Density analysis
# ---------------------------------------------------------------------------


@dataclass
class DensityReport:
    """Density analysis over a CA run."""
    densities: List[float] = field(default_factory=list)
    mean: float = 0.0
    std: float = 0.0
    trend: str = "stable"  # "increasing", "decreasing", "stable", "oscillating"

    def to_dict(self) -> Dict:
        return {
            "densities": self.densities,
            "mean": self.mean,
            "std": self.std,
            "trend": self.trend,
        }


def density_over_time(ca, steps: int) -> DensityReport:
    """Track live-cell density over ``steps`` steps.

    Parameters
    ----------
    ca : CellularAutomaton
        The CA to analyse (stepped in-place).
    steps : int
        Number of steps to run.
    """
    densities = []
    for _ in range(steps):
        densities.append(ca.alive_count() / (ca.width * ca.height))
        ca.step()

    arr = np.array(densities)
    report = DensityReport(
        densities=densities,
        mean=float(arr.mean()),
        std=float(arr.std()),
    )

    # Determine trend.
    if len(arr) < 4:
        report.trend = "stable"
    else:
        first_half = arr[:len(arr)//2].mean()
        second_half = arr[len(arr)//2:].mean()
        diff = second_half - first_half
        if abs(diff) < 0.01:
            report.trend = "stable"
        elif diff > 0.02:
            report.trend = "increasing"
        else:
            report.trend = "decreasing"
        # Check oscillation.
        if arr.std() > 0.05 and len(arr) > 10:
            # Check if densities cycle.
            autocorr = np.correlate(arr - arr.mean(), arr - arr.mean(), mode="full")
            autocorr = autocorr[len(autocorr)//2:]  # right half
            if len(autocorr) > 3:
                # Normalised autocorrelation at lag > 0.
                peaks = sum(1 for i in range(2, len(autocorr)) if autocorr[i] > 0.5 * autocorr[0])
                if peaks > 0:
                    report.trend = "oscillating"

    return report


# ---------------------------------------------------------------------------
# Parameter sweep
# ---------------------------------------------------------------------------


@dataclass
class SweepResult:
    """Result of a single parameter sweep configuration."""
    params: Dict
    final_alive: int
    mean_density: float
    stable: bool
    cycle_detected: bool
    cycle_length: int
    entropy: float


def parameter_sweep(
    rule_factory: Callable,
    param_grid: Dict[str, List],
    width: int = 50,
    height: int = 50,
    steps: int = 100,
    density: float = 0.3,
    seed: int = 42,
) -> List[SweepResult]:
    """Run a parameter sweep over a grid of rule parameters.

    Parameters
    ----------
    rule_factory : callable
        Function that takes keyword arguments and returns a Rule instance.
        e.g. ``lambda p, g: ForestFireRule(p=p, g=g)``
    param_grid : dict
        Mapping of parameter name → list of values to try.
        e.g. ``{"p": [0.001, 0.01, 0.05], "g": [0.01, 0.05, 0.1]}``
    width, height : int
        Grid dimensions.
    steps : int
        Steps to run for each configuration.
    density : float
        Initial random density.
    seed : int
        Random seed for reproducibility.

    Returns
    -------
    list of SweepResult
        One result per configuration, sorted by mean density.
    """
    from .engine import CellularAutomaton

    # Generate all combinations.
    keys = list(param_grid.keys())
    combos = [{}]
    for key in keys:
        new_combos = []
        for combo in combos:
            for val in param_grid[key]:
                new_combo = dict(combo)
                new_combo[key] = val
                new_combos.append(new_combo)
        combos = new_combos

    results: List[SweepResult] = []
    for params in combos:
        rule = rule_factory(**params)
        ca = CellularAutomaton(rule, width=width, height=height)
        ca.randomize(density, seed=seed)
        stats = ca.run(steps)
        entropy = shannon_entropy(ca.grid)
        results.append(SweepResult(
            params=params,
            final_alive=stats.final_alive,
            mean_density=stats.final_alive / (width * height),
            stable=stats.stable,
            cycle_detected=stats.cycle_detected,
            cycle_length=stats.cycle_length,
            entropy=entropy,
        ))

    results.sort(key=lambda r: r.mean_density, reverse=True)
    return results


# ---------------------------------------------------------------------------
# Hamming distance / Lyapunov exponent proxy
# ---------------------------------------------------------------------------


def hamming_distance(grid_a: np.ndarray, grid_b: np.ndarray) -> int:
    """Compute the Hamming distance between two grids (number of differing cells)."""
    return int(np.count_nonzero(grid_a != grid_b))


def lyapunov_proxy(
    rule,
    width: int = 100,
    steps: int = 100,
    perturbation: int = 1,
    boundary: str = "periodic",
) -> List[int]:
    """Estimate the Lyapunov exponent of a 1D rule by perturbing the initial state.

    Runs two copies of the same CA from slightly different initial states and
    measures the Hamming distance at each step.  An exponentially growing
    distance indicates chaos (positive Lyapunov exponent).

    Parameters
    ----------
    rule : Rule
        1D rule to test.
    width : int
        Grid width.
    steps : int
        Number of steps to run.
    perturbation : int
        Number of cells to flip in the perturbed copy.
    boundary : str
        Boundary condition.

    Returns
    -------
    list of int
        Hamming distance at each step.
    """
    from .engine import CellularAutomaton

    ca_a = CellularAutomaton(rule, width=width, boundary=boundary)
    ca_b = CellularAutomaton(rule, width=width, boundary=boundary)
    ca_a.center_seed()
    ca_b.center_seed()
    # Perturb: flip a few cells near the centre.
    for i in range(perturbation):
        ca_b.set_cell(width // 2 + i + 1, value=1)

    distances = []
    for _ in range(steps):
        ca_a.step()
        ca_b.step()
        distances.append(hamming_distance(ca_a.grid, ca_b.grid))
    return distances


# ---------------------------------------------------------------------------
# Local pattern diversity
# ---------------------------------------------------------------------------


def local_diversity(grid: np.ndarray, radius: int = 1) -> int:
    """Count the number of distinct local neighbourhoods in a grid.

    Higher diversity suggests more complex/chaotic behaviour.
    """
    if grid.ndim == 1:
        grid = grid.reshape(1, -1)
    h, w = grid.shape
    padded = np.pad(grid, radius, mode="wrap")

    patterns = set()
    for y in range(h):
        for x in range(w):
            block = padded[y:y+2*radius+1, x:x+2*radius+1]
            patterns.add(block.tobytes())
    return len(patterns)