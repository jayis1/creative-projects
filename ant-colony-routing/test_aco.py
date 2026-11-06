import math
import unittest
from pathlib import Path
from aco import load_points, route_length, solve, validate

class RoutingTests(unittest.TestCase):
    def test_fixed_seed_is_reproducible(self):
        pts = [(0.,0.),(4.,0.),(5.,3.),(2.,5.),(-1.,3.)]
        self.assertEqual(solve(pts, seed=8), solve(pts, seed=8))
    def test_tour_is_permutation_and_length_matches(self):
        pts = [(0.,0.),(2.,0.),(2.,2.),(0.,2.)]
        result = solve(pts, ants=4, iterations=8)
        self.assertEqual(set(result.route), set(range(4)))
        self.assertAlmostEqual(result.distance, 8.0)
        self.assertTrue(all(a >= b for a,b in zip(result.history, result.history[1:])))
    def test_two_points_and_coincident_points(self):
        self.assertEqual(solve([(0.,0.),(3.,4.)], ants=1, iterations=1).distance, 10)
        self.assertEqual(solve([(1.,1.),(1.,1.)], ants=1, iterations=2).distance, 0)
    def test_validation(self):
        for points in [[], [(math.inf,0.)], [(1.,)], [(0.,0.)] * 201]:
            with self.assertRaises(ValueError): validate(points)
        with self.assertRaises(ValueError): solve([(0.,0.),(1.,1.)], evaporation=0)
    def test_json_input_checks(self):
        with self.assertRaises(ValueError): load_points(Path('/missing/aco.json'))

if __name__ == '__main__': unittest.main()
