import unittest
from bayes_net import BayesNet


class BugRegressionTests(unittest.TestCase):
    def test_partial_joint_probability_has_work_limit(self):
        net = BayesNet()
        for i in range(17):
            net.add_node(f"x{i}", [], {(): 0.5})
        with self.assertRaises(ValueError):
            net.joint_probability({}, max_assignments=1000)

    def test_map_rejects_invalid_work_limit(self):
        net = BayesNet()
        net.add_node("x", [], {(): 0.5})
        for limit in (0, -1, True, 1.5):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                net.map_assignment({}, max_assignments=limit)


if __name__ == "__main__":
    unittest.main()
