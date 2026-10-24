import unittest
from petri_net import PetriNet, Transition

class PetriNetTests(unittest.TestCase):
    def setUp(self):
        self.net = PetriNet({'ready': 1, 'busy': 0}, (
            Transition('start', (('ready', 1),), (('busy', 1),)),
            Transition('finish', (('busy', 1),), (('ready', 1),)),
        ))

    def test_fire_and_disabled_transition(self):
        self.assertEqual(self.net.fire(self.net.initial, self.net.transitions[0]), (0, 1))
        with self.assertRaises(ValueError):
            self.net.fire(self.net.initial, self.net.transitions[1])

    def test_reachability(self):
        self.assertEqual(self.net.reachable(), {(1, 0), (0, 1)})

    def test_simulation_stops_when_deadlocked(self):
        self.assertEqual(len(self.net.simulate(5, ('start',))), 2)

    def test_deadlock_analysis(self):
        self.assertEqual(self.net.deadlocks(), set())
        dead_end = PetriNet({'p': 0}, ())
        self.assertEqual(dead_end.deadlocks(), {(0,)})

    def test_initial_marking_respects_token_cap(self):
        net = PetriNet({'p': 3}, ())
        with self.assertRaises(ValueError):
            net.reachable(token_cap=2)

    def test_resource_bounds(self):
        with self.assertRaises(ValueError):
            self.net.simulate(-1)
        with self.assertRaises(RuntimeError):
            self.net.reachable(max_states=1)

    def test_invalid_arc(self):
        with self.assertRaises(ValueError):
            PetriNet({'p': 1}, (Transition('bad', (('missing', 1),), ()),))

if __name__ == '__main__':
    unittest.main()
