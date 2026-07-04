"""
Bug hunt tests for maze-generator-solver.

Each test verifies a specific bug before it's fixed, then the fix is applied.
Run with: python3 -m pytest test_maze.py -v
or:  python3 test_maze.py
"""

import json
import os
import sys
import tempfile
import unittest

# Make the module importable.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from maze import (
    Cell,
    Direction,
    Maze,
    manhattan_distance,
    euclidean_distance,
    chebyshev_distance,
    _write_png,
)


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

    def test_1x1_maze(self):
        m = Maze(1, 1)
        m.generate("recursive_backtracking")
        # A 1×1 maze has no passages — all walls remain.
        cell = m.get_cell(0, 0)
        self.assertEqual(len(cell.walls), 4)

    def test_start_end_defaults(self):
        m = Maze(10, 5)
        self.assertEqual(m.start, (0, 0))
        self.assertEqual(m.end, (9, 4))

    def test_set_start_end_validation(self):
        m = Maze(10, 5)
        with self.assertRaises(ValueError):
            m.set_start(-1, 0)
        with self.assertRaises(ValueError):
            m.set_start(10, 0)
        with self.assertRaises(ValueError):
            m.set_end(0, 5)
        m.set_start(5, 2)
        m.set_end(9, 4)
        self.assertEqual(m.start, (5, 2))
        self.assertEqual(m.end, (9, 4))


class TestGeneration(unittest.TestCase):
    """Tests for all generation algorithms."""

    GENERATORS = [
        "recursive_backtracking",
        "prims",
        "kruskals",
        "ellers",
        "wilsons",
        "binary_tree",
        "sidewinder",
    ]

    def test_all_generators_produce_perfect_mazes(self):
        """Every generator should produce a perfect maze (spanning tree)."""
        for algo in self.GENERATORS:
            with self.subTest(algorithm=algo):
                m = Maze(8, 6, seed=42)
                m.generate(algo)
                self.assertTrue(
                    m.is_perfect(),
                    f"{algo} did not produce a perfect maze",
                )

    def test_all_generators_solvable(self):
        """Every generator should produce a solvable maze."""
        for algo in self.GENERATORS:
            with self.subTest(algorithm=algo):
                m = Maze(8, 6, seed=42)
                m.generate(algo)
                sol = m.solve("bfs")
                self.assertIsNotNone(sol, f"{algo} produced unsolvable maze")
                self.assertEqual(sol[0], (0, 0))
                self.assertEqual(sol[-1], (7, 5))

    def test_reproducibility_with_seed(self):
        """Same seed produces same maze."""
        m1 = Maze(10, 5, seed=123)
        m1.generate("recursive_backtracking")
        m2 = Maze(10, 5, seed=123)
        m2.generate("recursive_backtracking")
        for y in range(5):
            for x in range(10):
                self.assertEqual(
                    m1.cells[y][x].walls,
                    m2.cells[y][x].walls,
                    f"Walls differ at ({x},{y})",
                )

    def test_unknown_algorithm_raises(self):
        m = Maze(5, 5)
        with self.assertRaises(ValueError):
            m.generate("nonexistent_algorithm")

    def test_remove_wall_non_adjacent_raises(self):
        m = Maze(5, 5)
        with self.assertRaises(ValueError):
            m.remove_wall(m.get_cell(0, 0), m.get_cell(2, 2))

    def test_add_wall(self):
        m = Maze(3, 3)
        a = m.get_cell(0, 0)
        b = m.get_cell(1, 0)
        m.remove_wall(a, b)
        self.assertNotIn(Direction.EAST, a.walls)
        m.add_wall(a, b)
        self.assertIn(Direction.EAST, a.walls)


