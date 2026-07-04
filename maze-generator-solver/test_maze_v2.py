"""
Comprehensive test suite for maze_solver package (v2).

Covers:
- All 9 generation algorithms (perfect maze + solvability)
- All 7 solving algorithms (path validity, shortest path verification)
- Heuristic functions
- Braid functionality
- JSON serialization (round-trip, file I/O, batch)
- Maze validation (perfect maze check)
- Distance maps
- Waypoint pathfinding
- ASCII rendering, PNG export, SVG export
- Benchmarking (explored count correctness)
- Difficulty scoring
- Maze comparison
- Config file loading (JSON)
- CLI interface
- Edge cases (1×1, 2×2, 1×N, N×1 mazes)
- IDA* optimality

Run with: python3 -m pytest test_maze_v2.py -v
"""

import json
import os
import sys
import tempfile
import unittest

# Make the package importable.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from maze_solver import (
    Cell,
    Direction,
    Maze,
    HEURISTICS,
    GENERATOR_NAMES,
    SOLVER_NAMES,
)
from maze_solver.heuristics import (
    manhattan_distance,
    euclidean_distance,
    chebyshev_distance,
)
from maze_solver.analysis import analyze_maze, compare_mazes, difficulty_score
from maze_solver.io_utils import load_config_json, maze_from_config, save_batch, load_batch
from maze_solver.renderers import render_ascii, write_png, write_svg


class TestDirection(unittest.TestCase):
    """Tests for the Direction enum."""

    def test_opposite(self):
        self.assertEqual(Direction.NORTH.opposite, Direction.SOUTH)
        self.assertEqual(Direction.SOUTH.opposite, Direction.NORTH)
        self.assertEqual(Direction.EAST.opposite, Direction.WEST)
        self.assertEqual(Direction.WEST.opposite, Direction.EAST)

    def test_dx_dy(self):
        self.assertEqual((Direction.NORTH.dx, Direction.NORTH.dy), (0, -1))
        self.assertEqual((Direction.EAST.dx, Direction.EAST.dy), (1, 0))
        self.assertEqual((Direction.SOUTH.dx, Direction.SOUTH.dy), (0, 1))
        self.assertEqual((Direction.WEST.dx, Direction.WEST.dy), (-1, 0))


class TestCell(unittest.TestCase):
    """Tests for Cell."""

    def test_init_fully_walled(self):
        c = Cell(3, 5)
        self.assertEqual(c.x, 3)
        self.assertEqual(c.y, 5)
        self.assertEqual(len(c.walls), 4)
        self.assertFalse(c.visited)

    def test_open_count(self):
        c = Cell(0, 0)
        self.assertEqual(c.open_count, 0)
        c.walls.discard(Direction.NORTH)
        self.assertEqual(c.open_count, 1)
        c.walls.discard(Direction.SOUTH)
        self.assertEqual(c.open_count, 2)

    def test_equality_and_hash(self):
        c1 = Cell(2, 3)
        c2 = Cell(2, 3)
        c3 = Cell(3, 2)
        self.assertEqual(c1, c2)
        self.assertNotEqual(c1, c3)
        self.assertEqual(hash(c1), hash(c2))


class TestMazeConstruction(unittest.TestCase):
    """Tests for Maze initialization and validation."""

    def test_valid_construction(self):
        m = Maze(10, 5, seed=42)
        self.assertEqual(m.width, 10)
        self.assertEqual(m.height, 5)
        self.assertEqual(len(m.cells), 5)
        self.assertEqual(len(m.cells[0]), 10)

    def test_zero_dimensions(self):
        with self.assertRaises(ValueError):
            Maze(0, 5)
        with self.assertRaises(ValueError):
            Maze(5, 0)

    def test_negative_dimensions(self):
        with self.assertRaises(ValueError):
            Maze(-1, 5)

    def test_non_integer_dimensions(self):
        with self.assertRaises(TypeError):
            Maze(3.5, 5)
        with self.assertRaises(TypeError):
            Maze(5, "3")

    def test_len(self):
        m = Maze(10, 5)
        self.assertEqual(len(m), 50)

    def test_contains(self):
        m = Maze(10, 5)
        self.assertTrue((5, 3) in m)
        self.assertFalse((10, 3) in m)
        self.assertFalse((3, 5) in m)

    def test_repr(self):
        m = Maze(10, 5, seed=42)
        self.assertIn("10x5", repr(m))
        self.assertIn("42", repr(m))


