"""rl-solver: a Markov Decision Process & Reinforcement Learning toolkit.

Provides model-based dynamic programming (value/policy iteration, linear
algebra policy evaluation, modified policy iteration) and model-free
tabular RL (Q-learning, SARSA, Expected SARSA, Double Q-learning,
Monte-Carlo control, n-step methods, TD(λ) with eligibility traces)
for discrete MDPs.
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
from .nstep import (
    NStepSARSALearner,
    NStepTreeBackupLearner,
    SARSALambdaLearner,
    QLambdaLearner,
)
from .environments import (
    make_russell_norvig_grid,
    make_cliff_walking,
    make_frozen_lake,
    make_chain,
    make_taxi,
    make_bridge_walking,
    make_random_mdp,
    PRESETS,
)
from .analysis import simulate_policy, evaluate_policy, compare_planners, compare_learners
from .visualization import (
    render_value_heatmap,
    render_policy_grid,
    render_q_table,
    render_learning_curve,
)
from .config import (
    load_config,
    save_config,
    validate_config,
    DEFAULT_EXPERIMENT_CONFIG,
    serialize_value_function,
    deserialize_value_function,
    serialize_policy,
    deserialize_policy,
)
from .logging_utils import get_logger, set_log_level

__version__ = "2.0.0"

__all__ = [
    # core
    "MDP", "GridWorld", "Policy",
    # planners
    "policy_evaluation_linear", "policy_evaluation_iterative",
    "value_iteration", "policy_iteration", "modified_policy_iteration",
    "greedy_policy", "q_values",
    # learners
    "QLearner", "SARSALearner", "ExpectedSARSALearner", "DoubleQLearner",
    "MonteCarloLearner",
    # n-step / TD(λ)
    "NStepSARSALearner", "NStepTreeBackupLearner",
    "SARSALambdaLearner", "QLambdaLearner",
    # environments
    "make_russell_norvig_grid", "make_cliff_walking", "make_frozen_lake",
    "make_chain", "make_taxi", "make_bridge_walking", "make_random_mdp",
    "PRESETS",
    # analysis
    "simulate_policy", "evaluate_policy", "compare_planners", "compare_learners",
    # visualization
    "render_value_heatmap", "render_policy_grid", "render_q_table",
    "render_learning_curve",
    # config
    "load_config", "save_config", "validate_config", "DEFAULT_EXPERIMENT_CONFIG",
    "serialize_value_function", "deserialize_value_function",
    "serialize_policy", "deserialize_policy",
    # logging
    "get_logger", "set_log_level",
]