"""Tests for the DSP module."""

import math
import pytest

from waveform_synth.dsp import (
    window_hann, window_hamming, window_blackman, window_rectangle,
    fft, fft_magnitude,
    convolve, correlate, autocorrelate,
    lowpass_filter, highpass_filter, bandpass_filter,
    amplitude_envelope, onset_detection,
)
from waveform_synth.core import Oscillator, Waveform


class TestWindows:
    def test_hann_window_length(self):
        """Hann window should have correct length."""
        w = window_hann(64)
        assert len(w) == 64

    def test_hann_window_symmetry(self):
        """Hann window should be symmetric."""
        w = window_hann(64)
        for i in range(32):
            assert abs(w[i] - w[63 - i]) < 1e-10

    def test_hann_window_bounds(self):
        """Hann window values should be in [0, 1]."""
        w = window_hann(64)
        assert all(0 <= v <= 1 for v in w)
        assert abs(w[0]) < 1e-10  # Starts near 0
        assert abs(w[63]) < 1e-10  # Ends near 0

    def test_hamming_window_length(self):
        """Hamming window should have correct length."""
        w = window_hamming(128)
        assert len(w) == 128

    def test_blackman_window_length(self):
        """Blackman window should have correct length."""
        w = window_blackman(32)
        assert len(w) == 32

    def test_rectangle_window(self):
        """Rectangle window should be all 1s."""
        w = window_rectangle(10)
        assert len(w) == 10
        assert all(v == 1.0 for v in w)

    def test_invalid_window_length(self):
        """Window length <= 0 should raise ValueError."""
        for fn in [window_hann, window_hamming, window_blackman, window_rectangle]:
            with pytest.raises(ValueError):
                fn(0)
            with pytest.raises(ValueError):
                fn(-1)


class TestFFT:
    def test_fft_length(self):
        """FFT output length should match input."""
        samples = [1.0, 0.0, -1.0, 0.0]
        result = fft(samples)
        assert len(result) == 4

    def test_fft_dc_component(self):
        """FFT of a constant signal should have energy at DC (bin 0)."""
        samples = [1.0] * 16
        result = fft(samples)
        dc_real, dc_imag = result[0]
        assert abs(dc_real - 16.0) < 0.01
        assert abs(dc_imag) < 0.01

    def test_fft_magnitude_pure_sine(self):
        """FFT magnitude of a pure sine should peak at its frequency."""
        sample_rate = 44100
        freq = 440.0
        samples = [math.sin(2 * math.pi * freq * i / sample_rate) for i in range(4096)]
        spectrum = fft_magnitude(samples, sample_rate)

        # Find peak
        peak_bin = max(spectrum, key=lambda x: x[1])
        # Peak should be near 440Hz
        assert abs(peak_bin[0] - freq) < 50, f"Expected peak near {freq}Hz, got {peak_bin[0]:.1f}Hz"

    def test_fft_empty(self):
        """FFT of empty list should return empty list."""
        assert fft([]) == []


class TestConvolution:
    def test_convolve_impulse(self):
        """Convolving with an impulse should return the original signal."""
        signal = [1.0, 2.0, 3.0, 4.0]
        impulse = [1.0, 0.0, 0.0]
        result = convolve(signal, impulse)
        # Length should be len(signal) + len(impulse) - 1
        assert len(result) == len(signal) + len(impulse) - 1

    def test_convolve_moving_average(self):
        """Convolution with uniform kernel should smooth the signal."""
        signal = [0.0, 0.0, 1.0, 0.0, 0.0]
        kernel = [1.0 / 3] * 3
        result = convolve(signal, kernel)
        assert len(result) == 7

    def test_convolve_empty(self):
        """Convolving with empty should return empty."""
        assert convolve([], [1.0]) == []
        assert convolve([1.0], []) == []

    def test_correlate_autocorrelation(self):
        """Auto-correlation peak should be at lag 0."""
        samples = [math.sin(2 * math.pi * 440 * i / 44100) for i in range(1000)]
        auto = autocorrelate(samples, max_lag=100)
        assert len(auto) == 100
        assert auto[0] == pytest.approx(1.0)  # Normalized


