import math
import unittest

from trophic_web.model import Web, derivative, meadow, simulate, step


class ModelTests(unittest.TestCase):
    def test_derivative_known_value(self):
        web = Web(("a",), (1.0,), ((-0.5,),))
        self.assertEqual(derivative(web, (2.0,)), (0.0,))

    def test_logistic_solution_grows_toward_capacity(self):
        web = Web(("a",), (1.0,), ((-1.0,),))
        states = simulate(web, (0.2,), 0.02, 250)
        self.assertGreater(states[-1][0], states[0][0])
        self.assertLess(states[-1][0], 1.0)

    def test_zero_steps_preserves_initial(self):
        web, start = meadow()
        self.assertEqual(simulate(web, start, steps=0), [start])

    def test_rejects_bad_dimensions_and_state(self):
        with self.assertRaises(ValueError):
            derivative(Web(("a",), (1.0,), ()), (1.0,))
        with self.assertRaises(ValueError):
            derivative(Web(("a",), (1.0,), ((0.0,),)), (-1.0,))

    def test_step_rejects_nonpositive_dt(self):
        web, start = meadow()
        with self.assertRaises(ValueError):
            step(web, start, 0)

    def test_simulation_is_deterministic(self):
        web, start = meadow()
        self.assertEqual(simulate(web, start, steps=20), simulate(web, start, steps=20))


if __name__ == "__main__":
    unittest.main()
