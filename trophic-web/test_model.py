import json
import tempfile
import unittest
from pathlib import Path

from trophic_web.model import Web, derivative, meadow, simulate, step
from trophic_web.io import load_web, write_csv


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

    def test_json_load_and_csv_export(self):
        payload = {"names": ["reed"], "growth": [0.2], "interactions": [[-0.1]], "initial": [1.0]}
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "web.json"
            output = Path(directory) / "trajectory.csv"
            source.write_text(json.dumps(payload), encoding="utf-8")
            web, initial = load_web(source)
            trajectory = simulate(web, initial, steps=2)
            write_csv(output, web, trajectory, 0.1)
            rows = output.read_text(encoding="utf-8").splitlines()
        self.assertEqual(web.names, ("reed",))
        self.assertEqual(initial, (1.0,))
        self.assertEqual(len(rows), 4)
        self.assertEqual(rows[0], "time,reed")


if __name__ == "__main__":
    unittest.main()