class TestSolving(unittest.TestCase):
    """Tests for solving algorithms."""

    SOLVERS = ["bfs", "dfs", "astar", "dijkstra", "bidirectional", "greedy"]

    def setUp(self):
        self.maze = Maze(10, 8, seed=42)
        self.maze.generate("recursive_backtracking")

    def test_all_solvers_find_path(self):
        for solver in self.SOLVERS:
            with self.subTest(solver=solver):
                sol = self.maze.solve(solver)
                self.assertIsNotNone(sol, f"{solver} found no solution")
                self.assertEqual(sol[0], (0, 0))
                self.assertEqual(sol[-1], (9, 7))

    def test_bfs_finds_shortest_path(self):
        """BFS must find the shortest path."""
        bfs_sol = self.maze.solve("bfs")
        # Compare with A* (also optimal).
        astar_sol = self.maze.solve("astar")
        self.assertEqual(len(bfs_sol), len(astar_sol))

    def test_astar_finds_shortest_path(self):
        """A* must find the shortest path (same length as BFS)."""
        bfs_sol = self.maze.solve("bfs")
        for h in ["manhattan", "euclidean", "chebyshev"]:
            with self.subTest(heuristic=h):
                astar_sol = self.maze.solve("astar", heuristic=h)
                self.assertEqual(len(astar_sol), len(bfs_sol))

    def test_dijkstra_finds_shortest_path(self):
        bfs_sol = self.maze.solve("bfs")
        dij_sol = self.maze.solve("dijkstra")
        self.assertEqual(len(dij_sol), len(bfs_sol))

    def test_bidirectional_finds_shortest_path(self):
        bfs_sol = self.maze.solve("bfs")
        bi_sol = self.maze.solve("bidirectional")
        self.assertEqual(len(bi_sol), len(bfs_sol))

    def test_dfs_finds_valid_path(self):
        """DFS finds a path (not necessarily shortest)."""
        dfs_sol = self.maze.solve("dfs")
        bfs_sol = self.maze.solve("bfs")
        self.assertIsNotNone(dfs_sol)
        # DFS path is at least as long as BFS.
        self.assertGreaterEqual(len(dfs_sol), len(bfs_sol))

    def test_path_is_valid(self):
        """Solution path must consist of adjacent, connected cells."""
        for solver in self.SOLVERS:
            with self.subTest(solver=solver):
                sol = self.maze.solve(solver)
                self.assertIsNotNone(sol)
                for i in range(len(sol) - 1):
                    x1, y1 = sol[i]
                    x2, y2 = sol[i + 1]
                    # Must be adjacent (Manhattan distance 1).
                    self.assertEqual(
                        abs(x1 - x2) + abs(y1 - y2), 1,
                        f"{solver}: non-adjacent cells in path at step {i}",
                    )
                    # Must not have a wall between them.
                    cell1 = self.maze.get_cell(x1, y1)
                    cell2 = self.maze.get_cell(x2, y2)
                    # Determine which direction.
                    if x2 > x1:
                        self.assertNotIn(Direction.EAST, cell1.walls)
                    elif x2 < x1:
                        self.assertNotIn(Direction.WEST, cell1.walls)
                    elif y2 > y1:
                        self.assertNotIn(Direction.SOUTH, cell1.walls)
                    elif y2 < y1:
                        self.assertNotIn(Direction.NORTH, cell1.walls)

    def test_custom_start_end(self):
        sol = self.maze.solve("bfs", start=(9, 0), end=(0, 7))
        self.assertIsNotNone(sol)
        self.assertEqual(sol[0], (9, 0))
        self.assertEqual(sol[-1], (0, 7))

    def test_invalid_start_raises(self):
        with self.assertRaises(ValueError):
            self.maze.solve("bfs", start=(-1, 0))

    def test_invalid_end_raises(self):
        with self.assertRaises(ValueError):
            self.maze.solve("bfs", end=(100, 0))

    def test_unknown_solver_raises(self):
        with self.assertRaises(ValueError):
            self.maze.solve("nonexistent")

    def test_unknown_heuristic_raises(self):
        with self.assertRaises(ValueError):
            self.maze.solve("astar", heuristic="nonexistent")

    def test_start_equals_end(self):
        sol = self.maze.solve("bfs", start=(5, 5), end=(5, 5))
        self.assertEqual(sol, [(5, 5)])

    def test_bidirectional_start_equals_end(self):
        sol = self.maze.solve("bidirectional", start=(5, 5), end=(5, 5))
        self.assertEqual(sol, [(5, 5)])

    def test_solve_restores_start_end(self):
        """solve() with temporary start/end should restore originals."""
        original_start = self.maze.start
        original_end = self.maze.end
        self.maze.solve("bfs", start=(3, 3), end=(7, 7))
        self.assertEqual(self.maze.start, original_start)
        self.assertEqual(self.maze.end, original_end)


