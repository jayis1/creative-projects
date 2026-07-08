#!/usr/bin/env python3
"""Comprehensive tests for new wavelet-transform v2.0 modules.

Tests SWT, CWT, signals, analysis, boundary, config, extended wavelets,
and cycle-spinning denoising.
"""
import math
import os
import random
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wavelet import (
    wavelet, Daubechies, DWT, MODWT, SWT,
    cwt, icwt, Morlet, MexicanHat, Paul, DOG,
    Threshold, soft, cycle_spin_denoise, denoise1d,
    generate, list_signals, add_noise,
    analyze, scale_statistics, energy_distribution, wavelet_variance,
    scale_correlation,
    compare_wavelets, BoundaryMode, extend_signal,
    WaveletConfig, load_config, save_config,
    sine, chirp, blocks, bumps, heavisine, doppler,
    white_noise, brown_noise, pink_noise,
    energy, entropy, mse, snr, rmse,
)
from wavelet.cwt import CWTResult
from wavelet.swt import SWTResult
from wavelet.analysis import AnalysisResult, ScaleStats


class TestExtendedWavelets(unittest.TestCase):
    """Test extended Daubechies wavelets (db5-db10)."""

    def test_db5_to_db10_creation(self):
        for n in range(5, 11):
            w = wavelet(f"db{n}")
            self.assertEqual(w.name, f"db{n}")
            self.assertEqual(w.filter_length, 2 * n)
            self.assertEqual(w.vanishing_moments, n)
            self.assertTrue(w.orthogonal)

    def test_db5_to_db10_unit_energy(self):
        for n in range(5, 11):
            w = wavelet(f"db{n}")
            e = sum(c * c for c in w.dec_lo)
            self.assertAlmostEqual(e, 1.0, places=10)

    def test_db5_to_db10_roundtrip(self):
        for n in [5, 6, 8, 10]:
            w = wavelet(f"db{n}")
            dwt = DWT(w)
            for length in [256, 512]:
                if dwt.max_level(length) < 1:
                    continue
                sig = [math.sin(2 * math.pi * 4 * i / length) for i in range(length)]
                result = dwt.decompose(sig)
                recon = dwt.reconstruct(result)
                err = max(abs(s - r) for s, r in zip(sig, recon))
                self.assertLess(err, 1e-9, f"db{n} n={length}: err={err}")


class TestSWT(unittest.TestCase):
    """Test Stationary Wavelet Transform."""

    def test_roundtrip_orthogonal(self):
        for wname in ["haar", "db4", "sym4", "coif2"]:
            swt = SWT(wname)
            for n in [64, 128, 256]:
                sig = [math.sin(2 * math.pi * 4 * i / n) for i in range(n)]
                result = swt.decompose(sig, level=3)
                recon = swt.reconstruct(result)
                err = max(abs(s - r) for s, r in zip(sig, recon))
                self.assertLess(err, 1e-9, f"SWT {wname} n={n}: err={err}")

    def test_output_length(self):
        """SWT output should have the same length as input."""
        swt = SWT("db4")
        n = 128
        sig = [math.sin(2 * math.pi * 4 * i / n) for i in range(n)]
        result = swt.decompose(sig, level=3)
        self.assertEqual(len(result.approx), n)
        for detail in result.details:
            self.assertEqual(len(detail), n)

    def test_level_count(self):
        swt = SWT("db4")
        sig = [math.sin(2 * math.pi * 4 * i / 128) for i in range(128)]
        result = swt.decompose(sig, level=4)
        self.assertEqual(result.level, 4)
        self.assertEqual(len(result.details), 4)

    def test_too_short(self):
        swt = SWT("db4")
        with self.assertRaises(ValueError):
            swt.decompose([1.0, 2.0, 3.0])

    def test_result_repr(self):
        swt = SWT("haar")
        result = swt.decompose([1.0] * 64, level=2)
        self.assertIn("SWTResult", repr(result))

    def test_biorthogonal(self):
        swt = SWT("bior2.2")
        n = 128
        sig = [math.sin(2 * math.pi * 4 * i / n) for i in range(n)]
        result = swt.decompose(sig, level=2)
        recon = swt.reconstruct(result)
        err = max(abs(s - r) for s, r in zip(sig, recon))
        self.assertLess(err, 1e-9, f"SWT bior2.2: err={err}")


