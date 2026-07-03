"""Additional preset MDP environments.

Extends the core environment set with:
* **Maze** — GridWorld with interior walls/obstacles
* **Blackjack** — simplified Blackjack MDP (playable strategy learning)
* **Windy GridWorld** — Sutton & Barto §6.5 example
* **Pendulum** — discretised pendulum swing-up (a continuous-state MDP
  exposed via discrete bins so the tabular algorithms can learn it)
* **Dice Game** — "Alice's dice" toy MDP with a single state and
  multiple actions of varying risk/reward (good for illustrating the
  effect of γ)
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Tuple

from .mdp import MDP, GridWorld


def make_maze(
    width: int = 8,
    height: int = 6,
    walls: List[Tuple[int, int]] = [(1, 1), (1, 2), (2, 1), (3, 3), (3, 4),
                                     (4, 3), (5, 1), (5, 2)],
    goal: Tuple[int, int] = (5, 7),
    start: Tuple[int, int] = (0, 0),
    gamma: float = 0.99,
    step_cost: float = -0.01,
    slip: float = 0.0,
) -> MDP:
    """A gridworld maze with interior wall cells.

    Wall cells are impassable — the agent bounces back to its current
    position.  The goal cell is terminal with reward +1.  All other
    steps cost ``step_cost``.
    """
    wall_set = set(walls)
    # ensure goal/start aren't walls
    wall_set.discard(goal)
    wall_set.discard(start)
    states = [(r, c) for r in range(height) for c in range(width)
              if (r, c) not in wall_set]
    actions = ["N", "S", "E", "W"]
    dirs = {"N": (-1, 0), "S": (1, 0), "E": (0, 1), "W": (0, -1)}
    perp = {"N": ["E", "W"], "S": ["E", "W"],
            "E": ["N", "S"], "W": ["N", "S"]}
    terminals = {goal}
    transitions: Dict = {}

    def in_bounds(r: int, c: int) -> bool:
        return 0 <= r < height and 0 <= c < width and (r, c) not in wall_set

    for (r, c) in states:
        if (r, c) in terminals:
            continue
        transitions[(r, c)] = {}
        for a in actions:
            intended_p = 1.0 - slip
            slip_p = slip / 2.0 if slip > 0 else 0.0
            dist: Dict[Tuple[int, int], float] = {}
            for direction, p in [(a, intended_p)] + [(pd, slip_p) for pd in perp[a]]:
                dr, dc = dirs[direction]
                nr, nc = r + dr, c + dc
                if not in_bounds(nr, nc):
                    nr, nc = r, c  # wall or boundary -> stay
                dist[(nr, nc)] = dist.get((nr, nc), 0.0) + p
            outcomes = []
            for ns, p in dist.items():
                if ns == goal:
                    reward = 1.0
                else:
                    reward = step_cost
                outcomes.append((ns, p, reward))
            transitions[(r, c)][a] = outcomes
    return MDP(states, actions, transitions, gamma=gamma,
               terminal_states=terminals, start_state=start)


def make_windy_gridworld(
    width: int = 10,
    height: int = 7,
    wind: Tuple[int, ...] = (0, 0, 0, 1, 1, 1, 2, 2, 1, 0),
    start: Tuple[int, int] = (3, 0),
    goal: Tuple[int, int] = (3, 7),
    gamma: float = 1.0,
    king_moves: bool = False,
) -> MDP:
    """Windy GridWorld (Sutton & Barto Example 6.5 / Ex 6.9).

    The agent navigates a grid where each column has an upward *wind*
    that pushes the agent after each action.  Standard moves are
    N/S/E/W; with ``king_moves=True`` the agent can also move
    diagonally (8 actions).  Every step costs −1; reaching the goal
    ends the episode.
    """
    wind_list = list(wind)
    if len(wind_list) < width:
        wind_list += [0] * (width - len(wind_list))
    states = [(r, c) for r in range(height) for c in range(width)]
    actions = ["N", "S", "E", "W"]
    if king_moves:
        actions += ["NE", "NW", "SE", "SW"]
    dirs = {"N": (-1, 0), "S": (1, 0), "E": (0, 1), "W": (0, -1),
            "NE": (-1, 1), "NW": (-1, -1), "SE": (1, 1), "SW": (1, -1)}
    terminals = {goal}
    transitions: Dict = {}

    def in_b(r: int, c: int) -> bool:
        return 0 <= r < height and 0 <= c < width

    for (r, c) in states:
        if (r, c) in terminals:
            continue
        transitions[(r, c)] = {}
        for a in actions:
            dr, dc = dirs[a]
            nr, nc = r + dr, c + dc
            # Apply wind (upward push) — column-based
            nr -= wind_list[c]
            # Clamp to bounds
            nr = max(0, min(height - 1, nr))
            nc = max(0, min(width - 1, nc))
            transitions[(r, c)][a] = [((nr, nc), 1.0, -1.0)]
    return MDP(states, actions, transitions, gamma=gamma,
               terminal_states=terminals, start_state=start)


def make_blackjack(
    gamma: float = 1.0,
    hit_on_soft_17: bool = True,
) -> MDP:
    """A simplified, fully-observable Blackjack MDP.

    States are ``(player_sum, dealer_show, usable_ace)`` tuples where
    ``player_sum`` ∈ [12, 21], ``dealer_show`` ∈ [1, 10] (1 = ace),
    and ``usable_ace`` is a bool.  Three absorbing terminal states
    ``WIN``, ``LOSE``, ``PUSH`` represent resolved outcomes.

    Actions:
    * ``hit`` — draw a card (1–10, uniform — face cards count as 10);
      if the player busts (sum > 21) the transition goes to ``LOSE``.
    * ``stand`` — the dealer plays out its hand deterministically and
      the outcome is sampled from the dealer's draw distribution.  The
      terminal reward is +1 (win), −1 (lose), or 0 (push).

    The dealer draws until reaching 17 (hitting soft 17 when
    ``hit_on_soft_17`` is true), with aces counted as 11 when they
    don't bust the hand.
    """
    import random as _r

    def card_value(card: int) -> int:
        return 1 if card == 1 else min(card, 10)

    def _dealer_play(dealer_show: int, rng: _r.Random) -> int:
        """Return dealer's final total; 0 means bust."""
        cards = [dealer_show]
        while True:
            total = 0
            aces = 0
            for c in cards:
                if c == 1:
                    aces += 1
                    total += 11
                else:
                    total += min(c, 10)
            while total > 21 and aces > 0:
                total -= 10
                aces -= 1
            if total >= 17:
                if total == 17 and aces > 0 and hit_on_soft_17:
                    cards.append(rng.randint(1, 10))
                    continue
                return total
            cards.append(rng.randint(1, 10))

    # Player states
    player_states: List[Tuple] = []
    for p in range(12, 22):
        for d in range(1, 11):
            player_states.append((p, d, False))
            player_states.append((p, d, True))
    terminals = {"WIN", "LOSE", "PUSH"}
    states: List = list(player_states) + ["WIN", "LOSE", "PUSH"]
    actions = ["hit", "stand"]
    transitions: Dict = {}

    for s in player_states:
        p, d, ua = s
        transitions[s] = {}
        # --- hit ---
        hit_dist: Dict[Any, List[float]] = {}  # ns -> [prob, reward]
        for card in range(1, 11):
            prob = 1.0 / 10.0
            val = 11 if card == 1 else card
            new_sum = p + val
            new_ua = ua or (card == 1)
            # convert ace if bust
            if new_sum > 21 and new_ua:
                new_sum -= 10
                if card == 1:
                    new_ua = False
                else:
                    new_ua = ua  # existing ace converted
            if new_sum > 21:
                ns = "LOSE"
            elif new_sum >= 12:
                ns = (new_sum, d, new_ua)
            else:
                # < 12: treat as still in play with the new sum
                ns = (max(12, new_sum), d, new_ua)
            hit_dist.setdefault(ns, [0.0, 0.0])
            hit_dist[ns][0] += prob
        transitions[s]["hit"] = [(ns, info[0], info[1])
                                  for ns, info in hit_dist.items()]
        # --- stand: sample dealer outcomes ---
        rng = _r.Random(98765 + d * 31 + p * 100 + (1 if ua else 0) * 100000)
        n_samples = 2000
        counts = {"WIN": 0, "LOSE": 0, "PUSH": 0}
        for _ in range(n_samples):
            dealer = _dealer_play(d, rng)
            if dealer == 0 or dealer < p:
                counts["WIN"] += 1
            elif dealer > p:
                counts["LOSE"] += 1
            else:
                counts["PUSH"] += 1
        stand_dist: Dict[str, List[float]] = {}
        for outcome, cnt in counts.items():
            prob = cnt / n_samples
            reward = 1.0 if outcome == "WIN" else (-1.0 if outcome == "LOSE" else 0.0)
            stand_dist.setdefault(outcome, [0.0, 0.0])
            stand_dist[outcome][0] += prob
            stand_dist[outcome][1] = reward
        transitions[s]["stand"] = [(ns, info[0], info[1])
                                    for ns, info in stand_dist.items()]

    return MDP(states, actions, transitions, gamma=gamma,
               terminal_states=terminals, start_state=(13, 1, False))


