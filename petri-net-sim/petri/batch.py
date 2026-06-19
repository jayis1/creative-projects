"""Batch simulation runner: run many simulations and aggregate statistics.

Useful for Monte Carlo analysis of Petri nets: estimating deadlock
probability, throughput, average token counts, and confidence intervals.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Optional

from .net import PetriNet
from .simulator import Simulator


@dataclass
class BatchStats:
    """Aggregated statistics from a batch of simulation runs."""

    num_runs: int
    deadlock_count: int
    deadlock_probability: float
    deadlock_ci_low: float
    deadlock_ci_high: float
    mean_steps: float
    std_steps: float
    min_steps: int
    max_steps: int
    mean_final_tokens: dict[str, float]
    std_final_tokens: dict[str, float]
    transition_fire_counts: dict[str, int]
    transition_fire_frequencies: dict[str, float]

    def __repr__(self) -> str:
        lines = [
            f"BatchStats(n={self.num_runs})",
            f"  Deadlock prob: {self.deadlock_probability:.4f} "
            f"(95% CI: [{self.deadlock_ci_low:.4f}, {self.deadlock_ci_high:.4f}])",
            f"  Steps: mean={self.mean_steps:.1f}, std={self.std_steps:.1f}, "
            f"range=[{self.min_steps}, {self.max_steps}]",
        ]
        if self.mean_final_tokens:
            lines.append("  Mean final tokens:")
            for p in sorted(self.mean_final_tokens):
                m = self.mean_final_tokens[p]
                s = self.std_final_tokens.get(p, 0.0)
                lines.append(f"    {p}: {m:.2f} ± {s:.2f}")
        if self.transition_fire_frequencies:
            lines.append("  Transition fire frequencies:")
            for t in sorted(self.transition_fire_frequencies):
                lines.append(f"    {t}: {self.transition_fire_frequencies[t]:.4f}")
        return "\n".join(lines)


def batch_simulate(
    net: PetriNet,
    num_runs: int = 1000,
    max_steps: int = 1000,
    seed: Optional[int] = None,
    confidence_level: float = 0.95,
) -> BatchStats:
    """Run many random-walk simulations and aggregate statistics.

    Parameters
    ----------
    net : PetriNet
        The net to simulate.
    num_runs : int
        Number of independent simulation runs.
    max_steps : int
        Maximum steps per run.
    seed : int, optional
        Base seed (each run uses seed + run_index for reproducibility).
    confidence_level : float
        Confidence level for the Wilson score interval on deadlock probability.

    Returns BatchStats with aggregated results.
    """
    import math

    deadlock_count = 0
    steps_list: list[int] = []
    final_tokens: dict[str, list[int]] = {}
    transition_counts: dict[str, int] = {}

    for run in range(num_runs):
        run_seed = seed + run if seed is not None else None
        sim = Simulator(net, seed=run_seed)
        result = sim.random_walk(max_steps=max_steps)

        if result.deadlocked:
            deadlock_count += 1
        steps_list.append(result.steps_fired)

        for p_name, tokens in result.final_marking.items():
            final_tokens.setdefault(p_name, []).append(tokens)

        for rec in result.trace:
            transition_counts[rec.transition] = transition_counts.get(rec.transition, 0) + 1

    # Deadlock probability with Wilson score confidence interval
    p_hat = deadlock_count / num_runs
    z = 1.96 if confidence_level == 0.95 else 1.645  # 95% or 90%
    n = num_runs
    denom = 1 + z**2 / n
    center = (p_hat + z**2 / (2 * n)) / denom
    margin = z * math.sqrt((p_hat * (1 - p_hat) / n) + z**2 / (4 * n**2)) / denom
    ci_low = max(0.0, center - margin)
    ci_high = min(1.0, center + margin)

    # Token statistics
    mean_final: dict[str, float] = {}
    std_final: dict[str, float] = {}
    for p_name, values in final_tokens.items():
        mean_final[p_name] = statistics.mean(values)
        if len(values) > 1:
            std_final[p_name] = statistics.stdev(values)
        else:
            std_final[p_name] = 0.0

    # Transition fire frequencies (per run)
    total_fires = sum(transition_counts.values())
    fire_freqs = {
        t: count / total_fires for t, count in transition_counts.items()
    } if total_fires > 0 else {}

    return BatchStats(
        num_runs=num_runs,
        deadlock_count=deadlock_count,
        deadlock_probability=p_hat,
        deadlock_ci_low=ci_low,
        deadlock_ci_high=ci_high,
        mean_steps=statistics.mean(steps_list),
        std_steps=statistics.stdev(steps_list) if len(steps_list) > 1 else 0.0,
        min_steps=min(steps_list) if steps_list else 0,
        max_steps=max(steps_list) if steps_list else 0,
        mean_final_tokens=mean_final,
        std_final_tokens=std_final,
        transition_fire_counts=transition_counts,
        transition_fire_frequencies=fire_freqs,
    )