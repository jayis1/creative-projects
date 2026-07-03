"""Model-based and function-approximation RL algorithms.

Includes:
* **Dyna-Q** — model-based Q-learning with planning via a learned model
  and simulated experience (Sutton & Barto §8.2)
* **R-Max** — optimistic-initialisation model-based algorithm with the
  "knows what it knows" property (Brafman & Tennenholtz 2002)
* **Tabular gradient-descent Q-learning** — semi-gradient Q-learning
  with a linear function approximator and tile coding features
* **Boltzmann (softmax) exploration** — temperature-controlled action
  selection, useful for environments where ε-greedy is too coarse

These complement the one-step and n-step tabular learners in
:mod:`rl_solver.learners` and :mod:`rl_solver.nstep`.
"""
from __future__ import annotations

import math
import random
from typing import Any, Dict, List, Optional, Tuple

from .mdp import MDP
from .planners import Policy, greedy_policy
from .learners import _BaseLearner, _eps_greedy_action, Episode, EpisodeStep


# ====================================================================== #
# Boltzmann (softmax) action selection
# ====================================================================== #
def _boltzmann_action(
    q: Dict[Any, Dict[Any, float]],
    state: Any,
    actions: List[Any],
    temperature: float,
    rng: random.Random,
) -> Any:
    """Boltzmann/softmax action selection.

    As ``temperature → 0`` the policy becomes fully greedy; as it → ∞
    the policy becomes uniform-random.  Numerically stable via the
    log-sum-exp trick.
    """
    if not actions:
        return None
    if temperature <= 1e-12:
        # fully greedy with tie-break
        best_q = -math.inf
        best_actions: List[Any] = []
        for a in actions:
            qa = q.get(state, {}).get(a, 0.0)
            if qa > best_q + 1e-12:
                best_q = qa
                best_actions = [a]
            elif abs(qa - best_q) <= 1e-12:
                best_actions.append(a)
        return rng.choice(best_actions)
    # softmax with log-sum-exp stabilisation
    logits = [q.get(state, {}).get(a, 0.0) / temperature for a in actions]
    mx = max(logits)
    exps = [math.exp(l - mx) for l in logits]
    total = sum(exps)
    probs = [e / total for e in exps]
    u = rng.random()
    cum = 0.0
    for a, p in zip(actions, probs):
        cum += p
        if u <= cum:
            return a
    return actions[-1]


