import math
import tempfile
import unittest
import wave
from pathlib import Path
from main import analyze, analyze_wav, fft, read_wav

class FftTests(unittest.TestCase):
    def test_impulse_has_flat_spectrum(self):
        values = fft([1, 0, 0, 0])
        self.assertTrue(all(abs(abs(v) - 1) < 1e-12 for v in values))

    def test_rejects_invalid_lengths(self):
        for values in ([], [1, 2, 3]):
            with self.assertRaises(ValueError):
                fft(values)

    def test_detects_bin_centered_tone_and_metrics(self):
        n, rate, bin_no = 1024, 8192, 32
        samples = [math.sin(2 * math.pi * bin_no * i / n) for i in range(n)]
        result = analyze(samples, rate)
        self.assertAlmostEqual(result.dominant_frequency_hz or 0.0, 256.0, places=5)
        self.assertAlmostEqual(result.rms, math.sqrt(0.5), places=3)
        self.assertGreater(result.spectral_centroid_hz, 250)

    def test_rejects_nan_and_invalid_frame_size(self):
        with self.assertRaises(ValueError):
            analyze([float("nan")], 8000)
        with self.assertRaises(ValueError):
            analyze([1.0], 8000, frame_size=3)
        with self.assertRaises(ValueError):
            analyze([1.0], 8000, frame_size=131072)

    def test_reads_multichannel_pcm_and_bounds_samples(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "stereo.wav"
            with wave.open(str(path), "wb") as out:
                out.setnchannels(2); out.setsampwidth(2); out.setframerate(8000)
                out.writeframes(b"\x00\x40\x00\xc0" * 8)
            samples, rate = read_wav(path)
            self.assertEqual(rate, 8000)
            self.assertEqual(samples, [0.0] * 8)
            with self.assertRaises(ValueError):
                read_wav(path, max_samples=7)

    def test_empty_wav_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "empty.wav"
            with wave.open(str(path), "wb") as out:
                out.setnchannels(1); out.setsampwidth(2); out.setframerate(8000)
            with self.assertRaises(ValueError):
                analyze_wav(path)

if __name__ == "__main__":
    unittest.main()