class TestCWT(unittest.TestCase):
    """Test Continuous Wavelet Transform."""

    def test_morlet(self):
        w = Morlet()
        self.assertEqual(w.name, "morlet")
        self.assertTrue(w.complex)
        val = w(0.0, 1.0)
        self.assertAlmostEqual(val.real, math.pi ** -0.25, places=10)

    def test_mexican_hat(self):
        w = MexicanHat()
        self.assertEqual(w.name, "mexhat")
        self.assertFalse(w.complex)
        val = w(0.0, 1.0)
        self.assertGreater(val.real, 0)

    def test_paul(self):
        w = Paul(m=4)
        self.assertEqual(w.name, "paul4")
        self.assertTrue(w.complex)

    def test_dog(self):
        w = DOG(m=2)
        self.assertEqual(w.name, "dog2")
        # DOG(2) is the same as Mexican Hat
        val_dog = w(1.0, 1.0)
        mexhat = MexicanHat()
        val_mex = mexhat(1.0, 1.0)
        self.assertAlmostEqual(val_dog.real, val_mex.real * math.sqrt(3) * math.pi ** 0.25 / 2,
                               places=5)

    def test_cwt_shape(self):
        sig = chirp(128)
        result = cwt(sig, "morlet")
        self.assertEqual(result.input_length, 128)
        self.assertGreater(result.n_scales, 1)
        for row in result.coefficients:
            self.assertEqual(len(row), 128)

    def test_cwt_all_wavelets(self):
        sig = chirp(64)
        expected_names = {
            "morlet": "morlet", "mexhat": "mexhat",
            "paul": "paul4", "dog2": "dog2", "dog4": "dog4",
        }
        for wname in ["morlet", "mexhat", "paul", "dog2", "dog4"]:
            result = cwt(sig, wname)
            self.assertEqual(result.wavelet_name, expected_names[wname])
            self.assertGreater(result.n_scales, 0)

    def test_cwt_power(self):
        sig = chirp(64)
        result = cwt(sig, "morlet")
        power = result.power
        self.assertEqual(len(power), result.n_scales)
        for row in power:
            for p in row:
                self.assertGreaterEqual(p, 0)

    def test_icwt_reconstruction(self):
        """CWT reconstruction should approximately recover the signal."""
        sig = chirp(128)
        result = cwt(sig, "morlet")
        recon = icwt(result)
        # CWT is redundant, reconstruction is approximate
        err = mse(sig, recon)
        self.assertLess(err, 0.1, f"CWT reconstruction MSE={err}")

    def test_cwt_empty_signal(self):
        with self.assertRaises(ValueError):
            cwt([], "morlet")

    def test_cwt_custom_scales(self):
        sig = sine(64)
        scales = [1.0, 2.0, 4.0, 8.0]
        result = cwt(sig, "morlet", scales=scales)
        self.assertEqual(len(result.scales), 4)
        self.assertEqual(result.scales, scales)


class TestSignals(unittest.TestCase):
    """Test signal generation utilities."""

    def test_all_signals(self):
        names = list_signals()
        self.assertGreater(len(names), 10)
        for name in names:
            sig = generate(name, 64)
            self.assertEqual(len(sig), 64)

    def test_sine(self):
        sig = sine(128, freq=4.0)
        self.assertEqual(len(sig), 128)
        self.assertAlmostEqual(sig[0], 0.0, places=10)

    def test_multi_tone(self):
        sig = generate("multi", 128)
        self.assertEqual(len(sig), 128)

    def test_chirp(self):
        sig = chirp(128)
        self.assertEqual(len(sig), 128)

    def test_blocks(self):
        sig = blocks(256)
        self.assertEqual(len(sig), 256)
        # Blocks should have sharp transitions
        diffs = [abs(sig[i+1] - sig[i]) for i in range(len(sig)-1)]
        self.assertGreater(max(diffs), 0.1)

    def test_doppler(self):
        sig = doppler(256)
        self.assertEqual(len(sig), 256)

    def test_heavisine(self):
        sig = heavisine(256)
        self.assertEqual(len(sig), 256)

    def test_bumps(self):
        sig = bumps(256)
        self.assertEqual(len(sig), 256)

    def test_noise_types(self):
        for noise_fn in [white_noise, brown_noise, pink_noise]:
            sig = noise_fn(128, sigma=1.0, seed=42)
            self.assertEqual(len(sig), 128)

    def test_add_noise(self):
        clean = sine(128)
        noisy = add_noise(clean, 0.5, seed=42)
        self.assertEqual(len(noisy), 128)
        # Should be different
        self.assertGreater(mse(clean, noisy), 0.01)

    def test_generate_invalid(self):
        with self.assertRaises(ValueError):
            generate("nonexistent", 128)

    def test_generate_with_noise(self):
        sig = generate("sine", 128, noise=0.3)
        self.assertEqual(len(sig), 128)

    def test_reproducibility(self):
        sig1 = generate("sine", 128, noise=0.3, seed=42)
        sig2 = generate("sine", 128, noise=0.3, seed=42)
        self.assertEqual(sig1, sig2)


