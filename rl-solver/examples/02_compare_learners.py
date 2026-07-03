"""Example 2: Train and compare all RL learners on Cliff Walking."""
from rl_solver import (
    make_cliff_walking, simulate_policy,
    QLearner, SARSALearner, ExpectedSARSALearner, DoubleQLearner,
    MonteCarloLearner, NStepSARSALearner, SARSALambdaLearner,
    DynaQLearner, BoltzmannQLearner,
    render_learning_curve,
)

mdp = make_cliff_walking()

learners = [
    ("Q-Learning", QLearner, {"alpha": 0.5, "epsilon": 0.1, "seed": 42}),
    ("SARSA", SARSALearner, {"alpha": 0.5, "epsilon": 0.1, "seed": 42}),
    ("Expected SARSA", ExpectedSARSALearner, {"alpha": 0.5, "epsilon": 0.1, "seed": 42}),
    ("Double Q", DoubleQLearner, {"alpha": 0.5, "epsilon": 0.1, "seed": 42}),
    ("Monte Carlo", MonteCarloLearner, {"alpha": 0.5, "epsilon": 0.1, "seed": 42}),
    ("n-step SARSA(3)", NStepSARSALearner, {"n": 3, "alpha": 0.5, "epsilon": 0.1, "seed": 42}),
    ("SARSA(λ=0.5)", SARSALambdaLearner, {"lam": 0.5, "alpha": 0.5, "epsilon": 0.1, "seed": 42}),
    ("Dyna-Q", DynaQLearner, {"alpha": 0.5, "epsilon": 0.1, "n_planning": 10, "seed": 42}),
    ("Boltzmann Q", BoltzmannQLearner, {"alpha": 0.5, "temperature": 0.5, "seed": 42}),
]

print("=" * 70)
print("RL Learner Comparison on Cliff Walking (12×4)")
print("=" * 70)
print(f"Training: 5000 episodes each\n")

print(f"{'Learner':<20} {'TrainReward':>12} {'SimReturn':>12} {'Success':>10}")
print("-" * 56)

for name, cls, kwargs in learners:
    learner = cls(mdp, **kwargs)
    stats = learner.train(n_episodes=5000, max_steps=500)
    sim = simulate_policy(mdp, learner.greedy_policy(), n_episodes=200, seed=42)
    print(f"{name:<20} {stats['mean_reward']:>12.2f} "
          f"{sim['mean_return']:>12.2f} {sim['success_rate']:>10.1%}")

# Show learning curve for Q-learning
q_learner = QLearner(mdp, alpha=0.5, epsilon=0.1, seed=42)
q_learner.train(n_episodes=5000, max_steps=500)
print("\nQ-Learning learning curve:")
print(render_learning_curve(q_learner.episode_rewards, width=50, height=10))