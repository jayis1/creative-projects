"""Compare the four cell-selection strategies on a dungeon.

Run with:  python3 examples/compare_strategies.py
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wfc_generator import WFCGrid, create_dungeon_tileset, SelectionStrategy

STRATEGIES = [
    SelectionStrategy.MIN_ENTROPY,
    SelectionStrategy.MRV,
    SelectionStrategy.RANDOM,
    SelectionStrategy.LEXICAL,
]


def main():
    tileset = create_dungeon_tileset()
    width, height = 30, 20
    print(f"{'strategy':<14} {'time(s)':>8} {'cells/s':>9} {'backtracks':>11} {'restarts':>9}")
    print("-" * 55)
    for strat in STRATEGIES:
        grid = WFCGrid(tileset, width, height, seed=123, selection=strat)
        start = time.time()
        ok = grid.run()
        elapsed = time.time() - start
        if not ok:
            print(f"{strat.value:<14} {'FAILED':>8}")
            continue
        cells_s = (width * height) / elapsed if elapsed > 0 else 0
        print(
            f"{strat.value:<14} {elapsed:>8.3f} {cells_s:>9.0f} "
            f"{grid.stats.backtrack_count:>11} {grid.stats.restart_count:>9}"
        )


if __name__ == "__main__":
    main()