class TestHeuristics(unittest.TestCase):
    """Tests for heuristic functions."""

    def test_manhattan(self):
        a = Cell(0, 0)
        b = Cell(3, 4)
        self.assertEqual(manhattan_distance(a, b), 7)

    def test_euclidean(self):
        a = Cell(0, 0)
        b = Cell(3, 4)
        self.assertEqual(euclidean_distance(a, b), 5.0)

    def test_chebyshev(self):
        a = Cell(0, 0)
        b = Cell(3, 4)
        self.assertEqual(chebyshev_distance(a, b), 4)


class TestBraid(unittest.TestCase):
    """Tests for braid functionality."""

    def test_braid_reduces_dead_ends(self):
        m = Maze(10, 8, seed=42)
        m.generate("recursive_backtracking")
        stats_before = m.analyze()
        m.braid(1.0)
        stats_after = m.analyze()
        self.assertLessEqual(stats_after["dead_ends"], stats_before["dead_ends"])

    def test_braid_probability_0(self):
        m = Maze(10, 8, seed=42)
        m.generate("recursive_backtracking")
        stats_before = m.analyze()
        m.braid(0.0)
        stats_after = m.analyze()
        self.assertEqual(stats_before["dead_ends"], stats_after["dead_ends"])

    def test_braid_invalid_probability(self):
        m = Maze(5, 5)
        with self.assertRaises(ValueError):
            m.braid(-0.1)
        with self.assertRaises(ValueError):
            m.braid(1.5)

    def test_braid_creates_loops(self):
        """Braiding with probability 1.0 should make is_perfect False."""
        m = Maze(10, 8, seed=42)
        m.generate("recursive_backtracking")
        self.assertTrue(m.is_perfect())
        m.braid(1.0)
        self.assertFalse(m.is_perfect())


class TestSerialization(unittest.TestCase):
    """Tests for JSON serialization."""

    def test_json_round_trip(self):
        m = Maze(10, 8, seed=42)
        m.generate("kruskals")
        m.set_start(2, 3)
        m.set_end(7, 5)
        json_str = m.to_json()
        m2 = Maze.from_json(json_str)
        self.assertEqual(m2.width, m.width)
        self.assertEqual(m2.height, m.height)
        self.assertEqual(m2.seed, m.seed)
        self.assertEqual(m2.start, m.start)
        self.assertEqual(m2.end, m.end)
        for y in range(m.height):
            for x in range(m.width):
                self.assertEqual(
                    m.cells[y][x].walls, m2.cells[y][x].walls,
                    f"Walls differ at ({x},{y})",
                )

    def test_save_load_file(self):
        m = Maze(8, 5, seed=7)
        m.generate("prims")
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            path = f.name
        try:
            m.save(path)
            m2 = Maze.load(path)
            self.assertEqual(m2.width, m.width)
            self.assertEqual(m2.height, m.height)
            for y in range(m.height):
                for x in range(m.width):
                    self.assertEqual(
                        m.cells[y][x].walls, m2.cells[y][x].walls,
                    )
        finally:
            os.unlink(path)

    def test_from_dict_invalid_walls_raises(self):
        """Loading a dict with wrong wall dimensions should raise."""
        data = {"width": 3, "height": 3, "seed": None,
                "start": [0, 0], "end": [2, 2],
                "walls": [[[["NORTH"]] for _ in range(3)] for _ in range(3)]}
        # This should raise because wall names might be invalid or
        # dimensions mismatch.
        with self.assertRaises((KeyError, ValueError, TypeError)):
            Maze.from_dict(data)


