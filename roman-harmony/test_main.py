import unittest
from main import analyze, pitch_class, progression

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

    def test_nonempty_progression_required(self):
        with self.assertRaises(ValueError):
            progression([])

if __name__ == "__main__":
    unittest.main()