def make_dice_game(gamma: float = 0.9) -> MDP:
    """A one-state MDP with three actions of varying risk.

    State 0: the only non-terminal state.
    * **roll_safe** — reward 2.5 on average, no risk.
    * **roll_medium** — reward 4 with 50% chance, 0 with 50%.
    * **roll_risky** — reward 6 with 1/6 chance, 0 with 5/6.

    After any roll there is a 10% chance of entering the terminal
    "game_over" state (representing the end of a finite game).
    """
    states = [0, "game_over"]
    actions = ["roll_safe", "roll_medium", "roll_risky"]
    terminals = {"game_over"}
    transitions: Dict = {
        0: {
            "roll_safe": [
                (0, 0.9, 2.5),
                ("game_over", 0.1, 2.5),
            ],
            "roll_medium": [
                (0, 0.45, 4.0),
                ("game_over", 0.05, 4.0),
                (0, 0.45, 0.0),
                ("game_over", 0.05, 0.0),
            ],
            "roll_risky": [
                (0, 0.15, 6.0),   # 1/6 * 0.9
                ("game_over", 1/60, 6.0),  # 1/6 * 0.1
                (0, 0.75, 0.0),   # 5/6 * 0.9
                ("game_over", 5/60, 0.0),  # 5/6 * 0.1
            ],
        },
    }
    return MDP(states, actions, transitions, gamma=gamma,
               terminal_states=terminals, start_state=0)


