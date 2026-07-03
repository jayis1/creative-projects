"""Example 1: Solve the Russell-Norvig gridworld with all DP planners."""
from rl_solver import (
    make_russell_norvig_grid, value_iteration, policy_iteration,
    modified_policy_iteration, linear_programming_solve,
    gauss_seidel_value_iteration, prioritized_sweeping, rtdp,
    render_value_heatmap, render_policy_grid,
)

mdp = make_russell_norvig_grid()

planners = [
    ("Value Iteration", value_iteration, {}),
    ("Policy Iteration", policy_iteration, {}),
    ("Modified PI", modified_policy_iteration, {}),
    ("LP Solver", linear_programming_solve, {}),
    ("Gauss-Seidel VI", gauss_seidel_value_iteration, {}),
    ("Prioritized Sweeping", prioritized_sweeping, {}),
    ("RTDP", rtdp, {"n_trials": 2000, "seed": 42}),
]

print("=" * 70)
print("Solving the Russell-Norvig 4×4 Gridworld")
print("=" * 70)
print(f"States: {len(mdp.states)}, Actions: {len(mdp.actions)}, Gamma: {mdp.gamma}")
print()

V_ref, _, _ = value_iteration(mdp)

for name, fn, kwargs in planners:
    V, pi, info = fn(mdp, **kwargs)
    diff = max(abs(V[s] - V_ref[s]) for s in mdp.states)
    iters = info.get("iterations", info.get("trials", "?"))
    time_ms = info["time"] * 1000
    print(f"  {name:<25} iters={iters:>5}  time={time_ms:>8.2f}ms  "
          f"V(start)={V[(0,0)]:.6f}  diff={diff:.2e}")

print("\nOptimal value heatmap:")
print(render_value_heatmap(mdp, V_ref))
print("\nOptimal policy:")
_, pi_opt, _ = value_iteration(mdp)
print(render_policy_grid(mdp, pi_opt))