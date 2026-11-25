import unittest

from coverage import CoveragePlan, plan_coverage, render

class CoverageTests(unittest.TestCase):
    def test_visits_every_free_cell_and_avoids_obstacles(self):
        grid = ["....", ".##.", "...."]
        result = plan_coverage(grid)
        expected = {(r,c) for r,row in enumerate(grid) for c,ch in enumerate(row) if ch == "."}
        self.assertEqual(set(result.cells), expected)
        self.assertTrue(all(grid[r][c] == "." for r,c in result.cells))
        self.assertEqual(result.distance, len(result.cells)-1)

    def test_render_is_dimensions_and_blockers_preserved(self):
        grid = ["...", ".#."]
        out = render(grid, plan_coverage(grid))
        self.assertEqual(out.replace("\n", "" ).count("#"), 1)
        self.assertEqual(len(out.splitlines()), 2)

    def test_invalid_inputs(self):
        for grid in ([], [""], ["..", "."], [".x"]):
            with self.subTest(grid=grid), self.assertRaises(ValueError):
                plan_coverage(grid)
        with self.assertRaises(ValueError):
            plan_coverage([".#."], (0,1))
        with self.assertRaises(ValueError):
            plan_coverage([".#."], (4,4))

    def test_column_sweep_and_invalid_axis(self):
        grid = ["...", ".#.", "..."]
        result = plan_coverage(grid, axis="columns")
        expected = {(r,c) for r,row in enumerate(grid) for c,ch in enumerate(row) if ch == "."}
        self.assertEqual(set(result.cells), expected)
        with self.assertRaisesRegex(ValueError, "axis"):
            plan_coverage(grid, axis="diagonal")

    def test_render_rejects_malformed_plan_coordinates(self):
        grid = [".#"]
        with self.assertRaisesRegex(ValueError, "invalid traversable cell"):
            render(grid, CoveragePlan(((2, 0),), 0.0))
        with self.assertRaisesRegex(ValueError, "invalid traversable cell"):
            render(grid, CoveragePlan(((0, 1),), 0.0))

    def test_disconnected_area_rejected(self):
        with self.assertRaisesRegex(ValueError, "connected"):
            plan_coverage([".#."])

    def test_single_cell(self):
        result = plan_coverage(["."], (0,0))
        self.assertEqual(result.cells, ((0,0),))
        self.assertEqual(result.distance, 0)

if __name__ == "__main__":
    unittest.main()
