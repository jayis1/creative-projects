"""Core MDP (Markov Decision Process) data structures.

Defines the formal MDP, environments, and transition dynamics used by
all planning and learning algorithms in the toolkit.
"""
from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

State = Any
Action = Any


class MDP:
    """A Markov Decision Process with discrete states and actions.

    Transition probabilities and rewards are specified explicitly, making
    this a *model-based* MDP suitable for dynamic-programming planners
    (value/policy iteration).  Learning algorithms that do not need the
    model (Q-learning, SARSA, Monte-Carlo) can still consume the MDP via
    :meth:`step` sampling.

    Parameters
    ----------
    states : sequence of hashable states
    actions : sequence of hashable actions
    transitions : dict[state][action] -> list of (next_state, prob, reward)
        Each entry is a list of (next_state, probability, reward) tuples.
        Probabilities for a given (state, action) pair must sum to 1.
        A reward of ``None`` is treated as 0.0.
    gamma : discount factor in [0, 1)
    terminal_states : optional set of absorbing states
    start_state : optional initial state (defaults to states[0])
    """

    def __init__(
        self,
        states: Sequence[State],
        actions: Sequence[Action],
        transitions: Dict[State, Dict[Action, List[Tuple[State, float, Optional[float]]]]],
        gamma: float = 0.9,
        terminal_states: Optional[Iterable[State]] = None,
        start_state: Optional[State] = None,
    ) -> None:
        if not states:
            raise ValueError("MDP must have at least one state")
        if not actions:
            raise ValueError("MDP must have at least one action")
        self.states: List[State] = list(states)
        self.actions: List[Action] = list(actions)
        self._state_set = set(self.states)
        self._action_set = set(self.actions)
        self.transitions = transitions
        if not 0.0 <= gamma < 1.0:
            raise ValueError(f"gamma must be in [0, 1), got {gamma}")
        self.gamma = gamma
        self.terminal_states: set = set(terminal_states) if terminal_states else set()
        for ts in self.terminal_states:
            if ts not in self._state_set:
                raise ValueError(f"terminal state {ts!r} not in states")
        self.start_state = start_state if start_state is not None else self.states[0]
        if self.start_state not in self._state_set:
            raise ValueError(f"start_state {self.start_state!r} not in states")
        self._validate()

    # ------------------------------------------------------------------ #
    # validation
    # ------------------------------------------------------------------ #
    def _validate(self) -> None:
        for s in self.states:
            if s not in self.transitions:
                # allow states with no outgoing transitions (terminals)
                continue
            for a, outcomes in self.transitions[s].items():
                if a not in self._action_set:
                    raise ValueError(f"unknown action {a!r} for state {s!r}")
                total = 0.0
                seen = set()
                for ns, p, r in outcomes:
                    if ns not in self._state_set:
                        raise ValueError(
                            f"next_state {ns!r} not in states (from {s!r},{a!r})"
                        )
                    if p < 0 or p > 1:
                        raise ValueError(
                            f"probability {p} out of [0,1] for ({s!r},{a!r})->{ns!r}"
                        )
                    total += p
                    seen.add(ns)
                # allow small floating point slack
                if abs(total - 1.0) > 1e-9:
                    raise ValueError(
                        f"transition probs for ({s!r},{a!r}) sum to {total}, not 1.0"
                    )

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #
    def is_terminal(self, state: State) -> bool:
        return state in self.terminal_states

    def available_actions(self, state: State) -> List[Action]:
        """Actions with defined transitions from *state* (terminals -> [])."""
        if self.is_terminal(state):
            return []
        return [a for a in self.actions if state in self.transitions and a in self.transitions[state]]

    def expected_reward(self, state: State, action: Action) -> float:
        """E[R | s, a] = sum_p p * r."""
        total = 0.0
        for ns, p, r in self.transitions.get(state, {}).get(action, []):
            total += p * (r if r is not None else 0.0)
        return total

    def transition_dist(self, state: State, action: Action) -> List[Tuple[State, float]]:
        """Return list of (next_state, prob) for (state, action)."""
        return [(ns, p) for ns, p, _ in self.transitions.get(state, {}).get(action, [])]

    def step(self, state: State, action: Action, rng: Optional[random.Random] = None) -> Tuple[State, float]:
        """Sample one transition. Returns (next_state, reward)."""
        if self.is_terminal(state):
            return state, 0.0
        outcomes = self.transitions.get(state, {}).get(action)
        if not outcomes:
            raise ValueError(f"no transition defined for ({state!r}, {action!r})")
        rng = rng or random
        u = rng.random()
        cum = 0.0
        for ns, p, r in outcomes:
            cum += p
            if u <= cum:
                return ns, (r if r is not None else 0.0)
        # floating point fallback
        ns, p, r = outcomes[-1]
        return ns, (r if r is not None else 0.0)

    # ------------------------------------------------------------------ #
    # serialization
    # ------------------------------------------------------------------ #
    def to_dict(self) -> Dict[str, Any]:
        def _key(x):
            return x if isinstance(x, (str, int, float, bool)) else str(x)

        trans = {}
        for s, ad in self.transitions.items():
            trans[_key(s)] = {
                _key(a): [[_key(ns), p, r] for ns, p, r in out]
                for a, out in ad.items()
            }
        return {
            "states": [_key(s) for s in self.states],
            "actions": [_key(a) for a in self.actions],
            "transitions": trans,
            "gamma": self.gamma,
            "terminal_states": [_key(s) for s in self.terminal_states],
            "start_state": _key(self.start_state),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)

    def fingerprint(self) -> str:
        return hashlib.sha1(self.to_json().encode()).hexdigest()[:12]


