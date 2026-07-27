#!/usr/bin/env python3
"""Example: Batch generate puzzles and analyze difficulty distribution.

Usage:
    python3 examples/batch_analyze.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from collections import Counter
from kenken_solver import KenKenGenerator, KenKenSolver, PuzzleAnalyzer


def main() -> None:
    size = 5
    count = 20
    print(f"Generating {count} {size}x{size} puzzles and analyzing difficulty...\n")

    categories = Counter()
    scores = []
    all_solutions_unique = True

    for i in range(count):
        gen = KenKenGenerator(size=size, seed=i + 1)
        puzzle = gen.generate()
        analyzer = PuzzleAnalyzer(puzzle)
        result = analyzer.analyze()
        categories[result["difficulty_category"]] += 1
        scores.append(result["difficulty_score"])

        # Verify uniqueness
        solver = KenKenSolver(puzzle, max_solutions=2)
        solver.solve()
        if len(solver.solutions) != 1:
            all_solutions_unique = False

    print(f"Generated {count} puzzles, all unique: {all_solutions_unique}")
    print(f"\nDifficulty distribution:")
    for cat in ["easy", "medium", "hard"]:
        print(f"  {cat:8s}: {categories[cat]}")
    print(f"\nDifficulty scores:")
    print(f"  Min: {min(scores)}")
    print(f"  Max: {max(scores)}")
    print(f"  Avg: {sum(scores) / len(scores):.1f}")
    print(f"  Range: {max(scores) - min(scores)}")


if __name__ == "__main__":
    main()