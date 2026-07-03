"""Example 4: Windy Gridworld — compare standard vs king moves."""
from rl_solver import (
    make_windy_gridworld, value_iteration, simulate_policy,
    render_policy_grid, render_value_heatmap,
)

# Standard 4-action windy gridworld
mdp_std = make_windy_gridworld(king_moves=False)
V_std, pi_std, info_std = value_iteration(mdp_std, theta=1e-6)
sim_std = simulate_policy(mdp_std, pi_std, n_episodes=1000, seed=42)

print("=" * 60)
print("Windy Gridworld (Sutton & Barto §6.5)")
print("=" * 60)
print(f"\nStandard moves (N/S/E/W):")
print(f"  Optimal path length: {-V_std[(3,0)]:.0f} steps")
print(f"  Simulated mean return: {sim_std['mean_return']:.2f}")
print(f"  Converged in {info_std['iterations']} iterations")

print("\nValue heatmap:")
print(render_value_heatmap(mdp_std, V_std))
print("\nPolicy:")
print(render_policy_grid(mdp_std, pi_std))

# King moves (8 actions)
mdp_king = make_windy_gridworld(king_moves=True)
V_king, pi_king, info_king = value_iteration(mdp_king, theta=1e-6)
sim_king = simulate_policy(mdp_king, pi_king, n_episodes=1000, seed=42)

print(f"\nKing moves (8 directions):")
print(f"  Optimal path length: {-V_king[(3,0)]:.0f} steps")
print(f"  Simulated mean return: {sim_king['mean_return']:.2f}")
print(f"  Converged in {info_king['iterations']} iterations")