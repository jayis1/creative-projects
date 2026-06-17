"""Tests for the audio_io module."""

import os
import tempfile
import pytest

from waveform_synth.core import Oscillator, Waveform, normalize
from waveform_synth.export import WavWriter
from waveform_synth.audio_io import (
    AudioInfo, detect_audio_format, read_aiff,
    write_raw_pcm, get_audio_info,
)


class TestAudioFormatDetection:
    def test_detect_wav(self):
        """Should detect WAV files."""
        # Create a simple WAV file
        osc = Oscillator(Waveform.SINE, frequency=440.0, sample_rate=44100)
        samples = normalize(osc.generate(0.1))
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            filepath = f.name
        try:
            writer = WavWriter(sample_rate=44100)
            writer.write(filepath, samples)
            fmt = detect_audio_format(filepath)
            assert fmt == 'wav'
        finally:
            os.unlink(filepath)

    def test_detect_unknown(self):
        """Should return 'unknown' for non-audio files."""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False, mode='w') as f:
            f.write("Hello, this is not audio")
            filepath = f.name
        try:
            fmt = detect_audio_format(filepath)
            assert fmt == 'unknown'
        finally:
            os.unlink(filepath)


class TestRawPCM:
    def test_write_raw_pcm_16bit(self):
        """Should write 16-bit raw PCM data."""
        samples = [0.5, -0.5, 0.3, -0.3]
        with tempfile.NamedTemporaryFile(suffix='.pcm', delete=False) as f:
            filepath = f.name
        try:
            write_raw_pcm(filepath, samples, bits_per_sample=16)
            size = os.path.getsize(filepath)
            assert size == len(samples) * 2  # 16-bit = 2 bytes per sample
        finally:
            os.unlink(filepath)

    def test_write_raw_pcm_8bit(self):
        """Should write 8-bit raw PCM data."""
        samples = [0.5, -0.5, 0.3]
        with tempfile.NamedTemporaryFile(suffix='.pcm', delete=False) as f:
            filepath = f.name
        try:
            write_raw_pcm(filepath, samples, bits_per_sample=8)
            size = os.path.getsize(filepath)
            assert size == len(samples)  # 8-bit = 1 byte per sample
        finally:
            os.unlink(filepath)

    def test_write_raw_pcm_empty(self):
        """Should raise ValueError for empty samples."""
        with pytest.raises(ValueError):
            write_raw_pcm('/tmp/test.pcm', [], bits_per_sample=16)

    def test_write_raw_pcm_unsupported_depth(self):
        """Should raise ValueError for unsupported bit depth."""
        with pytest.raises(ValueError):
            write_raw_pcm('/tmp/test.pcm', [0.5], bits_per_sample=12)


class TestAudioInfo:
    def test_wav_info(self):
        """Should read WAV file metadata."""
        osc = Oscillator(Waveform.SINE, frequency=440.0, sample_rate=44100)
        samples = normalize(osc.generate(0.5))
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            filepath = f.name
        try:
            writer = WavWriter(sample_rate=44100)
            writer.write(filepath, samples)
            info = get_audio_info(filepath)
            assert info.format == 'wav'
            assert info.sample_rate == 44100
            assert info.num_channels == 1
            assert info.bits_per_sample == 16
            assert info.num_samples == len(samples)
            assert abs(info.duration_seconds - 0.5) < 0.01
        finally:
            os.unlink(filepath)

    def test_audio_info_properties(self):
        """AudioInfo should have correct default properties."""
        info = AudioInfo()
        assert info.sample_rate == 44100
        assert info.num_channels == 1
        assert info.bits_per_sample == 16
        assert info.format == 'wav'
        assert info.duration_seconds == 0.0

    def test_audio_info_repr(self):
        """AudioInfo repr should be informative."""
        info = AudioInfo(sample_rate=48000, num_channels=2)
        assert '48000' in repr(info)
        assert '2' in repr(info)
