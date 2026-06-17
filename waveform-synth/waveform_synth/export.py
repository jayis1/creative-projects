"""
WAV file export and import.

Writes audio samples as standard PCM WAV files (8, 16, 24, 32-bit).
Supports mono and stereo output with configurable sample rate.
Also reads WAV files for analysis and visualization.
"""

import struct
from typing import List, Tuple, Optional


class WavWriter:
    """
    Writes audio samples to WAV files.

    Args:
        sample_rate: Samples per second (default 44100).
        num_channels: Number of channels (default 1 = mono).
        bits_per_sample: Bit depth (default 16).
    """

    def __init__(self, sample_rate: int = 44100, num_channels: int = 1, bits_per_sample: int = 16):
        if sample_rate <= 0:
            raise ValueError(f"Sample rate must be > 0, got {sample_rate}")
        if num_channels not in (1, 2):
            raise ValueError(f"Only 1 or 2 channels supported, got {num_channels}")
        if bits_per_sample not in (8, 16, 24, 32):
            raise ValueError(f"Bits per sample must be 8, 16, 24, or 32, got {bits_per_sample}")

        self.sample_rate = sample_rate
        self.num_channels = num_channels
        self.bits_per_sample = bits_per_sample

    def _samples_to_bytes(self, samples: List[float]) -> bytes:
        """Convert float samples in [-1.0, 1.0] to PCM byte data."""
        byte_data = bytearray()

        if self.bits_per_sample == 16:
            max_val = 32767
            for s in samples:
                # Clamp to [-1.0, 1.0]
                clamped = max(-1.0, min(1.0, s))
                int_val = int(clamped * max_val)
                # Handle the edge case of -1.0 mapping to -32768
                if int_val < -max_val:
                    int_val = -max_val
                byte_data.extend(struct.pack('<h', int_val))

        elif self.bits_per_sample == 8:
            for s in samples:
                clamped = max(-1.0, min(1.0, s))
                # 8-bit PCM is unsigned (0-255, center at 128)
                int_val = int((clamped + 1.0) * 127.5)
                int_val = max(0, min(255, int_val))
                byte_data.extend(struct.pack('B', int_val))

        elif self.bits_per_sample == 24:
            max_val = 8388607  # 2^23 - 1
            for s in samples:
                clamped = max(-1.0, min(1.0, s))
                int_val = int(clamped * max_val)
                if int_val < -max_val:
                    int_val = -max_val
                # 24-bit as 3 bytes, little-endian
                byte_data.extend(struct.pack('<i', int_val)[:3])

        elif self.bits_per_sample == 32:
            max_val = 2147483647  # 2^31 - 1
            for s in samples:
                clamped = max(-1.0, min(1.0, s))
                int_val = int(clamped * max_val)
                if int_val < -max_val:
                    int_val = -max_val
                byte_data.extend(struct.pack('<i', int_val))

        return bytes(byte_data)

    def write(self, filepath: str, samples: List[float]) -> None:
        """
        Write audio samples to a WAV file.

        Args:
            filepath: Output file path.
            samples: Audio samples as floats in [-1.0, 1.0].

        Raises:
            ValueError: If samples is empty.
        """
        if not samples:
            raise ValueError("Cannot write empty sample list to WAV file")

        byte_data = self._samples_to_bytes(samples)
        data_size = len(byte_data)
        byte_rate = self.sample_rate * self.num_channels * (self.bits_per_sample // 8)
        block_align = self.num_channels * (self.bits_per_sample // 8)

        # WAV file format:
        # RIFF header (12 bytes) + fmt chunk (24 bytes) + data chunk header (8 bytes) + data
        fmt_chunk_size = 16
        file_size = 4 + (8 + fmt_chunk_size) + (8 + data_size)

        with open(filepath, 'wb') as f:
            # RIFF header
            f.write(b'RIFF')
            f.write(struct.pack('<I', file_size))
            f.write(b'WAVE')

            # fmt chunk
            f.write(b'fmt ')
            f.write(struct.pack('<I', fmt_chunk_size))
            f.write(struct.pack('<H', 1))  # PCM format
            f.write(struct.pack('<H', self.num_channels))
            f.write(struct.pack('<I', self.sample_rate))
            f.write(struct.pack('<I', byte_rate))
            f.write(struct.pack('<H', block_align))
            f.write(struct.pack('<H', self.bits_per_sample))

            # data chunk
            f.write(b'data')
            f.write(struct.pack('<I', data_size))
            f.write(byte_data)

    @staticmethod
    def samples_from_wav(filepath: str) -> tuple:
        """
        Read a WAV file and return (samples, sample_rate, num_channels, bits_per_sample).

        Supports 8, 16, 24, and 32-bit PCM WAV files.

        Args:
            filepath: Path to WAV file.

        Returns:
            Tuple of (samples as float list, sample_rate, num_channels, bits_per_sample).

        Raises:
            ValueError: If the file is not a valid PCM WAV.
            FileNotFoundError: If the file doesn't exist.
        """
        with open(filepath, 'rb') as f:
            # Read RIFF header
            riff_id = f.read(4)
            if riff_id != b'RIFF':
                raise ValueError(f"Not a RIFF file: {riff_id}")
            file_size = struct.unpack('<I', f.read(4))[0]
            wave_id = f.read(4)
            if wave_id != b'WAVE':
                raise ValueError(f"Not a WAVE file: {wave_id}")

            fmt_found = False
            audio_format = 0
            num_channels = 0
            sample_rate = 0
            bits_per_sample = 0
            samples = []

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
                    # Read any remaining fmt data
                    remaining = chunk_size - 16
                    if remaining > 0:
                        f.read(remaining)
                    fmt_found = True
                elif chunk_id == b'data':
                    if not fmt_found:
                        raise ValueError("data chunk found before fmt chunk")
                    if audio_format != 1:
                        raise ValueError(f"Only PCM (format 1) supported, got format {audio_format}")

                    data = f.read(chunk_size)
                    bytes_per_sample = bits_per_sample // 8

                    if bits_per_sample == 16:
                        max_val = 32767
                        for i in range(0, len(data), 2):
                            int_val = struct.unpack('<h', data[i:i+2])[0]
                            samples.append(int_val / max_val)

                    elif bits_per_sample == 8:
                        for b in data:
                            # 8-bit PCM is unsigned (0-255, center at 128)
                            samples.append((b - 128) / 128.0)

                    elif bits_per_sample == 24:
                        max_val = 8388607
                        for i in range(0, len(data), 3):
                            b = data[i:i+3]
                            # Sign-extend 24-bit to 32-bit
                            int_val = int.from_bytes(b, byteorder='little', signed=True)
                            # Actually, let's handle this correctly
                            int_val = b[0] | (b[1] << 8) | (b[2] << 16)
                            if int_val >= 0x800000:  # negative
                                int_val -= 0x1000000
                            samples.append(int_val / max_val)

                    elif bits_per_sample == 32:
                        max_val = 2147483647
                        for i in range(0, len(data), 4):
                            int_val = struct.unpack('<i', data[i:i+4])[0]
                            samples.append(int_val / max_val)

                    break  # We got the data
                else:
                    # Skip unknown chunks
                    f.read(chunk_size)

            return samples, sample_rate, num_channels, bits_per_sample

    def write_stereo(self, filepath: str, left: List[float], right: List[float]) -> None:
        """
        Write stereo audio to a WAV file.

        Args:
            filepath: Output file path.
            left: Left channel samples (floats in [-1.0, 1.0]).
            right: Right channel samples (must be same length as left).

        Raises:
            ValueError: If channels have different lengths.
        """
        if len(left) != len(right):
            raise ValueError(f"Channel lengths must match: left={len(left)}, right={len(right)}")
        if not left:
            raise ValueError("Cannot write empty sample list to WAV file")

        # Interleave channels
        interleaved = []
        for l, r in zip(left, right):
            interleaved.append(l)
            interleaved.append(r)

        byte_data = self._samples_to_bytes(interleaved)
        data_size = len(byte_data)
        byte_rate = self.sample_rate * self.num_channels * (self.bits_per_sample // 8)
        block_align = self.num_channels * (self.bits_per_sample // 8)

        # Override channels for stereo
        channels = 2
        byte_rate_stereo = self.sample_rate * 2 * (self.bits_per_sample // 8)
        block_align_stereo = 2 * (self.bits_per_sample // 8)

        fmt_chunk_size = 16
        file_size = 4 + (8 + fmt_chunk_size) + (8 + data_size)

        with open(filepath, 'wb') as f:
            # RIFF header
            f.write(b'RIFF')
            f.write(struct.pack('<I', file_size))
            f.write(b'WAVE')

            # fmt chunk
            f.write(b'fmt ')
            f.write(struct.pack('<I', fmt_chunk_size))
            f.write(struct.pack('<H', 1))  # PCM format
            f.write(struct.pack('<H', channels))
            f.write(struct.pack('<I', self.sample_rate))
            f.write(struct.pack('<I', byte_rate_stereo))
            f.write(struct.pack('<H', block_align_stereo))
            f.write(struct.pack('<H', self.bits_per_sample))

            # data chunk
            f.write(b'data')
            f.write(struct.pack('<I', data_size))
            f.write(byte_data)