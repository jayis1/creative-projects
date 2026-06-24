"""Transposition table for search memoization.

Stores evaluated positions keyed by Zobrist hash, enabling the search
to avoid re-evaluating positions it has already seen. Uses the
depth-preferred replacement scheme: a new entry replaces an old one
if it has equal or greater depth.
"""

from __future__ import annotations

from typing import Optional, Tuple

# Entry flags
FLAG_EXACT = 0    # exact score
FLAG_LOWER = 1    # beta cutoff (score is a lower bound)
FLAG_UPPER = 2    # fail-low (score is an upper bound)


class TTEntry:
    __slots__ = ("key", "depth", "score", "flag", "best_move")

    def __init__(self, key: int, depth: int, score: int,
                 flag: int, best_move=None):
        self.key = key
        self.depth = depth
        self.score = score
        self.flag = flag
        self.best_move = best_move


class TranspositionTable:
    """A fixed-size transposition table using Zobrist hashing.

    Uses a simple hash table with replacement: if the table is full,
    entries with lower depth are replaced first.
    """

    def __init__(self, size: int = 1 << 18) -> None:
        """Create a TT with 2^size entries (default 262144)."""
        self.size = size
        self.table: dict[int, TTEntry] = {}

    def store(self, key: int, depth: int, score: int, flag: int,
              best_move=None) -> None:
        """Store a position in the TT."""
        existing = self.table.get(key)
        # Replace if new entry has >= depth (depth-preferred replacement)
        if existing is None or depth >= existing.depth:
            self.table[key] = TTEntry(key, depth, score, flag, best_move)
            # Prevent unbounded growth
            if len(self.table) > self.size:
                # Evict shallowest entries
                self._evict()

    def probe(self, key: int) -> Optional[TTEntry]:
        """Look up a position in the TT."""
        return self.table.get(key)

    def _evict(self) -> None:
        """Remove the shallowest entries to stay within size."""
        if len(self.table) <= self.size:
            return
        # Sort by depth and remove the 10% shallowest
        to_remove = len(self.table) - self.size + self.size // 10
        items = sorted(self.table.items(), key=lambda x: x[1].depth)
        for i in range(to_remove):
            del self.table[items[i][0]]

    def clear(self) -> None:
        self.table.clear()

    def __len__(self) -> int:
        return len(self.table)