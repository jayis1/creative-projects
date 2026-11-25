import math
import unittest

from planner import Grid, find_path


class AStarTests(unittest.TestCase):
    def test_open_diagonal_is_optimal(self):
        route = find_path(Grid.from_rows([[1] * 4 for _ in range(4)]), (0, 0), (3, 3))
        self.assertAlmostEqual(route.cost, 3 * math.sqrt(2))
        self.assertEqual(route.points[0], (0, 0))
        self.assertEqual(route.points[-1], (3, 3))

    def test_weighted_detour(self):
        grid = Grid.from_rows([[1, 9, 1], [1, 9, 1], [1, 1, 1]])
        route = find_path(grid, (0, 0), (2, 0))
        self.assertTrue(all(x != 1 or y == 2 for x, y in route.points))

    def test_blocked_corner_and_unreachable(self):
        grid = Grid.from_rows([[1, None], [None, 1]])
        self.assertIsNone(find_path(grid, (0, 0), (1, 1)))

    def test_invalid_grids_and_endpoints(self):
        for data in ([], [[1], [1, 2]], [[0]], [[float('inf')]]):
            with self.assertRaises(ValueError):
                Grid.from_rows(data)
        grid = Grid.from_rows([[1, None]])
        with self.assertRaises(ValueError):
            find_path(grid, (0, 0), (1, 0))

    def test_identical_endpoints(self):
        self.assertEqual(find_path(Grid.from_rows([[1]]), (0, 0), (0, 0)).points, ((0, 0),))

    def test_tiny_positive_terrain_is_supported(self):
        grid = Grid.from_rows([[1e-15, 1e-15, 1e-15]])
        route = find_path(grid, (0, 0), (2, 0))
        self.assertIsNotNone(route)
        self.assertAlmostEqual(route.cost, 2e-15, places=29)


if __name__ == '__main__':
    unittest.main()
