"""
Example: Configuration file support.

Demonstrates loading engine configuration from JSON and YAML files,
and using the config to create games and engines.
"""

import json
import os
import tempfile

from mcts import MCTSConfig

# Create a configuration programmatically
config = MCTSConfig()
config.game.name = "connect4"
config.engine.policy = "rave"
config.engine.simulation_limit = 5000
config.engine.rave_k = 300
config.engine.seed = 42
config.engine.verbose = True

# Save to JSON
with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
    json.dump(config.to_dict(), f, indent=2)
    config_path = f.name

print(f"Config saved to: {config_path}")
with open(config_path) as f:
    print(f.read())

# Load from JSON
loaded = MCTSConfig.from_file(config_path)
print(f"\nLoaded config:")
print(f"  Game: {loaded.game.name}")
print(f"  Policy: {loaded.engine.policy}")
print(f"  Sims: {loaded.engine.simulation_limit}")
print(f"  RAVE k: {loaded.engine.rave_k}")

# Create game and engine from config
game = loaded.game.create()
engine = loaded.engine.create(loaded.game.name)

print(f"\nGame: {type(game).__name__}")
print(f"Engine policy: {engine.policy.name}")

# Run a search
result = engine.search(game)
print(f"\nSearch result: best_move={result.best_move}, win_rate={result.win_rate:.1%}")

os.unlink(config_path)