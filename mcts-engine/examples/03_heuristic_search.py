"""
Example: Heuristic-guided search with progressive bias.

Demonstrates using game-specific heuristics to guide MCTS search
via progressive bias and epsilon-greedy rollouts.
"""

from mcts import (
    MCTSEngine, Connect4, UCTPolicy,
    get_heuristic, make_rollout_policy,
)

game = Connect4()
print("Connect4 initial board:")
print(game.display())
print()

# Get the Connect4 heuristic
heuristic = get_heuristic("connect4")

# Engine with progressive bias (heuristic priors) + heuristic rollouts
rollout = make_rollout_policy(heuristic, epsilon=0.2)
engine = MCTSEngine(
    selection_policy=UCTPolicy(1.4142),
    simulation_limit=10000,
    seed=42,
    progressive_bias=1.0,
    heuristic_fn=heuristic,
    rollout_policy=rollout,
    verbose=True,
)

result = engine.search(game)
print(f"\nBest move: {result.best_move}")
print(f"Win rate: {result.win_rate:.1%}")

# Compare with plain UCT (no heuristic)
engine_plain = MCTSEngine(
    selection_policy=UCTPolicy(1.4142),
    simulation_limit=10000,
    seed=42,
)
result_plain = engine_plain.search(game)
print(f"\nPlain UCT win rate: {result_plain.win_rate:.1%}")
print(f"Heuristic-guided win rate: {result.win_rate:.1%}")