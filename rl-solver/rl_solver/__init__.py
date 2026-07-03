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
from .advanced_planners import (
    linear_programming_solve,
    gauss_seidel_value_iteration,
    prioritized_sweeping,
    rtdp,
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
from .advanced_learners import (
    DynaQLearner,
    RMaxLearner,
    BoltzmannQLearner,
    TileCoder,
    GradientQLearner,
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
from .extra_environments import (
    make_maze,
    make_windy_gridworld,
    make_blackjack,
    make_dice_game,
    make_pendulum,
    EXTENDED_PRESETS,
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

__version__ = "3.0.0"

__all__ = [
    # core
    "MDP", "GridWorld", "Policy",
    # planners
    "policy_evaluation_linear", "policy_evaluation_iterative",
    "value_iteration", "policy_iteration", "modified_policy_iteration",
    "greedy_policy", "q_values",
    # advanced planners
    "linear_programming_solve", "gauss_seidel_value_iteration",
    "prioritized_sweeping", "rtdp",
    # learners
    "QLearner", "SARSALearner", "ExpectedSARSALearner", "DoubleQLearner",
    "MonteCarloLearner",
    # n-step / TD(λ)
    "NStepSARSALearner", "NStepTreeBackupLearner",
    "SARSALambdaLearner", "QLambdaLearner",
    # advanced learners
    "DynaQLearner", "RMaxLearner", "BoltzmannQLearner",
    "TileCoder", "GradientQLearner",
    # environments
    "make_russell_norvig_grid", "make_cliff_walking", "make_frozen_lake",
    "make_chain", "make_taxi", "make_bridge_walking", "make_random_mdp",
    "PRESETS",
    # extra environments
    "make_maze", "make_windy_gridworld", "make_blackjack",
    "make_dice_game", "make_pendulum", "EXTENDED_PRESETS",
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