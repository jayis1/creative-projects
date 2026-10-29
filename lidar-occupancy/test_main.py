import math
import unittest

from main import Grid


class GridTests(unittest.TestCase):
    def test_world_coordinates_and_bresenham_octants(self):
        grid = Grid.create(7, 7, origin_x=-3, origin_y=-3)
        expected = [(-3, -2), (-2, -1), (-1, 0), (0, 1), (1, 2), (2, 3)]
        for endpoint in ((2, 3), (3, 2), (3, -2), (2, -3), (-2, -3), (-3, -2), (-3, 2), (-2, 3)):
            cells = grid._bresenham((3, 3), (3 + endpoint[0], 3 + endpoint[1]))
            self.assertEqual(cells[0], (3, 3))
            self.assertEqual(cells[-1], (3 + endpoint[0], 3 + endpoint[1]))
            self.assertLessEqual(max(max(abs(a[0]-b[0]), abs(a[1]-b[1])) for a,b in zip(cells,cells[1:])), 1)
        self.assertEqual(grid.world_to_cell(-3, -3), (0, 0))
        self.assertIsNone(grid.world_to_cell(4, 0))

    def test_ray_marks_intermediate_free_and_endpoint_occupied(self):
        grid = Grid.create(6, 2)
        grid.trace_ray((0.2, 0.2), (4.2, 0.2))
        self.assertEqual(grid.cells[0][:5], [-0.4, -0.4, -0.4, -0.4, 0.85])

    def test_miss_marks_endpoint_free(self):
        grid = Grid.create(3, 1)
        grid.trace_ray((0.2, 0.2), (2.2, 0.2), hit=False)
        self.assertEqual(grid.cells[0], [-0.4, -0.4, -0.4])

    def test_rejects_invalid_dimensions_and_coordinates(self):
        for args in ((0, 1), (1, -1), (2001, 1000)):
            with self.assertRaises(ValueError):
                Grid.create(*args)
        grid = Grid.create(2, 2)
        with self.assertRaises(ValueError):
            grid.world_to_cell(math.nan, 0)
        with self.assertRaises(ValueError):
            Grid.create(2, 2, resolution=math.inf)

    def test_repeated_updates_are_clamped(self):
        grid = Grid.create(1, 1)
        for _ in range(20):
            grid.trace_ray((0.1, 0.1), (0.1, 0.1))
        self.assertEqual(grid.cells[0][0], 5.0)


if __name__ == "__main__":
    unittest.main()