class TestHeuristics(unittest.TestCase):
    """Tests for heuristic functions."""

    def test_manhattan(self):
        a = Cell(0, 0)
        b = Cell(3, 4)
        self.assertEqual(manhattan_distance(a, b), 7)

    def test_euclidean(self):
        a = Cell(0, 0)
        b = Cell(3, 4)
        self.assertAlmostEqual(euclidean_distance(a, b), 5.0)

    def test_chebyshev(self):
        a = Cell(0, 0)
        b = Cell(3, 4)
        self.assertEqual(chebyshev_distance(a, b), 4)

    def test_heuristics_registry(self):
        self.assertIn("manhattan", HEURISTICS)
        self.assertIn("euclidean", HEURISTICS)
        self.assertIn("chebyshev", HEURISTICS)


class TestGenerators(unittest.TestCase):
    """Tests for all 9 generation algorithms."""

    GENERATORS = GENERATOR_NAMES

    def _make_and_generate(self, w, h, algo, seed=42):
        m = Maze(w, h, seed=seed)
        m.generate(algo)
        return m

    def test_all_generators_produce_solvable_mazes(self):
        for algo in self.GENERATORS:
            m = self._make_and_generate(10, 10, algo)
            solution = m.solve("bfs")
            self.assertIsNotNone(
                solution, f"{algo}: maze should be solvable"
            )
            self.assertTrue(
                solution[0] == m.start,
                f"{algo}: solution should start at maze start"
            )
            self.assertTrue(
                solution[-1] == m.end,
                f"{algo}: solution should end at maze end"
            )

    def test_all_generators_produce_perfect_mazes(self):
        for algo in self.GENERATORS:
            m = self._make_and_generate(8, 8, algo)
            self.assertTrue(
                m.is_perfect(),
                f"{algo}: should produce a perfect maze"
            )

    def test_1x1_maze_all_generators(self):
        for algo in self.GENERATORS:
            m = self._make_and_generate(1, 1, algo)
            self.assertTrue(m.is_perfect(), f"{algo}: 1x1 should be perfect")

    def test_1xN_maze_all_generators(self):
        for algo in self.GENERATORS:
            m = self._make_and_generate(1, 10, algo)
            solution = m.solve("bfs")
            self.assertIsNotNone(solution, f"{algo}: 1x10 should be solvable")

    def test_Nx1_maze_all_generators(self):
        for algo in self.GENERATORS:
            m = self._make_and_generate(10, 1, algo)
            solution = m.solve("bfs")
            self.assertIsNotNone(solution, f"{algo}: 10x1 should be solvable")

    def test_2x2_maze_all_generators(self):
        for algo in self.GENERATORS:
            m = self._make_and_generate(2, 2, algo)
            self.assertTrue(m.is_perfect(), f"{algo}: 2x2 should be perfect")

    def test_seed_reproducibility(self):
        for algo in self.GENERATORS:
            m1 = self._make_and_generate(10, 10, algo, seed=123)
            m2 = self._make_and_generate(10, 10, algo, seed=123)
            # Same seed should produce identical mazes.
            for y in range(10):
                for x in range(10):
                    self.assertEqual(
                        m1.cells[y][x].walls,
                        m2.cells[y][x].walls,
                        f"{algo}: same seed should produce same maze at ({x},{y})"
                    )

    def test_unknown_algorithm_raises(self):
        m = Maze(5, 5)
        with self.assertRaises(ValueError):
            m.generate("nonexistent_algorithm")


