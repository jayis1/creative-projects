"""Run-Length Encoding (RLE) codec with CRC32 integrity.

A simple but effective pre-processing step for data with many repeated
bytes, especially useful when chained before Huffman or other codecs.
"""

from __future__ import annotations

import struct
import zlib
from typing import Optional
from .bitio import BitReader, BitWriter


class RLECodec:
    """Run-Length Encoding codec.

    Format:
    - 4 bytes: original data length (little-endian)
    - 4 bytes: CRC32 checksum of original data (little-endian)
    - Encoded stream:
      - Non-special bytes: output as-is
      - Special byte (0xFF): always followed by:
        - count byte: 0 = literal 0xFF byte
        - count byte: N (1-253) = run of N+2 identical bytes that follow
        - count byte: 0xFE = literal 0xFF followed by another 0xFF (double 0xFF)
        - count byte: 0xFF = reserved (unused)
      To disambiguate: when the encoder sees a run of 3+ identical bytes
      (any value including 0xFF), it emits: 0xFF, value, count where
      count = run_length - 2. Single and double bytes are emitted literally
      (except 0xFF which needs the escape sequence).
    """

    ESCAPE = 0xFF

    def compress(self, data: bytes) -> bytes:
        """Compress data using RLE."""
        checksum = zlib.crc32(data) & 0xFFFFFFFF

        if not data:
            return struct.pack("<II", 0, checksum)

        result = bytearray()
        result.extend(struct.pack("<II", len(data), checksum))

        i = 0
        n = len(data)
        while i < n:
            b = data[i]
            # Count the run length
            run = 1
            while i + run < n and data[i + run] == b and run < 255:
                run += 1

            if run >= 3:
                # Emit as run: escape + byte + (run-2)
                result.append(self.ESCAPE)
                result.append(b)
                result.append(run - 2)
                i += run
            elif b == self.ESCAPE:
                # Escape the escape byte: escape + escape + 0
                for _ in range(run):
                    result.append(self.ESCAPE)
                    result.append(self.ESCAPE)
                    result.append(0)
                i += run
            else:
                # Single or double non-escape byte, emit literally
                for _ in range(run):
                    result.append(b)
                i += run

        return bytes(result)

    def decompress(self, data: bytes) -> bytes:
        """Decompress RLE-encoded data."""
        if len(data) < 8:
            raise ValueError("RLE data too short for header")

        orig_len, checksum = struct.unpack("<II", data[:8])

        if orig_len == 0:
            # Verify checksum of empty data
            if checksum != zlib.crc32(b"") & 0xFFFFFFFF:
                raise ValueError("CRC32 checksum mismatch")
            return b""

        payload = data[8:]
        result = bytearray()
        i = 0
        n = len(payload)

        while i < n and len(result) < orig_len:
            b = payload[i]
            if b == self.ESCAPE:
                # Escape sequence: next byte is value, then count
                if i + 2 >= n:
                    raise ValueError("Incomplete RLE escape sequence at end of data")
                value = payload[i + 1]
                count_byte = payload[i + 2]
                if count_byte == 0:
                    # Single literal escape byte (value should be 0xFF)
                    result.append(value)
                    i += 3
                else:
                    # Run of count_byte + 2 identical bytes
                    count = count_byte + 2
                    result.extend([value] * count)
                    i += 3
            else:
                # Regular byte, emit as-is
                result.append(b)
                i += 1

        # Verify length and checksum
        result_bytes = bytes(result[:orig_len])
        if len(result_bytes) != orig_len:
            raise ValueError(f"Length mismatch: expected {orig_len}, got {len(result_bytes)}")
        actual_checksum = zlib.crc32(result_bytes) & 0xFFFFFFFF
        if actual_checksum != checksum:
            raise ValueError(f"CRC32 checksum mismatch: expected {checksum:#010x}, got {actual_checksum:#010x}")

        return result_bytes