class TestValidation(unittest.TestCase):
    """Tests for maze validation."""

    def test_perfect_maze(self):
        m = Maze(8, 6, seed=42)
        m.generate("recursive_backtracking")
        self.assertTrue(m.is_perfect())

    def test_braided_maze_not_perfect(self):
        m = Maze(8, 6, seed=42)
        m.generate("recursive_backtracking")
        m.braid(1.0)
        self.assertFalse(m.is_perfect())

    def test_empty_maze_not_connected(self):
        """A maze with no walls removed is not connected (except 1x1)."""
        m = Maze(3, 3)
        # No generation — all walls present.
        self.assertFalse(m.is_perfect())

    def test_1x1_is_perfect(self):
        """A 1×1 maze is trivially perfect (1 node, 0 edges = spanning tree)."""
        m = Maze(1, 1)
        m.generate("recursive_backtracking")
        self.assertTrue(m.is_perfect())


class TestDistanceMap(unittest.TestCase):
    """Tests for distance map."""

    def test_distance_map_start(self):
        m = Maze(8, 6, seed=42)
        m.generate("recursive_backtracking")
        dist = m.distance_map()
        self.assertEqual(dist[0][0], 0)

    def test_distance_map_all_reachable(self):
        """In a perfect maze, all cells should be reachable."""
        m = Maze(8, 6, seed=42)
        m.generate("recursive_backtracking")
        dist = m.distance_map()
        for y in range(m.height):
            for x in range(m.width):
                self.assertGreaterEqual(dist[y][x], 0,
                                        f"Cell ({x},{y}) is unreachable")

    def test_distance_map_custom_source(self):
        m = Maze(8, 6, seed=42)
        m.generate("recursive_backtracking")
        dist = m.distance_map(source=(4, 3))
        self.assertEqual(dist[3][4], 0)

    def test_distance_map_invalid_source(self):
        m = Maze(5, 5)
        with self.assertRaises(ValueError):
            m.distance_map(source=(-1, 0))


class TestWaypoints(unittest.TestCase):
    """Tests for waypoint pathfinding."""

    def test_waypoints_basic(self):
        m = Maze(10, 8, seed=42)
        m.generate("recursive_backtracking")
        path = m.solve_waypoints([(0, 0), (9, 7)], "bfs")
        self.assertIsNotNone(path)
        self.assertEqual(path[0], (0, 0))
        self.assertEqual(path[-1], (9, 7))

    def test_waypoints_three_points(self):
        m = Maze(10, 8, seed=42)
        m.generate("recursive_backtracking")
        path = m.solve_waypoints([(0, 0), (5, 4), (9, 7)], "bfs")
        self.assertIsNotNone(path)
        self.assertEqual(path[0], (0, 0))
        self.assertEqual(path[-1], (9, 7))

    def test_waypoints_too_few_raises(self):
        m = Maze(5, 5)
        with self.assertRaises(ValueError):
            m.solve_waypoints([(0, 0)])

    def test_waypoints_unreachable_returns_none(self):
        """If any segment is unreachable, return None."""
        m = Maze(5, 5)
        # No generation — all walls intact, so no path exists.
        path = m.solve_waypoints([(0, 0), (4, 4)], "bfs")
        self.assertIsNone(path)


class TestRender(unittest.TestCase):
    """Tests for rendering."""

    def test_render_returns_string(self):
        m = Maze(5, 3, seed=1)
        m.generate("recursive_backtracking")
        s = m.render()
        self.assertIsInstance(s, str)
        lines = s.split("\n")
        # Grid is (5*2+1) x (3*2+1) = 11 x 7
        self.assertEqual(len(lines), 7)
        self.assertEqual(len(lines[0]), 11)

    def test_render_with_solution(self):
        m = Maze(5, 3, seed=1)
        m.generate("recursive_backtracking")
        sol = m.solve("bfs")
        s = m.render(solution=sol)
        self.assertIn("S", s)
        self.assertIn("E", s)
        self.assertIn("·", s)

    def test_render_no_start_end(self):
        m = Maze(5, 3, seed=1)
        m.generate("recursive_backtracking")
        s = m.render(mark_start_end=False)
        self.assertNotIn("S", s)
        self.assertNotIn("E", s)