class TestAnalysis(unittest.TestCase):
    """Test coefficient analysis."""

    def test_scale_statistics(self):
        dwt = DWT("db4")
        sig = sine(256)
        result = dwt.decompose(sig, level=4)
        stats = scale_statistics(result)
        self.assertEqual(len(stats), 5)  # 4 details + 1 approx
        for s in stats:
            self.assertIsInstance(s, ScaleStats)
            self.assertGreaterEqual(s.n, 0)

    def test_energy_distribution(self):
        dwt = DWT("db4")
        sig = sine(256)
        result = dwt.decompose(sig, level=3)
        edist = energy_distribution(result)
        self.assertEqual(len(edist), 4)  # 3 details + approx
        self.assertAlmostEqual(sum(edist), 1.0, places=5)

    def test_wavelet_variance(self):
        dwt = DWT("db4")
        sig = sine(256)
        result = dwt.decompose(sig, level=3)
        wvar = wavelet_variance(result)
        self.assertEqual(len(wvar), 3)
        for v in wvar:
            self.assertGreaterEqual(v, 0)

    def test_scale_correlation(self):
        dwt = DWT("db4")
        sig = sine(256)
        result = dwt.decompose(sig, level=3)
        corr = scale_correlation(result)
        self.assertEqual(len(corr), 3)
        # Diagonal should be 1.0
        for i in range(len(corr)):
            self.assertAlmostEqual(corr[i][i], 1.0, places=5)

    def test_analyze(self):
        dwt = DWT("db4")
        sig = sine(256)
        result = dwt.decompose(sig, level=3)
        analysis = analyze(result)
        self.assertIsInstance(analysis, AnalysisResult)
        self.assertEqual(analysis.n_scales, 3)
        self.assertGreater(analysis.total_energy, 0)
        summary = analysis.summary()
        self.assertIsInstance(summary, str)
        self.assertIn("Wavelet Analysis Summary", summary)

    def test_compare_wavelets(self):
        sig = sine(256)
        results = compare_wavelets(sig, ["haar", "db4", "sym4"], level=3)
        self.assertEqual(len(results), 3)
        for name, analysis in results.items():
            self.assertIsInstance(analysis, AnalysisResult)


class TestBoundary(unittest.TestCase):
    """Test boundary extension."""

    def test_periodic(self):
        ext = extend_signal([1, 2, 3, 4], 3, BoundaryMode.PERIODIC)
        # Should wrap around
        self.assertEqual(ext, [3, 4, 1, 2, 3, 4, 1, 2])

    def test_zero(self):
        ext = extend_signal([1, 2, 3, 4], 3, BoundaryMode.ZERO)
        self.assertEqual(ext, [0, 0, 1, 2, 3, 4, 0, 0])

    def test_constant(self):
        ext = extend_signal([1, 2, 3, 4], 3, BoundaryMode.CONSTANT)
        self.assertEqual(ext, [1, 1, 1, 2, 3, 4, 4, 4])

    def test_symmetric(self):
        ext = extend_signal([1, 2, 3, 4], 3, BoundaryMode.SYMMETRIC)
        self.assertEqual(len(ext), 4 + 2 * 2)  # ext = filter_len - 1 = 2

    def test_invalid_mode(self):
        with self.assertRaises(ValueError):
            extend_signal([1, 2, 3], 2, "invalid")


