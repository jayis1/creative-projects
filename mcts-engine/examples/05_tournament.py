"""
Example: Tournament mode — compare engine configurations.

Runs a round-robin tournament between UCT, RAVE, and heuristic-guided
MCTS configurations. Elo ratings are computed from results.
"""

from mcts import (
    MCTSEngine, TicTacToe, UCTPolicy, RAVEPolicy,
    Tournament, PlayerSpec, get_heuristic,
)

# Define players with different engine configurations
h = get_heuristic("tictactoe")
players = [
    PlayerSpec("UCT-c1.41", MCTSEngine(
        UCTPolicy(1.4142), simulation_limit=1000, seed=42)),
    PlayerSpec("UCT-c0.5", MCTSEngine(
        UCTPolicy(0.5), simulation_limit=1000, seed=99)),
    PlayerSpec("RAVE", MCTSEngine(
        RAVEPolicy(1.4142, 300), simulation_limit=1000, rave=True, seed=77)),
    PlayerSpec("UCT+Heur", MCTSEngine(
        UCTPolicy(1.4142), simulation_limit=1000, seed=55,
        progressive_bias=1.0, heuristic_fn=h)),
]

# Run tournament (each pair plays 4 games)
tourney = Tournament(
    players,
    game_factory=lambda: TicTacToe(),
    rounds=4,
)

print("Starting tournament...")
result = tourney.run()
print()
print(result.summary())