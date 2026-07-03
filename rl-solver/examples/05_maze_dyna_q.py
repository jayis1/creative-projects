"""Example 5: Maze solving with walls and Dyna-Q learning."""
from rl_solver import (
    make_maze, value_iteration, DynaQLearner, QLearner,
    simulate_policy, render_policy_grid, render_value_heatmap,
)

# Create a 10×8 maze with walls
walls = [
    (1, 2), (1, 3), (1, 4),
    (3, 1), (3, 5), (3, 6),
    (5, 3), (5, 4), (5, 7),
    (6, 3), (6, 4),
]
mdp = make_maze(width=10, height=8, walls=walls,
                goal=(7, 9), start=(0, 0), gamma=0.99)

# Optimal solution
V, pi, info = value_iteration(mdp)
print("=" * 60)
print("Maze Solving: DP vs Dyna-Q")
print("=" * 60)
print(f"States: {len(mdp.states)}, Walls: {len(walls)}")
print(f"Optimal V(start) = {V[(0,0)]:.4f}")
print(f"VI iterations: {info['iterations']}")
print()

# Compare Q-learning vs Dyna-Q
print("Training Q-learning vs Dyna-Q (2000 episodes)...")
q_learner = QLearner(mdp, alpha=0.5, epsilon=0.3, seed=42)
q_learner.train(n_episodes=2000, max_steps=500)
sim_q = simulate_policy(mdp, q_learner.greedy_policy(), n_episodes=200, seed=42)

dyna = DynaQLearner(mdp, alpha=0.5, epsilon=0.3, n_planning=20, seed=42)
dyna.train(n_episodes=2000, max_steps=500)
sim_dyna = simulate_policy(mdp, dyna.greedy_policy(), n_episodes=200, seed=42)

print(f"Q-Learning:  sim_return={sim_q['mean_return']:.3f}, "
      f"success={sim_q['success_rate']:.1%}")
print(f"Dyna-Q(20):  sim_return={sim_dyna['mean_return']:.3f}, "
      f"success={sim_dyna['success_rate']:.1%}")

print("\nOptimal policy (arrows):")
print(render_policy_grid(mdp, pi))