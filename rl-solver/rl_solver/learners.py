"""Model-free reinforcement-learning algorithms.

Tabular (non-function-approximation) methods that learn from sampled
experience without access to the MDP transition model:

* Q-learning  (off-policy TD control)
* SARSA       (on-policy TD control)
* Expected SARSA
* Double Q-learning
* Monte-Carlo control (first-visit & every-visit, epsilon-soft)
* n-step SARSA / n-step Tree Backup  (in :mod:`nstep`)

All learners implement a common interface:

    learner = QLearner(mdp, alpha=0.1, epsilon=0.1)
    episode = learner.run_episode(rng=random.Random(0))
    Q = learner.Q   # dict[state][action] -> value
    pi = learner.greedy_policy()

An *episode* is a list of (state, action, reward, next_state, done) tuples.
"""
from __future__ import annotations

import math
import random
from typing import Any, Dict, List, Optional, Tuple

from .mdp import MDP
from .planners import Policy, greedy_policy


EpisodeStep = Tuple[Any, Any, float, Any, bool]
Episode = List[EpisodeStep]


def _eps_greedy_action(
    q: Dict[Any, Dict[Any, float]],
    state: Any,
    actions: List[Any],
    epsilon: float,
    rng: random.Random,
) -> Any:
    """Epsilon-greedy action selection from Q-table."""
    if not actions:
        return None
    if rng.random() < epsilon:
        return rng.choice(actions)
    # greedy with random tie-break
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


