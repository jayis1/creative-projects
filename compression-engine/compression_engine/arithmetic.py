"""Arithmetic coding codec with CRC32 integrity.

Arithmetic coding achieves near-optimal compression by encoding symbols
as fractional values within [0, 1). Unlike Huffman coding which assigns
whole bits to each symbol, arithmetic coding can use fractional bits,
making it more efficient especially for symbols with highly skewed
probabilities.

Features:
- Adaptive frequency model that updates as symbols are processed
- Full CRC32 integrity verification
- Near-optimal compression ratio for any input
"""

from __future__ import annotations

import struct
import zlib
from typing import Dict, List, Tuple

from .base import Codec, IntegrityError, FormatError, compute_crc32, verify_crc32
from .bitio import BitWriter, BitReader


# Precision constants for 32-bit arithmetic
PRECISION = 32
MAX_RANGE = (1 << PRECISION) - 1
QUARTER = 1 << (PRECISION - 2)
HALF = 1 << (PRECISION - 1)
THREE_QUARTER = QUARTER * 3


class _FrequencyModel:
    """Adaptive frequency model for arithmetic coding.

    Maintains byte frequencies and cumulative counts. Frequencies
    are updated as symbols are processed (adaptive model).
    """

    TOTAL_SYMBOLS = 257  # 256 byte values + 1 EOF

    def __init__(self) -> None:
        # Start with count of 1 for each symbol to avoid zero probabilities
        self.freq: List[int] = [1] * self.TOTAL_SYMBOLS
        self.cum_freq: List[int] = [0] * (self.TOTAL_SYMBOLS + 1)
        self._update_cum_freq()

    def _update_cum_freq(self) -> None:
        """Recalculate cumulative frequencies."""
        self.cum_freq[0] = 0
        for i in range(self.TOTAL_SYMBOLS):
            self.cum_freq[i + 1] = self.cum_freq[i] + self.freq[i]

    @property
    def total(self) -> int:
        """Total frequency count."""
        return self.cum_freq[self.TOTAL_SYMBOLS]

    def get_range(self, symbol: int) -> Tuple[int, int, int]:
        """Get (low_cum, high_cum, total) for a symbol."""
        return self.cum_freq[symbol], self.cum_freq[symbol + 1], self.total

    def update(self, symbol: int) -> None:
        """Update frequency for a symbol after encoding/decoding it."""
        self.freq[symbol] += 1
        self._update_cum_freq()
        # Rescale if total gets too large (prevents overflow)
        if self.total >= HALF:
            self._rescale()

    def _rescale(self) -> None:
        """Halve all frequencies to prevent overflow, keeping min of 1."""
        for i in range(self.TOTAL_SYMBOLS):
            self.freq[i] = max(1, self.freq[i] // 2)
        self._update_cum_freq()

    def find_symbol(self, value: int) -> Tuple[int, int, int]:
        """Find symbol for a given cumulative frequency value (for decoding).

        Returns (symbol, low_cum, high_cum).
        """
        lo, hi = 0, self.TOTAL_SYMBOLS - 1
        while lo < hi:
            mid = (lo + hi) // 2
            if self.cum_freq[mid + 1] <= value:
                lo = mid + 1
            else:
                hi = mid
        symbol = lo
        return symbol, self.cum_freq[symbol], self.cum_freq[symbol + 1]


class ArithmeticCodec(Codec):
    """Arithmetic coding codec with adaptive frequency model and CRC32 integrity.

    Format:
    - 4 bytes: original data length (little-endian)
    - 4 bytes: CRC32 checksum of original data (little-endian)
    - 4 bytes: compressed bitstream length in bytes (little-endian)
    - N bytes: compressed bitstream
    """

    name = "arithmetic"

    def compress(self, data: bytes) -> bytes:
        """Compress data using arithmetic coding."""
        if len(data) > 0xFFFFFFFF:
            raise ValueError("Data too large for arithmetic codec (max ~4GB)")

        checksum = compute_crc32(data)

        if not data:
            compressed = b""
            header = self._encode_header(0, checksum, 0)
            return header

        model = _FrequencyModel()
        low = 0
        high = MAX_RANGE
        pending_bits = 0
        output_bits: List[int] = []

        def output_bit_plus_pending(bit: int) -> None:
            nonlocal pending_bits
            output_bits.append(bit)
            for _ in range(pending_bits):
                output_bits.append(bit ^ 1)
            pending_bits = 0

        # Encode each byte then EOF (symbol 256)
        symbols = list(data) + [256]

        for symbol in symbols:
            sym_low, sym_high, total = model.get_range(symbol)
            rng = high - low + 1
            high = low + (rng * sym_high) // total - 1
            low = low + (rng * sym_low) // total

            # E1/E2/E3 normalization
            while True:
                if high < HALF:
                    output_bit_plus_pending(0)
                elif low >= HALF:
                    output_bit_plus_pending(1)
                    low -= HALF
                    high -= HALF
                elif low >= QUARTER and high < THREE_QUARTER:
                    pending_bits += 1
                    low -= QUARTER
                    high -= QUARTER
                else:
                    break
                low = low * 2
                high = high * 2 + 1

            model.update(symbol)

        # Flush: ensure final range is resolved
        pending_bits += 1
        if low < QUARTER:
            output_bit_plus_pending(0)
        else:
            output_bit_plus_pending(1)

        # Convert bits to bytes
        compressed = self._bits_to_bytes(output_bits)

        # Build output: header + compressed
        header = self._encode_header(len(data), checksum, len(compressed))
        return header + compressed

    def decompress(self, data: bytes) -> bytes:
        """Decompress arithmetic-coded data with CRC32 verification."""
        if len(data) < 12:
            raise FormatError("Data too short for arithmetic codec header")

        orig_len = int.from_bytes(data[:4], "little")
        expected_checksum = int.from_bytes(data[4:8], "little")
        compressed_len = int.from_bytes(data[8:12], "little")

        if orig_len == 0:
            verify_crc32(b"", expected_checksum, "arithmetic empty data")
            return b""

        compressed = data[12:12 + compressed_len]
        if len(compressed) != compressed_len:
            raise FormatError(
                f"Compressed data length mismatch: expected {compressed_len}, "
                f"got {len(compressed)}"
            )

        # Convert bytes to bits
        bit_stream = self._bytes_to_bits(compressed)
        bit_idx = 0

        model = _FrequencyModel()
        low = 0
        high = MAX_RANGE

        # Initialize code value from first PRECISION bits
        code = 0
        for _ in range(PRECISION):
            if bit_idx < len(bit_stream):
                code = (code << 1) | bit_stream[bit_idx]
                bit_idx += 1
            else:
                code = code << 1

        result = bytearray()

        for _ in range(orig_len):
            rng = high - low + 1
            # Scale code into current range to find cumulative frequency
            scaled = ((code - low + 1) * model.total - 1) // rng

            # Find symbol
            symbol, sym_low, sym_high = model.find_symbol(scaled)

            if symbol == 256:
                # EOF - shouldn't happen before we've read orig_len bytes
                break

            if symbol > 255:
                raise FormatError(f"Invalid symbol during decompression: {symbol}")

            result.append(symbol)

            # Update range
            high = low + (rng * sym_high) // model.total - 1
            low = low + (rng * sym_low) // model.total

            # E1/E2/E3 normalization
            while True:
                if high < HALF:
                    pass  # MSB is 0
                elif low >= HALF:
                    low -= HALF
                    high -= HALF
                    code -= HALF
                elif low >= QUARTER and high < THREE_QUARTER:
                    low -= QUARTER
                    high -= QUARTER
                    code -= QUARTER
                else:
                    break
                low = low * 2
                high = high * 2 + 1
                code = code * 2
                if bit_idx < len(bit_stream):
                    code |= bit_stream[bit_idx]
                    bit_idx += 1

            model.update(symbol)

        result_bytes = bytes(result[:orig_len])
        verify_crc32(result_bytes, expected_checksum, "arithmetic decompression")
        return result_bytes

    @staticmethod
    def _encode_header(orig_len: int, checksum: int, compressed_len: int) -> bytes:
        """Encode the arithmetic codec header."""
        header = bytearray()
        for shift in range(0, 32, 8):
            header.append((orig_len >> shift) & 0xFF)
        for shift in range(0, 32, 8):
            header.append((checksum >> shift) & 0xFF)
        for shift in range(0, 32, 8):
            header.append((compressed_len >> shift) & 0xFF)
        return bytes(header)

    @staticmethod
    def _bits_to_bytes(bits: List[int]) -> bytes:
        """Convert a list of bits to bytes, padding with zeros."""
        result = bytearray()
        for i in range(0, len(bits), 8):
            byte_val = 0
            for j in range(8):
                if i + j < len(bits):
                    byte_val |= (bits[i + j] << (7 - j))
            result.append(byte_val)
        return bytes(result)

    @staticmethod
    def _bytes_to_bits(data: bytes) -> List[int]:
        """Convert bytes to a list of bits (MSB first)."""
        bits: List[int] = []
        for byte in data:
            for i in range(7, -1, -1):
                bits.append((byte >> i) & 1)
        return bits