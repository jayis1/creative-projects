"""Example 3: Solve the Blackjack MDP and find the optimal policy."""
from rl_solver import make_blackjack, value_iteration, render_policy_grid

mdp = make_blackjack()
V, pi, info = value_iteration(mdp, theta=1e-8)

print("=" * 60)
print("Blackjack Optimal Strategy")
print("=" * 60)
print(f"States: {len(mdp.states)}, Actions: {mdp.actions}")
print(f"Iterations: {info['iterations']}")
print(f"V(start) = {V[mdp.start_state]:.4f}")
print()

# Print strategy table: player_sum vs dealer_show
print("Optimal strategy (H=hit, S=stand):")
print()
print("         Dealer showing:")
print("  Player  " + "  ".join(f"{d:>2}" for d in range(1, 11)))
print("  Sum    " + "-" * 30)
for p in range(12, 22):
    row_no_ace = ""
    row_with_ace = ""
    for d in range(1, 11):
        s_no = (p, d, False)
        s_yes = (p, d, True)
        a_no = pi[s_no] if s_no in pi.table else "?"
        a_yes = pi[s_yes] if s_yes in pi.table else "?"
        row_no_ace += f"  {a_no[0].upper() if a_no else '?':>1}"
        row_with_ace += f"  {a_yes[0].upper() if a_yes else '?':>1}"
    print(f"  {p:>2}     {row_no_ace}   (no usable ace)")
    if p <= 21:
        print(f"  {p:>2}     {row_with_ace}   (usable ace)")
        print()