class TestPNG(unittest.TestCase):
    """Tests for PNG export."""

    def test_png_export(self):
        m = Maze(5, 3, seed=1)
        m.generate("recursive_backtracking")
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            path = f.name
        try:
            m.to_png(path)
            self.assertTrue(os.path.exists(path))
            with open(path, "rb") as f:
                header = f.read(8)
            # PNG signature.
            self.assertEqual(header, b"\x89PNG\r\n\x1a\n")
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


class TestBenchmark(unittest.TestCase):
    """Tests for benchmarking."""

    def test_benchmark_all_solvers(self):
        m = Maze(10, 8, seed=42)
        m.generate("recursive_backtracking")
        results = m.benchmark()
        self.assertEqual(len(results), len(m.SOLVERS))
        for r in results:
            self.assertIn("algorithm", r)
            self.assertIn("path_length", r)
            self.assertIn("found", r)
            self.assertIn("explored", r)
            self.assertIn("time_ms", r)

    def test_benchmark_subset(self):
        m = Maze(10, 8, seed=42)
        m.generate("recursive_backtracking")
        results = m.benchmark(["bfs", "astar"])
        self.assertEqual(len(results), 2)

    def test_benchmark_explored_count_correct(self):
        """BUG #7: explored count must be > 0 for all solvers.

        A*, Dijkstra, greedy, and bidirectional use their own visited
        sets instead of cell.visited, so the explored count was always 0.
        After the fix, all solvers should report explored > 0.
        """
        m = Maze(10, 8, seed=42)
        m.generate("recursive_backtracking")
        results = m.benchmark()
        for r in results:
            self.assertGreater(
                r["explored"], 0,
                f"{r['algorithm']}: explored count should be > 0",
            )


class TestRenderDistanceMap(unittest.TestCase):
    """Tests for distance heatmap rendering."""

    def test_render_distance_map_returns_string(self):
        m = Maze(5, 3, seed=1)
        m.generate("recursive_backtracking")
        s = m.render_distance_map()
        self.assertIsInstance(s, str)

    def test_render_distance_map_empty_maze(self):
        """BUG #1: render_distance_map crashes when no cells are reachable.

        max() on an empty generator raises ValueError when all distances
        are -1 (disconnected maze). After fix, it should handle gracefully.
        """
        m = Maze(3, 3)
        # No generation — all walls intact → only source is reachable.
        # distance_map from (0,0) will have only (0,0) at distance 0.
        # But this shouldn't crash.
        s = m.render_distance_map()
        self.assertIsInstance(s, str)


class TestEdgeCases(unittest.TestCase):
    """Tests for edge cases."""

    def test_2x2_maze_all_generators(self):
        for algo in TestGeneration.GENERATORS:
            with self.subTest(algorithm=algo):
                m = Maze(2, 2, seed=42)
                m.generate(algo)
                self.assertTrue(m.is_perfect(), f"{algo} failed on 2×2")

    def test_1xN_maze_all_generators(self):
        for algo in TestGeneration.GENERATORS:
            with self.subTest(algorithm=algo):
                m = Maze(5, 1, seed=42)
                m.generate(algo)
                self.assertTrue(m.is_perfect(), f"{algo} failed on 5×1")

    def test_Nx1_maze_all_generators(self):
        for algo in TestGeneration.GENERATORS:
            with self.subTest(algorithm=algo):
                m = Maze(1, 5, seed=42)
                m.generate(algo)
                self.assertTrue(m.is_perfect(), f"{algo} failed on 1×5")

    def test_analyze_returns_dict(self):
        m = Maze(8, 6, seed=42)
        m.generate("recursive_backtracking")
        stats = m.analyze()
        self.assertIsInstance(stats, dict)
        self.assertIn("dead_ends", stats)
        self.assertIn("junctions", stats)
        self.assertIn("is_perfect", stats)
        self.assertIn("braid_ratio", stats)

    def test_accessible_neighbors_respects_walls(self):
        m = Maze(3, 3)
        # No walls removed — no accessible neighbors.
        cell = m.get_cell(1, 1)
        self.assertEqual(len(m.accessible_neighbors(cell)), 0)
        # Remove one wall.
        m.remove_wall(m.get_cell(1, 1), m.get_cell(2, 1))
        self.assertEqual(len(m.accessible_neighbors(cell)), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)