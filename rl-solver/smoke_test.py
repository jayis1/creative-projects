"""Quick smoke test for rl-solver (not part of pytest suite)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rl_solver import (
    make_russell_norvig_grid, make_cliff_walking, make_frozen_lake, make_chain,
    value_iteration, policy_iteration, modified_policy_iteration,
    policy_evaluation_linear, policy_evaluation_iterative,
    QLearner, SARSALearner, ExpectedSARSALearner, DoubleQLearner, MonteCarloLearner,
    simulate_policy, compare_planners, compare_learners, greedy_policy, q_values,
)

def main():
    # Test 1: Russell-Norvig grid value iteration
    mdp = make_russell_norvig_grid()
    V, pi, info = value_iteration(mdp)
    print(f"VI: iters={info['iterations']}, V(start)={V[(0,0)]:.4f}")

    # Test 2: Policy iteration matches value iteration
    V2, pi2, info2 = policy_iteration(mdp)
    diff = max(abs(V[s] - V2[s]) for s in mdp.states)
    print(f"PI: iters={info2['iterations']}, max diff from VI: {diff:.2e}")
    assert diff < 1e-4, f"VI and PI disagree by {diff}"

    # Test 3: Linear policy evaluation matches iterative
    V_lin = policy_evaluation_linear(mdp, pi)
    V_iter = policy_evaluation_iterative(mdp, pi)
    diff2 = max(abs(V_lin[s] - V_iter[s]) for s in mdp.states)
    print(f"Linear vs iterative eval diff: {diff2:.2e}")
    assert diff2 < 1e-4

    # Test 4: Q-learning on small grid
    q = QLearner(mdp, alpha=0.1, epsilon=0.2, seed=42)
    stats = q.train(n_episodes=5000, max_steps=200)
    pi_q = q.greedy_policy()
    sim = simulate_policy(mdp, pi_q, n_episodes=500, seed=42)
    print(f"Q-learning: mean_reward={stats['mean_reward']:.3f}, sim_return={sim['mean_return']:.3f}")

    # Test 5: Chain MDP
    chain = make_chain(n=5)
    Vc, pic, _ = value_iteration(chain)
    print(f"Chain: V(0)={Vc[0]:.4f}, policy(0)={pic[0]}")

    # Test 6: Compare planners
    results = compare_planners(mdp, seed=42)
    for r in results:
        print(f"  {r['name']}: return={r['sim_mean_return']:.3f}")

    print("\nAll smoke tests passed!")


if __name__ == "__main__":
    main()