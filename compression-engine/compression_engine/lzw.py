"""LZW (Lempel-Ziv-Welch) compression codec with CRC32 integrity.

Uses GIF-style "early change" convention for code width transitions:
when the next code to be assigned equals (1 << current_width), the
code width increases by 1 BEFORE the next code is written/read.

Both encoder and decoder track next_code identically, ensuring
synchronization without off-by-one errors.

Features:
- Variable code width (starts at 9 bits, grows up to max_bits)
- Dictionary reset when full (CLEAR_CODE)
- Full CRC32 integrity verification
"""

from __future__ import annotations

from .base import Codec, FormatError, compute_crc32, verify_crc32
from .bitio import BitReader, BitWriter

CLEAR_CODE = 256
EOF_CODE = 257
FIRST_CODE = 258


class LZWCodec(Codec):
    """LZW compression codec with GIF-style early-change width transitions.

    Format:
    - 4 bytes: original data length (LE)
    - 4 bytes: CRC32 of original data (LE)
    - 1 byte: max_bits (9-16)
    - Compressed bitstream
    """

    name = "lzw"

    def __init__(self, max_bits: int = 16) -> None:
        if not 9 <= max_bits <= 16:
            raise ValueError(f"max_bits must be 9-16, got {max_bits}")
        self.max_bits = max_bits

    def compress(self, data: bytes) -> bytes:
        if len(data) > 0xFFFFFFFF:
            raise ValueError("Data too large for LZW codec (max ~4GB)")

        checksum = compute_crc32(data)
        writer = BitWriter()

        for shift in range(0, 32, 8):
            writer.write_byte((len(data) >> shift) & 0xFF)
        for shift in range(0, 32, 8):
            writer.write_byte((checksum >> shift) & 0xFF)
        writer.write_byte(self.max_bits)

        if not data:
            writer.write_bits(EOF_CODE, 9)
            return writer.flush()

        table: dict[bytes, int] = {bytes([i]): i for i in range(256)}
        next_code = FIRST_CODE
        code_width = 9

        writer.write_bits(CLEAR_CODE, code_width)
        current = bytes([data[0]])

        for i in range(1, len(data)):
            candidate = current + bytes([data[i]])
            if candidate in table:
                current = candidate
            else:
                writer.write_bits(table[current], code_width)

                if next_code <= (1 << self.max_bits) - 1:
                    table[candidate] = next_code
                    next_code += 1

                    # Early change: bump width when next code won't fit
                    if next_code > (1 << code_width) and code_width < self.max_bits:
                        code_width += 1
                else:
                    writer.write_bits(CLEAR_CODE, code_width)
                    table = {bytes([j]): j for j in range(256)}
                    code_width = 9
                    next_code = FIRST_CODE

                current = bytes([data[i]])

        writer.write_bits(table[current], code_width)
        writer.write_bits(EOF_CODE, code_width)
        return writer.flush()

    def decompress(self, data: bytes) -> bytes:
        reader = BitReader(data)

        orig_len = 0
        for shift in range(0, 32, 8):
            orig_len |= reader.read_byte() << shift
        expected_checksum = 0
        for shift in range(0, 32, 8):
            expected_checksum |= reader.read_byte() << shift
        max_bits = reader.read_byte()

        if not (9 <= max_bits <= 16):
            raise FormatError(f"Invalid max_bits: {max_bits}")

        if orig_len == 0:
            verify_crc32(b"", expected_checksum, "LZW empty data")
            return b""

        table: dict[int, bytes] = {i: bytes([i]) for i in range(256)}
        next_code = FIRST_CODE
        code_width = 9
        result = bytearray()

        # Read and verify initial CLEAR code
        code = reader.read_bits(code_width)
        if code != CLEAR_CODE:
            raise FormatError(f"Expected CLEAR_CODE, got {code}")

        # Read first data code - this one does NOT generate a table entry
        prev_code = reader.read_bits(code_width)
        if prev_code == EOF_CODE:
            verify_crc32(bytes(result[:orig_len]), expected_checksum, "LZW early EOF")
            return bytes(result[:orig_len])
        if prev_code > 255:
            raise FormatError(f"Invalid first code: {prev_code}")

        prev_entry = table[prev_code]
        result.extend(prev_entry)

        while len(result) < orig_len:
            # Check if we need to bump width BEFORE reading next code.
            # The encoder bumps after adding entry (next_code > threshold).
            # The decoder is one behind, so we use next_code+1 > threshold,
            # which is equivalent to next_code >= threshold.
            # Wait — let me think again. The encoder bumps when next_code
            # exceeds (1 << width). The decoder has next_code one less than
            # encoder at the same point. So decoder should bump when
            # (next_code + 1) > (1 << code_width), i.e., next_code >= (1 << code_width).
            if next_code >= (1 << code_width) and code_width < max_bits:
                code_width += 1

            code = reader.read_bits(code_width)

            if code == EOF_CODE:
                break

            if code == CLEAR_CODE:
                table = {i: bytes([i]) for i in range(256)}
                code_width = 9
                next_code = FIRST_CODE

                prev_code = reader.read_bits(code_width)
                if prev_code == EOF_CODE:
                    break
                if prev_code > 255:
                    raise FormatError(f"Invalid code after CLEAR: {prev_code}")
                prev_entry = table[prev_code]
                result.extend(prev_entry)
                continue

            if code in table:
                entry = table[code]
            elif code == next_code:
                entry = prev_entry + bytes([prev_entry[0]])
            else:
                raise FormatError(f"Invalid LZW code: {code} (next_code={next_code})")

            result.extend(entry)

            if next_code <= (1 << max_bits) - 1:
                table[next_code] = prev_entry + bytes([entry[0]])
                next_code += 1

            prev_entry = entry

        result_bytes = bytes(result[:orig_len])
        verify_crc32(result_bytes, expected_checksum, "LZW decompression")
        return result_bytes