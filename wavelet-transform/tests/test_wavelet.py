#!/usr/bin/env python3
"""Comprehensive test suite for the wavelet-transform package."""
import math
import random
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wavelet import (
    wavelet, Haar, Daubechies, Symlet, Coiflet, Biorthogonal,
    DWT, MODWT, WaveletPacket,
    Threshold, soft, hard, garrote, firm,
    denoise1d, denoise2d,
    compress1d, decompress1d,
    energy, entropy, psnr, mse, snr,
)
from wavelet.compress import serialize, deserialize
from wavelet.utils import rmse, mean_absolute_error


class TestWavelets(unittest.TestCase):
    """Test wavelet creation and filter properties."""

    def test_haar(self):
        w = Haar()
        self.assertEqual(w.name, "haar")
        self.assertEqual(w.filter_length, 2)
        self.assertEqual(w.vanishing_moments, 1)
        self.assertTrue(w.orthogonal)

    def test_daubechies(self):
        for N in [1, 2, 3, 4]:
            w = Daubechies(N)
            self.assertEqual(w.name, f"db{N}")
            self.assertEqual(w.vanishing_moments, N)
            self.assertTrue(w.orthogonal)
            # Check filter length = 2*N
            self.assertEqual(w.filter_length, 2 * N)

    def test_daubechies_invalid(self):
        with self.assertRaises(ValueError):
            Daubechies(0)
        with self.assertRaises(ValueError):
            Daubechies(5)

    def test_symlet(self):
        for N in [2, 3, 4, 5]:
            w = Symlet(N)
            self.assertEqual(w.name, f"sym{N}")
            self.assertTrue(w.orthogonal)

    def test_coiflet(self):
        for N in [1, 2, 3]:
            w = Coiflet(N)
            self.assertEqual(w.name, f"coif{N}")
            self.assertTrue(w.orthogonal)

    def test_biorthogonal(self):
        for name in ["1.1", "2.2", "1.3", "3.1", "3.3"]:
            w = Biorthogonal(name)
            self.assertEqual(w.name, f"bior{name}")
            self.assertFalse(w.orthogonal)
            self.assertTrue(w.biorthogonal)

    def test_factory(self):
        for name in ["haar", "db1", "db4", "sym4", "coif2", "bior2.2"]:
            w = wavelet(name)
            self.assertIsNotNone(w)

    def test_factory_invalid(self):
        with self.assertRaises(ValueError):
            wavelet("nonexistent")

    def test_filter_energy(self):
        """Orthogonal wavelet filters should have unit energy."""
        for name in ["haar", "db2", "db4", "sym4", "coif2"]:
            w = wavelet(name)
            e = sum(c * c for c in w.dec_lo)
            self.assertAlmostEqual(e, 1.0, places=10)