def make_pendulum(
    n_angle_bins: int = 16,
    n_vel_bins: int = 12,
    gamma: float = 0.95,
    max_torque: float = 1.0,
) -> MDP:
    """A discretised pendulum swing-up MDP.

    The state space is the pendulum angle θ ∈ [−π, π] and angular
    velocity ω ∈ [−8, 8], each discretised into bins.  Actions are
    discrete torques ``{-max, 0, +max}``.  The reward is
    ``-(θ² + 0.1ω² + 0.001a²)``, rewarding an upright position.

    This is a classic control problem, here made tabular so the
    existing learners can tackle it.  The dynamics integrate one
    Euler step per transition:

        ω' = ω + (3g/(2L)·sin(θ) - 3a/(m·L²)) · dt
        θ' = θ + ω' · dt
    """
    import math as _m
    g = 10.0
    L = 1.0
    m = 1.0
    dt = 0.05
    angle_low, angle_high = -_m.pi, _m.pi
    vel_low, vel_high = -8.0, 8.0
    actions = [-max_torque, 0.0, max_torque]
    angle_edges = [angle_low + i * (angle_high - angle_low) / n_angle_bins
                   for i in range(n_angle_bins + 1)]
    vel_edges = [vel_low + i * (vel_high - vel_low) / n_vel_bins
                 for i in range(n_vel_bins + 1)]
    states: List[Tuple[int, int]] = []
    for ai in range(n_angle_bins):
        for vi in range(n_vel_bins):
            states.append((ai, vi))

    def angle_center(ai: int) -> float:
        return (angle_edges[ai] + angle_edges[ai + 1]) / 2

    def vel_center(vi: int) -> float:
        return (vel_edges[vi] + vel_edges[vi + 1]) / 2

    def to_bin(theta: float, omega: float) -> Tuple[int, int]:
        # wrap angle
        while theta > _m.pi:
            theta -= 2 * _m.pi
        while theta < -_m.pi:
            theta += 2 * _m.pi
        ai = min(n_angle_bins - 1, max(0, int((theta - angle_low) /
                                              (angle_high - angle_low) * n_angle_bins)))
        vi = min(n_vel_bins - 1, max(0, int((omega - vel_low) /
                                             (vel_high - vel_low) * n_vel_bins)))
        return ai, vi

    transitions: Dict = {}
    for (ai, vi) in states:
        transitions[(ai, vi)] = {}
        theta = angle_center(ai)
        omega = vel_center(vi)
        for a in actions:
            new_omega = omega + (3 * g / (2 * L) * _m.sin(theta) -
                                 3 * a / (m * L ** 2)) * dt
            new_theta = theta + new_omega * dt
            new_omega = max(vel_low, min(vel_high, new_omega))
            reward = -(theta ** 2 + 0.1 * omega ** 2 + 0.001 * a ** 2)
            ns = to_bin(new_theta, new_omega)
            transitions[(ai, vi)][a] = [(ns, 1.0, reward)]
    return MDP(states, actions, transitions, gamma=gamma,
               terminal_states=None, start_state=(n_angle_bins // 2, 0))


# ====================================================================== #
# Extended preset registry
# ====================================================================== #
from .environments import PRESETS as _CORE_PRESETS  # noqa: E402

EXTENDED_PRESETS = {
    **_CORE_PRESETS,
    "maze": make_maze,
    "windy": make_windy_gridworld,
    "blackjack": make_blackjack,
    "dice": make_dice_game,
    "pendulum": make_pendulum,
}

__all__ = [
    "make_maze",
    "make_windy_gridworld",
    "make_blackjack",
    "make_dice_game",
    "make_pendulum",
    "EXTENDED_PRESETS",
]