class TestSolvers(unittest.TestCase):
    """Tests for all 7 solving algorithms."""

    SOLVERS = SOLVER_NAMES

    def setUp(self):
        self.maze = Maze(15, 10, seed=42)
        self.maze.generate("recursive_backtracking")

    def test_all_solvers_find_solution(self):
        for algo in self.SOLVERS:
            solution = self.maze.solve(algo)
            self.assertIsNotNone(solution, f"{algo}: should find a solution")
            self.assertEqual(solution[0], self.maze.start,
                              f"{algo}: should start at start")
            self.assertEqual(solution[-1], self.maze.end,
                             f"{algo}: should end at end")

    def test_bfs_finds_shortest_path(self):
        bfs_sol = self.maze.solve("bfs")
        astar_sol = self.maze.solve("astar")
        dijkstra_sol = self.maze.solve("dijkstra")
        bidir_sol = self.maze.solve("bidirectional")
        ida_sol = self.maze.solve("ida_star")
        # All optimal solvers should find the same length.
        self.assertEqual(len(bfs_sol), len(astar_sol))
        self.assertEqual(len(bfs_sol), len(dijkstra_sol))
        self.assertEqual(len(bfs_sol), len(bidir_sol))
        self.assertEqual(len(bfs_sol), len(ida_sol))

    def test_dfs_finds_valid_path(self):
        dfs_sol = self.maze.solve("dfs")
        self.assertIsNotNone(dfs_sol)
        # DFS path should be valid (consecutive cells adjacent and connected).
        for i in range(len(dfs_sol) - 1):
            x1, y1 = dfs_sol[i]
            x2, y2 = dfs_sol[i + 1]
            self.assertEqual(abs(x1 - x2) + abs(y1 - y2), 1,
                             "Path cells must be adjacent")
            c1 = self.maze.cells[y1][x1]
            c2 = self.maze.cells[y2][x2]
            # Wall between them must be removed.
            if x1 == x2:
                if y1 < y2:
                    self.assertNotIn(Direction.SOUTH, c1.walls)
                else:
                    self.assertNotIn(Direction.NORTH, c1.walls)
            else:
                if x1 < x2:
                    self.assertNotIn(Direction.EAST, c1.walls)
                else:
                    self.assertNotIn(Direction.WEST, c1.walls)

    def test_unknown_solver_raises(self):
        with self.assertRaises(ValueError):
            self.maze.solve("nonexistent_solver")

    def test_unknown_heuristic_raises(self):
        with self.assertRaises(ValueError):
            self.maze.solve("astar", heuristic="nonexistent")

    def test_custom_start_end(self):
        solution = self.maze.solve("bfs", start=(0, 0), end=(14, 9))
        self.assertIsNotNone(solution)
        self.assertEqual(solution[0], (0, 0))
        self.assertEqual(solution[-1], (14, 9))

    def test_invalid_coords_raise(self):
        with self.assertRaises((ValueError, TypeError)):
            self.maze.solve("bfs", start=(-1, 0))
        with self.assertRaises((ValueError, TypeError)):
            self.maze.solve("bfs", end=(100, 0))

    def test_ida_star_optimal(self):
        """IDA* should find the same length path as BFS."""
        m = Maze(10, 10, seed=7)
        m.generate("prims")
        bfs_len = len(m.solve("bfs"))
        ida_len = len(m.solve("ida_star"))
        self.assertEqual(bfs_len, ida_len, "IDA* should find optimal path")

    def test_ida_star_small_maze(self):
        """IDA* on a 1x1 maze returns just the start."""
        m = Maze(1, 1)
        m.generate("recursive_backtracking")
        sol = m.solve("ida_star")
        self.assertEqual(sol, [(0, 0)])


