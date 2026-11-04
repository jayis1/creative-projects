import unittest
from main import analyze, classify_cadence, pitch_class, progression, progression_report

class HarmonyTests(unittest.TestCase):
    def test_major_key_diatonic_chords(self):
        self.assertEqual(analyze("I").notes, ("C", "E", "G"))
        self.assertEqual(analyze("ii", "G").notes, ("A", "C", "E"))
        self.assertEqual(analyze("V7", "F").notes, ("C", "E", "G", "A#"))

    def test_minor_key(self):
        chord = analyze("i", "A", "minor")
        self.assertEqual((chord.root, chord.quality, chord.notes), ("A", "minor", ("A", "C", "E")))

    def test_accidentals_and_inversions(self):
        self.assertEqual(analyze("bVII", "C").root, "A#")
        self.assertEqual(analyze("I6").notes, ("E", "G", "C"))

    def test_invalid_input(self):
        for token in ("VIII", "Vx", ""):
            with self.subTest(token=token), self.assertRaises(ValueError):
                analyze(token)
        with self.assertRaises(ValueError):
            analyze("I", mode="dorian")
        with self.assertRaises(ValueError):
            pitch_class("H")

    def test_cadence_classification(self):
        self.assertEqual(classify_cadence(progression(["V", "I"])), "authentic")
        self.assertEqual(classify_cadence(progression(["IV", "I"])), "plagal")
        self.assertEqual(classify_cadence(progression(["V", "vi"])), "deceptive")
        self.assertEqual(classify_cadence(progression(["I", "V"])), "half")
        self.assertEqual(classify_cadence(progression(["I"])), "incomplete")

    def test_structured_report(self):
        report = progression_report(["V", "I"], "G")
        self.assertEqual((report["key"], report["mode"], report["cadence"]), ("G", "major", "authentic"))
        self.assertEqual(len(report["chords"]), 2)

    def test_nonempty_progression_required(self):
        with self.assertRaises(ValueError):
            progression([])

if __name__ == "__main__":
    unittest.main()
