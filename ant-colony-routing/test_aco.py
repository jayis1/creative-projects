import math
import unittest
from pathlib import Path
from aco import improve_two_opt, load_config, load_points, main, route_length, solve, validate

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
    def test_two_opt_removes_crossing(self):
        pts = [(0.,0.),(2.,2.),(0.,2.),(2.,0.)]
        distances = [[math.dist(a,b) for b in pts] for a in pts]
        crossed = (0,1,2,3)
        improved = improve_two_opt(crossed, distances)
        self.assertLess(route_length(improved, distances), route_length(crossed, distances))
        self.assertEqual(set(improved), set(crossed))
    def test_json_rejects_huge_integer(self):
        import json
        path = Path('huge-point.json')
        path.write_text(json.dumps([[0, 0], [10**400, 0]]))
        try:
            with self.assertRaises(ValueError): load_points(path)
        finally:
            path.unlink(missing_ok=True)
    def test_json_input_checks(self):
        with self.assertRaises(ValueError): load_points(Path('/missing/aco.json'))
    def test_config_rejects_non_object_and_unknown_keys(self):
        import json
        path = Path('config-test.json')
        try:
            for text in ('[]', '{"ants": 2, "typo": 3}'):
                path.write_text(text)
                with self.assertRaises(ValueError): load_config(path)
        finally:
            path.unlink(missing_ok=True)
    def test_cli_config_and_explicit_override(self):
        import json
        from unittest.mock import patch
        config_path = Path('config-test.json')
        try:
            config_path.write_text(json.dumps({'ants': 1, 'iterations': 1, 'seed': 5}))
            with patch('sys.argv', ['aco.py', '--config', str(config_path), '--seed', '7']):
                self.assertEqual(main(), 0)
        finally:
            config_path.unlink(missing_ok=True)

if __name__ == '__main__': unittest.main()
