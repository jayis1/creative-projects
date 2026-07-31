"""
Example: RAVE search and comparison with UCT.

Shows how to use RAVE (Rapid Action Value Estimation) and compare
win rates against plain UCT.
"""

from mcts import MCTSEngine, TicTacToe, UCTPolicy, RAVEPolicy

game = TicTacToe()

# UCT search
engine_uct = MCTSEngine(
    selection_policy=UCTPolicy(1.4142),
    simulation_limit=5000,
    seed=42,
)
result_uct = engine_uct.search(game)
print(f"UCT:  best_move={result_uct.best_move}, win_rate={result_uct.win_rate:.1%}, "
      f"sims={result_uct.simulations}, time={result_uct.time_elapsed:.3f}s")

# RAVE search
engine_rave = MCTSEngine(
    selection_policy=RAVEPolicy(1.4142, rave_k=300),
    simulation_limit=5000,
    rave=True,
    seed=42,
)
result_rave = engine_rave.search(game)
print(f"RAVE: best_move={result_rave.best_move}, win_rate={result_rave.win_rate:.1%}, "
      f"sims={result_rave.simulations}, time={result_rave.time_elapsed:.3f}s")

# RAVE typically converges faster (higher win rate with same simulations)
if result_rave.win_rate > result_uct.win_rate:
    print("\nRAVE found a better move faster!")
else:
    print("\nUCT found a good move (RAVE may need more simulations).")