class TestBraid(unittest.TestCase):
    """Tests for braid functionality."""

    def test_braid_creates_loops(self):
        m = Maze(10, 10, seed=42)
        m.generate("recursive_backtracking")
        self.assertTrue(m.is_perfect())
        m.braid(1.0)
        self.assertFalse(m.is_perfect(), "Braided maze should have cycles")

    def test_braid_reduces_dead_ends(self):
        m = Maze(10, 10, seed=42)
        m.generate("recursive_backtracking")
        stats_before = analyze_maze(m)
        m.braid(1.0)
        stats_after = analyze_maze(m)
        self.assertLessEqual(
            stats_after["dead_ends"], stats_before["dead_ends"],
            "Braiding should reduce dead ends"
        )

    def test_braid_invalid_probability(self):
        m = Maze(5, 5)
        with self.assertRaises(ValueError):
            m.braid(-0.5)
        with self.assertRaises(ValueError):
            m.braid(1.5)

    def test_braid_probability_0(self):
        m = Maze(10, 10, seed=42)
        m.generate("recursive_backtracking")
        count = m.braid(0.0)
        self.assertEqual(count, 0, "Probability 0 should braid nothing")


class TestSerialization(unittest.TestCase):
    """Tests for JSON serialization."""

    def test_json_round_trip(self):
        m = Maze(15, 10, seed=42)
        m.generate("kruskals")
        m.set_start(0, 0)
        m.set_end(14, 9)
        json_str = m.to_json()
        restored = Maze.from_json(json_str)
        self.assertEqual(restored.width, m.width)
        self.assertEqual(restored.height, m.height)
        self.assertEqual(restored.start, m.start)
        self.assertEqual(restored.end, m.end)
        for y in range(m.height):
            for x in range(m.width):
                self.assertEqual(
                    restored.cells[y][x].walls,
                    m.cells[y][x].walls,
                    f"Walls differ at ({x},{y})"
                )

    def test_save_load_file(self):
        m = Maze(10, 10, seed=42)
        m.generate("ellers")
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            path = f.name
        try:
            m.save(path)
            loaded = Maze.load(path)
            self.assertEqual(loaded.width, m.width)
            self.assertEqual(loaded.height, m.height)
        finally:
            os.unlink(path)

    def test_from_dict_invalid_walls_raises(self):
        with self.assertRaises(ValueError):
            Maze.from_dict({
                "width": 2,
                "height": 2,
                "walls": [
                    [["NORTH", "INVALID"], ["NORTH"]],
                    [["NORTH"], ["NORTH"]],
                ],
            })

    def test_from_dict_wrong_dimensions_raises(self):
        with self.assertRaises(ValueError):
            Maze.from_dict({
                "width": 3,
                "height": 2,
                "walls": [[["NORTH"]], [["NORTH"]]],  # 2x1 not 3x2
            })

    def test_batch_save_load(self):
        mazes = []
        for i in range(3):
            m = Maze(5, 5, seed=i)
            m.generate("recursive_backtracking")
            mazes.append(m)
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            path = f.name
        try:
            save_batch(mazes, path)
            loaded = load_batch(path)
            self.assertEqual(len(loaded), 3)
            for orig, rest in zip(mazes, loaded):
                self.assertEqual(orig.width, rest.width)
        finally:
            os.unlink(path)


class TestValidation(unittest.TestCase):
    """Tests for maze validation."""

    def test_perfect_maze(self):
        m = Maze(10, 10, seed=42)
        m.generate("recursive_backtracking")
        self.assertTrue(m.is_perfect())

    def test_braided_maze_not_perfect(self):
        m = Maze(10, 10, seed=42)
        m.generate("recursive_backtracking")
        m.braid(1.0)
        self.assertFalse(m.is_perfect())

    def test_empty_maze_not_connected(self):
        m = Maze(5, 5)
        # No generation — all walls remain, not connected.
        self.assertFalse(m.is_perfect())

    def test_1x1_is_perfect(self):
        m = Maze(1, 1)
        m.generate("recursive_backtracking")
        self.assertTrue(m.is_perfect())


