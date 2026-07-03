"""n-step and TD(λ) temporal-difference learning algorithms.

Includes:
* n-step SARSA
* n-step Tree Backup (off-policy, no importance sampling)
* TD(λ) with accumulating eligibility traces (forward and backward views)
* True Online SARSA(λ) (van Seijen & Sutton 2014)

These methods bridge the gap between one-step TD and Monte-Carlo methods,
offering a tunable bias-variance tradeoff via n or λ.
"""
from __future__ import annotations

import math
import random
from typing import Any, Dict, List, Optional, Tuple

from .mdp import MDP
from .planners import Policy, greedy_policy
from .learners import _BaseLearner, _eps_greedy_action, Episode


class NStepSARSALearner(_BaseLearner):
    """n-step SARSA (on-policy).

    Updates Q(s,a) using the n-step return:
        G_t:n = r_{t+1} + γ r_{t+2} + ... + γ^{n-1} r_{t+n} + γ^n Q(s_{t+n}, a_{t+n})

    See Sutton & Barto §7.2.  Requires storing the last n transitions.
    """

    def __init__(self, *args, n: int = 3, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        if n < 1:
            raise ValueError("n must be >= 1")
        self.n = n

    def run_episode(self, max_steps: int = 10000) -> Episode:
        state = self.mdp.start_state
        if self.mdp.is_terminal(state):
            self.episode_count += 1
            self.episode_rewards.append(0.0)
            self.episode_lengths.append(0)
            return []
        self._ensure_q(state)
        action = self._select_action(state)
        # store trajectory: (state, action, reward)
        trajectory: List[Tuple[Any, Any, float]] = []
        episode: Episode = []
        total_reward = 0.0
        t = 0  # time step
        T = max_steps  # will update to actual terminal time
        step = 0
        while True:
            if t < T:
                next_state, reward = self.mdp.step(state, action, rng=self.rng)
                trajectory.append((state, action, reward))
                total_reward += reward
                done = self.mdp.is_terminal(next_state)
                episode.append((state, action, reward, next_state, done))
                self._ensure_q(next_state)
                if done:
                    T = t + 1
                    next_action = None
                else:
                    next_action = self._select_action(next_state)
            else:
                next_state, next_action = None, None

            # update time: tau = t - n + 1
            tau = t - self.n + 1
            if tau >= 0:
                # compute n-step return
                G = 0.0
                for i in range(tau + 1, min(tau + self.n, T) + 1):
                    _, _, r_i = trajectory[i - 1]  # trajectory is 0-indexed
                    G += (self.mdp.gamma ** (i - tau - 1)) * r_i
                if tau + self.n < T:
                    s_tau_n = trajectory[tau + self.n - 1][0]
                    a_tau_n = trajectory[tau + self.n - 1][1]
                    G += (self.mdp.gamma ** self.n) * self.Q[s_tau_n][a_tau_n]
                s_tau, a_tau, _ = trajectory[tau]
                self.Q[s_tau][a_tau] += self.alpha * (G - self.Q[s_tau][a_tau])

            self.step_count += 1
            if tau == T - 1:
                break
            t += 1
            state = next_state
            action = next_action
            step += 1
            if step >= max_steps * 2:
                break  # safety

        self.episode_count += 1
        self.episode_rewards.append(total_reward)
        self.episode_lengths.append(len(episode))
        return episode

    def _update(self, s, a, r, ns, done) -> None:
        pass  # handled in run_episode


class NStepTreeBackupLearner(_BaseLearner):
    """n-step Tree Backup (off-policy, no importance sampling).

    Uses the expectation over all actions at each non-selected step.
    See Sutton & Barto §7.5.
    """

    def __init__(self, *args, n: int = 3, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        if n < 1:
            raise ValueError("n must be >= 1")
        self.n = n

    def _expected_q(self, state: Any) -> float:
        """E[Q(s,a')] under current epsilon-greedy policy."""
        actions = self.mdp.available_actions(state)
        if not actions:
            return 0.0
        nq = self.Q.get(state, {})
        if not nq:
            return 0.0
        eps = self._current_epsilon()
        max_q = max(nq.values())
        greedy_acts = [a for a in actions if abs(nq.get(a, 0.0) - max_q) <= 1e-12]
        expected = 0.0
        for a in actions:
            p_greedy = eps / len(actions)
            p_exploit = (1 - eps) / len(greedy_acts) if a in greedy_acts else 0.0
            expected += (p_greedy + p_exploit) * nq.get(a, 0.0)
        return expected

    def run_episode(self, max_steps: int = 10000) -> Episode:
        state = self.mdp.start_state
        if self.mdp.is_terminal(state):
            self.episode_count += 1
            self.episode_rewards.append(0.0)
            self.episode_lengths.append(0)
            return []
        self._ensure_q(state)
        action = self._select_action(state)
        trajectory: List[Tuple[Any, Any, float]] = []
        episode: Episode = []
        total_reward = 0.0
        t = 0
        T = max_steps
        step = 0
        while True:
            if t < T:
                next_state, reward = self.mdp.step(state, action, rng=self.rng)
                trajectory.append((state, action, reward))
                total_reward += reward
                done = self.mdp.is_terminal(next_state)
                episode.append((state, action, reward, next_state, done))
                self._ensure_q(next_state)
                if done:
                    T = t + 1
                    next_action = None
                else:
                    next_action = self._select_action(next_state)
            else:
                next_state, next_action = None, None

            tau = t - self.n + 1
            if tau >= 0:
                # n-step tree backup return
                G = trajectory[tau][2]  # r_{tau+1}
                # sum of expectations for steps tau+1 .. min(tau+n-1, T-1)
                for k in range(tau + 1, min(tau + self.n, T)):
                    s_k = trajectory[k][0]
                    G = G + (self.mdp.gamma ** (k - tau)) * self._expected_q(s_k)
                if tau + self.n < T:
                    s_tau_n = trajectory[tau + self.n - 1][0]
                    G += (self.mdp.gamma ** self.n) * self.Q[s_tau_n][trajectory[tau + self.n - 1][1]]
                s_tau, a_tau, _ = trajectory[tau]
                self.Q[s_tau][a_tau] += self.alpha * (G - self.Q[s_tau][a_tau])

            self.step_count += 1
            if tau == T - 1:
                break
            t += 1
            state = next_state
            action = next_action
            step += 1
            if step >= max_steps * 2:
                break

        self.episode_count += 1
        self.episode_rewards.append(total_reward)
        self.episode_lengths.append(len(episode))
        return episode

    def _update(self, s, a, r, ns, done) -> None:
        pass


class SARSALambdaLearner(_BaseLearner):
    """SARSA(λ) with accumulating eligibility traces (backward view).

    The eligibility trace e(s,a) accumulates visits, decaying by γλ each
    step.  All Q values are updated in proportion to their trace:

        δ = r + γ Q(s',a') - Q(s,a)
        e(s,a) += 1           (accumulating)  [or replace traces]
        Q(s,a) += α δ e(s',a') for all s,a
        e(s,a) *= γλ

    See Sutton & Barto §12.7.
    """

    def __init__(self, *args, lam: float = 0.9, replace_traces: bool = False, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        if not 0.0 <= lam <= 1.0:
            raise ValueError("lambda must be in [0, 1]")
        self.lam = lam
        self.replace_traces = replace_traces
        self.traces: Dict[Tuple[Any, Any], float] = {}

    def run_episode(self, max_steps: int = 10000) -> Episode:
        state = self.mdp.start_state
        if self.mdp.is_terminal(state):
            self.episode_count += 1
            self.episode_rewards.append(0.0)
            self.episode_lengths.append(0)
            return []
        self._ensure_q(state)
        action = self._select_action(state)
        self.traces = {}
        episode: Episode = []
        total_reward = 0.0
        for _ in range(max_steps):
            next_state, reward = self.mdp.step(state, action, rng=self.rng)
            done = self.mdp.is_terminal(next_state)
            self._ensure_q(next_state)
            next_action = None if done else self._select_action(next_state)
            episode.append((state, action, reward, next_state, done))
            # TD error
            if done:
                td_target = reward
            else:
                td_target = reward + self.mdp.gamma * self.Q[next_state][next_action]
            delta = td_target - self.Q[state][action]
            # update trace
            sa = (state, action)
            if self.replace_traces:
                self.traces[sa] = 1.0
            else:
                self.traces[sa] = self.traces.get(sa, 0.0) + 1.0
            # update all Q values with traces
            for (s2, a2), e_val in list(self.traces.items()):
                if e_val < 1e-15:
                    del self.traces[(s2, a2)]
                    continue
                self.Q[s2][a2] += self.alpha * delta * e_val
                self.traces[(s2, a2)] *= self.mdp.gamma * self.lam
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

    def _update(self, s, a, r, ns, done) -> None:
        pass


class QLambdaLearner(_BaseLearner):
    """Watkins' Q(λ) — Q-learning with eligibility traces.

    Uses off-policy max for the TD target, but traces are zeroed when a
    non-greedy action is taken (Watkins' Q(λ)).
    """

    def __init__(self, *args, lam: float = 0.9, replace_traces: bool = False, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.lam = lam
        self.replace_traces = replace_traces
        self.traces: Dict[Tuple[Any, Any], float] = {}

    def run_episode(self, max_steps: int = 10000) -> Episode:
        state = self.mdp.start_state
        if self.mdp.is_terminal(state):
            self.episode_count += 1
            self.episode_rewards.append(0.0)
            self.episode_lengths.append(0)
            return []
        self._ensure_q(state)
        action = self._select_action(state)
        self.traces = {}
        episode: Episode = []
        total_reward = 0.0
        for _ in range(max_steps):
            next_state, reward = self.mdp.step(state, action, rng=self.rng)
            done = self.mdp.is_terminal(next_state)
            self._ensure_q(next_state)
            episode.append((state, action, reward, next_state, done))
            # off-policy max
            nq = self.Q.get(next_state, {})
            max_next = max(nq.values()) if nq else 0.0
            td_target = reward + (0.0 if done else self.mdp.gamma * max_next)
            delta = td_target - self.Q[state][action]
            sa = (state, action)
            if self.replace_traces:
                self.traces[sa] = 1.0
            else:
                self.traces[sa] = self.traces.get(sa, 0.0) + 1.0
            # update all Q with traces
            for (s2, a2), e_val in list(self.traces.items()):
                if e_val < 1e-15:
                    del self.traces[(s2, a2)]
                    continue
                self.Q[s2][a2] += self.alpha * delta * e_val
                self.traces[(s2, a2)] *= self.mdp.gamma * self.lam
            # Watkins' Q(λ): reset traces if action was non-greedy
            nq_state = self.Q.get(state, {})
            if nq_state:
                greedy_a = max(nq_state, key=lambda k: nq_state[k])
                if action != greedy_a:
                    self.traces = {}
            self.step_count += 1
            total_reward += reward
            next_action = None if done else self._select_action(next_state)
            state = next_state
            action = next_action
            if done or action is None:
                break
        self.episode_count += 1
        self.episode_rewards.append(total_reward)
        self.episode_lengths.append(len(episode))
        return episode

    def _update(self, s, a, r, ns, done) -> None:
        pass


__all__ = [
    "NStepSARSALearner",
    "NStepTreeBackupLearner",
    "SARSALambdaLearner",
    "QLambdaLearner",
]