class TestConfig(unittest.TestCase):
    """Test configuration system."""

    def test_default_config(self):
        config = WaveletConfig()
        self.assertEqual(config.wavelet, "db4")
        self.assertEqual(config.transform, "dwt")
        errors = config.validate()
        self.assertEqual(errors, [])

    def test_json_config(self):
        config = WaveletConfig(wavelet="sym4", level=3, transform="modwt")
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            path = f.name
        try:
            save_config(config, path)
            loaded = load_config(path)
            self.assertEqual(loaded.wavelet, "sym4")
            self.assertEqual(loaded.level, 3)
            self.assertEqual(loaded.transform, "modwt")
        finally:
            os.unlink(path)

    def test_toml_config(self):
        config = WaveletConfig(wavelet="coif2", level=2)
        with tempfile.NamedTemporaryFile(suffix=".toml", mode="w", delete=False) as f:
            path = f.name
        try:
            save_config(config, path)
            loaded = load_config(path)
            self.assertEqual(loaded.wavelet, "coif2")
            self.assertEqual(loaded.level, 2)
        finally:
            os.unlink(path)

    def test_config_validation_errors(self):
        config = WaveletConfig(wavelet="nonexistent")
        errors = config.validate()
        self.assertGreater(len(errors), 0)

    def test_config_invalid_transform(self):
        config = WaveletConfig(transform="invalid")
        errors = config.validate()
        self.assertTrue(any("transform" in e for e in errors))

    def test_config_nested_denoise(self):
        from wavelet import DenoiseConfig
        config = WaveletConfig(denoise=DenoiseConfig(method="sure", threshold_func="hard"))
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            path = f.name
        try:
            save_config(config, path)
            loaded = load_config(path)
            self.assertEqual(loaded.denoise.method, "sure")
            self.assertEqual(loaded.denoise.threshold_func, "hard")
        finally:
            os.unlink(path)

    def test_unsupported_format(self):
        with self.assertRaises(ValueError):
            save_config(WaveletConfig(), "/tmp/test.txt")


class TestCycleSpinning(unittest.TestCase):
    """Test cycle-spinning denoising."""

    def test_improves_snr(self):
        random.seed(42)
        n = 128
        clean = blocks(n)
        noisy = add_noise(clean, 0.5, seed=42)
        noisy_snr = snr(clean, noisy)
        denoised = cycle_spin_denoise(noisy, "db4", n_shifts=8)
        den_snr = snr(clean, denoised)
        self.assertGreater(den_snr, noisy_snr)

    def test_output_length(self):
        sig = [math.sin(2 * math.pi * 4 * i / 128) for i in range(128)]
        denoised = cycle_spin_denoise(sig, "haar", n_shifts=4)
        self.assertEqual(len(denoised), 128)

    def test_n_shifts_exceeds_n(self):
        sig = [1.0] * 32
        denoised = cycle_spin_denoise(sig, "haar", n_shifts=100)
        self.assertEqual(len(denoised), 32)


class TestLogging(unittest.TestCase):
    """Test logging utilities."""

    def test_get_logger(self):
        from wavelet.logging_utils import get_logger, set_log_level, set_verbose
        logger = get_logger("test")
        self.assertIsNotNone(logger)
        set_verbose(False)
        set_log_level("WARNING")


class TestIntegration(unittest.TestCase):
    """Integration tests combining multiple modules."""

    def test_full_pipeline(self):
        """Generate → DWT → Analyze → Denoise → Compare."""
        clean = generate("doppler", 256)
        noisy = add_noise(clean, 0.3, seed=42)
        # DWT + analysis
        dwt = DWT("db4")
        result = dwt.decompose(noisy, level=4)
        analysis = analyze(result)
        self.assertGreater(analysis.total_energy, 0)
        # Denoise with cycle spinning
        denoised = cycle_spin_denoise(noisy, "db4", n_shifts=8)
        self.assertGreater(snr(clean, denoised), snr(clean, noisy))
        # Compare wavelets
        comparison = compare_wavelets(clean, ["haar", "db4", "sym4"], level=3)
        self.assertEqual(len(comparison), 3)

    def test_cwt_then_dwt(self):
        """Use CWT for analysis, DWT for denoising."""
        sig = chirp(128)
        cwt_result = cwt(sig, "morlet")
        self.assertGreater(cwt_result.n_scales, 5)
        # DWT denoising on same signal
        noisy = add_noise(sig, 0.2, seed=42)
        denoised = denoise1d(noisy, "db4")
        self.assertEqual(len(denoised), 128)

    def test_all_db_wavelets_roundtrip(self):
        """All db1-db10 should achieve perfect reconstruction."""
        for n in range(1, 11):
            w = wavelet(f"db{n}")
            dwt = DWT(w)
            length = max(256, 4 * w.filter_length)
            sig = [math.sin(2 * math.pi * 4 * i / length) for i in range(length)]
            result = dwt.decompose(sig)
            recon = dwt.reconstruct(result)
            err = max(abs(s - r) for s, r in zip(sig, recon))
            self.assertLess(err, 1e-9, f"db{n}: err={err}")


if __name__ == "__main__":
    unittest.main(verbosity=2)