class TestDistanceMap(unittest.TestCase):
    """Tests for distance map computation."""

    def test_distance_map_start(self):
        m = Maze(10, 5, seed=42)
        m.generate("recursive_backtracking")
        dist = m.distance_map()
        self.assertEqual(dist[0][0], 0, "Start cell should have distance 0")

    def test_distance_map_all_reachable(self):
        m = Maze(10, 5, seed=42)
        m.generate("recursive_backtracking")
        dist = m.distance_map()
        for y in range(m.height):
            for x in range(m.width):
                self.assertGreaterEqual(
                    dist[y][x], 0,
                    f"Cell ({x},{y}) should be reachable"
                )

    def test_distance_map_custom_source(self):
        m = Maze(10, 5, seed=42)
        m.generate("recursive_backtracking")
        dist = m.distance_map(source=(5, 2))
        self.assertEqual(dist[2][5], 0, "Custom source should have distance 0")

    def test_distance_map_invalid_source(self):
        m = Maze(5, 5)
        with self.assertRaises((ValueError, TypeError)):
            m.distance_map(source=(-1, 0))

    def test_distance_map_after_solve(self):
        """Ensure distance_map works correctly after solve()."""
        m = Maze(10, 5, seed=42)
        m.generate("recursive_backtracking")
        m.solve("bfs")
        dist = m.distance_map()
        self.assertEqual(dist[0][0], 0, "Should work after solve()")


class TestWaypoints(unittest.TestCase):
    """Tests for waypoint pathfinding."""

    def test_waypoints_basic(self):
        m = Maze(10, 10, seed=42)
        m.generate("recursive_backtracking")
        path = m.solve_waypoints([(0, 0), (9, 9)])
        self.assertIsNotNone(path)
        self.assertEqual(path[0], (0, 0))
        self.assertEqual(path[-1], (9, 9))

    def test_waypoints_three_points(self):
        m = Maze(15, 10, seed=42)
        m.generate("recursive_backtracking")
        path = m.solve_waypoints([(0, 0), (7, 5), (14, 9)])
        self.assertIsNotNone(path)
        self.assertEqual(path[0], (0, 0))
        self.assertEqual(path[-1], (14, 9))

    def test_waypoints_too_few_raises(self):
        m = Maze(5, 5)
        with self.assertRaises(ValueError):
            m.solve_waypoints([(0, 0)])

    def test_waypoints_unreachable_returns_none(self):
        m = Maze(5, 5)
        # No generation — all walls up, no path possible.
        path = m.solve_waypoints([(0, 0), (4, 4)])
        self.assertIsNone(path)


class TestRender(unittest.TestCase):
    """Tests for ASCII rendering."""

    def test_render_returns_string(self):
        m = Maze(5, 3, seed=42)
        m.generate("recursive_backtracking")
        s = m.render()
        self.assertIsInstance(s, str)
        self.assertIn("+", s)
        self.assertIn("|", s)
        self.assertIn("-", s)

    def test_render_with_solution(self):
        m = Maze(10, 5, seed=42)
        m.generate("recursive_backtracking")
        sol = m.solve("bfs")
        s = m.render(solution=sol)
        self.assertIn("·", s)
        self.assertIn("S", s)
        self.assertIn("E", s)

    def test_render_no_start_end(self):
        m = Maze(5, 3, seed=42)
        m.generate("recursive_backtracking")
        s = m.render(mark_start_end=False)
        self.assertNotIn("S", s)
        self.assertNotIn("E", s)

    def test_render_distance_map_returns_string(self):
        m = Maze(5, 3, seed=42)
        m.generate("recursive_backtracking")
        s = m.render_distance_map()
        self.assertIsInstance(s, str)

    def test_render_distance_map_empty_maze(self):
        m = Maze(3, 3)
        # No generation, all walls — only source reachable.
        s = m.render_distance_map()
        self.assertIsInstance(s, str)


