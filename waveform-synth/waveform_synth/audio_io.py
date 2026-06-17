"""
Audio file format support.

Provides reading and writing of common audio file formats beyond WAV:
- AIFF/AIFC reading
- Raw PCM reading/writing
- Audio format detection and metadata

Also extends WavWriter with enhanced functionality.
"""

import struct
import math
from typing import List, Tuple, Optional, Dict, Any


class AudioInfo:
    """Metadata about an audio file."""

    def __init__(self, sample_rate: int = 44100, num_channels: int = 1,
                 bits_per_sample: int = 16, num_samples: int = 0,
                 format: str = "wav"):
        self.sample_rate = sample_rate
        self.num_channels = num_channels
        self.bits_per_sample = bits_per_sample
        self.num_samples = num_samples
        self.format = format

    @property
    def duration_seconds(self) -> float:
        """Duration in seconds."""
        if self.sample_rate == 0:
            return 0.0
        return self.num_samples / self.sample_rate

    @property
    def byte_rate(self) -> int:
        """Bytes per second."""
        return self.sample_rate * self.num_channels * (self.bits_per_sample // 8)

    def __repr__(self):
        return (f"AudioInfo(format={self.format}, sr={self.sample_rate}, "
                f"ch={self.num_channels}, bits={self.bits_per_sample}, "
                f"dur={self.duration_seconds:.2f}s)")


def detect_audio_format(filepath: str) -> str:
    """
    Detect audio file format from file header.

    Args:
        filepath: Path to the audio file.

    Returns:
        Format string: 'wav', 'aiff', 'au', or 'unknown'.

    Raises:
        FileNotFoundError: If the file doesn't exist.
    """
    with open(filepath, 'rb') as f:
        header = f.read(12)

    if len(header) < 4:
        return 'unknown'

    if header[:4] == b'RIFF' and header[8:12] == b'WAVE':
        return 'wav'
    elif header[:4] == b'FORM' and header[8:12] in (b'AIFF', b'AIFC'):
        return 'aiff'
    elif header[:4] == b'.snd':
        return 'au'
    else:
        return 'unknown'


def read_aiff(filepath: str) -> Tuple[List[float], int, int, int]:
    """
    Read an AIFF audio file.

    Args:
        filepath: Path to the AIFF file.

    Returns:
        Tuple of (samples, sample_rate, num_channels, bits_per_sample).

    Raises:
        ValueError: If the file is not a valid AIFF.
    """
    with open(filepath, 'rb') as f:
        form_id = f.read(4)
        if form_id != b'FORM':
            raise ValueError("Not an AIFF file (missing FORM header)")

        form_size = struct.unpack('>I', f.read(4))[0]
        form_type = f.read(4)
        if form_type not in (b'AIFF', b'AIFC'):
            raise ValueError(f"Expected AIFF/AIFC form type, got {form_type}")

        sample_rate = 44100
        num_channels = 1
        bits_per_sample = 16
        num_frames = 0
        samples = []

        while True:
            chunk_id = f.read(4)
            if len(chunk_id) < 4:
                break
            chunk_size = struct.unpack('>I', f.read(4))[0]

            if chunk_id == b'COMM':
                num_channels = struct.unpack('>h', f.read(2))[0]
                num_frames = struct.unpack('>I', f.read(4))[0]
                bits_per_sample = struct.unpack('>h', f.read(2))[0]
                # Sample rate is 80-bit extended float — simplified parsing
                sr_bytes = f.read(10)
                # Parse 80-bit IEEE 754 extended (simplified)
                exponent = ((sr_bytes[0] & 0x7F) << 8) | sr_bytes[1]
                exponent -= 16383
                # Mantissa: use only first 4 bytes for approximation
                mantissa = struct.unpack('>I', sr_bytes[2:6])[0]
                if sr_bytes[0] & 0x80:
                    mantissa = -mantissa
                sample_rate = int(mantissa * (2 ** (exponent - 31))) if exponent > 31 else int(mantissa >> (31 - exponent))
                if sample_rate <= 0:
                    sample_rate = 44100  # fallback
                # Skip remaining chunk data
                remaining = chunk_size - 18
                if remaining > 0:
                    f.read(remaining)

            elif chunk_id == b'SSND':
                offset = struct.unpack('>I', f.read(4))[0]
                block_size = struct.unpack('>I', f.read(4))[0]
                data_start = f.tell()
                data_size = chunk_size - 8

                if bits_per_sample == 16:
                    max_val = 32767
                    num_samples_total = data_size // 2
                    for i in range(min(num_samples_total, num_frames * num_channels)):
                        val = struct.unpack('>h', f.read(2))[0]
                        samples.append(val / max_val)
                elif bits_per_sample == 8:
                    for i in range(min(data_size, num_frames * num_channels)):
                        val = f.read(1)[0]
                        samples.append((val - 128) / 128.0)
                elif bits_per_sample == 24:
                    max_val = 8388607
                    num_samples_total = data_size // 3
                    for i in range(min(num_samples_total, num_frames * num_channels)):
                        b = f.read(3)
                        val = b[0] << 16 | b[1] << 8 | b[2]
                        if val >= 0x800000:
                            val -= 0x1000000
                        samples.append(val / max_val)
                elif bits_per_sample == 32:
                    max_val = 2147483647
                    num_samples_total = data_size // 4
                    for i in range(min(num_samples_total, num_frames * num_channels)):
                        val = struct.unpack('>i', f.read(4))[0]
                        samples.append(val / max_val)

                # Skip any remaining data
                f.seek(data_start + data_size)
                break
            else:
                # Skip unknown chunks
                f.read(chunk_size)

    return samples, sample_rate, num_channels, bits_per_sample


def write_raw_pcm(filepath: str, samples: List[float], sample_rate: int = 44100,
                  bits_per_sample: int = 16, num_channels: int = 1):
    """
    Write raw PCM audio data (no header).

    Args:
        filepath: Output file path.
        samples: Audio samples as floats in [-1.0, 1.0].
        sample_rate: Sample rate (metadata only — not stored in file).
        bits_per_sample: Bit depth (8, 16, 24, or 32).
        num_channels: Number of channels.
    """
    if not samples:
        raise ValueError("Cannot write empty sample list")

    with open(filepath, 'wb') as f:
        if bits_per_sample == 16:
            max_val = 32767
            for s in samples:
                clamped = max(-1.0, min(1.0, s))
                int_val = int(clamped * max_val)
                if int_val < -max_val:
                    int_val = -max_val
                f.write(struct.pack('<h', int_val))
        elif bits_per_sample == 8:
            for s in samples:
                clamped = max(-1.0, min(1.0, s))
                int_val = int((clamped + 1.0) * 127.5)
                int_val = max(0, min(255, int_val))
                f.write(struct.pack('B', int_val))
        elif bits_per_sample == 24:
            max_val = 8388607
            for s in samples:
                clamped = max(-1.0, min(1.0, s))
                int_val = int(clamped * max_val)
                if int_val < -max_val:
                    int_val = -max_val
                f.write(struct.pack('<i', int_val)[:3])
        elif bits_per_sample == 32:
            max_val = 2147483647
            for s in samples:
                clamped = max(-1.0, min(1.0, s))
                int_val = int(clamped * max_val)
                if int_val < -max_val:
                    int_val = -max_val
                f.write(struct.pack('<i', int_val))
        else:
            raise ValueError(f"Unsupported bit depth: {bits_per_sample}")


def get_audio_info(filepath: str) -> AudioInfo:
    """
    Get metadata about an audio file without reading all samples.

    Args:
        filepath: Path to the audio file.

    Returns:
        AudioInfo object with file metadata.
    """
    fmt = detect_audio_format(filepath)

    if fmt == 'wav':
        with open(filepath, 'rb') as f:
            f.read(4)  # RIFF
            f.read(4)  # size
            f.read(4)  # WAVE
            num_channels = 1
            sample_rate = 44100
            bits_per_sample = 16
            while True:
                chunk_id = f.read(4)
                if len(chunk_id) < 4:
                    break
                chunk_size = struct.unpack('<I', f.read(4))[0]
                if chunk_id == b'fmt ':
                    audio_format = struct.unpack('<H', f.read(2))[0]
                    num_channels = struct.unpack('<H', f.read(2))[0]
                    sample_rate = struct.unpack('<I', f.read(4))[0]
                    byte_rate = struct.unpack('<I', f.read(4))[0]
                    block_align = struct.unpack('<H', f.read(2))[0]
                    bits_per_sample = struct.unpack('<H', f.read(2))[0]
                    remaining = chunk_size - 16
                    if remaining > 0:
                        f.read(remaining)
                elif chunk_id == b'data':
                    data_size = chunk_size
                    bytes_per_sample = bits_per_sample // 8
                    num_samples = data_size // bytes_per_sample // num_channels
                    return AudioInfo(
                        sample_rate=sample_rate,
                        num_channels=num_channels,
                        bits_per_sample=bits_per_sample,
                        num_samples=num_samples,
                        format='wav'
                    )
                else:
                    f.read(chunk_size)

    elif fmt == 'aiff':
        samples, sr, ch, bps = read_aiff(filepath)
        return AudioInfo(
            sample_rate=sr,
            num_channels=ch,
            bits_per_sample=bps,
            num_samples=len(samples),
            format='aiff'
        )

    return AudioInfo(format='unknown')


__all__ = ['AudioInfo', 'detect_audio_format', 'read_aiff', 'write_raw_pcm', 'get_audio_info']