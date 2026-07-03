"""Analysis utilities: policy simulation, evaluation, and comparison tools."""
from __future__ import annotations

import random
import time
from typing import Any, Dict, List, Optional, Tuple

from .mdp import MDP
from .planners import Policy, value_iteration, policy_iteration, modified_policy_iteration


def simulate_policy(
    mdp: MDP,
    policy: Policy,
    n_episodes: int = 1000,
    max_steps: int = 1000,
    seed: Optional[int] = None,
) -> Dict[str, Any]:
    """Simulate a deterministic policy and return statistics.

    Returns dict with mean_return, std_return, min, max, mean_length,
    success_rate (fraction of episodes that reached a terminal state).
    """
    rng = random.Random(seed)
    returns: List[float] = []
    lengths: List[int] = []
    successes = 0
    for _ in range(n_episodes):
        state = mdp.start_state
        total = 0.0
        steps = 0
        for steps in range(max_steps):
            if mdp.is_terminal(state):
                successes += 1
                break
            a = policy[state]
            if a is None:
                break
            state, r = mdp.step(state, a, rng=rng)
            total += r
        else:
            # did not terminate within max_steps
            pass
        if mdp.is_terminal(state):
            successes += 1 if steps < max_steps else 0
        returns.append(total)
        lengths.append(steps)
    n = len(returns)
    mean = sum(returns) / n if n else 0.0
    var = sum((x - mean) ** 2 for x in returns) / n if n else 0.0
    return {
        "n_episodes": n,
        "mean_return": mean,
        "std_return": var ** 0.5,
        "min_return": min(returns) if returns else 0.0,
        "max_return": max(returns) if returns else 0.0,
        "mean_length": sum(lengths) / n if n else 0.0,
        "success_rate": successes / n if n else 0.0,
    }


def evaluate_policy(mdp: MDP, policy: Policy, n_episodes: int = 1000,
                    seed: Optional[int] = None) -> float:
    """Convenience: return only the mean return."""
    return simulate_policy(mdp, policy, n_episodes=n_episodes, seed=seed)["mean_return"]


def compare_planners(
    mdp: MDP,
    planners: Optional[List[str]] = None,
    theta: float = 1e-8,
    sim_episodes: int = 500,
    seed: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Run several DP planners on the same MDP and compare results.

    Each result dict contains: name, iterations, time, sim_mean_return,
    sim_success_rate, and the solved V (optional).
    """
    if planners is None:
        planners = ["value_iteration", "policy_iteration", "modified_policy_iteration"]
    results: List[Dict[str, Any]] = []
    for name in planners:
        t0 = time.perf_counter()
        if name == "value_iteration":
            V, pi, info = value_iteration(mdp, theta=theta)
        elif name == "policy_iteration":
            V, pi, info = policy_iteration(mdp, theta=theta)
        elif name == "modified_policy_iteration":
            V, pi, info = modified_policy_iteration(mdp, theta=theta)
        else:
            continue
        sim = simulate_policy(mdp, pi, n_episodes=sim_episodes, seed=seed)
        results.append({
            "name": name,
            "iterations": info["iterations"],
            "time": info["time"],
            "sim_mean_return": sim["mean_return"],
            "sim_success_rate": sim["success_rate"],
            "V": V,
            "policy": pi,
        })
    return results


def compare_learners(
    mdp: MDP,
    learners: List,
    n_episodes: int = 5000,
    max_steps: int = 1000,
    sim_episodes: int = 500,
    seed: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Train multiple learners and compare their resulting policies.

    Each learner should be an instance of a class with ``train`` and
    ``greedy_policy`` methods (e.g. QLearner).
    """
    results: List[Dict[str, Any]] = []
    for learner in learners:
        stats = learner.train(n_episodes=n_episodes, max_steps=max_steps)
        pi = learner.greedy_policy()
        sim = simulate_policy(mdp, pi, n_episodes=sim_episodes, seed=seed)
        results.append({
            "name": type(learner).__name__,
            "train_stats": stats,
            "sim_mean_return": sim["mean_return"],
            "sim_success_rate": sim["success_rate"],
            "policy": pi,
        })
    return results


__all__ = ["simulate_policy", "evaluate_policy", "compare_planners", "compare_learners"]