class TestPNG(unittest.TestCase):
    """Tests for PNG export."""

    def test_png_export(self):
        m = Maze(10, 5, seed=42)
        m.generate("recursive_backtracking")
        with tempfile.NamedTemporaryFile(
            suffix=".png", delete=False
        ) as f:
            path = f.name
        try:
            m.to_png(path)
            self.assertTrue(os.path.getsize(path) > 0)
            with open(path, "rb") as pf:
                sig = pf.read(8)
            self.assertEqual(sig, b"\x89PNG\r\n\x1a\n")
        finally:
            os.unlink(path)

    def test_png_with_solution(self):
        m = Maze(10, 5, seed=42)
        m.generate("recursive_backtracking")
        sol = m.solve("bfs")
        with tempfile.NamedTemporaryFile(
            suffix=".png", delete=False
        ) as f:
            path = f.name
        try:
            m.to_png(path, solution=sol)
            self.assertTrue(os.path.getsize(path) > 0)
        finally:
            os.unlink(path)

    def test_png_invalid_cell_size(self):
        m = Maze(5, 5)
        with self.assertRaises(ValueError):
            m.to_png("/tmp/test.png", cell_size=0)

    def test_png_invalid_wall_thickness(self):
        m = Maze(5, 5)
        with self.assertRaises(ValueError):
            m.to_png("/tmp/test.png", wall_thickness=0)


class TestSVG(unittest.TestCase):
    """Tests for SVG export."""

    def test_svg_export(self):
        m = Maze(10, 5, seed=42)
        m.generate("recursive_backtracking")
        with tempfile.NamedTemporaryFile(
            suffix=".svg", delete=False
        ) as f:
            path = f.name
        try:
            m.to_svg(path)
            self.assertTrue(os.path.getsize(path) > 0)
            with open(path, "r") as sf:
                content = sf.read()
            self.assertIn("<svg", content)
            self.assertIn("</svg>", content)
            self.assertIn("stroke", content)
        finally:
            os.unlink(path)

    def test_svg_with_solution(self):
        m = Maze(10, 5, seed=42)
        m.generate("recursive_backtracking")
        sol = m.solve("bfs")
        with tempfile.NamedTemporaryFile(
            suffix=".svg", delete=False
        ) as f:
            path = f.name
        try:
            m.to_svg(path, solution=sol)
            with open(path, "r") as sf:
                content = sf.read()
            self.assertIn("polyline", content)
        finally:
            os.unlink(path)

    def test_svg_invalid_cell_size(self):
        m = Maze(5, 5)
        with self.assertRaises(ValueError):
            m.to_svg("/tmp/test.svg", cell_size=0)


class TestBenchmark(unittest.TestCase):
    """Tests for benchmarking."""

    def test_benchmark_all_solvers(self):
        m = Maze(10, 10, seed=42)
        m.generate("recursive_backtracking")
        results = m.benchmark()
        self.assertEqual(len(results), len(SOLVER_NAMES))
        for r in results:
            self.assertIn("algorithm", r)
            self.assertIn("path_length", r)
            self.assertIn("found", r)
            self.assertIn("explored", r)
            self.assertIn("time_ms", r)

    def test_benchmark_subset(self):
        m = Maze(10, 10, seed=42)
        m.generate("recursive_backtracking")
        results = m.benchmark(algorithms=["bfs", "dfs"])
        self.assertEqual(len(results), 2)

    def test_benchmark_explored_count_correct(self):
        m = Maze(10, 10, seed=42)
        m.generate("recursive_backtracking")
        results = m.benchmark()
        for r in results:
            if r["found"]:
                self.assertGreater(
                    r["explored"], 0,
                    f"{r['algorithm']}: explored should be > 0 for found solutions"
                )

    def test_benchmark_unknown_solver_raises(self):
        m = Maze(5, 5)
        with self.assertRaises(ValueError):
            m.benchmark(algorithms=["nonexistent"])


