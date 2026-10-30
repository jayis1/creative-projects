import json
import pathlib
import subprocess
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

    def test_json_output_contains_machine_readable_notes_and_motion(self):
        script = pathlib.Path(__file__).resolve().parents[1] / "chord_voicer.py"
        result = subprocess.run(
            [sys.executable, str(script), "--format", "json", "C/E", "F", "G"],
            check=True, capture_output=True, text=True,
        )
        payload = json.loads(result.stdout)
        self.assertEqual(payload["chords"][0]["midi"], [52, 55, 60])
        self.assertEqual(payload["chords"][0]["note_names"], ["E3", "G3", "C4"])
        self.assertEqual(payload["total_motion_semitones"], 9)

    def test_cli_invalid_chord_has_concise_error(self):
        script = pathlib.Path(__file__).resolve().parents[1] / "chord_voicer.py"
        result = subprocess.run(
            [sys.executable, str(script), "H"], capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("error: unsupported chord: 'H'", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_register_must_stay_within_midi_range(self):
        for bounds in ((-1, 60), (60, 128)):
            with self.subTest(bounds=bounds), self.assertRaises(ValueError):
                voice_lead(["C"], low=bounds[0], high=bounds[1])


if __name__ == "__main__":
    unittest.main()