class TestDWT1D(unittest.TestCase):
    """Test 1-D DWT decomposition and reconstruction."""

    def _generate_signal(self, kind="sine", n=256):
        if kind == "sine":
            return [math.sin(2 * math.pi * 4 * i / n) for i in range(n)]
        elif kind == "chirp":
            return [math.sin(2 * math.pi * (1 + 10 * i / n) * i / n) for i in range(n)]
        elif kind == "multi":
            return [math.sin(2 * math.pi * 4 * i / n) + 0.3 * math.sin(2 * math.pi * 16 * i / n)
                    for i in range(n)]
        elif kind == "ramp":
            return [float(i) / n for i in range(n)]
        else:
            return [math.sin(2 * math.pi * 4 * i / n) for i in range(n)]

    def test_single_level_roundtrip(self):
        for wname in ["haar", "db2", "db4", "sym4", "coif2", "bior2.2"]:
            w = wavelet(wname)
            dwt = DWT(w)
            for n in [32, 64, 128, 256]:
                if n < w.filter_length:
                    continue
                sig = self._generate_signal("sine", n)
                a, d = dwt.decompose1(sig)
                recon = dwt.reconstruct1(a, d, out_len=n)
                err = max(abs(s - r) for s, r in zip(sig, recon))
                self.assertLess(err, 1e-10, f"{wname} n={n}: single-level err={err}")

    def test_multilevel_roundtrip(self):
        for wname in ["haar", "db2", "db4", "sym4", "coif2", "bior2.2"]:
            w = wavelet(wname)
            dwt = DWT(w)
            for n in [64, 128, 256, 512]:
                if dwt.max_level(n) < 1:
                    continue
                for kind in ["sine", "chirp", "multi", "ramp"]:
                    sig = self._generate_signal(kind, n)
                    result = dwt.decompose(sig)
                    recon = dwt.reconstruct(result)
                    err = max(abs(s - r) for s, r in zip(sig, recon))
                    self.assertLess(err, 1e-9, f"{wname} n={n} {kind}: err={err}")

    def test_max_level(self):
        dwt = DWT("haar")
        self.assertGreater(dwt.max_level(256), 0)
        self.assertEqual(dwt.max_level(0), 0)

    def test_decompose_too_short(self):
        dwt = DWT("db4")
        with self.assertRaises(ValueError):
            dwt.decompose([1.0, 2.0, 3.0])  # length 3 < filter length 8

    def test_dwt_result_structure(self):
        dwt = DWT("db4")
        sig = [math.sin(2 * math.pi * 4 * i / 128) for i in range(128)]
        result = dwt.decompose(sig, level=3)
        self.assertEqual(result.level, 3)
        self.assertEqual(len(result.details), 3)
        self.assertEqual(result.input_length, 128)
        self.assertEqual(result.wavelet_name, "db4")
        # Check that detail sizes decrease
        for i in range(len(result.details) - 1):
            self.assertGreaterEqual(len(result.details[i]), len(result.details[i + 1]))


class TestDWT2D(unittest.TestCase):
    """Test 2-D DWT."""

    def test_2d_roundtrip(self):
        dwt = DWT("haar")
        matrix = [[float(i * 8 + j) for j in range(8)] for i in range(8)]
        decomp = dwt.decompose2(matrix, level=1)
        recon = dwt.reconstruct2(decomp)
        err = max(abs(matrix[i][j] - recon[i][j]) for i in range(8) for j in range(8))
        self.assertLess(err, 1e-10)

    def test_2d_structure(self):
        dwt = DWT("haar")
        matrix = [[float(i + j) for j in range(8)] for i in range(8)]
        decomp = dwt.decompose2(matrix, level=2)
        self.assertEqual(decomp["level"], 2)
        self.assertEqual(decomp["shape"], (8, 8))
        self.assertEqual(len(decomp["subbands"]), 2)
        for sb in decomp["subbands"]:
            self.assertIn("LH", sb)
            self.assertIn("HL", sb)
            self.assertIn("HH", sb)


class TestMODWT(unittest.TestCase):
    """Test MODWT."""

    def test_roundtrip(self):
        for wname in ["haar", "db4", "sym4", "coif2"]:
            mod = MODWT(wname)
            for n in [32, 64, 128]:
                sig = [math.sin(2 * math.pi * 4 * i / n) for i in range(n)]
                result = mod.decompose(sig, level=3)
                recon = mod.reconstruct(result)
                err = max(abs(s - r) for s, r in zip(sig, recon))
                self.assertLess(err, 1e-10, f"MODWT {wname} n={n}: err={err}")

    def test_output_length(self):
        """MODWT output should have the same length as input."""
        mod = MODWT("haar")
        n = 64
        sig = [math.sin(2 * math.pi * 4 * i / n) for i in range(n)]
        result = mod.decompose(sig, level=3)
        self.assertEqual(len(result.approx), n)
        for detail in result.details:
            self.assertEqual(len(detail), n)


