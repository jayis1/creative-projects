"""
Example: Batch solving and benchmarking.

Demonstrates solving multiple puzzles at once and measuring performance.
"""
from nonogram.batch import BatchSolver
from nonogram.benchmark import BenchmarkSuite
from nonogram.stats import SolverStats

# Batch solve all puzzles in the puzzles/ directory.
print("=" * 60)
print("Batch Solving")
print("=" * 60)
bs = BatchSolver(check_unique=True)
report = bs.solve_files("puzzles/")
print(report.summary())
print()

# Save reports.
print(report.to_json())

# Run benchmarks.
print("\n" + "=" * 60)
print("Benchmarking")
print("=" * 60)
suite = BenchmarkSuite(warmup=False)
suite.run_all()
print(suite.summary())

# Show stats.
print("\n" + "=" * 60)
print("Solver Statistics")
print("=" * 60)
stats = SolverStats()
stats.propagation_rounds = 42
stats.lines_solved = 100
stats.backtrack_nodes = 5
print(stats.summary())