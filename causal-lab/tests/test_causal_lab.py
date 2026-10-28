import unittest
from causal_lab import CausalGraph

class ModelTests(unittest.TestCase):
    def test_order_and_intervention(self):
        m=CausalGraph({'x':{'intercept':1},'y':{'parents':{'x':2}}})
        self.assertEqual(m.sample(seed=3)[0], {'x':1.0,'y':2.0})
        self.assertEqual(m.sample(seed=3,interventions={'x':4})[0]['y'],8.0)
    def test_cycles_rejected(self):
        with self.assertRaisesRegex(ValueError,'cycle'):
            CausalGraph({'x':{'parents':{'y':1}},'y':{'parents':{'x':1}}})
    def test_seed_reproducible(self):
        m=CausalGraph({'x':{'noise':1}})
        self.assertEqual(m.sample(10,42),m.sample(10,42))
    def test_exact_expected_values_do_intervention(self):
        m=CausalGraph({'x':{'intercept':2,'noise':99},'y':{'intercept':1,'parents':{'x':3}}})
        self.assertEqual(m.expected_values(), {'x':2.0,'y':7.0})
        self.assertEqual(m.expected_values({'x':4}), {'x':4.0,'y':13.0})
    def test_unknown_intervention_rejected(self):
        with self.assertRaisesRegex(ValueError,'known variables'):
            CausalGraph({'x':{}}).expected_values({'missing':1})
    def test_nonfinite_model_parameters_rejected(self):
        import math
        with self.assertRaisesRegex(ValueError, 'finite'):
            CausalGraph({'x': {'intercept': math.nan}})
        with self.assertRaisesRegex(ValueError, 'finite'):
            CausalGraph({'x': {'noise': math.inf}})
        with self.assertRaisesRegex(ValueError, 'finite'):
            CausalGraph({'x': {'parents': {'y': math.nan}}, 'y': {}})

if __name__=='__main__': unittest.main()