# ====================================================================== #
# Dyna-Q
# ====================================================================== #
class DynaQLearner(_BaseLearner):
    """Dyna-Q: model-based Q-learning with simulated planning steps.

    After each real environment step, the agent performs ``n_planning``
    additional updates using *simulated* experience drawn from a learned
    tabular model of the environment.  The model is simply a table
    mapping (s, a) -> (next_state, reward) for deterministic MDPs, or a
    list of observed outcomes for stochastic MDPs (sampled uniformly).

    Parameters
    ----------
    n_planning : number of simulated planning updates per real step.
    """
    def __init__(
        self,
        *args,
        n_planning: int = 10,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        if n_planning < 0:
            raise ValueError("n_planning must be >= 0")
        self.n_planning = n_planning
        # Model: (s,a) -> list of (next_state, reward) observations
        self._model: Dict[Tuple[Any, Any], List[Tuple[Any, float]]] = {}
        self._visited: List[Tuple[Any, Any]] = []  # for random sampling

    def _update(self, s: Any, a: Any, r: float, ns: Any, done: bool) -> None:
        self._ensure_q(ns)
        # 1. Direct Q-learning update from real experience
        if done:
            target = r
        else:
            nq = self.Q.get(ns, {})
            max_next = max(nq.values()) if nq else 0.0
            target = r + self.mdp.gamma * max_next
        self.Q[s][a] += self.alpha * (target - self.Q[s][a])

        # 2. Update model
        sa = (s, a)
        if sa not in self._model:
            self._model[sa] = []
            self._visited.append(sa)
        self._model[sa].append((ns, r))

        # 3. Planning: random sample from model
        for _ in range(self.n_planning):
            if not self._visited:
                break
            idx = self.rng.randint(0, len(self._visited) - 1)
            ms, ma = self._visited[idx]
            outcomes = self._model[(ms, ma)]
            ns_m, r_m = outcomes[self.rng.randint(0, len(outcomes) - 1)]
            if self.mdp.is_terminal(ns_m):
                t = r_m
            else:
                self._ensure_q(ns_m)
                nq = self.Q.get(ns_m, {})
                max_next = max(nq.values()) if nq else 0.0
                t = r_m + self.mdp.gamma * max_next
            self.Q[ms][ma] += self.alpha * (t - self.Q[ms][ma])


# ====================================================================== #
# R-Max
# ====================================================================== #
class RMaxLearner(_BaseLearner):
    """R-Max: model-based algorithm with optimistic initialization.

    Assumes that any (s, a) pair visited fewer than ``threshold`` times
    yields the maximum possible reward ``r_max``.  Once a pair has been
    sampled enough it switches to model-based planning on the known
    model.  Provides the "knows what it knows" property: the agent only
    plans on the known model and explores the unknown optimistically.
    """
    def __init__(
        self,
        *args,
        r_max: float = 1.0,
        threshold: int = 5,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.r_max = r_max
        self.threshold = threshold
        self._counts: Dict[Tuple[Any, Any], int] = {}
        # Model statistics
        self._next_counts: Dict[Tuple[Any, Any], Dict[Any, int]] = {}
        self._reward_sums: Dict[Tuple[Any, Any], float] = {}
        self._reward_counts: Dict[Tuple[Any, Any], int] = {}

    def _is_known(self, s: Any, a: Any) -> bool:
        return self._counts.get((s, a), 0) >= self.threshold

    def _plan_known(self, max_iter: int = 100, theta: float = 1e-4) -> Dict[Any, float]:
        """Value iteration over the known part of the model.

        Returns V for all states.  Unknown (s,a) use optimistic r_max.
        """
        V = {s: 0.0 for s in self.mdp.states}
        for _ in range(max_iter):
            delta = 0.0
            for s in self.mdp.states:
                acts = self.mdp.available_actions(s)
                if not acts:
                    continue
                if self.mdp.is_terminal(s):
                    continue
                best = -math.inf
                for a in acts:
                    q = self._q_value_direct(s, a, V)
                    if q > best:
                        best = q
                delta = max(delta, abs(best - V[s]))
                V[s] = best
            if delta < theta:
                break
        return V

    def _q_value_direct(self, s: Any, a: Any, V: Dict[Any, float]) -> float:
        """Compute Q(s,a) using current V and the model (no recursion)."""
        if self._is_known(s, a):
            sa = (s, a)
            total = self._counts.get(sa, 0)
            if total == 0:
                return self.r_max
            nc = self._next_counts.get(sa, {})
            exp_r = self._reward_sums.get(sa, 0.0) / max(1, self._reward_counts.get(sa, 1))
            exp_v = 0.0
            for ns, cnt in nc.items():
                p = cnt / total
                if self.mdp.is_terminal(ns):
                    exp_v += p * 0.0
                else:
                    exp_v += p * V.get(ns, 0.0)
            return exp_r + self.mdp.gamma * exp_v
        return self.r_max

    def _q_known(self, s: Any, a: Any) -> float:
        """Return Q for a known (s,a) using a cached V from planning."""
        if not hasattr(self, '_cached_V') or self._cached_V is None:
            self._cached_V = self._plan_known()
        V = self._cached_V
        return self._q_value_direct(s, a, V)

    def _q_value(self, s: Any, a: Any) -> float:
        """Return Q(s,a): optimistic r_max for unknown, model-based otherwise."""
        if self._is_known(s, a):
            return self._q_known(s, a)
        return self.r_max

    def _select_action(self, state: Any) -> Any:
        actions = self.mdp.available_actions(state)
        if not actions:
            return None
        eps = self._current_epsilon()
        if self.rng.random() < eps:
            return self.rng.choice(actions)
        best_q = -math.inf
        best_actions: List[Any] = []
        for a in actions:
            qa = self._q_value(state, a)
            if qa > best_q + 1e-12:
                best_q = qa
                best_actions = [a]
            elif abs(qa - best_q) <= 1e-12:
                best_actions.append(a)
        return self.rng.choice(best_actions)

    def _update(self, s: Any, a: Any, r: float, ns: Any, done: bool) -> None:
        sa = (s, a)
        self._counts[sa] = self._counts.get(sa, 0) + 1
        self._next_counts.setdefault(sa, {})
        self._next_counts[sa][ns] = self._next_counts[sa].get(ns, 0) + 1
        self._reward_sums[sa] = self._reward_sums.get(sa, 0.0) + r
        self._reward_counts[sa] = self._reward_counts.get(sa, 0) + 1
        self._ensure_q(ns)
        # Invalidate cached V so it's recomputed on next access
        self._cached_V = None
        # Update Q table based on current model
        self.Q[s][a] = self._q_value(s, a)

    def value_function(self) -> Dict[Any, float]:
        return {s: max((self._q_value(s, a) for a in self.mdp.available_actions(s)),
                       default=0.0)
                for s in self.mdp.states}

    def greedy_policy(self) -> Policy:
        pi = Policy(self.mdp)
        for s in self.mdp.states:
            acts = self.mdp.available_actions(s)
            if not acts:
                pi[s] = None
                continue
            best_a = acts[0]
            best_q = -math.inf
            for a in acts:
                q = self._q_value(s, a)
                if q > best_q + 1e-12:
                    best_q = q
                    best_a = a
            pi[s] = best_a
        return pi


# ====================================================================== #
# Tabular gradient-descent Q-learning with tile coding
# ====================================================================== #
class TileCoder:
    """Multi-tiling tile coder for feature extraction.

    Maps a continuous state into a sparse binary feature vector via
    multiple offset tilings.  Used by the gradient Q-learner.
    """
    def __init__(
        self,
        n_tilings: int = 8,
        bins_per_dim: int = 8,
        low: Tuple[float, ...] = (0.0, 0.0),
        high: Tuple[float, ...] = (1.0, 1.0),
        seed: Optional[int] = None,
    ) -> None:
        self.n_tilings = n_tilings
        self.bins = bins_per_dim
        self.low = low
        self.high = high
        self.dim = len(low)
        rng = random.Random(seed)
        # Random offset per tiling, per dimension (asymmetric offsets)
        self.offsets: List[Tuple[float, ...]] = []
        for _ in range(n_tilings):
            off = tuple(rng.uniform(-0.1, 0.1) / bins_per_dim
                        for _ in range(self.dim))
            self.offsets.append(off)
        self.tile_size = tuple((h - l) / bins_per_dim
                               for l, h in zip(low, high))
        self.n_features = n_tilings * (bins_per_dim ** self.dim)

    def features(self, state: Tuple[float, ...]) -> List[int]:
        """Return the list of active feature indices for *state*."""
        idxs: List[int] = []
        base = 0
        for t in range(self.n_tilings):
            off = self.offsets[t]
            idx = t * (self.bins ** self.dim)
            multiplier = 1
            for d in range(self.dim):
                tile = int((state[d] - self.low[d] + off[d]) / self.tile_size[d])
                tile = max(0, min(self.bins - 1, tile))
                idx += tile * multiplier
                multiplier *= self.bins
            idxs.append(idx)
        return idxs

    @property
    def size(self) -> int:
        return self.n_features


class GradientQLearner:
    """Semi-gradient Q-learning with linear function approximation.

    Uses tile coding for state features and learns a weight vector
    ``w`` such that ``Q(s, a) ≈ w · φ(s, a)``.  Suitable for continuous
    or large state spaces where tabular methods are intractable.

    Note: this learner does **not** inherit from ``_BaseLearner``
    because it manages its own state representation; it still provides
    the same ``run_episode``, ``train``, and ``greedy_policy`` interface.
    """
    def __init__(
        self,
        mdp: MDP,
        tile_coder: TileCoder,
        alpha: float = 0.1,
        epsilon: float = 0.1,
        epsilon_decay: float = 0.999,
        epsilon_min: float = 0.01,
        seed: Optional[int] = None,
    ) -> None:
        self.mdp = mdp
        self.tc = tile_coder
        self.alpha = alpha / tile_coder.n_tilings  # step size normalisation
        self.epsilon = epsilon
        self.epsilon_decay = epsilon_decay
        self.epsilon_min = epsilon_min
        self.rng = random.Random(seed)
        self.n_actions = len(mdp.actions)
        self.action_idx = {a: i for i, a in enumerate(mdp.actions)}
        self.actions = list(mdp.actions)
        # Weight vector: w[action_index][feature_index]
        self.w: Dict[int, Dict[int, float]] = {i: {} for i in range(self.n_actions)}
        self.episode_count = 0
        self.step_count = 0
        self.episode_rewards: List[float] = []
        self.episode_lengths: List[int] = []

    def _state_to_features(self, state: Any) -> List[int]:
        """Convert an MDP state into tile-coded features."""
        # Try to interpret as tuple of floats
        try:
            s_tuple = tuple(float(x) for x in state)
            return self.tc.features(s_tuple)
        except (TypeError, ValueError):
            # Fall back: hash-based index for discrete states
            h = hash(state) % self.tc.size
            return [h]

    def _q(self, state: Any, action: Any) -> float:
        feats = self._state_to_features(state)
        ai = self.action_idx[action]
        w = self.w[ai]
        return sum(w.get(f, 0.0) for f in feats)

    def _current_epsilon(self) -> float:
        return max(self.epsilon_min,
                   self.epsilon * (self.epsilon_decay ** self.episode_count))

    def _select_action(self, state: Any) -> Any:
        actions = self.mdp.available_actions(state)
        if not actions:
            return None
        eps = self._current_epsilon()
        if self.rng.random() < eps:
            return self.rng.choice(actions)
        best_q = -math.inf
        best_actions: List[Any] = []
        for a in actions:
            qa = self._q(state, a)
            if qa > best_q + 1e-12:
                best_q = qa
                best_actions = [a]
            elif abs(qa - best_q) <= 1e-12:
                best_actions.append(a)
        return self.rng.choice(best_actions)

    def run_episode(self, max_steps: int = 10000) -> Episode:
        state = self.mdp.start_state
        episode: Episode = []
        total_reward = 0.0
        for _ in range(max_steps):
            if self.mdp.is_terminal(state):
                break
            action = self._select_action(state)
            if action is None:
                break
            next_state, reward = self.mdp.step(state, action, rng=self.rng)
            done = self.mdp.is_terminal(next_state)
            episode.append((state, action, reward, next_state, done))
            # Semi-gradient Q-learning update
            if done:
                target = reward
            else:
                max_next = max(self._q(next_state, a2)
                               for a2 in self.mdp.available_actions(next_state))
                target = reward + self.mdp.gamma * max_next
            feats = self._state_to_features(state)
            ai = self.action_idx[action]
            current_q = sum(self.w[ai].get(f, 0.0) for f in feats)
            td_error = target - current_q
            for f in feats:
                self.w[ai][f] = self.w[ai].get(f, 0.0) + self.alpha * td_error
            self.step_count += 1
            total_reward += reward
            state = next_state
        self.episode_count += 1
        self.episode_rewards.append(total_reward)
        self.episode_lengths.append(len(episode))
        return episode

    def train(self, n_episodes: int, max_steps: int = 10000,
              verbose: bool = False) -> Dict[str, Any]:
        for i in range(n_episodes):
            self.run_episode(max_steps=max_steps)
            if verbose and (i + 1) % max(1, n_episodes // 10) == 0:
                window = max(1, n_episodes // 10)
                avg = sum(self.episode_rewards[-window:]) / window
                print(f"  episode {i+1}/{n_episodes}  "
                      f"eps={self._current_epsilon():.4f}  avg={avg:.3f}")
        return {
            "episodes": self.episode_count,
            "steps": self.step_count,
            "mean_reward": sum(self.episode_rewards) / max(1, len(self.episode_rewards)),
            "mean_length": sum(self.episode_lengths) / max(1, len(self.episode_lengths)),
        }

    def value_function(self) -> Dict[Any, float]:
        return {s: max(self._q(s, a) for a in self.mdp.available_actions(s))
                       if self.mdp.available_actions(s) else 0.0
                for s in self.mdp.states}

    def greedy_policy(self) -> Policy:
        pi = Policy(self.mdp)
        for s in self.mdp.states:
            acts = self.mdp.available_actions(s)
            if not acts:
                pi[s] = None
                continue
            best_a = acts[0]
            best_q = -math.inf
            for a in acts:
                q = self._q(s, a)
                if q > best_q + 1e-12:
                    best_q = q
                    best_a = a
            pi[s] = best_a
        return pi


# ====================================================================== #
# Boltzmann Q-learning wrapper
# ====================================================================== #
class BoltzmannQLearner(_BaseLearner):
    """Q-learning with Boltzmann (softmax) exploration.

    Instead of ε-greedy, this learner samples actions from a softmax
    distribution with a configurable temperature that can decay over
    episodes.  Provides smoother exploration in environments where
    ε-greedy is too abrupt.
    """
    def __init__(
        self,
        *args,
        temperature: float = 1.0,
        temp_decay: float = 0.999,
        temp_min: float = 0.01,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.temperature = temperature
        self.temp_decay = temp_decay
        self.temp_min = temp_min

    def _current_temp(self) -> float:
        return max(self.temp_min,
                   self.temperature * (self.temp_decay ** self.episode_count))

    def _select_action(self, state: Any) -> Any:
        actions = self.mdp.available_actions(state)
        return _boltzmann_action(self.Q, state, actions,
                                 self._current_temp(), self.rng)

    def _update(self, s: Any, a: Any, r: float, ns: Any, done: bool) -> None:
        self._ensure_q(ns)
        if done:
            target = r
        else:
            nq = self.Q.get(ns, {})
            max_next = max(nq.values()) if nq else 0.0
            target = r + self.mdp.gamma * max_next
        self.Q[s][a] += self.alpha * (target - self.Q[s][a])


__all__ = [
    "DynaQLearner",
    "RMaxLearner",
    "TileCoder",
    "GradientQLearner",
    "BoltzmannQLearner",
    "_boltzmann_action",
]