# ====================================================================== #
# GridWorld environment
# ====================================================================== #
@dataclass
class GridWorld:
    """A classic gridworld MDP generator.

    The agent navigates an ``rows x cols`` grid.  Special cells can be
    designated as terminal goals (positive reward) or traps (negative
    reward).  Stepping into a goal/trap ends the episode.  Each step
    costs ``step_cost`` (typically small negative) to encourage short
    paths.  Movement is noisy: with probability ``slip`` the agent moves
    perpendicular instead of the intended direction.

    States are ``(row, col)`` tuples.  Actions are one of
    ``'N','S','E','W'``.
    """

    rows: int
    cols: int
    goals: Dict[Tuple[int, int], float] = field(default_factory=dict)
    traps: Dict[Tuple[int, int], float] = field(default_factory=dict)
    step_cost: float = -0.04
    slip: float = 0.0
    gamma: float = 0.99
    start: Tuple[int, int] = (0, 0)

    _DIRS = {"N": (-1, 0), "S": (1, 0), "E": (0, 1), "W": (0, -1)}
    _PERP = {"N": ["E", "W"], "S": ["E", "W"], "E": ["N", "S"], "W": ["N", "S"]}

    def __post_init__(self) -> None:
        if self.rows < 1 or self.cols < 1:
            raise ValueError("rows and cols must be >= 1")
        if not 0.0 <= self.slip < 1.0:
            raise ValueError("slip must be in [0, 1)")
        if not 0.0 <= self.gamma < 1.0:
            raise ValueError("gamma must be in [0, 1)")
        for g in self.goals:
            self._check_cell(g)
        for t in self.traps:
            self._check_cell(t)
        self._check_cell(self.start)

    def _check_cell(self, cell: Tuple[int, int]) -> None:
        r, c = cell
        if not (0 <= r < self.rows and 0 <= c < self.cols):
            raise ValueError(f"cell {cell} out of bounds ({self.rows}x{self.cols})")

    def _in_bounds(self, r: int, c: int) -> bool:
        return 0 <= r < self.rows and 0 <= c < self.cols

    def states(self) -> List[Tuple[int, int]]:
        return [(r, c) for r in range(self.rows) for c in range(self.cols)]

    def terminal_states(self) -> List[Tuple[int, int]]:
        return list(self.goals.keys()) + list(self.traps.keys())

    def _move(self, r: int, c: int, direction: str) -> Tuple[int, int]:
        dr, dc = self._DIRS[direction]
        nr, nc = r + dr, c + dc
        if self._in_bounds(nr, nc):
            return (nr, nc)
        return (r, c)  # blocked -> stay

    def to_mdp(self) -> MDP:
        states = self.states()
        actions = ["N", "S", "E", "W"]
        terminals = set(self.terminal_states())
        transitions: Dict = {}
        for (r, c) in states:
            if (r, c) in terminals:
                continue
            transitions[(r, c)] = {}
            for a in actions:
                # intended direction prob = 1 - slip, each perpendicular slip/2
                intended_p = 1.0 - self.slip
                slip_p = self.slip / 2.0 if self.slip > 0 else 0.0
                dist: Dict[Tuple[int, int], float] = {}
                # intended
                ns = self._move(r, c, a)
                dist[ns] = dist.get(ns, 0.0) + intended_p
                # slips
                for perp in self._PERP[a]:
                    ns2 = self._move(r, c, perp)
                    dist[ns2] = dist.get(ns2, 0.0) + slip_p
                outcomes = []
                for ns_cell, p in dist.items():
                    if ns_cell in self.goals:
                        reward = self.goals[ns_cell]
                    elif ns_cell in self.traps:
                        reward = self.traps[ns_cell]
                    else:
                        reward = self.step_cost
                    outcomes.append((ns_cell, p, reward))
                transitions[(r, c)][a] = outcomes
        return MDP(
            states=states,
            actions=actions,
            transitions=transitions,
            gamma=self.gamma,
            terminal_states=terminals,
            start_state=self.start,
        )


__all__ = ["MDP", "GridWorld"]