class _BaseLearner:
    """Common scaffolding for tabular TD / MC learners."""

    def __init__(
        self,
        mdp: MDP,
        alpha: float = 0.1,
        epsilon: float = 0.1,
        epsilon_decay: float = 0.999,
        epsilon_min: float = 0.01,
        init_q: float = 0.0,
        seed: Optional[int] = None,
    ) -> None:
        self.mdp = mdp
        self.alpha = alpha
        self.epsilon = epsilon
        self.epsilon_decay = epsilon_decay
        self.epsilon_min = epsilon_min
        self.init_q = init_q
        self.rng = random.Random(seed)
        self.Q: Dict[Any, Dict[Any, float]] = {}
        for s in mdp.states:
            self.Q[s] = {a: init_q for a in mdp.available_actions(s)}
        self.episode_count = 0
        self.step_count = 0
        # running stats
        self.episode_rewards: List[float] = []
        self.episode_lengths: List[int] = []

    # ------------------------------------------------------------------ #
    def _current_epsilon(self) -> float:
        return max(self.epsilon_min, self.epsilon * (self.epsilon_decay ** self.episode_count))

    def _select_action(self, state: Any) -> Any:
        eps = self._current_epsilon()
        actions = self.mdp.available_actions(state)
        return _eps_greedy_action(self.Q, state, actions, eps, self.rng)

    def _ensure_q(self, state: Any) -> None:
        if state not in self.Q:
            self.Q[state] = {a: self.init_q for a in self.mdp.available_actions(state)}

    # ------------------------------------------------------------------ #
    def run_episode(self, max_steps: int = 10000) -> Episode:
        """Run one episode of interaction; subclasses override :meth:`_update`."""
        state = self.mdp.start_state
        episode: Episode = []
        total_reward = 0.0
        for _ in range(max_steps):
            if self.mdp.is_terminal(state):
                break
            self._ensure_q(state)
            action = self._select_action(state)
            if action is None:
                break
            next_state, reward = self.mdp.step(state, action, rng=self.rng)
            done = self.mdp.is_terminal(next_state)
            episode.append((state, action, reward, next_state, done))
            self._update(state, action, reward, next_state, done)
            self.step_count += 1
            total_reward += reward
            state = next_state
        self.episode_count += 1
        self.episode_rewards.append(total_reward)
        self.episode_lengths.append(len(episode))
        return episode

    def _update(
        self, s: Any, a: Any, r: float, ns: Any, done: bool
    ) -> None:  # pragma: no cover - abstract
        raise NotImplementedError

    # ------------------------------------------------------------------ #
    def train(self, n_episodes: int, max_steps: int = 10000, verbose: bool = False) -> Dict[str, Any]:
        """Run many episodes and return summary statistics."""
        for i in range(n_episodes):
            self.run_episode(max_steps=max_steps)
            if verbose and (i + 1) % max(1, n_episodes // 10) == 0:
                avg = sum(self.episode_rewards[-max(1, n_episodes // 10):]) / max(1, n_episodes // 10)
                print(f"  episode {i+1}/{n_episodes}  eps={self._current_epsilon():.4f}  avg_reward={avg:.3f}")
        return {
            "episodes": self.episode_count,
            "steps": self.step_count,
            "mean_reward": sum(self.episode_rewards) / max(1, len(self.episode_rewards)),
            "mean_length": sum(self.episode_lengths) / max(1, len(self.episode_lengths)),
        }

    def greedy_policy(self) -> Policy:
        return greedy_policy(self.mdp, self.value_function())

    def value_function(self) -> Dict[Any, float]:
        return {s: max(q.values()) if q else 0.0 for s, q in self.Q.items()}


# ====================================================================== #
# Q-learning
# ====================================================================== #
class QLearner(_BaseLearner):
    """Off-policy TD(0) control: Q(s,a) <- Q + a [r + g max_a' Q(s',a') - Q]."""

    def _update(self, s: Any, a: Any, r: float, ns: Any, done: bool) -> None:
        self._ensure_q(ns)
        if done:
            target = r
        else:
            nq = self.Q.get(ns, {})
            max_next = max(nq.values()) if nq else 0.0
            target = r + self.mdp.gamma * max_next
        self.Q[s][a] += self.alpha * (target - self.Q[s][a])


# ====================================================================== #
# SARSA
# ====================================================================== #
class SARSALearner(_BaseLearner):
    """On-policy TD(0) control: Q(s,a) <- Q + a [r + g Q(s',a') - Q]."""

    def run_episode(self, max_steps: int = 10000) -> Episode:
        state = self.mdp.start_state
        if self.mdp.is_terminal(state):
            self.episode_count += 1
            self.episode_rewards.append(0.0)
            self.episode_lengths.append(0)
            return []
        self._ensure_q(state)
        action = self._select_action(state)
        episode: Episode = []
        total_reward = 0.0
        for _ in range(max_steps):
            next_state, reward = self.mdp.step(state, action, rng=self.rng)
            done = self.mdp.is_terminal(next_state)
            self._ensure_q(next_state)
            next_action = None if done else self._select_action(next_state)
            episode.append((state, action, reward, next_state, done))
            # SARSA update uses the actually chosen next action
            if done:
                target = reward
            else:
                target = reward + self.mdp.gamma * self.Q[next_state][next_action]
            self.Q[state][action] += self.alpha * (target - self.Q[state][action])
            self.step_count += 1
            total_reward += reward
            state = next_state
            action = next_action
            if done or action is None:
                break
        self.episode_count += 1
        self.episode_rewards.append(total_reward)
        self.episode_lengths.append(len(episode))
        return episode

    def _update(self, s: Any, a: Any, r: float, ns: Any, done: bool) -> None:
        # Not used — SARSA overrides run_episode for on-policy next action.
        pass


# ====================================================================== #
# Expected SARSA
# ====================================================================== #
class ExpectedSARSALearner(_BaseLearner):
    """Expected SARSA: target = r + g * E[Q(s',a')] under eps-greedy."""

    def _update(self, s: Any, a: Any, r: float, ns: Any, done: bool) -> None:
        self._ensure_q(ns)
        if done:
            target = r
        else:
            nq = self.Q.get(ns, {})
            actions = self.mdp.available_actions(ns)
            if not actions:
                target = r
            else:
                eps = self._current_epsilon()
                max_q = max(nq.values()) if nq else 0.0
                # find greedy actions (ties)
                greedy_actions = [act for act in actions if abs(nq.get(act, 0.0) - max_q) <= 1e-12]
                expected = 0.0
                for act in actions:
                    p_greedy = eps / len(actions)
                    p_exploit = (1 - eps) / len(greedy_actions) if act in greedy_actions else 0.0
                    p = p_greedy + p_exploit
                    expected += p * nq.get(act, 0.0)
                target = r + self.mdp.gamma * expected
        self.Q[s][a] += self.alpha * (target - self.Q[s][a])


# ====================================================================== #
# Double Q-learning
# ====================================================================== #
class DoubleQLearner(_BaseLearner):
    """Double Q-learning: two independent Q tables to reduce overestimation."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.Q2: Dict[Any, Dict[Any, float]] = {}
        for s in mdp_states(self.mdp):
            self.Q2[s] = {a: self.init_q for a in self.mdp.available_actions(s)}

    def _ensure_q(self, state: Any) -> None:
        super()._ensure_q(state)
        if state not in self.Q2:
            self.Q2[state] = {a: self.init_q for a in self.mdp.available_actions(state)}

    def _select_action(self, state: Any) -> Any:
        eps = self._current_epsilon()
        actions = self.mdp.available_actions(state)
        if not actions:
            return None
        if self.rng.random() < eps:
            return self.rng.choice(actions)
        # greedy on sum Q1 + Q2
        summed = {a: self.Q.get(state, {}).get(a, 0.0) + self.Q2.get(state, {}).get(a, 0.0)
                  for a in actions}
        best_q = max(summed.values())
        best = [a for a in actions if abs(summed[a] - best_q) <= 1e-12]
        return self.rng.choice(best)

    def _update(self, s: Any, a: Any, r: float, ns: Any, done: bool) -> None:
        self._ensure_q(ns)
        if self.rng.random() < 0.5:
            # update Q1 using Q2 for bootstrap
            if done:
                target = r
            else:
                nq1 = self.Q.get(ns, {})
                # argmax over Q1
                if nq1:
                    best_a = max(nq1, key=lambda x: nq1[x])
                    target = r + self.mdp.gamma * self.Q2.get(ns, {}).get(best_a, 0.0)
                else:
                    target = r
            self.Q[s][a] += self.alpha * (target - self.Q[s][a])
        else:
            if done:
                target = r
            else:
                nq2 = self.Q2.get(ns, {})
                if nq2:
                    best_a = max(nq2, key=lambda x: nq2[x])
                    target = r + self.mdp.gamma * self.Q.get(ns, {}).get(best_a, 0.0)
                else:
                    target = r
            self.Q2[s][a] += self.alpha * (target - self.Q2[s][a])

    def value_function(self) -> Dict[Any, float]:
        return {s: max((self.Q.get(s, {}).get(a, 0.0) + self.Q2.get(s, {}).get(a, 0.0))
                       for a in self.mdp.available_actions(s)) if self.mdp.available_actions(s) else 0.0
                for s in self.mdp.states}

    def greedy_policy(self) -> Policy:
        # use averaged Q for policy extraction
        V = self.value_function()
        # build a combined Q for greedy extraction
        combined = {}
        for s in self.mdp.states:
            combined[s] = {a: self.Q.get(s, {}).get(a, 0.0) + self.Q2.get(s, {}).get(a, 0.0)
                           for a in self.mdp.available_actions(s)}
        pi = Policy(self.mdp)
        for s in self.mdp.states:
            acts = self.mdp.available_actions(s)
            if not acts:
                pi[s] = None
                continue
            pi[s] = max(combined.get(s, {}), key=combined.get(s, {}).get) if combined.get(s) else None
        return pi


def mdp_states(mdp: MDP):
    return mdp.states


# ====================================================================== #
# Monte-Carlo control
# ====================================================================== #
class MonteCarloLearner(_BaseLearner):
    """Monte-Carlo control with epsilon-soft policies.

    ``first_visit=True`` updates only the first occurrence of each (s,a)
    in an episode; ``first_visit=False`` updates every occurrence.
    Uses incremental mean update: Q <- Q + (1/N) * (G - Q).
    """

    def __init__(self, *args, first_visit: bool = True, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.first_visit = first_visit
        self.returns_sum: Dict[Tuple[Any, Any], float] = {}
        self.returns_count: Dict[Tuple[Any, Any], int] = {}

    def run_episode(self, max_steps: int = 10000) -> Episode:
        state = self.mdp.start_state
        episode: Episode = []
        total_reward = 0.0
        for _ in range(max_steps):
            if self.mdp.is_terminal(state):
                break
            self._ensure_q(state)
            action = self._select_action(state)
            if action is None:
                break
            next_state, reward = self.mdp.step(state, action, rng=self.rng)
            done = self.mdp.is_terminal(next_state)
            episode.append((state, action, reward, next_state, done))
            total_reward += reward
            state = next_state
        # MC update: compute returns G from the end
        G = 0.0
        visited: set = set()
        for (s, a, r, ns, done) in reversed(episode):
            G = r + self.mdp.gamma * G
            sa = (s, a)
            if self.first_visit and sa in visited:
                continue
            visited.add(sa)
            self.returns_sum[sa] = self.returns_sum.get(sa, 0.0) + G
            self.returns_count[sa] = self.returns_count.get(sa, 0) + 1
            self.Q[s][a] = self.returns_sum[sa] / self.returns_count[sa]
        self.episode_count += 1
        self.step_count += len(episode)
        self.episode_rewards.append(total_reward)
        self.episode_lengths.append(len(episode))
        return episode

    def _update(self, s: Any, a: Any, r: float, ns: Any, done: bool) -> None:
        pass  # MC updates in run_episode


__all__ = [
    "QLearner",
    "SARSALearner",
    "ExpectedSARSALearner",
    "DoubleQLearner",
    "MonteCarloLearner",
]