import unittest

from main import make_terrain, render_ascii, route_flow


class RunoffTests(unittest.TestCase):
    def test_deterministic_terrain(self):
        self.assertEqual(make_terrain(8, 5, 11), make_terrain(8, 5, 11))
        self.assertNotEqual(make_terrain(8, 5, 11), make_terrain(8, 5, 12))

    def test_accumulation_conserves_cell_contributions(self):
        grid = [[9, 8, 7], [8, 6, 5], [7, 5, 1]]
        downstream, accumulation = route_flow(grid)
        sinks = [accumulation[y][x] for y, row in enumerate(downstream) for x, dest in enumerate(row) if dest is None]
        self.assertEqual(sum(sinks), 9)
        self.assertTrue(sinks)

    def test_flat_grid_is_all_sinks(self):
        d, a = route_flow([[2, 2], [2, 2]])
        self.assertTrue(all(v is None for row in d for v in row))
        self.assertEqual(a, [[1.0, 1.0], [1.0, 1.0]])

    def test_diagonal_routing_reaches_lower_corner(self):
        grid = [[3.0, 2.0], [2.0, 0.0]]
        four, _ = route_flow(grid, 4)
        eight, _ = route_flow(grid, 8)
        self.assertEqual(four[0][0], 1)
        self.assertEqual(eight[0][0], 3)

    def test_stream_threshold_selects_channel_cells(self):
        grid = [[3.0, 2.0], [2.0, 0.0]]
        _, accumulation = route_flow(grid)
        image = render_ascii(grid, accumulation, stream_threshold=3)
        self.assertEqual(image.count("#"), 1)
        with self.assertRaises(ValueError):
            render_ascii(grid, accumulation, stream_threshold=-1)

    def test_ascii_shape(self):
        grid = [[3, 2], [2, 1]]
        _, a = route_flow(grid)
        self.assertEqual([len(row) for row in render_ascii(grid, a).splitlines()], [2, 2])


if __name__ == "__main__":
    unittest.main()
