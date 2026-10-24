import unittest
from modelcheck import Formula as F, TransitionSystem, check, satisfying

class ModelCheckTests(unittest.TestCase):
    def setUp(self):
        self.ts = TransitionSystem.build('a', {'a':['b'], 'b':['a','c'], 'c':['c']},
            {'a':['start'], 'b':['mid'], 'c':['goal']})

    def test_reachable_includes_implicit_terminal_and_cycle(self):
        self.assertEqual(set(self.ts.states), {'a','b','c'})

    def test_eventuality_and_universal_eventuality(self):
        self.assertTrue(check(self.ts, F.EF(F.atom('goal'))))
        self.assertFalse(check(self.ts, F.AF(F.atom('goal'))))

    def test_global_and_existential_global(self):
        self.assertFalse(check(self.ts, F.AG(F.neg(F.atom('goal')))))
        self.assertTrue(check(self.ts, F.EG(F.neg(F.atom('goal')))))

    def test_next_operators(self):
        self.assertTrue(check(self.ts, F.EX(F.atom('mid'))))
        self.assertFalse(check(self.ts, F.AX(F.atom('goal'))))

    def test_boolean_operators(self):
        self.assertTrue(check(self.ts, F.both(F.atom('start'), F.neg(F.atom('goal')))))
        self.assertTrue('a' in satisfying(self.ts, F.either(F.atom('start'), F.atom('goal'))))

    def test_shortest_path(self):
        self.assertEqual(self.ts.shortest_path(lambda s: s == 'c'), ['a','b','c'])

    def test_empty_transition_relation(self):
        ts = TransitionSystem.build(0, {})
        self.assertTrue(check(ts, F.AF(F.atom('missing'))))
        self.assertFalse(check(ts, F.EX(F.atom('missing'))))

if __name__ == '__main__': unittest.main()
