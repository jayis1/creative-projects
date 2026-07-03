"""Preset MDP environments used for benchmarking and demonstration.

All factories return an :class:`~rlsolver.mdp.MDP` instance.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

from .mdp import MDP, GridWorld


def make_russell_norvig_grid(size: int = 4, slip: float = 0.0, gamma: float = 0.99) -> MDP:
    """The classic Russell & Norvig 4x4 gridworld (AIMA Figure 17.1).

    The agent starts at (0,0) (top-left).  Goal (+1) at (3,3) bottom-right,
    trap (-1) at (3,0) bottom-left.  Each step costs -0.04.
    """
    gw = GridWorld(
        rows=size,
        cols=size,
        goals={(size - 1, size - 1): 1.0},
        traps={(size - 1, 0): -1.0},
        step_cost=-0.04,
        slip=slip,
        gamma=gamma,
        start=(0, 0),
    )
    return gw.to_mdp()


def make_cliff_walking(width: int = 12, height: int = 4, gamma: float = 0.99) -> MDP:
    """Sutton & Barto Cliff Walking.

    The agent starts at the bottom-left.  The bottom row (except start and
    goal) is a cliff: stepping off gives reward -100 and sends the agent
    back to start (episode continues).  Reaching the goal gives +1 and
    terminates.  All other steps cost -1.
    """
    rows, cols = height, width
    states = [(r, c) for r in range(rows) for c in range(cols)]
    actions = ["N", "S", "E", "W"]
    dirs = {"N": (-1, 0), "S": (1, 0), "E": (0, 1), "W": (0, -1)}
    start = (rows - 1, 0)
    goal = (rows - 1, cols - 1)
    terminals = {goal}
    transitions: Dict = {}

    def in_b(r: int, c: int) -> bool:
        return 0 <= r < rows and 0 <= c < cols

    for (r, c) in states:
        if (r, c) in terminals:
            continue
        transitions[(r, c)] = {}
        for a in actions:
            dr, dc = dirs[a]
            nr, nc = r + dr, c + dc
            if not in_b(nr, nc):
                nr, nc = r, c  # wall -> stay
            # cliff check: bottom row except start and goal
            if nr == rows - 1 and 0 < nc < cols - 1:
                # fell off cliff -> reward -100, back to start
                transitions[(r, c)][a] = [(start, 1.0, -100.0)]
            elif (nr, nc) == goal:
                transitions[(r, c)][a] = [(goal, 1.0, 1.0)]
            else:
                transitions[(r, c)][a] = [((nr, nc), 1.0, -1.0)]
    return MDP(states, actions, transitions, gamma=gamma,
               terminal_states=terminals, start_state=start)


def make_frozen_lake(
    size: int = 4,
    hole_reward: float = -1.0,
    goal_reward: float = 1.0,
    slip: float = 0.33,
    gamma: float = 0.99,
    holes: List[Tuple[int, int]] = [(1, 1), (1, 3), (2, 3), (3, 0)],
) -> MDP:
    """Frozen Lake: navigate a slippery grid to a goal, avoiding holes.

    Slipping (default 1/3) means the agent moves in a random direction
    instead of the intended one.  Falling in a hole terminates with a
    negative reward; reaching the goal terminates with +1.
    """
    gw = GridWorld(
        rows=size,
        cols=size,
        goals={(size - 1, size - 1): goal_reward},
        traps={h: hole_reward for h in holes},
        step_cost=0.0,
        slip=slip,
        gamma=gamma,
        start=(0, 0),
    )
    return gw.to_mdp()


def make_chain(n: int = 5, gamma: float = 0.9, slip: float = 0.0) -> MDP:
    """A 1D chain MDP (Alice's restaurant / chain walk).

    States 0..n-1 in a line.  Two actions: 'left' and 'right'.  Reaching
    state n-1 gives reward +1 (then stays); all other transitions give 0.
    With probability ``slip`` the opposite action is taken.
    """
    states = list(range(n))
    actions = ["left", "right"]
    terminals = {n - 1}
    transitions: Dict = {}
    for s in range(n - 1):
        transitions[s] = {}
        for a in actions:
            intended = a
            opposite = "right" if a == "left" else "left"
            outcomes: Dict[int, List] = {}
            for direction, p in [(intended, 1 - slip), (opposite, slip)]:
                if direction == "left":
                    ns = max(0, s - 1)
                else:
                    ns = min(n - 1, s + 1)
                if ns == n - 1:
                    r = 1.0
                else:
                    r = 0.0
                outcomes.setdefault(ns, [0.0, r])
                outcomes[ns][0] += p
            transitions[s][a] = [(ns, p, r) for ns, (p, r) in outcomes.items()]
    # terminal state n-1: self-loop reward 1
    transitions[n - 1] = {"left": [(n - 1, 1.0, 1.0)], "right": [(n - 1, 1.0, 1.0)]}
    return MDP(states, actions, transitions, gamma=gamma,
               terminal_states=terminals, start_state=0)


def make_taxi(gamma: float = 0.95) -> MDP:
    """A simplified Taxi MDP.

    States encode (taxi_row, taxi_col, passenger_loc, destination) where
    passenger_loc is one of 4 stands (0-3) or 'in_taxi'.  Actions:
    N/S/E/W (move), 'pickup', 'dropoff'.  Reward: +20 for successful
    dropoff, -1 per step, -10 for illegal pickup/dropoff.

    This is a compact 5x5 variant with 4 stand locations at the corners.
    """
    rows, cols = 5, 5
    stands = [(0, 0), (0, 4), (4, 0), (4, 4)]  # R, G, Y, B
    passenger_locs = [0, 1, 2, 3, "in_taxi"]
    destinations = [0, 1, 2, 3]
    actions = ["N", "S", "E", "W", "pickup", "dropoff"]
    dirs = {"N": (-1, 0), "S": (1, 0), "E": (0, 1), "W": (0, -1)}

    states: List[Tuple] = []
    for r in range(rows):
        for c in range(cols):
            for p in passenger_locs:
                for d in destinations:
                    states.append((r, c, p, d))
    terminals: set = set()
    transitions: Dict = {}

    def in_b(rr, cc):
        return 0 <= rr < rows and 0 <= cc < cols

    for st in states:
        r, c, p, d = st
        # terminal if passenger delivered
        if p == "in_taxi" and (r, c) == stands[d]:
            terminals.add(st)
            continue
        transitions[st] = {}
        for a in actions:
            if a in dirs:
                dr, dc = dirs[a]
                nr, nc = r + dr, c + dc
                if not in_b(nr, nc):
                    nr, nc = r, c
                ns = (nr, nc, p, d)
                transitions[st][a] = [(ns, 1.0, -1.0)]
            elif a == "pickup":
                if p != "in_taxi" and (r, c) == stands[p]:
                    ns = (r, c, "in_taxi", d)
                    transitions[st][a] = [(ns, 1.0, -1.0)]
                else:
                    transitions[st][a] = [(st, 1.0, -10.0)]
            elif a == "dropoff":
                if p == "in_taxi" and (r, c) == stands[d]:
                    ns = (r, c, d, d)  # passenger at destination stand
                    # actually delivered -> terminal
                    transitions[st][a] = [(st, 1.0, 20.0)]
                else:
                    transitions[st][a] = [(st, 1.0, -10.0)]
    return MDP(states, actions, transitions, gamma=gamma,
               terminal_states=terminals, start_state=(0, 0, 0, 3))


def make_bridge_walking(size: int = 10, gamma: float = 0.99) -> MDP:
    """Bridge walking: a 1×n bridge over a chasm.

    The agent walks along a 1-row bridge of ``size`` cells.  At each end
    there is a choice of going forward or "jumping off" (W from left,
    E from right).  Reaching the far end gives +10; jumping gives −10 and
    resets to start.  Every step costs −1.
    """
    states = [(0, c) for c in range(size)]
    # add off-bridge states
    off_left = (-1, 0)
    off_right = (-2, 0)
    all_states = states + [off_left, off_right]
    actions = ["N", "S", "E", "W"]
    terminals = {(0, size - 1), off_left, off_right}
    transitions: Dict = {}
    for (r, c) in states:
        if (r, c) in terminals:
            continue
        transitions[(r, c)] = {}
        for a in actions:
            if a == "E":
                if c + 1 < size:
                    ns = (0, c + 1)
                    reward = 10.0 if ns == (0, size - 1) else -1.0
                else:
                    ns = off_right
                    reward = -10.0
            elif a == "W":
                if c == 0:
                    ns = off_left
                    reward = -10.0
                else:
                    ns = (0, c - 1)
                    reward = -1.0
            else:
                ns = (0, c)  # N/S do nothing on a 1-row bridge
                reward = -1.0
            transitions[(r, c)][a] = [(ns, 1.0, reward)]
    return MDP(all_states, actions, transitions, gamma=gamma,
               terminal_states=terminals, start_state=(0, 0))


def make_random_mdp(
    n_states: int = 10,
    n_actions: int = 3,
    gamma: float = 0.9,
    seed: int = 0,
    reward_range: Tuple[float, float] = (-1.0, 1.0),
    terminal_frac: float = 0.1,
) -> MDP:
    """Generate a random MDP with given dimensions.

    Each (state, action) pair gets a random distribution over next states
    and random rewards.  Useful for stress-testing planners.
    """
    import random as _r
    rng = _r.Random(seed)
    states = list(range(n_states))
    actions = [f"a{i}" for i in range(n_actions)]
    n_term = max(1, int(n_states * terminal_frac))
    terminals = set(rng.sample(states, n_term))
    transitions: Dict = {}
    for s in states:
        if s in terminals:
            continue
        transitions[s] = {}
        for a in actions:
            # random number of next states (1-4)
            k = rng.randint(1, min(4, n_states))
            next_states = rng.sample(states, k)
            # random probabilities
            raw = [rng.random() for _ in range(k)]
            total = sum(raw)
            probs = [x / total for x in raw]
            outcomes = []
            for ns, p in zip(next_states, probs):
                r = rng.uniform(*reward_range)
                outcomes.append((ns, p, r))
            transitions[s][a] = outcomes
    return MDP(states, actions, transitions, gamma=gamma,
               terminal_states=terminals, start_state=0)


PRESETS = {
    "russell_norvig": make_russell_norvig_grid,
    "cliff_walking": make_cliff_walking,
    "frozen_lake": make_frozen_lake,
    "chain": make_chain,
    "taxi": make_taxi,
    "bridge_walking": make_bridge_walking,
    "random": make_random_mdp,
}

__all__ = [
    "make_russell_norvig_grid",
    "make_cliff_walking",
    "make_frozen_lake",
    "make_chain",
    "make_taxi",
    "make_bridge_walking",
    "make_random_mdp",
    "PRESETS",
]