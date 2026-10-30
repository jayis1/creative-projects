import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from chord_voicer import chord_tones, total_motion, voice_lead


class ChordVoicerTests(unittest.TestCase):
    def test_major_triad(self):
        self.assertEqual(chord_tones("C"), (0, 4, 7))

    def test_voice_leading_respects_register_and_sorted_voices(self):
        result = voice_lead(["C", "F", "G"], low=48, high=72)
        self.assertEqual(len(result), 3)
        self.assertTrue(all(len(chord) == 3 for chord in result))
        self.assertTrue(all(tuple(sorted(chord)) == chord for chord in result))
        self.assertTrue(all(48 <= note <= 72 for chord in result for note in chord))

    def test_invalid_chord_rejected(self):
        with self.assertRaises(ValueError):
            chord_tones("H")

    def test_slash_bass_and_motion_stats(self):
        result = voice_lead(["C/E", "F", "G"])
        self.assertEqual(result[0][0] % 12, 4)
        self.assertEqual(total_motion(result), 9)

    def test_invalid_slash_bass_rejected(self):
        with self.assertRaises(ValueError):
            voice_lead(["C/F#"])


if __name__ == "__main__":
    unittest.main()
