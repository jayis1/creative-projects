import unittest
from stitch_planner import plan, svg

class PlannerTests(unittest.TestCase):
    def test_runs_and_alternating_scan(self):
        self.assertEqual(plan(["##..#", ".....", "#..##"], 2), [(0.,0.),(1.,0.),(4.,0.),(4.,0.),(4.,2.),(3.,2.),(0.,2.),(0.,2.)])
    def test_invalid_mask(self):
        with self.assertRaises(ValueError): plan(["##", "#"])
    def test_subdivision(self):
        text = svg([(0.,0.), (4.,0.)], 5, 2, 1.5)
        self.assertEqual(text.count("L"), 3)

if __name__ == "__main__": unittest.main()
