"""Delta encoding codec for numeric/sequential data.

Delta encoding stores the differences between consecutive values rather
than the values themselves. This is especially effective for time-series
data, sorted sequences, and audio waveforms where consecutive values are
typically close together, resulting in smaller values that compress better.
"""

from __future__ import annotations

import struct
import zlib
from typing import Optional
from .bitio import BitReader, BitWriter


class DeltaCodec:
    """Delta encoding codec.

    Format:
    - 4 bytes: original data length (little-endian)
    - 4 bytes: CRC32 checksum of original data (little-endian)
    - 1 byte: mode (0=byte-level delta, 1=uint16 LE delta, 2=uint32 LE delta)
    - First value(s) stored literally, then deltas as signed varint
    - For uint16/uint32 modes, any trailing bytes (if data length is not
      a multiple of the element size) are stored literally after the delta stream.
    """

    def __init__(self, mode: str = "auto") -> None:
        """Initialize delta codec.

        Args:
            mode: 'byte' for byte-level, 'uint16' for 16-bit LE values,
                  'uint32' for 32-bit LE values, 'auto' to auto-detect.
        """
        mode_map = {"byte": 0, "uint16": 1, "uint32": 2, "auto": -1}
        if mode not in mode_map:
            raise ValueError(f"Invalid mode: {mode}. Use 'byte', 'uint16', 'uint32', or 'auto'")
        self._mode = mode_map[mode]

    def _detect_mode(self, data: bytes) -> int:
        """Auto-detect the best delta encoding mode."""
        n = len(data)
        # Only consider uint32 if data is well-aligned and has enough values
        if n % 4 == 0 and n >= 8:
            vals = [struct.unpack_from("<I", data, i)[0] for i in range(0, min(n, 64), 4)]
            if len(vals) >= 2:
                deltas = [vals[i+1] - vals[i] for i in range(len(vals)-1)]
                if all(-128 <= d <= 127 for d in deltas):
                    return 2
        # Only consider uint16 if data is well-aligned and has enough values
        if n % 2 == 0 and n >= 4:
            vals = [struct.unpack_from("<H", data, i)[0] for i in range(0, min(n, 64), 2)]
            if len(vals) >= 2:
                deltas = [vals[i+1] - vals[i] for i in range(len(vals)-1)]
                if all(-128 <= d <= 127 for d in deltas):
                    return 1
        return 0

    def _encode_varint(self, value: int) -> bytes:
        """Encode a signed integer as a variable-length integer (zigzag + varint)."""
        # Zigzag encoding: maps signed to unsigned (0->0, -1->1, 1->2, -2->3, ...)
        unsigned = (value << 1) ^ (value >> 31) if value < 0 else (value << 1)
        result = bytearray()
        while unsigned > 0x7F:
            result.append((unsigned & 0x7F) | 0x80)
            unsigned >>= 7
        result.append(unsigned & 0x7F)
        return bytes(result)

    def _decode_varint(self, data: bytes, offset: int) -> tuple:
        """Decode a varint from data at offset. Returns (value, new_offset)."""
        unsigned = 0
        shift = 0
        while offset < len(data):
            b = data[offset]
            offset += 1
            unsigned |= (b & 0x7F) << shift
            shift += 7
            if not (b & 0x80):
                break
        # Zigzag decode
        value = (unsigned >> 1) ^ -(unsigned & 1)
        return value, offset

    def compress(self, data: bytes) -> bytes:
        """Compress data using delta encoding."""
        checksum = zlib.crc32(data) & 0xFFFFFFFF

        if not data:
            return struct.pack("<II", 0, checksum) + b"\x00"  # mode=0

        mode = self._mode if self._mode >= 0 else self._detect_mode(data)

        result = bytearray()
        result.extend(struct.pack("<II", len(data), checksum))
        result.append(mode)

        if mode == 0:
            # Byte-level delta
            result.append(data[0])
            prev = data[0]
            for i in range(1, len(data)):
                delta = data[i] - prev
                result.extend(self._encode_varint(delta))
                prev = data[i]
        elif mode == 1:
            # uint16 LE delta
            n = len(data) // 2
            # Store number of uint16 values as 2-byte LE
            result.extend(struct.pack("<H", n))
            vals = [struct.unpack_from("<H", data, i * 2)[0] for i in range(n)]
            result.extend(struct.pack("<H", vals[0]))
            prev = vals[0]
            for i in range(1, n):
                delta = vals[i] - prev
                result.extend(self._encode_varint(delta))
                prev = vals[i]
            # Store any trailing bytes literally
            trailing = data[n * 2:]
            if trailing:
                result.extend(trailing)
        elif mode == 2:
            # uint32 LE delta
            n = len(data) // 4
            # Store number of uint32 values as 2-byte LE
            result.extend(struct.pack("<H", n))
            vals = [struct.unpack_from("<I", data, i * 4)[0] for i in range(n)]
            result.extend(struct.pack("<I", vals[0]))
            prev = vals[0]
            for i in range(1, n):
                delta = vals[i] - prev
                result.extend(self._encode_varint(delta))
                prev = vals[i]
            # Store any trailing bytes literally
            trailing = data[n * 4:]
            if trailing:
                result.extend(trailing)

        return bytes(result)

    def decompress(self, data: bytes) -> bytes:
        """Decompress delta-encoded data."""
        if len(data) < 9:
            raise ValueError("Delta data too short for header")

        orig_len, checksum = struct.unpack("<II", data[:8])
        if orig_len == 0:
            if checksum != zlib.crc32(b"") & 0xFFFFFFFF:
                raise ValueError("CRC32 checksum mismatch")
            return b""

        mode = data[8]
        payload = data[9:]

        if mode == 0:
            # Byte-level delta
            result = bytearray()
            offset = 0
            first = payload[offset]
            offset += 1
            result.append(first)
            prev = first
            while len(result) < orig_len and offset < len(payload):
                delta, offset = self._decode_varint(payload, offset)
                value = (prev + delta) & 0xFF
                result.append(value)
                prev = value
        elif mode == 1:
            # uint16 LE delta
            result = bytearray()
            offset = 0
            n_vals = struct.unpack_from("<H", payload, offset)[0]
            offset += 2
            first = struct.unpack_from("<H", payload, offset)[0]
            offset += 2
            result.extend(struct.pack("<H", first))
            prev = first
            for _ in range(1, n_vals):
                delta, offset = self._decode_varint(payload, offset)
                value = prev + delta
                result.extend(struct.pack("<H", value & 0xFFFF))
                prev = value
            # Read any trailing bytes literally
            expected_trailing = orig_len - len(result)
            if expected_trailing > 0:
                result.extend(payload[offset:offset + expected_trailing])
        elif mode == 2:
            # uint32 LE delta
            result = bytearray()
            offset = 0
            n_vals = struct.unpack_from("<H", payload, offset)[0]
            offset += 2
            first = struct.unpack_from("<I", payload, offset)[0]
            offset += 4
            result.extend(struct.pack("<I", first))
            prev = first
            for _ in range(1, n_vals):
                delta, offset = self._decode_varint(payload, offset)
                value = prev + delta
                result.extend(struct.pack("<I", value & 0xFFFFFFFF))
                prev = value
            # Read any trailing bytes literally
            expected_trailing = orig_len - len(result)
            if expected_trailing > 0:
                result.extend(payload[offset:offset + expected_trailing])
        else:
            raise ValueError(f"Invalid delta mode: {mode}")

        result_bytes = bytes(result[:orig_len])
        if len(result_bytes) != orig_len:
            raise ValueError(f"Length mismatch: expected {orig_len}, got {len(result_bytes)}")
        actual_checksum = zlib.crc32(result_bytes) & 0xFFFFFFFF
        if actual_checksum != checksum:
            raise ValueError(f"CRC32 checksum mismatch: expected {checksum:#010x}, got {actual_checksum:#010x}")

        return result_bytes