class TestDifficultyScore(unittest.TestCase):
    """Tests for difficulty scoring."""

    def test_difficulty_returns_float(self):
        m = Maze(10, 10, seed=42)
        m.generate("recursive_backtracking")
        score = difficulty_score(m)
        self.assertIsInstance(score, float)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 100.0)

    def test_trivial_maze_low_difficulty(self):
        """A 1xN maze (trivially solvable) should have low difficulty."""
        m = Maze(1, 20, seed=42)
        m.generate("binary_tree")
        score = difficulty_score(m)
        self.assertLess(score, 50.0, "Trivial maze should have low difficulty")

    def test_complex_maze_higher_difficulty(self):
        """A complex maze should score higher than a trivial one."""
        trivial = Maze(1, 20, seed=42)
        trivial.generate("binary_tree")
        complex_m = Maze(20, 20, seed=42)
        complex_m.generate("recursive_backtracking")
        self.assertGreater(
            difficulty_score(complex_m),
            difficulty_score(trivial),
            "Complex maze should have higher difficulty"
        )

    def test_difficulty_in_analyze(self):
        m = Maze(10, 10, seed=42)
        m.generate("recursive_backtracking")
        stats = analyze_maze(m)
        self.assertIn("difficulty_score", stats)


class TestCompareMazes(unittest.TestCase):
    """Tests for maze comparison."""

    def test_compare_same_maze(self):
        m1 = Maze(10, 10, seed=42)
        m1.generate("recursive_backtracking")
        m2 = Maze(10, 10, seed=42)
        m2.generate("recursive_backtracking")
        result = compare_mazes(m1, m2)
        self.assertTrue(result["same_dimensions"])
        self.assertEqual(result["wall_diff_count"], 0)
        self.assertEqual(result["same_walls"], 100)

    def test_compare_different_mazes(self):
        m1 = Maze(10, 10, seed=42)
        m1.generate("recursive_backtracking")
        m2 = Maze(10, 10, seed=99)
        m2.generate("prims")
        result = compare_mazes(m1, m2)
        self.assertTrue(result["same_dimensions"])
        self.assertGreater(result["wall_diff_count"], 0)

    def test_compare_different_dimensions(self):
        m1 = Maze(10, 10, seed=42)
        m1.generate("recursive_backtracking")
        m2 = Maze(5, 5, seed=42)
        m2.generate("recursive_backtracking")
        result = compare_mazes(m1, m2)
        self.assertFalse(result["same_dimensions"])


