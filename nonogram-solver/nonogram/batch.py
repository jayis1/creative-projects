"""
Batch solver for processing multiple puzzle files at once.

Supports glob patterns, directories, and file lists. Can output solutions
in various formats and generate a summary report.

Usage::

    from nonogram.batch import BatchSolver

    bs = BatchSolver(output_dir="solutions/")
    report = bs.solve_files("puzzles/*.json")
    print(report.summary())

CLI::

    python -m nonogram.cli batch puzzles/*.json --output-dir solutions/
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from nonogram.board import Board, Cell
from nonogram.solver import Solver, SolveResult
from nonogram.io import PuzzleIO

logger = logging.getLogger("nonogram.batch")


@dataclass
class PuzzleResult:
    """Result of solving a single puzzle file."""
    filename: str
    solved: bool
    iterations: int = 0
    backtracks: int = 0
    elapsed: float = 0.0
    error: Optional[str] = None
    unique: Optional[bool] = None

    def to_dict(self) -> dict:
        return {
            "filename": self.filename,
            "solved": self.solved,
            "iterations": self.iterations,
            "backtracks": self.backtracks,
            "elapsed": round(self.elapsed, 4),
            "error": self.error,
            "unique": self.unique,
        }


@dataclass
class BatchReport:
    """Aggregate report for a batch of puzzles."""
    results: List[PuzzleResult] = field(default_factory=list)
    total_elapsed: float = 0.0

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def solved_count(self) -> int:
        return sum(1 for r in self.results if r.solved)

    @property
    def failed_count(self) -> int:
        return sum(1 for r in self.results if not r.solved)

    @property
    def unique_count(self) -> int:
        return sum(1 for r in self.results if r.unique)

    def summary(self) -> str:
        """Human-readable summary string."""
        lines = [
            f"Batch Report: {self.total} puzzles",
            f"  Solved:    {self.solved_count}",
            f"  Failed:    {self.failed_count}",
            f"  Unique:    {self.unique_count}",
            f"  Total time: {self.total_elapsed:.2f}s",
        ]
        if self.results:
            avg = sum(r.elapsed for r in self.results) / len(self.results)
            lines.append(f"  Avg time:   {avg:.4f}s")
        return "\n".join(lines)

    def to_json(self) -> str:
        """Serialise the report to a JSON string."""
        import json
        return json.dumps({
            "total": self.total,
            "solved": self.solved_count,
            "failed": self.failed_count,
            "unique": self.unique_count,
            "total_elapsed": round(self.total_elapsed, 4),
            "results": [r.to_dict() for r in self.results],
        }, indent=2)

    def to_csv(self) -> str:
        """Serialise the report as CSV."""
        header = "filename,solved,iterations,backtracks,elapsed,unique,error"
        rows = [header]
        for r in self.results:
            rows.append(
                f"{r.filename},{r.solved},{r.iterations},"
                f"{r.backtracks},{r.elapsed:.4f},"
                f"{r.unique if r.unique is not None else ''},"
                f"{r.error or ''}"
            )
        return "\n".join(rows)


class BatchSolver:
    """Solve multiple nonogram puzzle files in batch.

    Parameters
    ----------
    output_dir : str, optional
        Directory to write solved boards (as JSON). Created if it doesn't
        exist. If None, no files are written.
    solver : Solver, optional
        A pre-configured solver instance. If None, a default Solver is used.
    check_unique : bool
        If True, also check solution uniqueness for each puzzle.
    """

    def __init__(
        self,
        output_dir: Optional[str] = None,
        solver: Optional[Solver] = None,
        check_unique: bool = False,
    ) -> None:
        self.output_dir = Path(output_dir) if output_dir else None
        if self.output_dir:
            self.output_dir.mkdir(parents=True, exist_ok=True)
        self.solver = solver or Solver()
        self.check_unique = check_unique

    def solve_file(self, path: str) -> PuzzleResult:
        """Solve a single puzzle file and return a PuzzleResult."""
        p = Path(path)
        start = time.perf_counter()
        try:
            board = _load_board(str(p))
            # Reset grid to unknown.
            for r in range(board.height):
                for c in range(board.width):
                    board.grid[r][c] = Cell.UNKNOWN
            result = self.solver.solve(board)
            elapsed = time.perf_counter() - start

            unique: Optional[bool] = None
            if self.check_unique and result.solved:
                test = Board(board.row_clues, board.col_clues)
                count = self.solver.count_solutions(test, limit=2)
                unique = count == 1

            # Save output.
            if result.solved and self.output_dir:
                out_path = self.output_dir / f"{p.stem}_solved.json"
                PuzzleIO.save_json(board, str(out_path))

            return PuzzleResult(
                filename=str(p),
                solved=result.solved,
                iterations=result.iterations,
                backtracks=result.backtracks,
                elapsed=elapsed,
                unique=unique,
            )
        except Exception as exc:
            elapsed = time.perf_counter() - start
            logger.error("Error solving %s: %s", p, exc)
            return PuzzleResult(
                filename=str(p),
                solved=False,
                elapsed=elapsed,
                error=str(exc),
            )

    def solve_files(
        self,
        pattern: str,
        recursive: bool = False,
    ) -> BatchReport:
        """Solve all puzzle files matching *pattern*.

        Parameters
        ----------
        pattern : str
            Glob pattern (e.g. ``"puzzles/*.json"``) or a directory path.
            If a directory, all ``.json`` and ``.non`` files inside it are
            processed.
        recursive : bool
            If True and *pattern* is a directory, search subdirectories too.

        Returns
        -------
        BatchReport
            Aggregate report of all results.
        """
        p = Path(pattern)
        if p.is_dir():
            # Gather all puzzle files from the directory.
            files = sorted(
                list(p.glob("**/*.json" if recursive else "*.json"))
                + list(p.glob("**/*.non" if recursive else "*.non"))
            )
        else:
            files = sorted(Path(".").glob(pattern))
            if not files and p.exists():
                files = [p]

        results: List[PuzzleResult] = []
        total_start = time.perf_counter()
        for f in files:
            logger.info("Solving %s ...", f)
            result = self.solve_file(str(f))
            results.append(result)
            status = "SOLVED" if result.solved else "FAILED"
            logger.info(
                "  %s — %s (iters=%d, bt=%d, %.3fs)",
                f, status, result.iterations, result.backtracks, result.elapsed,
            )
        total_elapsed = time.perf_counter() - total_start

        return BatchReport(results=results, total_elapsed=total_elapsed)


def _load_board(path: str) -> Board:
    """Load a board from JSON or NON format based on extension."""
    p = Path(path)
    if p.suffix == ".non":
        return PuzzleIO.load_non(path)
    return PuzzleIO.load_json(path)