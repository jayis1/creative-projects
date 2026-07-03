"""Enhanced smoke test for rl-solver v2.0 (not part of pytest suite)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rl_solver import (
    make_russell_norvig_grid, make_cliff_walking, make_frozen_lake, make_chain,
    make_bridge_walking, make_random_mdp,
    value_iteration, policy_iteration, modified_policy_iteration,
    policy_evaluation_linear, policy_evaluation_iterative,
    QLearner, SARSALearner, ExpectedSARSALearner, DoubleQLearner, MonteCarloLearner,
    NStepSARSALearner, NStepTreeBackupLearner, SARSALambdaLearner, QLambdaLearner,
    simulate_policy, compare_planners, compare_learners, greedy_policy, q_values,
    render_value_heatmap, render_policy_grid, render_q_table, render_learning_curve,
)


def main():
    print("=" * 60)
    print("rl-solver v2.0 Enhanced Smoke Test")
    print("=" * 60)

    # 1. DP planners
    mdp = make_russell_norvig_grid()
    V, pi, info = value_iteration(mdp)
    print(f"\n[DP] VI: iters={info['iterations']}, V(start)={V[(0,0)]:.4f}")
    V2, pi2, _ = policy_iteration(mdp)
    diff = max(abs(V[s] - V2[s]) for s in mdp.states)
    assert diff < 1e-4, f"VI/PI mismatch: {diff}"
    print(f"[DP] PI matches VI (diff={diff:.2e})")

    # 2. Linear policy evaluation
    V_lin = policy_evaluation_linear(mdp, pi)
    V_iter = policy_evaluation_iterative(mdp, pi)
    diff2 = max(abs(V_lin[s] - V_iter[s]) for s in mdp.states)
    assert diff2 < 1e-4
    print(f"[DP] Linear vs iterative eval: diff={diff2:.2e}")

    # 3. Q-learning
    q = QLearner(mdp, alpha=0.1, epsilon=0.2, seed=42)
    q.train(n_episodes=5000, max_steps=200)
    sim = simulate_policy(mdp, q.greedy_policy(), n_episodes=500, seed=42)
    print(f"[RL] Q-learning: sim_return={sim['mean_return']:.3f}, success={sim['success_rate']:.2%}")

    # 4. SARSA
    sarsa = SARSALearner(mdp, alpha=0.1, epsilon=0.2, seed=42)
    sarsa.train(n_episodes=5000, max_steps=200)
    sim2 = simulate_policy(mdp, sarsa.greedy_policy(), n_episodes=500, seed=42)
    print(f"[RL] SARSA: sim_return={sim2['mean_return']:.3f}")

    # 5. n-step SARSA
    ns = NStepSARSALearner(mdp, n=3, alpha=0.1, epsilon=0.2, seed=42)
    ns.train(n_episodes=5000, max_steps=200)
    sim3 = simulate_policy(mdp, ns.greedy_policy(), n_episodes=500, seed=42)
    print(f"[RL] n-step SARSA (n=3): sim_return={sim3['mean_return']:.3f}")

    # 6. SARSA(λ)
    sl = SARSALambdaLearner(mdp, lam=0.5, alpha=0.1, epsilon=0.2, seed=42)
    sl.train(n_episodes=5000, max_steps=200)
    sim4 = simulate_policy(mdp, sl.greedy_policy(), n_episodes=500, seed=42)
    print(f"[RL] SARSA(λ=0.5): sim_return={sim4['mean_return']:.3f}")

    # 7. Q(λ)
    ql = QLambdaLearner(mdp, lam=0.5, alpha=0.1, epsilon=0.2, seed=42)
    ql.train(n_episodes=5000, max_steps=200)
    sim5 = simulate_policy(mdp, ql.greedy_policy(), n_episodes=500, seed=42)
    print(f"[RL] Q(λ=0.5): sim_return={sim5['mean_return']:.3f}")

    # 8. Double Q-learning
    dq = DoubleQLearner(mdp, alpha=0.1, epsilon=0.2, seed=42)
    dq.train(n_episodes=5000, max_steps=200)
    sim6 = simulate_policy(mdp, dq.greedy_policy(), n_episodes=500, seed=42)
    print(f"[RL] Double Q: sim_return={sim6['mean_return']:.3f}")

    # 9. New environments
    bridge = make_bridge_walking(size=5)
    Vb, pib, _ = value_iteration(bridge)
    print(f"[Env] Bridge: V(start)={Vb[(0,0)]:.4f}, policy(0,0)={pib[(0,0)]}")

    rmdp = make_random_mdp(n_states=10, n_actions=3, seed=7)
    Vr, pir, _ = value_iteration(rmdp)
    print(f"[Env] Random MDP (10s/3a): V(0)={Vr[0]:.4f}")

    # 10. Visualization
    print("\n[Vis] Value heatmap:")
    print(render_value_heatmap(mdp, V))
    print("\n[Vis] Policy grid:")
    print(render_policy_grid(mdp, pi))
    print("\n[Vis] Q-table (first few):")
    print(render_q_table(q.Q, max_states=8))
    print("\n[Vis] Learning curve:")
    print(render_learning_curve(q.episode_rewards, width=40, height=8))

    # 11. Compare planners
    print("\n[Compare] Planners:")
    for r in compare_planners(mdp, seed=42):
        print(f"  {r['name']}: return={r['sim_mean_return']:.3f}, iters={r['iterations']}")

    print("\n✅ All enhanced smoke tests passed!")


if __name__ == "__main__":
    main()