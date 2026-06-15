"""Bit-level I/O for compression codecs."""

import struct
from typing import Optional


class BitWriter:
    """Write individual bits to a byte buffer, MSB first."""

    def __init__(self) -> None:
        self._buffer: bytearray = bytearray()
        self._current_byte: int = 0
        self._bit_pos: int = 7  # MSB first: 7=most significant, 0=least

    def write_bit(self, bit: int) -> None:
        """Write a single bit (0 or 1)."""
        if bit:
            self._current_byte |= (1 << self._bit_pos)
        self._bit_pos -= 1
        if self._bit_pos < 0:
            self._buffer.append(self._current_byte)
            self._current_byte = 0
            self._bit_pos = 7

    def write_bits(self, value: int, num_bits: int) -> None:
        """Write `num_bits` bits from `value`, MSB first."""
        for i in range(num_bits - 1, -1, -1):
            self.write_bit((value >> i) & 1)

    def write_byte(self, byte: int) -> None:
        """Write a full byte (8 bits)."""
        self.write_bits(byte & 0xFF, 8)

    def write_bytes(self, data: bytes) -> None:
        """Write a sequence of bytes."""
        for b in data:
            self.write_byte(b)

    def write_uint16_le(self, value: int) -> None:
        """Write a 16-bit unsigned integer in little-endian."""
        self.write_byte(value & 0xFF)
        self.write_byte((value >> 8) & 0xFF)

    def flush(self) -> bytes:
        """Flush remaining bits (pad with zeros) and return the complete byte sequence."""
        if self._bit_pos < 7:
            self._buffer.append(self._current_byte)
            self._current_byte = 0
            self._bit_pos = 7
        return bytes(self._buffer)

    @property
    def bit_length(self) -> int:
        """Total number of bits written."""
        return len(self._buffer) * 8 + (7 - self._bit_pos)


class BitReader:
    """Read individual bits from a byte buffer, MSB first."""

    def __init__(self, data: bytes) -> None:
        self._data: bytes = data
        self._byte_pos: int = 0
        self._bit_pos: int = 7

    def read_bit(self) -> int:
        """Read a single bit. Raises EOFError if no bits remain."""
        if self._byte_pos >= len(self._data):
            raise EOFError("No more bits to read")
        bit = (self._data[self._byte_pos] >> self._bit_pos) & 1
        self._bit_pos -= 1
        if self._bit_pos < 0:
            self._byte_pos += 1
            self._bit_pos = 7
        return bit

    def read_bits(self, num_bits: int) -> int:
        """Read `num_bits` bits and return as integer, MSB first."""
        value = 0
        for _ in range(num_bits):
            value = (value << 1) | self.read_bit()
        return value

    def read_byte(self) -> int:
        """Read a full byte (8 bits)."""
        return self.read_bits(8)

    def read_bytes(self, count: int) -> bytes:
        """Read `count` bytes."""
        return bytes(self.read_byte() for _ in range(count))

    def read_uint16_le(self) -> int:
        """Read a 16-bit unsigned integer in little-endian."""
        low = self.read_byte()
        high = self.read_byte()
        return (high << 8) | low

    @property
    def bits_remaining(self) -> int:
        """Number of bits remaining to read."""
        if self._byte_pos >= len(self._data):
            return 0
        return (len(self._data) - self._byte_pos - 1) * 8 + self._bit_pos + 1

    @property
    def is_finished(self) -> bool:
        """Whether all bits have been read."""
        return self._byte_pos >= len(self._data)