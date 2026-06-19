"""Stochastic Petri nets (SPN): firing rates, CTMC generation, steady-state analysis.

Extends the core PetriNet model with exponentially distributed firing delays.
Each transition gets a firing rate λ; the probability of firing in an
infinitesimal interval dt is λ·dt. The resulting Continuous-Time Markov Chain
(CTMC) can be analyzed for steady-state probabilities.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from .net import PetriNet
from .analysis import reachability_graph, ReachabilityGraph


@dataclass
class StochasticTransition:
    """Transition with a stochastic firing rate."""

    name: str
    rate: float = 1.0
    guard: Optional[callable] = None  # type: ignore[type-arg]
    label: str = ""

    def __post_init__(self) -> None:
        if self.rate <= 0:
            raise ValueError(f"StochasticTransition '{self.name}': rate must be > 0")


class StochasticPetriNet:
    """A Petri net with stochastic firing rates on transitions.

    Wraps a standard PetriNet and associates a firing rate (λ) with each
    transition. The firing delay is exponentially distributed with mean 1/λ.
    """

    def __init__(self, net: PetriNet) -> None:
        self.net = net
        self._rates: dict[str, float] = {}

    def set_rate(self, transition_name: str, rate: float) -> None:
        """Set the firing rate λ for a transition."""
        if transition_name not in self.net.transitions:
            raise KeyError(f"No such transition: {transition_name}")
        if rate <= 0:
            raise ValueError("Rate must be > 0")
        self._rates[transition_name] = rate

    def get_rate(self, transition_name: str) -> float:
        """Get the firing rate λ for a transition (default 1.0)."""
        return self._rates.get(transition_name, 1.0)

    def all_rates(self) -> dict[str, float]:
        """Return rates for all transitions."""
        return {t: self._rates.get(t, 1.0) for t in self.net.transitions}


@dataclass
class CTMCState:
    """A state in the Continuous-Time Markov Chain."""

    marking: dict[str, int]
    transitions: list[tuple[str, float, str]] = field(default_factory=list)
    # (transition_name, rate, target_state_id)
    total_rate: float = 0.0


@dataclass
class CTMC:
    """Continuous-Time Markov Chain derived from a stochastic Petri net."""

    states: dict[str, CTMCState] = field(default_factory=dict)
    initial_id: str = ""
    generator: list[list[float]] = field(default_factory=list)
    state_ids: list[str] = field(default_factory=list)

    @property
    def num_states(self) -> int:
        return len(self.states)


def build_ctmc(
    spn: StochasticPetriNet,
    initial_marking: Optional[dict[str, int]] = None,
    max_states: int = 10_000,
) -> CTMC:
    """Build the Continuous-Time Markov Chain from a stochastic Petri net.

    Uses the reachability graph as the state space. Each edge (transition
    firing) gets a rate equal to the transition's firing rate λ.
    The infinitesimal generator matrix Q is:

        Q[i][j] = sum of rates for transitions from state i to state j  (i ≠ j)
        Q[i][i] = -sum of all outgoing rates from state i
    """
    rg = reachability_graph(
        spn.net,
        initial_marking=initial_marking,
        max_states=max_states,
        detect_omega=False,
    )

    ctmc = CTMC()
    state_ids = sorted(rg.nodes.keys())
    ctmc.state_ids = state_ids
    id_idx = {sid: i for i, sid in enumerate(state_ids)}
    n = len(state_ids)

    for sid in state_ids:
        node = rg.nodes[sid]
        state = CTMCState(marking=dict(node.marking))
        total = 0.0
        for t_name, target_id in node.successors:
            rate = spn.get_rate(t_name)
            state.transitions.append((t_name, rate, target_id))
            total += rate
        state.total_rate = total
        ctmc.states[sid] = state

    ctmc.initial_id = rg.initial_id

    # Build generator matrix Q
    Q = [[0.0] * n for _ in range(n)]
    for sid in state_ids:
        i = id_idx[sid]
        state = ctmc.states[sid]
        for t_name, rate, target_id in state.transitions:
            j = id_idx[target_id]
            Q[i][j] += rate
        Q[i][i] = -state.total_rate

    ctmc.generator = Q
    return ctmc


def steady_state_probabilities(ctmc: CTMC, tolerance: float = 1e-12, max_iter: int = 100_000) -> dict[str, float]:
    """Compute steady-state probabilities π for the CTMC.

    Solves π · Q = 0 with the normalization constraint Σπ = 1.
    Uses an iterative power method on the embedded DTMC.

    Returns a dict mapping state_id -> steady-state probability.
    """
    n = ctmc.num_states
    if n == 0:
        return {}

    # Build transition probability matrix P for the embedded DTMC:
    # P[i][j] = Q[i][j] / total_rate_i  (if total_rate_i > 0)
    # For absorbing states (total_rate = 0), P[i][i] = 1
    P = [[0.0] * n for _ in range(n)]
    for i, sid in enumerate(ctmc.state_ids):
        state = ctmc.states[sid]
        if state.total_rate > 0:
            for t_name, rate, target_id in state.transitions:
                j = ctmc.state_ids.index(target_id)
                P[i][j] = rate / state.total_rate
        else:
            P[i][i] = 1.0  # absorbing state

    # Power iteration: start with uniform distribution
    pi = [1.0 / n] * n
    for iteration in range(max_iter):
        new_pi = [0.0] * n
        for i in range(n):
            for j in range(n):
                new_pi[j] += pi[i] * P[i][j]
        # Check convergence
        diff = sum(abs(new_pi[i] - pi[i]) for i in range(n))
        pi = new_pi
        if diff < tolerance:
            break

    # Normalize
    total = sum(pi)
    if total > 0:
        pi = [p / total for p in pi]

    return {ctmc.state_ids[i]: pi[i] for i in range(n)}


@dataclass
class MonteCarloResult:
    """Result of Monte Carlo simulation of a stochastic Petri net."""

    num_runs: int
    deadlock_count: int
    deadlock_probability: float
    avg_steps: float
    max_steps_seen: int
    min_steps: int
    marking_distribution: dict[str, dict[int, float]] = field(default_factory=dict)
    # place_name -> {token_count: probability}

    def __repr__(self) -> str:
        lines = [
            f"MonteCarloResult(runs={self.num_runs})",
            f"  Deadlock probability: {self.deadlock_probability:.4f}",
            f"  Avg steps: {self.avg_steps:.1f}",
            f"  Steps range: [{self.min_steps}, {self.max_steps_seen}]",
        ]
        if self.marking_distribution:
            lines.append("  Marking distributions:")
            for p_name in sorted(self.marking_distribution):
                dist = self.marking_distribution[p_name]
                parts = [f"{k}:{v:.2%}" for k, v in sorted(dist.items())]
                lines.append(f"    {p_name}: {', '.join(parts)}")
        return "\n".join(lines)


def monte_carlo(
    net: PetriNet,
    num_runs: int = 1000,
    max_steps: int = 1000,
    seed: Optional[int] = None,
) -> MonteCarloResult:
    """Run Monte Carlo simulation: many random walks to estimate deadlock probability.

    Each run fires random enabled transitions until deadlock or max_steps.
    Reports the fraction of runs that deadlocked, average steps, and
    the distribution of token counts per place at the final marking.
    """
    import random

    rng = random.Random(seed)
    deadlock_count = 0
    total_steps = 0
    max_steps_seen = 0
    min_steps = max_steps + 1
    # marking_distribution: place -> {token_count: count}
    place_counts: dict[str, dict[int, int]] = {}

    for run in range(num_runs):
        current = net.initial_marking()
        steps = 0
        deadlocked = False
        for _ in range(max_steps):
            enabled = net.enabled_transitions(current)
            if not enabled:
                deadlocked = True
                break
            choice = rng.choice(enabled)
            current = net.fire(choice, current)
            steps += 1

        if deadlocked:
            deadlock_count += 1
        total_steps += steps
        max_steps_seen = max(max_steps_seen, steps)
        if steps > 0:
            min_steps = min(min_steps, steps)

        # Record final marking distribution
        for p_name, tokens in current.items():
            if p_name not in place_counts:
                place_counts[p_name] = {}
            place_counts[p_name][tokens] = place_counts[p_name].get(tokens, 0) + 1

    # Convert counts to probabilities
    marking_distribution: dict[str, dict[int, float]] = {}
    for p_name, counts in place_counts.items():
        marking_distribution[p_name] = {
            k: v / num_runs for k, v in counts.items()
        }

    return MonteCarloResult(
        num_runs=num_runs,
        deadlock_count=deadlock_count,
        deadlock_probability=deadlock_count / num_runs,
        avg_steps=total_steps / num_runs,
        max_steps_seen=max_steps_seen,
        min_steps=min_steps if min_steps <= max_steps else 0,
        marking_distribution=marking_distribution,
    )


@dataclass
class ExpectedTimeResult:
    """Expected time to absorption or to reach a target marking."""

    expected_time: float
    found_target: bool
    mean_first_passage_time: float

    def __repr__(self) -> str:
        return (
            f"ExpectedTimeResult(expected={self.expected_time:.4f}, "
            f"found={self.found_target}, MFTP={self.mean_first_passage_time:.4f})"
        )


def expected_time_to_target(
    spn: StochasticPetriNet,
    target: dict[str, int],
    initial_marking: Optional[dict[str, int]] = None,
    max_states: int = 10_000,
) -> ExpectedTimeResult:
    """Compute expected time to reach a target marking.

    Uses the CTMC and solves a system of linear equations:
    For non-target state i: E[i] = 1/total_rate_i + sum_j P[i][j] * E[j]
    For target state i: E[i] = 0

    Returns the expected time from the initial state.
    """
    ctmc = build_ctmc(spn, initial_marking, max_states=max_states)
    n = ctmc.num_states
    if n == 0:
        return ExpectedTimeResult(0.0, False, 0.0)

    # Identify target states
    target_states: set[int] = set()
    for i, sid in enumerate(ctmc.state_ids):
        marking = ctmc.states[sid].marking
        if all(marking.get(k, 0) == v for k, v in target.items()):
            target_states.add(i)

    if not target_states:
        return ExpectedTimeResult(float("inf"), False, float("inf"))

    initial_idx = ctmc.state_ids.index(ctmc.initial_id) if ctmc.initial_id in ctmc.state_ids else 0

    # If initial state is already a target
    if initial_idx in target_states:
        return ExpectedTimeResult(0.0, True, 0.0)

    # Solve E[i] = 1/total_rate_i + sum_j (rate_ij / total_rate_i) * E[j]
    # for non-target states, E[target] = 0
    # Use Gauss-Seidel iteration
    E = [0.0] * n
    for iteration in range(100_000):
        max_diff = 0.0
        for i in range(n):
            if i in target_states:
                continue
            state = ctmc.states[ctmc.state_ids[i]]
            if state.total_rate == 0:
                E[i] = float("inf")  # absorbing, can't reach target
                continue
            new_val = 1.0 / state.total_rate
            for t_name, rate, target_id in state.transitions:
                j = ctmc.state_ids.index(target_id)
                new_val += (rate / state.total_rate) * E[j]
            diff = abs(new_val - E[i])
            max_diff = max(max_diff, diff)
            E[i] = new_val
        if max_diff < 1e-10:
            break

    result = E[initial_idx]
    found = not math.isinf(result)
    return ExpectedTimeResult(result, found, result)