class TestWaveletPackets(unittest.TestCase):
    """Test wavelet packet decomposition."""

    def test_roundtrip(self):
        wp = WaveletPacket("db4")
        n = 64
        sig = [math.sin(2 * math.pi * 4 * i / n) for i in range(n)]
        result = wp.decompose(sig, level=3)
        recon = wp.reconstruct(result)
        err = max(abs(s - r) for s, r in zip(sig, recon))
        self.assertLess(err, 1e-10)

    def test_packet_count(self):
        wp = WaveletPacket("haar")
        n = 64
        sig = [math.sin(2 * math.pi * 4 * i / n) for i in range(n)]
        result = wp.decompose(sig, level=3)
        # Full binary tree: 1 + 2 + 4 + 8 = 15 nodes
        self.assertEqual(len(result["packets"]), 15)

    def test_best_basis(self):
        wp = WaveletPacket("db4")
        n = 128
        sig = [math.sin(2 * math.pi * 4 * i / n) for i in range(n)]
        result = wp.decompose(sig, level=4)
        selected = wp.best_basis(result)
        self.assertGreater(len(selected), 0)
        self.assertLessEqual(len(selected), 31)  # max 2^5 - 1 nodes


class TestThresholding(unittest.TestCase):
    """Test thresholding functions."""

    def test_soft(self):
        self.assertEqual(soft(5.0, 2.0), 3.0)
        self.assertEqual(soft(-5.0, 2.0), -3.0)
        self.assertEqual(soft(1.0, 2.0), 0.0)
        self.assertEqual(soft(0.0, 2.0), 0.0)

    def test_hard(self):
        self.assertEqual(hard(5.0, 2.0), 5.0)
        self.assertEqual(hard(1.0, 2.0), 0.0)
        self.assertEqual(hard(-5.0, 2.0), -5.0)

    def test_garrote(self):
        self.assertAlmostEqual(garrote(5.0, 2.0), 5.0 - 4.0 / 5.0)
        self.assertEqual(garrote(1.0, 2.0), 0.0)

    def test_firm(self):
        self.assertEqual(firm(1.0, 2.0, 4.0), 0.0)
        self.assertEqual(firm(5.0, 2.0, 4.0), 5.0)
        self.assertAlmostEqual(firm(3.0, 2.0, 4.0), 3.0 * (3.0 - 2.0) / (4.0 - 2.0))

    def test_firm_invalid(self):
        with self.assertRaises(ValueError):
            firm(1.0, 4.0, 2.0)  # t2 <= t1

    def test_estimate_sigma(self):
        from wavelet.threshold import estimate_sigma
        # Noise with known std
        random.seed(42)
        noise = [random.gauss(0, 1.0) for _ in range(1000)]
        sigma = estimate_sigma(noise)
        self.assertAlmostEqual(sigma, 1.0, delta=0.3)

    def test_universal_threshold(self):
        from wavelet.threshold import universal_threshold
        t = universal_threshold(100, 1.0)
        expected = math.sqrt(2 * math.log(100))
        self.assertAlmostEqual(t, expected)

    def test_threshold_methods(self):
        from wavelet.threshold import estimate_threshold
        coeffs = [0.1, -0.05, 0.3, -0.02, 0.8, -0.1, 0.05]
        for method in [Threshold.UNIVERSAL, Threshold.SURE, Threshold.BAYES, Threshold.MINIMAX]:
            t = estimate_threshold(coeffs, method)
            self.assertGreaterEqual(t, 0.0)