class TestConfigLoading(unittest.TestCase):
    """Tests for configuration file loading."""

    def test_load_config_json(self):
        config_data = {
            "width": 15,
            "height": 10,
            "seed": 42,
            "generator": "prims",
            "braid": 0.5,
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(config_data, f)
            path = f.name
        try:
            config = load_config_json(path)
            self.assertEqual(config["width"], 15)
            self.assertEqual(config["generator"], "prims")
            self.assertEqual(config["braid"], 0.5)
        finally:
            os.unlink(path)

    def test_maze_from_config(self):
        config = {
            "width": 12,
            "height": 8,
            "seed": 42,
            "generator": "kruskals",
        }
        m = maze_from_config(config)
        self.assertEqual(m.width, 12)
        self.assertEqual(m.height, 8)
        sol = m.solve("bfs")
        self.assertIsNotNone(sol, "Config-generated maze should be solvable")

    def test_maze_from_config_with_braid(self):
        config = {
            "width": 12,
            "height": 8,
            "seed": 42,
            "generator": "recursive_backtracking",
            "braid": 1.0,
        }
        m = maze_from_config(config)
        self.assertFalse(m.is_perfect(), "Braided maze should not be perfect")

    def test_maze_from_config_with_custom_start_end(self):
        config = {
            "width": 10,
            "height": 10,
            "seed": 42,
            "generator": "prims",
            "start": [0, 0],
            "end": [9, 9],
        }
        m = maze_from_config(config)
        self.assertEqual(m.start, (0, 0))
        self.assertEqual(m.end, (9, 9))


class TestCLI(unittest.TestCase):
    """Tests for the CLI interface."""

    def test_cli_generate_no_display(self):
        from maze_solver.cli import main
        main(["--no-display", "--seed", "42", "-W", "5", "-H", "5"])

    def test_cli_solve(self):
        from maze_solver.cli import main
        main(["--solve", "--seed", "42", "-W", "5", "-H", "5", "--no-display"])

    def test_cli_analyze(self):
        from maze_solver.cli import main
        main(["--analyze", "--seed", "42", "-W", "5", "-H", "5", "--no-display"])

    def test_cli_benchmark(self):
        from maze_solver.cli import main
        main(["--benchmark", "--seed", "42", "-W", "5", "-H", "5", "--no-display"])

    def test_cli_difficulty(self):
        from maze_solver.cli import main
        main(["--difficulty", "--seed", "42", "-W", "5", "-H", "5", "--no-display"])

    def test_cli_validate(self):
        from maze_solver.cli import main
        main(["--validate", "--seed", "42", "-W", "5", "-H", "5", "--no-display"])

    def test_cli_all_generators(self):
        from maze_solver.cli import main
        for g in GENERATOR_NAMES:
            main(["-g", g, "--no-display", "-W", "5", "-H", "5", "--seed", "42"])

    def test_cli_save_load(self):
        from maze_solver.cli import main
        with tempfile.NamedTemporaryFile(
            suffix=".json", delete=False
        ) as f:
            path = f.name
        try:
            main(["--save", path, "--no-display", "-W", "5", "-H", "5", "--seed", "42"])
            self.assertTrue(os.path.getsize(path) > 0)
            main(["--load", path, "--no-display"])
        finally:
            os.unlink(path)

    def test_cli_config_file(self):
        from maze_solver.cli import main
        config_data = {
            "width": 8,
            "height": 5,
            "seed": 42,
            "generator": "prims",
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(config_data, f)
            path = f.name
        try:
            main(["--config", path, "--no-display", "--validate"])
        finally:
            os.unlink(path)


class TestEdgeCases(unittest.TestCase):
    """Tests for edge cases."""

    def test_1xN_maze_all_generators(self):
        for algo in GENERATOR_NAMES:
            m = Maze(1, 10, seed=42)
            m.generate(algo)
            sol = m.solve("bfs")
            self.assertIsNotNone(sol, f"{algo}: 1x10 should be solvable")

    def test_2x2_maze_all_generators(self):
        for algo in GENERATOR_NAMES:
            m = Maze(2, 2, seed=42)
            m.generate(algo)
            self.assertTrue(m.is_perfect(), f"{algo}: 2x2 should be perfect")

    def test_Nx1_maze_all_generators(self):
        for algo in GENERATOR_NAMES:
            m = Maze(10, 1, seed=42)
            m.generate(algo)
            sol = m.solve("bfs")
            self.assertIsNotNone(sol, f"{algo}: 10x1 should be solvable")

    def test_accessible_neighbors_respects_walls(self):
        m = Maze(3, 3, seed=42)
        m.generate("recursive_backtracking")
        cell = m.cells[1][1]
        for n in m.accessible_neighbors(cell):
            # No wall between cell and accessible neighbor.
            if n.x == cell.x:
                if n.y < cell.y:
                    self.assertNotIn(Direction.NORTH, cell.walls)
                else:
                    self.assertNotIn(Direction.SOUTH, cell.walls)
            else:
                if n.x < cell.x:
                    self.assertNotIn(Direction.WEST, cell.walls)
                else:
                    self.assertNotIn(Direction.EAST, cell.walls)

    def test_analyze_returns_dict(self):
        m = Maze(10, 5, seed=42)
        m.generate("recursive_backtracking")
        stats = m.analyze()
        self.assertIsInstance(stats, dict)
        self.assertIn("dead_ends", stats)
        self.assertIn("corridors", stats)
        self.assertIn("junctions", stats)
        self.assertIn("difficulty_score", stats)

    def test_large_maze_performance(self):
        """Generate and solve a large maze in reasonable time."""
        import time
        m = Maze(50, 50, seed=42)
        m.generate("recursive_backtracking")
        t0 = time.perf_counter()
        sol = m.solve("bfs")
        elapsed = time.perf_counter() - t0
        self.assertIsNotNone(sol)
        self.assertLess(elapsed, 2.0, "50x50 BFS should complete in < 2s")


if __name__ == "__main__":
    unittest.main()