"""Bug hunt tests for rl-solver — verify bugs exist, then verify fixes."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import pytest
from rl_solver import (
    MDP, GridWorld,
    make_russell_norvig_grid, make_taxi, make_bridge_walking,
    value_iteration, policy_iteration, Policy,
    simulate_policy, QLearner,
    render_learning_curve,
    policy_evaluation_linear,
)


# ---- Bug 1: simulate_policy double-counts successes ----
class TestSuccessRateBug:
    """simulate_policy can count success_rate > 1.0 due to double counting."""

    def test_success_rate_at_most_1(self):
        """success_rate should never exceed 1.0 (100%)."""
        mdp = make_russell_norvig_grid()
        V, pi, _ = value_iteration(mdp)
        sim = simulate_policy(mdp, pi, n_episodes=500, seed=42)
        assert sim["success_rate"] <= 1.0, \
            f"success_rate {sim['success_rate']} > 1.0 — double-counting bug"


# ---- Bug 2: make_taxi marks terminal before dropoff is possible ----
class TestTaxiTerminalBug:
    """States where passenger is in_taxi at destination are terminal, but
    the agent hasn't dropped off yet — the +20 dropoff reward is unreachable."""

    def test_dropoff_reachable(self):
        """The +20 dropoff reward should be reachable in the taxi MDP."""
        mdp = make_taxi()
        # Find a state where passenger is in_taxi at destination stand
        # and verify it's NOT terminal (agent still needs to dropoff)
        stands = [(0, 0), (0, 4), (4, 0), (4, 4)]
        # state = (row, col, passenger_loc, destination)
        # If passenger is in_taxi and at destination stand, should NOT be terminal
        # — agent needs to perform 'dropoff' action first
        for s in mdp.states:
            r, c, p, d = s
            if p == "in_taxi" and (r, c) == stands[d]:
                # This state should NOT be terminal — dropoff hasn't happened
                assert not mdp.is_terminal(s), \
                    f"State {s} is terminal but dropoff hasn't happened — premature terminal bug"

    def test_dropoff_reward_reachable(self):
        """The optimal value should include the +20 dropoff reward."""
        mdp = make_taxi()
        V, pi, _ = value_iteration(mdp, theta=1e-6)
        # The start state should have a positive value (can reach +20)
        assert V[mdp.start_state] > 0, \
            f"V(start)={V[mdp.start_state]} should be positive — dropoff reward unreachable"


# ---- Bug 3: make_taxi dropoff transition uses wrong next_state ----
class TestTaxiDropoffTransitionBug:
    """The dropoff transition uses `st` (self-loop) instead of a proper
    post-dropoff state. After dropoff, the passenger should be at the
    destination stand, not still in the taxi."""

    def test_dropoff_changes_passenger_loc(self):
        """After dropoff, passenger should no longer be in_taxi."""
        mdp = make_taxi()
        stands = [(0, 0), (0, 4), (4, 0), (4, 4)]
        # Find a state where we can dropoff
        for s in mdp.states:
            r, c, p, d = s
            if p == "in_taxi" and (r, c) == stands[d]:
                if "dropoff" in mdp.transitions.get(s, {}):
                    outcomes = mdp.transitions[s]["dropoff"]
                    for ns, prob, reward in outcomes:
                        # After dropoff, passenger should not be "in_taxi"
                        ns_p = ns[2]  # passenger_loc component
                        assert ns_p != "in_taxi", \
                            f"After dropoff from {s}, next state {ns} still has passenger in_taxi"


# ---- Bug 4: bridge_walking docstring says "resets to start" but terminates ----
class TestBridgeDocstringBug:
    """The bridge_walking docstring says jumping 'resets to start' but
    actually the off-bridge states are terminal. This is a doc/reality
    mismatch. We verify the actual behavior matches the docstring after fix."""

    def test_jump_resets_to_start(self):
        """After jumping off, the agent should be back at start (not terminal)."""
        mdp = make_bridge_walking(size=5)
        # off_left and off_right should NOT be terminal — they should
        # transition back to start
        # After fix, off-bridge should send agent back to start (0,0)
        # Check: jumping off from (0,0) with W should go to start, not terminal
        assert (0, 0) in mdp.transitions
        outcomes = mdp.transitions[(0, 0)].get("W", [])
        for ns, prob, reward in outcomes:
            # After fix: should go back to start (0,0), not to a terminal
            assert not mdp.is_terminal(ns), \
                f"Jumping off bridge leads to terminal {ns} — should reset to start"


# ---- Bug 5: render_learning_curve x-axis label off ----
class TestLearningCurveAxis:
    """The x-axis label should show 0 at left and n at right, properly aligned."""

    def test_axis_labels(self):
        """The learning curve should have correct axis labels."""
        rewards = [0.0, 1.0, 2.0, 3.0]
        result = render_learning_curve(rewards, width=10, height=5)
        lines = result.split("\n")
        # last line should have 0 and 4
        assert "0" in lines[-1]
        assert "4" in lines[-1]


# ---- Bug 6: policy_evaluation_linear unused timeout parameter ----
class TestPolicyEvalLinearTimeout:
    """policy_evaluation_linear has an unused `timeout` parameter."""

    def test_timeout_parameter_accepted(self):
        """The timeout parameter should be accepted without error."""
        mdp = make_russell_norvig_grid()
        V, pi, _ = value_iteration(mdp)
        # Should not raise even with timeout
        V2 = policy_evaluation_linear(mdp, pi, timeout=10.0)
        assert V2 is not None


# ---- Integration: all planners agree ----
class TestPlannerAgreement:
    """All three DP planners should produce the same optimal values."""

    def test_all_planners_agree(self):
        from rl_solver import modified_policy_iteration
        mdp = make_russell_norvig_grid()
        V1, _, _ = value_iteration(mdp)
        V2, _, _ = policy_iteration(mdp)
        V3, _, _ = modified_policy_iteration(mdp)
        max_diff = max(
            max(abs(V1[s] - V2[s]) for s in mdp.states),
            max(abs(V1[s] - V3[s]) for s in mdp.states),
        )
        assert max_diff < 1e-3, f"Planners disagree by {max_diff}"