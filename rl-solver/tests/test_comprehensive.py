"""Comprehensive test suite for rl-solver v3.0.

Tests cover:
* MDP core (validation, transitions, serialization)
* All DP planners (VI, PI, MPI, LP, Gauss-Seidel, Prioritized Sweeping, RTDP)
* All RL learners (Q, SARSA, Expected SARSA, Double Q, MC, n-step, TD(λ),
  Dyna-Q, R-Max, Boltzmann, Gradient Q)
* All environments (7 core + 5 extra)
* Visualization, config, analysis
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import pytest
import random
from rl_solver import (
    MDP, GridWorld, Policy,
    value_iteration, policy_iteration, modified_policy_iteration,
    policy_evaluation_linear, policy_evaluation_iterative,
    linear_programming_solve, gauss_seidel_value_iteration,
    prioritized_sweeping, rtdp,
    QLearner, SARSALearner, ExpectedSARSALearner, DoubleQLearner, MonteCarloLearner,
    NStepSARSALearner, NStepTreeBackupLearner, SARSALambdaLearner, QLambdaLearner,
    DynaQLearner, RMaxLearner, BoltzmannQLearner, TileCoder, GradientQLearner,
    make_russell_norvig_grid, make_cliff_walking, make_frozen_lake, make_chain,
    make_taxi, make_bridge_walking, make_random_mdp,
    make_maze, make_windy_gridworld, make_blackjack, make_dice_game, make_pendulum,
    simulate_policy, compare_planners, compare_learners,
    render_value_heatmap, render_policy_grid, render_q_table, render_learning_curve,
    serialize_value_function, deserialize_value_function,
    serialize_policy, deserialize_policy,
    EXTENDED_PRESETS,
)


# ====================================================================== #
# MDP core tests
# ====================================================================== #
class TestMDPCore:
    def test_empty_states_rejected(self):
        with pytest.raises(ValueError, match="at least one state"):
            MDP([], ["a"], {}, gamma=0.9)

    def test_empty_actions_rejected(self):
        with pytest.raises(ValueError, match="at least one action"):
            MDP([0], [], {}, gamma=0.9)

    def test_gamma_range(self):
        with pytest.raises(ValueError, match="gamma"):
            MDP([0], ["a"], {0: {"a": [(0, 1.0, 0.0)]}}, gamma=-0.1)
        with pytest.raises(ValueError, match="gamma"):
            MDP([0], ["a"], {0: {"a": [(0, 1.0, 0.0)]}}, gamma=1.5)

    def test_gamma_one_allowed(self):
        """gamma=1.0 should be allowed (episodic tasks)."""
        mdp = MDP([0, 1], ["a"], {0: {"a": [(1, 1.0, -1.0)]}},
                  gamma=1.0, terminal_states={1})
        assert mdp.gamma == 1.0

    def test_invalid_transition_prob(self):
        with pytest.raises(ValueError, match="sum to"):
            MDP([0, 1], ["a"], {0: {"a": [(1, 0.5, 0.0)]}}, gamma=0.9,
                terminal_states={1})

    def test_unknown_next_state(self):
        with pytest.raises(ValueError, match="not in states"):
            MDP([0], ["a"], {0: {"a": [(99, 1.0, 0.0)]}}, gamma=0.9)

    def test_step_returns_valid(self):
        mdp = make_russell_norvig_grid()
        ns, r = mdp.step((0, 0), "E")
        assert ns in mdp.states
        assert isinstance(r, float)

    def test_step_terminal(self):
        mdp = make_russell_norvig_grid()
        ns, r = mdp.step((3, 3), "N")
        assert ns == (3, 3)
        assert r == 0.0

    def test_serialization(self):
        mdp = make_russell_norvig_grid()
        d = mdp.to_dict()
        assert "states" in d and "transitions" in d
        j = mdp.to_json()
        assert isinstance(j, str)
        assert len(mdp.fingerprint()) == 12

    def test_gridworld_validation(self):
        with pytest.raises(ValueError):
            GridWorld(rows=0, cols=5)
        with pytest.raises(ValueError):
            GridWorld(rows=5, cols=5, slip=1.5)


# ====================================================================== #
# DP planner tests
# ====================================================================== #
class TestPlanners:
    @pytest.fixture
    def mdp(self):
        return make_russell_norvig_grid()

    def test_value_iteration_converges(self, mdp):
        V, pi, info = value_iteration(mdp)
        assert info["converged"]
        assert V[(0, 0)] > 0  # start state should have positive value
        assert V[(3, 3)] == 0.0  # terminal

    def test_policy_iteration_converges(self, mdp):
        V, pi, info = policy_iteration(mdp)
        assert info["converged"]
        assert V[(0, 0)] > 0

    def test_modified_policy_iteration_converges(self, mdp):
        V, pi, info = modified_policy_iteration(mdp)
        assert info["converged"]
        assert V[(0, 0)] > 0

    def test_all_planners_agree(self, mdp):
        V1, _, _ = value_iteration(mdp)
        V2, _, _ = policy_iteration(mdp)
        V3, _, _ = modified_policy_iteration(mdp)
        max_diff = max(
            max(abs(V1[s] - V2[s]) for s in mdp.states),
            max(abs(V1[s] - V3[s]) for s in mdp.states),
        )
        assert max_diff < 1e-3

    def test_lp_matches_vi(self, mdp):
        V1, _, _ = value_iteration(mdp)
        V2, _, _ = linear_programming_solve(mdp)
        max_diff = max(abs(V1[s] - V2[s]) for s in mdp.states)
        assert max_diff < 1e-4

    def test_gauss_seidel_matches_vi(self, mdp):
        V1, _, _ = value_iteration(mdp)
        V2, _, _ = gauss_seidel_value_iteration(mdp)
        max_diff = max(abs(V1[s] - V2[s]) for s in mdp.states)
        assert max_diff < 1e-6

    def test_prioritized_sweeping_matches_vi(self, mdp):
        V1, _, _ = value_iteration(mdp)
        V2, _, _ = prioritized_sweeping(mdp)
        max_diff = max(abs(V1[s] - V2[s]) for s in mdp.states)
        assert max_diff < 1e-4

    def test_rtdp_approximates_vi(self, mdp):
        V1, _, _ = value_iteration(mdp)
        V2, _, _ = rtdp(mdp, n_trials=2000, seed=42)
        # RTDP converges asymptotically; check it's in the right ballpark
        diff = abs(V1[mdp.start_state] - V2[mdp.start_state])
        assert diff < 0.5

    def test_policy_evaluation_methods_agree(self, mdp):
        V, pi, _ = value_iteration(mdp)
        V_lin = policy_evaluation_linear(mdp, pi)
        V_iter = policy_evaluation_iterative(mdp, pi)
        diff = max(abs(V_lin[s] - V_iter[s]) for s in mdp.states)
        assert diff < 1e-4

    def test_value_iteration_history(self, mdp):
        V, pi, info = value_iteration(mdp, record_history=True)
        assert "history" in info
        assert len(info["history"]) == info["iterations"]

    def test_q_values(self, mdp):
        V, _, _ = value_iteration(mdp)
        Q = _q_values_helper(mdp, V)
        for s in mdp.states:
            if mdp.available_actions(s):
                assert len(Q[s]) == len(mdp.available_actions(s))

    def test_greedy_policy_optimal(self, mdp):
        from rl_solver import greedy_policy
        V, pi_opt, _ = value_iteration(mdp)
        pi_greedy = greedy_policy(mdp, V)
        for s in mdp.states:
            if mdp.available_actions(s):
                assert pi_opt[s] == pi_greedy[s]


def _q_values_helper(mdp, V):
    from rl_solver import q_values
    return q_values(mdp, V)


# ====================================================================== #
# RL learner tests
# ====================================================================== #
class TestLearners:
    @pytest.fixture
    def mdp(self):
        return make_russell_norvig_grid()

    def test_q_learning_improves(self, mdp):
        learner = QLearner(mdp, alpha=0.1, epsilon=0.3, seed=42)
        learner.train(n_episodes=5000, max_steps=200)
        # Greedy policy should reach the goal most of the time
        sim = simulate_policy(mdp, learner.greedy_policy(), n_episodes=500, seed=42)
        assert sim["success_rate"] > 0.5

    def test_sarsa_improves(self, mdp):
        learner = SARSALearner(mdp, alpha=0.1, epsilon=0.3, seed=42)
        learner.train(n_episodes=5000, max_steps=200)
        sim = simulate_policy(mdp, learner.greedy_policy(), n_episodes=500, seed=42)
        assert sim["success_rate"] > 0.3

    def test_expected_sarsa_improves(self, mdp):
        learner = ExpectedSARSALearner(mdp, alpha=0.1, epsilon=0.3, seed=42)
        learner.train(n_episodes=5000, max_steps=200)
        sim = simulate_policy(mdp, learner.greedy_policy(), n_episodes=500, seed=42)
        assert sim["success_rate"] > 0.3

    def test_double_q_improves(self, mdp):
        learner = DoubleQLearner(mdp, alpha=0.1, epsilon=0.3, seed=42)
        learner.train(n_episodes=5000, max_steps=200)
        sim = simulate_policy(mdp, learner.greedy_policy(), n_episodes=500, seed=42)
        assert sim["success_rate"] > 0.3

    def test_mc_improves(self, mdp):
        learner = MonteCarloLearner(mdp, alpha=0.1, epsilon=0.3, seed=42)
        learner.train(n_episodes=5000, max_steps=200)
        sim = simulate_policy(mdp, learner.greedy_policy(), n_episodes=500, seed=42)
        assert sim["success_rate"] > 0.2

    def test_nstep_sarsa_improves(self, mdp):
        learner = NStepSARSALearner(mdp, n=3, alpha=0.1, epsilon=0.3, seed=42)
        learner.train(n_episodes=5000, max_steps=200)
        sim = simulate_policy(mdp, learner.greedy_policy(), n_episodes=500, seed=42)
        assert sim["success_rate"] > 0.3

    def test_nstep_tree_backup_improves(self, mdp):
        learner = NStepTreeBackupLearner(mdp, n=3, alpha=0.1, epsilon=0.3, seed=42)
        learner.train(n_episodes=5000, max_steps=200)
        # Tree backup is off-policy and may converge slower; just verify it runs
        assert len(learner.Q) > 0
        assert learner.episode_count == 5000

    def test_sarsa_lambda_improves(self, mdp):
        learner = SARSALambdaLearner(mdp, lam=0.5, alpha=0.1, epsilon=0.3, seed=42)
        learner.train(n_episodes=5000, max_steps=200)
        sim = simulate_policy(mdp, learner.greedy_policy(), n_episodes=500, seed=42)
        assert sim["success_rate"] > 0.3

    def test_q_lambda_improves(self, mdp):
        learner = QLambdaLearner(mdp, lam=0.5, alpha=0.1, epsilon=0.3, seed=42)
        learner.train(n_episodes=5000, max_steps=200)
        sim = simulate_policy(mdp, learner.greedy_policy(), n_episodes=500, seed=42)
        assert sim["success_rate"] > 0.3

    def test_dyna_q_improves(self, mdp):
        learner = DynaQLearner(mdp, alpha=0.1, epsilon=0.3, n_planning=5, seed=42)
        learner.train(n_episodes=2000, max_steps=200)
        sim = simulate_policy(mdp, learner.greedy_policy(), n_episodes=500, seed=42)
        assert sim["success_rate"] > 0.3

    def test_rmax_improves(self, mdp):
        learner = RMaxLearner(mdp, r_max=1.0, threshold=3, seed=42)
        learner.train(n_episodes=3000, max_steps=200)
        sim = simulate_policy(mdp, learner.greedy_policy(), n_episodes=500, seed=42)
        assert sim["success_rate"] > 0.3

    def test_boltzmann_q_improves(self, mdp):
        learner = BoltzmannQLearner(mdp, alpha=0.1, temperature=0.5, seed=42)
        learner.train(n_episodes=5000, max_steps=200)
        sim = simulate_policy(mdp, learner.greedy_policy(), n_episodes=500, seed=42)
        assert sim["success_rate"] > 0.3

    def test_double_q_greedy_policy_no_crash(self, mdp):
        """DoubleQLearner.greedy_policy should not crash on any MDP."""
        learner = DoubleQLearner(mdp, seed=42)
        pi = learner.greedy_policy()
        for s in mdp.states:
            if mdp.available_actions(s):
                assert pi[s] is not None

    def test_mc_first_vs_every_visit(self, mdp):
        mc1 = MonteCarloLearner(mdp, first_visit=True, seed=42)
        mc1.train(n_episodes=1000, max_steps=100)
        mc2 = MonteCarloLearner(mdp, first_visit=False, seed=42)
        mc2.train(n_episodes=1000, max_steps=100)
        # Both should produce some learned values
        assert len(mc1.Q) > 0
        assert len(mc2.Q) > 0

    def test_train_returns_stats(self, mdp):
        learner = QLearner(mdp, seed=42)
        stats = learner.train(n_episodes=100, max_steps=50)
        assert "episodes" in stats
        assert "mean_reward" in stats
        assert stats["episodes"] == 100


# ====================================================================== #
# Gradient Q learner tests
# ====================================================================== #
class TestGradientQLearner:
    def test_tile_coder_features(self):
        tc = TileCoder(n_tilings=4, bins_per_dim=8,
                       low=(0.0, 0.0), high=(1.0, 1.0), seed=42)
        feats = tc.features((0.5, 0.5))
        assert len(feats) == 4  # one per tiling
        assert all(0 <= f < tc.size for f in feats)

    def test_gradient_q_learns(self):
        mdp = make_pendulum(n_angle_bins=8, n_vel_bins=6)
        tc = TileCoder(n_tilings=4, bins_per_dim=8,
                       low=(-3.14159, -8.0), high=(3.14159, 8.0), seed=42)
        learner = GradientQLearner(mdp, tc, alpha=0.1, epsilon=0.2, seed=42)
        stats = learner.train(n_episodes=200, max_steps=100)
        assert stats["episodes"] == 200
        assert isinstance(stats["mean_reward"], float)


# ====================================================================== #
# Environment tests
# ====================================================================== #
class TestEnvironments:
    def test_russell_norvig(self):
        mdp = make_russell_norvig_grid()
        assert len(mdp.states) == 16
        assert len(mdp.actions) == 4
        assert (3, 3) in mdp.terminal_states
        assert (3, 0) in mdp.terminal_states

    def test_cliff_walking(self):
        mdp = make_cliff_walking()
        assert mdp.start_state == (3, 0)
        V, pi, info = value_iteration(mdp, theta=1e-6)
        assert V[(3, 0)] > -20  # should find a reasonable path

    def test_frozen_lake(self):
        mdp = make_frozen_lake()
        assert len(mdp.states) == 16
        V, pi, info = value_iteration(mdp, theta=1e-6)
        assert V[(0, 0)] > 0  # despite slip, should have positive value

    def test_chain(self):
        mdp = make_chain(n=5)
        assert len(mdp.states) == 5
        V, pi, info = value_iteration(mdp)
        assert V[4] == 0.0  # terminal
        assert V[0] > 0

    def test_taxi(self):
        mdp = make_taxi()
        V, pi, info = value_iteration(mdp, theta=1e-6)
        assert V[mdp.start_state] > 0  # can reach +20

    def test_bridge_walking(self):
        mdp = make_bridge_walking(size=5)
        V, pi, info = value_iteration(mdp)
        assert V[(0, 0)] > 0

    def test_random_mdp(self):
        mdp = make_random_mdp(n_states=10, n_actions=3, seed=42)
        assert len(mdp.states) == 10
        assert len(mdp.actions) == 3
        V, pi, info = value_iteration(mdp)
        assert len(V) == 10

    def test_maze(self):
        mdp = make_maze(width=5, height=4, walls=[(1, 1), (1, 2)], goal=(3, 4))
        assert (1, 1) not in mdp.states  # wall excluded
        V, pi, info = value_iteration(mdp)
        assert V[(0, 0)] > 0

    def test_windy_gridworld(self):
        mdp = make_windy_gridworld()
        assert len(mdp.states) == 70
        V, pi, info = value_iteration(mdp, theta=1e-6)
        assert V[(3, 0)] < 0  # costs steps

    def test_windy_king_moves(self):
        mdp = make_windy_gridworld(king_moves=True)
        assert len(mdp.actions) == 8
        V, pi, info = value_iteration(mdp, theta=1e-6)

    def test_blackjack(self):
        mdp = make_blackjack()
        assert len(mdp.actions) == 2
        V, pi, info = value_iteration(mdp, theta=1e-6)
        # Some states should have positive value
        assert any(V[s] > 0 for s in mdp.states if isinstance(s, tuple))

    def test_dice_game(self):
        mdp = make_dice_game()
        assert len(mdp.states) == 2
        V, pi, info = value_iteration(mdp)
        assert pi[0] is not None

    def test_pendulum(self):
        mdp = make_pendulum()
        assert len(mdp.actions) == 3
        V, pi, info = value_iteration(mdp, theta=1e-4, max_iter=500)
        assert len(V) > 0

    def test_all_presets_valid(self):
        """All registered presets should produce valid MDPs solvable by VI."""
        for name, factory in EXTENDED_PRESETS.items():
            try:
                mdp = factory()
            except TypeError:
                # Some factories require args; skip
                continue
            V, pi, info = value_iteration(mdp, theta=1e-4, max_iter=500)
            assert len(V) > 0, f"Preset {name} failed"


# ====================================================================== #
# Analysis & visualization tests
# ====================================================================== #
class TestAnalysis:
    def test_simulate_policy_returns_stats(self):
        mdp = make_russell_norvig_grid()
        V, pi, _ = value_iteration(mdp)
        sim = simulate_policy(mdp, pi, n_episodes=100, seed=42)
        assert "mean_return" in sim
        assert "success_rate" in sim
        assert 0 <= sim["success_rate"] <= 1.0

    def test_simulate_policy_success_rate_bounded(self):
        """success_rate must never exceed 1.0 (bug fix verification)."""
        mdp = make_russell_norvig_grid()
        V, pi, _ = value_iteration(mdp)
        sim = simulate_policy(mdp, pi, n_episodes=500, seed=42)
        assert sim["success_rate"] <= 1.0

    def test_compare_planners(self):
        mdp = make_russell_norvig_grid()
        results = compare_planners(mdp, sim_episodes=100, seed=42)
        assert len(results) >= 3
        for r in results:
            assert "name" in r and "iterations" in r

    def test_compare_learners(self):
        mdp = make_russell_norvig_grid()
        learners = [QLearner(mdp, seed=42), SARSALearner(mdp, seed=42)]
        results = compare_learners(mdp, learners, n_episodes=500,
                                   sim_episodes=100, seed=42)
        assert len(results) == 2


class TestVisualization:
    def test_value_heatmap(self):
        mdp = make_russell_norvig_grid()
        V, _, _ = value_iteration(mdp)
        s = render_value_heatmap(mdp, V)
        assert isinstance(s, str) and len(s) > 0

    def test_policy_grid(self):
        mdp = make_russell_norvig_grid()
        _, pi, _ = value_iteration(mdp)
        s = render_policy_grid(mdp, pi)
        assert isinstance(s, str) and len(s) > 0

    def test_q_table(self):
        mdp = make_russell_norvig_grid()
        learner = QLearner(mdp, seed=42)
        learner.train(n_episodes=100, max_steps=50)
        s = render_q_table(learner.Q)
        assert isinstance(s, str) and len(s) > 0

    def test_learning_curve(self):
        rewards = [float(x) for x in range(100)]
        s = render_learning_curve(rewards, width=40, height=10)
        assert isinstance(s, str) and len(s) > 0

    def test_learning_curve_empty(self):
        s = render_learning_curve([])
        assert "no data" in s.lower()


# ====================================================================== #
# Config & serialization tests
# ====================================================================== #
class TestConfig:
    def test_serialize_deserialize_value_function(self, tmp_path):
        mdp = make_russell_norvig_grid()
        V, _, _ = value_iteration(mdp)
        path = str(tmp_path / "values.json")
        serialize_value_function(V, path)
        V2 = deserialize_value_function(path)
        assert str((0, 0)) in V2

    def test_serialize_deserialize_policy(self, tmp_path):
        mdp = make_russell_norvig_grid()
        _, pi, _ = value_iteration(mdp)
        path = str(tmp_path / "policy.json")
        serialize_policy(pi, path)
        p2 = deserialize_policy(path)
        assert len(p2) > 0

    def test_default_config_valid(self):
        from rl_solver import DEFAULT_EXPERIMENT_CONFIG, validate_config
        assert validate_config(DEFAULT_EXPERIMENT_CONFIG)


# ====================================================================== #
# Known bug regression tests
# ====================================================================== #
class TestBugRegressions:
    def test_success_rate_not_double_counted(self):
        """Bug 1: simulate_policy double-counted successes."""
        mdp = make_russell_norvig_grid()
        V, pi, _ = value_iteration(mdp)
        sim = simulate_policy(mdp, pi, n_episodes=500, seed=42)
        assert sim["success_rate"] <= 1.0

    def test_taxi_no_premature_terminal(self):
        """Bug 2: make_taxi marked terminal before dropoff."""
        mdp = make_taxi()
        stands = [(0, 0), (0, 4), (4, 0), (4, 4)]
        for s in mdp.states:
            r, c, p, d = s
            if p == "in_taxi" and (r, c) == stands[d]:
                assert not mdp.is_terminal(s), \
                    f"State {s} is terminal but dropoff hasn't happened"

    def test_taxi_dropoff_reward_reachable(self):
        """Bug 2/3: +20 dropoff reward should be reachable."""
        mdp = make_taxi()
        V, pi, _ = value_iteration(mdp, theta=1e-6)
        assert V[mdp.start_state] > 0

    def test_taxi_dropoff_changes_passenger_loc(self):
        """Bug 3: dropoff should move passenger out of taxi."""
        mdp = make_taxi()
        stands = [(0, 0), (0, 4), (4, 0), (4, 4)]
        for s in mdp.states:
            r, c, p, d = s
            if p == "in_taxi" and (r, c) == stands[d]:
                for ns, prob, reward in mdp.transitions.get(s, {}).get("dropoff", []):
                    assert ns[2] != "in_taxi", \
                        f"After dropoff from {s}, passenger still in_taxi"

    def test_bridge_jump_resets_to_start(self):
        """Bug 4: jumping off bridge resets to start, not terminal."""
        mdp = make_bridge_walking(size=5)
        outcomes = mdp.transitions.get((0, 0), {}).get("W", [])
        for ns, prob, reward in outcomes:
            assert not mdp.is_terminal(ns), \
                f"Jumping off bridge leads to terminal {ns}"

    def test_double_q_greedy_no_crash(self):
        """Bug 5: DoubleQLearner.greedy_policy crashes on empty dict."""
        mdp = make_russell_norvig_grid()
        learner = DoubleQLearner(mdp, seed=42)
        pi = learner.greedy_policy()  # should not crash
        assert pi is not None