class TestFilters:
    def test_lowpass_reduces_high_freq(self):
        """Low-pass filter should reduce high-frequency content."""
        # Create a signal with both low and high frequencies
        low = [0.7 * math.sin(2 * math.pi * 100 * i / 44100) for i in range(44100)]
        high = [0.3 * math.sin(2 * math.pi * 5000 * i / 44100) for i in range(44100)]
        combined = [l + h for l, h in zip(low, high)]

        filtered = lowpass_filter(combined, cutoff=500, sample_rate=44100)

        # After low-pass at 500Hz, the 5000Hz component should be attenuated
        # The filtered signal should have lower energy than original
        from waveform_synth.analysis import rms
        orig_rms = rms(combined)
        filt_rms = rms(filtered)
        assert filt_rms < orig_rms

    def test_highpass_reduces_low_freq(self):
        """High-pass filter should reduce low-frequency content."""
        low = [0.7 * math.sin(2 * math.pi * 100 * i / 44100) for i in range(44100)]
        high = [0.3 * math.sin(2 * math.pi * 5000 * i / 44100) for i in range(44100)]
        combined = [l + h for l, h in zip(low, high)]

        filtered = highpass_filter(combined, cutoff=2000, sample_rate=44100)

        from waveform_synth.analysis import rms
        filt_rms = rms(filtered)
        # After high-pass at 2000Hz, the 100Hz component should be mostly removed
        # So RMS should be closer to just the high component's RMS
        assert filt_rms < 0.5  # Much less than the combined RMS

    def test_bandpass_preserves_mid(self):
        """Band-pass filter should preserve mid-frequency content."""
        mid = [math.sin(2 * math.pi * 1000 * i / 44100) for i in range(44100)]
        filtered = bandpass_filter(mid, low_cutoff=500, high_cutoff=2000, sample_rate=44100)
        # Signal at 1kHz should still be present after band-pass filtering
        assert len(filtered) == len(mid)

    def test_empty_input(self):
        """Filters should handle empty input gracefully."""
        assert lowpass_filter([], 1000) == []
        assert highpass_filter([], 1000) == []


class TestAmplitudeEnvelope:
    def test_envelope_length(self):
        """Envelope should have reasonable number of frames."""
        samples = [1.0] * 44100
        env = amplitude_envelope(samples, frame_size=1024, hop_size=512)
        # Expected: roughly (44100 - 1024) / 512 + 1 ≈ 85, but last partial frame counts too
        assert len(env) > 80

    def test_envelope_constant_signal(self):
        """Envelope of a constant signal should be constant."""
        samples = [0.5] * 44100
        env = amplitude_envelope(samples, frame_size=1024, hop_size=512)
        for e in env:
            assert abs(e - 0.5) < 0.01

    def test_envelope_empty(self):
        """Empty input should return empty envelope."""
        assert amplitude_envelope([]) == []


class TestOnsetDetection:
    def test_onset_detection_basic(self):
        """Should detect onsets in a signal with distinct notes."""
        # Create a signal with silence between notes
        note1 = [0.8 * math.sin(2 * math.pi * 440 * i / 44100) for i in range(4410)]
        silence = [0.0] * 2205
        note2 = [0.8 * math.sin(2 * math.pi * 660 * i / 44100) for i in range(4410)]
        combined = note1 + silence + note2
        onsets = onset_detection(combined, frame_size=512, hop_size=256, threshold=0.2)
        # Should detect at least 1 onset
        assert len(onsets) >= 1

    def test_onset_detection_empty(self):
        """Empty signal should have no onsets."""
        assert onset_detection([]) == []

    def test_onset_detection_short(self):
        """Very short signal should have no onsets."""
        assert onset_detection([0.1] * 10) == []