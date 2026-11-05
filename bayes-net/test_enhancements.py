import unittest
from bayes_net import BayesNet


class EnhancementTests(unittest.TestCase):
    def test_map_assignment_respects_evidence_and_tie_order(self):
        net = BayesNet()
        net.add_node("coin", [], {(): 0.5})
        self.assertEqual(net.map_assignment({}), {"coin": False})
        self.assertEqual(net.map_assignment({"coin": True}), {"coin": True})

    def test_joint_probability_and_impossible_evidence(self):
        net = BayesNet()
        net.add_node("coin", [], {(): 0.5})
        self.assertEqual(net.joint_probability({"coin": True}), 0.5)
        with self.assertRaises(ValueError):
            net.distribution("coin", {"coin": True, "unknown": False})

    def test_large_enumeration_guard(self):
        net = BayesNet()
        for i in range(17):
            net.add_node(f"x{i}", [], {(): 0.5})
        with self.assertRaises(ValueError):
            net.distribution("x0", {}, max_assignments=1000)


if __name__ == "__main__":
    unittest.main()