class TestDenoising(unittest.TestCase):
    """Test denoising."""

    def test_denoise_improves_snr(self):
        random.seed(42)
        n = 256
        clean = [math.sin(2 * math.pi * 4 * i / n) for i in range(n)]
        noisy = [c + random.gauss(0, 0.3) for c in clean]
        noisy_snr = snr(clean, noisy)
        for wname in ["haar", "db4"]:
            for method in [Threshold.UNIVERSAL, Threshold.BAYES]:
                denoised = denoise1d(noisy, wavelet=wname, threshold_method=method)
                den_snr = snr(clean, denoised)
                self.assertGreater(den_snr, noisy_snr,
                                   f"{wname} {method.value}: SNR {noisy_snr:.2f} -> {den_snr:.2f}")

    def test_denoise_modwt(self):
        random.seed(42)
        n = 128
        clean = [math.sin(2 * math.pi * 4 * i / n) for i in range(n)]
        noisy = [c + random.gauss(0, 0.3) for c in clean]
        denoised = denoise1d(noisy, wavelet="db4", transform="modwt")
        self.assertEqual(len(denoised), n)

    def test_denoise2d(self):
        random.seed(42)
        matrix = [[math.sin(i * 0.1) * math.cos(j * 0.1) for j in range(16)]
                  for i in range(16)]
        noisy = [[v + random.gauss(0, 0.2) for v in row] for row in matrix]
        denoised = denoise2d(noisy, wavelet="haar")
        self.assertEqual(len(denoised), 16)
        self.assertEqual(len(denoised[0]), 16)


class TestCompression(unittest.TestCase):
    """Test compression and decompression."""

    def test_compress_decompress(self):
        n = 256
        sig = [math.sin(2 * math.pi * 4 * i / n) + 0.3 * math.sin(2 * math.pi * 16 * i / n)
               for i in range(n)]
        compressed = compress1d(sig, wavelet="db4", keep_ratio=0.3)
        recon = decompress1d(compressed)
        self.assertEqual(len(recon), n)
        # Should have reasonable reconstruction
        err = mse(sig, recon)
        self.assertLess(err, 0.01)

    def test_compression_ratio(self):
        n = 256
        sig = [math.sin(2 * math.pi * 4 * i / n) for i in range(n)]
        compressed = compress1d(sig, wavelet="db4", keep_ratio=0.2)
        self.assertGreater(compressed.compression_ratio, 1.0)
        self.assertGreater(compressed.sparsity, 0.5)

    def test_serialization(self):
        n = 128
        sig = [math.sin(2 * math.pi * 4 * i / n) for i in range(n)]
        compressed = compress1d(sig, wavelet="db4", keep_ratio=0.3)
        data = serialize(compressed)
        decomp = deserialize(data)
        self.assertEqual(decomp.wavelet_name, compressed.wavelet_name)
        self.assertEqual(decomp.input_length, compressed.input_length)
        self.assertEqual(decomp.level, compressed.level)
        self.assertGreater(len(data), 0)

    def test_keep_ratio_invalid(self):
        with self.assertRaises(ValueError):
            compress1d([1.0] * 64, keep_ratio=0.0)
        with self.assertRaises(ValueError):
            compress1d([1.0] * 64, keep_ratio=1.5)


class TestUtils(unittest.TestCase):
    """Test utility functions."""

    def test_energy(self):
        self.assertAlmostEqual(energy([1, 2, 3]), 14)
        self.assertEqual(energy([]), 0)

    def test_entropy(self):
        self.assertGreater(entropy([1, 1, 1, 1]), 0)
        self.assertEqual(entropy([]), 0)
        self.assertEqual(entropy([0, 0, 0]), 0)

    def test_mse(self):
        self.assertEqual(mse([1, 2, 3], [1, 2, 3]), 0)
        self.assertAlmostEqual(mse([1, 2], [2, 3]), 1.0)

    def test_mse_length_mismatch(self):
        with self.assertRaises(ValueError):
            mse([1, 2], [1, 2, 3])

    def test_psnr(self):
        self.assertEqual(psnr([1, 2, 3], [1, 2, 3]), float("inf"))

    def test_snr(self):
        self.assertEqual(snr([1, 2, 3], [1, 2, 3]), float("inf"))

    def test_rmse(self):
        self.assertAlmostEqual(rmse([1, 2], [2, 3]), 1.0)

    def test_mae(self):
        self.assertAlmostEqual(mean_absolute_error([1, 2, 3], [2, 3, 4]), 1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)