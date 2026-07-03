"""rl-solver: a Markov Decision Process & Reinforcement Learning toolkit.

Provides model-based dynamic programming (value/policy iteration, linear
algebra policy evaluation, modified policy iteration) and model-free
tabular RL (Q-learning, SARSA, Expected SARSA, Double Q-learning,
Monte-Carlo control) for discrete MDPs.
"""
from .mdp import MDP, GridWorld
from .planners import (
    Policy,
    policy_evaluation_linear,
    policy_evaluation_iterative,
    value_iteration,
    policy_iteration,
    modified_policy_iteration,
    greedy_policy,
    q_values,
)
from .learners import (
    QLearner,
    SARSALearner,
    ExpectedSARSALearner,
    DoubleQLearner,
    MonteCarloLearner,
)
from .environments import (
    make_russell_norvig_grid,
    make_cliff_walking,
    make_frozen_lake,
    make_chain,
    make_taxi,
    PRESETS,
)
from .analysis import simulate_policy, evaluate_policy, compare_planners, compare_learners

__version__ = "1.0.0"

__all__ = [
    "MDP",
    "GridWorld",
    "Policy",
    "policy_evaluation_linear",
    "policy_evaluation_iterative",
    "value_iteration",
    "policy_iteration",
    "modified_policy_iteration",
    "greedy_policy",
    "q_values",
    "QLearner",
    "SARSALearner",
    "ExpectedSARSALearner",
    "DoubleQLearner",
    "MonteCarloLearner",
    "make_russell_norvig_grid",
    "make_cliff_walking",
    "make_frozen_lake",
    "make_chain",
    "make_taxi",
    "PRESETS",
    "simulate_policy",
    "evaluate_policy",
    "compare_planners",
    "compare_learners",
]