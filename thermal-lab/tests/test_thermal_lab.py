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
    def test_two_zone_link_transfers_heat(self):
        model = Model.from_dict({"zones":[{"name":"hot","capacity_wh_k":1000,"outside_w_k":0},{"name":"cold","capacity_wh_k":1000,"outside_w_k":0}],"links":[{"a":"hot","b":"cold","w_k":100}]})
        result = simulate(model, {"hot":30,"cold":10}, 0, .25, .25)
        self.assertLess(result[-1]["hot"], 30)
        self.assertGreater(result[-1]["cold"], 10)
    def test_explicit_step_cannot_exceed_thermal_stability_limit(self):
        model = Model.from_dict({"zones":[{"name":"fast","capacity_wh_k":1000,"outside_w_k":1000}]})
        with self.assertRaisesRegex(ValueError, "stability limit"):
            simulate(model, {"fast":20}, 0, 2, 2)

if __name__ == "__main__": unittest.main()
