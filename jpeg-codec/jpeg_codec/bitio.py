"""Bit-level I/O for JPEG entropy coding.

JPEG stores Huffman-coded data as a packed bit-stream, MSB first.  A
special byte-stuffing rule applies: whenever a 0xFF byte is emitted, a
following 0x00 byte is inserted so the decoder can distinguish stuffed
0x00 from real JPEG markers (which always have a non-zero second byte).

This module provides :class:`BitWriter` and :class:`BitReader`.
"""

import numpy as np


class BitWriter:
    """Write individual bits into a bytearray, MSB-first, with JPEG
    byte-stuffing (0xFF -> 0xFF 0x00) and optional padding flush.
    """

    def __init__(self):
        self._data = bytearray()
        self._cur = 0
        self._nbits = 0

    def write_bits(self, value: int, n: int):
        """Write the low *n* bits of *value*, MSB first."""
        if n == 0:
            return
        for i in range(n - 1, -1, -1):
            bit = (value >> i) & 1
            self._cur = (self._cur << 1) | bit
            self._nbits += 1
            if self._nbits == 8:
                self._flush_byte()

    def _flush_byte(self):
        b = self._cur & 0xFF
        self._data.append(b)
        if b == 0xFF:
            self._data.append(0x00)  # byte stuffing
        self._cur = 0
        self._nbits = 0

    def flush(self):
        """Pad the remaining bits with 1-bits and flush the final byte."""
        if self._nbits > 0:
            # Pad with 1s (JPEG standard).
            pad = 8 - self._nbits
            self._cur = (self._cur << pad) | ((1 << pad) - 1)
            self._nbits = 8
            self._flush_byte()

    def get_bytes(self) -> bytes:
        return bytes(self._data)

    def reset(self) -> None:
        """Reset the writer to a fresh state (after flush + get_bytes).

        This allows the encoder to insert raw marker bytes between
        restart intervals by extracting each segment separately.
        """
        self._data = bytearray()
        self._cur = 0
        self._nbits = 0


class BitReader:
    """Read bits MSB-first from a bytes buffer, undoing JPEG byte-stuffing.

    Raises :class:`EOFError` when bits are exhausted.
    """

    def __init__(self, data: bytes, start: int = 0):
        self._data = data
        self._pos = start
        self._cur = 0
        self._nbits = 0

    def _fill(self):
        """Load the next byte into the bit buffer, skipping stuffed 0x00."""
        if self._pos >= len(self._data):
            raise EOFError("Bit stream exhausted")
        b = self._data[self._pos]
        self._pos += 1
        if b == 0xFF:
            if self._pos < len(self._data):
                nxt = self._data[self._pos]
                if nxt == 0x00:
                    # Stuffed zero: consume it, keep 0xFF.
                    self._pos += 1
                elif nxt == 0xFF:
                    # Fill bytes (0xFF 0xFF ...) -- skip per JPEG.
                    return self._fill()
                else:
                    # A real marker: we've hit the end of the scan data.
                    self._pos -= 1  # back up so caller can see it
                    raise EOFError("Encountered marker in bit stream")
            else:
                raise EOFError("Bit stream exhausted after 0xFF")
        self._cur = (self._cur << 8) | b
        self._nbits += 8

    def read_bit(self) -> int:
        if self._nbits == 0:
            self._fill()
        self._nbits -= 1
        return (self._cur >> self._nbits) & 1

    def read_bits(self, n: int) -> int:
        if n == 0:
            return 0
        while self._nbits < n:
            self._fill()
        self._nbits -= n
        return (self._cur >> self._nbits) & ((1 << n) - 1)

    @property
    def position(self) -> int:
        return self._pos