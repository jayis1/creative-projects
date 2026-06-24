"""Example: Use configuration files to customize the engine."""

from chess_engine import Board, Search, load_config, apply_search_config

# Example YAML config (save to engine.yaml and pass to load_config)
EXAMPLE_YAML = """\
search:
  max_depth: 6
  time_limit: 5.0
  use_null_move: true
  use_lmr: true
  use_history: true
  use_killers: true
  use_iterative_deepening: true
  use_tt: true

evaluation:
  tempo_bonus: 10

opening_book:
  enabled: true
  file: null

logging:
  level: INFO
"""

def main():
    import tempfile, os, json

    # Write a JSON config (YAML also supported if pyyaml installed)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({
            "search": {
                "max_depth": 5,
                "use_null_move": True,
                "use_lmr": True,
            }
        }, f)
        config_path = f.name

    try:
        # Load and apply
        cfg = load_config(config_path)
        print(f"Loaded config: max_depth={cfg['search']['max_depth']}, "
              f"null_move={cfg['search']['use_null_move']}")

        search = Search()
        apply_search_config(search, cfg)
        print(f"Search max_depth: {search.max_depth}")
        print(f"Search use_null_move: {search.use_null_move}")

        # Search
        board = Board()
        move, score = search.search(board, depth=3)
        print(f"\nBest move: {move.uci()}, score: {score}")
    finally:
        os.unlink(config_path)


if __name__ == "__main__":
    main()