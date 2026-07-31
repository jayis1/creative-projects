"""
Opening book support for MCTS games.

An opening book stores pre-computed best moves for common opening
positions, allowing the engine to play instantly in known positions
and save search time for the midgame.

Books are stored as JSON files mapping state hash keys to move
recommendations. They can be built via self-play or imported from
external sources.
"""

from __future__ import annotations

import json
import os
import random
from typing import Dict, List, Optional

from .core import GameMove, GameState, Player


class OpeningBook:
    """A simple opening book mapping state hashes to recommended moves.

    The book stores entries as::

        {
            "state_hash": {
                "moves": [{"row": 0, "col": 0, "weight": 1.0}, ...],
                "depth": 3
            },
            ...
        }

    ``weight`` allows probabilistic move selection when multiple
    good moves exist for a position.
    """

    def __init__(self) -> None:
        self._entries: Dict[str, dict] = {}

    def add(
        self,
        state: GameState,
        move: GameMove,
        weight: float = 1.0,
        depth: int = 0,
    ) -> None:
        """Add a move recommendation for a state."""
        key = state.hash_key()
        entry = self._entries.get(key, {"moves": [], "depth": depth})
        # Check if move already exists
        for m in entry["moves"]:
            if m["row"] == move.row and m["col"] == move.col:
                m["weight"] = max(m["weight"], weight)
                break
        else:
            entry["moves"].append({
                "row": move.row,
                "col": move.col,
                "weight": weight,
            })
        entry["depth"] = max(entry["depth"], depth)
        self._entries[key] = entry

    def lookup(self, state: GameState) -> Optional[GameMove]:
        """Look up a move for the given state.

        Returns a weighted-random choice from the book entries,
        or None if the position is not in the book.
        """
        key = state.hash_key()
        entry = self._entries.get(key)
        if not entry or not entry["moves"]:
            return None
        moves = entry["moves"]
        weights = [m["weight"] for m in moves]
        total = sum(weights)
        if total <= 0:
            return None
        # Weighted random selection
        r = random.random() * total
        cumulative = 0.0
        for m, w in zip(moves, weights):
            cumulative += w
            if r <= cumulative:
                return GameMove(m["row"], m["col"])
        return GameMove(moves[-1]["row"], moves[-1]["col"])

    def has(self, state: GameState) -> bool:
        """Check if the book has an entry for this state."""
        return state.hash_key() in self._entries

    def __len__(self) -> int:
        return len(self._entries)

    def save(self, path: str) -> None:
        """Save the opening book to a JSON file."""
        with open(path, "w") as f:
            json.dump(self._entries, f, indent=2)

    @classmethod
    def load(cls, path: str) -> "OpeningBook":
        """Load an opening book from a JSON file."""
        book = cls()
        if not os.path.exists(path):
            return book
        with open(path, "r") as f:
            book._entries = json.load(f)
        return book

    @classmethod
    def build_from_selfplay(
        cls,
        game: GameState,
        engine,
        num_games: int = 100,
        max_depth: int = 6,
        seed: int = 42,
    ) -> "OpeningBook":
        """Build an opening book by running self-play games.

        Records the first ``max_depth`` moves of each game, weighting
        moves by the game outcome (win = 1.0, draw = 0.5, loss = 0.0).
        """
        book = cls()
        rng = random.Random(seed)

        for g in range(num_games):
            current = game
            move_history: List[tuple] = []
            count = 0

            # Play a game
            while not current.is_terminal() and count < 200:
                if count < max_depth:
                    result = engine.search(current)
                    if result.best_move is None:
                        break
                    move = result.best_move
                    move_history.append((current, move))
                else:
                    # Play rest of game quickly
                    legal = current.legal_moves()
                    if not legal:
                        break
                    move = rng.choice(legal)

                current = current.apply(move)
                count += 1

            # Determine outcome weight
            winner = current.winner()
            if winner == Player.NONE:
                weight = 0.5
            else:
                weight = 1.0  # winning moves get full weight

            # Record opening moves
            for i, (state, move) in enumerate(move_history):
                # Weight by depth (earlier moves matter more)
                depth_weight = 1.0 - (i / max(1, max_depth)) * 0.3
                book.add(state, move, weight=weight * depth_weight, depth=i)

        return book