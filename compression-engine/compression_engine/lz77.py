"""LZ77 sliding-window compression codec."""

from __future__ import annotations

from typing import List, Tuple
from .bitio import BitReader, BitWriter


class LZ77Codec:
    """LZ77 compression with configurable window size and min match length.

    Token format:
    - Literal byte: flag=0, 8-bit byte value
    - Match: flag=1, offset (variable bits), length (variable bits)

    The offset and length bit widths are chosen based on window_size.
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
        if not data:
            # Write header then empty
            writer = BitWriter()
            writer.write_uint16_le(0)  # original length = 0
            return writer.flush()

        writer = BitWriter()
        writer.write_uint16_le(len(data))
        writer.write_bits(self._offset_bits, 5)  # 5 bits for offset bit width (max 31)
        writer.write_bits(self._length_bits, 5)  # 5 bits for length bit width

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
                        # We wrap around: compare against what we've already encoded
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
        """Decompress LZ77-coded data."""
        reader = BitReader(data)
        orig_len = reader.read_uint16_le()
        if orig_len == 0:
            return b""
        offset_bits = reader.read_bits(5)
        length_bits = reader.read_bits(5)
        min_match = 3  # same as default

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
        return bytes(result[:orig_len])