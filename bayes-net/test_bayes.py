import unittest
from bayes_net import BayesNet


class ExactInferenceTests(unittest.TestCase):
    def network(self):
        net = BayesNet()
        net.add_node("rain", [], {(): 0.2})
        net.add_node("sprinkler", ["rain"], {(True,): 0.01, (False,): 0.4})
        net.add_node("wet", ["rain", "sprinkler"], {
            (True, True): 0.99, (True, False): 0.8,
            (False, True): 0.9, (False, False): 0.0,
        })
        return net

    def test_prior_and_posterior_reference_values(self):
        net = self.network()
        self.assertAlmostEqual(net.probability("rain", {"wet": True}), 0.3576876756, places=7)
        self.assertAlmostEqual(net.probability("wet", {}), 0.44838, places=7)

    def test_evidence_query_and_joint_distribution(self):
        net = self.network()
        self.assertAlmostEqual(net.probability("rain", {"rain": True}), 1.0)
        dist = net.distribution("rain", {"wet": True})
        self.assertAlmostEqual(sum(dist.values()), 1.0)
        self.assertLess(dist[True], dist[False])

    def test_unknown_variables_are_rejected(self):
        with self.assertRaises(ValueError):
            self.network().probability("missing", {})


if __name__ == "__main__":
    unittest.main()
