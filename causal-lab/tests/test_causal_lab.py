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

if __name__=='__main__': unittest.main()
