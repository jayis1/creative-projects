import unittest
from main import Epidemic

class EpidemicTests(unittest.TestCase):
    def test_random_network_is_seeded_and_degree_bounded(self):
        a = Epidemic(24, contacts_per_person=3, topology="random", seed=12)
        b = Epidemic(24, contacts_per_person=3, topology="random", seed=12)
        self.assertEqual(a.people, b.people)
        self.assertTrue(all(len(p.contacts) <= 3 for p in a.people))

    def test_intervention_reduces_transmission_after_start_day(self):
        sim = Epidemic(30, contacts_per_person=4, beta=1, incubation_days=1,
                       infectious_days=5, intervention_day=0, beta_multiplier=0)
        sim.run(12)
        self.assertEqual(sim.summary()["ever_infected"], 1)

    def test_summary_reports_peak_and_attack_rate(self):
        sim = Epidemic(10, contacts_per_person=0)
        sim.run(12)
        self.assertEqual(sim.summary()["peak_infectious"], 1)
        self.assertEqual(sim.summary()["attack_rate"], .1)

    def test_invalid_topology_and_intervention(self):
        with self.assertRaises(ValueError): Epidemic(10, topology="unknown")
        with self.assertRaises(ValueError): Epidemic(10, beta_multiplier=2)

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
