import unittest

from automata_inference import infer


class InferenceTests(unittest.TestCase):
    def test_preserves_training_labels(self):
        positive = ["a", "aa", "aaa", "b", "bb", "bbb"]
        negative = ["", "ab", "ba", "aab", "bba"]
        machine = infer(positive, negative)
        self.assertTrue(all(machine.accepts(word) for word in positive))
        self.assertFalse(any(machine.accepts(word) for word in negative))

    def test_unicode_and_empty_word(self):
        machine = infer(["", "é"], ["e", "éé"])
        self.assertTrue(machine.accepts(""))
        self.assertTrue(machine.accepts("é"))
        self.assertFalse(machine.accepts("éé"))

    def test_conflicting_samples_rejected(self):
        with self.assertRaises(ValueError):
            infer(["same"], ["same"])

    def test_minimization_preserves_classification(self):
        machine = infer(["0", "00", "000"], ["", "1", "01"])
        smaller = machine.minimize()
        for word in ["", "0", "00", "000", "1", "01", "001", "0000"]:
            self.assertEqual(machine.accepts(word), smaller.accepts(word))


if __name__ == "__main__":
    unittest.main()
