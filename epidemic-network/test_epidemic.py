import unittest
from main import Epidemic

class EpidemicTests(unittest.TestCase):
    def test_seed_reproduces_history(self):
        a = Epidemic(30, seed=9).run(40)
        b = Epidemic(30, seed=9).run(40)
        self.assertEqual(a, b)

    def test_counts_conserve_population(self):
        sim = Epidemic(50, seed=3)
        for _ in range(30):
            row = sim.step()
            self.assertEqual(sum(row[k] for k in "SEIR"), 50)

    def test_zero_contacts_stops_after_patient_zero(self):
        sim = Epidemic(10, contacts_per_person=0)
        sim.run(20)
        self.assertEqual(sim.summary()["ever_infected"], 1)
        self.assertEqual(sim.counts(), {"S": 9, "E": 0, "I": 0, "R": 1})

    def test_invalid_model_parameters(self):
        for args in [(1,), (5, 5), (5, 1, 1.1), (5, 1, .2, 0)]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                Epidemic(*args)

    def test_negative_run_limit_rejected(self):
        with self.assertRaises(ValueError):
            Epidemic(5).run(-1)

if __name__ == "__main__": unittest.main()
