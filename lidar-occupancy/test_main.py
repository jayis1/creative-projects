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

    def test_scan_range_clipping_and_json_summary(self):
        import json
        grid = Grid.create(7, 3, origin_x=-1, origin_y=-1)
        grid.integrate_scan((0.1, 0.1), [(0.0, 2.1), (math.pi / 2, 99.0)], max_range=3.0)
        self.assertGreater(grid.cells[1][3], 0)
        self.assertLess(grid.cells[1][2], 0)
        self.assertLess(grid.cells[2][1], 0)
        summary = grid.summary()
        self.assertEqual(summary["occupied"], 1)
        self.assertGreater(summary["free"], 0)
        payload = json.loads(grid.to_json())
        self.assertEqual(payload["width"], 7)
        self.assertEqual(payload["origin"], [-1, -1])

    def test_scan_rejects_invalid_ranges_and_caps_beam_count(self):
        grid = Grid.create(3, 3)
        for beams, limit in [([(0.0, -1.0)], 2.0), ([(math.inf, 1.0)], 2.0), ([], math.nan)]:
            with self.assertRaises(ValueError):
                grid.integrate_scan((1.0, 1.0), beams, limit)
        with self.assertRaises(ValueError):
            grid.integrate_scan((1.0, 1.0), [(0.0, 1.0)] * 100_001, 2.0)

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
