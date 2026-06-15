"""LZ77 sliding-window compression codec with CRC32 integrity."""

from __future__ import annotations

import zlib
from typing import List, Tuple
from .bitio import BitReader, BitWriter


class LZ77Codec:
    """LZ77 compression with configurable window size and min match length.

    Token format:
    - Literal byte: flag=0, 8-bit byte value
    - Match: flag=1, offset (variable bits), length (variable bits)

    The offset and length bit widths are chosen based on window_size.

    Header format:
    - 4 bytes: original data length (little-endian)
    - 4 bytes: CRC32 checksum of original data (little-endian)
    - 5 bits: offset bit width
    - 5 bits: length bit width
    - 8 bits: min_match value (stored so decompressor knows the offset)
    """

    def __init__(self, window_size: int = 4096, min_match: int = 3, max_match: int = 258) -> None:
        self.window_size = window_size
        self.min_match = min_match
        self.max_match = max_match
        # Calculate bit widths
        self._offset_bits = (window_size - 1).bit_length()
        self._length_bits = (max_match - min_match).bit_length() if max_match > min_match else 1

    def compress(self, data: bytes) -> bytes:
        """Compress data using LZ77."""
        checksum = zlib.crc32(data) & 0xFFFFFFFF

        writer = BitWriter()
        # Write 4-byte original length
        for shift in range(0, 32, 8):
            writer.write_byte((len(data) >> shift) & 0xFF)
        # Write 4-byte CRC32
        for shift in range(0, 32, 8):
            writer.write_byte((checksum >> shift) & 0xFF)

        if not data:
            return writer.flush()

        writer.write_bits(self._offset_bits, 5)
        writer.write_bits(self._length_bits, 5)
        # Store min_match so decompressor can reconstruct it
        writer.write_byte(self.min_match)

        i = 0
        while i < len(data):
            best_offset = 0
            best_length = 0
            # Search window
            window_start = max(0, i - self.window_size)
            # Look ahead buffer limit
            max_len = min(self.max_match, len(data) - i)
            for j in range(window_start, i):
                length = 0
                while length < max_len and data[j + length] == data[i + length]:
                    length += 1
                    # Allow match to extend into the look-ahead buffer (run-length optimization)
                    if j + length >= i:
                        pass  # the comparison above still works since data[j+length]==data[i+length]
                if length >= self.min_match and length > best_length:
                    best_length = length
                    best_offset = i - j
                    if best_length == self.max_match:
                        break
            if best_length >= self.min_match:
                # Emit match
                writer.write_bit(1)
                writer.write_bits(best_offset - 1, self._offset_bits)
                writer.write_bits(best_length - self.min_match, self._length_bits)
                i += best_length
            else:
                # Emit literal
                writer.write_bit(0)
                writer.write_byte(data[i])
                i += 1
        return writer.flush()

    def decompress(self, data: bytes) -> bytes:
        """Decompress LZ77-coded data with CRC32 verification."""
        reader = BitReader(data)
        # Read 4-byte original length
        orig_len = 0
        for shift in range(0, 32, 8):
            orig_len |= reader.read_byte() << shift
        # Read 4-byte CRC32
        expected_checksum = 0
        for shift in range(0, 32, 8):
            expected_checksum |= reader.read_byte() << shift

        if orig_len == 0:
            actual_checksum = zlib.crc32(b"") & 0xFFFFFFFF
            if actual_checksum != expected_checksum:
                raise ValueError(f"CRC32 mismatch: expected {expected_checksum:#010x}, got {actual_checksum:#010x}")
            return b""

        offset_bits = reader.read_bits(5)
        length_bits = reader.read_bits(5)
        # Read min_match from header (fix: was hardcoded to 3)
        min_match = reader.read_byte()

        result = bytearray()
        while len(result) < orig_len:
            flag = reader.read_bit()
            if flag == 0:
                # Literal
                result.append(reader.read_byte())
            else:
                # Match
                offset = reader.read_bits(offset_bits) + 1
                length = reader.read_bits(length_bits) + min_match
                for _ in range(length):
                    result.append(result[-offset])

        result_bytes = bytes(result[:orig_len])
        actual_checksum = zlib.crc32(result_bytes) & 0xFFFFFFFF
        if actual_checksum != expected_checksum:
            raise ValueError(f"CRC32 mismatch: expected {expected_checksum:#010x}, got {actual_checksum:#010x}")
        return result_bytes