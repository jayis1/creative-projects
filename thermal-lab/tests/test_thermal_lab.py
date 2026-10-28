import unittest
from thermal_lab import Model, simulate

class ThermalLabTests(unittest.TestCase):
    def setUp(self):
        self.model = Model.from_dict({"zones":[{"name":"a","capacity_wh_k":1000,"outside_w_k":100}]})
    def test_isolated_zone_cools_toward_outside(self):
        result = simulate(self.model, {"a":20}, 0, 1, 0.25)
        self.assertEqual(len(result), 5)
        self.assertAlmostEqual(result[-1]["a"], 18.0737578125)
    def test_heating_gain(self):
        result = simulate(self.model, {"a":20}, 0, 1, 0.25, {"a":100})
        self.assertGreater(result[-1]["a"], 12.890625)
    def test_model_rejects_duplicate_zone(self):
        with self.assertRaises(ValueError): Model.from_dict({"zones":[{"name":"x","capacity_wh_k":1,"outside_w_k":0},{"name":"x","capacity_wh_k":1,"outside_w_k":0}]})
    def test_requires_all_initial_zones(self):
        with self.assertRaises(ValueError): simulate(self.model, {}, 0, 1, .25)

if __name__ == "__main__": unittest.main()
